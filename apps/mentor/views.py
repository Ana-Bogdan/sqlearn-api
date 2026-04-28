"""AI Mentor HTTP endpoints.

All three views share a common pattern:
1. Validate input via a request serializer.
2. Resolve the related Exercise (when applicable).
3. Delegate to the ``mentor_service`` Singleton.
4. Translate ``RateLimitExceeded`` / ``HintCapReached`` into a 200 fallback
   response so the frontend handles every outcome through the same shape.

The Gemini-side failures (timeout, API error, missing key) are already
caught inside ``mentor_service._run`` and returned as ``available=False``
dicts, so we don't catch them again here.
"""

from __future__ import annotations

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import pagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsAdmin
from apps.curriculum.models import Exercise

from .exceptions import HintCapReached, RateLimitExceeded
from .models import AIRequestLog, MentorRequestKind, MentorRequestOutcome
from .serializers import (
    AIRequestLogSerializer,
    ExplainErrorRequestSerializer,
    HintRequestSerializer,
    MentorResponseSerializer,
    NLToSQLRequestSerializer,
)
from .service import mentor_service


def _resolve_exercise(exercise_id):
    """Return a published+active exercise or 404."""

    return get_object_or_404(
        Exercise.objects.visible(), pk=exercise_id
    )


def _rate_limit_response(exc: RateLimitExceeded) -> dict:
    return {
        "available": False,
        "message": (
            f"You've used all {settings.AI_MENTOR_RATE_LIMIT_PER_HOUR} AI "
            "Mentor requests this hour. Try the static hints, or come back "
            f"in {max(1, exc.retry_after_seconds // 60)} minutes."
        ),
        "outcome": MentorRequestOutcome.RATE_LIMITED.value,
        "retry_after_seconds": exc.retry_after_seconds,
    }


def _hint_cap_response() -> dict:
    cap = settings.AI_MENTOR_HINTS_PER_EXERCISE
    return {
        "available": False,
        "message": (
            f"You've used all {cap} AI hints for this exercise. Try writing a "
            "query and use Explain Error if it doesn't work."
        ),
        "outcome": MentorRequestOutcome.HINT_CAP_REACHED.value,
        "hint_level": cap,
        "hints_remaining": 0,
    }


class ExplainErrorView(APIView):
    """POST /api/mentor/explain-error/"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ExplainErrorRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        exercise = _resolve_exercise(data["exercise_id"])

        try:
            result = mentor_service.explain_error(
                user=request.user,
                exercise=exercise,
                user_sql=data["sql_text"],
                error_message=data["error_message"],
                history=serializer.history_as_messages(),
            )
        except RateLimitExceeded as exc:
            result = _rate_limit_response(exc)

        return Response(MentorResponseSerializer(result).data)


class HintView(APIView):
    """POST /api/mentor/hint/"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = HintRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        exercise = _resolve_exercise(data["exercise_id"])

        try:
            result = mentor_service.get_hint(
                user=request.user,
                exercise=exercise,
                user_sql=data.get("sql_text", ""),
                history=serializer.history_as_messages(),
            )
        except RateLimitExceeded as exc:
            result = _rate_limit_response(exc)
        except HintCapReached:
            result = _hint_cap_response()

        return Response(MentorResponseSerializer(result).data)


class NLToSQLView(APIView):
    """POST /api/mentor/nl-to-sql/"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = NLToSQLRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        exercise = None
        exercise_id = data.get("exercise_id")
        if exercise_id is not None:
            exercise = _resolve_exercise(exercise_id)

        try:
            result = mentor_service.nl_to_sql(
                user=request.user,
                natural_language=data["natural_language"],
                exercise=exercise,
                history=serializer.history_as_messages(),
            )
        except RateLimitExceeded as exc:
            result = _rate_limit_response(exc)

        return Response(MentorResponseSerializer(result).data)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------


class MentorLogsPagination(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


class AdminMentorLogsView(APIView):
    """GET /api/admin/mentor-logs/ — paginated, filterable AI request audit log.

    Query params (all optional):
    * ``user`` — filter by user UUID
    * ``kind`` — explain_error | hint | nl_to_sql
    * ``outcome`` — success | rate_limited | hint_cap_reached | gemini_error | timeout | invalid_input
    * ``exercise`` — filter by exercise ID
    * ``since`` / ``until`` — ISO datetimes inclusive
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        qs = AIRequestLog.objects.select_related("user", "exercise").order_by(
            "-created_at"
        )

        user_id = request.query_params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)

        kind = request.query_params.get("kind")
        if kind in {k.value for k in MentorRequestKind}:
            qs = qs.filter(kind=kind)

        outcome = request.query_params.get("outcome")
        if outcome in {o.value for o in MentorRequestOutcome}:
            qs = qs.filter(outcome=outcome)

        exercise_id = request.query_params.get("exercise")
        if exercise_id:
            qs = qs.filter(exercise_id=exercise_id)

        since = request.query_params.get("since")
        if since:
            qs = qs.filter(created_at__gte=since)

        until = request.query_params.get("until")
        if until:
            qs = qs.filter(created_at__lte=until)

        paginator = MentorLogsPagination()
        page = paginator.paginate_queryset(qs, request, view=self)

        rows = [
            {
                "id": log.id,
                "user_id": log.user_id,
                "user_email": log.user.email,
                "kind": log.kind,
                "outcome": log.outcome,
                "exercise_id": log.exercise_id,
                "exercise_title": log.exercise.title if log.exercise else None,
                "prompt_tokens": log.prompt_tokens,
                "response_tokens": log.response_tokens,
                "latency_ms": log.latency_ms,
                "created_at": log.created_at,
            }
            for log in (page or [])
        ]
        return paginator.get_paginated_response(
            AIRequestLogSerializer(rows, many=True).data
        )
