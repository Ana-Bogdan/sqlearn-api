"""Strategy base — defines the contract every prompt strategy implements."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class ChatMessage:
    """One turn in a conversation, in chronological order."""

    role: ChatRole
    content: str


@dataclass(frozen=True)
class BuiltPrompt:
    """The output of ``PromptStrategy.build()``.

    ``system_instruction`` is sent as Gemini's system prompt. ``history`` is
    prior conversation turns (oldest first), and ``user_message`` is the
    latest user turn the model should respond to.
    """

    system_instruction: str
    history: list[ChatMessage]
    user_message: str


# Shared persona the model adopts for every mentor request. Centralizing it
# here keeps tone consistent across strategies — and makes it a one-line
# change if we want to A/B-test a different voice later.
TUTOR_PERSONA = (
    "You are SQLearn's AI Mentor: a patient, concise SQL tutor for absolute "
    "beginners working through a guided curriculum on PostgreSQL. "
    "Always respond in English. Keep answers short (under 120 words unless "
    "code is involved). Use Markdown for formatting and put SQL in fenced "
    "```sql``` code blocks. Address the learner directly in the second "
    "person. Never insult or talk down to the learner."
)


class PromptStrategy(ABC):
    """Abstract base for the Strategy pattern.

    Subclasses are constructed with the context they need (an exercise, a
    SQL query, a natural-language question, etc.) and produce a
    fully-formed ``BuiltPrompt`` via :py:meth:`build`.
    """

    @abstractmethod
    def build(self) -> BuiltPrompt:
        """Return the system instruction, history, and final user message."""

    # -- helpers shared by concrete strategies ----------------------------

    @staticmethod
    def _format_history(history: list[ChatMessage] | None) -> list[ChatMessage]:
        """Defensive copy + filter so strategies can't mutate caller state."""

        if not history:
            return []
        return [m for m in history if m.content.strip()]
