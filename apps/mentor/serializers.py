"""DRF serializers for the AI Mentor endpoints.

Request serializers validate FE input, output serializers shape the
response uniformly across endpoints (always returning a payload that the
FE can render with the same drawer component regardless of mentor kind).
"""

from __future__ import annotations

from rest_framework import serializers

from .strategies import ChatMessage, ChatRole


# ---------------------------------------------------------------------------
# Inbound
# ---------------------------------------------------------------------------


class ChatMessageSerializer(serializers.Serializer):
    """One turn of conversational memory passed in by the FE."""

    role = serializers.ChoiceField(choices=[r.value for r in ChatRole])
    content = serializers.CharField(max_length=4000, allow_blank=False)

    def to_chat_message(self) -> ChatMessage:
        data = self.validated_data
        return ChatMessage(role=ChatRole(data["role"]), content=data["content"])


class _BaseMentorRequestSerializer(serializers.Serializer):
    """Shared fields/behaviour across all mentor request payloads."""

    history = ChatMessageSerializer(many=True, required=False, default=list)

    def history_as_messages(self) -> list[ChatMessage]:
        # ChatMessageSerializer is a per-item nested serializer here, so the
        # already-validated values are plain dicts. Build ChatMessage from
        # them directly rather than re-running .is_valid().
        return [
            ChatMessage(role=ChatRole(item["role"]), content=item["content"])
            for item in self.validated_data.get("history", [])
        ]


class ExplainErrorRequestSerializer(_BaseMentorRequestSerializer):
    exercise_id = serializers.IntegerField()
    sql_text = serializers.CharField(max_length=10_000, allow_blank=False)
    error_message = serializers.CharField(max_length=4_000, allow_blank=False)


class HintRequestSerializer(_BaseMentorRequestSerializer):
    exercise_id = serializers.IntegerField()
    sql_text = serializers.CharField(
        max_length=10_000, allow_blank=True, required=False, default=""
    )


class NLToSQLRequestSerializer(_BaseMentorRequestSerializer):
    natural_language = serializers.CharField(max_length=2_000, allow_blank=False)
    # Optional: when present we use the exercise's dataset; when omitted we
    # use the playground schema (free-sandbox flow).
    exercise_id = serializers.IntegerField(required=False, allow_null=True)


# ---------------------------------------------------------------------------
# Outbound
# ---------------------------------------------------------------------------


class MentorResponseSerializer(serializers.Serializer):
    """Uniform response shape for every mentor endpoint.

    On success: ``available=True`` and ``message`` holds the model output.
    On any failure path (Gemini error, timeout, rate limit, hint cap) the
    server still returns HTTP 200 with ``available=False`` and a fallback
    ``message`` so the FE handles all paths through a single code branch.
    """

    available = serializers.BooleanField()
    message = serializers.CharField()
    # Only set when ``available=True``
    prompt_tokens = serializers.IntegerField(required=False)
    response_tokens = serializers.IntegerField(required=False)
    latency_ms = serializers.IntegerField(required=False)
    # Hint-specific
    hint_level = serializers.IntegerField(required=False)
    hints_remaining = serializers.IntegerField(required=False)
    # Failure-mode metadata (rate_limited / hint_cap_reached / gemini_error / timeout)
    outcome = serializers.CharField(required=False)
    retry_after_seconds = serializers.IntegerField(required=False)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


class AIRequestLogSerializer(serializers.Serializer):
    """Read-only row format for the admin mentor-logs endpoint.

    Consumes plain dicts assembled by the view (rather than ORM instances)
    so we don't have to worry about ``source="exercise.title"`` blowing up
    when a log row's exercise FK is null after a soft-deleted exercise.
    """

    id = serializers.IntegerField()
    user_id = serializers.UUIDField()
    user_email = serializers.EmailField()
    kind = serializers.CharField()
    outcome = serializers.CharField()
    exercise_id = serializers.IntegerField(allow_null=True)
    exercise_title = serializers.CharField(allow_null=True, allow_blank=True)
    prompt_tokens = serializers.IntegerField()
    response_tokens = serializers.IntegerField()
    latency_ms = serializers.IntegerField()
    created_at = serializers.DateTimeField()
