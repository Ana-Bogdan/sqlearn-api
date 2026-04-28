"""View-level tests for the mentor endpoints with a mocked Gemini client.

We patch ``mentor_service._gemini`` so the same singleton the views import
hits a stub instead of the real SDK.
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.curriculum.models import Chapter, Exercise, Lesson
from apps.mentor.gemini_client import GeminiResponse
from apps.mentor.models import (
    AIRequestLog,
    MentorRequestKind,
    MentorRequestOutcome,
)
from apps.users.models import UserRole

User = get_user_model()


def _gemini_stub(text="Mock answer."):
    stub = MagicMock()
    stub.generate.return_value = GeminiResponse(
        text=text, prompt_tokens=10, response_tokens=5
    )
    return stub


class _BaseFixture(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
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
        cls.chapter = Chapter.objects.create(
            title="Filtering", description="WHERE", order=1
        )
        cls.lesson = Lesson.objects.create(
            chapter=cls.chapter, title="WHERE basics", order=1
        )
        cls.exercise = Exercise.objects.create(
            chapter=cls.chapter,
            lesson=cls.lesson,
            title="Find old students",
            instructions="Return all students older than 20.",
            solution_query="SELECT * FROM students WHERE age > 20;",
            is_published=True,
        )


class ExplainErrorViewTests(_BaseFixture):
    def test_unauthenticated_returns_401_or_403(self):
        url = reverse("mentor-explain-error")
        resp = self.client.post(url, {}, format="json")
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_happy_path(self):
        from apps.mentor.service import mentor_service

        url = reverse("mentor-explain-error")
        self.client.force_authenticate(self.user)

        with patch.object(mentor_service, "_gemini", _gemini_stub("Looks like a typo.")):
            resp = self.client.post(
                url,
                {
                    "exercise_id": self.exercise.id,
                    "sql_text": "SELECT * FORM students;",
                    "error_message": 'syntax error at "FORM"',
                },
                format="json",
            )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertTrue(body["available"])
        self.assertIn("typo", body["message"])

    def test_404_when_exercise_does_not_exist(self):
        from apps.mentor.service import mentor_service

        url = reverse("mentor-explain-error")
        self.client.force_authenticate(self.user)

        with patch.object(mentor_service, "_gemini", _gemini_stub()):
            resp = self.client.post(
                url,
                {
                    "exercise_id": 999_999,
                    "sql_text": "SELECT 1;",
                    "error_message": "x",
                },
                format="json",
            )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class HintViewTests(_BaseFixture):
    def test_first_hint_returns_level_1(self):
        from apps.mentor.service import mentor_service

        url = reverse("mentor-hint")
        self.client.force_authenticate(self.user)

        with patch.object(mentor_service, "_gemini", _gemini_stub("Try filtering.")):
            resp = self.client.post(
                url,
                {"exercise_id": self.exercise.id, "sql_text": "SELECT 1;"},
                format="json",
            )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertTrue(body["available"])
        self.assertEqual(body["hint_level"], 1)
        self.assertEqual(body["hints_remaining"], 2)

    def test_fourth_hint_returns_cap_fallback(self):
        from apps.mentor.service import mentor_service

        url = reverse("mentor-hint")
        self.client.force_authenticate(self.user)

        with patch.object(mentor_service, "_gemini", _gemini_stub("hint")):
            for _ in range(3):
                self.client.post(
                    url,
                    {"exercise_id": self.exercise.id, "sql_text": ""},
                    format="json",
                )

            resp = self.client.post(
                url,
                {"exercise_id": self.exercise.id, "sql_text": ""},
                format="json",
            )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertFalse(body["available"])
        self.assertEqual(body["outcome"], MentorRequestOutcome.HINT_CAP_REACHED.value)
        self.assertEqual(body["hints_remaining"], 0)


class NLToSQLViewTests(_BaseFixture):
    def test_without_exercise_uses_playground(self):
        from apps.mentor.service import mentor_service

        url = reverse("mentor-nl-to-sql")
        self.client.force_authenticate(self.user)

        with patch.object(mentor_service, "_gemini", _gemini_stub("```sql\nSELECT 1;\n```")):
            resp = self.client.post(
                url,
                {"natural_language": "give me anything"},
                format="json",
            )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertTrue(body["available"])


class AdminMentorLogsViewTests(_BaseFixture):
    def test_non_admin_forbidden(self):
        url = reverse("admin-mentor-logs")
        self.client.force_authenticate(self.user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_and_filter(self):
        AIRequestLog.objects.create(
            user=self.user,
            kind=MentorRequestKind.HINT,
            exercise=self.exercise,
            outcome=MentorRequestOutcome.SUCCESS,
            prompt_tokens=10,
            response_tokens=5,
            latency_ms=120,
        )
        AIRequestLog.objects.create(
            user=self.user,
            kind=MentorRequestKind.EXPLAIN_ERROR,
            exercise=self.exercise,
            outcome=MentorRequestOutcome.GEMINI_ERROR,
            latency_ms=80,
        )

        url = reverse("admin-mentor-logs")
        self.client.force_authenticate(self.admin)

        # No filter: both rows
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["count"], 2)

        # Filter by kind
        resp = self.client.get(url, {"kind": "hint"})
        self.assertEqual(resp.json()["count"], 1)
        self.assertEqual(resp.json()["results"][0]["kind"], "hint")

        # Filter by outcome
        resp = self.client.get(url, {"outcome": "gemini_error"})
        self.assertEqual(resp.json()["count"], 1)
