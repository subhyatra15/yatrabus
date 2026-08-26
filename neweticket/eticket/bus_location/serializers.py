from rest_framework import serializers
from .models import BusLocation


class BusLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusLocation
        fields = [
            "id",
            "bus",
            "latitude",
            "longitude",
            "speed",
            "heading",
            "accuracy",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]