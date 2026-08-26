from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from schedule.models import Schedule
from seat.models import Seat
from routes.models import RouteStop
import uuid


class Booking(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("CANCELLED", "Cancelled"),
        ("COMPLETED", "Completed"),
        ("REFUNDED", "Refunded"),
        ("EXPIRED", "Expired"),
    )

    booking_number = models.CharField(
        max_length=30,
        unique=True,
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )

    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name="bookings",
    )



    booking_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    platform_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    qr_code = models.ImageField(
        upload_to="booking_qr/",
        blank=True,
        null=True,
    )

    qr_token = models.CharField(
        max_length=255,
        unique=True,
        default=uuid.uuid4,
        editable=False,
    )

    boarding_stop = models.ForeignKey(
        RouteStop,
        on_delete=models.PROTECT,
        related_name="boarding_bookings"
    )

    dropping_stop = models.ForeignKey(
        RouteStop,
        on_delete=models.PROTECT,
        related_name="dropping_bookings"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    expired_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "booking"

    def save(self, *args, **kwargs):
        # Set expiry only when creating a new booking
        if self._state.adding and not self.expired_at:
            self.expired_at = timezone.now() + timedelta(minutes=10)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.booking_number


class BookingSeat(models.Model):

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="booking_seats",
    )

    seat = models.ForeignKey(
        Seat,
        on_delete=models.CASCADE,
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    class Meta:
        db_table = "booking_seat"

        constraints = [
            models.UniqueConstraint(
                fields=["booking", "seat"],
                name="unique_booking_seat",
            )
        ]

    def __str__(self):
        return f"{self.booking.booking_number} - {self.seat.seat_number}"
    

