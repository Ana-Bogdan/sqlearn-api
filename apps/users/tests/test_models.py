"""Unit tests for the custom user model manager."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.users.models import UserRole

User = get_user_model()


class UserManagerTests(TestCase):
    def test_create_user_defaults_to_learner(self):
        user = User.objects.create_user(
            email="learner@example.com",
            password="pw-Complex-1!",
            first_name="Lea",
            last_name="Rner",
        )
        self.assertEqual(user.role, UserRole.LEARNER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("pw-Complex-1!"))

    def test_create_user_normalizes_email(self):
        user = User.objects.create_user(
            email="Learner@EXAMPLE.com",
            password="pw-Complex-1!",
            first_name="Lea",
            last_name="Rner",
        )
        # normalize_email lowercases the domain part.
        self.assertEqual(user.email, "Learner@example.com")

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email="", password="pw-Complex-1!", first_name="A", last_name="B"
            )

    def test_create_superuser_is_admin_staff_superuser(self):
        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="pw-Complex-1!",
            first_name="Ad",
            last_name="Min",
        )
        self.assertEqual(admin.role, UserRole.ADMIN)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_str_is_email(self):
        user = User.objects.create_user(
            email="learner@example.com",
            password="pw-Complex-1!",
            first_name="Lea",
            last_name="Rner",
        )
        self.assertEqual(str(user), "learner@example.com")
