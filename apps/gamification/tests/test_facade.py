"""Tests for the GamificationFacade — XP, level, streak, and badge orchestration."""

from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.curriculum.models import Chapter, Difficulty, Exercise, Lesson
from apps.gamification.badges import EEST
from apps.gamification.facade import GamificationFacade
from apps.progress.models import ExerciseStatus, UserExerciseProgress

User = get_user_model()


class GamificationFacadeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="u@example.com", password="pw-Complex-1!", first_name="U", last_name="U"
        )
        self.chapter = Chapter.objects.create(title="C", order=1)
        self.lesson = Lesson.objects.create(chapter=self.chapter, title="L", order=1)
        self.exercise = Exercise.objects.create(
            chapter=self.chapter, lesson=self.lesson, title="E",
            instructions="x", solution_query="SELECT 1;",
            difficulty=Difficulty.EASY, is_published=True,
        )
        self.completed_at = datetime(2026, 6, 13, 12, 0, tzinfo=EEST)

    def _run(self, *, first_attempt=True, completed_at=None):
        return GamificationFacade().process_exercise_completion(
            self.user,
            self.exercise,
            was_first_attempt=first_attempt,
            completed_at=completed_at or self.completed_at,
            started_at=self.completed_at,
        )

    def test_awards_base_plus_first_attempt_xp(self):
        result = self._run(first_attempt=True)
        # Easy (20) + first attempt 50% (10); streak just became 1 so no streak bonus.
        self.assertEqual(result["xp_earned"], 30)
        self.user.refresh_from_db()
        self.assertEqual(self.user.xp, 30)

    def test_level_up_is_reported(self):
        self.user.xp = 90
        self.user.save(update_fields=["xp"])
        quiz = Exercise.objects.create(
            chapter=self.chapter, title="Quiz", instructions="x",
            solution_query="SELECT 1;", is_published=True, is_chapter_quiz=True,
        )
        result = GamificationFacade().process_exercise_completion(
            self.user, quiz, was_first_attempt=False, completed_at=self.completed_at,
            started_at=self.completed_at,
        )
        # 90 + 100 (quiz) = 190 -> level 2.
        self.assertEqual(result["total_xp"], 190)
        self.assertEqual(result["level"], 2)
        self.assertTrue(result["level_up"])
        self.assertEqual(result["previous_level"], 1)

    def test_first_completion_starts_streak_at_one(self):
        result = self._run()
        self.assertTrue(result["streak_updated"])
        self.assertEqual(result["current_streak"], 1)
        self.assertEqual(result["longest_streak"], 1)

    def test_consecutive_day_increments_streak(self):
        yesterday = (self.completed_at - timedelta(days=1)).date()
        self.user.last_activity_date = yesterday
        self.user.current_streak = 1
        self.user.longest_streak = 1
        self.user.save()
        result = self._run()
        self.assertEqual(result["current_streak"], 2)
        self.assertEqual(result["longest_streak"], 2)

    def test_same_day_does_not_change_streak(self):
        self.user.last_activity_date = self.completed_at.astimezone(EEST).date()
        self.user.current_streak = 5
        self.user.save()
        result = self._run()
        self.assertFalse(result["streak_updated"])
        self.assertEqual(result["current_streak"], 5)

    def test_gap_resets_streak(self):
        self.user.last_activity_date = (self.completed_at - timedelta(days=5)).date()
        self.user.current_streak = 4
        self.user.longest_streak = 4
        self.user.save()
        result = self._run()
        self.assertEqual(result["current_streak"], 1)
        # Longest is preserved across the reset.
        self.assertEqual(result["longest_streak"], 4)

    def test_badges_earned_includes_first_query(self):
        UserExerciseProgress.objects.create(
            user=self.user, exercise=self.exercise, status=ExerciseStatus.COMPLETED
        )
        result = self._run()
        triggers = {b["trigger_type"] for b in result["badges_earned"]}
        self.assertIn("first_query", triggers)
