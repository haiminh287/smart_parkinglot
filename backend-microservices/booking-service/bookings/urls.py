"""
URL configuration for booking-service.
"""

from django.urls import path

from . import views
from .views_lifecycle import BookingLifecycleViewSet
from .views_payment import BookingPaymentViewSet
from .views_query import BookingQueryViewSet

# Gateway sends /bookings/... → main urls.py has path('bookings/', ...)
# So we're already inside /bookings/, paths here are relative
urlpatterns = [
    # Package Pricings
    path(
        "packagepricings/",
        views.PackagePricingViewSet.as_view({"get": "list", "post": "create"}),
        name="packagepricing-list",
    ),
    path(
        "packagepricings/<uuid:pk>/",
        views.PackagePricingViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="packagepricing-detail",
    ),
    # Query actions (must come before generic patterns)
    path(
        "current-parking/",
        BookingQueryViewSet.as_view({"get": "current_parking"}),
        name="booking-current-parking",
    ),
    path(
        "current/",
        BookingQueryViewSet.as_view({"get": "current"}),
        name="booking-current",
    ),
    path(
        "upcoming/",
        BookingQueryViewSet.as_view({"get": "upcoming_bookings"}),
        name="booking-upcoming",
    ),
    path(
        "stats/",
        BookingQueryViewSet.as_view({"get": "booking_stats"}),
        name="booking-stats",
    ),
    path(
        "check-slot-bookings/",
        BookingQueryViewSet.as_view({"post": "check_slot_bookings"}),
        name="booking-check-slot",
    ),
    # Payment actions
    path(
        "payment/",
        BookingPaymentViewSet.as_view({"post": "initiate_payment"}),
        name="booking-payment",
    ),
    path(
        "payment/verify/",
        BookingPaymentViewSet.as_view({"post": "verify_payment"}),
        name="booking-payment-verify",
    ),
    # CRUD - List and Create
    path(
        "",
        views.BookingViewSet.as_view({"get": "list", "post": "create"}),
        name="booking-list",
    ),
    # Detail
    path(
        "<uuid:pk>/",
        views.BookingViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="booking-detail",
    ),
    # Lifecycle actions
    path(
        "<uuid:pk>/checkin/",
        BookingLifecycleViewSet.as_view({"post": "checkin"}),
        name="booking-checkin",
    ),
    path(
        "<uuid:pk>/checkout/",
        BookingLifecycleViewSet.as_view({"post": "checkout"}),
        name="booking-checkout",
    ),
    path(
        "<uuid:pk>/cancel/",
        BookingLifecycleViewSet.as_view({"post": "cancel"}),
        name="booking-cancel",
    ),
    path(
        "<uuid:pk>/extend/",
        BookingLifecycleViewSet.as_view({"post": "extend_booking"}),
        name="booking-extend",
    ),
    path(
        "<uuid:pk>/qr-code/",
        BookingQueryViewSet.as_view({"get": "qr_code"}),
        name="booking-qr-code",
    ),
    path(
        "<uuid:pk>/payment/",
        BookingPaymentViewSet.as_view({"post": "payment"}),
        name="booking-detail-payment",
    ),
]
