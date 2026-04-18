from django.contrib import admin

from .models import ExerciseDataset, SandboxSchema


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
