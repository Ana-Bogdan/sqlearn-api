"""Tests for the retry logic in ``GeminiClient._call_sdk``.

We don't have ``google-genai`` installed in the test environment, so we
patch the client object directly with a stand-in whose
``models.generate_content`` raises configured exceptions. This is the same
shape the real SDK exposes, just stubbed.
"""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.mentor.exceptions import GeminiAPIError
from apps.mentor.gemini_client import GeminiClient, _is_transient
from apps.mentor.strategies import BuiltPrompt


def _stub_response(text="ok"):
    """Mimics google-genai's response object with a usage_metadata field."""

    resp = MagicMock()
    resp.text = text
    resp.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)
    return resp


def _stub_models_with_side_effect(side_effect):
    """Build a stand-in for ``client.models`` whose generate_content does X."""

    models = MagicMock()
    models.generate_content.side_effect = side_effect
    return models


class IsTransientTests(SimpleTestCase):
    def test_503_strings_are_transient(self):
        self.assertTrue(_is_transient(Exception("503 UNAVAILABLE")))
        self.assertTrue(_is_transient(Exception("RESOURCE_EXHAUSTED quota")))
        self.assertTrue(_is_transient(Exception("DEADLINE_EXCEEDED")))

    def test_other_errors_are_not_transient(self):
        self.assertFalse(_is_transient(Exception("invalid api key")))
        self.assertFalse(_is_transient(Exception("safety filter triggered")))
        self.assertFalse(_is_transient(Exception("400 bad request")))


@override_settings(AI_MENTOR_MAX_RETRIES=3, AI_MENTOR_TIMEOUT_SECONDS=30)
class CallSDKRetryTests(SimpleTestCase):
    def setUp(self):
        self.prompt = BuiltPrompt(
            system_instruction="sys", history=[], user_message="hi"
        )

    @patch("apps.mentor.gemini_client.time.sleep")  # don't actually sleep
    def test_retries_on_503_then_succeeds(self, _sleep):
        client = GeminiClient()
        fake_genai_client = MagicMock()
        fake_genai_client.models = _stub_models_with_side_effect(
            [Exception("503 UNAVAILABLE"), Exception("503 UNAVAILABLE"), _stub_response("eventually ok")]
        )

        with patch.object(client, "_ensure_client", return_value=fake_genai_client), \
             patch("apps.mentor.gemini_client.types", create=True) as types_stub:
            types_stub.Content = MagicMock()
            types_stub.Part.from_text = MagicMock()
            types_stub.GenerateContentConfig = MagicMock()
            response = client._call_sdk(fake_genai_client, "model-x", self.prompt)

        self.assertEqual(response.text, "eventually ok")
        self.assertEqual(fake_genai_client.models.generate_content.call_count, 3)

    @patch("apps.mentor.gemini_client.time.sleep")
    def test_non_transient_error_raises_immediately(self, sleep):
        client = GeminiClient()
        fake_genai_client = MagicMock()
        fake_genai_client.models = _stub_models_with_side_effect(
            [Exception("invalid api key"), _stub_response("never reached")]
        )

        with patch.object(client, "_ensure_client", return_value=fake_genai_client), \
             patch("apps.mentor.gemini_client.types", create=True) as types_stub:
            types_stub.Content = MagicMock()
            types_stub.Part.from_text = MagicMock()
            types_stub.GenerateContentConfig = MagicMock()
            with self.assertRaises(GeminiAPIError):
                client._call_sdk(fake_genai_client, "model-x", self.prompt)

        self.assertEqual(fake_genai_client.models.generate_content.call_count, 1)
        sleep.assert_not_called()

    @patch("apps.mentor.gemini_client.time.sleep")
    def test_gives_up_after_max_retries(self, sleep):
        client = GeminiClient()
        fake_genai_client = MagicMock()
        fake_genai_client.models = _stub_models_with_side_effect(
            [Exception("503 UNAVAILABLE")] * 5
        )

        with patch.object(client, "_ensure_client", return_value=fake_genai_client), \
             patch("apps.mentor.gemini_client.types", create=True) as types_stub:
            types_stub.Content = MagicMock()
            types_stub.Part.from_text = MagicMock()
            types_stub.GenerateContentConfig = MagicMock()
            with self.assertRaises(GeminiAPIError):
                client._call_sdk(fake_genai_client, "model-x", self.prompt)

        # Tries exactly AI_MENTOR_MAX_RETRIES times, then raises.
        self.assertEqual(fake_genai_client.models.generate_content.call_count, 3)
        self.assertEqual(sleep.call_count, 2)  # backoff between attempts 1→2 and 2→3
