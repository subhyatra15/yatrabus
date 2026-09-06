from rest_framework import serializers
from .models import Route, RouteStop, RouteFare



class RouteStopSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    # route = serializers.CharField(source="route", read_only=True
    
    class Meta:
        model = RouteStop
        fields ="__all__"

class RouteFareSerializer(serializers.ModelSerializer):
    from_stop_city = serializers.CharField(source="from_stop.city.name", read_only=True)
    to_stop_city = serializers.CharField(source="to_stop.city.name", read_only=True)

    class Meta:
        model = RouteFare
        fields = [
            "id",
            "from_stop",
            "from_stop_city",
            "to_stop",
            "to_stop_city",
            "fare",
        ]

class RouteSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(
        source="operator.fullName",
        read_only=True
    )

    bus_name = serializers.CharField(
        source="bus.bus_name",
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

    fare = serializers.SerializerMethodField()
    stops = RouteStopSerializer(many=True, read_only=True)
    fares = RouteFareSerializer(many=True, read_only=True)
    

    class Meta:
        model = Route
        fields = [
            "id",
            "operator",
            "operator_name",
            "bus",
            "bus_name",
            "source_city",
            "source_city_name",
            "destination_city",
            "destination_city_name",
            "fare",
            "fares",
            "stops",
            "distance",
            "duration",
            "status",
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
            # Get source and destination stops
            source_stop = RouteStop.objects.filter(
                route=obj,
                city=obj.source_city,
                is_boarding=True
            ).first()
            
            dest_stop = RouteStop.objects.filter(
                route=obj,
                city=obj.destination_city,
                is_dropping=True
            ).first()
            
            if source_stop and dest_stop:
                # Get fare between stops
                fare_obj = RouteFare.objects.filter(
                    route=obj,
                    from_stop=source_stop,
                    to_stop=dest_stop
                ).first()
                
                if fare_obj:
                    return fare_obj.fare
                    
            return None
            
        except Exception:
            return None

    def validate(self, attrs):
        if attrs["source_city"] == attrs["destination_city"]:
            raise serializers.ValidationError(
                "Source and destination city cannot be the same."
            )

        return attrs


