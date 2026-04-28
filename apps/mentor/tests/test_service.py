"""Service-level tests with a mocked Gemini client.

We never call the real SDK in tests — every test replaces the singleton's
``_gemini`` attribute with a stub that records calls and returns canned
responses. This keeps tests deterministic, free, and offline.
"""

from datetime import timedelta
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.curriculum.models import Chapter, Exercise, Lesson
from apps.mentor.exceptions import HintCapReached, RateLimitExceeded
from apps.mentor.gemini_client import GeminiResponse
from apps.mentor.models import (
    AIRequestLog,
    MentorRequestKind,
    MentorRequestOutcome,
)
from apps.mentor.service import AIMentorService

User = get_user_model()


def make_gemini_stub(text="A helpful explanation."):
    """Return a stand-in for ``GeminiClient`` with a counted ``.generate``."""

    stub = MagicMock()
    stub.generate.return_value = GeminiResponse(
        text=text, prompt_tokens=42, response_tokens=17
    )
    return stub


class _BaseFixture(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="learner@example.com",
            password="pw-Complex-1!",
            first_name="Lea",
            last_name="Rner",
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


class ExplainErrorServiceTests(_BaseFixture):
    def test_happy_path_returns_text_and_logs_success(self):
        gemini = make_gemini_stub("Your FORM is a typo of FROM.")
        service = AIMentorService(gemini_client=gemini)

        result = service.explain_error(
            user=self.user,
            exercise=self.exercise,
            user_sql="SELECT * FORM students;",
            error_message='syntax error at "FORM"',
        )

        self.assertTrue(result["available"])
        self.assertIn("FROM", result["message"])
        self.assertEqual(result["prompt_tokens"], 42)

        log = AIRequestLog.objects.get()
        self.assertEqual(log.kind, MentorRequestKind.EXPLAIN_ERROR)
        self.assertEqual(log.outcome, MentorRequestOutcome.SUCCESS)
        self.assertEqual(log.exercise, self.exercise)
        gemini.generate.assert_called_once()

    def test_gemini_error_returns_fallback_and_logs_error(self):
        from apps.mentor.exceptions import GeminiAPIError

        gemini = MagicMock()
        gemini.generate.side_effect = GeminiAPIError("boom")
        service = AIMentorService(gemini_client=gemini)

        result = service.explain_error(
            user=self.user,
            exercise=self.exercise,
            user_sql="SELECT 1;",
            error_message="x",
        )

        self.assertFalse(result["available"])
        self.assertEqual(result["outcome"], MentorRequestOutcome.GEMINI_ERROR.value)
        self.assertEqual(
            AIRequestLog.objects.get().outcome,
            MentorRequestOutcome.GEMINI_ERROR,
        )

    def test_gemini_timeout_returns_fallback(self):
        from apps.mentor.exceptions import GeminiTimeout

        gemini = MagicMock()
        gemini.generate.side_effect = GeminiTimeout("slow")
        service = AIMentorService(gemini_client=gemini)

        result = service.explain_error(
            user=self.user,
            exercise=self.exercise,
            user_sql="SELECT 1;",
            error_message="x",
        )
        self.assertFalse(result["available"])
        self.assertEqual(result["outcome"], MentorRequestOutcome.TIMEOUT.value)


class HintServiceTests(_BaseFixture):
    def test_first_three_hints_progress_levels(self):
        gemini = make_gemini_stub("hint text")
        service = AIMentorService(gemini_client=gemini)

        for expected_level in (1, 2, 3):
            result = service.get_hint(
                user=self.user, exercise=self.exercise, user_sql=""
            )
            self.assertTrue(result["available"])
            self.assertEqual(result["hint_level"], expected_level)
            self.assertEqual(result["hints_remaining"], 3 - expected_level)

        self.assertEqual(
            AIRequestLog.objects.filter(
                kind=MentorRequestKind.HINT,
                outcome=MentorRequestOutcome.SUCCESS,
            ).count(),
            3,
        )

    def test_fourth_hint_blocked_by_cap(self):
        gemini = make_gemini_stub("hint")
        service = AIMentorService(gemini_client=gemini)
        for _ in range(3):
            service.get_hint(user=self.user, exercise=self.exercise, user_sql="")

        with self.assertRaises(HintCapReached):
            service.get_hint(user=self.user, exercise=self.exercise, user_sql="")

        # The blocked attempt is logged with the cap-reached outcome so it
        # shows up in admin analytics.
        self.assertEqual(
            AIRequestLog.objects.filter(
                outcome=MentorRequestOutcome.HINT_CAP_REACHED
            ).count(),
            1,
        )

    def test_hints_for_other_exercise_dont_count_toward_cap(self):
        gemini = make_gemini_stub("hint")
        service = AIMentorService(gemini_client=gemini)
        other = Exercise.objects.create(
            chapter=self.chapter,
            lesson=self.lesson,
            title="Other",
            instructions="x",
            solution_query="SELECT 1;",
            is_published=True,
        )
        for _ in range(3):
            service.get_hint(user=self.user, exercise=other, user_sql="")
        # Original exercise still has all 3 hints available.
        result = service.get_hint(
            user=self.user, exercise=self.exercise, user_sql=""
        )
        self.assertEqual(result["hint_level"], 1)


@override_settings(AI_MENTOR_RATE_LIMIT_PER_HOUR=3)
class RateLimitServiceTests(_BaseFixture):
    def test_blocks_after_cap_and_carries_retry_after(self):
        gemini = make_gemini_stub("ok")
        service = AIMentorService(gemini_client=gemini)

        for _ in range(3):
            service.explain_error(
                user=self.user,
                exercise=self.exercise,
                user_sql="x",
                error_message="y",
            )

        with self.assertRaises(RateLimitExceeded) as cm:
            service.explain_error(
                user=self.user,
                exercise=self.exercise,
                user_sql="x",
                error_message="y",
            )

        self.assertGreater(cm.exception.retry_after_seconds, 0)
        self.assertLessEqual(cm.exception.retry_after_seconds, 60 * 60)
        # Rate-limited attempt is logged but does NOT count toward the window.
        self.assertEqual(
            AIRequestLog.objects.filter(
                outcome=MentorRequestOutcome.RATE_LIMITED
            ).count(),
            1,
        )

    def test_old_logs_outside_window_dont_count(self):
        gemini = make_gemini_stub("ok")
        service = AIMentorService(gemini_client=gemini)

        # Seed 3 successful logs from 2 hours ago — should not block a fresh one.
        old = timezone.now() - timedelta(hours=2)
        for _ in range(3):
            log = AIRequestLog.objects.create(
                user=self.user,
                kind=MentorRequestKind.EXPLAIN_ERROR,
                exercise=self.exercise,
                outcome=MentorRequestOutcome.SUCCESS,
            )
            AIRequestLog.objects.filter(pk=log.pk).update(created_at=old)

        # Should succeed despite 3 historical logs.
        result = service.explain_error(
            user=self.user,
            exercise=self.exercise,
            user_sql="x",
            error_message="y",
        )
        self.assertTrue(result["available"])
