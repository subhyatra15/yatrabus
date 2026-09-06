from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import RouteViewSet,BusRouteViewSet, RouteStopView, PopularRouteView, CalculatePriceView, CreateBusRouteView

router = DefaultRouter()
router.register(
    "routes",
    RouteViewSet,
    basename="route"
)


router.register(r'bus-routes', BusRouteViewSet, basename='bus-route')

urlpatterns = [
    path("routes/popular/", PopularRouteView.as_view(), name="popular-routes"),
    path("routes/routestop/", RouteStopView.as_view(), name="routestop"),
    path("routes/priceperseat/", CalculatePriceView.as_view(), name="routestop"),
    path("routes/create/", CreateBusRouteView.as_view(), name="route_create"),

]


urlpatterns += router.urls