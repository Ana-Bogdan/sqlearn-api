from django.urls import path

from . import views

urlpatterns = [
    path("users/me/", views.MeUpdateView.as_view(), name="users-me"),
    path(
        "users/me/password/",
        views.ChangePasswordView.as_view(),
        name="users-me-password",
    ),
]
