from __future__ import annotations

from typing import Iterable

from django.db import connections, transaction

from apps.sandbox.models import SandboxSchema

SANDBOX_DB_ALIAS = "sandbox"


def user_schema_name(user_id) -> str:
    return f"sandbox_user_{user_id}"


class SandboxService:
    """Manages per-user PostgreSQL schemas that hold exercise datasets.

    The schema is created lazily on first use and reset to its template state
    at the start of every exercise submission so mutations from previous
    attempts never leak between runs.
    """

    db_alias = SANDBOX_DB_ALIAS

    def schema_name(self, user_id) -> str:
        return user_schema_name(user_id)

    def prepare_exercise_schema(
        self, user_id, sandbox_schemas: Iterable[SandboxSchema]
    ) -> str:
        schemas = list(sandbox_schemas)
        name = self.schema_name(user_id)
        conn = connections[self.db_alias]
        conn.ensure_connection()

        with transaction.atomic(using=self.db_alias):
            with conn.cursor() as cur:
                cur.execute(f'DROP SCHEMA IF EXISTS "{name}" CASCADE')
                cur.execute(f'CREATE SCHEMA "{name}"')
                cur.execute(f'SET LOCAL search_path TO "{name}"')
                for schema in schemas:
                    for statement in _split_sql_statements(schema.schema_sql):
                        cur.execute(statement)
        return name

    def drop_user_schema(self, user_id) -> None:
        name = self.schema_name(user_id)
        conn = connections[self.db_alias]
        conn.ensure_connection()
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{name}" CASCADE')


def _split_sql_statements(sql: str) -> list[str]:
    """Split seed SQL on top-level semicolons.

    psycopg3 runs a single statement per ``execute()`` call when parameters
    are bound, and we want the behaviour to be predictable regardless of
    protocol. Seed ``schema_sql`` is admin-authored DDL + INSERTs with no
    semicolons inside literal values, so a naive split is sufficient.
    """
    statements = []
    for chunk in sql.split(";"):
        stripped = chunk.strip()
        if stripped:
            statements.append(stripped)
    return statements
