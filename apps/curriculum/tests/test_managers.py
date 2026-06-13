"""Unit tests for the curriculum querysets/managers."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from apps.curriculum.models import Chapter, Exercise, Lesson
from apps.progress.models import (
    ExerciseStatus,
    UserExerciseProgress,
    UserLessonProgress,
)

User = get_user_model()


class ChapterManagerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="u@example.com", password="pw-Complex-1!", first_name="U", last_name="U"
        )
        cls.active = Chapter.objects.create(title="Active", order=1)
        cls.inactive = Chapter.objects.create(title="Inactive", order=2, is_active=False)
        cls.lesson = Lesson.objects.create(chapter=cls.active, title="L", order=1)
        cls.ex1 = Exercise.objects.create(
            chapter=cls.active, lesson=cls.lesson, title="E1",
            instructions="x", solution_query="SELECT 1;", is_published=True,
        )
        cls.ex2 = Exercise.objects.create(
            chapter=cls.active, lesson=cls.lesson, title="E2",
            instructions="x", solution_query="SELECT 1;", is_published=True,
        )

    def test_active_excludes_inactive(self):
        titles = list(Chapter.objects.active().values_list("title", flat=True))
        self.assertIn("Active", titles)
        self.assertNotIn("Inactive", titles)

    def test_with_user_progress_anonymous_has_zero_completion(self):
        chapter = (
            Chapter.objects.active()
            .with_user_progress(AnonymousUser())
            .get(pk=self.active.pk)
        )
        self.assertEqual(chapter.total_exercises, 2)
        self.assertEqual(chapter.completed_exercises, 0)
        self.assertEqual(chapter.completion_percent, 0.0)

    def test_with_user_progress_counts_completed(self):
        UserExerciseProgress.objects.create(
            user=self.user, exercise=self.ex1, status=ExerciseStatus.COMPLETED
        )
        chapter = (
            Chapter.objects.active()
            .with_user_progress(self.user)
            .get(pk=self.active.pk)
        )
        self.assertEqual(chapter.total_exercises, 2)
        self.assertEqual(chapter.completed_exercises, 1)
        self.assertEqual(chapter.completion_percent, 50.0)


class LessonManagerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="u@example.com", password="pw-Complex-1!", first_name="U", last_name="U"
        )
        cls.chapter = Chapter.objects.create(title="C", order=1)
        cls.lesson = Lesson.objects.create(chapter=cls.chapter, title="L1", order=1)
        cls.other_lesson = Lesson.objects.create(chapter=cls.chapter, title="L2", order=2)
        cls.ex = Exercise.objects.create(
            chapter=cls.chapter, lesson=cls.lesson, title="E",
            instructions="x", solution_query="SELECT 1;", is_published=True,
        )

    def test_for_chapter_returns_ordered_active_lessons(self):
        lessons = list(Lesson.objects.for_chapter(self.chapter.id))
        self.assertEqual([l.title for l in lessons], ["L1", "L2"])

    def test_with_user_progress_is_completed_flag(self):
        UserLessonProgress.objects.create(
            user=self.user, lesson=self.lesson, is_completed=True
        )
        lesson = (
            Lesson.objects.with_user_progress(self.user).get(pk=self.lesson.pk)
        )
        self.assertTrue(lesson.is_completed)
        self.assertEqual(lesson.total_exercises, 1)

    def test_with_user_progress_anonymous_not_completed(self):
        lesson = (
            Lesson.objects.with_user_progress(AnonymousUser()).get(pk=self.lesson.pk)
        )
        self.assertFalse(lesson.is_completed)


class ExerciseManagerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="u@example.com", password="pw-Complex-1!", first_name="U", last_name="U"
        )
        cls.chapter = Chapter.objects.create(title="C", order=1)
        cls.lesson = Lesson.objects.create(chapter=cls.chapter, title="L", order=1)
        cls.published = Exercise.objects.create(
            chapter=cls.chapter, lesson=cls.lesson, title="Published",
            instructions="x", solution_query="SELECT 1;", is_published=True, order=1,
        )
        cls.draft = Exercise.objects.create(
            chapter=cls.chapter, lesson=cls.lesson, title="Draft",
            instructions="x", solution_query="SELECT 1;", is_published=False, order=2,
        )
        cls.quiz = Exercise.objects.create(
            chapter=cls.chapter, title="Quiz",
            instructions="x", solution_query="SELECT 1;", is_published=True,
            is_chapter_quiz=True, order=3,
        )

    def test_visible_filters_to_active_published(self):
        titles = list(Exercise.objects.visible().values_list("title", flat=True))
        self.assertIn("Published", titles)
        self.assertNotIn("Draft", titles)

    def test_for_lesson_excludes_quizzes_and_drafts(self):
        titles = list(
            Exercise.objects.for_lesson(self.lesson.id).values_list("title", flat=True)
        )
        self.assertEqual(titles, ["Published"])

    def test_for_chapter_quiz_only_by_default(self):
        titles = list(
            Exercise.objects.for_chapter(self.chapter.id).values_list("title", flat=True)
        )
        self.assertEqual(titles, ["Quiz"])

    def test_for_chapter_can_include_lesson_exercises(self):
        titles = set(
            Exercise.objects.for_chapter(
                self.chapter.id, include_lesson_exercises=True
            ).values_list("title", flat=True)
        )
        self.assertEqual(titles, {"Published", "Quiz"})

    def test_with_user_status_defaults_to_not_started(self):
        ex = Exercise.objects.with_user_status(self.user).get(pk=self.published.pk)
        self.assertEqual(ex.user_status, ExerciseStatus.NOT_STARTED)

    def test_with_user_status_reflects_progress(self):
        UserExerciseProgress.objects.create(
            user=self.user, exercise=self.published, status=ExerciseStatus.COMPLETED
        )
        ex = Exercise.objects.with_user_status(self.user).get(pk=self.published.pk)
        self.assertEqual(ex.user_status, ExerciseStatus.COMPLETED)

    def test_with_user_status_anonymous(self):
        ex = Exercise.objects.with_user_status(AnonymousUser()).get(pk=self.published.pk)
        self.assertEqual(ex.user_status, ExerciseStatus.NOT_STARTED)
