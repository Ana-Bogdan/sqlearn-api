"""Seed a test user with a fully completed chapter so the chapter quiz unlocks.

Marks every non-quiz exercise in the target chapter as ``COMPLETED`` and every
lesson in the chapter as ``is_completed=True`` for the user. The chapter quiz
itself is left untouched so it can be taken fresh.

Idempotent: re-running updates progress in place. Pass ``--reset`` to wipe the
user's existing progress for the chapter first (useful when re-testing the
quiz from a clean slate).

Examples::

    python manage.py seed_test_user
    python manage.py seed_test_user --chapter 2
    python manage.py seed_test_user --email me@example.com --password hunter2 --reset
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.curriculum.models import Chapter, Exercise, Lesson
from apps.progress.models import (
    ExerciseStatus,
    UserExerciseProgress,
    UserLessonProgress,
)
from apps.users.models import User


DEFAULT_EMAIL = "quiztester@sqlearn.dev"
DEFAULT_PASSWORD = "sqlearn123"
DEFAULT_FIRST_NAME = "Quiz"
DEFAULT_LAST_NAME = "Tester"


class Command(BaseCommand):
    help = (
        "Create or update a test user whose progress in the given chapter is "
        "fully complete except for the chapter quiz."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--chapter",
            type=int,
            default=1,
            help="Chapter `order` to complete (default: 1).",
        )
        parser.add_argument(
            "--email",
            default=DEFAULT_EMAIL,
            help=f"Login email (default: {DEFAULT_EMAIL}).",
        )
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help=f"Login password (default: {DEFAULT_PASSWORD}).",
        )
        parser.add_argument(
            "--first-name",
            default=DEFAULT_FIRST_NAME,
            help=f"User first name (default: {DEFAULT_FIRST_NAME}).",
        )
        parser.add_argument(
            "--last-name",
            default=DEFAULT_LAST_NAME,
            help=f"User last name (default: {DEFAULT_LAST_NAME}).",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete this user's existing exercise/lesson progress for the "
                "chapter before seeding. Useful when re-taking the quiz."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        chapter_order = opts["chapter"]
        email = opts["email"].strip().lower()
        password = opts["password"]

        chapter = Chapter.objects.filter(order=chapter_order, is_active=True).first()
        if chapter is None:
            raise CommandError(
                f"No active chapter found with order={chapter_order}. "
                "Run `python manage.py seed_curriculum` first."
            )

        user, user_created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": opts["first_name"],
                "last_name": opts["last_name"],
            },
        )
        # Always (re)set the password so the documented credentials work even
        # if the row pre-existed from a previous run.
        user.set_password(password)
        if not user.is_active:
            user.is_active = True
        user.save()

        lessons = list(
            Lesson.objects.filter(chapter=chapter, is_active=True).order_by("order")
        )
        # Same filter the chapter API uses (active + published, non-quiz).
        exercises = list(
            Exercise.objects.filter(
                chapter=chapter,
                is_active=True,
                is_published=True,
                is_chapter_quiz=False,
            ).order_by("lesson_id", "order")
        )
        quiz_exercises = list(
            Exercise.objects.filter(
                chapter=chapter,
                is_active=True,
                is_published=True,
                is_chapter_quiz=True,
            ).order_by("order")
        )

        if not lessons:
            raise CommandError(
                f"Chapter {chapter_order} has no active lessons. Nothing to seed."
            )
        if not exercises:
            self.stdout.write(
                self.style.WARNING(
                    "Chapter has no non-quiz exercises — only lesson progress "
                    "will be marked. Quiz unlock relies on lesson completion."
                )
            )

        if opts["reset"]:
            ex_ids = [e.id for e in exercises] + [q.id for q in quiz_exercises]
            UserExerciseProgress.objects.filter(
                user=user, exercise_id__in=ex_ids
            ).delete()
            UserLessonProgress.objects.filter(
                user=user, lesson__in=lessons
            ).delete()

        now = timezone.now()

        # Mark every non-quiz exercise in the chapter as completed.
        for exercise in exercises:
            UserExerciseProgress.objects.update_or_create(
                user=user,
                exercise=exercise,
                defaults={
                    "status": ExerciseStatus.COMPLETED,
                    "completed_at": now,
                    # Test fixture, not a real attempt — leave first_attempt
                    # True so any later real submission still counts as the
                    # "first" one for XP/badge purposes.
                    "first_attempt": True,
                },
            )

        # Mark every lesson in the chapter as completed. This is what the quiz
        # unlock check (`get_chapter_quizzes` in the chapter serializer) reads
        # directly — exercise progress alone won't unlock the quiz.
        for lesson in lessons:
            UserLessonProgress.objects.update_or_create(
                user=user,
                lesson=lesson,
                defaults={
                    "is_completed": True,
                    "completed_at": now,
                },
            )

        self._print_summary(
            user=user,
            user_created=user_created,
            chapter=chapter,
            lesson_count=len(lessons),
            exercise_count=len(exercises),
            quiz_count=len(quiz_exercises),
            email=email,
            password=password,
            reset=opts["reset"],
        )

    def _print_summary(
        self,
        *,
        user,
        user_created,
        chapter,
        lesson_count,
        exercise_count,
        quiz_count,
        email,
        password,
        reset,
    ):
        action = "Created" if user_created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} user: {user.email}"))
        self.stdout.write(f"  user_id        : {user.id}")
        self.stdout.write(f"  chapter        : {chapter.order}. {chapter.title}")
        self.stdout.write(f"  lessons done   : {lesson_count}")
        self.stdout.write(f"  exercises done : {exercise_count}")
        self.stdout.write(
            f"  quizzes ready  : {quiz_count} "
            f"({'unlocked' if quiz_count else 'none defined'})"
        )
        if reset:
            self.stdout.write(self.style.WARNING("  reset          : yes"))
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Login credentials"))
        self.stdout.write(f"  email    : {email}")
        self.stdout.write(f"  password : {password}")
