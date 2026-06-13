"""Unit tests for the SandboxDatabaseRouter."""

from django.test import SimpleTestCase

from apps.sandbox.routers import SandboxDatabaseRouter


class SandboxDatabaseRouterTests(SimpleTestCase):
    def setUp(self):
        self.router = SandboxDatabaseRouter()

    def test_read_and_write_are_unrouted(self):
        self.assertIsNone(self.router.db_for_read(object))
        self.assertIsNone(self.router.db_for_write(object))

    def test_relations_are_unrouted(self):
        self.assertIsNone(self.router.allow_relation(object(), object()))

    def test_migrations_blocked_on_sandbox_alias(self):
        self.assertFalse(self.router.allow_migrate("sandbox", "users"))

    def test_migrations_unconstrained_on_default_alias(self):
        self.assertIsNone(self.router.allow_migrate("default", "users"))
