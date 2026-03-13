"""
ViewSet for Incident management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from shared.gateway_permissions import IsGatewayAuthenticated
from .incident_models import Incident
from .incident_serializers import IncidentSerializer


class IncidentViewSet(viewsets.ModelViewSet):
    """ViewSet for Incident management."""
    
    queryset = Incident.objects.all()
    serializer_class = IncidentSerializer
    permission_classes = [IsGatewayAuthenticated]
    
    def get_queryset(self):
        """Filter incidents by user (non-admin see only their own)."""
        # Check if request wants all incidents (admin view)
        if self.request.query_params.get('all') == 'true':
            return Incident.objects.all().order_by('-created_at')
        
        # Regular users see only their own incidents
        return Incident.objects.filter(user_id=self.request.user_id).order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """Create new incident (panic button)."""
        # Work with a mutable dict copy of the request data
        data = dict(request.data)
        
        # Handle nested location object from frontend
        # Frontend sends: { location: { zoneId, slotId } }
        # CamelCaseParser converts to: { location: { zone_id, slot_id } }
        location = data.pop('location', None)
        if isinstance(location, dict):
            if location.get('zone_id'):
                data['zone_id'] = location['zone_id']
            if location.get('slot_id'):
                data['slot_id'] = location['slot_id']
        
        serializer = self.get_serializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        incident = serializer.save()
        
        # Auto-notify security for emergency types
        if incident.type in ('emergency', 'theft', 'accident'):
            incident.security_notified = True
            incident.security_notified_at = timezone.now()
            incident.status = 'in_progress'
            incident.save(update_fields=['security_notified', 'security_notified_at', 'status'])
        
        return Response({
            'incident': IncidentSerializer(incident).data,
            'message': 'Incident reported successfully. Security has been notified.'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='my')
    def my_incidents(self, request):
        """Get user's incident history."""
        incidents = self.get_queryset().order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            incidents = incidents.filter(status=status_filter)
        
        # Filter by type if provided
        type_filter = request.query_params.get('type')
        if type_filter:
            incidents = incidents.filter(type=type_filter)
        
        serializer = self.get_serializer(incidents, many=True)
        return Response({
            'count': incidents.count(),
            'results': serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_incident(self, request, pk=None):
        """Cancel an incident (user action)."""
        incident = self.get_object()
        
        if incident.status == 'resolved':
            return Response(
                {'error': 'Cannot cancel resolved incident'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        incident.status = 'cancelled'
        incident.save(update_fields=['status'])
        
        return Response({
            'message': 'Incident cancelled',
            'incident': IncidentSerializer(incident).data
        })
    
    @action(detail=True, methods=['post'], url_path='request-security')
    def request_security(self, request, pk=None):
        """Request security assistance for incident."""
        incident = self.get_object()
        
        if incident.security_notified:
            return Response(
                {'message': 'Security already notified'},
                status=status.HTTP_200_OK
            )
        
        incident.security_notified = True
        incident.security_notified_at = timezone.now()
        incident.status = 'in_progress'
        incident.save(update_fields=['security_notified', 'security_notified_at', 'status'])
        
        # TODO: Send notification to security team
        
        return Response({
            'message': 'Security assistance requested',
            'incident': IncidentSerializer(incident).data
        })
    
    @action(detail=False, methods=['get'], url_path='nearby-camera')
    def nearby_camera(self, request):
        """Find camera near incident location."""
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        zone_id = request.query_params.get('zone_id')
        
        # Require either (lat+lng) OR zone_id
        if not zone_id and (not latitude or not longitude):
            return Response(
                {'error': 'Either zone_id OR (latitude AND longitude) required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mock response - would query parking service for cameras
        # In real implementation, call parking-service camera API
        camera_info = {
            'camera_id': 'cam-001',
            'zone_id': zone_id if zone_id else 'zone-from-lat-lng',
            'stream_url': 'rtsp://example.com/camera/001',
            'is_active': True,
            'latitude': float(latitude) if latitude else None,
            'longitude': float(longitude) if longitude else None,
            'message': 'Camera found near location'
        }
        
        return Response(camera_info)
