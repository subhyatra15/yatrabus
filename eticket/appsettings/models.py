from django.db import models


class Settings(models.Model):
    email = models.EmailField(max_length=150, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)

    platform_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    promo_code = models.CharField(max_length=150, null=True, blank=True)
    code_expired_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"email: {self.email} platform_cost: {self.platform_cost}"