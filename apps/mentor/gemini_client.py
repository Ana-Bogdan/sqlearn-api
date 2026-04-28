"""Thin wrapper around the ``google-genai`` SDK.

Isolated in its own module so the rest of the codebase can mock a single
import in tests (``apps.mentor.gemini_client.GeminiClient.generate``)
without touching the SDK directly. The wrapper:

* Lazily instantiates the ``genai.Client`` (the singleton owns one instance).
* Translates our ``BuiltPrompt`` into Gemini's ``Content``/``Part`` shape,
  mapping our ``ChatRole.ASSISTANT`` to Gemini's ``"model"`` role.
* Enforces the call timeout via ``concurrent.futures``; the SDK doesn't
  expose a per-call deadline universally.
* Returns a small ``GeminiResponse`` value object including token counts
  pulled from ``response.usage_metadata`` so we can persist them on
  ``AIRequestLog``.
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
from dataclasses import dataclass

from django.conf import settings

from .exceptions import GeminiAPIError, GeminiNotConfigured, GeminiTimeout
from .strategies import BuiltPrompt, ChatRole

logger = logging.getLogger(__name__)


# Substrings we treat as transient Gemini errors worth retrying.
# Matches both the SDK's exception messages and the JSON ``status`` field
# the server returns for capacity / quota issues.
_TRANSIENT_ERROR_MARKERS = (
    "503",
    "UNAVAILABLE",
    "RESOURCE_EXHAUSTED",
    "deadline exceeded",
    "DEADLINE_EXCEEDED",
)


def _is_transient(exc: Exception) -> bool:
    msg = str(exc)
    return any(marker in msg for marker in _TRANSIENT_ERROR_MARKERS)


@dataclass(frozen=True)
class GeminiResponse:
    text: str
    prompt_tokens: int
    response_tokens: int


class GeminiClient:
    """Lazy, thread-safe-ish wrapper around the ``google-genai`` client."""

    def __init__(self):
        self._client = None
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="mentor-gemini"
        )

    # -- public API -------------------------------------------------------

    def generate(self, prompt: BuiltPrompt, *, model: str | None = None) -> GeminiResponse:
        """Send the prompt to Gemini and return the response.

        Raises ``GeminiNotConfigured`` if no API key is set,
        ``GeminiTimeout`` if the call exceeds the configured deadline,
        ``GeminiAPIError`` for any other SDK-level failure.
        """

        client = self._ensure_client()
        model_name = model or settings.AI_MENTOR_MODEL
        timeout = settings.AI_MENTOR_TIMEOUT_SECONDS

        future = self._executor.submit(
            self._call_sdk, client, model_name, prompt
        )
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise GeminiTimeout(
                f"Gemini call exceeded {timeout}s deadline"
            ) from exc

    # -- internals --------------------------------------------------------

    def _ensure_client(self):
        if self._client is not None:
            return self._client

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise GeminiNotConfigured("GEMINI_API_KEY is not set")

        # Imported lazily so unit tests that mock generate() don't require
        # google-genai to be installed in the test environment.
        from google import genai  # type: ignore

        self._client = genai.Client(api_key=api_key)
        return self._client

    def _call_sdk(self, client, model_name: str, prompt: BuiltPrompt) -> GeminiResponse:
        from google.genai import types  # type: ignore

        contents = []
        for msg in prompt.history:
            role = "user" if msg.role == ChatRole.USER else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg.content)],
                )
            )
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt.user_message)],
            )
        )

        config = types.GenerateContentConfig(
            system_instruction=prompt.system_instruction,
            temperature=0.3,
            max_output_tokens=600,
        )

        # Retry transient errors (503/UNAVAILABLE/RESOURCE_EXHAUSTED) with
        # exponential-ish backoff. Permanent errors (auth, safety blocks,
        # malformed prompts) bubble up on the first attempt.
        max_attempts = max(1, settings.AI_MENTOR_MAX_RETRIES)
        backoff_schedule = (0.5, 1.5, 3.0, 5.0)

        last_exc: Exception | None = None
        for attempt in range(max_attempts):
            try:
                response = client.models.generate_content(
                    model=model_name, contents=contents, config=config
                )
                break
            except Exception as exc:  # noqa: BLE001 — translate any SDK failure
                last_exc = exc
                if not _is_transient(exc) or attempt == max_attempts - 1:
                    logger.warning("Gemini SDK call failed: %s", exc)
                    raise GeminiAPIError(str(exc)) from exc
                wait = backoff_schedule[min(attempt, len(backoff_schedule) - 1)]
                logger.info(
                    "Gemini transient error (attempt %s/%s), retrying in %ss: %s",
                    attempt + 1,
                    max_attempts,
                    wait,
                    exc,
                )
                time.sleep(wait)
        else:  # pragma: no cover — defensive, the loop always breaks or raises
            raise GeminiAPIError(str(last_exc)) from last_exc

        text = (response.text or "").strip()
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
        response_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)

        if not text:
            raise GeminiAPIError("Gemini returned an empty response")

        return GeminiResponse(
            text=text,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
        )
