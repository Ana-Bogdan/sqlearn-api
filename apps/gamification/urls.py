from django.urls import path

from . import views

urlpatterns = [
    path("leaderboard/", views.LeaderboardView.as_view(), name="leaderboard"),
    path("badges/", views.BadgesListView.as_view(), name="badges-list"),
    path(
        "users/me/progress/",
        views.MyProgressView.as_view(),
        name="my-progress",
    ),
    path(
        "users/<uuid:user_id>/profile/",
        views.PublicProfileView.as_view(),
        name="public-profile",
    ),
]
