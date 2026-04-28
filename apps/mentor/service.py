"""AI Mentor service — Singleton entry point for all mentor requests.

Design pattern: **Singleton**. Exactly one ``AIMentorService`` instance
lives at module scope (``mentor_service`` below). Because Python imports a
module only once per process, importing ``mentor_service`` from anywhere
in the codebase always returns the same object — no metaclass tricks, no
``__new__`` overrides. The instance owns a single ``GeminiClient`` (which
in turn lazily owns the ``genai.Client`` connection).

Responsibilities:

* Pick the right prompt :class:`Strategy` for the request kind.
* Enforce rate limiting (``AI_MENTOR_RATE_LIMIT_PER_HOUR``) and the
  per-exercise hint cap (``AI_MENTOR_HINTS_PER_EXERCISE``) by querying
  ``AIRequestLog``.
* Call Gemini, translate failures into a structured fallback response.
* Persist a row to ``AIRequestLog`` for every attempt — successful, rate-
  limited, or errored — so the admin endpoint and the rate-limit query
  see the same source of truth.
"""

from __future__ import annotations

import logging
import time
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .exceptions import (
    GeminiAPIError,
    GeminiNotConfigured,
    GeminiTimeout,
    HintCapReached,
    RateLimitExceeded,
)
from .gemini_client import GeminiClient, GeminiResponse
from .models import AIRequestLog, MentorRequestKind, MentorRequestOutcome
from .schema_inspector import schema_for_exercise, schema_for_playground
from .strategies import (
    BuiltPrompt,
    ChatMessage,
    ExplainErrorContext,
    ExplainErrorStrategy,
    HintContext,
    HintStrategy,
    NLToSQLContext,
    NLToSQLStrategy,
    PromptStrategy,
)

logger = logging.getLogger(__name__)


