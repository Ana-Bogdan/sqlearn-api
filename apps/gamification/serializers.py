from __future__ import annotations

from rest_framework import serializers

from .levels import next_threshold, threshold_for_level, title_for_level
from .models import Badge, UserBadge


class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ("id", "trigger_type", "name", "description", "icon", "category")


class BadgeWithStatusSerializer(serializers.ModelSerializer):
    earned = serializers.BooleanField()
    awarded_at = serializers.DateTimeField(allow_null=True)

    class Meta:
        model = Badge
        fields = (
            "id",
            "trigger_type",
            "name",
            "description",
            "icon",
            "category",
            "earned",
            "awarded_at",
        )


class UserBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer()

    class Meta:
        model = UserBadge
        fields = ("badge", "awarded_at")


class LeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    id = serializers.UUIDField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    level = serializers.IntegerField()
    xp = serializers.IntegerField()
    badge_count = serializers.IntegerField()


class PublicProfileSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    level = serializers.IntegerField()
    level_title = serializers.CharField()
    xp = serializers.IntegerField()
    current_streak = serializers.IntegerField()
    longest_streak = serializers.IntegerField()
    exercises_completed = serializers.IntegerField()
    badges_earned = serializers.IntegerField()
    next_level_xp = serializers.IntegerField(allow_null=True)
    badges = UserBadgeSerializer(many=True)


class ProgressSummarySerializer(serializers.Serializer):
    xp = serializers.IntegerField()
    level = serializers.IntegerField()
    level_title = serializers.CharField()
    level_start_xp = serializers.IntegerField()
    next_level_xp = serializers.IntegerField(allow_null=True)
    current_streak = serializers.IntegerField()
    longest_streak = serializers.IntegerField()
    total_chapters = serializers.IntegerField()
    completed_chapters = serializers.IntegerField()
    total_lessons = serializers.IntegerField()
    completed_lessons = serializers.IntegerField()
    total_exercises = serializers.IntegerField()
    completed_exercises = serializers.IntegerField()
    badges_earned = serializers.IntegerField()
    total_badges = serializers.IntegerField()


def build_level_metadata(level: int) -> dict:
    return {
        "level_title": title_for_level(level),
        "level_start_xp": threshold_for_level(level),
        "next_level_xp": next_threshold(level),
    }
