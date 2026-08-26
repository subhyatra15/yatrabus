from rest_framework import serializers
from .models import Bus
from routes.serializers import RouteSerializer
from routes.models import RouteFare, RouteStop


class BusSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(
        source="operator.fullName",
        read_only=True
    )

    routes = RouteSerializer(
        many=True,
        read_only=True
    )
    
    total_bookings = serializers.IntegerField(read_only=True)
    
    # Add fare field
    fare = serializers.SerializerMethodField()
    
    # Optional: Add source and destination city names if needed
    source_city_name = serializers.SerializerMethodField()
    destination_city_name = serializers.SerializerMethodField()

    class Meta:
        model = Bus
        fields = [
            "id",
            "operator",
            "operator_name",
            "bus_name",
            "bus_number",
            "bus_type",
            "total_seats",
            "seat_layout",
            "wifi",
            "charging",
            "ac",
            "status",
            "routes",
            "fare",  # Add fare field
            "source_city_name",  # Optional
            "destination_city_name",  # Optional
            "total_bookings",
            'busimage',
            "created_at",
            "updated_at",
        ]

        read_only_fields = (
            "id",
            "operator",
            "created_at",
            "updated_at",
        )

    def get_fare(self, obj):
        try:
            source_city_id = self.context.get('source_city_id')
            destination_city_id = self.context.get('destination_city_id')
            
            # If specific cities are provided, get fare for that route
            if source_city_id and destination_city_id:
                route = obj.routes.filter(
                    status="ACTIVE",
                    source_city_id=source_city_id,
                    destination_city_id=destination_city_id
                ).first()
                
                if route:
                    source_stop = RouteStop.objects.filter(
                        route=route,
                        city_id=source_city_id,
                        is_boarding=True
                    ).first()
                    
                    dest_stop = RouteStop.objects.filter(
                        route=route,
                        city_id=destination_city_id,
                        is_dropping=True
                    ).first()
                    
                    if source_stop and dest_stop:
                        fare_obj = RouteFare.objects.filter(
                            route=route,
                            from_stop=source_stop,
                            to_stop=dest_stop
                        ).first()
                        
                        if fare_obj:
                            return fare_obj.fare
            
            # Otherwise, get minimum fare among all active routes
            fares = []
            for route in obj.routes.filter(status="ACTIVE"):
                source_stop = RouteStop.objects.filter(
                    route=route,
                    city=route.source_city,
                    is_boarding=True
                ).first()
                
                dest_stop = RouteStop.objects.filter(
                    route=route,
                    city=route.destination_city,
                    is_dropping=True
                ).first()
                
                if source_stop and dest_stop:
                    fare_obj = RouteFare.objects.filter(
                        route=route,
                        from_stop=source_stop,
                        to_stop=dest_stop
                    ).first()
                    
                    if fare_obj:
                        fares.append(float(fare_obj.fare))
            
            if fares:
                return min(fares)  # Return minimum fare
                
            return None
            
        except Exception:
            return None

    def get_source_city_name(self, obj):
        """Get source city name from context if provided"""
        source_city_id = self.context.get('source_city_id')
        if source_city_id:
            route = obj.routes.filter(
                status="ACTIVE",
                source_city_id=source_city_id
            ).first()
            if route:
                return route.source_city.name
        return None
    
    def get_destination_city_name(self, obj):
        """Get destination city name from context if provided"""
        destination_city_id = self.context.get('destination_city_id')
        if destination_city_id:
            route = obj.routes.filter(
                status="ACTIVE",
                destination_city_id=destination_city_id
            ).first()
            if route:
                return route.destination_city.name
        return None

    def validate_bus_number(self, value):
        if Bus.objects.filter(
            bus_number=value
        ).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise serializers.ValidationError(
                "Bus number already exists."
            )
        return value