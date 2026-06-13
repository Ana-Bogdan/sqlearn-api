"""Unit tests for the ForbiddenOperationHandler and comment stripping.

The other pipeline handlers (syntax check, execution) require a live
PostgreSQL connection and are exercised against Postgres only — see the note
in ``test_views.py``.
"""

from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.sandbox.services.pipeline import (
    ForbiddenOperationHandler,
    SubmissionContext,
    _strip_sql_comments,
)


def _ctx(sql, chapter_order=1):
    exercise = SimpleNamespace(chapter=SimpleNamespace(order=chapter_order))
    return SubmissionContext(user=SimpleNamespace(id=1), exercise=exercise, sql=sql)


class StripSqlCommentsTests(SimpleTestCase):
    def test_strips_line_comments(self):
        out = _strip_sql_comments("SELECT 1 -- a comment\nFROM t")
        self.assertNotIn("comment", out)

    def test_strips_block_comments(self):
        out = _strip_sql_comments("SELECT /* DROP TABLE t */ 1")
        self.assertNotIn("DROP", out)


class ForbiddenOperationHandlerTests(SimpleTestCase):
    def setUp(self):
        self.handler = ForbiddenOperationHandler()

    def test_ddl_is_blocked_in_any_chapter(self):
        outcome = self.handler.process(_ctx("DROP TABLE students", chapter_order=9))
        self.assertEqual(outcome["status"], "forbidden")

    def test_select_is_allowed(self):
        outcome = self.handler.process(_ctx("SELECT * FROM students", chapter_order=1))
        self.assertIsNone(outcome)

    def test_writes_blocked_before_chapter_seven(self):
        outcome = self.handler.process(
            _ctx("INSERT INTO students VALUES (1)", chapter_order=3)
        )
        self.assertEqual(outcome["status"], "forbidden")
        self.assertIn("SELECT", outcome["message"])

    def test_writes_allowed_from_chapter_seven(self):
        outcome = self.handler.process(
            _ctx("INSERT INTO students VALUES (1)", chapter_order=7)
        )
        self.assertIsNone(outcome)

    def test_ddl_hidden_in_comment_is_ignored(self):
        outcome = self.handler.process(
            _ctx("SELECT 1 -- DROP TABLE x", chapter_order=1)
        )
        self.assertIsNone(outcome)
