"""Admin REST endpoints (Milestone 15).

All endpoints in this module require ``IsAdmin`` (see
``apps.authentication.permissions``). Soft delete is implemented for
chapters, lessons, exercises and datasets by flipping ``is_active`` to
``False`` so historical user progress / submissions stay intact.

The exercise ``test-solution`` endpoint runs ``solution_query`` against the
exercise's dataset using the same per-user sandbox infrastructure used at
runtime, so admins always validate against the exact environment the
learner will see.
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, F, FloatField, Q
from django.db.models.expressions import ExpressionWrapper
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdmin
from apps.curriculum.models import Chapter, Exercise, Lesson
from apps.gamification.models import Badge
from apps.progress.models import ExerciseStatus, UserExerciseProgress
from apps.sandbox.models import ExerciseDataset, SandboxSchema
from apps.sandbox.services import (
    QueryExecutionError,
    QueryExecutionService,
    QuerySyntaxError,
    QueryTimeout,
    SandboxService,
)

from .pagination import AdminPagination
from .serializers import (
    AdminBadgeSerializer,
    AdminChapterReorderSerializer,
    AdminChapterSerializer,
    AdminExerciseSerializer,
    AdminLessonSerializer,
    AdminSandboxSchemaSerializer,
    AdminStatsSerializer,
    AdminUserSerializer,
    TestSolutionResultSerializer,
)

User = get_user_model()


class AdminChapterListCreateView(generics.ListCreateAPIView):
    """``GET/POST /api/admin/chapters/``.

    Admin listing includes inactive chapters so soft-deleted content is
    still visible for restoration.
    """

    permission_classes = [IsAdmin]
    serializer_class = AdminChapterSerializer
    queryset = Chapter.objects.all().order_by("order", "id")
    pagination_class = None


class AdminChapterDetailView(generics.RetrieveUpdateDestroyAPIView):
    """``GET/PUT/PATCH/DELETE /api/admin/chapters/{id}/`` (soft delete)."""

    permission_classes = [IsAdmin]
    serializer_class = AdminChapterSerializer
    queryset = Chapter.objects.all()

    def perform_destroy(self, instance: Chapter) -> None:
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class AdminChapterReorderView(APIView):
    """``PATCH /api/admin/chapters/{id}/reorder/``.

    Moves a chapter to ``order = N`` and shifts the affected siblings.
    """

    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        chapter = get_object_or_404(Chapter, pk=pk)
        serializer = AdminChapterReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = serializer.validated_data["order"]

        with transaction.atomic():
            old = chapter.order
            if target == old:
                return Response(AdminChapterSerializer(chapter).data)

            siblings = Chapter.objects.exclude(pk=chapter.pk)
            if target > old:
                # Pulled down — shift items in (old, target] up by one.
                siblings.filter(order__gt=old, order__lte=target).update(
                    order=F("order") - 1
                )
            else:
                # Pulled up — shift items in [target, old) down by one.
                siblings.filter(order__gte=target, order__lt=old).update(
                    order=F("order") + 1
                )

            chapter.order = target
            chapter.save(update_fields=["order", "updated_at"])

        return Response(AdminChapterSerializer(chapter).data)


class AdminLessonCreateView(generics.CreateAPIView):
    """``POST /api/admin/lessons/``."""

    permission_classes = [IsAdmin]
    serializer_class = AdminLessonSerializer
    queryset = Lesson.objects.all()


class AdminLessonDetailView(generics.RetrieveUpdateDestroyAPIView):
    """``GET/PUT/PATCH/DELETE /api/admin/lessons/{id}/`` (soft delete)."""

    permission_classes = [IsAdmin]
    serializer_class = AdminLessonSerializer
    queryset = Lesson.objects.all()

    def perform_destroy(self, instance: Lesson) -> None:
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class AdminExerciseCreateView(generics.CreateAPIView):
    """``POST /api/admin/exercises/``."""

    permission_classes = [IsAdmin]
    serializer_class = AdminExerciseSerializer
    queryset = Exercise.objects.all()


class AdminExerciseDetailView(generics.RetrieveUpdateDestroyAPIView):
    """``GET/PUT/PATCH/DELETE /api/admin/exercises/{id}/`` (soft delete)."""

    permission_classes = [IsAdmin]
    serializer_class = AdminExerciseSerializer
    queryset = Exercise.objects.prefetch_related("hints", "datasets")

    def perform_destroy(self, instance: Exercise) -> None:
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class AdminExerciseTestSolutionView(APIView):
    """``POST /api/admin/exercises/{id}/test-solution/``.

    Runs ``solution_query`` against the exercise's dataset in the admin's
    own sandbox schema and returns the result rows. Used by the FE
    "Test Solution" button to auto-populate ``expected_result``.
    """

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        exercise = get_object_or_404(
            Exercise.objects.prefetch_related("datasets__sandbox_schema"),
            pk=pk,
        )

        if not exercise.solution_query.strip():
            return Response(
                {"detail": "Exercise has no solution_query."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sandbox_schemas = [
            link.sandbox_schema
            for link in ExerciseDataset.objects.filter(exercise=exercise)
            .select_related("sandbox_schema")
            .order_by("id")
        ]
        if not sandbox_schemas:
            return Response(
                {"detail": "Exercise is not linked to any dataset."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        SandboxService().prepare_exercise_schema(request.user.id, sandbox_schemas)

        try:
            result = QueryExecutionService().run(
                request.user.id, exercise.solution_query
            )
        except QuerySyntaxError as exc:
            return Response(
                {"detail": "Solution has a syntax error.", "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except QueryTimeout as exc:
            return Response(
                {"detail": "Solution timed out.", "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except QueryExecutionError as exc:
            return Response(
                {"detail": "Solution failed to execute.", "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(TestSolutionResultSerializer(result).data)


class AdminDatasetListCreateView(generics.ListCreateAPIView):
    """``GET/POST /api/admin/datasets/``."""

    permission_classes = [IsAdmin]
    serializer_class = AdminSandboxSchemaSerializer
    queryset = SandboxSchema.objects.all().order_by("name")
    pagination_class = None


class AdminDatasetDetailView(generics.RetrieveUpdateDestroyAPIView):
    """``GET/PUT/PATCH/DELETE /api/admin/datasets/{id}/``.

    Datasets aren't soft-deleted: ``ExerciseDataset.sandbox_schema`` uses
    ``on_delete=PROTECT``, so a delete attempt while datasets are linked to
    exercises returns a 409 with a clear message instead of a 500.
    """

    permission_classes = [IsAdmin]
    serializer_class = AdminSandboxSchemaSerializer
    queryset = SandboxSchema.objects.all()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.exercise_datasets.exists():
            return Response(
                {
                    "detail": (
                        "Cannot delete a dataset that is still linked to one "
                        "or more exercises."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)


class AdminBadgeDetailView(generics.RetrieveUpdateAPIView):
    """``GET/PUT/PATCH /api/admin/badges/{id}/`` — display fields only."""

    permission_classes = [IsAdmin]
    serializer_class = AdminBadgeSerializer
    queryset = Badge.objects.all()


class AdminBadgeListView(generics.ListAPIView):
    """``GET /api/admin/badges/`` — list all badges (admin view)."""

    permission_classes = [IsAdmin]
    serializer_class = AdminBadgeSerializer
    queryset = Badge.objects.all().order_by("category", "id")
    pagination_class = None


class AdminUserListView(generics.ListAPIView):
    """``GET /api/admin/users/`` — paginated, search by email/name."""

    permission_classes = [IsAdmin]
    serializer_class = AdminUserSerializer
    pagination_class = AdminPagination

    def get_queryset(self):
        qs = User.objects.all().order_by("-created_at")
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "false"}:
            qs = qs.filter(is_active=(is_active == "true"))
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        return qs


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    """``GET/PATCH /api/admin/users/{id}/`` — primarily for deactivate."""

    permission_classes = [IsAdmin]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all()
    http_method_names = ["get", "patch", "head", "options"]


class AdminStatsView(APIView):
    """``GET /api/admin/stats/`` — dashboard metrics."""

    permission_classes = [IsAdmin]

    def get(self, request):
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)

        total_users = User.objects.count()
        active_today = User.objects.filter(last_activity_date=today).count()
        active_this_week = User.objects.filter(
            last_activity_date__gte=today - timedelta(days=6)
        ).count()
        new_registrations_this_week = User.objects.filter(
            created_at__gte=week_ago
        ).count()

        completed_total = UserExerciseProgress.objects.filter(
            status=ExerciseStatus.COMPLETED
        ).count()
        avg_exercises_per_user = (
            completed_total / total_users if total_users else 0.0
        )

        # Failure ranking only considers exercises with at least one
        # submission so we don't surface freshly-published exercises with a
        # bogus 100% fail rate from a single early attempt — and exclude
        # unattempted exercises from "most attempted" too.
        attempts_qs = (
            Exercise.objects.filter(is_active=True, is_published=True)
            .annotate(
                attempts=Count("submissions", distinct=True),
                failures=Count(
                    "submissions",
                    filter=Q(submissions__was_correct=False),
                    distinct=True,
                ),
            )
            .filter(attempts__gt=0)
            .annotate(
                fail_rate=ExpressionWrapper(
                    Cast("failures", FloatField())
                    / Cast("attempts", FloatField()),
                    output_field=FloatField(),
                )
            )
        )

        highest_fail_rate = list(
            attempts_qs.order_by("-fail_rate", "-attempts", "id")[:5].values(
                "id",
                "title",
                "chapter_id",
                "lesson_id",
                "attempts",
                "failures",
                "fail_rate",
            )
        )
        most_attempted = list(
            attempts_qs.order_by("-attempts", "id")[:5].values(
                "id",
                "title",
                "chapter_id",
                "lesson_id",
                "attempts",
                "failures",
                "fail_rate",
            )
        )

        payload = {
            "total_users": total_users,
            "active_today": active_today,
            "active_this_week": active_this_week,
            "new_registrations_this_week": new_registrations_this_week,
            "avg_exercises_per_user": round(avg_exercises_per_user, 2),
            "highest_fail_rate_exercises": highest_fail_rate,
            "most_attempted_exercises": most_attempted,
        }
        return Response(AdminStatsSerializer(payload).data)


__all__ = [
    "AdminBadgeDetailView",
    "AdminBadgeListView",
    "AdminChapterDetailView",
    "AdminChapterListCreateView",
    "AdminChapterReorderView",
    "AdminDatasetDetailView",
    "AdminDatasetListCreateView",
    "AdminExerciseCreateView",
    "AdminExerciseDetailView",
    "AdminExerciseTestSolutionView",
    "AdminLessonCreateView",
    "AdminLessonDetailView",
    "AdminStatsView",
    "AdminUserDetailView",
    "AdminUserListView",
]
