from rest_framework.permissions import BasePermission

from apps.users.models import UserRole


class IsAdmin(BasePermission):
    """Allow only authenticated users with the admin role."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == UserRole.ADMIN)
