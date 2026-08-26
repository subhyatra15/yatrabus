from django.urls import path

from .consumers import SeatConsumer
from bus_location.consumers import BusLocationConsumer


websocket_urlpatterns = [
    path(
        "ws/trips/<int:trip_id>/seats/",
        SeatConsumer.as_asgi(),
    ),

    path(
        "ws/buses/<int:bus_id>/location/",
        BusLocationConsumer.as_asgi(),
    ),
]