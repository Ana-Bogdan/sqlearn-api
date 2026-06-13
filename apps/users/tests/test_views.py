"""View-level tests for the user self-service endpoints.

The default DRF test client does not enforce CSRF, so ``force_authenticate``
exercises these ``@csrf_protect`` views without a token. The CSRF path itself
is covered in ``apps.authentication.tests.test_csrf``.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

PASSWORD = "pw-Complex-1!"


class MeUpdateViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="learner@example.com",
            password=PASSWORD,
            first_name="Lea",
            last_name="Rner",
        )

    def test_anonymous_is_rejected(self):
        resp = self.client.patch(
            reverse("users-me"), {"first_name": "X"}, format="json"
        )
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_updates_name(self):
        self.client.force_authenticate(self.user)
        resp = self.client.patch(
            reverse("users-me"),
            {"first_name": "Newname", "last_name": "Newlast"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["first_name"], "Newname")
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Newname")

    def test_blank_name_is_rejected(self):
        self.client.force_authenticate(self.user)
        resp = self.client.patch(
            reverse("users-me"), {"first_name": "   "}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("first_name", resp.json())


class ChangePasswordViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="learner@example.com",
            password=PASSWORD,
            first_name="Lea",
            last_name="Rner",
        )

    def setUp(self):
        self.url = reverse("users-me-password")

    def test_anonymous_is_rejected(self):
        resp = self.client.put(
            self.url,
            {"current_password": PASSWORD, "new_password": "another-Pass-1!"},
            format="json",
        )
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_change_password_succeeds_and_rotates_cookies(self):
        self.client.force_authenticate(self.user)
        new_password = "another-Pass-1!"
        resp = self.client.put(
            self.url,
            {"current_password": PASSWORD, "new_password": new_password},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn("access_token", resp.cookies)
        self.assertIn("refresh_token", resp.cookies)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    def test_wrong_current_password_is_rejected(self):
        self.client.force_authenticate(self.user)
        resp = self.client.put(
            self.url,
            {"current_password": "wrong-Pass-1!", "new_password": "another-Pass-1!"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("current_password", resp.json())

    def test_reusing_current_password_is_rejected(self):
        self.client.force_authenticate(self.user)
        resp = self.client.put(
            self.url,
            {"current_password": PASSWORD, "new_password": PASSWORD},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", resp.json())

    def test_weak_new_password_is_rejected(self):
        self.client.force_authenticate(self.user)
        resp = self.client.put(
            self.url,
            {"current_password": PASSWORD, "new_password": "weakpass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", resp.json())
