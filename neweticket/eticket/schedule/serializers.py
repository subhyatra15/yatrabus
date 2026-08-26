from rest_framework import serializers

from .models import Schedule
from booking.models import BookingSeat
from seat.models import Seat



class ScheduleSerializer(serializers.ModelSerializer):
    bus = serializers.IntegerField(
        source="route.bus.id",
        read_only=True
    )

    operator = serializers.IntegerField(
        source="route.bus.operator.id",
        read_only=True
    )

    operator_name = serializers.CharField(
        source="route.bus.operator.fullName",
        read_only=True
    )

    operator_phone = serializers.CharField(
        source="route.bus.operator.phone",
        read_only=True
    )

    bus_name = serializers.CharField(
        source="route.bus.bus_name",
        read_only=True
    )

    bus_number = serializers.CharField(
        source="route.bus.bus_number",
        read_only=True
    )

    bus_type = serializers.CharField(
        source="route.bus.bus_type",
        read_only=True
    )

    total_seats = serializers.IntegerField(
        source="route.bus.total_seats",
        read_only=True
    )

    seat_layout = serializers.JSONField(
        source="route.bus.seat_layout",
        read_only=True
    )

    wifi = serializers.BooleanField(
        source="route.bus.wifi",
        read_only=True
    )

    charging = serializers.BooleanField(
        source="route.bus.charging",
        read_only=True
    )

    ac = serializers.BooleanField(
        source="route.bus.ac",
        read_only=True
    )

    source_city = serializers.CharField(
        source="route.source_city.name",
        read_only=True
    )

    destination_city = serializers.CharField(
        source="route.destination_city.name",
        read_only=True
    )

    available_seats = serializers.SerializerMethodField()

    booked_seats = serializers.SerializerMethodField()

    seats = serializers.SerializerMethodField()

    fare = serializers.SerializerMethodField()
    
    class Meta:
        model = Schedule
        fields = [
            "id",
            "route",
            "bus",
            "operator",
            "operator_name",
            "operator_phone",
            "bus_name",
            "bus_number",
            "bus_type",
            "total_seats",
            "seat_layout",
            "wifi",
            "charging",
            "ac",
            "fare",
            "source_city",
            "destination_city",
            "departure_datetime",
            "arrival_datetime",
            "available_seats",
            "booked_seats",
            "seats",
            "status",
            "created_at",
            "updated_at",
        ]

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):

        if attrs["arrival_datetime"] <= attrs["departure_datetime"]:
            raise serializers.ValidationError(
                "Arrival datetime must be after departure datetime."
            )

        return attrs


    def get_overlapping_booked_seat_ids(self, obj):
        boarding_stop = self.context.get(
            "boarding_stop_map", {}
        ).get(obj.id)

        dropping_stop = self.context.get(
            "dropping_stop_map", {}
        ).get(obj.id)

        if not boarding_stop or not dropping_stop:
            return set()

        new_start = boarding_stop.stop_order
        new_end = dropping_stop.stop_order

        booked_ids = set()

        bookings = BookingSeat.objects.filter(
            booking__schedule=obj,
            booking__booking_status__in=["PENDING", "PAID"]
        ).select_related(
            "booking__boarding_stop",
            "booking__dropping_stop"
        )

        for booking_seat in bookings:
            existing_start = booking_seat.booking.boarding_stop.stop_order
            existing_end = booking_seat.booking.dropping_stop.stop_order

            if existing_start < new_end and new_start < existing_end:
                booked_ids.add(booking_seat.seat_id)

        return booked_ids

    def get_booked_seats(self, obj):
        return len(self.get_overlapping_booked_seat_ids(obj))


    def get_available_seats(self, obj):
        total = obj.route.bus.total_seats
        booked = len(self.get_overlapping_booked_seat_ids(obj))
        return total - booked


    def get_seats(self, obj):
        booked_ids = self.get_overlapping_booked_seat_ids(obj)

        seats = Seat.objects.filter(
            bus=obj.route.bus
        ).order_by("seat_number")

        fare = self.get_fare(obj)

        return [
            {
                "id": seat.id,
                "seat_number": seat.seat_number,
                "status": "BOOKED" if seat.id in booked_ids else "AVAILABLE",
                "price": fare,
            }
            for seat in seats
        ]

    def get_fare(self, obj):
        return self.context.get(
            "fare_map",
            {}
        ).get(obj.id)
    
   

class ScheduleGenerateSerializer(serializers.Serializer):

    route = serializers.IntegerField()

    bus = serializers.IntegerField()

    departure_time = serializers.TimeField()

    arrival_time = serializers.TimeField()

    start_date = serializers.DateField()

    end_date = serializers.DateField()

    fare = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    repeat = serializers.ChoiceField(
        choices=[
            ("DAILY", "Daily"),
            ("WEEKLY", "Weekly"),
        ]
    )


class CreateScheduleSerializer(serializers.Serializer):
    """Serializer for creating a new schedule (Bus)"""
    route = serializers.IntegerField()
    vehicle = serializers.IntegerField()
    departure_datetime = serializers.DateTimeField()
    arrival_datetime = serializers.DateTimeField()
    status = serializers.ChoiceField(
        choices=["ACTIVE", "INACTIVE", "CANCELLED"],
        default="ACTIVE"
    )
    repeat_type = serializers.ChoiceField(
        choices=["none", "daily", "weekly", "monthly"],
        default="none",
        required=False
    )
    repeat_days = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    repeat_end_date = serializers.DateTimeField(
        required=False,
        allow_null=True
    )

    def validate(self, attrs):
        if attrs["arrival_datetime"] <= attrs["departure_datetime"]:
            raise serializers.ValidationError(
                "Arrival datetime must be after departure datetime."
            )
        return attrs


class CreateHiaceScheduleSerializer(serializers.Serializer):
    route = serializers.IntegerField()
    vehicle = serializers.IntegerField()
    departure_datetime = serializers.DateTimeField()
    arrival_datetime = serializers.DateTimeField()
    status = serializers.ChoiceField(
        choices=["ACTIVE", "INACTIVE", "CANCELLED"],
        default="ACTIVE"
    )
    repeat_type = serializers.ChoiceField(
        choices=["none", "daily", "weekly", "monthly"],
        default="none",
        required=False
    )
    repeat_days = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    repeat_end_date = serializers.DateTimeField(
        required=False,
        allow_null=True
    )

    def validate(self, attrs):
        if attrs["arrival_datetime"] <= attrs["departure_datetime"]:
            raise serializers.ValidationError(
                "Arrival datetime must be after departure datetime."
            )
        return attrs