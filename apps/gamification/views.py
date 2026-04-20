from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import pagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.curriculum.models import Chapter, Exercise, Lesson
from apps.progress.models import (
    ExerciseStatus,
    UserExerciseProgress,
    UserLessonProgress,
)

from .levels import next_threshold, threshold_for_level, title_for_level
from .models import Badge, UserBadge
from .serializers import (
    BadgeWithStatusSerializer,
    LeaderboardEntrySerializer,
    ProgressSummarySerializer,
    PublicProfileSerializer,
    UserBadgeSerializer,
)

User = get_user_model()


class LeaderboardPagination(pagination.PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class LeaderboardView(APIView):
    """GET /api/leaderboard/ — paginated top learners by XP.

    The current user's rank is always included in the response, even when they
    fall outside the paginated window."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            User.objects.filter(is_active=True)
            .annotate(
                badge_count=Count("user_badges", distinct=True),
            )
            .order_by("-xp", "id")
        )

        paginator = LeaderboardPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        start_index = (
            (paginator.page.number - 1) * paginator.page_size
            if paginator.page
            else 0
        )

        entries = [
            {
                "rank": start_index + idx + 1,
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "level": user.level,
                "xp": user.xp,
                "badge_count": user.badge_count,
            }
            for idx, user in enumerate(page or [])
        ]

        current_rank = _rank_for_user(request.user)
        current_user_entry = {
            "rank": current_rank,
            "id": request.user.id,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "level": request.user.level,
            "xp": request.user.xp,
            "badge_count": UserBadge.objects.filter(user=request.user).count(),
        }

        response = paginator.get_paginated_response(
            LeaderboardEntrySerializer(entries, many=True).data
        )
        response.data["current_user"] = LeaderboardEntrySerializer(
            current_user_entry
        ).data
        return response


def _rank_for_user(user) -> int:
    higher = User.objects.filter(is_active=True).filter(
        Q(xp__gt=user.xp) | Q(xp=user.xp, id__lt=user.id)
    ).count()
    return higher + 1


class BadgesListView(APIView):
    """GET /api/badges/ — every badge with earned status for the caller."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        owned = {
            ub.badge_id: ub.awarded_at
            for ub in UserBadge.objects.filter(user=request.user)
        }
        rows = []
        for badge in Badge.objects.order_by("category", "id"):
            rows.append(
                {
                    "id": badge.id,
                    "trigger_type": badge.trigger_type,
                    "name": badge.name,
                    "description": badge.description,
                    "icon": badge.icon,
                    "category": badge.category,
                    "earned": badge.id in owned,
                    "awarded_at": owned.get(badge.id),
                }
            )
        return Response(BadgeWithStatusSerializer(rows, many=True).data)


class PublicProfileView(APIView):
    """GET /api/users/{id}/profile/ — public stats for any active user."""

    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id, is_active=True)

        exercises_completed = UserExerciseProgress.objects.filter(
            user=user, status=ExerciseStatus.COMPLETED
        ).count()
        badges = (
            UserBadge.objects.filter(user=user)
            .select_related("badge")
            .order_by("-awarded_at")
        )

        payload = {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "level": user.level,
            "level_title": title_for_level(user.level),
            "xp": user.xp,
            "current_streak": user.current_streak,
            "longest_streak": user.longest_streak,
            "exercises_completed": exercises_completed,
            "badges_earned": badges.count(),
            "next_level_xp": next_threshold(user.level),
            "badges": UserBadgeSerializer(badges, many=True).data,
        }
        return Response(PublicProfileSerializer(payload).data)


class MyProgressView(APIView):
    """GET /api/users/me/progress/ — aggregate dashboard payload."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        total_chapters = Chapter.objects.active().count()
        total_lessons = Lesson.objects.active().count()
        total_exercises = Exercise.objects.visible().count()

        completed_exercises = UserExerciseProgress.objects.filter(
            user=user, status=ExerciseStatus.COMPLETED
        ).count()
        completed_lessons = UserLessonProgress.objects.filter(
            user=user, is_completed=True
        ).count()

        chapter_counts = (
            Chapter.objects.active()
            .annotate(
                total=Count(
                    "exercises",
                    filter=Q(
                        exercises__is_active=True,
                        exercises__is_published=True,
                    ),
                    distinct=True,
                ),
                done=Count(
                    "exercises__user_progress",
                    filter=Q(
                        exercises__is_active=True,
                        exercises__is_published=True,
                        exercises__user_progress__user=user,
                        exercises__user_progress__status=ExerciseStatus.COMPLETED,
                    ),
                    distinct=True,
                ),
            )
            .values_list("total", "done")
        )
        completed_chapters = sum(
            1 for total, done in chapter_counts if total > 0 and done >= total
        )

        payload = {
            "xp": user.xp,
            "level": user.level,
            "level_title": title_for_level(user.level),
            "level_start_xp": threshold_for_level(user.level),
            "next_level_xp": next_threshold(user.level),
            "current_streak": user.current_streak,
            "longest_streak": user.longest_streak,
            "total_chapters": total_chapters,
            "completed_chapters": completed_chapters,
            "total_lessons": total_lessons,
            "completed_lessons": completed_lessons,
            "total_exercises": total_exercises,
            "completed_exercises": completed_exercises,
            "badges_earned": UserBadge.objects.filter(user=user).count(),
            "total_badges": Badge.objects.count(),
        }
        return Response(ProgressSummarySerializer(payload).data)
