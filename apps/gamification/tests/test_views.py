"""View-level tests for the gamification endpoints (excl. leaderboard)."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.curriculum.models import Chapter, Exercise, Lesson
from apps.gamification.badges import award_badge
from apps.progress.models import ExerciseStatus, UserExerciseProgress

User = get_user_model()

PASSWORD = "pw-Complex-1!"


class BadgesListViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="u@example.com", password=PASSWORD, first_name="U", last_name="U"
        )

    def test_requires_authentication(self):
        resp = self.client.get(reverse("badges-list"))
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_lists_all_badges_with_earned_status(self):
        award_badge(self.user, "first_query")
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("badges-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertGreater(len(body), 1)
        by_trigger = {b["trigger_type"]: b for b in body}
        self.assertTrue(by_trigger["first_query"]["earned"])
        self.assertIsNotNone(by_trigger["first_query"]["awarded_at"])
        self.assertFalse(by_trigger["streak_30"]["earned"])


class MyProgressViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="u@example.com", password=PASSWORD, first_name="U", last_name="U",
            xp=120, level=2,
        )
        cls.chapter = Chapter.objects.create(title="C", order=1)
        cls.lesson = Lesson.objects.create(chapter=cls.chapter, title="L", order=1)
        cls.ex = Exercise.objects.create(
            chapter=cls.chapter, lesson=cls.lesson, title="E",
            instructions="x", solution_query="SELECT 1;", is_published=True,
        )

    def test_returns_aggregate_dashboard(self):
        UserExerciseProgress.objects.create(
            user=self.user, exercise=self.ex, status=ExerciseStatus.COMPLETED
        )
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("my-progress"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertEqual(body["xp"], 120)
        self.assertEqual(body["level"], 2)
        self.assertEqual(body["level_title"], "Data Rookie")
        self.assertEqual(body["total_exercises"], 1)
        self.assertEqual(body["completed_exercises"], 1)
        self.assertEqual(body["total_chapters"], 1)
        self.assertEqual(body["completed_chapters"], 1)

    def test_requires_authentication(self):
        resp = self.client.get(reverse("my-progress"))
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )


class PublicProfileViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="u@example.com", password=PASSWORD, first_name="Vis", last_name="Ible",
            xp=350, level=3,
        )
        cls.viewer = User.objects.create_user(
            email="v@example.com", password=PASSWORD, first_name="V", last_name="Iewer"
        )
        cls.inactive = User.objects.create_user(
            email="x@example.com", password=PASSWORD, first_name="In", last_name="Active",
            is_active=False,
        )

    def test_returns_public_stats(self):
        award_badge(self.user, "first_query")
        self.client.force_authenticate(self.viewer)
        resp = self.client.get(reverse("public-profile", args=[self.user.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertEqual(body["first_name"], "Vis")
        self.assertEqual(body["level"], 3)
        self.assertEqual(body["level_title"], "Filter Finder")
        self.assertEqual(body["badges_earned"], 1)
        self.assertEqual(len(body["badges"]), 1)

    def test_inactive_user_is_404(self):
        self.client.force_authenticate(self.viewer)
        resp = self.client.get(reverse("public-profile", args=[self.inactive.id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_requires_authentication(self):
        resp = self.client.get(reverse("public-profile", args=[self.user.id]))
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
