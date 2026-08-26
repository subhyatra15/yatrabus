from django.db import models
from bus.models import Bus


class BusLocation(models.Model):
    bus = models.ForeignKey(
        Bus,
        on_delete=models.CASCADE,
        related_name="locations",
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    speed = models.FloatField(
        null=True,
        blank=True,
    )

    heading = models.FloatField(
        null=True,
        blank=True,
    )

    accuracy = models.FloatField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.bus_id} - {self.latitude}, {self.longitude}"