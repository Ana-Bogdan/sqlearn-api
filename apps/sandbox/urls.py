from django.urls import path

from . import views

urlpatterns = [
    path(
        "exercises/<int:pk>/submit/",
        views.ExerciseSubmitView.as_view(),
        name="exercise-submit",
    ),
]
