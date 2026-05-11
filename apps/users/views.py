from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.cookies import set_auth_cookies
from apps.authentication.serializers import UserSerializer

from .serializers import ChangePasswordSerializer, UpdateProfileSerializer


@method_decorator(csrf_protect, name="patch")
class MeUpdateView(APIView):
    """PATCH /api/users/me/ — update the current user's profile."""

    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = UpdateProfileSerializer(
            instance=request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


@method_decorator(csrf_protect, name="put")
class ChangePasswordView(APIView):
    """PUT /api/users/me/password/ — change the current user's password.

    Rotates the JWT pair so the active session keeps working after the
    password is replaced.
    """

    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])

        refresh = RefreshToken.for_user(user)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        set_auth_cookies(
            response,
            access_token=str(refresh.access_token),
            refresh_token=str(refresh),
        )
        return response
