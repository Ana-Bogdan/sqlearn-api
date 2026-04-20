from django.contrib import admin

from .models import Badge, UserBadge


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "trigger_type", "icon")
    list_filter = ("category",)
    search_fields = ("name", "trigger_type")
    readonly_fields = ("created_at",)


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "awarded_at")
    list_filter = ("badge__category",)
    search_fields = ("user__email", "badge__name", "badge__trigger_type")
    autocomplete_fields = ("user", "badge")
    readonly_fields = ("awarded_at",)
