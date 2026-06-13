"""View-level tests for the authentication endpoints.

Covers registration, login, logout, token refresh, the ``me`` endpoint, and
the password-reset flow, including cookie behaviour and account-enumeration
protection. CSRF behaviour lives in ``test_csrf.py``.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import UserRole

User = get_user_model()

PASSWORD = "pw-Complex-1!"
ACCESS = settings.AUTH_COOKIE_ACCESS
REFRESH = settings.AUTH_COOKIE_REFRESH


class RegisterViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("auth-register")

    def _payload(self, **overrides):
        data = {
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
            "password": PASSWORD,
        }
        data.update(overrides)
        return data

    def test_register_success_creates_user_and_sets_cookies(self):
        resp = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.json()["user"]["email"], "new@example.com")
        self.assertEqual(resp.json()["user"]["role"], UserRole.LEARNER)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())
        self.assertIn(ACCESS, resp.cookies)
        self.assertIn(REFRESH, resp.cookies)
        self.assertTrue(resp.cookies[ACCESS]["httponly"])

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(
            email="new@example.com",
            password=PASSWORD,
            first_name="Existing",
            last_name="User",
        )
        resp = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", resp.json())

    def test_register_rejects_weak_password(self):
        resp = self.client.post(
            self.url, self._payload(password="alllowercase"), format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", resp.json())

    def test_register_rejects_short_password(self):
        resp = self.client.post(
            self.url, self._payload(password="Aa1!"), format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", resp.json())

    def test_register_rejects_missing_fields(self):
        resp = self.client.post(self.url, {"email": "x@example.com"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class LoginViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="learner@example.com",
            password=PASSWORD,
            first_name="Lea",
            last_name="Rner",
        )

    def setUp(self):
        self.url = reverse("auth-login")

    def test_login_success_sets_cookies_and_returns_user(self):
        resp = self.client.post(
            self.url,
            {"email": "learner@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["user"]["email"], "learner@example.com")
        self.assertIn(ACCESS, resp.cookies)
        self.assertIn(REFRESH, resp.cookies)

    def test_login_wrong_password_is_rejected(self):
        resp = self.client.post(
            self.url,
            {"email": "learner@example.com", "password": "wrong-Password-1!"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn(ACCESS, resp.cookies)

    def test_login_unknown_email_is_rejected(self):
        resp = self.client.post(
            self.url,
            {"email": "nobody@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_inactive_account_is_rejected(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        resp = self.client.post(
            self.url,
            {"email": "learner@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutViewTests(APITestCase):
    def test_logout_clears_auth_cookies(self):
        resp = self.client.post(reverse("auth-logout"))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        # delete_cookie sets the cookie to an empty value with max-age 0.
        self.assertIn(ACCESS, resp.cookies)
        self.assertIn(REFRESH, resp.cookies)
        self.assertEqual(resp.cookies[ACCESS].value, "")
        self.assertEqual(resp.cookies[REFRESH].value, "")


class RefreshViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="learner@example.com",
            password=PASSWORD,
            first_name="Lea",
            last_name="Rner",
        )

    def setUp(self):
        self.url = reverse("auth-refresh")

    def _login(self):
        self.client.post(
            reverse("auth-login"),
            {"email": "learner@example.com", "password": PASSWORD},
            format="json",
        )

    def test_refresh_issues_new_access_cookie(self):
        self._login()
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn(ACCESS, resp.cookies)

    def test_refresh_without_cookie_is_rejected(self):
        # InvalidToken is an AuthenticationFailed subclass, but the view has no
        # authenticators, so DRF can't build a WWW-Authenticate header and
        # downgrades the 401 to 403.
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_refresh_with_invalid_token_is_rejected(self):
        self.client.cookies[REFRESH] = "not-a-real-token"
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class MeViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="learner@example.com",
            password=PASSWORD,
            first_name="Lea",
            last_name="Rner",
        )

    def test_me_requires_authentication(self):
        resp = self.client.get(reverse("auth-me"))
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_me_returns_current_user(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("auth-me"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["email"], "learner@example.com")


class PasswordResetViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="learner@example.com",
            password=PASSWORD,
            first_name="Lea",
            last_name="Rner",
        )

    def test_existing_email_sends_reset_email(self):
        resp = self.client.post(
            reverse("auth-password-reset"),
            {"email": "learner@example.com"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("learner@example.com", mail.outbox[0].to)

    def test_unknown_email_returns_204_without_sending(self):
        # Account-enumeration protection: always 204, but no email is sent.
        resp = self.client.post(
            reverse("auth-password-reset"),
            {"email": "nobody@example.com"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(mail.outbox), 0)

    def test_inactive_account_receives_no_email(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        resp = self.client.post(
            reverse("auth-password-reset"),
            {"email": "learner@example.com"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_email_format_is_rejected(self):
        resp = self.client.post(
            reverse("auth-password-reset"),
            {"email": "not-an-email"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="learner@example.com",
            password=PASSWORD,
            first_name="Lea",
            last_name="Rner",
        )

    def setUp(self):
        self.url = reverse("auth-password-reset-confirm")
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)

    def test_valid_token_changes_password(self):
        new_password = "brand-New-Pass-2!"
        resp = self.client.post(
            self.url,
            {"uid": self.uid, "token": self.token, "new_password": new_password},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    def test_invalid_uid_is_rejected(self):
        resp = self.client.post(
            self.url,
            {"uid": "bogus", "token": self.token, "new_password": "brand-New-Pass-2!"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("uid", resp.json())

    def test_invalid_token_is_rejected(self):
        resp = self.client.post(
            self.url,
            {"uid": self.uid, "token": "wrong-token", "new_password": "brand-New-Pass-2!"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("token", resp.json())

    def test_weak_new_password_is_rejected(self):
        resp = self.client.post(
            self.url,
            {"uid": self.uid, "token": self.token, "new_password": "weakpass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
