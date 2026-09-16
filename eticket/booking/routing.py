from django.urls import path

from .consumers import SeatConsumer
from hiace.consumers import HiaceSeatConsumer
from bus_location.consumers import BusLocationConsumer


websocket_urlpatterns = [
    # -------- Bus seat selection --------
    path(
        "ws/trips/<int:trip_id>/seats/",
        SeatConsumer.as_asgi(),
    ),

    # -------- Hiace seat selection --------
    path(
        "ws/hiacetrips/<int:trip_id>/seats/",
        HiaceSeatConsumer.as_asgi(),
    ),

    # -------- Bus live location --------
    path(
        "ws/buses/<int:bus_id>/location/",
        BusLocationConsumer.as_asgi(),
    ),
]