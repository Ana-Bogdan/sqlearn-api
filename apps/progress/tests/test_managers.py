"""Unit tests for the progress manager/queryset."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from apps.curriculum.models import Chapter, Exercise, Lesson
from apps.progress.models import ExerciseStatus, UserExerciseProgress

User = get_user_model()


class UserProgressManagerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="u@example.com", password="pw-Complex-1!", first_name="U", last_name="U"
        )
        cls.other = User.objects.create_user(
            email="o@example.com", password="pw-Complex-1!", first_name="O", last_name="O"
        )
        cls.chapter = Chapter.objects.create(title="C", order=1)
        cls.lesson = Lesson.objects.create(chapter=cls.chapter, title="L", order=1)
        cls.exercise = Exercise.objects.create(
            chapter=cls.chapter, lesson=cls.lesson, title="E",
            instructions="x", solution_query="SELECT 1;", is_published=True,
        )

    def test_get_completion_status_anonymous(self):
        self.assertEqual(
            UserExerciseProgress.objects.get_completion_status(
                AnonymousUser(), self.exercise
            ),
            ExerciseStatus.NOT_STARTED,
        )

    def test_get_completion_status_no_row(self):
        self.assertEqual(
            UserExerciseProgress.objects.get_completion_status(self.user, self.exercise),
            ExerciseStatus.NOT_STARTED,
        )

    def test_get_completion_status_with_row(self):
        UserExerciseProgress.objects.create(
            user=self.user, exercise=self.exercise, status=ExerciseStatus.COMPLETED
        )
        self.assertEqual(
            UserExerciseProgress.objects.get_completion_status(self.user, self.exercise),
            ExerciseStatus.COMPLETED,
        )

    def test_for_user_scopes_to_one_user(self):
        UserExerciseProgress.objects.create(
            user=self.user, exercise=self.exercise, status=ExerciseStatus.ATTEMPTED
        )
        UserExerciseProgress.objects.create(
            user=self.other, exercise=self.exercise, status=ExerciseStatus.COMPLETED
        )
        rows = UserExerciseProgress.objects.for_user(self.user)
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().user, self.user)

    def test_completed_filters_by_status(self):
        UserExerciseProgress.objects.create(
            user=self.user, exercise=self.exercise, status=ExerciseStatus.COMPLETED
        )
        UserExerciseProgress.objects.create(
            user=self.other, exercise=self.exercise, status=ExerciseStatus.ATTEMPTED
        )
        self.assertEqual(UserExerciseProgress.objects.completed().count(), 1)
