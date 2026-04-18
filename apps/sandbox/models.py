from django.db import models


class SandboxSchema(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    schema_sql = models.TextField(
        help_text="DDL + INSERT statements that set up this dataset."
    )
    is_playground = models.BooleanField(
        default=False,
        help_text="Used by the free-play sandbox page when true.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sandbox_schemas"
        ordering = ("name",)

    def __str__(self):
        return self.name


class ExerciseDataset(models.Model):
    exercise = models.ForeignKey(
        "curriculum.Exercise",
        on_delete=models.CASCADE,
        related_name="datasets",
    )
    sandbox_schema = models.ForeignKey(
        SandboxSchema, on_delete=models.PROTECT, related_name="exercise_datasets"
    )

    class Meta:
        db_table = "exercise_datasets"
        constraints = [
            models.UniqueConstraint(
                fields=("exercise", "sandbox_schema"),
                name="dataset_unique_per_exercise_schema",
            ),
        ]

    def __str__(self):
        return f"{self.exercise_id} ↔ {self.sandbox_schema.name}"
