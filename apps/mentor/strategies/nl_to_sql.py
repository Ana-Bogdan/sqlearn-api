"""Strategy for the *Natural Language to SQL* request.

Used in the free Sandbox (and possibly in lessons) when the learner types a
question in English and wants the model to generate the corresponding
PostgreSQL query against a sandbox schema. The model returns the SQL plus a
short explanation so the learner understands what they're about to run.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import BuiltPrompt, ChatMessage, PromptStrategy, TUTOR_PERSONA


@dataclass(frozen=True)
class NLToSQLContext:
    natural_language: str
    schema_description: str
    history: list[ChatMessage] = field(default_factory=list)


class NLToSQLStrategy(PromptStrategy):
    """Build a prompt that asks the model to translate English to SQL."""

    def __init__(self, context: NLToSQLContext):
        self._ctx = context

    def build(self) -> BuiltPrompt:
        ctx = self._ctx

        system = (
            f"{TUTOR_PERSONA}\n\n"
            "Task: Translate the learner's natural-language request into a "
            "single PostgreSQL query that runs against the schema provided. "
            "Output exactly two sections, in this order:\n"
            "1. A fenced ```sql``` code block with the query (and ONLY the "
            "query, no comments inside the block).\n"
            "2. A 'Why' section: 1-2 sentences plain-English explanation of "
            "what the query does.\n"
            "Use only tables and columns that appear in the schema. If the "
            "request is ambiguous, pick the most reasonable interpretation "
            "and call out the assumption in the 'Why' section."
        )

        user_message = (
            f"## Schema\n"
            f"```\n{ctx.schema_description.strip()}\n```\n\n"
            f"## Request\n"
            f"{ctx.natural_language.strip()}"
        )

        return BuiltPrompt(
            system_instruction=system,
            history=self._format_history(ctx.history),
            user_message=user_message,
        )
