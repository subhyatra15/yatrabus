from rest_framework import serializers

from .models import Booking, BookingSeat
from schedule.models import Schedule
from schedule.serializers import ScheduleSerializer
from routes.models import RouteStop
from eticketauth.serializers import UserSerializer


class BookingSeatSerializer(serializers.ModelSerializer):
    seat_number = serializers.CharField(source="seat.seat_number",read_only=True)
    class Meta:
        model = BookingSeat
        fields = (
            "seat",
            "price",
            "seat_number"
        )


class RouteStopSerializer(serializers.ModelSerializer):
    city = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = RouteStop
        fields = (
            "id",
            "city",
            "stop_order",
        )


class BookingSerializer(serializers.ModelSerializer):
    # GET Response
    schedule = ScheduleSerializer(read_only=True)
    boarding_stop = RouteStopSerializer(read_only=True)
    dropping_stop = RouteStopSerializer(read_only=True)

    booking_seats = BookingSeatSerializer(many=True, read_only=True)

    customer = UserSerializer(read_only=True)

    # POST Request
    schedule_id = serializers.PrimaryKeyRelatedField(
        queryset=Schedule.objects.all(),
        source="schedule",
        write_only=True,
    )

    boarding_stop_id = serializers.PrimaryKeyRelatedField(
        queryset=RouteStop.objects.all(),
        source="boarding_stop",
        write_only=True,
    )

    dropping_stop_id = serializers.PrimaryKeyRelatedField(
        queryset=RouteStop.objects.all(),
        source="dropping_stop",
        write_only=True,
    )

    class Meta:
        model = Booking
        fields = (
            "id",
            "booking_number",
            "customer",
            "qr_token",
            # GET
            "schedule",
            "boarding_stop",
            "dropping_stop",

            # POST
            "schedule_id",
            "boarding_stop_id",
            "dropping_stop_id",

            "booking_status",
            "platform_amount",
            "subtotal",
            "discount",
            "tax",
            "total_amount",
            "booking_seats",
            "expired_at",
            "created_at",
        )

        read_only_fields = (
            "booking_number",
            "customer",
            "schedule",
            "boarding_stop",
            "dropping_stop",
            "platform_amount",
            "subtotal",
            "discount",
            "tax",
            "total_amount",
            "created_at",
            "expired_at"
        )

    def validate(self, attrs):
        boarding = attrs.get("boarding_stop")
        dropping = attrs.get("dropping_stop")
        schedule = attrs.get("schedule")

        if boarding and dropping:
            if boarding.route_id != dropping.route_id:
                raise serializers.ValidationError(
                    "Boarding and dropping stops must belong to the same route."
                )

            if boarding.stop_order >= dropping.stop_order:
                raise serializers.ValidationError(
                    "Dropping stop must come after boarding stop."
                )

        if schedule and boarding:
            if boarding.route_id != schedule.route_id:
                raise serializers.ValidationError(
                    "Boarding stop does not belong to this schedule."
                )

        if schedule and dropping:
            if dropping.route_id != schedule.route_id:
                raise serializers.ValidationError(
                    "Dropping stop does not belong to this schedule."
                )

        return attrs




class EarningSeatSerializer(serializers.ModelSerializer):
    seat_number = serializers.CharField(source="seat.seat_number", read_only=True)

    class Meta:
        model = BookingSeat
        fields = ["id", "seat_number", "price"]


class EarningBookingSerializer(serializers.ModelSerializer):
    booking_number = serializers.CharField(read_only=True)
    customer_name = serializers.CharField(source="customer.fullName", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    schedule_id = serializers.IntegerField(source="schedule.id", read_only=True)
    route = serializers.SerializerMethodField()
    departure_datetime = serializers.DateTimeField(
        source="schedule.departure_datetime", read_only=True
    )
    vehicle_name = serializers.SerializerMethodField()
    vehicle_number = serializers.SerializerMethodField()
    seats = EarningSeatSerializer(source="booking_seats", many=True, read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "booking_number",
            "customer_name",
            "customer_phone",
            "schedule_id",
            "route",
            "departure_datetime",
            "vehicle_name",
            "vehicle_number",
            "booking_status",
            "subtotal",
            "discount",
            "tax",
            "platform_amount",
            "total_amount",
            "seats",
            "created_at",
        ]

    def get_route(self, obj):
        return f"{obj.schedule.route.source_city.name} → {obj.schedule.route.destination_city.name}"

    def get_vehicle_name(self, obj):
        bus = getattr(obj.schedule.route, "bus", None)
        return bus.bus_name if bus else "N/A"

    def get_vehicle_number(self, obj):
        bus = getattr(obj.schedule.route, "bus", None)
        return bus.bus_number if bus else "N/A"