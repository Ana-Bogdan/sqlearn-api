"""View-level tests for the learner-facing curriculum endpoints."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.curriculum.models import Chapter, Exercise, ExerciseHint, Lesson
from apps.progress.models import (
    ExerciseStatus,
    UserExerciseProgress,
    UserLessonProgress,
)

User = get_user_model()

PASSWORD = "pw-Complex-1!"


class _CurriculumFixture(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="learner@example.com",
            password=PASSWORD,
            first_name="Lea",
            last_name="Rner",
        )
        cls.chapter = Chapter.objects.create(
            title="Filtering", description="WHERE", order=1
        )
        cls.inactive_chapter = Chapter.objects.create(
            title="Hidden", order=2, is_active=False
        )
        cls.lesson = Lesson.objects.create(
            chapter=cls.chapter, title="WHERE basics", order=1, theory_content="Theory"
        )
        cls.lesson_two = Lesson.objects.create(
            chapter=cls.chapter, title="WHERE more", order=2
        )
        cls.exercise = Exercise.objects.create(
            chapter=cls.chapter,
            lesson=cls.lesson,
            title="Find old students",
            instructions="Return all students older than 20.",
            solution_query="SELECT * FROM students WHERE age > 20;",
            is_published=True,
            order=1,
        )
        cls.exercise_two = Exercise.objects.create(
            chapter=cls.chapter,
            lesson=cls.lesson,
            title="Second",
            instructions="x",
            solution_query="SELECT 1;",
            is_published=True,
            order=2,
        )
        cls.unpublished = Exercise.objects.create(
            chapter=cls.chapter,
            lesson=cls.lesson,
            title="Draft",
            instructions="x",
            solution_query="SELECT 1;",
            is_published=False,
            order=3,
        )
        cls.hint = ExerciseHint.objects.create(
            exercise=cls.exercise, hint_text="Use WHERE", order=1
        )
        ExerciseHint.objects.create(
            exercise=cls.exercise, hint_text="Compare age", order=2
        )


class ChapterListViewTests(_CurriculumFixture):
    def test_requires_authentication(self):
        resp = self.client.get(reverse("chapter-list"))
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_lists_only_active_chapters_with_progress(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("chapter-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        titles = [c["title"] for c in resp.json()]
        self.assertIn("Filtering", titles)
        self.assertNotIn("Hidden", titles)
        chapter_row = resp.json()[0]
        self.assertEqual(chapter_row["total_exercises"], 2)
        self.assertEqual(chapter_row["completed_exercises"], 0)

    def test_completion_percent_reflects_progress(self):
        UserExerciseProgress.objects.create(
            user=self.user,
            exercise=self.exercise,
            status=ExerciseStatus.COMPLETED,
        )
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("chapter-list"))
        chapter_row = resp.json()[0]
        self.assertEqual(chapter_row["completed_exercises"], 1)
        self.assertEqual(chapter_row["completion_percent"], 50.0)


class ChapterDetailViewTests(_CurriculumFixture):
    def test_returns_lessons_and_quizzes(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("chapter-detail", args=[self.chapter.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertIn("lessons", body)
        self.assertIn("chapter_quizzes", body)
        self.assertEqual(len(body["lessons"]), 2)

    def test_first_lesson_unlocked_rest_locked(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("chapter-detail", args=[self.chapter.id]))
        lessons = resp.json()["lessons"]
        self.assertFalse(lessons[0]["is_locked"])
        self.assertTrue(lessons[1]["is_locked"])

    def test_inactive_chapter_returns_404(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(
            reverse("chapter-detail", args=[self.inactive_chapter.id])
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class LessonDetailViewTests(_CurriculumFixture):
    def test_returns_theory_and_published_exercises(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("lesson-detail", args=[self.lesson.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertEqual(body["theory_content"], "Theory")
        # Only the two published, non-quiz exercises are listed.
        self.assertEqual(len(body["exercises"]), 2)

    def test_anonymous_is_rejected(self):
        resp = self.client.get(reverse("lesson-detail", args=[self.lesson.id]))
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )


class ExerciseDetailViewTests(_CurriculumFixture):
    def test_returns_exercise_with_status_and_hint_count(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("exercise-detail", args=[self.exercise.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertEqual(body["user_status"], ExerciseStatus.NOT_STARTED)
        self.assertEqual(body["hint_count"], 2)
        # solution_query must never leak to learners.
        self.assertNotIn("solution_query", body)

    def test_reflects_user_status(self):
        UserExerciseProgress.objects.create(
            user=self.user,
            exercise=self.exercise,
            status=ExerciseStatus.ATTEMPTED,
        )
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("exercise-detail", args=[self.exercise.id]))
        self.assertEqual(resp.json()["user_status"], ExerciseStatus.ATTEMPTED)

    def test_unpublished_exercise_returns_404(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("exercise-detail", args=[self.unpublished.id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class ExerciseHintsViewTests(_CurriculumFixture):
    def test_returns_hints_in_order(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("exercise-hints", args=[self.exercise.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        hints = resp.json()
        self.assertEqual([h["order"] for h in hints], [1, 2])
        self.assertEqual(hints[0]["hint_text"], "Use WHERE")

    def test_hints_for_unpublished_exercise_404(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("exercise-hints", args=[self.unpublished.id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_is_rejected(self):
        resp = self.client.get(reverse("exercise-hints", args=[self.exercise.id]))
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
