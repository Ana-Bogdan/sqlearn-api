from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .comparator import compare_results
from .exceptions import QueryExecutionError, QuerySyntaxError, QueryTimeout
from .execution_service import QueryExecutionService


# ---------------------------------------------------------------------------
# Context passed between handlers
# ---------------------------------------------------------------------------


@dataclass
class SubmissionContext:
    user: Any
    exercise: Any
    sql: str
    result: dict[str, Any] | None = None
    is_correct: bool = False
    outcome: dict[str, Any] | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Chain of Responsibility base
# ---------------------------------------------------------------------------


class Handler(ABC):
    def __init__(self) -> None:
        self._next: Handler | None = None

    def set_next(self, handler: "Handler") -> "Handler":
        self._next = handler
        return handler

    def handle(self, ctx: SubmissionContext) -> dict[str, Any] | None:
        outcome = self.process(ctx)
        if outcome is not None:
            ctx.outcome = outcome
            return outcome
        if self._next is not None:
            return self._next.handle(ctx)
        return None

    @abstractmethod
    def process(self, ctx: SubmissionContext) -> dict[str, Any] | None:
        ...


# ---------------------------------------------------------------------------
# Concrete handlers
# ---------------------------------------------------------------------------

_COMMENT_LINE = re.compile(r"--[^\n]*", re.MULTILINE)
_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)
_DDL_PATTERN = re.compile(
    r"\b(CREATE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|VACUUM|REINDEX|CLUSTER)\b",
    re.IGNORECASE,
)
_WRITE_PATTERN = re.compile(r"\b(INSERT|UPDATE|DELETE|MERGE|COPY)\b", re.IGNORECASE)

WRITE_ALLOWED_FROM_CHAPTER = 7


def _strip_sql_comments(sql: str) -> str:
    sql = _COMMENT_BLOCK.sub(" ", sql)
    sql = _COMMENT_LINE.sub(" ", sql)
    return sql


class ForbiddenOperationHandler(Handler):
    """Rejects SQL that the current chapter is not permitted to run.

    DDL is blocked in every chapter; non-SELECT (INSERT/UPDATE/DELETE/MERGE/
    COPY) is blocked for chapters 1-6 and allowed from chapter 7 onwards.
    """

    def process(self, ctx: SubmissionContext) -> dict[str, Any] | None:
        stripped = _strip_sql_comments(ctx.sql)
        chapter_order = getattr(ctx.exercise.chapter, "order", 1)

        if _DDL_PATTERN.search(stripped):
            return {
                "status": "forbidden",
                "message": (
                    "Schema-changing statements (CREATE, DROP, ALTER, TRUNCATE, "
                    "GRANT, REVOKE) are not allowed in exercises."
                ),
            }

        if chapter_order < WRITE_ALLOWED_FROM_CHAPTER and _WRITE_PATTERN.search(stripped):
            return {
                "status": "forbidden",
                "message": "Only SELECT queries are allowed in this chapter.",
            }

        return None


class SyntaxCheckHandler(Handler):
    """Uses ``EXPLAIN`` to surface PostgreSQL syntax errors with a friendly message.

    EXPLAIN parses and plans the query without executing it, so we can catch
    syntax mistakes cheaply. Other errors (unknown table, unknown column,
    type mismatch) are deferred to the execution handler so the user sees the
    real PostgreSQL diagnostic message.
    """

    def __init__(self, execution_service: QueryExecutionService) -> None:
        super().__init__()
        self._execution = execution_service

    def process(self, ctx: SubmissionContext) -> dict[str, Any] | None:
        plan_sql = f"EXPLAIN {ctx.sql.rstrip().rstrip(';')}"
        try:
            self._execution.run(ctx.user.id, plan_sql)
        except QuerySyntaxError as exc:
            return {
                "status": "syntax_error",
                "message": f"Syntax error: {exc}",
            }
        except (QueryTimeout, QueryExecutionError):
            # Defer other error types to the execution handler so the user
            # sees the real runtime error message rather than a plan-time one.
            return None
        return None


class ExecutionHandler(Handler):
    """Executes the user's query inside their sandbox schema."""

    def __init__(self, execution_service: QueryExecutionService) -> None:
        super().__init__()
        self._execution = execution_service

    def process(self, ctx: SubmissionContext) -> dict[str, Any] | None:
        try:
            ctx.result = self._execution.run(ctx.user.id, ctx.sql)
        except QueryTimeout:
            return {
                "status": "timeout",
                "message": (
                    "Your query took longer than 5 seconds to run. Try narrowing "
                    "it down or adding a filter."
                ),
            }
        except QuerySyntaxError as exc:
            return {"status": "syntax_error", "message": f"Syntax error: {exc}"}
        except QueryExecutionError as exc:
            return {"status": "execution_error", "message": str(exc)}
        return None


class ResultComparisonHandler(Handler):
    """Compares the execution result with the exercise's expected result."""

    def process(self, ctx: SubmissionContext) -> dict[str, Any] | None:
        expected = ctx.exercise.expected_result or {}
        actual = ctx.result or {"columns": [], "rows": []}

        correct, reason = compare_results(expected, actual)
        if correct:
            ctx.is_correct = True
            return {
                "status": "correct",
                "message": "Correct! Your query returned the expected result.",
                "result": actual,
            }

        message_map = {
            "columns_mismatch": (
                "The columns returned don't match the expected columns. Check "
                "the column names and their order."
            ),
            "row_count_mismatch": (
                "The number of rows returned doesn't match the expected result."
            ),
            "rows_mismatch": (
                "The query ran, but the rows don't match the expected result."
            ),
        }
        return {
            "status": "incorrect",
            "reason": reason,
            "message": message_map.get(
                reason or "",
                "The query ran, but the result doesn't match what was expected.",
            ),
            "result": actual,
            "expected": expected,
        }


# ---------------------------------------------------------------------------
# Pipeline wiring
# ---------------------------------------------------------------------------


class QueryValidationPipeline:
    """Wires the handlers into the Chain of Responsibility:

    ForbiddenOperation → SyntaxCheck → Execution → ResultComparison

    Each handler either short-circuits the chain by returning an outcome, or
    passes control to the next handler.
    """

    def __init__(self, execution_service: QueryExecutionService | None = None) -> None:
        self._execution = execution_service or QueryExecutionService()
        self._head = ForbiddenOperationHandler()
        syntax = SyntaxCheckHandler(self._execution)
        execution = ExecutionHandler(self._execution)
        comparison = ResultComparisonHandler()
        self._head.set_next(syntax).set_next(execution).set_next(comparison)

    def run(self, context: SubmissionContext) -> dict[str, Any]:
        outcome = self._head.handle(context)
        if outcome is None:
            # Defensive: the final handler always produces an outcome.
            outcome = {
                "status": "execution_error",
                "message": "The query produced no outcome.",
            }
            context.outcome = outcome
        return outcome
