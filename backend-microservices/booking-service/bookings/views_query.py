"""
Query/read-only views for booking-service.
"""

import logging

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from shared.gateway_permissions import IsGatewayAuthenticated

from . import services
from .models import Booking
from .serializers import BookingSerializer

logger = logging.getLogger(__name__)


class BookingQueryViewSet(viewsets.GenericViewSet):
    """Read-only query endpoints for bookings."""

    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsGatewayAuthenticated]

    def get_queryset(self):
        user_id = getattr(self.request, "user_id", None)
        if user_id == "system":
            return Booking.objects.all()
        if user_id:
            return Booking.objects.filter(user_id=user_id)
        return Booking.objects.none()

    @action(detail=False, methods=["get"], url_path="current-parking")
    def current_parking(self, request):
        """Get current parking session with live cost."""
        booking = Booking.objects.filter(
            user_id=request.user_id, check_in_status="checked_in"
        ).first()

        if not booking:
            return Response(
                {"detail": "No active parking session"},
                status=status.HTTP_404_NOT_FOUND,
            )

        cost_info = services.calculate_current_cost(booking)
        serializer = self.get_serializer(booking)
        return Response(
            {
                "booking": serializer.data,
                "duration": cost_info["duration_minutes"],
                "currentCost": cost_info["current_cost"],
                "hoursParked": cost_info["hours_parked"],
                "billableHours": cost_info["billable_hours"],
                "pricePerHour": float(cost_info["hourly_rate"]),
                "message": "Current parking session",
            }
        )

    @action(detail=False, methods=["get"])
    def current(self, request):
        """Get current parking session (alias for current-parking)."""
        booking = Booking.objects.filter(
            user_id=request.user_id, check_in_status="checked_in"
        ).first()

        if not booking:
            return Response(
                {"detail": "No active parking session"},
                status=status.HTTP_404_NOT_FOUND,
            )

        cost_info = services.calculate_current_cost(booking)
        serializer = self.get_serializer(booking)
        return Response(
            {
                "booking": serializer.data,
                "duration_minutes": cost_info["duration_minutes"],
                "current_cost": cost_info["current_cost"],
            }
        )

    @action(detail=False, methods=["get"], url_path="upcoming")
    def upcoming_bookings(self, request):
        """Get upcoming bookings (not checked in yet)."""
        bookings_qs = Booking.objects.filter(
            user_id=request.user_id,
            check_in_status="not_checked_in",
            start_time__gte=timezone.now(),
        ).order_by("start_time")

        count = bookings_qs.count()
        bookings = bookings_qs[:5]

        serializer = self.get_serializer(bookings, many=True)
        return Response(
            {"results": serializer.data, "count": count, "message": "Upcoming bookings"}
        )

    @action(detail=False, methods=["get"], url_path="stats")
    def booking_stats(self, request):
        """Get user booking statistics with monthly breakdown."""
        stats = services.get_user_stats(request.user_id)
        return Response(stats)

    @action(detail=True, methods=["get"], url_path="qr-code")
    def qr_code(self, request, pk=None):
        """Get QR code for booking."""
        booking = self.get_object()
        return Response(
            {
                "qr_code": booking.qr_code_data,
                "expires_at": (
                    booking.start_time.isoformat() if booking.start_time else None
                ),
            }
        )

    @action(detail=False, methods=["post"], url_path="check-slot-bookings")
    def check_slot_bookings(self, request):
        """Check which slots have overlapping bookings in given time range."""
        slot_ids = request.data.get("slot_ids", [])
        start_time = request.data.get("start_time")
        end_time = request.data.get("end_time")

        if not slot_ids or not start_time:
            return Response(
                {"error": "slot_ids and start_time are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = services.check_overlapping_bookings(slot_ids, start_time, end_time)

        if "error" in result:
            return Response(
                {"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(result)
