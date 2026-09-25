from django.db import models
from django.conf import settings

# Device
class Device(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="devices"
    )

    token = models.CharField(
        max_length=500,
        unique=True
    )

    device = models.CharField(
        max_length=20,
        choices=[
            ("ANDROID", "Android"),
            ("IOS", "iOS"),
            ("WEB", "Web"),
        ],
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.device}"


# Notification 