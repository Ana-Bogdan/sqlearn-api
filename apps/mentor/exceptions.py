"""Custom exceptions raised inside the AI Mentor module.

These are caught by the service and translated into structured fallback
responses; they should never bubble up to DRF's exception handler.
"""

from __future__ import annotations


class MentorError(Exception):
    """Base class for all mentor-internal exceptions."""


class GeminiNotConfigured(MentorError):
    """Raised when GEMINI_API_KEY is missing or empty."""


class GeminiTimeout(MentorError):
    """Raised when a Gemini call exceeds AI_MENTOR_TIMEOUT_SECONDS."""


class GeminiAPIError(MentorError):
    """Raised when the Gemini SDK returns an error response."""


class RateLimitExceeded(MentorError):
    """Raised when the per-user hourly request cap is reached."""

    def __init__(self, retry_after_seconds: int):
        super().__init__(
            f"Rate limit exceeded; retry in {retry_after_seconds}s"
        )
        self.retry_after_seconds = retry_after_seconds


class HintCapReached(MentorError):
    """Raised when the per-exercise AI hint cap is reached."""
