import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("curriculum", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AIRequestLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("explain_error", "Explain Error"),
                            ("hint", "Hint"),
                            ("nl_to_sql", "Natural Language to SQL"),
                        ],
                        db_index=True,
                        max_length=32,
                    ),
                ),
                (
                    "outcome",
                    models.CharField(
                        choices=[
                            ("success", "Success"),
                            ("rate_limited", "Rate Limited"),
                            ("hint_cap_reached", "Hint Cap Reached"),
                            ("gemini_error", "Gemini Error"),
                            ("timeout", "Timeout"),
                            ("invalid_input", "Invalid Input"),
                        ],
                        db_index=True,
                        default="success",
                        max_length=32,
                    ),
                ),
                ("prompt_tokens", models.PositiveIntegerField(default=0)),
                ("response_tokens", models.PositiveIntegerField(default=0)),
                ("latency_ms", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "exercise",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mentor_requests",
                        to="curriculum.exercise",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mentor_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "ai_request_logs",
                "ordering": ("-created_at",),
                "indexes": [
                    models.Index(
                        fields=["user", "created_at"],
                        name="mentor_log_user_time_idx",
                    ),
                    models.Index(
                        fields=["user", "exercise", "kind"],
                        name="mentor_log_user_ex_kind_idx",
                    ),
                ],
            },
        ),
    ]
