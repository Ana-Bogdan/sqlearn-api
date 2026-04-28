"""Strategy for the *Progressive Hint* request.

Each exercise allows up to ``AI_MENTOR_HINTS_PER_EXERCISE`` AI hints
(default 3). Hint #1 is a gentle conceptual nudge; #2 names the specific
clauses or functions to consider; #3 is almost-but-not-quite the solution
structure. The hint *level* is passed in by the service based on how many
hint logs already exist for this user+exercise.

We never reveal the canonical solution query, even at level 3.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import BuiltPrompt, ChatMessage, PromptStrategy, TUTOR_PERSONA


# Per-level guidance the model adopts. Keeping this as a constant (rather
# than inline f-strings) makes it easy to tune levels independently during
# thesis evaluation.
LEVEL_GUIDANCE = {
    1: (
        "This is hint LEVEL 1 of 3 (gentlest). Nudge the learner toward the "
        "right SQL *concept* (e.g. 'think about how to filter rows'). "
        "Do not name specific keywords yet. One short paragraph, no code."
    ),
    2: (
        "This is hint LEVEL 2 of 3 (more specific). Name the SQL clauses or "
        "functions they should use (e.g. 'use WHERE with the LIKE operator'). "
        "Don't write a working query — describe the structure in prose. "
        "One short paragraph plus optional 1-2 line skeleton with placeholders."
    ),
    3: (
        "This is hint LEVEL 3 of 3 (most specific). Sketch the query "
        "structure with placeholder values, e.g. "
        "'SELECT <columns> FROM students WHERE age > <number> ORDER BY ...'. "
        "Use placeholders the learner must fill in — never the final solution."
    ),
}


@dataclass(frozen=True)
class HintContext:
    exercise_title: str
    exercise_instructions: str
    schema_description: str
    user_sql: str
    hint_level: int  # 1, 2, or 3
    history: list[ChatMessage] = field(default_factory=list)

    def __post_init__(self):
        if self.hint_level not in (1, 2, 3):
            raise ValueError(
                f"hint_level must be 1, 2, or 3, got {self.hint_level!r}"
            )


class HintStrategy(PromptStrategy):
    """Build a progressive-hint prompt at the requested level."""

    def __init__(self, context: HintContext):
        self._ctx = context

    def build(self) -> BuiltPrompt:
        ctx = self._ctx

        system = (
            f"{TUTOR_PERSONA}\n\n"
            f"Task: Give a hint for the SQL exercise below. "
            f"{LEVEL_GUIDANCE[ctx.hint_level]} "
            "NEVER write the full correct query — that defeats the purpose."
        )

        attempt_block = (
            f"## My current attempt\n```sql\n{ctx.user_sql.strip()}\n```\n\n"
            if ctx.user_sql.strip()
            else "## My current attempt\n_(I haven't written anything yet.)_\n\n"
        )

        user_message = (
            f"## Exercise\n"
            f"**{ctx.exercise_title}**\n\n"
            f"{ctx.exercise_instructions}\n\n"
            f"## Schema available\n"
            f"```\n{ctx.schema_description.strip()}\n```\n\n"
            f"{attempt_block}"
            f"Please give me a level-{ctx.hint_level} hint."
        )

        return BuiltPrompt(
            system_instruction=system,
            history=self._format_history(ctx.history),
            user_message=user_message,
        )
