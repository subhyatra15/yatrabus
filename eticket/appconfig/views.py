# eticket/appconfig/views.py
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import AppVersionConfig
from .serializers import AppVersionConfigSerializer


class AppVersionConfigViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AppVersionConfig.objects.all()
    serializer_class = AppVersionConfigSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        platform = self.request.query_params.get("platform")
        if platform:
            qs = qs.filter(platform=platform.lower())
        return qs