from django.urls import path

from . import views

urlpatterns = [
    path("chapters/", views.ChapterListView.as_view(), name="chapter-list"),
    path("chapters/<int:pk>/", views.ChapterDetailView.as_view(), name="chapter-detail"),
    path("lessons/<int:pk>/", views.LessonDetailView.as_view(), name="lesson-detail"),
    path("exercises/<int:pk>/", views.ExerciseDetailView.as_view(), name="exercise-detail"),
    path(
        "exercises/<int:pk>/hints/",
        views.ExerciseHintsView.as_view(),
        name="exercise-hints",
    ),
]
