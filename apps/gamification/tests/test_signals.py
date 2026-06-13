"""Tests for the gamification signal receivers and dispatch helpers."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.curriculum.models import Chapter, Exercise, Lesson
from apps.gamification.signals import (
    check_sandbox_badges,
    dispatch_exercise_completed,
)
from apps.progress.models import (
    ExerciseStatus,
    UserExerciseProgress,
    UserLessonProgress,
)
from apps.sandbox.models import SandboxQueryAttempt

User = get_user_model()


class DispatchExerciseCompletedTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="u@example.com", password="pw-Complex-1!", first_name="U", last_name="U"
        )
        self.chapter = Chapter.objects.create(title="C", order=1)
        self.lesson = Lesson.objects.create(chapter=self.chapter, title="L", order=1)
        self.exercise = Exercise.objects.create(
            chapter=self.chapter, lesson=self.lesson, title="E",
            instructions="x", solution_query="SELECT 1;", is_published=True,
        )

    def _complete(self, exercise):
        progress = UserExerciseProgress.objects.create(
            user=self.user, exercise=exercise,
            status=ExerciseStatus.COMPLETED, completed_at=timezone.now(),
        )
        return progress

    def test_dispatch_returns_gamification_dict(self):
        progress = self._complete(self.exercise)
        result = dispatch_exercise_completed(
            user=self.user, exercise=self.exercise, progress=progress
        )
        self.assertIsInstance(result, dict)
        self.assertIn("xp_earned", result)

    def test_lesson_progress_marked_complete_when_all_exercises_done(self):
        # Single exercise in the lesson; completing it should complete the lesson.
        progress = self._complete(self.exercise)
        dispatch_exercise_completed(
            user=self.user, exercise=self.exercise, progress=progress
        )
        lesson_progress = UserLessonProgress.objects.get(
            user=self.user, lesson=self.lesson
        )
        self.assertTrue(lesson_progress.is_completed)

    def test_quiz_completion_creates_no_lesson_progress(self):
        quiz = Exercise.objects.create(
            chapter=self.chapter, title="Quiz", instructions="x",
            solution_query="SELECT 1;", is_published=True, is_chapter_quiz=True,
        )
        progress = self._complete(quiz)
        dispatch_exercise_completed(
            user=self.user, exercise=quiz, progress=progress
        )
        self.assertFalse(
            UserLessonProgress.objects.filter(user=self.user).exists()
        )

    def test_lesson_not_completed_while_exercises_remain(self):
        Exercise.objects.create(
            chapter=self.chapter, lesson=self.lesson, title="E2",
            instructions="x", solution_query="SELECT 1;", is_published=True, order=2,
        )
        progress = self._complete(self.exercise)
        dispatch_exercise_completed(
            user=self.user, exercise=self.exercise, progress=progress
        )
        lesson_progress = UserLessonProgress.objects.get(
            user=self.user, lesson=self.lesson
        )
        self.assertFalse(lesson_progress.is_completed)


class CheckSandboxBadgesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="u@example.com", password="pw-Complex-1!", first_name="U", last_name="U"
        )

    def test_awards_sandbox_explorer_at_threshold(self):
        for _ in range(20):
            SandboxQueryAttempt.objects.create(
                user=self.user, sql_text="SELECT 1", succeeded=True
            )
        awarded = check_sandbox_badges(self.user)
        triggers = {b["trigger_type"] for b in awarded}
        self.assertIn("sandbox_explorer", triggers)

    def test_no_award_below_threshold(self):
        SandboxQueryAttempt.objects.create(
            user=self.user, sql_text="SELECT 1", succeeded=True
        )
        self.assertEqual(check_sandbox_badges(self.user), [])
