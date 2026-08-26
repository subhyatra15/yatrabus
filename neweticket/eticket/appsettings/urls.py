
from rest_framework import routers

router = routers.DefaultRouter()
from .views import SettingsViewSet

router.register(r'settings',SettingsViewSet,basename='settings')

urlpatterns = router.urls