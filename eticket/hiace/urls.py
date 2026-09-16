from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HiaceViewSet,
    HiaceBookingViewSet, 
    HiaceScheduleViewSet,
    HiaceRouteViewSet,
    SeatViewSet,
    CreateHiaceRouteView,
    CreateHiaceScheduleView,
    SelectSeatView,
    ReleaseSeatView,
    SelectedSeatsView
)

router = DefaultRouter()
router.register(r'hiaces', HiaceViewSet, basename='hiaces')
router.register(r'hiace-bookings', HiaceBookingViewSet, basename='hiace-booking')
router.register(r'hiace-schedules', HiaceScheduleViewSet, basename='hiace-schedule')
router.register(r'hiace-routes', HiaceRouteViewSet, basename='hiace-route')

urlpatterns = [
    path(
    'hiace-seats/',
    SeatViewSet.as_view({
        'get': 'list',
        'post': 'create',
    }),
    name='hiace-seats'
    ),
    path(
        "hiace-routes/create/",
        CreateHiaceRouteView.as_view(),
        name="hiace-routes-create",
    ),
    path('hiace-schedule/', CreateHiaceScheduleView.as_view(), name='create-hiace-schedule'),
     # Select a seat
        path(
            "hiacetrips/<int:trip_id>/seats/<str:seat_id>/select/",
            SelectSeatView.as_view(),
            name="select-seat",
        ),
    
        # Release a selected seat
        path(
            "hiacetrips/<int:trip_id>/seats/<str:seat_id>/release/",
            ReleaseSeatView.as_view(),
            name="release-seat",
        ),
    
        # Get temporarily selected seats
        path(
            "hiacetrips/<int:trip_id>/seats/selected/",
            SelectedSeatsView.as_view(),
            name="selected-seats",
        ),
    path('', include(router.urls))


   
]

