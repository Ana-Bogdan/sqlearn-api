from django.conf import settings
from django.db import models

from .managers import UserProgressManager


class ExerciseStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not started"
    ATTEMPTED = "attempted", "Attempted"
    COMPLETED = "completed", "Completed"


class UserExerciseProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exercise_progress",
    )
    exercise = models.ForeignKey(
        "curriculum.Exercise",
        on_delete=models.CASCADE,
        related_name="user_progress",
    )
    status = models.CharField(
        max_length=20,
        choices=ExerciseStatus.choices,
        default=ExerciseStatus.NOT_STARTED,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    first_attempt = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserProgressManager()

    class Meta:
        db_table = "user_exercise_progress"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "exercise"), name="user_progress_unique_per_exercise"
            ),
        ]
        indexes = [
            models.Index(fields=("user", "status")),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.exercise_id} = {self.status}"


class UserLessonProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )
    lesson = models.ForeignKey(
        "curriculum.Lesson",
        on_delete=models.CASCADE,
        related_name="user_progress",
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_lesson_progress"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "lesson"), name="user_lesson_unique"
            ),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.lesson_id} done={self.is_completed}"


class QuerySubmission(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    exercise = models.ForeignKey(
        "curriculum.Exercise",
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    sql_text = models.TextField()
    was_correct = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "query_submissions"
        ordering = ("-submitted_at",)
        indexes = [
            models.Index(fields=("user", "exercise")),
            models.Index(fields=("exercise", "was_correct")),
        ]

    def __str__(self):
        outcome = "✓" if self.was_correct else "✗"
        return f"{self.user_id}:{self.exercise_id} {outcome}"
