"""
Lifecycle actions for bookings: checkin, checkout, extend, cancel.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from shared.gateway_permissions import IsGatewayAuthenticated

from . import services
from .models import Booking
from .serializers import BookingSerializer


class BookingLifecycleViewSet(viewsets.GenericViewSet):
    """Lifecycle actions: checkin, checkout, extend, cancel."""

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

    @action(detail=True, methods=["post"], url_path="checkin")
    def checkin(self, request, pk=None):
        """Check-in to a booking (scan QR code at entry gate)."""
        booking = self.get_object()

        checkin_result = services.perform_checkin_with_reallocation(booking)
        if not checkin_result.get("ok"):
            return Response(
                {
                    "error": checkin_result.get(
                        "error",
                        "No slot available for check-in",
                    )
                },
                status=checkin_result.get("status_code", status.HTTP_409_CONFLICT),
            )

        booking = checkin_result["booking"]

        serializer = self.get_serializer(booking)
        return Response(
            {
                "booking": serializer.data,
                "message": "Check-in successful",
                "checkedInAt": (
                    booking.checked_in_at.isoformat() if booking.checked_in_at else None
                ),
            }
        )

    @action(detail=True, methods=["post"], url_path="checkout")
    def checkout(self, request, pk=None):
        """Check-out from a booking (scan QR code at exit)."""
        booking = self.get_object()

        error = services.validate_checkout(booking)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        checkout_result = services.perform_checkout(booking)
        if not checkout_result.get("ok"):
            return Response(
                {"error": checkout_result.get("error", "Checkout conflict")},
                status=checkout_result.get(
                    "status_code", status.HTTP_409_CONFLICT
                ),
            )

        pricing = checkout_result["pricing"]

        booking.refresh_from_db()
        serializer = BookingSerializer(booking)
        return Response(
            {
                "booking": serializer.data,
                "message": "Check-out successful",
                "durationHours": round(pricing["total_hours"], 2),
                "totalAmount": float(pricing["total_amount"]),
                "pricePerHour": float(pricing["hourly_price"]),
                "lateFee": float(pricing.get("late_fee", 0)),
                "lateFeeApplied": booking.late_fee_applied,
            }
        )

    @action(detail=True, methods=["post"], url_path="extend")
    def extend_booking(self, request, pk=None):
        """Extend an active booking's duration."""
        booking = self.get_object()

        if booking.check_in_status != "checked_in":
            return Response(
                {"error": "Only checked-in bookings can be extended"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        additional_hours = request.data.get("additional_hours")
        if (
            not additional_hours
            or not isinstance(additional_hours, (int, float))
            or additional_hours <= 0
        ):
            return Response(
                {"error": "additional_hours must be a positive number"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        additional_hours = int(additional_hours)

        ext_result = services.perform_extend(booking, additional_hours)

        booking.refresh_from_db()
        serializer = BookingSerializer(booking)
        return Response(
            {
                "booking": serializer.data,
                "extension": ext_result,
                "message": f"Booking extended by {additional_hours} hour(s)",
            }
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a booking."""
        booking = self.get_object()

        error = services.validate_cancel(booking)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        cancel_result = services.perform_cancel(booking)
        if not cancel_result.get("ok"):
            return Response(
                {"error": cancel_result.get("error", "Cancel conflict")},
                status=cancel_result.get("status_code", status.HTTP_409_CONFLICT),
            )

        booking = cancel_result["booking"]

        serializer = self.get_serializer(booking)
        return Response(
            {"booking": serializer.data, "message": "Booking cancelled successfully"}
        )
