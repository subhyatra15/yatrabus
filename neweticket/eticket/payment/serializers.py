from rest_framework import serializers

from .models import (
    Payment,
    PaymentLog,
    Refund
)


class PaymentLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = PaymentLog
        fields = (
            "id",
            "payment",
            "request_data",
            "response_data",
            "created_at",
        )

        read_only_fields = (
            "id",
            "created_at",
        )


class RefundSerializer(serializers.ModelSerializer):

    class Meta:
        model = Refund
        fields = (
            "id",
            "payment",
            "amount",
            "reason",
            "status",
            "refund_date",
            "created_at",
        )

        read_only_fields = (
            "id",
            "refund_date",
            "created_at",
        )


class PaymentSerializer(serializers.ModelSerializer):

    customer_name = serializers.CharField(
        source="customer.fullName",
        read_only=True
    )

    booking_number = serializers.CharField(
        source="booking.booking_number",
        read_only=True
    )

    logs = PaymentLogSerializer(
        many=True,
        read_only=True
    )

    refunds = RefundSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Payment

        fields = (
            "id",
            "booking",
            "booking_number",
            "customer",
            "customer_name",
            "payment_method",
            "gateway",
            "transaction_id",
            "amount",
            "currency",
            "status",
            "payment_date",
            "logs",
            "refunds",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "customer",
            "transaction_id",
            "status",
            "payment_date",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):

        booking = attrs["booking"]

        if booking.customer != self.context["request"].user:
            raise serializers.ValidationError(
                "You can only pay for your own booking."
            )

        if booking.booking_status == "PAID":
            raise serializers.ValidationError(
                "This booking has already been paid."
            )

        return attrs

    def validate_amount(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Amount must be greater than zero."
            )

        return value