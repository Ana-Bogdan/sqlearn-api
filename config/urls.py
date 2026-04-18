from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", include("apps.health.urls")),
    path("api/auth/", include("apps.authentication.urls")),
    path("api/", include("apps.curriculum.urls")),
]
