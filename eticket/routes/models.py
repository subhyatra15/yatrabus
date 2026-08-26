from django.db import models
from django.contrib.auth import get_user_model

from bus.models import Bus
from city.models import City

User = get_user_model()

class Route(models.Model):

    STATUS = (
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
    )

    operator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="routes",
        limit_choices_to={"role": "D"}
    )

    bus = models.ForeignKey(
        Bus,
        on_delete=models.CASCADE,
        related_name="routes"
    )

    source_city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name="source_routes"
    )

    destination_city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name="destination_routes"
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
        db_table = "route"

    def __str__(self):
        return f"{self.source_city} → {self.destination_city}"
    
# Route Stop
class RouteStop(models.Model):
    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name="stops"
    )

    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE
    )

    stop_order = models.PositiveIntegerField()

    arrival_offset = models.DurationField(
        help_text="Time from source"
    )

    departure_offset = models.DurationField(
        help_text="Time from source"
    )

    is_boarding = models.BooleanField(default=True)
    is_dropping = models.BooleanField(default=True)

    class Meta:
        db_table = "route_stop"
        ordering = ["stop_order"]
        unique_together = ("route", "stop_order")
    
    def __str__(self):
        return f"{self.city} - {self.stop_order}"
    
# Route Fare
class RouteFare(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE)

    from_stop = models.ForeignKey(
        RouteStop,
        related_name="fare_from",
        on_delete=models.CASCADE
    )

    to_stop = models.ForeignKey(
        RouteStop,
        related_name="fare_to",
        on_delete=models.CASCADE
    )

    fare = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"From :{self.from_stop.city} - To :{self.to_stop.city} Fare :{self.fare}"