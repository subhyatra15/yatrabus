from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from bus.models import Bus
from .models import BusLocation
from .serializers import BusLocationSerializer


class BusLocationUpdateAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, bus_id):

        try:
            bus = Bus.objects.get(id=bus_id)
        except Bus.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Bus not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")

        if latitude is None or longitude is None:
            return Response(
                {
                    "success": False,
                    "message": "latitude and longitude are required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (ValueError, TypeError):
            return Response(
                {
                    "success": False,
                    "message": "Invalid latitude or longitude",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not -90 <= latitude <= 90:
            return Response(
                {
                    "success": False,
                    "message": "Invalid latitude",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not -180 <= longitude <= 180:
            return Response(
                {
                    "success": False,
                    "message": "Invalid longitude",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        location = BusLocation.objects.create(
            bus=bus,
            latitude=latitude,
            longitude=longitude,
            speed=request.data.get("speed"),
            heading=request.data.get("heading"),
            accuracy=request.data.get("accuracy"),
        )

        data = BusLocationSerializer(location).data

        # Broadcast to WebSocket clients

        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            f"bus_location_{bus.id}",
            {
                "type": "bus_location_update",
                "data": data,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Bus location updated",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


class BusCurrentLocationAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, bus_id):

        location = (
            BusLocation.objects
            .filter(bus_id=bus_id)
            .order_by("-created_at")
            .first()
        )

        if not location:
            return Response(
                {
                    "success": False,
                    "message": "No location available",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "success": True,
                "data": BusLocationSerializer(location).data,
            }
        )


class BusLocationHistoryAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, bus_id):

        locations = (
            BusLocation.objects
            .filter(bus_id=bus_id)
            .order_by("-created_at")[:100]
        )

        serializer = BusLocationSerializer(
            locations,
            many=True,
        )

        return Response(
            {
                "success": True,
                "count": len(serializer.data),
                "data": serializer.data,
            }
        )