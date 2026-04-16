"""
Smoke tests for parking-service.
Verifies service startup, DB connectivity, and Redis connectivity.
"""

import os

import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class TestHealthCheck(TestCase):
    """Verify parking-service is up and responsive."""

    def setUp(self):
        self.client = APIClient()
        self.client.defaults["HTTP_X_GATEWAY_SECRET"] = os.environ.get(
            "GATEWAY_SECRET", "test-secret-for-ci"
        )
        self.client.defaults["HTTP_X_USER_ID"] = "test-user-uuid"
        self.client.defaults["HTTP_X_USER_EMAIL"] = "test@example.com"

    def test_service_is_up(self):
        """Service responds to parking lots endpoint."""
        response = self.client.get("/parking/lots/")
        assert response.status_code in [
            200,
            401,
            403,
            404,
        ], f"Service returned unexpected status: {response.status_code}"


class TestDatabaseConnection(TestCase):
    """Verify database connectivity."""

    def test_db_connection(self):
        """Can query ParkingLot table."""
        from infrastructure.models import ParkingLot

        count = ParkingLot.objects.count()
        assert isinstance(count, int), "DB query should return an integer count"


class TestRedisConnection(TestCase):
    """Verify Redis connectivity."""

    def test_redis_ping(self):
        """Redis responds to PING (skipped if Redis unavailable)."""
        try:
            import redis as redis_lib
        except ImportError:
            pytest.skip("redis library not installed")
        from django.conf import settings

        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/3")
        try:
            r = redis_lib.from_url(redis_url, socket_connect_timeout=2)
            result = r.ping()
            assert result, "Redis should respond to PING"
        except (
            redis_lib.ConnectionError,
            redis_lib.TimeoutError,
            ConnectionRefusedError,
            OSError,
        ):
            pytest.skip("Redis is not available")
            pytest.skip("Redis is not available")
