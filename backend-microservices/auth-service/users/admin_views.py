"""
Admin views for user management.
"""

import requests
from django.conf import settings
from django.db.models import Count
from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.pagination import PageNumberPagination
from datetime import datetime, timedelta

from .models import User
from .serializers import UserSerializer, AdminUserUpdateSerializer, AdminUserCreateSerializer

try:
    from shared.gateway_permissions import IsGatewayAdmin
except ImportError:
    # Fallback if shared not on PYTHONPATH
    IsGatewayAdmin = IsAdminUser


class DashboardStatsView(views.APIView):
    """
    Dashboard statistics API for admin panel.
    Aggregates data from multiple microservices.
    """
    permission_classes = [IsGatewayAdmin]
    
    def get(self, request):
        """Get dashboard stats."""
        # User stats
        total_users = User.objects.filter(role='user').count()
        active_users = User.objects.filter(role='user', is_active=True).count()
        
        # Get stats from other services
        total_bookings = self._get_total_bookings()
        active_parkings = self._get_active_parkings()
        total_revenue = self._get_total_revenue()
        occupancy_rate = self._get_occupancy_rate()
        
        # Calculate changes (mock for now - would need historical data)
        stats = {
            'total_users': total_users,
            'total_bookings': total_bookings,
            'total_revenue': total_revenue,
            'active_parkings': active_parkings,
            'occupancy_rate': occupancy_rate,
            # Change percentages (mock - calculate from historical data)
            'users_change': 12.5,  # % change from last period
            'bookings_change': 8.3,
            'revenue_change': 15.2,
        }
        
        return Response(stats)
    
    def _get_total_bookings(self):
        """Get total bookings count from booking-service."""
        try:
            response = requests.get('http://localhost:8004/bookings/', timeout=2)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'count' in data:
                    return data['count']
            return 0
        except Exception:
            return 0
    
    def _get_active_parkings(self):
        """Get current active parkings from booking-service."""
        try:
            response = requests.get(
                'http://localhost:8004/bookings/',
                params={'check_in_status': 'checked_in,parked'},
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'count' in data:
                    return data['count']
            return 0
        except Exception:
            return 0
    
    def _get_total_revenue(self):
        """Get total revenue from payment-service."""
        try:
            response = requests.get('http://localhost:8007/payments/', timeout=2)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'results' in data:
                    payments = data['results']
                    total = sum(
                        float(p.get('amount', 0))
                        for p in payments
                        if p.get('status') == 'completed'
                    )
                    return total
            return 0
        except Exception:
            return 0
    
    def _get_occupancy_rate(self):
        """Get occupancy rate from parking-service."""
        try:
            response = requests.get('http://localhost:8002/lots/', timeout=2)
            if response.status_code == 200:
                data = response.json()
                lots = data.get('results', []) if isinstance(data, dict) else data
                
                if lots:
                    total_slots = sum(lot.get('total_slots', 0) for lot in lots)
                    available_slots = sum(lot.get('available_slots', 0) for lot in lots)
                    
                    if total_slots > 0:
                        occupied = total_slots - available_slots
                        return round((occupied / total_slots) * 100, 1)
            return 0
        except Exception:
            return 0


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for admin endpoints."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin user management.
    
    Provides:
    - List users with pagination and filters
    - Get user details with total_bookings and total_spent
    - Update user
    - Deactivate/activate user
    - Reset no-show count
    """
    
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsGatewayAdmin]
    pagination_class = StandardResultsSetPagination
    
    def get_serializer_class(self):
        """Return appropriate serializer per action."""
        if self.action == 'create':
            return AdminUserCreateSerializer
        elif self.action in ('update', 'partial_update'):
            return AdminUserUpdateSerializer
        return UserSerializer
    
    def get_queryset(self):
        """Filter users by role and active status."""
        queryset = super().get_queryset()
        
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=(is_active.lower() == 'true'))
        
        return queryset.order_by('-date_joined')
    
    def create(self, request, *args, **kwargs):
        """Create a new user (admin only)."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Update user (admin only). Returns full user data."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # Refresh from DB and return full user data
        instance.refresh_from_db()
        return Response(UserSerializer(instance).data)
    
    def retrieve(self, request, *args, **kwargs):
        """Get user with total_bookings and total_spent."""
        user = self.get_object()
        serializer = self.get_serializer(user)
        data = serializer.data
        
        # Add total_bookings from booking-service
        data['total_bookings'] = self._get_total_bookings(user.id)
        
        # Add total_spent from payment-service
        data['total_spent'] = self._get_total_spent(user.id)
        
        return Response(data)
    
    def list(self, request, *args, **kwargs):
        """List users with total_bookings and total_spent."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
            
            # Add total_bookings and total_spent for each user
            for user_data in data:
                user_data['total_bookings'] = self._get_total_bookings(user_data['id'])
                user_data['total_spent'] = self._get_total_spent(user_data['id'])
            
            return self.get_paginated_response(data)
        
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        
        for user_data in data:
            user_data['total_bookings'] = self._get_total_bookings(user_data['id'])
            user_data['total_spent'] = self._get_total_spent(user_data['id'])
        
        return Response(data)
    
    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        """Deactivate user account."""
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=['is_active'])
        
        return Response({
            'message': f'User {user.email} has been deactivated',
            'user': self.get_serializer(user).data
        })
    
    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        """Activate user account."""
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])
        
        return Response({
            'message': f'User {user.email} has been activated',
            'user': self.get_serializer(user).data
        })
    
    @action(detail=True, methods=['post'], url_path='reset-no-show')
    def reset_no_show(self, request, pk=None):
        """Reset user's no-show count."""
        user = self.get_object()
        user.no_show_count = 0
        user.force_online_payment = False
        user.save(update_fields=['no_show_count', 'force_online_payment'])
        
        return Response({
            'message': f'No-show count reset for {user.email}',
            'user': self.get_serializer(user).data
        })
    
    def _get_total_bookings(self, user_id):
        """Get total bookings count from booking-service."""
        try:
            response = requests.get(
                f'http://localhost:8004/bookings/',
                params={'user_id': user_id},
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                # Handle Django pagination response
                if isinstance(data, dict) and 'count' in data:
                    return data['count']
                elif isinstance(data, list):
                    return len(data)
            return 0
        except Exception:
            return 0
    
    def _get_total_spent(self, user_id):
        """Get total spent from payment-service."""
        try:
            response = requests.get(
                f'http://localhost:8005/payments/',
                params={'user_id': user_id},
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                # Sum up all completed payment amounts
                if isinstance(data, dict) and 'results' in data:
                    payments = data['results']
                elif isinstance(data, list):
                    payments = data
                else:
                    return 0
                
                total = sum(
                    float(payment.get('amount', 0))
                    for payment in payments
                    if payment.get('status') == 'completed'
                )
                return total
            return 0
        except Exception:
            return 0


class SystemConfigView(views.APIView):
    """
    System configuration API for admin panel.
    Returns and updates parking system configuration.
    """
    permission_classes = [IsGatewayAdmin]

    # Default config values (stored in memory for now)
    _config = {
        'price_per_hour_car': 10000,
        'price_per_hour_motorbike': 5000,
        'max_no_show_count': 3,
        'hold_time_minutes': 15,
        'auto_cancel_minutes': 30,
        'online_payment_required_after_no_shows': 2,
    }

    def get(self, request):
        """Return current system configuration."""
        return Response(self._config)

    def patch(self, request):
        """Update system configuration."""
        for key, value in request.data.items():
            if key in self._config:
                self._config[key] = value
        return Response(self._config)
