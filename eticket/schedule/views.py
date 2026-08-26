from django.utils.dateparse import parse_date

from rest_framework import viewsets, permissions,views,status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import Schedule
from .serializers import ScheduleSerializer, ScheduleGenerateSerializer,CreateScheduleSerializer
from .utils import expire_bookings
from rest_framework.response import Response
from routes.models import RouteStop, RouteFare
from hiace.models import HiaceSchedule
from routes.models import Route
from bus.models import Bus
from django.utils import timezone
from datetime import timedelta
from hiace.serializers import CreateHiaceScheduleSerializer
from hiace.models import Hiace, HiaceRoute, HiaceSchedule


class ScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduleSerializer
    now = timezone.now()
    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]

        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        expire_bookings()
        queryset = Schedule.objects.filter(arrival_datetime__gt=self.now).select_related(
            "route",
            "route__bus",
            "route__operator",
            "route__source_city",
            "route__destination_city",
        )

        user = self.request.user

        if not user.is_authenticated:
            queryset = queryset.filter(status="ACTIVE")

        elif user.role == "A":
            pass

        elif user.role == "D":
            queryset = queryset.filter(route__operator=user)

        else:
            queryset = queryset.filter(status="ACTIVE")

        source = self.request.query_params.get("source")
        destination = self.request.query_params.get("destination")
        date = self.request.query_params.get("date")

        if source:
            queryset = queryset.filter(
                route__source_city__name__icontains=source
            )

        if destination:
            queryset = queryset.filter(
                route__destination_city__name__icontains=destination
            )

        if date:
            travel_date = parse_date(date)

            if travel_date:
                queryset = queryset.filter(
                    departure_datetime__date=travel_date
                )

        return queryset.order_by("departure_datetime")
    

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        source = request.query_params.get("source")
        destination = request.query_params.get("destination")
        bus = request.query_params.get("bus")
        if bus:
            queryset = queryset.filter(route__bus = bus)

        fare_map = {}
        boarding_stop_map = {}
        dropping_stop_map = {}

        if source and destination:
            for schedule in queryset:
                try:
                    boarding_stop = RouteStop.objects.get(
                        route=schedule.route,
                        city__name__iexact=source
                    )

                    dropping_stop = RouteStop.objects.get(
                        route=schedule.route,
                        city__name__iexact=destination
                    )
                    
                    if boarding_stop.stop_order >= dropping_stop.stop_order:
                        fare_map[schedule.id] = None
                        continue

                    fare = RouteFare.objects.get(
                        route=schedule.route,
                        from_stop=boarding_stop,
                        to_stop=dropping_stop
                    )

                    fare_map[schedule.id] = fare.fare
                    boarding_stop_map[schedule.id] = boarding_stop
                    dropping_stop_map[schedule.id] = dropping_stop

                except (RouteStop.DoesNotExist, RouteFare.DoesNotExist):
                    fare_map[schedule.id] = None

        serializer = self.get_serializer(
            queryset,
            many=True,
            context={
                "fare_map": fare_map,
                "boarding_stop_map": boarding_stop_map,
                "dropping_stop_map": dropping_stop_map,
            }
        )

        return Response(serializer.data)


    def perform_create(self, serializer):
        user = self.request.user

        if user.role != "D":
            raise PermissionDenied(
                "Only operators can create schedules."
            )

        route = serializer.validated_data["route"]

        if route.operator != user:
            raise PermissionDenied(
                "You can only create schedules for your own routes."
            )

        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        schedule = self.get_object()

        if (
            user.role != "A"
            and schedule.route.operator != user
        ):
            raise PermissionDenied(
                "You do not have permission to update this schedule."
            )

        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user

        if (
            user.role != "A"
            and instance.route.operator != user
        ):
            raise PermissionDenied(
                "You do not have permission to delete this schedule."
            )

        instance.delete()




