from rest_framework import serializers

from apps.progress.models import ExerciseStatus

from .models import Chapter, Exercise, ExerciseHint, Lesson


class ChapterListSerializer(serializers.ModelSerializer):
    total_exercises = serializers.IntegerField(read_only=True)
    completed_exercises = serializers.IntegerField(read_only=True)
    completion_percent = serializers.FloatField(read_only=True)

    class Meta:
        model = Chapter
        fields = (
            "id",
            "title",
            "description",
            "order",
            "total_exercises",
            "completed_exercises",
            "completion_percent",
        )


class LessonListSerializer(serializers.ModelSerializer):
    total_exercises = serializers.IntegerField(read_only=True)
    completed_exercises = serializers.IntegerField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = Lesson
        fields = (
            "id",
            "chapter_id",
            "title",
            "order",
            "total_exercises",
            "completed_exercises",
            "is_completed",
        )


class ChapterDetailSerializer(ChapterListSerializer):
    lessons = serializers.SerializerMethodField()
    chapter_quizzes = serializers.SerializerMethodField()

    class Meta(ChapterListSerializer.Meta):
        fields = ChapterListSerializer.Meta.fields + ("lessons", "chapter_quizzes")

    def _user(self):
        request = self.context.get("request")
        return getattr(request, "user", None) if request else None

    def get_lessons(self, chapter: Chapter):
        qs = (
            Lesson.objects.filter(chapter=chapter, is_active=True)
            .with_user_progress(self._user())
            .order_by("order")
        )
        return LessonListSerializer(qs, many=True, context=self.context).data

    def get_chapter_quizzes(self, chapter: Chapter):
        qs = (
            Exercise.objects.for_chapter(chapter.id)
            .with_user_status(self._user())
        )
        return ExerciseSummarySerializer(qs, many=True, context=self.context).data


class ExerciseSummarySerializer(serializers.ModelSerializer):
    user_status = serializers.CharField(read_only=True, default=ExerciseStatus.NOT_STARTED)

    class Meta:
        model = Exercise
        fields = (
            "id",
            "title",
            "difficulty",
            "order",
            "is_chapter_quiz",
            "user_status",
        )


class LessonDetailSerializer(LessonListSerializer):
    description = serializers.CharField(source="theory_content", read_only=True)
    exercises = serializers.SerializerMethodField()

    class Meta(LessonListSerializer.Meta):
        fields = LessonListSerializer.Meta.fields + (
            "theory_content",
            "description",
            "exercises",
        )

    def get_exercises(self, lesson: Lesson):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        qs = Exercise.objects.for_lesson(lesson.id).with_user_status(user)
        return ExerciseSummarySerializer(qs, many=True, context=self.context).data


class ExerciseHintSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExerciseHint
        fields = ("id", "order", "hint_text")


class ExerciseDetailSerializer(serializers.ModelSerializer):
    user_status = serializers.CharField(read_only=True, default=ExerciseStatus.NOT_STARTED)
    hint_count = serializers.SerializerMethodField()

    class Meta:
        model = Exercise
        fields = (
            "id",
            "chapter_id",
            "lesson_id",
            "title",
            "instructions",
            "difficulty",
            "starter_code",
            "is_chapter_quiz",
            "order",
            "user_status",
            "hint_count",
        )

    def get_hint_count(self, exercise: Exercise) -> int:
        return exercise.hints.count()
