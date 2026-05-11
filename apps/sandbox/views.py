from __future__ import annotations

import re

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.curriculum.models import Exercise, Lesson
from apps.gamification.signals import (
    check_sandbox_badges,
    dispatch_exercise_completed,
)
from apps.progress.models import (
    ExerciseStatus,
    QuerySubmission,
    UserExerciseProgress,
)
from apps.sandbox.models import ExerciseDataset, SandboxQueryAttempt

from .serializers import SandboxExecuteSerializer, SubmitQuerySerializer
from .services import (
    QueryExecutionError,
    QueryExecutionService,
    QuerySyntaxError,
    QueryTimeout,
    QueryValidationPipeline,
    SandboxNotConfigured,
    SandboxService,
    SubmissionContext,
)


def _exercise_lock_reason(user, exercise: Exercise) -> str | None:
    """Return a human-readable reason if this exercise is locked for this user.

    Mirrors the chapter-detail serializer logic so the rule lives in one place
    semantically: lesson exercises require all earlier lessons in the chapter
    to be complete; chapter quizzes require *every* lesson complete.
    """
    if exercise.lesson_id is not None and not exercise.is_chapter_quiz:
        prior_lessons = (
            Lesson.objects.filter(
                chapter_id=exercise.chapter_id, is_active=True
            )
            .filter(order__lt=exercise.lesson.order)
            .with_user_progress(user)
        )
        if any(not bool(l.is_completed) for l in prior_lessons):
            return (
                "Finish the previous lesson before tackling this one."
            )
        return None

    if exercise.is_chapter_quiz:
        lessons = (
            Lesson.objects.filter(
                chapter_id=exercise.chapter_id, is_active=True
            )
            .with_user_progress(user)
        )
        if not lessons.exists():
            return None
        if any(not bool(l.is_completed) for l in lessons):
            return (
                "Complete every lesson in this chapter to unlock the quiz."
            )

    return None