# Get Schedule Details With RouteStop
class ScheduleDetailsWithRouteStop(views.APIView):
    def get(self, request, pk):
        routeid = request.query_params.get("routeid")
        boardingcity = request.query_params.get("boardingcity")
        droppingcity = request.query_params.get("droppingcity")

        if not routeid:
            return Response(
                {
                    "message": "RouteId Is Required",
                    "status": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not boardingcity:
            return Response(
                {
                    "message": "BoardingCity Is Required",
                    "status": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not droppingcity:
            return Response(
                {
                    "message": "DroppingCity Is Required",
                    "status": status.HTTP_400_BAD_REQUEST,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        schedule = Schedule.objects.select_related(
            "route",
            "route__bus",
            "route__operator",
            "route__source_city",
            "route__destination_city",
        ).filter(
            id=pk,
            route_id=routeid
        ).first()

        if not schedule:
            return Response(
                {
                    "message": "Schedule Not Found",
                    "status": status.HTTP_404_NOT_FOUND,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        fare_map = {}
        boarding_stop_map = {}
        dropping_stop_map = {}

        try:
            boarding_stop = RouteStop.objects.get(
                route=schedule.route,
                city__name__iexact=boardingcity,
            )

            dropping_stop = RouteStop.objects.get(
                route=schedule.route,
                city__name__iexact=droppingcity,
            )

            if boarding_stop.stop_order >= dropping_stop.stop_order:
                return Response(
                    {
                        "message": "Invalid Boarding and Dropping Stop",
                        "status": status.HTTP_400_BAD_REQUEST,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            fare = RouteFare.objects.filter(
                route=schedule.route,
                from_stop=boarding_stop,
                to_stop=dropping_stop,
            ).first()

            fare_map[schedule.id] = fare.fare if fare else None
            boarding_stop_map[schedule.id] = boarding_stop
            dropping_stop_map[schedule.id] = dropping_stop

        except RouteStop.DoesNotExist:
            fare_map[schedule.id] = None

        serializer = ScheduleSerializer(
            schedule,
            context={
                "fare_map": fare_map,
                "boarding_stop_map": boarding_stop_map,
                "dropping_stop_map": dropping_stop_map,
            },
        )

        return Response(
            {
                "message": "Successfully Get Schedule",
                "status": status.HTTP_200_OK,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )



# create Schedule

class CreateBusScheduleView(views.APIView):
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
        serializer = CreateScheduleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = serializer.validated_data
        
        try:
            # Get route and vehicle
            route = Route.objects.get(id=validated_data['route'])
            vehicle = Bus.objects.get(id=validated_data['vehicle'])
            
            # Check if route belongs to user
            # if route.operator != user:
            #     return Response(
            #         {'error': 'You can only create schedules for your own routes.'},
            #         status=status.HTTP_403_FORBIDDEN
            #     )
            
            # Check if vehicle belongs to user
            if vehicle.operator != user:
                return Response(
                    {'error': 'You can only create schedules for your own vehicles.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Create schedule
            schedule = Schedule.objects.create(
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
                    'message': 'Schedule created successfully.',
                    'data': {
                        'id': schedule.id,
                        'route': schedule.route.id,
                        'vehicle': vehicle.id,
                        'vehicle_name': vehicle.bus_name,
                        'departure_datetime': schedule.departure_datetime,
                        'arrival_datetime': schedule.arrival_datetime,
                        'status': schedule.status,
                    }
                },
                status=status.HTTP_201_CREATED
            )

        except Route.DoesNotExist:
            return Response(
                {'error': 'Route not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Bus.DoesNotExist:
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
        """Create recurring schedules"""
        repeat_type = validated_data.get('repeat_type')
        repeat_days = validated_data.get('repeat_days', [])
        repeat_end_date = validated_data.get('repeat_end_date')
        
        if not repeat_end_date:
            repeat_end_date = original_schedule.departure_datetime + timedelta(days=30)
        
        current_date = original_schedule.departure_datetime + timedelta(days=1)
        day_mapping = {
            'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 
            'Fri': 4, 'Sat': 5, 'Sun': 6
        }
        
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
                
                Schedule.objects.create(
                    route=route,
                    departure_datetime=current_date,
                    arrival_datetime=arrival_datetime,
                    status='ACTIVE'
                )
                schedules_created += 1
            
            current_date += timedelta(days=1)
        
        return schedules_created


