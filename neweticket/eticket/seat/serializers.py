from rest_framework import serializers
from .models import Seat
from bus.models import Bus


class SeatSerializer(serializers.ModelSerializer):

    bus_name = serializers.CharField(
        source="bus.bus_name",
        read_only=True
    )

    class Meta:
        model = Seat
        fields = [
            "id",
            "bus",
            "bus_name",
            "seat_number",
            "seat_type",
            "row",
            "col",
            "is_window",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
        ]

    def validate(self, attrs):
        bus = attrs.get("bus")
        seat_number = attrs.get("seat_number")

        queryset = Seat.objects.filter(
            bus=bus,
            seat_number=seat_number
        )

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                {
                    "seat_number": "Seat already exists for this bus."
                }
            )

        return attrs