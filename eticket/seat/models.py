from django.db import models
from bus.models import Bus


class Seat(models.Model):

    SEAT_TYPES = (
        ("NORMAL", "Normal"),
        ("VIP", "VIP"),
        ("SLEEPER", "Sleeper"),
    )

    bus = models.ForeignKey(
        Bus,
        on_delete=models.CASCADE,
        related_name="seats"
    )

    seat_number = models.CharField(max_length=10)

    seat_type = models.CharField(
        max_length=20,
        choices=SEAT_TYPES,
        default="NORMAL"
    )

    row = models.PositiveIntegerField(default=1)
    col = models.PositiveIntegerField(default=1)

    extra_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    is_window = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "seat"
        ordering = ["seat_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["bus", "seat_number"],
                name="unique_bus_seat"
            )
        ]

    def __str__(self):
        return f"{self.bus.bus_name} - {self.seat_number}"