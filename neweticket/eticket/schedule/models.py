from django.db import models
from routes.models import Route


class Schedule(models.Model):

    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("CANCELLED", "Cancelled"),
    )

    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name="schedules"
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
        db_table = "schedule"
        ordering = ["departure_datetime"]

    def __str__(self):
        return f"{self.route} ({self.departure_datetime})"