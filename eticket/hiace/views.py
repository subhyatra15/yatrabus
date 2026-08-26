from decimal import Decimal
import uuid

from django.db import transaction
from django.db.models import Q, Count
from rest_framework import status, viewsets, filters, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from appsettings.models import Settings
from rest_framework.exceptions import ValidationError
import traceback
from datetime import timedelta

from .models import (
    Hiace, HiaceRoute, HiaceRouteStop, HiaceRouteFare,
    HiaceSchedule, HiaceSeat, HiaceBooking, HiaceBookingSeat
)

from city.models import City
from .serializers import (
    HiaceSerializer, HiaceRouteSerializer, HiaceScheduleSerializer,
    HiaceBookingSerializer , HiaceSeatSerializer,CreateHiaceScheduleSerializer
)



class HiaceViewSet(viewsets.ModelViewSet):
    serializer_class = HiaceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Hiace.objects.filter(
            operator=self.request.user
        ).order_by("id")

    def perform_create(self, serializer):
        serializer.save(operator=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            "message": "Successfully Get Hiace Data",
            "data": serializer.data
        })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            serializer.save(operator=request.user)

            return Response({
                "message": "Hiace Created Successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response({
            "message": "Validation Error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return Response({
                "message": "Hiace Updated Successfully",
                "data": serializer.data
            })

        return Response({
            "message": "Validation Error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            return Response({
                "message": "Hiace Updated Successfully",
                "data": serializer.data
            })

        return Response({
            "message": "Validation Error",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class HiaceScheduleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HiaceScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['route__source_city__name', 'route__destination_city__name']
    ordering_fields = ['departure_datetime', 'arrival_datetime']

    def get_queryset(self):
        user = self.request.user
        hiace_id = self.request.query_params.get('hiace')
        queryset = HiaceSchedule.objects.filter(status='ACTIVE')
        
        if user.role == 'D':
            queryset = queryset.filter(route__operator = user)

        if hiace_id:
            queryset = queryset.filter(route__hiace = hiace_id)

        # Filter by source city
        source = self.request.query_params.get('source')
        if source:
            queryset = queryset.filter(
                Q(route__source_city__name__icontains=source)
            )

        
        
        # Filter by destination city
        destination = self.request.query_params.get('destination')
        if destination:
            queryset = queryset.filter(
                Q(route__destination_city__name__icontains=destination)
            )
        
        # Filter by date
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(
                departure_datetime__date=date
            )
        
        return queryset.select_related(
            'route',
            'route__source_city',
            'route__destination_city',
            'route__hiace',
            'route__operator',
        ).prefetch_related(
            'route__stops',
            'route__fares',
        ).order_by('departure_datetime')

    @action(detail=False, methods=['get'], url_path='withroutestop')
    def with_route_stop(self, request):
        schedule_id = request.query_params.get('schedule_id')
        if not schedule_id:
            return Response(
                {'error': 'schedule_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get the schedule
            schedule = HiaceSchedule.objects.get(id=schedule_id)
            
            # Get route stops
            route_id = request.query_params.get('routeid')
            boarding_city = request.query_params.get('boardingcity')
            dropping_city = request.query_params.get('droppingcity')
            
            if not route_id:
                return Response(
                    {'error': 'routeid parameter is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get route
            try:
                route = HiaceRoute.objects.get(id=route_id)
            except HiaceRoute.DoesNotExist:
                return Response(
                    {'error': 'Route not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get stops
            stops = HiaceRouteStop.objects.filter(route=route).order_by('stop_order')
            
            # Get boarding and dropping stops
            boarding_stop = None
            dropping_stop = None
            
            if boarding_city:
                boarding_stop = stops.filter(city__name__icontains=boarding_city, is_boarding=True).first()
            
            if dropping_city:
                dropping_stop = stops.filter(city__name__icontains=dropping_city, is_dropping=True).first()
            
            # Get fare between boarding and dropping stops
            fare = None
            if boarding_stop and dropping_stop:
                fare_obj = HiaceRouteFare.objects.filter(
                    route=route,
                    from_stop=boarding_stop,
                    to_stop=dropping_stop
                ).first()
                if fare_obj:
                    fare = fare_obj.fare
            
            # Get booked seats for this schedule
            booked_seats = HiaceBookingSeat.objects.filter(
                booking__schedule=schedule,
                booking__booking_status__in=['PENDING', 'PAID']
            ).values_list('seat_id', flat=True)
            
     
            all_seats = HiaceSeat.objects.filter(hiace=route.hiace)
            
            # Format seat data
            seat_data = []
            for seat in all_seats:
                seat_data.append({
                    'id': seat.id,
                    'seat_number': seat.seat_number,
                    'status': 'BOOKED' if seat.id in booked_seats else 'AVAILABLE',
                    'price': float(fare) if fare else 0,
                    'seat_type': seat.seat_type,
                    'row': seat.row,
                    'col': seat.col,
                    'is_window': seat.is_window,
                })
            
            # Build response data
            data = {
                'id': schedule.id,
                'route': schedule.route.id,
                'source_city': schedule.route.source_city.name,
                'destination_city': schedule.route.destination_city.name,
                'departure_datetime': schedule.departure_datetime,
                'arrival_datetime': schedule.arrival_datetime,
                'bus': schedule.route.hiace.id,
                'bus_name': schedule.route.hiace.hiace_name,
                'bus_number': schedule.route.hiace.hiace_number,
                'bus_type': schedule.route.hiace.hiace_type,
                'total_seats': schedule.route.hiace.total_seats,
                'available_seats': schedule.route.hiace.total_seats - len(booked_seats),
                'fare': float(fare) if fare else 0,
                'operator': schedule.route.operator.id,
                'operator_name': schedule.route.operator.fullName,
                'operator_phone': getattr(schedule.route.operator, 'phone', 'N/A'),
                'ac': schedule.route.hiace.ac,
                'wifi': schedule.route.hiace.wifi,
                'charging': schedule.route.hiace.charging,
                'status': schedule.status,
                'seat_layout': schedule.route.hiace.seat_layout,
                'stops': [
                    {
                        'id': stop.id,
                        'city': stop.city.id,
                        'city_name': stop.city.name,
                        'stop_order': stop.stop_order,
                        'arrival_offset': str(stop.arrival_offset),
                        'departure_offset': str(stop.departure_offset),
                        'is_boarding': stop.is_boarding,
                        'is_dropping': stop.is_dropping,
                    }
                    for stop in stops
                ],
                'seats': seat_data,
            }
            
            return Response({'data': data})
            
        except HiaceSchedule.DoesNotExist:
            return Response(
                {'error': 'Schedule not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class HiaceBookingViewSet(viewsets.ModelViewSet):
    serializer_class = HiaceBookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = HiaceBooking.objects.all()
        
        # Filter by user role
        if user.role != "A":
            queryset = queryset.filter(customer=user)
        
        # Apply source filter
        source = self.request.query_params.get('source')
        if source:
            queryset = queryset.filter(
                Q(schedule__route__source_city__name__icontains=source) |
                Q(boarding_stop__city__name__icontains=source)
            )
        
        # Apply destination filter
        destination = self.request.query_params.get('destination')
        if destination:
            queryset = queryset.filter(
                Q(schedule__route__destination_city__name__icontains=destination) |
                Q(dropping_stop__city__name__icontains=destination)
            )
        
        # Apply date filter
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(
                schedule__departure_datetime__date=date
            )
        
        # Apply status filter
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(booking_status=status_param.upper())
        
        return queryset.select_related(
            "customer",
            "schedule",
            "schedule__route",
            "schedule__route__hiace",
            "boarding_stop",
            "dropping_stop",
        ).prefetch_related(
            "hiace_booking_seats__seat",
        ).order_by("-created_at")

    @action(detail=False, methods=["get"], url_path="verify")
    def verify(self, request):
        qr_token = request.query_params.get("qr_token")

        if not qr_token:
            return Response(
                {"message": "QR token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking = (
            HiaceBooking.objects.select_related(
                "customer",
                "schedule",
                "schedule__route",
                "schedule__route__hiace",
                "boarding_stop",
                "dropping_stop",
            )
            .prefetch_related("hiace_booking_seats__seat")
            .filter(qr_token=qr_token)
            .first()
        )

        if not booking:
            return Response(
                {"message": "Invalid QR code."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = HiaceBookingSerializer(booking)

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

        # Validate stops
        if not boarding_stop_id or not dropping_stop_id:
            return Response(
                {"message": "Both boarding stop and dropping stop are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get schedule with lock to prevent race conditions
        try:
            schedule = HiaceSchedule.objects.select_for_update().select_related(
                "route",
                "route__hiace"
            ).get(id=request.data.get("schedule"))
        except HiaceSchedule.DoesNotExist:
            return Response(
                {"message": "Schedule not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate boarding and dropping stops
        try:
            boarding_stop = HiaceRouteStop.objects.get(
                id=boarding_stop_id,
                route=schedule.route
            )

            dropping_stop = HiaceRouteStop.objects.get(
                id=dropping_stop_id,
                route=schedule.route
            )
        except HiaceRouteStop.DoesNotExist:
            return Response(
                {"message": "Invalid boarding or dropping stop for this route."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Boarding must come before dropping
        if boarding_stop.stop_order >= dropping_stop.stop_order:
            return Response(
                {"message": "Boarding stop must be before dropping stop."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Selected seats
        seats = request.data.get("booking_seats", [])

        if not seats:
            return Response(
                {"message": "Please select at least one seat."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---------------------------------------------------------
        # Validate seats belong to this Hiace
        # ---------------------------------------------------------

        seat_ids = [item.get("seat") for item in seats]

        if None in seat_ids:
            return Response(
                {"message": "Invalid seat data."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Change HiaceSeat to your actual Hiace seat model name
        seat_objects = HiaceSeat.objects.filter(
            id__in=seat_ids,
            hiace=schedule.route.hiace
        )

        if seat_objects.count() != len(seat_ids):
            return Response(
                {"message": "One or more selected seats do not belong to this Hiace."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Prevent duplicate seat IDs in same request
        if len(set(seat_ids)) != len(seat_ids):
            return Response(
                {"message": "Duplicate seats cannot be selected."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Seat extra prices
        seat_extra_prices = {
            seat.id: seat.extra_price or Decimal("0.00")
            for seat in seat_objects
        }

        # ---------------------------------------------------------
        # Check available seats
        # ---------------------------------------------------------

        total_seats = schedule.route.hiace.total_seats

        booked_seats_count = HiaceBookingSeat.objects.filter(
            booking__schedule=schedule,
            booking__booking_status__in=["PENDING", "PAID"]
        ).count()

        available_seats = total_seats - booked_seats_count

        if available_seats < len(seats):
            return Response(
                {
                    "message": (
                        f"Not enough seats available. "
                        f"Only {available_seats} seats available."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---------------------------------------------------------
        # Check individual seats
        # ---------------------------------------------------------

        already_booked_seats = HiaceBookingSeat.objects.filter(
            booking__schedule=schedule,
            seat_id__in=seat_ids,
            booking__booking_status__in=["PENDING", "PAID"]
        ).values_list("seat_id", flat=True)

        already_booked_seats = list(already_booked_seats)

        if already_booked_seats:
            return Response(
                {
                    "message": (
                        f"Seats {already_booked_seats} are already booked."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---------------------------------------------------------
        # Get route fare
        # ---------------------------------------------------------

        try:
            route_fare = HiaceRouteFare.objects.get(
                route=schedule.route,
                from_stop=boarding_stop,
                to_stop=dropping_stop
            )

            base_fare_per_seat = route_fare.fare

        except HiaceRouteFare.DoesNotExist:
            return Response(
                {"message": "Fare not configured for this route segment."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---------------------------------------------------------
        # Get system settings
        # ---------------------------------------------------------

        try:
            settings = Settings.objects.first()

            if not settings:
                raise Settings.DoesNotExist

            tax_percentage = settings.tax
            platform_cost_percentage = settings.platform_cost

        except Settings.DoesNotExist:
            return Response(
                {
                    "message": (
                        "System settings not configured. "
                        "Please contact support."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # ---------------------------------------------------------
        # Calculate fare
        # ---------------------------------------------------------

        total_fare = Decimal("0.00")
        booking_seats_data = []

        discount = Decimal(str(request.data.get("discount", "0")))

        if discount < 0:
            return Response(
                {"message": "Discount cannot be negative."},
                status=status.HTTP_400_BAD_REQUEST
            )

        for item in seats:

            seat_id = item["seat"]

            extra_price = seat_extra_prices.get(
                seat_id,
                Decimal("0.00")
            )

            fare_per_seat = (
                base_fare_per_seat +
                extra_price
            )

            total_fare += fare_per_seat

            booking_seats_data.append(
                {
                    "seat_id": seat_id,
                    "price": fare_per_seat
                }
            )

        # ---------------------------------------------------------
        # Discount
        # ---------------------------------------------------------

        if discount > total_fare:
            return Response(
                {"message": "Discount cannot exceed total fare."},
                status=status.HTTP_400_BAD_REQUEST
            )

        discounted_fare = total_fare - discount

        # ---------------------------------------------------------
        # Platform fee and tax
        # ---------------------------------------------------------

        platform_fee = (
            discounted_fare *
            platform_cost_percentage
        )

        tax_amount = (
            discounted_fare *
            tax_percentage
        )

        # ---------------------------------------------------------
        # Final total
        # ---------------------------------------------------------

        total = (
            discounted_fare +
            platform_fee +
            tax_amount
        )

        # ---------------------------------------------------------
        # Create booking
        # ---------------------------------------------------------

        booking = HiaceBooking.objects.create(
            booking_number=f"HK-{uuid.uuid4().hex[:10].upper()}",
            customer=request.user,
            schedule=schedule,
            boarding_stop=boarding_stop,
            dropping_stop=dropping_stop,

            subtotal=total_fare,
            discount=discount,
            tax=tax_amount,
            platform_amount=platform_fee,
            total_amount=total,

            booking_status="PENDING",
        )

        # ---------------------------------------------------------
        # Create booking seats
        # ---------------------------------------------------------

        booking_seats = []

        for seat_data in booking_seats_data:
            booking_seats.append(
                HiaceBookingSeat(
                    booking=booking,
                    seat_id=seat_data["seat_id"],
                    price=seat_data["price"]
                )
            )

        HiaceBookingSeat.objects.bulk_create(booking_seats)

        # ---------------------------------------------------------
        # Response
        # ---------------------------------------------------------

        serializer = HiaceBookingSerializer(booking)

        return Response(
            {
                "message": "Hiace booking created successfully.",
                "data": serializer.data,
                "breakdown": {
                    "base_fare_per_seat": float(base_fare_per_seat),

                    "seat_extras": [
                        {
                            "seat_id": seat_data["seat_id"],
                            "extra_price": float(
                                seat_extra_prices[
                                    seat_data["seat_id"]
                                ]
                            )
                        }
                        for seat_data in booking_seats_data
                    ],

                    "total_fare": float(total_fare),
                    "discount": float(discount),
                    "discounted_fare": float(discounted_fare),

                    "platform_fee": float(platform_fee),
                    "tax": float(tax_amount),

                    "tax_percentage": float(
                        tax_percentage * 100
                    ),

                    "platform_percentage": float(
                        platform_cost_percentage * 100
                    ),

                    "total": float(total)
                }
            },
            status=status.HTTP_201_CREATED
        )


class HiaceRouteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HiaceRouteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HiaceRoute.objects.filter(status='ACTIVE')

    @action(detail=False, methods=['get'], url_path='routestop')
    def get_route_stops(self, request):
        """
        Get stops for a specific route
        Query params: routeid
        """
        route_id = request.query_params.get('routeid')
        if not route_id:
            return Response(
                {'error': 'routeid parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            route = HiaceRoute.objects.get(id=route_id)
            stops = HiaceRouteStop.objects.filter(route=route).order_by('stop_order')
            
            stops_data = []
            for stop in stops:
                stops_data.append({
                    'id': stop.id,
                    'city': stop.city.id,
                    'city_name': stop.city.name,
                    'stop_order': stop.stop_order,
                    'arrival_offset': str(stop.arrival_offset),
                    'departure_offset': str(stop.departure_offset),
                    'is_boarding': stop.is_boarding,
                    'is_dropping': stop.is_dropping,
                })
            
            return Response({
                'data': stops_data,
                'route': {
                    'id': route.id,
                    'source': route.source_city.name,
                    'destination': route.destination_city.name,
                }
            })
        except HiaceRoute.DoesNotExist:
            return Response(
                {'error': 'Route not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='priceperseat')
    def get_price_per_seat(self, request):
        """
        Get price per seat between two stops
        Query params: route, boardingstop, droppingstop
        """
        route_id = request.query_params.get('route')
        boarding_stop_id = request.query_params.get('boardingstop')
        dropping_stop_id = request.query_params.get('droppingstop')
        
        if not all([route_id, boarding_stop_id, dropping_stop_id]):
            return Response(
                {'error': 'route, boardingstop, and droppingstop parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            route = HiaceRoute.objects.get(id=route_id)
            boarding_stop = HiaceRouteStop.objects.get(id=boarding_stop_id, route=route)
            dropping_stop = HiaceRouteStop.objects.get(id=dropping_stop_id, route=route)
            
            if boarding_stop.stop_order >= dropping_stop.stop_order:
                return Response(
                    {'error': 'Boarding stop must be before dropping stop'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            fare_obj = HiaceRouteFare.objects.filter(
                route=route,
                from_stop=boarding_stop,
                to_stop=dropping_stop
            ).first()
            
            if fare_obj:
                return Response({
                    'priceperseat': fare_obj.fare,
                    'currency': 'NPR',
                    'from_stop': boarding_stop.city.name,
                    'to_stop': dropping_stop.city.name,
                })
            else:
                return Response(
                    {'error': 'Fare not found for this route segment'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except HiaceRoute.DoesNotExist:
            return Response(
                {'error': 'Route not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except HiaceRouteStop.DoesNotExist:
            return Response(
                {'error': 'Stop not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# Seats ViewSet
class SeatViewSet(viewsets.ModelViewSet): 
    serializer_class = HiaceSeatSerializer
    def get_queryset(self):
        hiaceid = self.request.query_params.get("hiace")
        
        queryset = HiaceSeat.objects.all()
        if hiaceid:
            queryset = queryset.filter(hiace_id=hiaceid)
            
        return queryset

    def perform_create(self, serializer):

        hiace = serializer.validated_data.get("hiace")

        if hiace is None:
            raise ValidationError("Hiace is required.")

        if (
            self.request.user.role != "A"
            and hiace.operator != self.request.user
        ):
            raise PermissionDenied(
                "You can only add seats to your own hiaces."
            )

        serializer.save()


# utils to convertStrToDuration
def convertStrToDuration(duration):
    hours,minutes,seconds = map(int,duration.split(":"))
    duration_val = timedelta(
        hours=hours,
        minutes=minutes,
        seconds=seconds
    )

    return duration_val

# Create Route,RouteStop & Routefare
class CreateHiaceRouteView(views.APIView):
    @transaction.atomic
    def post(self, request):
        user = request.user

        if user.role != "D":
            return Response(
                {
                    "message": "User must be an operator.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data

        try:
            hiace = Hiace.objects.filter(id=data.get("vehicle")).first()
            print("+++++++++++++++++++++++++++",hiace)
            route = HiaceRoute.objects.create(
                hiace=hiace,
                operator = user,
                source_city_id=data.get("source_city"),
                destination_city_id=data.get("destination_city"),
                distance=data.get("distance"),
                duration=convertStrToDuration(data.get("duration")),
            )

            # Create Stops
            routes_ids = []
            for stop in data.get("stops", []):
                obj = HiaceRouteStop.objects.create(
                    route=route,
                    city_id=stop.get("city"),
                    stop_order=stop.get("stop_order"),
                    arrival_offset=convertStrToDuration(stop.get("arrival_offset")),
                    departure_offset=convertStrToDuration(stop.get("departure_offset")),
                    is_boarding=stop.get("is_boarding", True),
                    is_dropping=stop.get("is_dropping", True),
                )
                routes_ids.append(obj.id)

            # Create Fares
            for index, fare in enumerate(data.get("fares", [])):
                if index + 1 >= len(routes_ids):
                    break
                HiaceRouteFare.objects.create(
                    route=route,
                    from_stop_id=routes_ids[index],
                    to_stop_id=routes_ids[index + 1],
                    fare=fare.get("fare"),
                )

            return Response(
                {
                    "message": "Route created successfully.",
                    "route_id": route.id,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            traceback.print_exc()
            return Response(
                {
                    "message": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        

class CreateHiaceScheduleView(views.APIView):
    """
    API View to create a new Hiace Schedule
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        # Check if user is a driver/operator
        if user.role != 'D':
            return Response(
                {'error': 'Access denied. Only operators can create schedules.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate input
        serializer = CreateHiaceScheduleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = serializer.validated_data
        
        try:
            # Get route and vehicle
            route = HiaceRoute.objects.get(id=validated_data['route'])
            vehicle = Hiace.objects.get(id=validated_data['vehicle'])
            
            # Check if route belongs to user
            if route.operator != user:
                return Response(
                    {'error': 'You can only create schedules for your own routes.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if vehicle belongs to user
            if vehicle.operator != user:
                return Response(
                    {'error': 'You can only create schedules for your own vehicles.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Create schedule
            schedule = HiaceSchedule.objects.create(
                route=route,
                departure_datetime=validated_data['departure_datetime'],
                arrival_datetime=validated_data['arrival_datetime'],
                status=validated_data.get('status', 'ACTIVE')
            )

            # Handle repeat schedules
            repeat_type = validated_data.get('repeat_type', 'none')
            if repeat_type != 'none':
                self.create_repeat_schedules(
                    schedule, 
                    validated_data, 
                    route, 
                    user
                )

            return Response(
                {
                    'message': 'Hiace schedule created successfully.',
                    'data': {
                        'id': schedule.id,
                        'route': schedule.route.id,
                        'vehicle': vehicle.id,
                        'vehicle_name': vehicle.hiace_name,
                        'departure_datetime': schedule.departure_datetime,
                        'arrival_datetime': schedule.arrival_datetime,
                        'status': schedule.status,
                    }
                },
                status=status.HTTP_201_CREATED
            )

        except HiaceRoute.DoesNotExist:
            return Response(
                {'error': 'Route not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Hiace.DoesNotExist:
            return Response(
                {'error': 'Vehicle not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create_repeat_schedules(self, original_schedule, validated_data, route, user):
        """Create recurring schedules for Hiace"""
        repeat_type = validated_data.get('repeat_type')
        repeat_days = validated_data.get('repeat_days', [])
        repeat_end_date = validated_data.get('repeat_end_date')
        
        if not repeat_end_date:
            repeat_end_date = original_schedule.departure_datetime + timedelta(days=30)
        
        current_date = original_schedule.departure_datetime + timedelta(days=1)
        
        schedules_created = 0
        
        while current_date <= repeat_end_date:
            should_create = False
            
            if repeat_type == 'daily':
                should_create = True
            elif repeat_type == 'weekly':
                day_name = current_date.strftime('%a')
                if day_name in repeat_days:
                    should_create = True
            elif repeat_type == 'monthly':
                if current_date.day == original_schedule.departure_datetime.day:
                    should_create = True
            
            if should_create:
                duration = original_schedule.arrival_datetime - original_schedule.departure_datetime
                arrival_datetime = current_date + duration
                
                HiaceSchedule.objects.create(
                    route=route,
                    departure_datetime=current_date,
                    arrival_datetime=arrival_datetime,
                    status='ACTIVE'
                )
                schedules_created += 1
            
            current_date += timedelta(days=1)
        
        return schedules_created
