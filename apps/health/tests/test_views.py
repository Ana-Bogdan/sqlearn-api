"""Tests for the health-check endpoint."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class HealthCheckViewTests(APITestCase):
    def test_health_check_is_public_and_reports_db(self):
        resp = self.client.get(reverse("health-check"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["database"], "healthy")
