from django.contrib import admin

from .models import AIRequestLog


@admin.register(AIRequestLog)
class AIRequestLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "kind",
        "outcome",
        "exercise",
        "prompt_tokens",
        "response_tokens",
        "latency_ms",
    )
    list_filter = ("kind", "outcome", "created_at")
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "exercise__title",
    )
    autocomplete_fields = ("user", "exercise")
    readonly_fields = (
        "user",
        "kind",
        "outcome",
        "exercise",
        "prompt_tokens",
        "response_tokens",
        "latency_ms",
        "created_at",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        # Logs are append-only via the service; never created in admin.
        return False
