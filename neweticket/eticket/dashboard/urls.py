# urls.py
from django.urls import path
from .views import (
    DashboardView,
    DriverTripsView,
    DriverTripDetailView,
    DriverVehiclesView,
    DriverProfileView
)

urlpatterns = [
    path('driver/dashboard/', DashboardView.as_view(), name='driver-dashboard'),
    path('driver/trips/', DriverTripsView.as_view(), name='driver-trips'),
    path('driver/trips/<int:trip_id>/', DriverTripDetailView.as_view(), name='driver-trip-detail'), 
    path('driver/vehicles/', DriverVehiclesView.as_view(), name='driver-vehicles'),
    path('driver/profile/', DriverProfileView.as_view(), name='driver-profile'),
]