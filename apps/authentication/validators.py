import re

from django.core.exceptions import ValidationError


class ComplexityValidator:
    MIN_LENGTH = 8
    UPPER_RE = re.compile(r"[A-Z]")
    LOWER_RE = re.compile(r"[a-z]")
    DIGIT_RE = re.compile(r"[0-9]")
    SYMBOL_RE = re.compile(r"[^A-Za-z0-9\s]")

    def validate(self, password, user=None):
        errors = []
        if len(password) < self.MIN_LENGTH:
            errors.append(f"at least {self.MIN_LENGTH} characters")
        if not self.UPPER_RE.search(password):
            errors.append("an uppercase letter")
        if not self.LOWER_RE.search(password):
            errors.append("a lowercase letter")
        if not self.DIGIT_RE.search(password):
            errors.append("a number")
        if not self.SYMBOL_RE.search(password):
            errors.append("a symbol")
        if errors:
            raise ValidationError(
                "Password must include " + ", ".join(errors) + ".",
                code="password_complexity",
            )

    def get_help_text(self):
        return (
            f"Your password must be at least {self.MIN_LENGTH} characters and "
            "include an uppercase letter, a lowercase letter, a number, and a symbol."
        )
