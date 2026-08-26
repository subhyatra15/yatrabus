from rest_framework import viewsets, permissions,views, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.db.models import Count,Q,Prefetch

from .models import Bus
from .serializers import BusSerializer
from routes.models import Route,RouteStop,RouteFare


class BusViewSet(viewsets.ModelViewSet):
    serializer_class = BusSerializer
    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]

        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        # Public users (not logged in)
        if not user.is_authenticated:
            return Bus.objects.all()

        # Passenger
        if user.role == "P":
            return Bus.objects.all()

        # Operator
        if user.role == "D":
            return Bus.objects.filter(operator=user)

        # Admin
        if user.role == "A":
            return Bus.objects.all()

        return Bus.objects.none()

    def perform_create(self, serializer):
        if self.request.user.role != "D":
            raise PermissionDenied("Only operators can create buses.")

        serializer.save(operator=self.request.user)

    def perform_update(self, serializer):
        bus = self.get_object()

        if (
            self.request.user.role != "A"
            and bus.operator != self.request.user
        ):
            raise PermissionDenied("You do not have permission.")

        serializer.save()

    def perform_destroy(self, instance):
        if (
            self.request.user.role != "A"
            and instance.operator != self.request.user
        ):
            raise PermissionDenied("You do not have permission.")

        instance.delete()


# RecommendedBusesView
class RecommendedBusesView(views.APIView):
    def get(self, request):
        # Get source and destination from query parameters (optional)
        source_city_id = request.query_params.get('source_city')
        destination_city_id = request.query_params.get('destination_city')
        
        # Base queryset
        buses = Bus.objects.filter(status="ACTIVE")
        
        # If source and destination are provided, filter buses that have routes for these cities
        if source_city_id and destination_city_id:
            buses = buses.filter(
                routes__source_city_id=source_city_id,
                routes__destination_city_id=destination_city_id,
                routes__status="ACTIVE"
            )
        
        # Get recommended buses based on booking count
        recommended_buses = (
            buses
            .select_related('operator')
            .prefetch_related(
                Prefetch(
                    'routes',
                    queryset=Route.objects.filter(status="ACTIVE")
                    .select_related('source_city', 'destination_city')
                    .prefetch_related(
                        Prefetch('stops', queryset=RouteStop.objects.select_related('city')),
                        Prefetch('routefare_set', queryset=RouteFare.objects.select_related('from_stop', 'to_stop'))
                    )
                )
            )
            .annotate(
                total_bookings=Count(
                    "routes__schedules__bookings",
                    filter=Q(
                        routes__schedules__bookings__booking_status="PAID"
                    )
                )
            )
            .filter(total_bookings__gt=0)  
            .order_by("-total_bookings")[:10]
        )

        if not recommended_buses:
            return Response(
                {"message": "No recommended buses found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serialize the buses with context
        context = {
            'source_city_id': source_city_id,
            'destination_city_id': destination_city_id,
            'request': request
        }
        serializer = BusSerializer(recommended_buses, many=True, context=context)
        
        return Response({
            "message": "Successfully fetched recommended buses",
            "count": len(serializer.data),
            "results": serializer.data
        })