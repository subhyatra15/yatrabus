from django.urls import path

from .views import (
    BusLocationUpdateAPIView,
    BusCurrentLocationAPIView,
    BusLocationHistoryAPIView,
)


urlpatterns = [

    path(
        "buses/<int:bus_id>/location/",
        BusLocationUpdateAPIView.as_view(),
        name="bus-location-update",
    ),

    path(
        "buses/<int:bus_id>/location/current/",
        BusCurrentLocationAPIView.as_view(),
        name="bus-location-current",
    ),

    path(
        "buses/<int:bus_id>/location/history/",
        BusLocationHistoryAPIView.as_view(),
        name="bus-location-history",
    ),
]