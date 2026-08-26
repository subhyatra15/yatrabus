# hiace/models.py
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class Hiace(models.Model):
    HIACE_TYPES = (
        ("AC", "AC"),
        ("NON_AC", "Non AC"),
    )

    STATUS = (
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
    )

    operator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="hiace_vehicles",
        limit_choices_to={"role": "D"},
    )

    hiace_name = models.CharField(max_length=100)
    hiace_number = models.CharField(max_length=50, unique=True)
    hiace_type = models.CharField(max_length=20, choices=HIACE_TYPES)

    total_seats = models.PositiveIntegerField()
    seat_layout = models.JSONField(default=dict)

    wifi = models.BooleanField(default=False)
    charging = models.BooleanField(default=False)
    ac = models.BooleanField(default=False)

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="ACTIVE"
    )

    hiaceimage = models.ImageField(upload_to='hiaceimage',null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hiace"
        ordering = ["hiace_name"]

    def __str__(self):
        return f"{self.hiace_name} ({self.hiace_number})"


class HiaceRoute(models.Model):
    STATUS = (
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
    )

    operator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="hiace_routes",
        limit_choices_to={"role": "D"}
    )

    hiace = models.ForeignKey(
        Hiace,
        on_delete=models.CASCADE,
        related_name="hiace_routes"
    )

    source_city = models.ForeignKey(
        "city.City",
        on_delete=models.CASCADE,
        related_name="hiace_source_routes"
    )

    destination_city = models.ForeignKey(
        "city.City",
        on_delete=models.CASCADE,
        related_name="hiace_destination_routes"
    )

    distance = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Distance in KM"
    )

    duration = models.DurationField()

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="ACTIVE"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hiace_route"
        ordering = ["source_city", "destination_city"]

    def __str__(self):
        return f"{self.source_city} → {self.destination_city} ({self.hiace.hiace_name})"


class HiaceRouteStop(models.Model):
    route = models.ForeignKey(
        HiaceRoute,
        on_delete=models.CASCADE,
        related_name="stops"
    )

    city = models.ForeignKey(
        "city.City",
        on_delete=models.CASCADE
    )

    stop_order = models.PositiveIntegerField()
    arrival_offset = models.DurationField(help_text="Time from source")
    departure_offset = models.DurationField(help_text="Time from source")
    is_boarding = models.BooleanField(default=True)
    is_dropping = models.BooleanField(default=True)

    class Meta:
        db_table = "hiace_route_stop"
        ordering = ["stop_order"]
        unique_together = ("route", "stop_order")

    def __str__(self):
        return f"{self.city} - {self.stop_order}"


class HiaceRouteFare(models.Model):
    route = models.ForeignKey(HiaceRoute, on_delete=models.CASCADE, related_name="fares")
    from_stop = models.ForeignKey(
        HiaceRouteStop,
        related_name="hiace_fare_from",
        on_delete=models.CASCADE
    )
    to_stop = models.ForeignKey(
        HiaceRouteStop,
        related_name="hiace_fare_to",
        on_delete=models.CASCADE
    )
    fare = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "hiace_route_fare"

    def __str__(self):
        return f"{self.from_stop.city} → {self.to_stop.city}: {self.fare}"


class HiaceSchedule(models.Model):
    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("CANCELLED", "Cancelled"),
    )

    route = models.ForeignKey(
        HiaceRoute,
        on_delete=models.CASCADE,
        related_name="hiace_schedules"
    )

    departure_datetime = models.DateTimeField()
    arrival_datetime = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hiace_schedule"
        ordering = ["departure_datetime"]

    def __str__(self):
        return f"{self.route} ({self.departure_datetime})"


class HiaceSeat(models.Model):
    SEAT_TYPES = (
        ("NORMAL", "Normal"),
        ("VIP", "VIP"),
    )

    hiace = models.ForeignKey(
        Hiace,
        on_delete=models.CASCADE,
        related_name="hiace_seats"
    )

    seat_number = models.CharField(max_length=10)
    seat_type = models.CharField(max_length=20, choices=SEAT_TYPES, default="NORMAL")
    row = models.PositiveIntegerField(default=1)
    col = models.PositiveIntegerField(default=1)
    extra_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_window = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hiace_seat"
        ordering = ["seat_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["hiace", "seat_number"],
                name="unique_hiace_seat"
            )
        ]

    def __str__(self):
        return f"{self.hiace.hiace_name} - {self.seat_number}"


class HiaceBooking(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("CANCELLED", "Cancelled"),
        ("COMPLETED", "Completed"),
        ("REFUNDED", "Refunded"),
        ("EXPIRED", "Expired"),
    )

    booking_number = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hiace_bookings",
    )
    schedule = models.ForeignKey(
        HiaceSchedule,
        on_delete=models.CASCADE,
        related_name="hiace_bookings",
    )
    booking_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )
    platform_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    qr_code = models.ImageField(upload_to="hiace_booking_qr/", blank=True, null=True)
    qr_token = models.CharField(max_length=255, unique=True, blank=True, null=True)

    boarding_stop = models.ForeignKey(
        HiaceRouteStop,
        on_delete=models.PROTECT,
        related_name="hiace_boarding_bookings"
    )
    dropping_stop = models.ForeignKey(
        HiaceRouteStop,
        on_delete=models.PROTECT,
        related_name="hiace_dropping_bookings"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "hiace_booking"

    def save(self, *args, **kwargs):
        if self._state.adding and not self.expired_at:
            self.expired_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.booking_number


class HiaceBookingSeat(models.Model):
    booking = models.ForeignKey(
        HiaceBooking,
        on_delete=models.CASCADE,
        related_name="hiace_booking_seats",
    )
    seat = models.ForeignKey(
        HiaceSeat,
        on_delete=models.CASCADE,
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "hiace_booking_seat"
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "seat"],
                name="unique_hiace_booking_seat",
            )
        ]

    def __str__(self):
        return f"{self.booking.booking_number} - {self.seat.seat_number}"