from rest_framework.routers import DefaultRouter
from .views import SeatViewSet

router = DefaultRouter()

router.register("seats", SeatViewSet, basename="seat")

urlpatterns = router.urls