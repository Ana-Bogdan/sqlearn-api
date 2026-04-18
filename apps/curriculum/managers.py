from __future__ import annotations

from django.db import models
from django.db.models import (
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce


def _completed_status_value() -> str:
    from apps.progress.models import ExerciseStatus

    return ExerciseStatus.COMPLETED


def _active_exercise_filter(prefix: str = "") -> Q:
    p = f"{prefix}__" if prefix else ""
    return Q(**{f"{p}is_active": True, f"{p}is_published": True})


class ChapterQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def with_user_progress(self, user):
        from apps.progress.models import UserExerciseProgress

        total_expr = Count(
            "exercises",
            filter=Q(exercises__is_active=True, exercises__is_published=True),
            distinct=True,
        )

        if user is None or not user.is_authenticated:
            return self.annotate(
                total_exercises=total_expr,
                completed_exercises=Value(0, output_field=IntegerField()),
                completion_percent=Value(0.0, output_field=FloatField()),
            )

        completed_subquery = (
            UserExerciseProgress.objects.filter(
                user=user,
                exercise__chapter=OuterRef("pk"),
                exercise__is_active=True,
                exercise__is_published=True,
                status=_completed_status_value(),
            )
            .values("exercise__chapter")
            .annotate(cnt=Count("id"))
            .values("cnt")
        )

        qs = self.annotate(
            total_exercises=total_expr,
            completed_exercises=Coalesce(
                Subquery(completed_subquery, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            ),
        )

        return qs.annotate(
            completion_percent=ExpressionWrapper(
                100.0 * F("completed_exercises") / F("total_exercises"),
                output_field=FloatField(),
            )
        )


class ChapterManager(models.Manager.from_queryset(ChapterQuerySet)):
    def get_queryset(self):
        return super().get_queryset()


class LessonQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def for_chapter(self, chapter_id):
        return self.filter(chapter_id=chapter_id, is_active=True).order_by("order")

    def with_user_progress(self, user):
        from apps.progress.models import UserExerciseProgress, UserLessonProgress

        total_expr = Count(
            "exercises",
            filter=Q(
                exercises__is_active=True,
                exercises__is_published=True,
                exercises__is_chapter_quiz=False,
            ),
            distinct=True,
        )

        if user is None or not user.is_authenticated:
            return self.annotate(
                total_exercises=total_expr,
                completed_exercises=Value(0, output_field=IntegerField()),
                is_completed=Value(False, output_field=models.BooleanField()),
            )

        completed_subquery = (
            UserExerciseProgress.objects.filter(
                user=user,
                exercise__lesson=OuterRef("pk"),
                exercise__is_active=True,
                exercise__is_published=True,
                exercise__is_chapter_quiz=False,
                status=_completed_status_value(),
            )
            .values("exercise__lesson")
            .annotate(cnt=Count("id"))
            .values("cnt")
        )

        lesson_done_subquery = UserLessonProgress.objects.filter(
            user=user, lesson=OuterRef("pk"), is_completed=True
        ).values("pk")[:1]

        return self.annotate(
            total_exercises=total_expr,
            completed_exercises=Coalesce(
                Subquery(completed_subquery, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            ),
            is_completed=models.Exists(lesson_done_subquery),
        )


class LessonManager(models.Manager.from_queryset(LessonQuerySet)):
    pass


class ExerciseQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(is_active=True, is_published=True)

    def for_lesson(self, lesson_id):
        return (
            self.filter(
                lesson_id=lesson_id,
                is_active=True,
                is_published=True,
                is_chapter_quiz=False,
            )
            .order_by("order")
        )

    def for_chapter(self, chapter_id, *, include_lesson_exercises: bool = False):
        qs = self.filter(
            chapter_id=chapter_id, is_active=True, is_published=True
        )
        if not include_lesson_exercises:
            qs = qs.filter(is_chapter_quiz=True)
        return qs.order_by("order")

    def with_user_status(self, user):
        from apps.progress.models import ExerciseStatus, UserExerciseProgress

        if user is None or not user.is_authenticated:
            return self.annotate(
                user_status=Value(
                    ExerciseStatus.NOT_STARTED, output_field=models.CharField()
                )
            )

        progress_subquery = UserExerciseProgress.objects.filter(
            user=user, exercise=OuterRef("pk")
        ).values("status")[:1]

        return self.annotate(
            user_status=Coalesce(
                Subquery(progress_subquery, output_field=models.CharField()),
                Value(ExerciseStatus.NOT_STARTED),
                output_field=models.CharField(),
            )
        )


class ExerciseManager(models.Manager.from_queryset(ExerciseQuerySet)):
    pass
