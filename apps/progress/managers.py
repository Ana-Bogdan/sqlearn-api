from __future__ import annotations

from django.db import models


class UserExerciseProgressQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(user=user)

    def completed(self):
        from .models import ExerciseStatus

        return self.filter(status=ExerciseStatus.COMPLETED)


class UserProgressManager(models.Manager.from_queryset(UserExerciseProgressQuerySet)):
    def get_completion_status(self, user, exercise) -> str:
        """Return the user's current status for an exercise, or 'not_started'."""
        from .models import ExerciseStatus

        if user is None or not user.is_authenticated:
            return ExerciseStatus.NOT_STARTED

        row = (
            self.get_queryset()
            .filter(user=user, exercise=exercise)
            .values_list("status", flat=True)
            .first()
        )
        return row or ExerciseStatus.NOT_STARTED
