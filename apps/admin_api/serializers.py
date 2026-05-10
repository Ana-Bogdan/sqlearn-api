"""Admin-facing serializers.

These deliberately expose more fields than the learner-facing serializers in
``apps.curriculum.serializers`` (e.g. ``solution_query``, ``expected_result``,
``is_published``, ``is_active``) because admins are authoring content.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.curriculum.models import Chapter, Difficulty, Exercise, ExerciseHint, Lesson
from apps.gamification.models import Badge
from apps.sandbox.models import ExerciseDataset, SandboxSchema

User = get_user_model()


# ---------------------------------------------------------------------------
# Chapters
# ---------------------------------------------------------------------------


class AdminChapterSerializer(serializers.ModelSerializer):
    lesson_count = serializers.SerializerMethodField()
    exercise_count = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = (
            "id",
            "title",
            "description",
            "order",
            "is_active",
            "lesson_count",
            "exercise_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_lesson_count(self, chapter: Chapter) -> int:
        return chapter.lessons.filter(is_active=True).count()

    def get_exercise_count(self, chapter: Chapter) -> int:
        return chapter.exercises.filter(is_active=True).count()


class AdminChapterReorderSerializer(serializers.Serializer):
    """Body for ``PATCH /api/admin/chapters/{id}/reorder/``.

    A single ``order`` value reorders just this chapter; sibling chapters with
    the same order are nudged so the requested chapter ends up at the target
    position. This is simpler for the FE than sending a full list and matches
    the drag-to-reorder UX in M17.
    """

    order = serializers.IntegerField(min_value=0)


# ---------------------------------------------------------------------------
# Lessons
# ---------------------------------------------------------------------------


class AdminLessonSerializer(serializers.ModelSerializer):
    exercise_count = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = (
            "id",
            "chapter",
            "title",
            "theory_content",
            "order",
            "is_active",
            "exercise_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_exercise_count(self, lesson: Lesson) -> int:
        return lesson.exercises.filter(is_active=True).count()


# ---------------------------------------------------------------------------
# Exercises
# ---------------------------------------------------------------------------


class AdminExerciseHintSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ExerciseHint
        fields = ("id", "order", "hint_text")


class AdminExerciseDatasetLinkSerializer(serializers.ModelSerializer):
    sandbox_schema_name = serializers.CharField(
        source="sandbox_schema.name", read_only=True
    )

    class Meta:
        model = ExerciseDataset
        fields = ("id", "sandbox_schema", "sandbox_schema_name")


class AdminExerciseSerializer(serializers.ModelSerializer):
    hints = AdminExerciseHintSerializer(many=True, required=False)
    datasets = AdminExerciseDatasetLinkSerializer(many=True, read_only=True)
    sandbox_schema_ids = serializers.PrimaryKeyRelatedField(
        queryset=SandboxSchema.objects.all(),
        many=True,
        write_only=True,
        required=False,
        help_text=(
            "Replaces this exercise's dataset links with the supplied "
            "SandboxSchema IDs. Omit to leave links unchanged."
        ),
    )
    difficulty = serializers.ChoiceField(
        choices=Difficulty.choices, default=Difficulty.EASY
    )

    class Meta:
        model = Exercise
        fields = (
            "id",
            "chapter",
            "lesson",
            "title",
            "instructions",
            "difficulty",
            "starter_code",
            "solution_query",
            "expected_result",
            "is_chapter_quiz",
            "is_published",
            "is_active",
            "order",
            "hints",
            "datasets",
            "sandbox_schema_ids",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "datasets")

    def validate(self, attrs):
        chapter = attrs.get("chapter") or getattr(self.instance, "chapter", None)
        lesson = attrs.get("lesson", getattr(self.instance, "lesson", None))
        is_quiz = attrs.get(
            "is_chapter_quiz",
            getattr(self.instance, "is_chapter_quiz", False),
        )

        if lesson is not None:
            if chapter is None:
                attrs["chapter"] = lesson.chapter
            elif lesson.chapter_id != chapter.id:
                raise serializers.ValidationError(
                    {"lesson": "Lesson does not belong to the selected chapter."}
                )

        if not is_quiz and attrs.get("lesson", lesson) is None:
            raise serializers.ValidationError(
                {"lesson": "Non-quiz exercises must belong to a lesson."}
            )

        if is_quiz and lesson is not None and "lesson" not in attrs:
            # Allow chapter quizzes to be unset from a lesson via explicit None.
            pass

        return attrs

    def create(self, validated_data):
        hints = validated_data.pop("hints", None)
        schema_ids = validated_data.pop("sandbox_schema_ids", None)
        exercise = Exercise.objects.create(**validated_data)
        if hints is not None:
            self._sync_hints(exercise, hints)
        if schema_ids is not None:
            self._sync_datasets(exercise, schema_ids)
        return exercise

    def update(self, instance, validated_data):
        hints = validated_data.pop("hints", None)
        schema_ids = validated_data.pop("sandbox_schema_ids", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if hints is not None:
            self._sync_hints(instance, hints)
        if schema_ids is not None:
            self._sync_datasets(instance, schema_ids)
        return instance

    def _sync_hints(self, exercise: Exercise, hints: list[dict]) -> None:
        """Replace the exercise's hint set with the provided list."""

        ExerciseHint.objects.filter(exercise=exercise).delete()
        for index, payload in enumerate(hints, start=1):
            ExerciseHint.objects.create(
                exercise=exercise,
                order=payload.get("order", index),
                hint_text=payload["hint_text"],
            )

    def _sync_datasets(self, exercise: Exercise, schemas) -> None:
        ExerciseDataset.objects.filter(exercise=exercise).delete()
        for schema in schemas:
            ExerciseDataset.objects.create(
                exercise=exercise, sandbox_schema=schema
            )


