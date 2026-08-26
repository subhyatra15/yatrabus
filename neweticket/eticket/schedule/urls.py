from rest_framework.routers import DefaultRouter
from .views import ScheduleViewSet,ScheduleDetailsWithRouteStop,CreateBusScheduleView
from django.urls import path

router = DefaultRouter()

router.register(
    "schedules",
    ScheduleViewSet,
    basename="schedule"
)


urlpatterns = [
    path(
        "schedules/withroutestop/<int:pk>/",
        ScheduleDetailsWithRouteStop.as_view(),
        name="schedules_withroutestop",
    ),
    path('bus-schedules/', CreateBusScheduleView.as_view(), name='create-bus-schedule')
]

urlpatterns += router.urls