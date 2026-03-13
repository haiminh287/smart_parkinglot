"""
URL configuration for parking-service.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'lots', views.ParkingLotViewSet, basename='lot')
router.register(r'floors', views.FloorViewSet, basename='floor')
router.register(r'zones', views.ZoneViewSet, basename='zone')
router.register(r'slots', views.CarSlotViewSet, basename='slot')
router.register(r'cameras', views.CameraViewSet, basename='camera')

urlpatterns = [
    path('', include(router.urls)),
]
