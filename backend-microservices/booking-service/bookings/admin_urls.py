"""
Admin URL configuration for booking-service revenue endpoints.
"""

from django.urls import path

from . import admin_views

urlpatterns = [
    path(
        "revenue/summary/",
        admin_views.RevenueStatsView.as_view(),
        name="admin-revenue-summary",
    ),
    path(
        "revenue/daily/",
        admin_views.DailyRevenueView.as_view(),
        name="admin-revenue-daily",
    ),
    path(
        "revenue/hourly/",
        admin_views.HourlyRevenueView.as_view(),
        name="admin-revenue-hourly",
    ),
]
