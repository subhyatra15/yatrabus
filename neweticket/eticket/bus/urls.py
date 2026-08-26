from rest_framework.routers import DefaultRouter
from .views import BusViewSet,RecommendedBusesView
from django.urls import path

router = DefaultRouter()

router.register("buses", BusViewSet, basename="bus")

urlpatterns = [
    path("buses/recommended/", RecommendedBusesView.as_view(), name="recommended-buses"),
]

urlpatterns += router.urls