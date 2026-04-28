from django.urls import path

from . import views

urlpatterns = [
    path(
        "mentor/explain-error/",
        views.ExplainErrorView.as_view(),
        name="mentor-explain-error",
    ),
    path("mentor/hint/", views.HintView.as_view(), name="mentor-hint"),
    path(
        "mentor/nl-to-sql/",
        views.NLToSQLView.as_view(),
        name="mentor-nl-to-sql",
    ),
    path(
        "admin/mentor-logs/",
        views.AdminMentorLogsView.as_view(),
        name="admin-mentor-logs",
    ),
]
