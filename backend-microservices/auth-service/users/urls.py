"""
URL configuration for users app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import admin_views

# Router for admin endpoints
admin_router = DefaultRouter()
admin_router.register(r'users', admin_views.AdminUserViewSet, basename='admin-user')

urlpatterns = [
    # Authentication endpoints
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('me/', views.CurrentUserView.as_view(), name='current-user'),
    
    # Password management
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset-password'),
    
    # OAuth2
    path('google/', views.google_auth_url_view, name='google-auth-url'),
    path('google/callback/', views.google_callback_view, name='google-callback'),
    
    # Admin endpoints
    path('admin/dashboard/stats/', admin_views.DashboardStatsView.as_view(), name='admin-dashboard-stats'),
    path('admin/config/', admin_views.SystemConfigView.as_view(), name='admin-config'),
    path('admin/', include(admin_router.urls)),
]
