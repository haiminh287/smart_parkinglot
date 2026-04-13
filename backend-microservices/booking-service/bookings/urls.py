"""
URL configuration for booking-service.
"""

from django.urls import path
from . import views

# Gateway sends /bookings/... → main urls.py has path('bookings/', ...)
# So we're already inside /bookings/, paths here are relative
urlpatterns = [
    # Package Pricings - /bookings/packagepricings/
    path('packagepricings/', views.PackagePricingViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='packagepricing-list'),
    
    path('packagepricings/<uuid:pk>/', views.PackagePricingViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='packagepricing-detail'),

    # Custom actions MUST come before generic patterns
    path('current-parking/', views.BookingViewSet.as_view({
        'get': 'current_parking'
    }), name='booking-current-parking'),
    
    path('upcoming/', views.BookingViewSet.as_view({
        'get': 'upcoming_bookings'
    }), name='booking-upcoming'),
    
    path('stats/', views.BookingViewSet.as_view({
        'get': 'booking_stats'
    }), name='booking-stats'),

    
    path('payment/', views.BookingViewSet.as_view({
        'post': 'initiate_payment'
    }), name='booking-payment'),
    
    path('payment/verify/', views.BookingViewSet.as_view({
        'post': 'verify_payment'
    }), name='booking-payment-verify'),
    
    path('check-slot-bookings/', views.BookingViewSet.as_view({
        'post': 'check_slot_bookings'
    }), name='booking-check-slot'),

    # List and Create
    path('', views.BookingViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='booking-list'),
    
    # Detail
    path('<uuid:pk>/', views.BookingViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='booking-detail'),
    
    path('<uuid:pk>/checkin/', views.BookingViewSet.as_view({
        'post': 'checkin'
    }), name='booking-checkin'),
    
    path('<uuid:pk>/checkout/', views.BookingViewSet.as_view({
        'post': 'checkout'
    }), name='booking-checkout'),
    
    path('<uuid:pk>/cancel/', views.BookingViewSet.as_view({
        'post': 'cancel'
    }), name='booking-cancel'),
    
    path('<uuid:pk>/extend/', views.BookingViewSet.as_view({
        'post': 'extend_booking'
    }), name='booking-extend'),
    
    path('<uuid:pk>/qr-code/', views.BookingViewSet.as_view({
        'get': 'qr_code'
    }), name='booking-qr-code'),
]

