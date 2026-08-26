from django.db import models


class City(models.Model):

    PROVINCE_CHOICES = (
        ("KOSHI", "Koshi"),
        ("MADESH", "Madhesh"),
        ("BAGMATI", "Bagmati"),
        ("GANDAKI", "Gandaki"),
        ("LUMBINI", "Lumbini"),
        ("KARNALI", "Karnali"),
        ("SUDURPASCHIM", "Sudurpaschim"),
    )

    name = models.CharField(max_length=100, unique=True)

    province = models.CharField(
        max_length=20,
        choices=PROVINCE_CHOICES
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "city"
        ordering = ["name"]

    def __str__(self):
        return self.name