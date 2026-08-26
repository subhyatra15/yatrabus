from django.contrib import admin
from .models import Payment, PaymentLog, Refund


class PaymentLogInline(admin.TabularInline):
    model = PaymentLog
    extra = 0
    readonly_fields = (
        "request_data",
        "response_data",
        "created_at",
    )


class RefundInline(admin.TabularInline):
    model = Refund
    extra = 0


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "booking",
        "customer",
        "payment_method",
        "transaction_id",
        "amount",
        "currency",
        "status",
        "payment_date",
    )

    list_filter = (
        "payment_method",
        "status",
        "currency",
    )

    search_fields = (
        "transaction_id",
        "booking__booking_number",
        "customer__username",
        "customer__first_name",
        "customer__last_name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [
        PaymentLogInline,
        RefundInline,
    ]


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "payment",
        "created_at",
    )

    readonly_fields = (
        "request_data",
        "response_data",
        "created_at",
    )


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "payment",
        "amount",
        "status",
        "refund_date",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "payment__transaction_id",
    )