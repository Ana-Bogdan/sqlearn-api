"""Mentor models.

``AIRequestLog`` is an append-only record of every call made to the AI Mentor.
It serves three purposes:

1. **Rate limiting** — count rows per user within the last hour to enforce
   ``AI_MENTOR_RATE_LIMIT_PER_HOUR``.
2. **Hint cap** — count ``hint`` rows per user+exercise to enforce
   ``AI_MENTOR_HINTS_PER_EXERCISE``.
3. **Analytics** — for the thesis demo, query "which exercises trigger the
   most help requests?" or "what fraction of requests fall back?".

We never store the prompt or response body to keep the table cheap and avoid
leaking learner SQL into long-term storage. Token counts come from the
Gemini response metadata when available.
"""

from django.conf import settings
from django.db import models


class MentorRequestKind(models.TextChoices):
    EXPLAIN_ERROR = "explain_error", "Explain Error"
    HINT = "hint", "Hint"
    NL_TO_SQL = "nl_to_sql", "Natural Language to SQL"


class MentorRequestOutcome(models.TextChoices):
    SUCCESS = "success", "Success"
    RATE_LIMITED = "rate_limited", "Rate Limited"
    HINT_CAP_REACHED = "hint_cap_reached", "Hint Cap Reached"
    GEMINI_ERROR = "gemini_error", "Gemini Error"
    TIMEOUT = "timeout", "Timeout"
    INVALID_INPUT = "invalid_input", "Invalid Input"


class AIRequestLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mentor_requests",
    )
    kind = models.CharField(
        max_length=32, choices=MentorRequestKind.choices, db_index=True
    )
    exercise = models.ForeignKey(
        "curriculum.Exercise",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mentor_requests",
    )
    outcome = models.CharField(
        max_length=32,
        choices=MentorRequestOutcome.choices,
        default=MentorRequestOutcome.SUCCESS,
        db_index=True,
    )
    prompt_tokens = models.PositiveIntegerField(default=0)
    response_tokens = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_request_logs"
        ordering = ("-created_at",)
        indexes = [
            # Rate-limit query: WHERE user_id=? AND created_at > now()-1h
            models.Index(
                fields=("user", "created_at"), name="mentor_log_user_time_idx"
            ),
            # Hint-cap query: WHERE user_id=? AND exercise_id=? AND kind='hint'
            models.Index(
                fields=("user", "exercise", "kind"),
                name="mentor_log_user_ex_kind_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} {self.kind} {self.outcome} @ {self.created_at:%Y-%m-%d %H:%M}"
