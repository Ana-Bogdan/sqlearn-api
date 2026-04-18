from django.contrib import admin

from .models import QuerySubmission, UserExerciseProgress, UserLessonProgress


@admin.register(UserExerciseProgress)
class UserExerciseProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "exercise", "status", "first_attempt", "completed_at")
    list_filter = ("status", "first_attempt")
    search_fields = ("user__email", "exercise__title")
    autocomplete_fields = ("user", "exercise")
    readonly_fields = ("created_at", "updated_at")


@admin.register(UserLessonProgress)
class UserLessonProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "is_completed", "completed_at")
    list_filter = ("is_completed",)
    search_fields = ("user__email", "lesson__title")
    autocomplete_fields = ("user", "lesson")


@admin.register(QuerySubmission)
class QuerySubmissionAdmin(admin.ModelAdmin):
    list_display = ("user", "exercise", "was_correct", "submitted_at")
    list_filter = ("was_correct",)
    search_fields = ("user__email", "exercise__title", "sql_text")
    autocomplete_fields = ("user", "exercise")
    readonly_fields = ("submitted_at",)
