from django.urls import path

from . import views

urlpatterns = [
    path(
        "exercises/<int:pk>/submit/",
        views.ExerciseSubmitView.as_view(),
        name="exercise-submit",
    ),
    path(
        "sandbox/execute/",
        views.SandboxExecuteView.as_view(),
        name="sandbox-execute",
    ),
    path(
        "sandbox/schema/",
        views.SandboxSchemaView.as_view(),
        name="sandbox-schema",
    ),
    path(
        "sandbox/reset/",
        views.SandboxResetView.as_view(),
        name="sandbox-reset",
    ),
]