class AIMentorService:
    """Coordinates strategy selection, throttling, and Gemini calls."""

    def __init__(self, gemini_client: GeminiClient | None = None):
        # Allow tests to inject a fake client. Production callers don't
        # pass anything — the module-level ``mentor_service`` constructs
        # its own once.
        self._gemini = gemini_client or GeminiClient()

    # =====================================================================
    # Public API — one method per request kind
    # =====================================================================

    def explain_error(
        self,
        *,
        user,
        exercise,
        user_sql: str,
        error_message: str,
        history: list[ChatMessage] | None = None,
    ) -> dict:
        self._enforce_rate_limit(user, MentorRequestKind.EXPLAIN_ERROR)

        strategy = ExplainErrorStrategy(
            ExplainErrorContext(
                exercise_title=exercise.title,
                exercise_instructions=exercise.instructions,
                user_sql=user_sql,
                error_message=error_message,
                history=history or [],
            )
        )
        return self._run(
            user=user,
            kind=MentorRequestKind.EXPLAIN_ERROR,
            exercise=exercise,
            strategy=strategy,
        )

    def get_hint(
        self,
        *,
        user,
        exercise,
        user_sql: str,
        history: list[ChatMessage] | None = None,
    ) -> dict:
        self._enforce_rate_limit(user, MentorRequestKind.HINT)
        used = self._count_hints_used(user, exercise)
        cap = settings.AI_MENTOR_HINTS_PER_EXERCISE
        if used >= cap:
            self._log(
                user=user,
                kind=MentorRequestKind.HINT,
                exercise=exercise,
                outcome=MentorRequestOutcome.HINT_CAP_REACHED,
            )
            raise HintCapReached(
                f"Already used {used}/{cap} AI hints for this exercise."
            )

        next_level = used + 1  # 1, 2, or 3
        strategy = HintStrategy(
            HintContext(
                exercise_title=exercise.title,
                exercise_instructions=exercise.instructions,
                schema_description=schema_for_exercise(exercise),
                user_sql=user_sql,
                hint_level=next_level,
                history=history or [],
            )
        )
        result = self._run(
            user=user,
            kind=MentorRequestKind.HINT,
            exercise=exercise,
            strategy=strategy,
        )
        # Decorate the response with hint-progression info so the FE can
        # render "Hint 2/3" and disable the button after the third.
        result["hint_level"] = next_level
        result["hints_remaining"] = max(0, cap - next_level)
        return result

    def nl_to_sql(
        self,
        *,
        user,
        natural_language: str,
        exercise=None,
        history: list[ChatMessage] | None = None,
    ) -> dict:
        self._enforce_rate_limit(user, MentorRequestKind.NL_TO_SQL)

        # In a lesson context the FE may pass the current exercise so we
        # use that exercise's dataset; in the free Sandbox there's no
        # exercise and we fall back to the playground schema.
        schema_description = (
            schema_for_exercise(exercise) if exercise else schema_for_playground()
        )

        strategy = NLToSQLStrategy(
            NLToSQLContext(
                natural_language=natural_language,
                schema_description=schema_description,
                history=history or [],
            )
        )
        return self._run(
            user=user,
            kind=MentorRequestKind.NL_TO_SQL,
            exercise=exercise,
            strategy=strategy,
        )

    # =====================================================================
    # Internals
    # =====================================================================

    def _run(
        self,
        *,
        user,
        kind: MentorRequestKind,
        exercise,
        strategy: PromptStrategy,
    ) -> dict:
        """Build the prompt, call Gemini, persist the log, return a dict.

        Catches every Gemini-side failure and converts it into a uniform
        fallback response so the view layer never has to handle SDK errors.
        """

        prompt: BuiltPrompt = strategy.build()
        started = time.monotonic()
        try:
            response: GeminiResponse = self._gemini.generate(prompt)
        except GeminiTimeout:
            return self._fallback(
                user=user,
                kind=kind,
                exercise=exercise,
                outcome=MentorRequestOutcome.TIMEOUT,
                latency_ms=self._elapsed_ms(started),
            )
        except (GeminiAPIError, GeminiNotConfigured) as exc:
            logger.warning("Gemini unavailable for %s: %s", kind, exc)
            return self._fallback(
                user=user,
                kind=kind,
                exercise=exercise,
                outcome=MentorRequestOutcome.GEMINI_ERROR,
                latency_ms=self._elapsed_ms(started),
            )

        latency_ms = self._elapsed_ms(started)
        self._log(
            user=user,
            kind=kind,
            exercise=exercise,
            outcome=MentorRequestOutcome.SUCCESS,
            prompt_tokens=response.prompt_tokens,
            response_tokens=response.response_tokens,
            latency_ms=latency_ms,
        )
        return {
            "available": True,
            "message": response.text,
            "prompt_tokens": response.prompt_tokens,
            "response_tokens": response.response_tokens,
            "latency_ms": latency_ms,
        }

    # -- throttling -------------------------------------------------------

    def _enforce_rate_limit(self, user, kind: MentorRequestKind) -> None:
        cap = settings.AI_MENTOR_RATE_LIMIT_PER_HOUR
        window_start = timezone.now() - timedelta(hours=1)
        used = AIRequestLog.objects.filter(
            user=user,
            created_at__gte=window_start,
            outcome=MentorRequestOutcome.SUCCESS,
        ).count()
        if used < cap:
            return

        # Best-effort retry-after = seconds until the oldest request in
        # the window falls out of it.
        oldest = (
            AIRequestLog.objects.filter(
                user=user,
                created_at__gte=window_start,
                outcome=MentorRequestOutcome.SUCCESS,
            )
            .order_by("created_at")
            .values_list("created_at", flat=True)
            .first()
        )
        retry_after = 60 * 60  # 1h default
        if oldest is not None:
            delta = (oldest + timedelta(hours=1)) - timezone.now()
            retry_after = max(1, int(delta.total_seconds()))
        # Log the rate-limited attempt so it shows up in admin analytics.
        # It does NOT count toward the next window because we filter by
        # outcome=SUCCESS above.
        self._log(
            user=user,
            kind=kind,
            exercise=None,
            outcome=MentorRequestOutcome.RATE_LIMITED,
        )
        raise RateLimitExceeded(retry_after)

    def _count_hints_used(self, user, exercise) -> int:
        return AIRequestLog.objects.filter(
            user=user,
            exercise=exercise,
            kind=MentorRequestKind.HINT,
            outcome=MentorRequestOutcome.SUCCESS,
        ).count()

    # -- logging + fallback ----------------------------------------------

    def _log(
        self,
        *,
        user,
        kind: MentorRequestKind,
        exercise,
        outcome: MentorRequestOutcome,
        prompt_tokens: int = 0,
        response_tokens: int = 0,
        latency_ms: int = 0,
    ) -> AIRequestLog:
        return AIRequestLog.objects.create(
            user=user,
            kind=kind,
            exercise=exercise,
            outcome=outcome,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
            latency_ms=latency_ms,
        )

    def _fallback(
        self,
        *,
        user,
        kind: MentorRequestKind,
        exercise,
        outcome: MentorRequestOutcome,
        latency_ms: int,
    ) -> dict:
        self._log(
            user=user,
            kind=kind,
            exercise=exercise,
            outcome=outcome,
            latency_ms=latency_ms,
        )
        return {
            "available": False,
            "message": settings.AI_MENTOR_FALLBACK_MESSAGE,
            "outcome": outcome.value,
        }

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return int((time.monotonic() - started) * 1000)


# =========================================================================
# Module-level singleton — Pythonic Singleton pattern.
# Importing ``mentor_service`` from any module in the codebase yields the
# same instance because Python only initialises a module's globals once.
# =========================================================================
mentor_service = AIMentorService()
