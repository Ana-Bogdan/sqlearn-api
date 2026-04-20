import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Badge",
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
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField()),
                ("icon", models.CharField(blank=True, max_length=50)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("milestone", "Milestone"),
                            ("skill", "Skill"),
                            ("streak", "Streak"),
                            ("fun", "Fun"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("trigger_type", models.CharField(max_length=50, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "badges",
                "ordering": ("category", "id"),
            },
        ),
        migrations.CreateModel(
            name="UserBadge",
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
                ("awarded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "badge",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="awards",
                        to="gamification.badge",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_badges",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "user_badges",
                "ordering": ("-awarded_at",),
                "constraints": [
                    models.UniqueConstraint(
                        fields=("user", "badge"), name="user_badge_unique"
                    ),
                ],
            },
        ),
    ]
