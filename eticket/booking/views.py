from decimal import Decimal
import uuid

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Booking, BookingSeat
from .serializers import BookingSerializer
from schedule.models import Schedule
from routes.models import RouteStop, RouteFare
from django.db.models import Prefetch
from appsettings.models import Settings

import json
import redis

from django.conf import settings
from rest_framework.views import APIView
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "A":
            return Booking.objects.all()
        return (
            Booking.objects.filter(customer=user)
            .select_related(
                "customer",
                "schedule",
                "schedule__route",
                "schedule__route__bus",
                "boarding_stop",
                "dropping_stop",
            )
            .prefetch_related(
                "booking_seats__seat",
            )
            .order_by("-created_at")
        )

    @action(detail=False, methods=["get"], url_path="verify")
    def verify(self, request):
        qr_token = request.query_params.get("qr_token")

        if not qr_token:
            return Response(
                {"message": "QR token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking = (
            Booking.objects.select_related(
                "customer",
                "schedule",
                "schedule__route",
                "schedule__route__bus",
                "boarding_stop",
                "dropping_stop",
            )
            .prefetch_related("booking_seats__seat","customer")
            .filter(qr_token=qr_token)
            .first()
        )

        if not booking:
            return Response(
                {"message": "Invalid QR code."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BookingSerializer(booking)

        return Response(
            {
                "message": "Ticket verified successfully.",
                "booking": serializer.data,
            }
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        boarding_stop_id = request.data.get("boardingstop")
        dropping_stop_id = request.data.get("droppingstop")
        
        # Validate that both stops are provided
        if not boarding_stop_id or not dropping_stop_id:
            return Response(
                {"message": "Both boarding stop and dropping stop are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the schedule with select_for_update to prevent race conditions
        try:
            schedule = Schedule.objects.select_for_update().get(
                id=request.data["schedule"]
            )
        except Schedule.DoesNotExist:
            return Response(
                {"message": "Schedule not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get the RouteStop instances and validate they belong to the route
        try:
            boarding_stop = RouteStop.objects.get(
                id=boarding_stop_id, 
                route=schedule.route
            )
            dropping_stop = RouteStop.objects.get(
                id=dropping_stop_id, 
                route=schedule.route
            )
        except RouteStop.DoesNotExist:
            return Response(
                {"message": "Invalid boarding or dropping stop for this route."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate that boarding stop comes before dropping stop in the route
        if boarding_stop.stop_order >= dropping_stop.stop_order:
            return Response(
                {"message": "Boarding stop must be before dropping stop."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get selected seats from request
        seats = request.data.get("booking_seats", [])

        if len(seats) == 0:
            return Response(
                {"message": "Please select at least one seat."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get seat objects to validate and get extra prices
        seat_ids = [item["seat"] for item in seats]
        seat_objects = Seat.objects.filter(id__in=seat_ids, bus=schedule.route.bus)
        
        if len(seat_objects) != len(seat_ids):
            return Response(
                {"message": "One or more selected seats do not belong to this bus."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create a dict for quick lookup of extra prices
        seat_extra_prices = {seat.id: seat.extra_price for seat in seat_objects}
        
        # Calculate available seats
        total_seats = schedule.route.bus.total_seats
        booked_seats_count = BookingSeat.objects.filter(
            booking__schedule=schedule,
            booking__booking_status__in=["PENDING", "PAID"]
        ).count()
        
        available_seats = total_seats - booked_seats_count
        
        if available_seats < len(seats):
            return Response(
                {"message": f"Not enough seats available. Only {available_seats} seats available."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if any specific seat is already booked
        already_booked_seats = BookingSeat.objects.filter(
            booking__schedule=schedule,
            seat_id__in=seat_ids,
            booking__booking_status__in=["PENDING", "PAID"]
        ).values_list('seat_id', flat=True)
        
        if already_booked_seats.exists():
            return Response(
                {"message": f"Seats {list(already_booked_seats)} are already booked."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate base fare based on the stops
        try:
            route_fare = RouteFare.objects.get(
                route=schedule.route,
                from_stop=boarding_stop,
                to_stop=dropping_stop
            )
            base_fare_per_seat = route_fare.fare
        except RouteFare.DoesNotExist:
            return Response(
                {"message": "Fare not configured for this route segment."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get settings from database
        try:
            settings = Settings.objects.first()  # Assuming you have a single settings instance
            if not settings:
                raise Settings.DoesNotExist()
            tax_percentage = settings.tax  # Should be a decimal like 0.13
            platform_cost_percentage = settings.platform_cost  # Should be a decimal like 0.05
        except Settings.DoesNotExist:
            return Response(
                {"message": "System settings not configured. Please contact support."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Calculate total amount with seat extra prices
        total_fare = Decimal('0')
        booking_seats_data = []
        discount = Decimal(request.data.get("discount", 0))
        
        # Get discount from request (assuming it's a flat amount)
        # If discount is percentage, you might want to adjust this logic
        
        for item in seats:
            seat_id = item["seat"]
            extra_price = seat_extra_prices.get(seat_id, Decimal('0'))
            fare_per_seat = base_fare_per_seat + extra_price
            total_fare += fare_per_seat
            
            booking_seats_data.append({
                'seat_id': seat_id,
                'price': fare_per_seat
            })
        
        # Apply discount (if it's a flat amount)
        if discount > total_fare:
            return Response(
                {"message": "Discount cannot exceed total fare."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        discounted_fare = total_fare - discount
        
        # Calculate platform fee and tax
        platform_fee = discounted_fare * platform_cost_percentage
        tax_amount = discounted_fare * tax_percentage
        
        # Calculate total
        total = discounted_fare + platform_fee + tax_amount

        # Create the booking
        booking = Booking.objects.create(
            booking_number=f"BK-{uuid.uuid4().hex[:10].upper()}",
            customer=request.user,
            schedule=schedule,
            boarding_stop=boarding_stop,
            dropping_stop=dropping_stop,
            subtotal=total_fare,  # Total fare without any deductions
            discount=discount,
            tax=tax_amount,
            platform_amount=platform_fee,
            total_amount=total,
            booking_status="PENDING",
        )

        # Create booking seats using bulk_create for efficiency
        booking_seats = []
        for seat_data in booking_seats_data:
            booking_seats.append(
                BookingSeat(
                    booking=booking,
                    seat_id=seat_data['seat_id'],
                    price=seat_data['price']
                )
            )
        
        BookingSeat.objects.bulk_create(booking_seats)

        serializer = BookingSerializer(booking)

        return Response(
            {
                "message": "Booking created successfully.",
                "data": serializer.data,
                "breakdown": {
                    "base_fare_per_seat": float(base_fare_per_seat),
                    "seat_extras": [
                        {
                            "seat_id": seat_data['seat_id'],
                            "extra_price": float(seat_extra_prices[seat_data['seat_id']])
                        }
                        for seat_data in booking_seats_data
                    ],
                    "total_fare": float(total_fare),
                    "discount": float(discount),
                    "discounted_fare": float(discounted_fare),
                    "platform_fee": float(platform_fee),
                    "tax": float(tax_amount),
                    "tax_percentage": float(tax_percentage * 100),
                    "total": float(total)
                }
            },
            status=status.HTTP_201_CREATED
        )


# User select seats:
redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


def seat_key(trip_id, seat_id):
    return f"trip:{trip_id}:seat:{seat_id}:selected"


class SelectSeatView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, trip_id, seat_id):

        key = seat_key(trip_id, seat_id)

        data = {
            "user_id": request.user.id,
            "name": request.user.fullName,
        }

        created = redis_client.set(
            key,
            json.dumps(data),
            nx=True,
            ex=600,  
        )

        if not created:

            existing = redis_client.get(key)

            existing_data = (
                json.loads(existing)
                if existing
                else None
            )

            return Response(
                {
                    "success": False,
                    "message": "Seat is already selected",
                    "selected_by": existing_data,
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Broadcast to everyone watching this trip
        channel_layer = get_channel_layer()

        async_to_sync(
            channel_layer.group_send
        )(
            f"trip_seats_{trip_id}",
            {
                "type": "seat_selected",
                "seat_id": seat_id,
                "user_id": request.user.id,
                "username": request.user.fullName,
            },
        )

        return Response(
            {
                "success": True,
                "seat_id": seat_id,
                "selected_by": request.user.id,
                "message": "Seat selected",
            },
            status=status.HTTP_200_OK,
        )


# Release Seat API:
class ReleaseSeatView(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, trip_id, seat_id):

        key = seat_key(trip_id, seat_id)

        value = redis_client.get(key)

        if not value:
            return Response({
                "success": True,
                "message": "Seat is already available",
            })

        data = json.loads(value)

        if data["user_id"] != request.user.id:

            return Response(
                {
                    "success": False,
                    "message": "You cannot release this seat",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        redis_client.delete(key)

        channel_layer = get_channel_layer()

        async_to_sync(
            channel_layer.group_send
        )(
            f"trip_seats_{trip_id}",
            {
                "type": "seat_available",
                "seat_id": seat_id,
            },
        )

        return Response({
            "success": True,
            "seat_id": seat_id,
            "message": "Seat released",
        })


# get selected seat
class SelectedSeatsView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):

        pattern = f"trip:{trip_id}:seat:*:selected"

        selected = []

        for key in redis_client.scan_iter(
            match=pattern
        ):

            value = redis_client.get(key)

            if not value:
                continue

            data = json.loads(value)

            parts = key.split(":")

            seat_id = parts[3]

            selected.append({
                "seat_id": seat_id,
                "user_id": data["user_id"],
                "is_mine": (
                    data["user_id"]
                    == request.user.id
                ),
                "ttl": redis_client.ttl(key),
            })

        return Response(selected)
