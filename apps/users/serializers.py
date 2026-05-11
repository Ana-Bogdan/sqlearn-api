from django.contrib.auth import get_user_model, password_validation
from rest_framework import serializers

User = get_user_model()


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name")

    def validate_first_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Enter your first name.")
        return cleaned

    def validate_last_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Enter your last name.")
        return cleaned


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    new_password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )

    def validate_current_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("That doesn't match your current password.")
        return value

    def validate_new_password(self, value: str) -> str:
        user = self.context["request"].user
        password_validation.validate_password(value, user=user)
        return value

    def validate(self, attrs):
        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "Choose a password different from your current one."}
            )
        return attrs