class ExerciseSubmitView(APIView):
    """Run a submitted SQL query through the validation pipeline.

    1. Resets the user's sandbox schema to the exercise dataset's template.
    2. Walks the Chain of Responsibility
       (forbidden op → syntax → execution → comparison).
    3. Records a ``QuerySubmission`` and updates ``UserExerciseProgress``.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        serializer = SubmitQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sql = serializer.validated_data["sql_text"]

        exercise = get_object_or_404(
            Exercise.objects.visible().select_related("chapter"), pk=pk
        )
        user = request.user

        # Enforce sequential progression: a learner can't submit against a
        # lesson exercise whose lesson is locked, nor a chapter quiz before
        # every lesson in the chapter is finished. Admins/staff bypass this
        # so they can validate authored content end-to-end.
        if not user.is_staff:
            lock_message = _exercise_lock_reason(user, exercise)
            if lock_message is not None:
                return Response(
                    {
                        "status": "forbidden",
                        "message": lock_message,
                        "user_status": ExerciseStatus.NOT_STARTED,
                        "was_first_attempt": False,
                        "submission_count": 0,
                        "gamification": None,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        sandbox_schemas = [
            link.sandbox_schema
            for link in ExerciseDataset.objects.filter(exercise=exercise)
            .select_related("sandbox_schema")
            .order_by("id")
        ]
        SandboxService().prepare_exercise_schema(user.id, sandbox_schemas)

        context = SubmissionContext(user=user, exercise=exercise, sql=sql)
        pipeline = QueryValidationPipeline(QueryExecutionService())
        outcome = pipeline.run(context)

        prior_submission_count = QuerySubmission.objects.filter(
            user=user, exercise=exercise
        ).count()
        QuerySubmission.objects.create(
            user=user,
            exercise=exercise,
            sql_text=sql,
            was_correct=context.is_correct,
        )

        progress, _ = UserExerciseProgress.objects.get_or_create(
            user=user, exercise=exercise
        )

        gamification_result = None
        if context.is_correct:
            if progress.status != ExerciseStatus.COMPLETED:
                progress.status = ExerciseStatus.COMPLETED
                progress.completed_at = timezone.now()
                progress.first_attempt = prior_submission_count == 0
                progress.save(
                    update_fields=[
                        "status",
                        "completed_at",
                        "first_attempt",
                        "updated_at",
                    ]
                )
                gamification_result = dispatch_exercise_completed(
                    user=user, exercise=exercise, progress=progress
                )
        else:
            if progress.status == ExerciseStatus.NOT_STARTED:
                progress.status = ExerciseStatus.ATTEMPTED
                progress.save(update_fields=["status", "updated_at"])

        response = {
            **outcome,
            "user_status": progress.status,
            "was_first_attempt": bool(
                context.is_correct
                and progress.status == ExerciseStatus.COMPLETED
                and progress.first_attempt
            ),
            "submission_count": prior_submission_count + 1,
            "gamification": gamification_result,
        }
        return Response(response)


# ---------------------------------------------------------------------------
# Free Sandbox (Milestone 18)
# ---------------------------------------------------------------------------

# DDL is forbidden in the playground so the schema browser stays in sync with
# the seeded shape. Writes (INSERT/UPDATE/DELETE) are allowed — that's the
# whole point of free play.
_DDL_PATTERN = re.compile(
    r"\b(CREATE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|VACUUM|REINDEX|CLUSTER)\b",
    re.IGNORECASE,
)
_COMMENT_LINE = re.compile(r"--[^\n]*", re.MULTILINE)
_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_sql_comments(sql: str) -> str:
    return _COMMENT_LINE.sub(
        " ", _COMMENT_BLOCK.sub(" ", sql)
    )


class SandboxExecuteView(APIView):
    """POST /api/sandbox/execute/ — run free-play SQL in the playground.

    Differs from exercise submission: no expected-result comparison, no
    progress tracking, but every attempt is logged in
    ``SandboxQueryAttempt`` so the Sandbox Explorer badge can fire.
    """

    permission_classes = [IsAuthenticated]
    execution_service = QueryExecutionService()

    def post(self, request):
        serializer = SandboxExecuteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sql = serializer.validated_data["sql_text"]
        user = request.user

        if _DDL_PATTERN.search(_strip_sql_comments(sql)):
            self._record_attempt(user, sql, succeeded=False)
            return Response(
                {
                    "status": "forbidden",
                    "message": (
                        "Schema-changing statements (CREATE, DROP, ALTER, "
                        "TRUNCATE, GRANT, REVOKE) aren't allowed in the "
                        "playground — use Reset to start fresh instead."
                    ),
                    "badges_earned": [],
                }
            )

        try:
            schema_name, _ = SandboxService().get_or_create_playground(user.id)
        except SandboxNotConfigured as exc:
            return Response(
                {"status": "execution_error", "message": str(exc), "badges_earned": []},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            result = self.execution_service.run(
                user.id, sql, schema_name=schema_name
            )
        except QueryTimeout:
            self._record_attempt(user, sql, succeeded=False)
            return Response(
                {
                    "status": "timeout",
                    "message": (
                        "Your query took longer than 5 seconds to run. Try "
                        "narrowing it down or adding a filter."
                    ),
                    "badges_earned": [],
                }
            )
        except QuerySyntaxError as exc:
            self._record_attempt(user, sql, succeeded=False)
            return Response(
                {
                    "status": "syntax_error",
                    "message": f"Syntax error: {exc}",
                    "badges_earned": [],
                }
            )
        except QueryExecutionError as exc:
            self._record_attempt(user, sql, succeeded=False)
            return Response(
                {
                    "status": "execution_error",
                    "message": str(exc),
                    "badges_earned": [],
                }
            )

        self._record_attempt(user, sql, succeeded=True)
        badges = check_sandbox_badges(user)
        return Response(
            {
                "status": "ok",
                "result": result,
                "badges_earned": badges,
            }
        )

    @staticmethod
    def _record_attempt(user, sql: str, *, succeeded: bool) -> None:
        SandboxQueryAttempt.objects.create(
            user=user,
            sql_text=sql,
            succeeded=succeeded,
        )


class SandboxSchemaView(APIView):
    """GET /api/sandbox/schema/ — playground table & column metadata.

    Reads ``information_schema`` for the user's playground schema after
    ensuring it exists, so the response reflects live state (including
    rows the learner may have inserted) rather than the seed snapshot.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            tables = SandboxService().introspect_playground(request.user.id)
        except SandboxNotConfigured as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                "tables": [
                    {
                        "name": t.name,
                        "row_count": t.row_count,
                        "columns": [
                            {
                                "name": c.name,
                                "data_type": c.data_type,
                                "is_nullable": c.is_nullable,
                            }
                            for c in t.columns
                        ],
                    }
                    for t in tables
                ]
            }
        )


class SandboxResetView(APIView):
    """POST /api/sandbox/reset/ — drop and re-seed the user's playground."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            SandboxService().reset_playground(request.user.id)
        except SandboxNotConfigured as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "reset"})
