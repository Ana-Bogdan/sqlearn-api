from django.urls import path

from . import views

app_name = "admin_api"

urlpatterns = [
    # Chapters
    path(
        "chapters/",
        views.AdminChapterListCreateView.as_view(),
        name="chapter-list",
    ),
    path(
        "chapters/<int:pk>/",
        views.AdminChapterDetailView.as_view(),
        name="chapter-detail",
    ),
    path(
        "chapters/<int:pk>/reorder/",
        views.AdminChapterReorderView.as_view(),
        name="chapter-reorder",
    ),
    # Lessons
    path(
        "lessons/",
        views.AdminLessonCreateView.as_view(),
        name="lesson-create",
    ),
    path(
        "lessons/<int:pk>/",
        views.AdminLessonDetailView.as_view(),
        name="lesson-detail",
    ),
    # Exercises
    path(
        "exercises/",
        views.AdminExerciseCreateView.as_view(),
        name="exercise-create",
    ),
    path(
        "exercises/<int:pk>/",
        views.AdminExerciseDetailView.as_view(),
        name="exercise-detail",
    ),
    path(
        "exercises/<int:pk>/test-solution/",
        views.AdminExerciseTestSolutionView.as_view(),
        name="exercise-test-solution",
    ),
    # Datasets
    path(
        "datasets/",
        views.AdminDatasetListCreateView.as_view(),
        name="dataset-list",
    ),
    path(
        "datasets/<int:pk>/",
        views.AdminDatasetDetailView.as_view(),
        name="dataset-detail",
    ),
    # Badges
    path(
        "badges/",
        views.AdminBadgeListView.as_view(),
        name="badge-list",
    ),
    path(
        "badges/<int:pk>/",
        views.AdminBadgeDetailView.as_view(),
        name="badge-detail",
    ),
    # Users
    path(
        "users/",
        views.AdminUserListView.as_view(),
        name="user-list",
    ),
    path(
        "users/<uuid:pk>/",
        views.AdminUserDetailView.as_view(),
        name="user-detail",
    ),
    # Stats
    path("stats/", views.AdminStatsView.as_view(), name="stats"),
]
