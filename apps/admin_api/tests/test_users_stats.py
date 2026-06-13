"""Admin user-management and dashboard-stats tests."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.curriculum.models import Chapter, Exercise, Lesson
from apps.progress.models import (
    ExerciseStatus,
    QuerySubmission,
    UserExerciseProgress,
)
from apps.users.models import UserRole

User = get_user_model()

PASSWORD = "pw-Complex-1!"


class AdminUserListTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            email="admin@example.com", password=PASSWORD, first_name="A", last_name="D",
            role=UserRole.ADMIN,
        )
        cls.alice = User.objects.create_user(
            email="alice@example.com", password=PASSWORD, first_name="Alice", last_name="A"
        )
        cls.bob = User.objects.create_user(
            email="bob@example.com", password=PASSWORD, first_name="Bob", last_name="B",
            is_active=False,
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_list_is_paginated(self):
        resp = self.client.get(reverse("admin_api:user-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("results", resp.json())
        self.assertIn("count", resp.json())

    def test_search_by_email(self):
        resp = self.client.get(reverse("admin_api:user-list"), {"search": "alice"})
        emails = [u["email"] for u in resp.json()["results"]]
        self.assertEqual(emails, ["alice@example.com"])

    def test_filter_by_is_active(self):
        resp = self.client.get(reverse("admin_api:user-list"), {"is_active": "false"})
        emails = [u["email"] for u in resp.json()["results"]]
        self.assertEqual(emails, ["bob@example.com"])

    def test_filter_by_role(self):
        resp = self.client.get(reverse("admin_api:user-list"), {"role": UserRole.ADMIN})
        emails = [u["email"] for u in resp.json()["results"]]
        self.assertEqual(emails, ["admin@example.com"])


class AdminUserDetailTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            email="admin@example.com", password=PASSWORD, first_name="A", last_name="D",
            role=UserRole.ADMIN,
        )
        cls.learner = User.objects.create_user(
            email="learner@example.com", password=PASSWORD, first_name="L", last_name="R"
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_deactivate_user(self):
        resp = self.client.patch(
            reverse("admin_api:user-detail", args=[self.learner.id]),
            {"is_active": False}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.learner.refresh_from_db()
        self.assertFalse(self.learner.is_active)

    def test_email_and_role_are_read_only(self):
        resp = self.client.patch(
            reverse("admin_api:user-detail", args=[self.learner.id]),
            {"email": "new@example.com", "role": UserRole.ADMIN}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.learner.refresh_from_db()
        self.assertEqual(self.learner.email, "learner@example.com")
        self.assertEqual(self.learner.role, UserRole.LEARNER)


class AdminStatsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            email="admin@example.com", password=PASSWORD, first_name="A", last_name="D",
            role=UserRole.ADMIN,
        )
        cls.learner = User.objects.create_user(
            email="learner@example.com", password=PASSWORD, first_name="L", last_name="R",
            last_activity_date=timezone.now().date(),
        )
        cls.chapter = Chapter.objects.create(title="C", order=1)
        cls.lesson = Lesson.objects.create(chapter=cls.chapter, title="L", order=1)
        cls.exercise = Exercise.objects.create(
            chapter=cls.chapter, lesson=cls.lesson, title="E",
            instructions="x", solution_query="SELECT 1;", is_published=True,
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_stats_payload_shape(self):
        UserExerciseProgress.objects.create(
            user=self.learner, exercise=self.exercise, status=ExerciseStatus.COMPLETED
        )
        resp = self.client.get(reverse("admin_api:stats"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertEqual(body["total_users"], 2)
        self.assertEqual(body["active_today"], 1)
        self.assertIn("avg_exercises_per_user", body)
        self.assertIn("highest_fail_rate_exercises", body)
        self.assertIn("most_attempted_exercises", body)

    def test_fail_rate_ranking_counts_submissions(self):
        QuerySubmission.objects.create(
            user=self.learner, exercise=self.exercise, sql_text="x", was_correct=False
        )
        QuerySubmission.objects.create(
            user=self.learner, exercise=self.exercise, sql_text="y", was_correct=True
        )
        resp = self.client.get(reverse("admin_api:stats"))
        ranked = resp.json()["most_attempted_exercises"]
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["attempts"], 2)
        self.assertEqual(ranked[0]["failures"], 1)
        self.assertEqual(ranked[0]["fail_rate"], 0.5)
