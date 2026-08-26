from django.urls import re_path

from .consumers import BusLocationConsumer


websocket_urlpatterns = [
    re_path(
        r"ws/buses/(?P<bus_id>\d+)/location/$",
        BusLocationConsumer.as_asgi(),
    ),
]