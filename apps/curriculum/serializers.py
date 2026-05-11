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
    is_locked = serializers.SerializerMethodField()

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
            "is_locked",
        )

    def get_is_locked(self, lesson: Lesson) -> bool:
        return bool(getattr(lesson, "is_locked", False))


class ChapterDetailSerializer(ChapterListSerializer):
    lessons = serializers.SerializerMethodField()
    chapter_quizzes = serializers.SerializerMethodField()

    class Meta(ChapterListSerializer.Meta):
        fields = ChapterListSerializer.Meta.fields + ("lessons", "chapter_quizzes")

    def _user(self):
        request = self.context.get("request")
        return getattr(request, "user", None) if request else None

    def get_lessons(self, chapter: Chapter):
        qs = list(
            Lesson.objects.filter(chapter=chapter, is_active=True)
            .with_user_progress(self._user())
            .order_by("order")
        )
        # A lesson unlocks once every preceding lesson in the chapter is
        # complete. The first lesson is always unlocked. Locking is purely
        # learner-progression UX — admins/staff bypass it on the client side
        # by simply not showing a lock chip when irrelevant.
        previous_done = True
        for lesson in qs:
            lesson.is_locked = not previous_done
            previous_done = previous_done and bool(lesson.is_completed)
        return LessonListSerializer(qs, many=True, context=self.context).data

    def get_chapter_quizzes(self, chapter: Chapter):
        user = self._user()
        # Quizzes unlock once every lesson in the chapter is completed.
        lessons = (
            Lesson.objects.filter(chapter=chapter, is_active=True)
            .with_user_progress(user)
        )
        all_lessons_done = (
            user is not None
            and user.is_authenticated
            and lessons.exists()
            and all(bool(l.is_completed) for l in lessons)
        )

        qs = list(
            Exercise.objects.for_chapter(chapter.id).with_user_status(user)
        )
        for exercise in qs:
            exercise.is_locked = not all_lessons_done
        return ExerciseSummarySerializer(qs, many=True, context=self.context).data


class ExerciseSummarySerializer(serializers.ModelSerializer):
    user_status = serializers.CharField(read_only=True, default=ExerciseStatus.NOT_STARTED)
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = Exercise
        fields = (
            "id",
            "title",
            "difficulty",
            "order",
            "is_chapter_quiz",
            "user_status",
            "is_locked",
        )

    def get_is_locked(self, exercise: Exercise) -> bool:
        return bool(getattr(exercise, "is_locked", False))


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
