from django.urls import path
from .views import DeviceListCreateView, DeviceDeleteView

urlpatterns = [
    path(
        "notification/token/",
        DeviceListCreateView.as_view(),
        name="device-list-create"
    ),

    path(
        "devices/<int:pk>/",
        DeviceDeleteView.as_view(),
        name="device-delete"
    ),
]