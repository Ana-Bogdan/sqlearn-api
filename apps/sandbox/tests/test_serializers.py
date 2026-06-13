"""Unit tests for the sandbox request serializers."""

from django.test import SimpleTestCase

from apps.sandbox.serializers import SandboxExecuteSerializer, SubmitQuerySerializer


class SubmitQuerySerializerTests(SimpleTestCase):
    def test_valid_sql_is_trimmed(self):
        serializer = SubmitQuerySerializer(data={"sql_text": "  SELECT 1;  "})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["sql_text"], "SELECT 1;")

    def test_blank_is_rejected(self):
        serializer = SubmitQuerySerializer(data={"sql_text": ""})
        self.assertFalse(serializer.is_valid())

    def test_whitespace_only_is_rejected(self):
        serializer = SubmitQuerySerializer(data={"sql_text": "   "})
        self.assertFalse(serializer.is_valid())


class SandboxExecuteSerializerTests(SimpleTestCase):
    def test_valid_sql_is_trimmed(self):
        serializer = SandboxExecuteSerializer(data={"sql_text": "  SELECT 1;  "})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["sql_text"], "SELECT 1;")

    def test_blank_is_rejected(self):
        serializer = SandboxExecuteSerializer(data={"sql_text": "   "})
        self.assertFalse(serializer.is_valid())
