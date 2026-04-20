"""Factory Method — ``BadgeFactory`` returns the appropriate checker for an
event category. Each checker returns the set of badge ``trigger_type`` strings
the user should now own; the facade is responsible for persisting them.

Four checker categories, one per badge grouping in the spec (milestone, skill,
streak, fun).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone as dt_timezone

from django.db.models import Count, Q

EEST = dt_timezone(timedelta(hours=3))


# Chapter ``order`` → trigger_type for chapter-specific skill badges.
CHAPTER_SKILL_BADGES: dict[int, str] = {
    5: "join_master",
    6: "subquery_sage",
    7: "data_surgeon",
}


class BadgeChecker(ABC):
    event_type: str = ""

    @abstractmethod
    def check(self, *, user, **context) -> list[str]:
        """Return trigger_types earned by this event."""


class MilestoneBadgeChecker(BadgeChecker):
    event_type = "milestone"

    def check(self, *, user, exercise=None, **_context) -> list[str]:
        from apps.curriculum.models import Chapter
        from apps.progress.models import ExerciseStatus, UserExerciseProgress

        earned: list[str] = []

        total_completed = UserExerciseProgress.objects.filter(
            user=user, status=ExerciseStatus.COMPLETED
        ).count()
        if total_completed >= 1:
            earned.append("first_query")

        chapter_counts = (
            Chapter.objects.active()
            .annotate(
                total=Count(
                    "exercises",
                    filter=Q(
                        exercises__is_active=True,
                        exercises__is_published=True,
                    ),
                    distinct=True,
                ),
                done=Count(
                    "exercises__user_progress",
                    filter=Q(
                        exercises__is_active=True,
                        exercises__is_published=True,
                        exercises__user_progress__user=user,
                        exercises__user_progress__status=ExerciseStatus.COMPLETED,
                    ),
                    distinct=True,
                ),
            )
            .values_list("total", "done")
        )

        completed_chapters = sum(
            1 for total, done in chapter_counts if total > 0 and done >= total
        )
        if completed_chapters >= 1:
            earned.append("chapter_initiate")
        if completed_chapters >= 4:
            earned.append("halfway_there")
        if completed_chapters >= 8:
            earned.append("curriculum_complete")
        return earned


class SkillBadgeChecker(BadgeChecker):
    event_type = "skill"

    def check(self, *, user, exercise=None, **_context) -> list[str]:
        from apps.progress.models import ExerciseStatus, UserExerciseProgress

        earned: list[str] = []

        first_attempt_completions = UserExerciseProgress.objects.filter(
            user=user,
            status=ExerciseStatus.COMPLETED,
            first_attempt=True,
        ).count()
        if first_attempt_completions >= 5:
            earned.append("perfectionist")

        first_attempt_quizzes = UserExerciseProgress.objects.filter(
            user=user,
            status=ExerciseStatus.COMPLETED,
            first_attempt=True,
            exercise__is_chapter_quiz=True,
        ).count()
        if first_attempt_quizzes >= 3:
            earned.append("quiz_ace")

        if exercise is not None and exercise.chapter_id:
            trigger = CHAPTER_SKILL_BADGES.get(exercise.chapter.order)
            if trigger and self._chapter_fully_completed(user, exercise.chapter):
                earned.append(trigger)

        return earned

    @staticmethod
    def _chapter_fully_completed(user, chapter) -> bool:
        from apps.curriculum.models import Exercise
        from apps.progress.models import ExerciseStatus, UserExerciseProgress

        total = Exercise.objects.visible().filter(chapter=chapter).count()
        if total == 0:
            return False
        done = UserExerciseProgress.objects.filter(
            user=user,
            status=ExerciseStatus.COMPLETED,
            exercise__chapter=chapter,
            exercise__is_active=True,
            exercise__is_published=True,
        ).count()
        return done >= total


class StreakBadgeChecker(BadgeChecker):
    event_type = "streak"

    def check(self, *, user, **_context) -> list[str]:
        earned: list[str] = []
        streak = getattr(user, "current_streak", 0) or 0
        if streak >= 3:
            earned.append("streak_3")
        if streak >= 7:
            earned.append("streak_7")
        if streak >= 30:
            earned.append("streak_30")
        return earned


class FunBadgeChecker(BadgeChecker):
    """Time-based fun badges.

    ``started_at`` is the moment the learner first touched this exercise
    (``UserExerciseProgress.created_at``). On a first-attempt correct submission
    the delta is effectively zero, so the speed badge requires a prior
    attempt — otherwise every first-try solve would be "under 30 seconds".
    """

    event_type = "fun"

    def check(
        self,
        *,
        user,
        completed_at: datetime | None = None,
        started_at: datetime | None = None,
        first_attempt: bool = False,
        **_context,
    ) -> list[str]:
        earned: list[str] = []

        if completed_at is not None:
            local_hour = completed_at.astimezone(EEST).hour
            if 0 <= local_hour < 5:
                earned.append("night_owl")

        if started_at is not None and completed_at is not None and not first_attempt:
            delta = (completed_at - started_at).total_seconds()
            if 0 <= delta < 30:
                earned.append("speed_demon")
            if delta >= 600:
                earned.append("brain_twister")

        return earned


class BadgeFactory:
    """Factory Method — ``get_checker(event_type)`` dispatches to a concrete
    checker. ``all_checkers()`` returns one of each so the facade can run the
    full sweep after every completion."""

    _checker_classes: dict[str, type[BadgeChecker]] = {
        "milestone": MilestoneBadgeChecker,
        "skill": SkillBadgeChecker,
        "streak": StreakBadgeChecker,
        "fun": FunBadgeChecker,
    }

    @classmethod
    def get_checker(cls, event_type: str) -> BadgeChecker:
        try:
            return cls._checker_classes[event_type]()
        except KeyError as exc:
            raise ValueError(f"Unknown badge event type: {event_type}") from exc

    @classmethod
    def all_checkers(cls) -> list[BadgeChecker]:
        return [checker_cls() for checker_cls in cls._checker_classes.values()]


def award_badge(user, trigger_type: str):
    """Idempotently grant a badge. Returns the ``Badge`` instance if this call
    actually awarded it to the user (first time), otherwise ``None``."""
    from .models import Badge, UserBadge

    badge = Badge.objects.filter(trigger_type=trigger_type).first()
    if badge is None:
        return None
    _, created = UserBadge.objects.get_or_create(user=user, badge=badge)
    return badge if created else None
