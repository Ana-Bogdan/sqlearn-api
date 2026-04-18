from rest_framework import serializers


class SubmitQuerySerializer(serializers.Serializer):
    sql_text = serializers.CharField(
        max_length=10_000,
        allow_blank=False,
        trim_whitespace=False,
    )

    def validate_sql_text(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("SQL text is required.")
        return cleaned
