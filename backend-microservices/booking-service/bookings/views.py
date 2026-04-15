"""
Views for booking-service — CRUD operations.

Lifecycle actions are in views_lifecycle.py
Payment actions are in views_payment.py
Query endpoints are in views_query.py
"""

import logging

from rest_framework import status, viewsets
from rest_framework.response import Response
from shared.gateway_permissions import IsGatewayAuthenticated

from . import services
from .events import create_booking_event, create_slot_event
from .models import Booking, PackagePricing
from .serializers import (
    BookingSerializer,
    CreateBookingSerializer,
    PackagePricingSerializer,
)

logger = logging.getLogger(__name__)


class PackagePricingViewSet(viewsets.ModelViewSet):
    """ViewSet for PackagePricing."""

    queryset = PackagePricing.objects.all()
    serializer_class = PackagePricingSerializer
    permission_classes = [IsGatewayAuthenticated]


class BookingViewSet(viewsets.ModelViewSet):
    """ViewSet for Booking CRUD operations."""

    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsGatewayAuthenticated]

    def get_serializer_class(self):
        """Use CreateBookingSerializer for POST, BookingSerializer for GET."""
        if self.action == "create":
            return CreateBookingSerializer
        return BookingSerializer

    def get_queryset(self):
        """Filter bookings by current user from gateway headers."""
        user_id = getattr(self.request, "user_id", None)
        if user_id == "system":
            return Booking.objects.all()
        if user_id:
            return Booking.objects.filter(user_id=user_id)
        return Booking.objects.none()

    def create(self, request, *args, **kwargs):
        """Create booking and return full BookingSerializer response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        if booking.slot_id:
            create_slot_event(booking.slot_id, "reserved", booking)
        create_booking_event("booking.created", booking)

        services.create_payment_for_booking(booking)

        output_serializer = BookingSerializer(booking)
        return Response(
            {
                "booking": output_serializer.data,
                "message": "Booking created successfully",
                "qrCode": booking.qr_code_data,
            },
            status=status.HTTP_201_CREATED,
        )
