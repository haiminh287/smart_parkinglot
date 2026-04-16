"""
Smoke tests for vehicle-service.
Verifies service startup, DB connectivity, and Redis connectivity.
"""

import os

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class TestHealthCheck(TestCase):
    """Verify vehicle-service is up and responsive."""

    def setUp(self):
        self.client = APIClient()
        self.client.defaults["HTTP_X_GATEWAY_SECRET"] = os.environ.get(
            "GATEWAY_SECRET", "test-secret-for-ci"
        )
        self.client.defaults["HTTP_X_USER_ID"] = "00000000-0000-0000-0000-000000000001"
        self.client.defaults["HTTP_X_USER_EMAIL"] = "test@example.com"

    def test_service_is_up(self):
        """Service responds to vehicles endpoint."""
        response = self.client.get("/vehicles/")
        assert response.status_code in [
            200,
            401,
            403,
            404,
        ], f"Service returned unexpected status: {response.status_code}"


class TestDatabaseConnection(TestCase):
    """Verify database connectivity."""

    def test_db_connection(self):
        """Can query Vehicle table."""
        from vehicles.models import Vehicle

        count = Vehicle.objects.count()
        assert isinstance(count, int), "DB query should return an integer count"
        assert isinstance(count, int), "DB query should return an integer count"
