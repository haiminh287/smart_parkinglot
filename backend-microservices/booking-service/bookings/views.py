"""
Views for booking-service.
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from shared.gateway_permissions import IsGatewayAuthenticated

from . import services
from .models import Booking, PackagePricing
from .serializers import (
    BookingSerializer,
    CreateBookingSerializer,
    PackagePricingSerializer,
)
from .events import create_slot_event, create_booking_event

logger = logging.getLogger(__name__)


class PackagePricingViewSet(viewsets.ModelViewSet):
    """ViewSet for PackagePricing."""

    queryset = PackagePricing.objects.all()
    serializer_class = PackagePricingSerializer
    permission_classes = [IsGatewayAuthenticated]


class BookingViewSet(viewsets.ModelViewSet):
    """ViewSet for Booking."""

    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsGatewayAuthenticated]

    def get_serializer_class(self):
        """Use CreateBookingSerializer for POST, BookingSerializer for GET."""
        if self.action == "create":
            return CreateBookingSerializer
        return BookingSerializer

    def get_queryset(self):
        """Filter bookings by current user from gateway headers.

        Special case: user_id == 'system' returns all bookings
        (for inter-service calls from AI service, etc.)
        """
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
            create_slot_event(booking.slot_id, 'reserved', booking)
        create_booking_event('booking.created', booking)

        # Auto-create payment record (best-effort, non-blocking)
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

    @action(detail=True, methods=["post"], url_path="checkin")
    def checkin(self, request, pk=None):
        """Check-in to a booking (scan QR code at entry gate)."""
        booking = self.get_object()

        if booking.check_in_status != "not_checked_in":
            status_map = {
                "checked_in": "already checked in",
                "checked_out": "already checked out",
                "cancelled": "cancelled",
                "no_show": "marked as no-show",
            }
            msg = status_map.get(
                booking.check_in_status, f"invalid status: {booking.check_in_status}"
            )
            return Response(
                {"error": f"Cannot check in: booking is {msg}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if booking.start_time and timezone.now() < booking.start_time - timedelta(
            minutes=30
        ):
            return Response(
                {
                    "message": "Chưa đến giờ check-in. Vui lòng đến trong vòng 30 phút trước giờ đặt."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.check_in_status = "checked_in"
        booking.checked_in_at = timezone.now()
        booking.save(update_fields=["check_in_status", "checked_in_at"])

        if booking.slot_id:
            create_slot_event(booking.slot_id, 'occupied', booking)
        create_booking_event('booking.checked_in', booking)

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

        if booking.check_in_status != "checked_in":
            return Response(
                {"error": "Only checked-in bookings can be checked out"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        error = services.validate_checkout(booking)
        if error:
            return Response({"message": error}, status=status.HTTP_400_BAD_REQUEST)

        pricing = services.calculate_checkout_price(booking)
        services.perform_checkout(booking)

        if booking.slot_id:
            create_slot_event(booking.slot_id, 'available', booking)
        create_booking_event('booking.checked_out', booking)

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

    def _get_hourly_price(self, vehicle_type):
        """Get hourly price for vehicle type from PackagePricing."""
        from decimal import Decimal

        try:
            pricing = PackagePricing.objects.get(
                package_type="hourly", vehicle_type=vehicle_type
            )
            return pricing.price
        except PackagePricing.DoesNotExist:
            # Default pricing if not configured
            if vehicle_type == "Car":
                return Decimal("15000.00")  # 15,000 VND per hour for cars
            else:
                return Decimal("5000.00")  # 5,000 VND per hour for motorbikes

    @action(detail=True, methods=["post"], url_path="extend")
    def extend_booking(self, request, pk=None):
        """Extend an active booking's duration.

        Request body: { "additional_hours": N }
        Only allowed when booking is checked_in.
        Extension price = additional_hours × hourly_price (no surcharge).
        """
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

        if booking.check_in_status in ["checked_in", "checked_out"]:
            return Response(
                {
                    "error": "Cannot cancel booking that has already started or completed"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.check_in_status = "cancelled"
        booking.save(update_fields=["check_in_status"])

        if booking.slot_id:
            create_slot_event(booking.slot_id, 'available', booking)
        create_booking_event('booking.cancelled', booking)

        # TODO: Process refund if paid online

        serializer = self.get_serializer(booking)
        return Response(
            {"booking": serializer.data, "message": "Booking cancelled successfully"}
        )

    @action(detail=False, methods=["get"], url_path="current-parking")
    def current_parking(self, request):
        """Get current parking session (checked_in status)."""
        # Permission already checked by IsGatewayAuthenticated
        booking = Booking.objects.filter(
            user_id=request.user_id, check_in_status="checked_in"
        ).first()

        if not booking:
            return Response(
                {"detail": "No active parking session"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Calculate duration and current cost
        if booking.checked_in_at:
            duration = (
                timezone.now() - booking.checked_in_at
            ).total_seconds() / 60  # in minutes
        else:
            duration = 0

        # Calculate cost based on hourly rate and actual time
        import math

        hourly_rate = self._get_hourly_price(booking.vehicle_type)
        hours_parked = duration / 60
        billable_hours = math.ceil(hours_parked) if hours_parked > 0 else 1
        current_cost = float(billable_hours * hourly_rate)

        serializer = self.get_serializer(booking)
        return Response(
            {
                "booking": serializer.data,
                "duration": int(duration),
                "currentCost": round(current_cost, 2),
                "hoursParked": round(hours_parked, 2),
                "billableHours": billable_hours,
                "pricePerHour": float(hourly_rate),
                "message": "Current parking session",
            }
        )

    @action(detail=False, methods=["get"], url_path="upcoming")
    def upcoming_bookings(self, request):
        """Get upcoming bookings (not checked in yet)."""
        # Permission already checked by IsGatewayAuthenticated
        bookings_qs = Booking.objects.filter(
            user_id=request.user_id,
            check_in_status="not_checked_in",
            start_time__gte=timezone.now(),
        ).order_by("start_time")

        # Get count before slicing
        count = bookings_qs.count()
        bookings = bookings_qs[:5]

        serializer = self.get_serializer(bookings, many=True)
        return Response(
            {"results": serializer.data, "count": count, "message": "Upcoming bookings"}
        )

    @action(detail=False, methods=["get"], url_path="stats")
    def booking_stats(self, request):
        """Get user booking statistics with monthly breakdown."""
        from decimal import Decimal

        from django.db.models import Count, Sum
        from django.db.models.functions import TruncMonth

        user_bookings = Booking.objects.filter(user_id=request.user_id)

        total_spent = user_bookings.filter(payment_status="completed").aggregate(
            total=Sum("price")
        )["total"] or Decimal("0")

        # Also count money from checked_out bookings (on_exit payments)
        exit_spent = user_bookings.filter(check_in_status="checked_out").aggregate(
            total=Sum("price")
        )["total"] or Decimal("0")

        actual_total_spent = max(total_spent, exit_spent)

        # Calculate total hours parked using Django aggregation
        from django.db.models import DurationField, ExpressionWrapper, F

        completed_bookings = user_bookings.filter(
            check_in_status__in=["checked_out"],
            checked_in_at__isnull=False,
            checked_out_at__isnull=False,
        )
        total_duration = completed_bookings.annotate(
            duration=ExpressionWrapper(
                F("checked_out_at") - F("checked_in_at"), output_field=DurationField()
            )
        ).aggregate(total=Sum("duration"))
        total_hours = (
            total_duration["total"].total_seconds() / 3600
            if total_duration["total"]
            else 0
        )

        # Monthly expenses breakdown (last 6 months)
        from datetime import timedelta

        from django.utils import timezone as tz

        six_months_ago = tz.now() - timedelta(days=180)
        monthly_data = (
            user_bookings.filter(created_at__gte=six_months_ago)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Sum("price"), count=Count("id"))
            .order_by("month")
        )

        monthly_expenses = []
        for item in monthly_data:
            monthly_expenses.append(
                {
                    "month": item["month"].strftime("%Y-%m") if item["month"] else "",
                    "amount": float(item["total"] or 0),
                    "count": item["count"],
                }
            )

        return Response(
            {
                "total_bookings": user_bookings.count(),
                "total_spent": float(actual_total_spent),
                "total_hours": round(total_hours, 1),
                "no_show_count": user_bookings.filter(
                    check_in_status="no_show"
                ).count(),
                "completed_bookings": user_bookings.filter(
                    check_in_status="checked_out"
                ).count(),
                "cancelled_bookings": user_bookings.filter(
                    check_in_status="cancelled"
                ).count(),
                "active_bookings": user_bookings.filter(
                    check_in_status="checked_in"
                ).count(),
                "monthly_expenses": monthly_expenses,
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
        # TODO: Verify with payment gateway
        return Response({"success": True, "message": "Payment verified"})

    @action(detail=True, methods=["get"], url_path="qr-code")
    def qr_code(self, request, pk=None):
        """Get QR code for booking."""
        booking = self.get_object()
        return Response(
            {
                "qr_code": booking.qr_code_data,
                "expires_at": (
                    (booking.start_time).isoformat() if booking.start_time else None
                ),
            }
        )

    @action(detail=False, methods=["post"], url_path="check-slot-bookings")
    def check_slot_bookings(self, request):
        """Check which slots have overlapping bookings in given time range.
        Used by parking-service to determine slot availability.
        """
        slot_ids = request.data.get("slot_ids", [])
        start_time = request.data.get("start_time")
        end_time = request.data.get("end_time")

        if not slot_ids or not start_time:
            return Response(
                {"error": "slot_ids and start_time are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from datetime import datetime

        from django.db.models import Q

        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            if end_time:
                end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            else:
                # If no end_time, check from start_time onwards
                end_dt = None
        except ValueError:
            return Response(
                {"error": "Invalid datetime format. Use ISO 8601"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find bookings that overlap with the requested time range
        # A booking overlaps if: booking_start < end_time AND booking_end > start_time
        query = Q(
            slot_id__in=slot_ids, check_in_status__in=["not_checked_in", "checked_in"]
        )

        if end_dt:
            query &= Q(start_time__lt=end_dt) & Q(end_time__gt=start_dt)
        else:
            query &= Q(end_time__gt=start_dt)

        overlapping_bookings = Booking.objects.filter(query)
        booked_slot_ids = list(
            overlapping_bookings.values_list("slot_id", flat=True).distinct()
        )

        return Response(
            {
                "booked_slot_ids": [str(sid) for sid in booked_slot_ids],
                "count": len(booked_slot_ids),
            }
        )

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

        # Check for existing active payments first
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

        # Initiate new payment via payment service
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
        import uuid as uuid_lib

        booking_id = request.data.get("booking_id")
        payment_method = request.data.get("payment_method")

        if not booking_id:
            return Response(
                {"error": "booking_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not payment_method:
            return Response(
                {"error": "payment_method is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate UUID before querying
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

        # Check for existing active payments first
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

        # Initiate new payment via payment service
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

    @action(detail=False, methods=["get"])
    def current(self, request):
        """Get current parking session (checked-in or parked booking)."""
        booking = Booking.objects.filter(
            user_id=request.user_id, check_in_status="checked_in"
        ).first()

        if not booking:
            return Response(
                {"detail": "No active parking session"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(booking)

        # Calculate current duration and cost (handle None checked_in_at)
        from datetime import timedelta

        duration = (
            (timezone.now() - booking.checked_in_at)
            if booking.checked_in_at
            else timedelta(0)
        )
        hours = duration.total_seconds() / 3600
        # TODO: Calculate current cost based on package pricing

        return Response(
            {
                "booking": serializer.data,
                "duration_minutes": int(duration.total_seconds() / 60),
                "current_cost": float(booking.price),
            }
        )
