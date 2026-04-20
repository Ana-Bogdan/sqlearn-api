from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.curriculum.models import Exercise
from apps.gamification.signals import dispatch_exercise_completed
from apps.progress.models import (
    ExerciseStatus,
    QuerySubmission,
    UserExerciseProgress,
)
from apps.sandbox.models import ExerciseDataset

from .serializers import SubmitQuerySerializer
from .services import (
    QueryExecutionService,
    QueryValidationPipeline,
    SandboxService,
    SubmissionContext,
)


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
