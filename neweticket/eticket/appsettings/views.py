from rest_framework import viewsets
from .models import Settings
from .serializers import SettingsSerializers

class SettingsViewSet(viewsets.ModelViewSet):
    queryset = Settings.objects.filter().order_by("id")
    serializer_class = SettingsSerializers