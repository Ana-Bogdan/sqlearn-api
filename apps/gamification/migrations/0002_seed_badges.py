from django.db import migrations

BADGE_SEED = [
    # Milestone
    {
        "trigger_type": "first_query",
        "name": "First Query",
        "description": "Complete your first exercise.",
        "icon": "sparkles",
        "category": "milestone",
    },
    {
        "trigger_type": "chapter_initiate",
        "name": "Chapter Initiate",
        "description": "Complete your first chapter.",
        "icon": "book-open",
        "category": "milestone",
    },
    {
        "trigger_type": "halfway_there",
        "name": "Halfway There",
        "description": "Complete 4 chapters.",
        "icon": "milestone",
        "category": "milestone",
    },
    {
        "trigger_type": "curriculum_complete",
        "name": "Curriculum Complete",
        "description": "Complete all 8 chapters.",
        "icon": "trophy",
        "category": "milestone",
    },
    # Skill
    {
        "trigger_type": "perfectionist",
        "name": "Perfectionist",
        "description": "Complete any 5 exercises on the first attempt.",
        "icon": "target",
        "category": "skill",
    },
    {
        "trigger_type": "join_master",
        "name": "Join Master",
        "description": "Complete all exercises in the Joins chapter.",
        "icon": "link",
        "category": "skill",
    },
    {
        "trigger_type": "subquery_sage",
        "name": "Subquery Sage",
        "description": "Complete all exercises in the Subqueries chapter.",
        "icon": "brackets",
        "category": "skill",
    },
    {
        "trigger_type": "data_surgeon",
        "name": "Data Surgeon",
        "description": "Complete all exercises in the Modifying Data chapter.",
        "icon": "scalpel",
        "category": "skill",
    },
    {
        "trigger_type": "quiz_ace",
        "name": "Quiz Ace",
        "description": "Complete any 3 chapter quizzes on the first attempt.",
        "icon": "award",
        "category": "skill",
    },
    # Streak
    {
        "trigger_type": "streak_3",
        "name": "3-Day Streak",
        "description": "Maintain a 3-day daily streak.",
        "icon": "flame",
        "category": "streak",
    },
    {
        "trigger_type": "streak_7",
        "name": "7-Day Streak",
        "description": "Maintain a 7-day daily streak.",
        "icon": "flame",
        "category": "streak",
    },
    {
        "trigger_type": "streak_30",
        "name": "30-Day Streak",
        "description": "Maintain a 30-day daily streak.",
        "icon": "flame",
        "category": "streak",
    },
    # Fun
    {
        "trigger_type": "night_owl",
        "name": "Night Owl",
        "description": "Complete an exercise between midnight and 5 AM (EEST).",
        "icon": "moon",
        "category": "fun",
    },
    {
        "trigger_type": "speed_demon",
        "name": "Speed Demon",
        "description": "Complete an exercise in under 30 seconds.",
        "icon": "zap",
        "category": "fun",
    },
    {
        "trigger_type": "brain_twister",
        "name": "Brain Twister",
        "description": "Complete an exercise after spending 10+ minutes on it.",
        "icon": "brain",
        "category": "fun",
    },
    {
        "trigger_type": "sandbox_explorer",
        "name": "Sandbox Explorer",
        "description": "Run 20 queries in the free sandbox.",
        "icon": "compass",
        "category": "fun",
    },
]


def seed_badges(apps, schema_editor):
    Badge = apps.get_model("gamification", "Badge")
    for data in BADGE_SEED:
        Badge.objects.update_or_create(
            trigger_type=data["trigger_type"],
            defaults={
                "name": data["name"],
                "description": data["description"],
                "icon": data["icon"],
                "category": data["category"],
            },
        )


def unseed_badges(apps, schema_editor):
    Badge = apps.get_model("gamification", "Badge")
    triggers = [b["trigger_type"] for b in BADGE_SEED]
    Badge.objects.filter(trigger_type__in=triggers).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("gamification", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_badges, reverse_code=unseed_badges),
    ]
