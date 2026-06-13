"""Tests for the leaderboard endpoint, focused on admin exclusion.

Admin accounts must neither appear in the ranked list nor count toward any
learner's rank.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import UserRole

User = get_user_model()


class LeaderboardAdminExclusionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Admin with the highest XP — should be invisible and not counted.
        cls.admin = User.objects.create_user(
            email="admin@example.com",
            password="pw-Complex-1!",
            first_name="Ad",
            last_name="Min",
            role=UserRole.ADMIN,
            xp=1000,
        )
        cls.top_learner = User.objects.create_user(
            email="top@example.com",
            password="pw-Complex-1!",
            first_name="Top",
            last_name="Learner",
            xp=500,
        )
        cls.second_learner = User.objects.create_user(
            email="second@example.com",
            password="pw-Complex-1!",
            first_name="Second",
            last_name="Learner",
            xp=100,
        )

    def test_admin_not_listed_in_results(self):
        self.client.force_authenticate(self.top_learner)
        resp = self.client.get(reverse("leaderboard"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        ids = [entry["id"] for entry in resp.data["results"]]
        self.assertNotIn(str(self.admin.id), [str(i) for i in ids])
        self.assertEqual(len(resp.data["results"]), 2)

    def test_admin_does_not_count_toward_learner_rank(self):
        # Despite the admin having the highest XP, the top learner is rank 1.
        self.client.force_authenticate(self.top_learner)
        resp = self.client.get(reverse("leaderboard"))

        ranks = {
            str(entry["id"]): entry["rank"] for entry in resp.data["results"]
        }
        self.assertEqual(ranks[str(self.top_learner.id)], 1)
        self.assertEqual(ranks[str(self.second_learner.id)], 2)
        self.assertEqual(resp.data["current_user"]["rank"], 1)
