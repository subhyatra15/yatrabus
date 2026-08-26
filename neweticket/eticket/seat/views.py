from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied

from .models import Seat
from .serializers import SeatSerializer


class SeatViewSet(viewsets.ModelViewSet):
    serializer_class = SeatSerializer

    def get_permissions(self):
        if self.action in ["list",'retrieve']:
            return  [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        params = self.request.query_params

        queryset = Seat.objects.select_related(
            "bus",
            "bus__operator"
        ).order_by("id")

        # Filter by bus ID
        bus_id = params.get("bus")

        if bus_id:
            queryset = queryset.filter(bus_id=bus_id)

        if not user.is_authenticated:
            return queryset

        if user.role == "A":
            return queryset

        if user.role == "D":
            return queryset.filter(bus__operator=user)

        return Seat.objects.none()

    def perform_create(self, serializer):

        bus = serializer.validated_data["bus"]

        if (
            self.request.user.role != "A"
            and bus.operator != self.request.user
        ):
            raise PermissionDenied(
                "You can only add seats to your own buses."
            )

        serializer.save()

    def perform_update(self, serializer):

        bus = serializer.instance.bus

        if (
            self.request.user.role != "A"
            and bus.operator != self.request.user
        ):
            raise PermissionDenied(
                "You can only update seats of your own buses."
            )

        serializer.save()

    def perform_destroy(self, instance):

        if (
            self.request.user.role != "A"
            and instance.bus.operator != self.request.user
        ):
            raise PermissionDenied(
                "You can only delete seats of your own buses."
            )

        instance.delete()