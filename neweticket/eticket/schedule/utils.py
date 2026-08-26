from django.utils import timezone
from booking.models import Booking

def expire_bookings():
    Booking.objects.filter(
        booking_status="PENDING",
        expired_at__lte=timezone.now()
    ).update(
        booking_status="EXPIRED"
    )


from booking.models import BookingSeat


