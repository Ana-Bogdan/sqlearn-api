from __future__ import annotations

from typing import Any

from django.db import connections, transaction
from django.db import utils as db_utils

from .exceptions import QueryExecutionError, QuerySyntaxError, QueryTimeout
from .sandbox_service import SANDBOX_DB_ALIAS, user_schema_name


class QueryExecutionService:
    """Runs a single SQL statement inside a user's sandbox schema.

    Each call opens its own transaction on the ``sandbox`` DB alias, sets a
    ``statement_timeout``, locks ``search_path`` to the user schema, and
    translates database errors into the service-level exception types used
    by the validation pipeline.

    Note: Django's ``cursor.execute`` wraps psycopg errors in
    ``django.db.utils.*`` equivalents before they reach our ``except``
    clauses. We inspect the original ``__cause__`` to distinguish syntax
    errors from cancellations from generic execution errors, so the
    pipeline can render the right banner regardless of the wrapping layer.
    """

    db_alias = SANDBOX_DB_ALIAS
    default_timeout_ms = 5000

    def run(
        self,
        user_id,
        sql: str,
        *,
        timeout_ms: int | None = None,
        schema_name: str | None = None,
    ) -> dict[str, Any]:
        from psycopg import errors as pg_errors

        timeout = int(timeout_ms if timeout_ms is not None else self.default_timeout_ms)
        schema = schema_name or user_schema_name(user_id)
        conn = connections[self.db_alias]
        conn.ensure_connection()

        try:
            with transaction.atomic(using=self.db_alias):
                with conn.cursor() as cur:
                    cur.execute(f"SET LOCAL statement_timeout = {timeout}")
                    cur.execute(f'SET LOCAL search_path TO "{schema}"')
                    cur.execute(sql)
                    if cur.description is None:
                        return {
                            "columns": [],
                            "rows": [],
                            "rowcount": cur.rowcount,
                        }
                    columns = [col.name for col in cur.description]
                    rows = [list(row) for row in cur.fetchall()]
                    return {
                        "columns": columns,
                        "rows": rows,
                        "rowcount": cur.rowcount,
                    }
        except db_utils.Error as exc:
            cause = exc.__cause__ if isinstance(exc.__cause__, pg_errors.Error) else None
            if isinstance(cause, pg_errors.QueryCanceled):
                raise QueryTimeout(_clean(str(exc))) from exc
            if isinstance(cause, pg_errors.SyntaxError):
                raise QuerySyntaxError(_clean(str(exc))) from exc
            raise QueryExecutionError(_clean(str(exc))) from exc
        except pg_errors.QueryCanceled as exc:
            raise QueryTimeout(_clean(str(exc))) from exc
        except pg_errors.SyntaxError as exc:
            raise QuerySyntaxError(_clean(str(exc))) from exc
        except pg_errors.Error as exc:
            raise QueryExecutionError(_clean(str(exc))) from exc


def _clean(message: str) -> str:
    # psycopg messages often end with "\nLINE 1: ..." — keep the first line
    # for a clean user-facing error.
    line, _, _ = message.strip().partition("\n")
    return line or message.strip()
