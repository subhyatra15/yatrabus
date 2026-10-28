from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import (
    BookingViewSet,
    SelectSeatView,
    ReleaseSeatView,
    SelectedSeatsView,
    DriverEarningsView
)


router = DefaultRouter()

router.register(
    "bookings",
    BookingViewSet,
    basename="booking",
)


urlpatterns = [
    path("driver/earnings/", DriverEarningsView.as_view(), name="driver-earnings"),
    # Select a seat
    path(
        "trips/<int:trip_id>/seats/<str:seat_id>/select/",
        SelectSeatView.as_view(),
        name="select-seat",
    ),

    # Release a selected seat
    path(
        "trips/<int:trip_id>/seats/<str:seat_id>/release/",
        ReleaseSeatView.as_view(),
        name="release-seat",
    ),

    # Get temporarily selected seats
    path(
        "trips/<int:trip_id>/seats/selected/",
        SelectedSeatsView.as_view(),
        name="selected-seats",
    ),
]


urlpatterns += router.urls
