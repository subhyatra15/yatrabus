
from rest_framework.routers import DefaultRouter
from .views import AppVersionConfigViewSet

router = DefaultRouter()
router.register(r"app-version", AppVersionConfigViewSet, basename="app-version")

urlpatterns = router.urls