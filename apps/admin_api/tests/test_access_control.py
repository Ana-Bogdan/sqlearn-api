"""Access-control tests: every admin endpoint requires the admin role."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import UserRole

User = get_user_model()

PASSWORD = "pw-Complex-1!"


class AdminAccessControlTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = User.objects.create_user(
            email="learner@example.com", password=PASSWORD, first_name="L", last_name="R"
        )
        cls.admin = User.objects.create_user(
            email="admin@example.com", password=PASSWORD, first_name="A", last_name="D",
            role=UserRole.ADMIN,
        )

    def _endpoints(self):
        return [
            reverse("admin_api:chapter-list"),
            reverse("admin_api:lesson-create"),
            reverse("admin_api:exercise-create"),
            reverse("admin_api:dataset-list"),
            reverse("admin_api:badge-list"),
            reverse("admin_api:user-list"),
            reverse("admin_api:stats"),
        ]

    def test_anonymous_is_denied_everywhere(self):
        for url in self._endpoints():
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertIn(
                    resp.status_code,
                    (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
                )

    def test_learner_is_forbidden_everywhere(self):
        self.client.force_authenticate(self.learner)
        for url in self._endpoints():
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_is_allowed(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(reverse("admin_api:chapter-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
