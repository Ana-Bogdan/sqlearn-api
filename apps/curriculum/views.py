from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Chapter, Exercise, Lesson
from .serializers import (
    ChapterDetailSerializer,
    ChapterListSerializer,
    ExerciseDetailSerializer,
    ExerciseHintSerializer,
    LessonDetailSerializer,
)


class ChapterListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChapterListSerializer

    def get_queryset(self):
        return (
            Chapter.objects.active()
            .with_user_progress(self.request.user)
            .order_by("order")
        )


class ChapterDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChapterDetailSerializer

    def get_queryset(self):
        return Chapter.objects.active().with_user_progress(self.request.user)


class LessonDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LessonDetailSerializer

    def get_queryset(self):
        return (
            Lesson.objects.active()
            .with_user_progress(self.request.user)
            .select_related("chapter")
        )


class ExerciseDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ExerciseDetailSerializer

    def get_queryset(self):
        return Exercise.objects.visible().with_user_status(self.request.user)


class ExerciseHintsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        exercise = get_object_or_404(Exercise.objects.visible(), pk=pk)
        hints = exercise.hints.order_by("order")
        return Response(ExerciseHintSerializer(hints, many=True).data)
