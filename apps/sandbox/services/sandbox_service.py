from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.db import connections, transaction

from apps.sandbox.models import SandboxSchema

SANDBOX_DB_ALIAS = "sandbox"


def user_schema_name(user_id) -> str:
    return f"sandbox_user_{user_id}"


def playground_schema_name(user_id) -> str:
    return f"sandbox_playground_{user_id}"


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool


@dataclass(frozen=True)
class TableInfo:
    name: str
    row_count: int
    columns: list[ColumnInfo]


class SandboxService:
    """Manages per-user PostgreSQL schemas that hold sandbox datasets.

    Two flavours of schema live under the ``sandbox`` DB alias:

    * The exercise schema (``sandbox_user_{id}``) — reset to the exercise
      template at the start of every submission so prior mutations cannot
      leak across attempts.
    * The playground schema (``sandbox_playground_{id}``) — created lazily
      on first sandbox visit, reset only when the learner clicks Reset.
      Held separately from the exercise schema so an active lesson and a
      free-play session don't trample each other's state.
    """

    db_alias = SANDBOX_DB_ALIAS

    def schema_name(self, user_id) -> str:
        return user_schema_name(user_id)

    def playground_schema_name(self, user_id) -> str:
        return playground_schema_name(user_id)

    # -- exercise (per-submission) schema -------------------------------

    def prepare_exercise_schema(
        self, user_id, sandbox_schemas: Iterable[SandboxSchema]
    ) -> str:
        return self._reset_schema(self.schema_name(user_id), sandbox_schemas)

    # -- playground schema ----------------------------------------------

    def get_or_create_playground(self, user_id) -> tuple[str, SandboxSchema]:
        """Return ``(schema_name, playground_template)`` for this user.

        The schema is created on first call and left intact on subsequent
        ones so the learner's playground state survives page reloads.
        """

        template = self._playground_template()
        name = self.playground_schema_name(user_id)
        if not self._schema_exists(name):
            self._reset_schema(name, [template])
        return name, template

    def reset_playground(self, user_id) -> tuple[str, SandboxSchema]:
        template = self._playground_template()
        name = self.playground_schema_name(user_id)
        self._reset_schema(name, [template])
        return name, template

    def introspect_playground(self, user_id) -> list[TableInfo]:
        """Return the live table/column shape of the user's playground.

        Reads from ``information_schema`` so the browser reflects the
        actual state — including any rows the learner has inserted —
        rather than a frozen snapshot of the seed SQL.
        """

        name, _ = self.get_or_create_playground(user_id)
        conn = connections[self.db_alias]
        conn.ensure_connection()

        tables: dict[str, list[ColumnInfo]] = {}
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = %s
                ORDER BY table_name, ordinal_position
                """,
                [name],
            )
            for table_name, column_name, data_type, is_nullable in cur.fetchall():
                tables.setdefault(table_name, []).append(
                    ColumnInfo(
                        name=column_name,
                        data_type=data_type,
                        is_nullable=(is_nullable == "YES"),
                    )
                )

            row_counts: dict[str, int] = {}
            for table_name in tables:
                cur.execute(f'SELECT COUNT(*) FROM "{name}"."{table_name}"')
                row_counts[table_name] = int(cur.fetchone()[0])

        return [
            TableInfo(name=t, row_count=row_counts.get(t, 0), columns=cols)
            for t, cols in sorted(tables.items())
        ]

    # -- shared helpers --------------------------------------------------

    def drop_user_schema(self, user_id) -> None:
        for name in (self.schema_name(user_id), self.playground_schema_name(user_id)):
            self._drop_schema(name)

    def _playground_template(self) -> SandboxSchema:
        template = SandboxSchema.objects.filter(is_playground=True).first()
        if template is None:
            raise SandboxNotConfigured(
                "No playground SandboxSchema is seeded. Run "
                "`python manage.py seed_playground` to create one."
            )
        return template

    def _schema_exists(self, name: str) -> bool:
        conn = connections[self.db_alias]
        conn.ensure_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                [name],
            )
            return cur.fetchone() is not None

    def _reset_schema(self, name: str, schemas: Iterable[SandboxSchema]) -> str:
        seeds = list(schemas)
        conn = connections[self.db_alias]
        conn.ensure_connection()

        with transaction.atomic(using=self.db_alias):
            with conn.cursor() as cur:
                cur.execute(f'DROP SCHEMA IF EXISTS "{name}" CASCADE')
                cur.execute(f'CREATE SCHEMA "{name}"')
                cur.execute(f'SET LOCAL search_path TO "{name}"')
                for schema in seeds:
                    for statement in _split_sql_statements(schema.schema_sql):
                        cur.execute(statement)
        return name

    def _drop_schema(self, name: str) -> None:
        conn = connections[self.db_alias]
        conn.ensure_connection()
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{name}" CASCADE')


class SandboxNotConfigured(RuntimeError):
    """Raised when a sandbox feature needs configuration that isn't seeded."""


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
