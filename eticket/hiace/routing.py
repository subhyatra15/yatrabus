from django.urls import path
from .consumers import HiaceSeatConsumer


websocket_urlpatterns = [
    path(
        "ws/hiacetrips/<int:trip_id>/seats/",
        HiaceSeatConsumer.as_asgi(),
    ),
]