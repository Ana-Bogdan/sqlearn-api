from django.db import models

from .managers import ChapterManager, ExerciseManager, LessonManager


class Difficulty(models.TextChoices):
    EASY = "easy", "Easy"
    MEDIUM = "medium", "Medium"
    HARD = "hard", "Hard"


class Chapter(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ChapterManager()

    class Meta:
        db_table = "chapters"
        ordering = ("order", "id")

    def __str__(self):
        return f"{self.order}. {self.title}"


class Lesson(models.Model):
    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, related_name="lessons"
    )
    title = models.CharField(max_length=200)
    theory_content = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = LessonManager()

    class Meta:
        db_table = "lessons"
        ordering = ("chapter__order", "order", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("chapter", "order"), name="lesson_unique_order_in_chapter"
            ),
        ]

    def __str__(self):
        return f"{self.chapter.order}.{self.order} {self.title}"


class Exercise(models.Model):
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="exercises",
        null=True,
        blank=True,
    )
    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, related_name="exercises"
    )
    title = models.CharField(max_length=200)
    instructions = models.TextField()
    difficulty = models.CharField(
        max_length=10, choices=Difficulty.choices, default=Difficulty.EASY
    )
    starter_code = models.TextField(blank=True)
    solution_query = models.TextField()
    expected_result = models.JSONField(default=dict)

    is_chapter_quiz = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ExerciseManager()

    class Meta:
        db_table = "exercises"
        ordering = ("chapter__order", "order", "id")
        indexes = [
            models.Index(fields=("lesson", "order")),
            models.Index(fields=("chapter", "is_chapter_quiz")),
        ]

    def __str__(self):
        scope = self.lesson_id or f"quiz ch.{self.chapter_id}"
        return f"[{scope}] {self.title}"


class ExerciseHint(models.Model):
    exercise = models.ForeignKey(
        Exercise, on_delete=models.CASCADE, related_name="hints"
    )
    hint_text = models.TextField()
    order = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "exercise_hints"
        ordering = ("exercise_id", "order")
        constraints = [
            models.UniqueConstraint(
                fields=("exercise", "order"), name="hint_unique_order_per_exercise"
            ),
        ]

    def __str__(self):
        return f"hint {self.order} for {self.exercise_id}"
