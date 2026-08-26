from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied

from .models import City
from .serializers import CitySerializer


class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer

    def get_permissions(self):
        # Public can view cities
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]

        # Login required for create/update/delete
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        if self.request.user.role != "A":
            raise PermissionDenied(
                "Only admin can create cities."
            )

        serializer.save()

    def perform_update(self, serializer):
        if self.request.user.role != "A":
            raise PermissionDenied(
                "Only admin can update cities."
            )

        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.role != "A":
            raise PermissionDenied(
                "Only admin can delete cities."
            )

        instance.delete()