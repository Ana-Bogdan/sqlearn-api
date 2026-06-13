"""Unit tests for the IsAdmin permission."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.authentication.permissions import IsAdmin
from apps.users.models import UserRole

User = get_user_model()


class IsAdminPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = User.objects.create_user(
            email="learner@example.com",
            password="pw-Complex-1!",
            first_name="Lea",
            last_name="Rner",
        )
        cls.admin = User.objects.create_user(
            email="admin@example.com",
            password="pw-Complex-1!",
            first_name="Ad",
            last_name="Min",
            role=UserRole.ADMIN,
        )

    def setUp(self):
        self.permission = IsAdmin()
        self.factory = APIRequestFactory()

    def _request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_admin_is_allowed(self):
        self.assertTrue(self.permission.has_permission(self._request(self.admin), None))

    def test_learner_is_denied(self):
        self.assertFalse(
            self.permission.has_permission(self._request(self.learner), None)
        )

    def test_anonymous_is_denied(self):
        self.assertFalse(
            self.permission.has_permission(self._request(AnonymousUser()), None)
        )