class TestSolutionResultSerializer(serializers.Serializer):
    columns = serializers.ListField(child=serializers.CharField())
    rows = serializers.ListField(child=serializers.ListField())
    rowcount = serializers.IntegerField()


# ---------------------------------------------------------------------------
# Datasets (sandbox schemas)
# ---------------------------------------------------------------------------


class AdminSandboxSchemaSerializer(serializers.ModelSerializer):
    exercise_count = serializers.SerializerMethodField()

    class Meta:
        model = SandboxSchema
        fields = (
            "id",
            "name",
            "description",
            "schema_sql",
            "is_playground",
            "exercise_count",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def get_exercise_count(self, schema: SandboxSchema) -> int:
        return schema.exercise_datasets.count()


# ---------------------------------------------------------------------------
# Badges
# ---------------------------------------------------------------------------


class AdminBadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ("id", "trigger_type", "name", "description", "icon", "category")
        # Trigger type and category drive backend logic, so admins can only
        # tweak display text (per spec: "edit display only").
        read_only_fields = ("id", "trigger_type", "category")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "xp",
            "level",
            "current_streak",
            "longest_streak",
            "last_activity_date",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "email",
            "role",
            "xp",
            "level",
            "current_streak",
            "longest_streak",
            "last_activity_date",
            "created_at",
            "updated_at",
        )


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class AdminExerciseStatRow(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    chapter_id = serializers.IntegerField()
    lesson_id = serializers.IntegerField(allow_null=True)
    attempts = serializers.IntegerField()
    failures = serializers.IntegerField()
    fail_rate = serializers.FloatField()


class AdminStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    active_today = serializers.IntegerField()
    active_this_week = serializers.IntegerField()
    new_registrations_this_week = serializers.IntegerField()
    avg_exercises_per_user = serializers.FloatField()
    highest_fail_rate_exercises = AdminExerciseStatRow(many=True)
    most_attempted_exercises = AdminExerciseStatRow(many=True)
