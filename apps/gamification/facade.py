"""Facade — single entry point for "exercise just completed" post-processing.

Coordinates the gamification subsystems:
1. Update the learner's streak (EEST calendar day).
2. Build the Decorator-based XP chain and award XP.
3. Recompute level from total XP.
4. Run every ``BadgeChecker`` from ``BadgeFactory`` and persist new badges.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timedelta

from django.utils import timezone

from .badges import EEST, BadgeFactory, award_badge
from .levels import level_for_xp, next_threshold, title_for_level
from .xp import build_calculator


class GamificationFacade:
    def process_exercise_completion(
        self,
        user,
        exercise,
        *,
        was_first_attempt: bool,
        completed_at: datetime | None = None,
        started_at: datetime | None = None,
    ) -> dict:
        completed_at = completed_at or timezone.now()

        streak_updated = self._update_streak(user, completed_at)

        calculator = build_calculator(
            exercise,
            first_attempt=was_first_attempt,
            streak_days=user.current_streak,
        )
        xp_earned = calculator.calculate()
        breakdown = [asdict(line) for line in calculator.breakdown()]

        previous_level = user.level
        user.xp = (user.xp or 0) + xp_earned
        new_level = level_for_xp(user.xp)
        user.level = new_level
        user.save(update_fields=["xp", "level"])

        badges_earned = self._check_and_award_badges(
            user=user,
            exercise=exercise,
            completed_at=completed_at,
            started_at=started_at,
            first_attempt=was_first_attempt,
        )

        return {
            "xp_earned": xp_earned,
            "xp_breakdown": breakdown,
            "total_xp": user.xp,
            "level": new_level,
            "level_title": title_for_level(new_level),
            "level_up": new_level > previous_level,
            "previous_level": previous_level,
            "next_level_xp": next_threshold(new_level),
            "current_streak": user.current_streak,
            "longest_streak": user.longest_streak,
            "streak_updated": streak_updated,
            "badges_earned": badges_earned,
        }

    def _update_streak(self, user, completed_at: datetime) -> bool:
        today = completed_at.astimezone(EEST).date()
        last: date | None = user.last_activity_date

        if last == today:
            return False

        if last == today - timedelta(days=1):
            user.current_streak = (user.current_streak or 0) + 1
        else:
            user.current_streak = 1

        user.longest_streak = max(user.longest_streak or 0, user.current_streak)
        user.last_activity_date = today
        user.save(
            update_fields=[
                "current_streak",
                "longest_streak",
                "last_activity_date",
            ]
        )
        return True

    def _check_and_award_badges(
        self,
        *,
        user,
        exercise,
        completed_at: datetime,
        started_at: datetime | None,
        first_attempt: bool,
    ) -> list[dict]:
        from .serializers import BadgeSerializer

        context = {
            "user": user,
            "exercise": exercise,
            "completed_at": completed_at,
            "started_at": started_at,
            "first_attempt": first_attempt,
        }

        triggers: list[str] = []
        seen: set[str] = set()
        for checker in BadgeFactory.all_checkers():
            for trigger in checker.check(**context):
                if trigger not in seen:
                    seen.add(trigger)
                    triggers.append(trigger)

        awarded = []
        for trigger in triggers:
            badge = award_badge(user, trigger)
            if badge is not None:
                awarded.append(BadgeSerializer(badge).data)
        return awarded
