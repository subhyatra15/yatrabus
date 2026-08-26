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