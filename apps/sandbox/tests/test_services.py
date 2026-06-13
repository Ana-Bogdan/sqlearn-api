"""Unit tests for sandbox service helpers that don't need PostgreSQL."""

from django.test import SimpleTestCase

from apps.sandbox.services.execution_service import _clean
from apps.sandbox.services.sandbox_service import (
    _split_sql_statements,
    playground_schema_name,
    user_schema_name,
)


class SchemaNameTests(SimpleTestCase):
    def test_user_schema_name(self):
        self.assertEqual(user_schema_name(42), "sandbox_user_42")

    def test_playground_schema_name(self):
        self.assertEqual(playground_schema_name(42), "sandbox_playground_42")


class SplitSqlStatementsTests(SimpleTestCase):
    def test_splits_on_semicolons(self):
        out = _split_sql_statements("CREATE TABLE t (id INT); INSERT INTO t VALUES (1);")
        self.assertEqual(len(out), 2)

    def test_ignores_blank_chunks(self):
        out = _split_sql_statements("SELECT 1;;;  ;")
        self.assertEqual(out, ["SELECT 1"])

    def test_empty_input(self):
        self.assertEqual(_split_sql_statements(""), [])


class CleanMessageTests(SimpleTestCase):
    def test_keeps_only_first_line(self):
        self.assertEqual(
            _clean('syntax error at "FORM"\nLINE 1: SELECT * FORM t'),
            'syntax error at "FORM"',
        )

    def test_strips_surrounding_whitespace(self):
        self.assertEqual(_clean("  boom  "), "boom")
