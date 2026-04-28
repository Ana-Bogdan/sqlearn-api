"""Strategy for the *Explain Error* request.

Triggered when a learner's submission failed (PostgreSQL syntax error,
runtime error, wrong-result diff). The model receives the exercise context,
the learner's SQL, and the error/diff message, and must explain *why* the
query failed in pedagogical terms — without writing the corrected query.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import BuiltPrompt, ChatMessage, PromptStrategy, TUTOR_PERSONA


@dataclass(frozen=True)
class ExplainErrorContext:
    exercise_title: str
    exercise_instructions: str
    user_sql: str
    error_message: str
    history: list[ChatMessage] = field(default_factory=list)


class ExplainErrorStrategy(PromptStrategy):
    """Build a prompt that asks the model to explain a query failure."""

    def __init__(self, context: ExplainErrorContext):
        self._ctx = context

    def build(self) -> BuiltPrompt:
        system = (
            f"{TUTOR_PERSONA}\n\n"
            "Task: Explain a PostgreSQL error a learner got while attempting a "
            "SQL exercise. Identify the *concept* they likely misunderstood, "
            "not just the literal error text. Do NOT write the corrected SQL "
            "— guide them toward fixing it themselves. Reference specific "
            "tokens from their query when helpful."
        )

        ctx = self._ctx
        user_message = (
            f"## Exercise\n"
            f"**{ctx.exercise_title}**\n\n"
            f"{ctx.exercise_instructions}\n\n"
            f"## My query\n"
            f"```sql\n{ctx.user_sql.strip()}\n```\n\n"
            f"## What PostgreSQL said\n"
            f"```\n{ctx.error_message.strip()}\n```\n\n"
            f"What went wrong, and what should I revisit?"
        )

        return BuiltPrompt(
            system_instruction=system,
            history=self._format_history(ctx.history),
            user_message=user_message,
        )
