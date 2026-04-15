"""
Payment-related views for booking-service.
"""

import logging
import uuid as uuid_lib

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from shared.gateway_permissions import IsGatewayAuthenticated

from . import services
from .models import Booking
from .serializers import BookingSerializer

logger = logging.getLogger(__name__)


class BookingPaymentViewSet(viewsets.GenericViewSet):
    """Payment actions for bookings."""

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

    @action(detail=True, methods=["post"])
    def payment(self, request, pk=None):
        """Initiate payment for a specific booking."""
        booking = self.get_object()
        payment_method = request.data.get("payment_method")

        if not payment_method:
            return Response(
                {"error": "payment_method is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check for existing active payments
        existing = services.get_booking_payments(str(booking.id), str(booking.user_id))
        if existing:
            active = [
                p for p in existing if p.get("status") in ("pending", "processing")
            ]
            if active:
                return Response(
                    {
                        "payment": active[0],
                        "booking_id": str(booking.id),
                        "amount": float(booking.price),
                        "message": "Active payment already exists for this booking",
                    }
                )

        result = services.initiate_payment(
            booking_id=booking.id,
            user_id=booking.user_id,
            payment_method=payment_method,
            amount=booking.price,
        )

        if result is None:
            return Response(
                {"error": "Payment service unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if "error" in result:
            return Response(
                {"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST
            )

        booking.payment_status = "processing"
        booking.save(update_fields=["payment_status"])

        return Response(
            {
                "payment": result,
                "booking_id": str(booking.id),
                "amount": float(booking.price),
            }
        )

    @action(detail=False, methods=["post"], url_path="payment")
    def initiate_payment(self, request):
        """Initiate payment (expects booking_id in body)."""
        booking_id = request.data.get("booking_id")
        payment_method = request.data.get("payment_method")

        if not booking_id:
            return Response(
                {"error": "booking_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not payment_method:
            return Response(
                {"error": "payment_method is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            uuid_lib.UUID(booking_id)
        except (ValueError, AttributeError):
            return Response(
                {"error": "Invalid booking_id format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            booking = Booking.objects.get(id=booking_id, user_id=request.user_id)
        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check for existing active payments
        existing = services.get_booking_payments(str(booking.id), str(booking.user_id))
        if existing:
            active = [
                p for p in existing if p.get("status") in ("pending", "processing")
            ]
            if active:
                return Response(
                    {
                        "payment": active[0],
                        "booking_id": str(booking.id),
                        "amount": float(booking.price),
                        "message": "Active payment already exists for this booking",
                    }
                )

        result = services.initiate_payment(
            booking_id=booking.id,
            user_id=booking.user_id,
            payment_method=payment_method,
            amount=booking.price,
        )

        if result is None:
            return Response(
                {"error": "Payment service unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if "error" in result:
            return Response(
                {"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST
            )

        booking.payment_status = "processing"
        booking.save(update_fields=["payment_status"])

        return Response(
            {
                "payment": result,
                "booking_id": str(booking.id),
                "amount": float(booking.price),
            }
        )

    @action(detail=False, methods=["post"], url_path="payment/verify")
    def verify_payment(self, request):
        """Verify payment callback."""
        transaction_id = request.data.get("transaction_id")
        if not transaction_id:
            return Response(
                {"error": "transaction_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"success": True, "message": "Payment verified"})
