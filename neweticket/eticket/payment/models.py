from django.db import models
from django.conf import settings
from booking.models import Booking


class Payment(models.Model):

    PAYMENT_METHODS = (
        ("ESEWA", "eSewa"),
        ("KHALTI", "Khalti"),
        ("STRIPE", "Stripe"),
        ("CASH", "Cash"),
    )

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    )

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS
    )

    gateway = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    transaction_id = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    currency = models.CharField(
        max_length=10,
        default="NPR"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    payment_date = models.DateTimeField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        db_table = "payment"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.booking.booking_number} - {self.payment_method}"
    


class PaymentLog(models.Model):

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="logs"
    )

    request_data = models.JSONField()

    response_data = models.JSONField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "payment_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Log {self.payment.id}"


class Refund(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    )

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="refunds"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    refund_date = models.DateTimeField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "refund"

    def __str__(self):
        return f"{self.payment.transaction_id}"