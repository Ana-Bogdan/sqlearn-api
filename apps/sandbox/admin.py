from django.contrib import admin

from .models import ExerciseDataset, SandboxQueryAttempt, SandboxSchema


@admin.register(SandboxSchema)
class SandboxSchemaAdmin(admin.ModelAdmin):
    list_display = ("name", "is_playground", "created_at")
    list_filter = ("is_playground",)
    search_fields = ("name", "description")


@admin.register(ExerciseDataset)
class ExerciseDatasetAdmin(admin.ModelAdmin):
    list_display = ("exercise", "sandbox_schema")
    list_filter = ("sandbox_schema",)
    search_fields = ("exercise__title", "sandbox_schema__name")
    autocomplete_fields = ("exercise", "sandbox_schema")


@admin.register(SandboxQueryAttempt)
class SandboxQueryAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "succeeded", "created_at")
    list_filter = ("succeeded",)
    search_fields = ("user__email", "sql_text")
    readonly_fields = ("created_at",)
