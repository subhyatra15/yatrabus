from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Bus(models.Model):

    BUS_TYPES = (
        ("AC", "AC"),
        ("NON_AC", "Non AC"),
        ("DELUXE", "Deluxe"),
        ("VIP", "VIP"),
        ("SLEEPER", "Sleeper"),
    )

    STATUS = (
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
    )

    operator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="buses",
        limit_choices_to={"role": "D"},
    )

    bus_name = models.CharField(max_length=100)
    bus_number = models.CharField(max_length=50, unique=True)
    bus_type = models.CharField(max_length=20, choices=BUS_TYPES)

    total_seats = models.PositiveIntegerField()

    seat_layout = models.JSONField(default=dict)

    wifi = models.BooleanField(default=False)
    charging = models.BooleanField(default=False)
    ac = models.BooleanField(default=False)

    busimage = models.ImageField(upload_to='busimage',null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="ACTIVE"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.bus_name} ({self.bus_number})"