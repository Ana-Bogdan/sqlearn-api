"""Unit tests for badge checkers, the factory, and award idempotency."""

from datetime import datetime, timedelta
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.curriculum.models import Chapter, Exercise, Lesson
from apps.gamification.badges import (
    EEST,
    BadgeFactory,
    FunBadgeChecker,
    MilestoneBadgeChecker,
    SandboxBadgeChecker,
    SkillBadgeChecker,
    StreakBadgeChecker,
    award_badge,
)
from apps.gamification.models import Badge, UserBadge
from apps.progress.models import ExerciseStatus, UserExerciseProgress
from apps.sandbox.models import SandboxQueryAttempt

User = get_user_model()


def _user(**kw):
    defaults = dict(
        email="u@example.com", password="pw-Complex-1!", first_name="U", last_name="U"
    )
    defaults.update(kw)
    return User.objects.create_user(**defaults)


class MilestoneBadgeCheckerTests(TestCase):
    def setUp(self):
        self.user = _user()
        self.chapter = Chapter.objects.create(title="C", order=1)
        self.lesson = Lesson.objects.create(chapter=self.chapter, title="L", order=1)
        self.ex = Exercise.objects.create(
            chapter=self.chapter, lesson=self.lesson, title="E",
            instructions="x", solution_query="SELECT 1;", is_published=True,
        )

    def test_first_query_after_one_completion(self):
        UserExerciseProgress.objects.create(
            user=self.user, exercise=self.ex, status=ExerciseStatus.COMPLETED
        )
        earned = MilestoneBadgeChecker().check(user=self.user)
        self.assertIn("first_query", earned)

    def test_chapter_initiate_when_chapter_completed(self):
        UserExerciseProgress.objects.create(
            user=self.user, exercise=self.ex, status=ExerciseStatus.COMPLETED
        )
        earned = MilestoneBadgeChecker().check(user=self.user)
        self.assertIn("chapter_initiate", earned)

    def test_no_badges_without_completions(self):
        earned = MilestoneBadgeChecker().check(user=self.user)
        self.assertEqual(earned, [])


class SkillBadgeCheckerTests(TestCase):
    def setUp(self):
        self.user = _user()
        self.chapter = Chapter.objects.create(title="Joins", order=5)
        self.lesson = Lesson.objects.create(chapter=self.chapter, title="L", order=1)

    def _complete(self, exercise, first_attempt=True):
        UserExerciseProgress.objects.create(
            user=self.user, exercise=exercise,
            status=ExerciseStatus.COMPLETED, first_attempt=first_attempt,
        )

    def test_perfectionist_after_five_first_attempts(self):
        for i in range(5):
            ex = Exercise.objects.create(
                chapter=self.chapter, lesson=self.lesson, title=f"E{i}",
                instructions="x", solution_query="SELECT 1;", is_published=True, order=i,
            )
            self._complete(ex)
        earned = SkillBadgeChecker().check(user=self.user)
        self.assertIn("perfectionist", earned)

    def test_chapter_skill_badge_when_chapter_fully_completed(self):
        ex = Exercise.objects.create(
            chapter=self.chapter, lesson=self.lesson, title="OnlyOne",
            instructions="x", solution_query="SELECT 1;", is_published=True,
        )
        self._complete(ex)
        earned = SkillBadgeChecker().check(user=self.user, exercise=ex)
        # Chapter order 5 maps to the join_master skill badge.
        self.assertIn("join_master", earned)

    def test_quiz_ace_after_three_first_attempt_quizzes(self):
        for i in range(3):
            quiz = Exercise.objects.create(
                chapter=self.chapter, title=f"Q{i}",
                instructions="x", solution_query="SELECT 1;", is_published=True,
                is_chapter_quiz=True, order=10 + i,
            )
            self._complete(quiz)
        earned = SkillBadgeChecker().check(user=self.user)
        self.assertIn("quiz_ace", earned)


