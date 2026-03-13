"""
Views for vehicle-service.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from shared.gateway_permissions import IsGatewayAuthenticated
from .models import Vehicle
from .serializers import VehicleSerializer


class VehicleViewSet(viewsets.ModelViewSet):
    """ViewSet for Vehicle."""

    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsGatewayAuthenticated]
    
    def get_queryset(self):
        """Filter vehicles by current user."""
        if getattr(self.request, 'user_id', None):
            return Vehicle.objects.filter(user_id=self.request.user_id)
        return Vehicle.objects.none()
    
    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, pk=None):
        """Set this vehicle as the default vehicle."""
        vehicle = self.get_object()
        
        # Remove default from all user's vehicles
        Vehicle.objects.filter(user_id=request.user_id, is_default=True).update(is_default=False)
        
        # Set this vehicle as default
        vehicle.is_default = True
        vehicle.save(update_fields=['is_default'])
        
        serializer = self.get_serializer(vehicle)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='default')
    def get_default(self, request):
        """Get the user's default vehicle."""
        vehicle = Vehicle.objects.filter(user_id=request.user_id, is_default=True).first()
        
        if not vehicle:
            return Response({'detail': 'No default vehicle set'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(vehicle)
        return Response(serializer.data)


