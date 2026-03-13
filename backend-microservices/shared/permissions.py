"""
Extended permission classes for ParkSmart microservices.

IsInternalService — verifies that the caller is an internal service
by checking X-Gateway-Secret header against the GATEWAY_SECRET env var.
Use this for broadcast endpoints, AI feeds, and any inter-service calls
that should NOT be accessible from the public internet.
"""
import os
from rest_framework.permissions import BasePermission


class IsInternalService(BasePermission):
    """
    Allow access only from trusted internal services.

    Checks that the request contains a valid X-Gateway-Secret header
    matching the GATEWAY_SECRET environment variable.

    Usage:
        class MyBroadcastView(APIView):
            permission_classes = [IsInternalService]
    """

    message = 'Internal service authentication required'

    def has_permission(self, request, view):
        secret = request.headers.get('X-Gateway-Secret')
        expected = os.getenv('GATEWAY_SECRET', '')
        if not expected:
            # Fail-closed: if env var is not set, deny everything
            return False
        return secret == expected
