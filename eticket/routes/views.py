from rest_framework import viewsets, permissions,views ,status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.db.models.deletion import ProtectedError


from .models import Route, RouteStop, RouteFare
from .serializers import RouteSerializer, RouteStopSerializer
from django.db.models import Count, Q, Prefetch
from django.db import transaction
import traceback
from datetime import timedelta
from bus.models import Bus


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



# BusRouteViewSet
class BusRouteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RouteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Route.objects.filter(status='ACTIVE',operator=user)

    @action(detail=False, methods=['get'], url_path='routestop')
    def get_route_stops(self, request):
        route_id = request.query_params.get('routeid')
        
        if not route_id:
            return Response(
                {'error': 'routeid parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            route = Route.objects.get(id=route_id,operator=user)
            stops = RouteStop.objects.filter(route=route).order_by('stop_order')
            
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
        except Route.DoesNotExist:
            return Response(
                {'error': 'Route not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='priceperseat')
    def get_price_per_seat(self, request):
        route_id = request.query_params.get('route')
        boarding_stop_id = request.query_params.get('boardingstop')
        dropping_stop_id = request.query_params.get('droppingstop')
        
        if not all([route_id, boarding_stop_id, dropping_stop_id]):
            return Response(
                {'error': 'route, boardingstop, and droppingstop parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            route = Route.objects.get(id=route_id)
            boarding_stop = RouteStop.objects.get(id=boarding_stop_id, route=route)
            dropping_stop = RouteStop.objects.get(id=dropping_stop_id, route=route)
            
            if boarding_stop.stop_order >= dropping_stop.stop_order:
                return Response(
                    {'error': 'Boarding stop must be before dropping stop'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            fare_obj = RouteFare.objects.filter(
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
                
        except Route.DoesNotExist:
            return Response(
                {'error': 'Route not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except RouteStop.DoesNotExist:
            return Response(
                {'error': 'Stop not found'},
                status=status.HTTP_404_NOT_FOUND
            )

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
                operator=user,
                source_city_id=data.get("source_city"),
                destination_city_id=data.get("destination_city"),
                distance=data.get("distance"),
                duration=parse_duration(data.get("duration")),
            )


            route_stops = {}

            for stop in data.get("stops", []):
                obj = RouteStop.objects.create(
                    route=route,
                    city_id=stop.get("city"),
                    stop_order=stop.get("stop_order"),
                    arrival_offset=parse_duration(
                        stop.get("arrival_offset")
                    ),
                    departure_offset=parse_duration(
                        stop.get("departure_offset")
                    ),
                    is_boarding=stop.get("is_boarding", True),
                    is_dropping=stop.get("is_dropping", True),
                )

                # Key = stop_order
                route_stops[obj.stop_order] = obj

                print(
                    "STOP:",
                    "order =", obj.stop_order,
                    "id =", obj.id,
                    "city =", obj.city_id,
                )

            # -----------------------------
            # Create Route Fares
            # -----------------------------

            for fare in data.get("fares", []):

                from_order = fare.get("from_stop")
                to_order = fare.get("to_stop")

                from_stop = route_stops.get(from_order)
                to_stop = route_stops.get(to_order)

                if from_stop is None:
                    raise ValueError(
                        f"Invalid from_stop order: {from_order}"
                    )

                if to_stop is None:
                    raise ValueError(
                        f"Invalid to_stop order: {to_order}"
                    )

                RouteFare.objects.create(
                    route=route,
                    from_stop=from_stop,
                    to_stop=to_stop,
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
    @transaction.atomic
    def put(self, request, pk):
        user = request.user

        if user.role != "D":
            return Response(
                {"message": "User must be an operator."},
                status=status.HTTP_403_FORBIDDEN,
            )

        route = Route.objects.filter(id=pk).first()
        if not route:
            return Response(
                {"message": "Route not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = request.data

        try:
            # -------- 1) scalar updates --------
            if data.get("vehicle") is not None:
                bus = Bus.objects.filter(id=data.get("vehicle")).first()
                if not bus:
                    return Response(
                        {"message": "Bus not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                route.bus = bus

            if data.get("source_city") is not None:
                route.source_city_id = data.get("source_city")
            if data.get("destination_city") is not None:
                route.destination_city_id = data.get("destination_city")
            if data.get("distance") is not None:
                route.distance = data.get("distance")
            if data.get("duration") is not None:
                route.duration = parse_duration(data.get("duration"))

            route.save()

            # -------- 2) stops + fares --------
            if "stops" in data:
                incoming_stops = data.get("stops", [])
                incoming_orders = {s.get("stop_order") for s in incoming_stops}

                # Fetch existing stops for this route
                existing_by_order = {s.stop_order: s for s in route.stops.all()}

                # Map: the client's "stop_order" -> the actual RouteStop object
                # and also let client use DB ids if it wants to
                stops_by_order = {}
                stops_by_id = {}

                # 2a) delete stops no longer present
                for order, stop in existing_by_order.items():
                    if order not in incoming_orders:
                        try:
                            stop.delete()
                        except ProtectedError:
                            return Response(
                                {
                                    "message": (
                                        f"Cannot remove stop #{order} because "
                                        "bookings already reference it."
                                    )
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                # 2b) update_or_create stops, then build lookup maps
                for stop in incoming_stops:
                    obj, _ = RouteStop.objects.update_or_create(
                        route=route,
                        stop_order=stop.get("stop_order"),
                        defaults={
                            "city_id": stop.get("city"),
                            "arrival_offset": parse_duration(stop.get("arrival_offset")),
                            "departure_offset": parse_duration(stop.get("departure_offset")),
                            "is_boarding": stop.get("is_boarding", True),
                            "is_dropping": stop.get("is_dropping", True),
                        },
                    )
                    stops_by_order[obj.stop_order] = obj
                    stops_by_id[obj.id] = obj

                # 2c) update_or_create fares
                incoming_fare_pairs = set()
                for fare in data.get("fares", []):
                    from_ref = fare.get("from_stop")
                    to_ref = fare.get("to_stop")

                    # Accept either stop_order or DB id — resolve to a RouteStop
                    from_stop = (
                        stops_by_order.get(from_ref)
                        or stops_by_id.get(from_ref)
                        or RouteStop.objects.filter(route=route, id=from_ref).first()
                    )
                    to_stop = (
                        stops_by_order.get(to_ref)
                        or stops_by_id.get(to_ref)
                        or RouteStop.objects.filter(route=route, id=to_ref).first()
                    )

                    if from_stop is None:
                        raise ValueError(f"Invalid from_stop: {from_ref}")
                    if to_stop is None:
                        raise ValueError(f"Invalid to_stop: {to_ref}")

                    incoming_fare_pairs.add((from_stop.id, to_stop.id))

                    RouteFare.objects.update_or_create(
                        route=route,
                        from_stop=from_stop,
                        to_stop=to_stop,
                        defaults={"fare": fare.get("fare")},
                    )

                # 2d) delete stale fares
                if incoming_fare_pairs:
                    stale = RouteFare.objects.filter(route=route)
                    for from_id, to_id in incoming_fare_pairs:
                        stale = stale.exclude(
                            from_stop_id=from_id,
                            to_stop_id=to_id,
                        )
                    stale.delete()

            return Response(
                {
                    "message": "Route updated successfully.",
                    "route_id": route.id,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            traceback.print_exc()
            return Response(
                {"message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )