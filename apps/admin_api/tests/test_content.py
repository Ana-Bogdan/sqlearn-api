"""Admin CRUD tests for chapters, lessons, exercises, datasets, and badges."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.curriculum.models import Chapter, Exercise, Lesson
from apps.gamification.models import Badge
from apps.sandbox.models import ExerciseDataset, SandboxSchema
from apps.users.models import UserRole

User = get_user_model()

PASSWORD = "pw-Complex-1!"


class _AdminFixture(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            email="admin@example.com", password=PASSWORD, first_name="A", last_name="D",
            role=UserRole.ADMIN,
        )

    def setUp(self):
        self.client.force_authenticate(self.admin)


class AdminChapterTests(_AdminFixture):
    def test_list_includes_inactive_chapters(self):
        Chapter.objects.create(title="Active", order=1)
        Chapter.objects.create(title="Hidden", order=2, is_active=False)
        resp = self.client.get(reverse("admin_api:chapter-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        titles = [c["title"] for c in resp.json()]
        self.assertIn("Hidden", titles)

    def test_create_chapter(self):
        resp = self.client.post(
            reverse("admin_api:chapter-list"),
            {"title": "New", "description": "d", "order": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Chapter.objects.filter(title="New").exists())

    def test_soft_delete_flips_is_active(self):
        chapter = Chapter.objects.create(title="C", order=1)
        resp = self.client.delete(
            reverse("admin_api:chapter-detail", args=[chapter.id])
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        chapter.refresh_from_db()
        self.assertFalse(chapter.is_active)

    def test_reorder_moves_chapter_down(self):
        c1 = Chapter.objects.create(title="C1", order=1)
        c2 = Chapter.objects.create(title="C2", order=2)
        c3 = Chapter.objects.create(title="C3", order=3)
        resp = self.client.patch(
            reverse("admin_api:chapter-reorder", args=[c1.id]),
            {"order": 3}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        c1.refresh_from_db(); c2.refresh_from_db(); c3.refresh_from_db()
        self.assertEqual(c1.order, 3)
        self.assertEqual(c2.order, 1)
        self.assertEqual(c3.order, 2)

    def test_reorder_moves_chapter_up(self):
        c1 = Chapter.objects.create(title="C1", order=1)
        c2 = Chapter.objects.create(title="C2", order=2)
        c3 = Chapter.objects.create(title="C3", order=3)
        resp = self.client.patch(
            reverse("admin_api:chapter-reorder", args=[c3.id]),
            {"order": 1}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        c1.refresh_from_db(); c2.refresh_from_db(); c3.refresh_from_db()
        self.assertEqual(c3.order, 1)
        self.assertEqual(c1.order, 2)
        self.assertEqual(c2.order, 3)

    def test_reorder_to_same_position_is_noop(self):
        c1 = Chapter.objects.create(title="C1", order=1)
        resp = self.client.patch(
            reverse("admin_api:chapter-reorder", args=[c1.id]),
            {"order": 1}, format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        c1.refresh_from_db()
        self.assertEqual(c1.order, 1)


class AdminLessonTests(_AdminFixture):
    def setUp(self):
        super().setUp()
        self.chapter = Chapter.objects.create(title="C", order=1)

    def test_create_lesson(self):
        resp = self.client.post(
            reverse("admin_api:lesson-create"),
            {"chapter": self.chapter.id, "title": "L", "order": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_soft_delete_lesson(self):
        lesson = Lesson.objects.create(chapter=self.chapter, title="L", order=1)
        resp = self.client.delete(
            reverse("admin_api:lesson-detail", args=[lesson.id])
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        lesson.refresh_from_db()
        self.assertFalse(lesson.is_active)


class AdminExerciseTests(_AdminFixture):
    def setUp(self):
        super().setUp()
        self.chapter = Chapter.objects.create(title="C", order=1)
        self.lesson = Lesson.objects.create(chapter=self.chapter, title="L", order=1)

    def _payload(self, **overrides):
        data = {
            "chapter": self.chapter.id,
            "lesson": self.lesson.id,
            "title": "E",
            "instructions": "do it",
            "solution_query": "SELECT 1;",
            "difficulty": "easy",
        }
        data.update(overrides)
        return data

    def test_create_exercise_with_hints(self):
        payload = self._payload(
            hints=[{"order": 1, "hint_text": "first"}, {"order": 2, "hint_text": "second"}]
        )
        resp = self.client.post(
            reverse("admin_api:exercise-create"), payload, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        exercise = Exercise.objects.get(title="E")
        self.assertEqual(exercise.hints.count(), 2)

    def test_non_quiz_requires_lesson(self):
        payload = self._payload()
        payload.pop("lesson")
        resp = self.client.post(
            reverse("admin_api:exercise-create"), payload, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("lesson", resp.json())

    def test_lesson_chapter_mismatch_is_rejected(self):
        other_chapter = Chapter.objects.create(title="Other", order=2)
        payload = self._payload(chapter=other_chapter.id)
        resp = self.client.post(
            reverse("admin_api:exercise-create"), payload, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_soft_delete_exercise(self):
        exercise = Exercise.objects.create(
            chapter=self.chapter, lesson=self.lesson, title="E",
            instructions="x", solution_query="SELECT 1;",
        )
        resp = self.client.delete(
            reverse("admin_api:exercise-detail", args=[exercise.id])
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        exercise.refresh_from_db()
        self.assertFalse(exercise.is_active)


class AdminTestSolutionTests(_AdminFixture):
    def setUp(self):
        super().setUp()
        self.chapter = Chapter.objects.create(title="C", order=1)
        self.lesson = Lesson.objects.create(chapter=self.chapter, title="L", order=1)
        self.exercise = Exercise.objects.create(
            chapter=self.chapter, lesson=self.lesson, title="E",
            instructions="x", solution_query="SELECT 1;",
        )

    def test_no_solution_query_returns_400(self):
        self.exercise.solution_query = "   "
        self.exercise.save(update_fields=["solution_query"])
        resp = self.client.post(
            reverse("admin_api:exercise-test-solution", args=[self.exercise.id])
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_dataset_returns_400(self):
        resp = self.client.post(
            reverse("admin_api:exercise-test-solution", args=[self.exercise.id])
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("dataset", resp.json()["detail"])

    def test_runs_solution_against_dataset(self):
        # Execution itself is PostgreSQL-only, so the sandbox boundary is mocked;
        # this verifies the view serializes the result correctly.
        schema = SandboxSchema.objects.create(name="ds", schema_sql="CREATE TABLE t (id INT);")
        ExerciseDataset.objects.create(exercise=self.exercise, sandbox_schema=schema)
        result = {"columns": ["id"], "rows": [[1]], "rowcount": 1}
        with patch("apps.admin_api.views.SandboxService"), patch(
            "apps.admin_api.views.QueryExecutionService"
        ) as exec_cls:
            exec_cls.return_value.run.return_value = result
            resp = self.client.post(
                reverse("admin_api:exercise-test-solution", args=[self.exercise.id])
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["columns"], ["id"])


class AdminDatasetTests(_AdminFixture):
    def test_create_and_list_dataset(self):
        resp = self.client.post(
            reverse("admin_api:dataset-list"),
            {"name": "ds", "schema_sql": "CREATE TABLE t (id INT);"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        listing = self.client.get(reverse("admin_api:dataset-list"))
        self.assertEqual(len(listing.json()), 1)

    def test_delete_unlinked_dataset(self):
        schema = SandboxSchema.objects.create(name="ds", schema_sql="x")
        resp = self.client.delete(
            reverse("admin_api:dataset-detail", args=[schema.id])
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_linked_dataset_conflicts(self):
        chapter = Chapter.objects.create(title="C", order=1)
        lesson = Lesson.objects.create(chapter=chapter, title="L", order=1)
        exercise = Exercise.objects.create(
            chapter=chapter, lesson=lesson, title="E",
            instructions="x", solution_query="SELECT 1;",
        )
        schema = SandboxSchema.objects.create(name="ds", schema_sql="x")
        ExerciseDataset.objects.create(exercise=exercise, sandbox_schema=schema)
        resp = self.client.delete(
            reverse("admin_api:dataset-detail", args=[schema.id])
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)


class AdminBadgeTests(_AdminFixture):
    def test_list_badges(self):
        resp = self.client.get(reverse("admin_api:badge-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreater(len(resp.json()), 0)

    def test_update_display_only(self):
        badge = Badge.objects.get(trigger_type="first_query")
        resp = self.client.patch(
            reverse("admin_api:badge-detail", args=[badge.id]),
            {"name": "Renamed", "trigger_type": "hacked", "category": "skill"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        badge.refresh_from_db()
        self.assertEqual(badge.name, "Renamed")
        # trigger_type and category are read-only.
        self.assertEqual(badge.trigger_type, "first_query")
        self.assertEqual(badge.category, "milestone")