class StreakBadgeCheckerTests(TestCase):
    def test_streak_thresholds(self):
        self.assertEqual(
            StreakBadgeChecker().check(user=SimpleNamespace(current_streak=2)), []
        )
        self.assertEqual(
            StreakBadgeChecker().check(user=SimpleNamespace(current_streak=3)),
            ["streak_3"],
        )
        self.assertEqual(
            set(StreakBadgeChecker().check(user=SimpleNamespace(current_streak=7))),
            {"streak_3", "streak_7"},
        )
        self.assertEqual(
            set(StreakBadgeChecker().check(user=SimpleNamespace(current_streak=30))),
            {"streak_3", "streak_7", "streak_30"},
        )


class FunBadgeCheckerTests(TestCase):
    def test_night_owl_between_midnight_and_five(self):
        completed = datetime(2026, 6, 13, 2, 0, tzinfo=EEST)
        earned = FunBadgeChecker().check(user=SimpleNamespace(), completed_at=completed)
        self.assertIn("night_owl", earned)

    def test_no_night_owl_during_the_day(self):
        completed = datetime(2026, 6, 13, 14, 0, tzinfo=EEST)
        earned = FunBadgeChecker().check(user=SimpleNamespace(), completed_at=completed)
        self.assertNotIn("night_owl", earned)

    def test_speed_demon_requires_prior_attempt(self):
        started = datetime(2026, 6, 13, 14, 0, tzinfo=EEST)
        completed = started + timedelta(seconds=10)
        earned = FunBadgeChecker().check(
            user=SimpleNamespace(),
            started_at=started,
            completed_at=completed,
            first_attempt=False,
        )
        self.assertIn("speed_demon", earned)

    def test_first_attempt_never_earns_speed_demon(self):
        started = datetime(2026, 6, 13, 14, 0, tzinfo=EEST)
        completed = started + timedelta(seconds=10)
        earned = FunBadgeChecker().check(
            user=SimpleNamespace(),
            started_at=started,
            completed_at=completed,
            first_attempt=True,
        )
        self.assertNotIn("speed_demon", earned)

    def test_brain_twister_after_ten_minutes(self):
        started = datetime(2026, 6, 13, 14, 0, tzinfo=EEST)
        completed = started + timedelta(minutes=11)
        earned = FunBadgeChecker().check(
            user=SimpleNamespace(),
            started_at=started,
            completed_at=completed,
            first_attempt=False,
        )
        self.assertIn("brain_twister", earned)


class SandboxBadgeCheckerTests(TestCase):
    def test_sandbox_explorer_after_twenty_attempts(self):
        user = _user()
        for _ in range(20):
            SandboxQueryAttempt.objects.create(user=user, sql_text="SELECT 1", succeeded=True)
        earned = SandboxBadgeChecker().check(user=user)
        self.assertIn("sandbox_explorer", earned)

    def test_no_badge_below_threshold(self):
        user = _user()
        SandboxQueryAttempt.objects.create(user=user, sql_text="SELECT 1", succeeded=True)
        self.assertEqual(SandboxBadgeChecker().check(user=user), [])


class BadgeFactoryTests(TestCase):
    def test_get_checker_returns_concrete_checker(self):
        self.assertIsInstance(BadgeFactory.get_checker("milestone"), MilestoneBadgeChecker)
        self.assertIsInstance(BadgeFactory.get_checker("sandbox"), SandboxBadgeChecker)

    def test_unknown_event_type_raises(self):
        with self.assertRaises(ValueError):
            BadgeFactory.get_checker("nope")

    def test_all_checkers_returns_one_of_each(self):
        self.assertEqual(len(BadgeFactory.all_checkers()), 5)


class AwardBadgeTests(TestCase):
    def setUp(self):
        self.user = _user()

    def test_award_is_idempotent(self):
        first = award_badge(self.user, "first_query")
        second = award_badge(self.user, "first_query")
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(
            UserBadge.objects.filter(user=self.user, badge=first).count(), 1
        )

    def test_unknown_trigger_returns_none(self):
        self.assertIsNone(award_badge(self.user, "does_not_exist"))
