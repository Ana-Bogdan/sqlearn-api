"""Unit tests for the password ComplexityValidator."""

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.authentication.validators import ComplexityValidator


class ComplexityValidatorTests(SimpleTestCase):
    def setUp(self):
        self.validator = ComplexityValidator()

    def test_accepts_a_complex_password(self):
        # Should not raise.
        self.validator.validate("pw-Complex-1!")

    def test_rejects_too_short(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("Aa1!")
        self.assertIn("at least 8 characters", str(ctx.exception))

    def test_rejects_missing_uppercase(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("lower-case-1!")
        self.assertIn("an uppercase letter", str(ctx.exception))

    def test_rejects_missing_lowercase(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("UPPER-CASE-1!")
        self.assertIn("a lowercase letter", str(ctx.exception))

    def test_rejects_missing_digit(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("NoDigits-here!")
        self.assertIn("a number", str(ctx.exception))

    def test_rejects_missing_symbol(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("NoSymbols1234")
        self.assertIn("a symbol", str(ctx.exception))

    def test_error_uses_complexity_code(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("weak")
        self.assertEqual(ctx.exception.code, "password_complexity")

    def test_get_help_text_mentions_requirements(self):
        text = self.validator.get_help_text()
        self.assertIn("8 characters", text)
        self.assertIn("uppercase", text)
        self.assertIn("symbol", text)
