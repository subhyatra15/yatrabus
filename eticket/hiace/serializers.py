# hiace/serializers.py
from rest_framework import serializers
from .models import (
    Hiace, HiaceRoute, HiaceRouteStop, HiaceRouteFare,
    HiaceSchedule, HiaceSeat, HiaceBooking, HiaceBookingSeat
)


class HiaceSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(
        source="operator.fullName",
        read_only=True
    )

    class Meta:
        model = Hiace
        fields = [
            "id",
            "operator",
            "operator_name",
            "hiace_name",
            "hiace_number",
            "hiace_type",
            "total_seats",
            "seat_layout",
            "wifi",
            "charging",
            "ac",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "operator", "created_at", "updated_at")


class HiaceRouteStopSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = HiaceRouteStop
        fields = [
            "id",
            "city",
            "city_name",
            "stop_order",
            "arrival_offset",
            "departure_offset",
            "is_boarding",
            "is_dropping",
        ]


class HiaceRouteFareSerializer(serializers.ModelSerializer):
    from_stop_city = serializers.CharField(source="from_stop.city.name", read_only=True)
    to_stop_city = serializers.CharField(source="to_stop.city.name", read_only=True)

    class Meta:
        model = HiaceRouteFare
        fields = [
            "id",
            "from_stop",
            "from_stop_city",
            "to_stop",
            "to_stop_city",
            "fare",
        ]


class HiaceRouteSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(
        source="operator.fullName",
        read_only=True
    )
    hiace_name = serializers.CharField(
        source="hiace.hiace_name",
        read_only=True
    )
    source_city_name = serializers.CharField(
        source="source_city.name",
        read_only=True
    )
    destination_city_name = serializers.CharField(
        source="destination_city.name",
        read_only=True
    )
    stops = HiaceRouteStopSerializer(many=True, read_only=True)
    fares = HiaceRouteFareSerializer(many=True, read_only=True)

    class Meta:
        model = HiaceRoute
        fields = [
            "id",
            "operator",
            "operator_name",
            "hiace",
            "hiace_name",
            "source_city",
            "source_city_name",
            "destination_city",
            "destination_city_name",
            "distance",
            "duration",
            "status",
            "stops",
            "fares",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "operator", "created_at", "updated_at")


class HiaceScheduleSerializer(serializers.ModelSerializer):
    route_details = HiaceRouteSerializer(source="route", read_only=True)
    available_seats = serializers.SerializerMethodField()

    class Meta:
        model = HiaceSchedule
        fields = [
            "id",
            "route",
            "route_details",
            "departure_datetime",
            "arrival_datetime",
            "status",
            "available_seats",
            "created_at",
            "updated_at",
        ]

    def get_available_seats(self, obj):
        total_seats = obj.route.hiace.total_seats
        booked_seats = HiaceBookingSeat.objects.filter(
            booking__schedule=obj,
            booking__booking_status__in=["PENDING", "PAID"]
        ).count()
        return total_seats - booked_seats


class HiaceSeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = HiaceSeat
        fields = [
            "id",
            "hiace",
            "seat_number",
            "seat_type",
            "row",
            "col",
            "extra_price",
            "is_window",
        ]


class HiaceBookingSeatSerializer(serializers.ModelSerializer):
    seat_number = serializers.CharField(source="seat.seat_number", read_only=True)

    class Meta:
        model = HiaceBookingSeat
        fields = ["id", "seat", "seat_number", "price"]


class HiaceBookingSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.fullName",
        read_only=True
    )
    schedule_details = HiaceScheduleSerializer(source="schedule", read_only=True)
    booking_seats = HiaceBookingSeatSerializer(many=True, read_only=True)
    from_city = serializers.CharField(
        source="boarding_stop.city.name",
        read_only=True
    )
    to_city = serializers.CharField(
        source="dropping_stop.city.name",
        read_only=True
    )

    class Meta:
        model = HiaceBooking
        fields = [
            "id",
            "booking_number",
            "customer",
            "customer_name",
            "schedule",
            "schedule_details",
            "booking_status",
            "platform_amount",
            "subtotal",
            "discount",
            "tax",
            "total_amount",
            "qr_code",
            "qr_token",
            "boarding_stop",
            "dropping_stop",
            "from_city",
            "to_city",
            "booking_seats",
            "created_at",
            "expired_at",
        ]
        read_only_fields = ("id", "booking_number", "customer", "created_at")



class HiaceScheduleSerializer(serializers.ModelSerializer):
    route_details = HiaceRouteSerializer(source="route", read_only=True)
    available_seats = serializers.SerializerMethodField()
    hiace_name = serializers.CharField(source="route.hiace.hiace_name", read_only=True)
    hiace_number = serializers.CharField(source="route.hiace.hiace_number", read_only=True)
    hiace_type = serializers.CharField(source="route.hiace.hiace_type", read_only=True)
    total_seats = serializers.IntegerField(source="route.hiace.total_seats", read_only=True)
    source_city = serializers.CharField(source="route.source_city.name", read_only=True)
    destination_city = serializers.CharField(source="route.destination_city.name", read_only=True)
    bus = serializers.IntegerField(source="route.hiace.id", read_only=True)
    fare = serializers.SerializerMethodField()
    operator = serializers.IntegerField(source="route.operator.id", read_only=True)
    operator_name = serializers.CharField(source="route.operator.fullName", read_only=True)
    status = serializers.CharField(source="route.status", read_only=True)

    class Meta:
        model = HiaceSchedule
        fields = [
            "id",
            "route",
            "route_details",
            "departure_datetime",
            "arrival_datetime",
            "status",
            "available_seats",
            "hiace_name",
            "hiace_number",
            "hiace_type",
            "total_seats",
            "source_city",
            "destination_city",
            "bus",
            "fare",
            "operator",
            "operator_name",
            "created_at",
            "updated_at",
        ]

    def get_available_seats(self, obj):
        total_seats = obj.route.hiace.total_seats
        booked_seats = HiaceBookingSeat.objects.filter(
            booking__schedule=obj,
            booking__booking_status__in=["PENDING", "PAID"]
        ).count()
        return total_seats - booked_seats

    def get_fare(self, obj):
        try:
            # Get the route fare between source and destination
            source_stop = obj.route.stops.filter(
                city=obj.route.source_city,
                is_boarding=True
            ).first()
            dest_stop = obj.route.stops.filter(
                city=obj.route.destination_city,
                is_dropping=True
            ).first()
            
            if source_stop and dest_stop:
                fare_obj = HiaceRouteFare.objects.filter(
                    route=obj.route,
                    from_stop=source_stop,
                    to_stop=dest_stop
                ).first()
                if fare_obj:
                    return fare_obj.fare
            return None
        except:
            return None


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