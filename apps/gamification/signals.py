"""Observer — one custom Django signal with two independent receivers.

``exercise_completed`` fires once per exercise per user, the first time the
completion transition happens. The view that handles submission is responsible
for dispatching it so gamification never runs twice for the same completion.

Receivers:
* ``_run_gamification``      — delegates to ``GamificationFacade``. Its dict
                                response is collected via ``send()`` return
                                value and surfaced back to the API caller.
* ``_update_lesson_progress`` — marks ``UserLessonProgress.is_completed`` when
                                every non-quiz exercise in the lesson is done.
"""

from __future__ import annotations

from django.dispatch import Signal, receiver
from django.utils import timezone

exercise_completed = Signal()


@receiver(exercise_completed)
def _run_gamification(sender, *, user, exercise, progress, **kwargs) -> dict:
    from .facade import GamificationFacade

    return GamificationFacade().process_exercise_completion(
        user,
        exercise,
        was_first_attempt=progress.first_attempt,
        completed_at=progress.completed_at,
        started_at=progress.created_at,
    )


@receiver(exercise_completed)
def _update_lesson_progress(sender, *, user, exercise, progress, **kwargs) -> None:
    from apps.curriculum.models import Exercise
    from apps.progress.models import ExerciseStatus, UserExerciseProgress, UserLessonProgress

    if exercise.lesson_id is None:
        return

    total_exercises = (
        Exercise.objects.visible()
        .filter(lesson_id=exercise.lesson_id, is_chapter_quiz=False)
        .count()
    )
    if total_exercises == 0:
        return

    completed_exercises = UserExerciseProgress.objects.filter(
        user=user,
        status=ExerciseStatus.COMPLETED,
        exercise__lesson_id=exercise.lesson_id,
        exercise__is_active=True,
        exercise__is_published=True,
        exercise__is_chapter_quiz=False,
    ).count()

    lesson_progress, _ = UserLessonProgress.objects.get_or_create(
        user=user, lesson_id=exercise.lesson_id
    )
    if (
        completed_exercises >= total_exercises
        and not lesson_progress.is_completed
    ):
        lesson_progress.is_completed = True
        lesson_progress.completed_at = timezone.now()
        lesson_progress.save(update_fields=["is_completed", "completed_at"])


def dispatch_exercise_completed(user, exercise, progress) -> dict | None:
    """Fire the signal and return the first receiver response that looks like a
    gamification result. Keeps call sites (``ExerciseSubmitView``) tidy."""
    responses = exercise_completed.send(
        sender=None, user=user, exercise=exercise, progress=progress
    )
    for _receiver, response in responses:
        if isinstance(response, dict):
            return response
    return None
