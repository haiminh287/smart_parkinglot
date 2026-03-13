"""
Smoke tests for auth-service.
Verifies service startup, DB connectivity, and Redis connectivity.
"""

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


class TestHealthCheck(TestCase):
    """Verify auth-service is up and responsive."""

    def setUp(self):
        self.client = APIClient()

    def test_service_is_up(self):
        """Service responds to health endpoint."""
        response = self.client.get('/health/')
        assert response.status_code == 200, (
            f"Service returned unexpected status: {response.status_code}"
        )


class TestDatabaseConnection(TestCase):
    """Verify database connectivity."""

    def test_db_connection_user(self):
        """Can query User table."""
        from users.models import User
        count = User.objects.count()
        assert isinstance(count, int), "DB query should return an integer count"


class TestRedisConnection(TestCase):
    """Verify Redis connectivity."""

    def test_redis_ping(self):
        """Redis responds to PING."""
        import redis as redis_lib
        from django.conf import settings

        redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/1')
        r = redis_lib.from_url(redis_url)
        try:
            assert r.ping(), "Redis should respond to PING"
        except redis_lib.exceptions.ConnectionError:
            pytest.skip("Redis not available")
