from django.contrib import admin

from .models import Chapter, Exercise, ExerciseHint, Lesson


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ("order", "title", "is_active")
    ordering = ("order",)
    show_change_link = True


class ExerciseHintInline(admin.TabularInline):
    model = ExerciseHint
    extra = 0
    fields = ("order", "hint_text")
    ordering = ("order",)


class ExerciseInline(admin.TabularInline):
    model = Exercise
    extra = 0
    fk_name = "lesson"
    fields = ("order", "title", "difficulty", "is_published", "is_active")
    ordering = ("order",)
    show_change_link = True


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("order", "title", "is_active", "created_at")
    list_filter = ("is_active",)
    ordering = ("order",)
    search_fields = ("title",)
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("chapter", "order", "title", "is_active")
    list_filter = ("is_active", "chapter")
    ordering = ("chapter__order", "order")
    search_fields = ("title",)
    inlines = [ExerciseInline]


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "chapter",
        "lesson",
        "difficulty",
        "is_chapter_quiz",
        "is_published",
        "is_active",
        "order",
    )
    list_filter = ("difficulty", "is_chapter_quiz", "is_published", "is_active", "chapter")
    search_fields = ("title", "instructions")
    inlines = [ExerciseHintInline]
    fieldsets = (
        (None, {"fields": ("chapter", "lesson", "title", "instructions", "order")}),
        ("Difficulty & flags", {"fields": ("difficulty", "is_chapter_quiz", "is_published", "is_active")}),
        ("Solution", {"fields": ("starter_code", "solution_query", "expected_result")}),
    )


@admin.register(ExerciseHint)
class ExerciseHintAdmin(admin.ModelAdmin):
    list_display = ("exercise", "order", "hint_text")
    list_filter = ("exercise__chapter",)
    ordering = ("exercise_id", "order")
