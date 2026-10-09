# eticket/appconfig/models.py
from django.db import models


class AppVersionConfig(models.Model):
    PLATFORM_CHOICES = (
        ("android", "Android"),
        ("ios", "iOS"),
    )

    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, unique=True)
    minimum_version = models.CharField(max_length=20)   # e.g. "1.2.0"
    latest_version = models.CharField(max_length=20)    # e.g. "1.4.0"
    mandatory = models.BooleanField(default=True)       # force update?
    store_url = models.URLField()                       # Play Store / App Store URL
    update_message = models.TextField(
        default="A new version of the app is available. Please update to continue."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "App Version Config"
        verbose_name_plural = "App Version Config"

    def __str__(self):
        return f"{self.platform} — min {self.minimum_version} / latest {self.latest_version}"