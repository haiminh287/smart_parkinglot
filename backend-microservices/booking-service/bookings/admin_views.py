"""
Admin views for revenue and statistics in booking-service.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate, ExtractHour
from django.utils import timezone
from rest_framework import status, views
from rest_framework.response import Response

try:
    from shared.gateway_permissions import IsGatewayAdmin
except ImportError:
    from rest_framework.permissions import IsAdminUser as IsGatewayAdmin

from .models import Booking


class RevenueStatsView(views.APIView):
    """
    GET /bookings/admin/revenue/summary/

    Returns aggregated revenue statistics from completed bookings.
    """

    permission_classes = [IsGatewayAdmin]

    def get(self, request) -> Response:
        """Return revenue summary with totals and breakdowns."""
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        completed_qs = Booking.objects.filter(payment_status="completed")

        # Revenue aggregations
        total_revenue = (
            completed_qs.aggregate(total=Sum("price"))["total"] or Decimal("0")
        )
        today_revenue = (
            completed_qs.filter(created_at__gte=today_start).aggregate(
                total=Sum("price")
            )["total"]
            or Decimal("0")
        )
        this_week_revenue = (
            completed_qs.filter(created_at__gte=week_start).aggregate(
                total=Sum("price")
            )["total"]
            or Decimal("0")
        )
        this_month_revenue = (
            completed_qs.filter(created_at__gte=month_start).aggregate(
                total=Sum("price")
            )["total"]
            or Decimal("0")
        )

        # Booking counts
        all_bookings = Booking.objects.all()
        total_bookings = all_bookings.count()
        completed_bookings = completed_qs.count()
        cancelled_bookings = all_bookings.filter(
            check_in_status="cancelled"
        ).count()
        active_bookings = all_bookings.filter(
            check_in_status="checked_in"
        ).count()

        # Average booking value (completed only)
        average_booking_value = (
            completed_qs.aggregate(avg=Avg("price"))["avg"] or Decimal("0")
        )

        # Payment method breakdown (on completed bookings)
        method_breakdown = (
            completed_qs.values("payment_method")
            .annotate(count=Count("id"), amount=Sum("price"))
            .order_by("payment_method")
        )
        # Always include both keys with defaults so frontend never gets undefined
        payment_methods: dict = {
            "online": {"count": 0, "amount": 0.0},
            "on_exit": {"count": 0, "amount": 0.0},
        }
        for entry in method_breakdown:
            key = entry["payment_method"]
            if key in payment_methods:
                payment_methods[key] = {
                    "count": entry["count"],
                    "amount": float(entry["amount"] or 0),
                }
            else:
                payment_methods[key] = {
                    "count": entry["count"],
                    "amount": float(entry["amount"] or 0),
                }

        return Response(
            {
                "total_revenue": float(total_revenue),
                "today_revenue": float(today_revenue),
                "this_week_revenue": float(this_week_revenue),
                "this_month_revenue": float(this_month_revenue),
                "total_bookings": total_bookings,
                "completed_bookings": completed_bookings,
                "cancelled_bookings": cancelled_bookings,
                "active_bookings": active_bookings,
                "average_booking_value": round(float(average_booking_value), 2),
                "payment_methods": payment_methods,
            }
        )


class DailyRevenueView(views.APIView):
    """
    GET /bookings/admin/revenue/daily/?days=30

    Returns daily revenue for the last N days.
    """

    permission_classes = [IsGatewayAdmin]

    def get(self, request) -> Response:
        """Return daily revenue breakdown."""
        try:
            days = int(request.query_params.get("days", 30))
        except (ValueError, TypeError):
            days = 30
        days = max(1, min(days, 365))

        now = timezone.now()
        start_date = (now - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        daily_data = (
            Booking.objects.filter(
                payment_status="completed",
                created_at__gte=start_date,
            )
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(revenue=Sum("price"), bookings=Count("id"))
            .order_by("date")
        )

        # Build a dict for quick lookup
        data_map: dict = {}
        for entry in daily_data:
            date_str = entry["date"].strftime("%Y-%m-%d")
            data_map[date_str] = {
                "date": date_str,
                "revenue": float(entry["revenue"] or 0),
                "bookings": entry["bookings"],
            }

        # Fill in missing days with zeros
        result = []
        current = start_date
        while current.date() <= now.date():
            date_str = current.strftime("%Y-%m-%d")
            if date_str in data_map:
                result.append(data_map[date_str])
            else:
                result.append(
                    {"date": date_str, "revenue": 0, "bookings": 0}
                )
            current += timedelta(days=1)

        return Response({"data": result})


class HourlyRevenueView(views.APIView):
    """
    GET /bookings/admin/revenue/hourly/?date=YYYY-MM-DD

    Returns hourly distribution for a given date (defaults to today).
    """

    permission_classes = [IsGatewayAdmin]

    def get(self, request) -> Response:
        """Return hourly revenue breakdown."""
        date_str = request.query_params.get("date")
        if date_str:
            try:
                from datetime import datetime

                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                day_start = timezone.make_aware(
                    datetime.combine(target_date, datetime.min.time())
                )
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            now = timezone.now()
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        day_end = day_start + timedelta(days=1)

        hourly_data = (
            Booking.objects.filter(
                payment_status="completed",
                created_at__gte=day_start,
                created_at__lt=day_end,
            )
            .annotate(hour=ExtractHour("created_at"))
            .values("hour")
            .annotate(revenue=Sum("price"), bookings=Count("id"))
            .order_by("hour")
        )

        # Build lookup
        hour_map: dict = {}
        for entry in hourly_data:
            hour_map[entry["hour"]] = {
                "hour": entry["hour"],
                "revenue": float(entry["revenue"] or 0),
                "bookings": entry["bookings"],
            }

        # Fill all 24 hours
        result = []
        for h in range(24):
            if h in hour_map:
                result.append(hour_map[h])
            else:
                result.append({"hour": h, "revenue": 0, "bookings": 0})

        return Response({"data": result})
