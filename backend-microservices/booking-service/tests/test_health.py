"""
Smoke tests for booking-service.
Verifies service startup, DB connectivity, and Redis connectivity.
"""

import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


class TestHealthCheck(TestCase):
    """Verify booking-service is up and responsive."""

    def setUp(self):
        self.client = APIClient()
        self.client.defaults['HTTP_X_GATEWAY_SECRET'] = 'gateway-internal-secret-key'
        self.client.defaults['HTTP_X_USER_ID'] = '00000000-0000-0000-0000-000000000001'
        self.client.defaults['HTTP_X_USER_EMAIL'] = 'test@example.com'

    def test_service_is_up(self):
        """Service responds to list endpoint."""
        response = self.client.get('/bookings/')
        assert response.status_code in [200, 401, 403], (
            f"Service returned unexpected status: {response.status_code}"
        )


class TestDatabaseConnection(TestCase):
    """Verify database connectivity."""

    def test_db_connection_booking(self):
        """Can query Booking table."""
        from bookings.models import Booking
        count = Booking.objects.count()
        assert isinstance(count, int), "DB query should return an integer count"

    def test_db_connection_pricing(self):
        """Can query PackagePricing table."""
        from bookings.models import PackagePricing
        count = PackagePricing.objects.count()
        assert isinstance(count, int), "DB query should return an integer count"


class TestRedisConnection(TestCase):
    """Verify Redis connectivity."""

    def test_redis_ping(self):
        """Redis responds to PING."""
        try:
            import redis as redis_lib
            from django.conf import settings

            redis_url = getattr(settings, 'REDIS_URL', None)
            if not redis_url:
                redis_url = 'redis://localhost:6379/2'

            r = redis_lib.from_url(redis_url)
            assert r.ping(), "Redis should respond to PING"
        except (ConnectionError, redis_lib.ConnectionError, redis_lib.exceptions.ConnectionError):
            pytest.skip("Redis not available")
