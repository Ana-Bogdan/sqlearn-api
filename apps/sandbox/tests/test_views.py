"""View-level tests for the sandbox endpoints.

PostgreSQL-only boundary
------------------------
Real SQL execution, per-user schema isolation, ``information_schema``
introspection, and statement timeouts depend on PostgreSQL features that do
not exist under the SQLite test database (``CREATE/DROP SCHEMA``,
``SET LOCAL search_path``/``statement_timeout``, ``psycopg`` error classes).
Those paths cannot run here, so this module:

* Tests the parts that need no live execution directly (auth, validation,
  DDL rejection, the "playground not configured" 503 path, lock rules).
* Tests the *view orchestration* around execution (progress transitions,
  gamification dispatch, attempt logging, badge surfacing) by mocking the
  ``SandboxService`` / execution boundary — the genuine SQL execution itself
  is the only thing not covered, and that is a Postgres-only concern.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.curriculum.models import Chapter, Exercise, Lesson
from apps.progress.models import ExerciseStatus, QuerySubmission, UserExerciseProgress
from apps.sandbox.models import SandboxQueryAttempt
from apps.sandbox.services import (
    QueryExecutionError,
    QuerySyntaxError,
    QueryTimeout,
    TableInfo,
)
from apps.users.models import UserRole

User = get_user_model()

PASSWORD = "pw-Complex-1!"

VIEWS_SVC = "apps.sandbox.views.SandboxService"
VIEWS_PIPELINE = "apps.sandbox.views.QueryValidationPipeline"


class _FakePipeline:
    """Stand-in for QueryValidationPipeline that records a fixed outcome."""

    correct = True
    outcome = {"status": "correct", "message": "ok"}

    def __init__(self, *args, **kwargs):
        pass

    def run(self, ctx):
        ctx.is_correct = self.correct
        return dict(self.outcome)


def _fake_pipeline(correct, outcome):
    return type("P", (_FakePipeline,), {"correct": correct, "outcome": outcome})


class ExerciseSubmitAuthTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.chapter = Chapter.objects.create(title="C", order=1)
        cls.lesson = Lesson.objects.create(chapter=cls.chapter, title="L", order=1)
        cls.exercise = Exercise.objects.create(
            chapter=cls.chapter, lesson=cls.lesson, title="E",
            instructions="x", solution_query="SELECT 1;", is_published=True,
        )

    def test_anonymous_is_rejected(self):
        resp = self.client.post(
            reverse("exercise-submit", args=[self.exercise.id]),
            {"sql_text": "SELECT 1;"}, format="json",
        )
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_blank_sql_is_rejected(self):
        user = User.objects.create_user(
            email="u@example.com", password=PASSWORD, first_name="U", last_name="U"
        )
        self.client.force_authenticate(user)
        resp = self.client.post(
            reverse("exercise-submit", args=[self.exercise.id]),
            {"sql_text": "   "}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class ExerciseSubmitLockTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.chapter = Chapter.objects.create(title="C", order=1)
        cls.lesson_one = Lesson.objects.create(chapter=cls.chapter, title="L1", order=1)
        cls.lesson_two = Lesson.objects.create(chapter=cls.chapter, title="L2", order=2)
        # Lesson 1 has an exercise that must be completed to unlock lesson 2.
        Exercise.objects.create(
            chapter=cls.chapter, lesson=cls.lesson_one, title="E1",
            instructions="x", solution_query="SELECT 1;", is_published=True,
        )
        cls.locked_exercise = Exercise.objects.create(
            chapter=cls.chapter, lesson=cls.lesson_two, title="E2",
            instructions="x", solution_query="SELECT 1;", is_published=True,
        )

    def test_locked_exercise_is_forbidden_for_learner(self):
        user = User.objects.create_user(
            email="u@example.com", password=PASSWORD, first_name="U", last_name="U"
        )
        self.client.force_authenticate(user)
        resp = self.client.post(
            reverse("exercise-submit", args=[self.locked_exercise.id]),
            {"sql_text": "SELECT 1;"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(resp.json()["status"], "forbidden")

    def test_locked_chapter_quiz_is_forbidden(self):
        quiz = Exercise.objects.create(
            chapter=self.chapter, title="Quiz", instructions="x",
            solution_query="SELECT 1;", is_published=True, is_chapter_quiz=True,
        )
        user = User.objects.create_user(
            email="q@example.com", password=PASSWORD, first_name="Q", last_name="Q"
        )
        self.client.force_authenticate(user)
        resp = self.client.post(
            reverse("exercise-submit", args=[quiz.id]),
            {"sql_text": "SELECT 1;"}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_bypasses_the_lock(self):
        admin = User.objects.create_user(
            email="a@example.com", password=PASSWORD, first_name="A", last_name="A",
            role=UserRole.ADMIN, is_staff=True,
        )
        self.client.force_authenticate(admin)
        with patch(VIEWS_SVC), patch(
            VIEWS_PIPELINE, _fake_pipeline(True, {"status": "correct", "message": "ok"})
        ):
            resp = self.client.post(
                reverse("exercise-submit", args=[self.locked_exercise.id]),
                {"sql_text": "SELECT 1;"}, format="json",
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class ExerciseSubmitOrchestrationTests(APITestCase):
    """Exercises the view's progress/gamification wiring with execution mocked."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="u@example.com", password=PASSWORD, first_name="U", last_name="U"
        )
        cls.chapter = Chapter.objects.create(title="C", order=1)
        cls.lesson = Lesson.objects.create(chapter=cls.chapter, title="L", order=1)
        cls.exercise = Exercise.objects.create(
            chapter=cls.chapter, lesson=cls.lesson, title="E",
            instructions="x", solution_query="SELECT 1;", is_published=True,
        )

    def setUp(self):
        self.client.force_authenticate(self.user)
        self.url = reverse("exercise-submit", args=[self.exercise.id])

    def test_correct_submission_completes_and_awards(self):
        with patch(VIEWS_SVC), patch(
            VIEWS_PIPELINE, _fake_pipeline(True, {"status": "correct", "message": "ok"})
        ):
            resp = self.client.post(self.url, {"sql_text": "SELECT 1;"}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertEqual(body["user_status"], ExerciseStatus.COMPLETED)
        self.assertTrue(body["was_first_attempt"])
        self.assertEqual(body["submission_count"], 1)
        self.assertIsNotNone(body["gamification"])
        progress = UserExerciseProgress.objects.get(user=self.user, exercise=self.exercise)
        self.assertEqual(progress.status, ExerciseStatus.COMPLETED)
        self.assertEqual(QuerySubmission.objects.filter(user=self.user).count(), 1)

    def test_incorrect_submission_marks_attempted(self):
        with patch(VIEWS_SVC), patch(
            VIEWS_PIPELINE,
            _fake_pipeline(False, {"status": "incorrect", "message": "nope"}),
        ):
            resp = self.client.post(self.url, {"sql_text": "SELECT 2;"}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertEqual(body["user_status"], ExerciseStatus.ATTEMPTED)
        self.assertFalse(body["was_first_attempt"])
        self.assertIsNone(body["gamification"])

    def test_second_correct_attempt_is_not_first_attempt(self):
        # First a wrong attempt, then a correct one.
        with patch(VIEWS_SVC), patch(
            VIEWS_PIPELINE,
            _fake_pipeline(False, {"status": "incorrect", "message": "nope"}),
        ):
            self.client.post(self.url, {"sql_text": "SELECT 2;"}, format="json")
        with patch(VIEWS_SVC), patch(
            VIEWS_PIPELINE, _fake_pipeline(True, {"status": "correct", "message": "ok"})
        ):
            resp = self.client.post(self.url, {"sql_text": "SELECT 1;"}, format="json")

        body = resp.json()
        self.assertEqual(body["user_status"], ExerciseStatus.COMPLETED)
        self.assertFalse(body["was_first_attempt"])
        self.assertEqual(body["submission_count"], 2)


class SandboxExecuteViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="u@example.com", password=PASSWORD, first_name="U", last_name="U"
        )

    def setUp(self):
        self.url = reverse("sandbox-execute")

    def test_anonymous_is_rejected(self):
        resp = self.client.post(self.url, {"sql_text": "SELECT 1;"}, format="json")
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_ddl_is_forbidden_and_logged(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post(
            self.url, {"sql_text": "DROP TABLE students;"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["status"], "forbidden")
        attempt = SandboxQueryAttempt.objects.get(user=self.user)
        self.assertFalse(attempt.succeeded)

    def test_missing_playground_returns_503(self):
        # No playground SandboxSchema is seeded, so the service reports it as
        # unconfigured before any SQL would run.
        self.client.force_authenticate(self.user)
        resp = self.client.post(self.url, {"sql_text": "SELECT 1;"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_successful_execution_logs_attempt(self):
        self.client.force_authenticate(self.user)
        result = {"columns": ["n"], "rows": [[1]], "rowcount": 1}
        with patch(VIEWS_SVC) as svc, patch(
            "apps.sandbox.views.SandboxExecuteView.execution_service"
        ) as exec_svc:
            svc.return_value.get_or_create_playground.return_value = ("schema", None)
            exec_svc.run.return_value = result
            resp = self.client.post(self.url, {"sql_text": "SELECT 1;"}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["result"], result)
        attempt = SandboxQueryAttempt.objects.get(user=self.user)
        self.assertTrue(attempt.succeeded)

    def _execute_raising(self, exc):
        with patch(VIEWS_SVC) as svc, patch(
            "apps.sandbox.views.SandboxExecuteView.execution_service"
        ) as exec_svc:
            svc.return_value.get_or_create_playground.return_value = ("schema", None)
            exec_svc.run.side_effect = exc
            return self.client.post(self.url, {"sql_text": "SELECT 1;"}, format="json")

    def test_timeout_is_reported_and_logged_as_failure(self):
        self.client.force_authenticate(self.user)
        resp = self._execute_raising(QueryTimeout("slow"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["status"], "timeout")
        self.assertFalse(SandboxQueryAttempt.objects.get(user=self.user).succeeded)

    def test_syntax_error_is_reported(self):
        self.client.force_authenticate(self.user)
        resp = self._execute_raising(QuerySyntaxError("bad"))
        self.assertEqual(resp.json()["status"], "syntax_error")

    def test_execution_error_is_reported(self):
        self.client.force_authenticate(self.user)
        resp = self._execute_raising(QueryExecutionError("boom"))
        self.assertEqual(resp.json()["status"], "execution_error")


class SandboxSchemaViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="u@example.com", password=PASSWORD, first_name="U", last_name="U"
        )

    def test_anonymous_is_rejected(self):
        resp = self.client.get(reverse("sandbox-schema"))
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_missing_playground_returns_503(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get(reverse("sandbox-schema"))
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_returns_table_metadata(self):
        self.client.force_authenticate(self.user)
        tables = [TableInfo(name="students", row_count=3, columns=[])]
        with patch(VIEWS_SVC) as svc:
            svc.return_value.introspect_playground.return_value = tables
            resp = self.client.get(reverse("sandbox-schema"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertEqual(body["tables"][0]["name"], "students")
        self.assertEqual(body["tables"][0]["row_count"], 3)


class SandboxResetViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="u@example.com", password=PASSWORD, first_name="U", last_name="U"
        )

    def test_anonymous_is_rejected(self):
        resp = self.client.post(reverse("sandbox-reset"))
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_missing_playground_returns_503(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post(reverse("sandbox-reset"))
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_reset_succeeds(self):
        self.client.force_authenticate(self.user)
        with patch(VIEWS_SVC):
            resp = self.client.post(reverse("sandbox-reset"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["status"], "reset")
