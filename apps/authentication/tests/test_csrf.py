"""Tests for CSRF protection and cookie-based auth transport.

These use a real login (not ``force_authenticate``) so the cookie JWT path —
and the CSRF enforcement baked into ``CookieJWTAuthentication`` and the
``@csrf_protect`` decorators — actually runs. ``enforce_csrf_checks=True`` is
required because DRF's test client disables CSRF enforcement by default.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()

PASSWORD = "pw-Complex-1!"


class CSRFCookieTests(APITestCase):
    def test_csrf_endpoint_sets_csrftoken_cookie(self):
        resp = self.client.get(reverse("auth-csrf"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("csrftoken", resp.cookies)


class CSRFEnforcementTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="learner@example.com",
            password=PASSWORD,
            first_name="Lea",
            last_name="Rner",
        )

    def setUp(self):
        # A client that actually enforces CSRF, mirroring the browser.
        self.client = APIClient(enforce_csrf_checks=True)
        # Real login populates the httpOnly access cookie; login itself has
        # no authentication classes, so it needs no CSRF token.
        self.client.post(
            reverse("auth-login"),
            {"email": "learner@example.com", "password": PASSWORD},
            format="json",
        )

    def test_unsafe_request_without_csrf_token_is_forbidden(self):
        resp = self.client.patch(
            reverse("users-me"), {"first_name": "Changed"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unsafe_request_with_csrf_token_succeeds(self):
        self.client.get(reverse("auth-csrf"))
        token = self.client.cookies["csrftoken"].value
        resp = self.client.patch(
            reverse("users-me"),
            {"first_name": "Changed"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["first_name"], "Changed")

    def test_logout_is_csrf_protected(self):
        resp = self.client.post(reverse("auth-logout"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_safe_request_needs_no_csrf_token(self):
        resp = self.client.get(reverse("auth-me"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["email"], "learner@example.com")
