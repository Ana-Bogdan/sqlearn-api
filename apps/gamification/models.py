from django.conf import settings
from django.db import models


class BadgeCategory(models.TextChoices):
    MILESTONE = "milestone", "Milestone"
    SKILL = "skill", "Skill"
    STREAK = "streak", "Streak"
    FUN = "fun", "Fun"


class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, blank=True)
    category = models.CharField(
        max_length=20, choices=BadgeCategory.choices, db_index=True
    )
    trigger_type = models.CharField(max_length=50, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "badges"
        ordering = ("category", "id")

    def __str__(self):
        return f"{self.name} [{self.category}]"


class UserBadge(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_badges",
    )
    badge = models.ForeignKey(
        Badge, on_delete=models.CASCADE, related_name="awards"
    )
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_badges"
        ordering = ("-awarded_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "badge"), name="user_badge_unique"
            ),
        ]

    def __str__(self):
        return f"{self.user_id} ← {self.badge.trigger_type}"
