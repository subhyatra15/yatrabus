from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status

from .models import Device
from .serializers import DeviceSerializer
from django.core.mail import send_mail
from django.conf import settings


class DeviceListCreateView(generics.ListCreateAPIView):
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Device.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        token = request.data.get("token")
        device_type = request.data.get("device")

        if not token:
            return Response(
                {"detail": "Token is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        device = Device(
                user=request.user,
                token=token,
                device=device_type
            )

        device.save()

        serializer = self.get_serializer(device)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class DeviceDeleteView(generics.DestroyAPIView):
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Device.objects.filter(user=self.request.user)




def send_Email():
    send_mail(
        subject='hello',
        message='hello',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=['bhattarain538@gmail.com'],
        fail_silently=False,
    )
    print("Send successfully")


send_Email()