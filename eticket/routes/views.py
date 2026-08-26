from rest_framework import viewsets, permissions,views ,status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from .models import Route, RouteStop, RouteFare
from .serializers import RouteSerializer, RouteStopSerializer
from django.db.models import Count, Q, Prefetch
from django.db import transaction
import traceback
from datetime import timedelta



def parse_duration(value):
    hours, minutes, seconds = map(int, value.split(":"))
    return timedelta(
        hours=hours,
        minutes=minutes,
        seconds=seconds,
    )


class RouteViewSet(viewsets.ModelViewSet):
    serializer_class = RouteSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]

        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        bus = self.request.query_params.get("bus")

        queryset = Route.objects.select_related(
            "operator",
            "bus",
            "source_city",
            "destination_city",
        )

        if user.role == 'D':
            queryset = queryset.filter(operator = user)

        if bus:
            queryset = queryset.filter(bus=bus)

        # Public users
        if not user.is_authenticated:
            return queryset.filter(status="ACTIVE")

        # Admin
        if user.role == "A":
            return queryset

        # Operator
        if user.role == "D":
            return queryset.filter(operator=user)

        # Passenger
        return queryset.filter(status="ACTIVE")

    def perform_create(self, serializer):
        if self.request.user.role != "D":
            raise PermissionDenied(
                "Only operators can create routes."
            )

        bus = serializer.validated_data["bus"]

        if bus.operator != self.request.user:
            raise PermissionDenied(
                "You can only create routes for your own buses."
            )

        serializer.save(operator=self.request.user)

    def perform_update(self, serializer):
        route = self.get_object()

        if (
            self.request.user.role != "A"
            and route.operator != self.request.user
        ):
            raise PermissionDenied(
                "You do not have permission."
            )

        serializer.save()

    def perform_destroy(self, instance):
        if (
            self.request.user.role != "A"
            and instance.operator != self.request.user
        ):
            raise PermissionDenied(
                "You do not have permission."
            )

        instance.delete()


# Get RouteStop
class RouteStopView(views.APIView):
    def get(self,request):
        routeid = request.query_params.get("routeid")

        if not routeid:
            return Response(
                {
                    'message':"Route Id Is Required",
                    'status' :status.HTTP_400_BAD_REQUEST
                }
            )
        
        routestopqueryset = RouteStop.objects.filter(route_id=routeid).select_related("route","city").order_by("stop_order")
        serializer = RouteStopSerializer(routestopqueryset,many=True)
        return Response({
            'message':"Successfully Get Route Stop",
            'data':serializer.data,
            'status':status.HTTP_200_OK
        })



# Calulate Price For Bording Leave to Boarding Stop
class CalculatePriceView(views.APIView):
    def get(self,request):
        boardingstop = request.query_params.get("boardingstop")
        droppingstop = request.query_params.get("droppingstop")
        route = request.query_params.get("route")

        if not boardingstop:
            return Response({
                'message':'Boarding Stop Is required',
                'status' : status.HTTP_400_BAD_REQUEST
            })
        
        if not droppingstop:
            return Response({
                'message':'Dropping Stop Is required',
                'status' : status.HTTP_400_BAD_REQUEST
            })
        
        if not route:
            return Response({
                'message':'Route Stop Is required',
                'status' : status.HTTP_400_BAD_REQUEST
            })
        
        if boardingstop == droppingstop:
            return Response({
                'message':'Boarding Stop & Dropping Stop Must Not Same',
                'status' : status.HTTP_400_BAD_REQUEST
            })
        
        priceperseat = RouteFare.objects.filter(route_id=route,from_stop=boardingstop,to_stop=droppingstop).first()
        print("+++++++++++++++++++++++++priceperseat",priceperseat)
        if not priceperseat:
            return Response({
                'message':'Priceperseat Not Found',
                'status' : status.HTTP_404_NOT_FOUND
            })
        
        return Response(
            {
                'message' : 'Successfully fetch Price per Seat',
                'priceperseat':priceperseat.fare,
                'status':status.HTTP_200_OK
            }
        )


# Popular Route
class PopularRouteView(views.APIView):
    def get(self, request):
        popular_routes = (
            Route.objects.filter(status="ACTIVE")
            .select_related('source_city', 'destination_city', 'operator', 'bus')
            .prefetch_related(
                Prefetch(
                    'stops',
                    queryset=RouteStop.objects.select_related('city')
                )
            )
            .annotate(
                total_bookings=Count(
                    "schedules__bookings",
                    filter=Q(
                        schedules__bookings__booking_status="PAID"
                    )
                )
            )
            .filter(total_bookings__gt=0)  
            .order_by("-total_bookings")[:10]
        )

        if not popular_routes:
            return Response(
                {"message": "No popular routes found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serialize the routes
        serializer = RouteSerializer(popular_routes, many=True)
        
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })



# Create Bus Route, RouteStop & RouteFare
class CreateBusRouteView(views.APIView):
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
            route = Route.objects.create(
                bus_id=data.get("vehicle"),
                operator = user,
                source_city_id=data.get("source_city"),
                destination_city_id=data.get("destination_city"),
                distance=data.get("distance"),
                duration=parse_duration(data.get("duration")),
            )

            # Create Stops
            routes_ids = []
            for stop in data.get("stops", []):
                obj = RouteStop.objects.create(
                    route=route,
                    city_id=stop.get("city"),
                    stop_order=stop.get("stop_order"),
                    arrival_offset=parse_duration(stop.get("arrival_offset")),
                    departure_offset=parse_duration(stop.get("departure_offset")),
                    is_boarding=stop.get("is_boarding", True),
                    is_dropping=stop.get("is_dropping", True),
                )
                routes_ids.append(obj.id)

            # Create Fares
            for index, fare in enumerate(data.get("fares", [])):
                if index + 1 >= len(routes_ids):
                    break
                RouteFare.objects.create(
                    route=route,
                    from_stop_id=fare.get("from_stop"),
                    to_stop_id=fare.get("to_stop"),
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
