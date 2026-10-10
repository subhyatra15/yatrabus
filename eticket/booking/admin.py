from django.contrib import admin
from django.db.models import Sum, DecimalField, Value
from django.db.models.functions import Coalesce
from django.utils.html import format_html
from import_export import resources, fields
from import_export.admin import ExportMixin
from import_export.formats.base_formats import CSV, XLSX

from .models import Booking, BookingSeat


class BusBookingResource(resources.ModelResource):
    booking_date = fields.Field(attribute='created_at', column_name='Date')
    username = fields.Field(attribute='customer__fullName', column_name='Driver Name')
    phone = fields.Field(attribute='customer__phone', column_name='Phone')
    route = fields.Field(attribute='schedule__route', column_name='Route')
    departure = fields.Field(attribute='schedule__departure_datetime', column_name='Departure')
    seats = fields.Field(column_name='Seats Booked')
    booking_status = fields.Field(attribute='booking_status', column_name='Status')
    subtotal = fields.Field(attribute='subtotal', column_name='Subtotal')
    discount = fields.Field(attribute='discount', column_name='Discount')
    tax = fields.Field(attribute='tax', column_name='Tax')
    platform_amount = fields.Field(attribute='platform_amount', column_name='Platform Fee')
    total_amount = fields.Field(attribute='total_amount', column_name='Total Amount')
    driver_income = fields.Field(column_name='Driver Income')

    class Meta:
        model = Booking
        fields = (
            'booking_number', 'booking_date', 'username', 'phone',
            'route', 'departure', 'seats', 'booking_status',
            'subtotal', 'discount', 'tax', 'platform_amount',
            'total_amount', 'driver_income',
        )
        export_order = fields

    def dehydrate_seats(self, obj):
        return obj.booking_seats.count()

    def dehydrate_driver_income(self, obj):
        try:
            return float(obj.total_amount) - float(obj.platform_amount)
        except Exception:
            return 0.0


# ============================================================
# 2. ADMIN — the full-featured Booking admin page
# ============================================================
@admin.register(Booking)
class BusBookingAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = BusBookingResource
    formats = [CSV, XLSX]

    list_display = (
        'booking_number',
        'created_at',
        'driver_name',
        'driver_phone',
        'route_info',
        'seats_count',
        'booking_status',
        'total_amount',
        'platform_amount',
        'driver_income_display',
    )

    list_filter = (
        'booking_status',
        'created_at',
        'schedule__route__source_city',
        'schedule__route__destination_city',
    )
    date_hierarchy = 'created_at'

    search_fields = (
        'booking_number',
        'customer__fullName',
        'customer__phone',
        'schedule__route__source_city__name',
        'schedule__route__destination_city__name',
    )

    list_select_related = (
        'customer', 'schedule',
        'schedule__route',
        'schedule__route__source_city',
        'schedule__route__destination_city',
    )

    # -------- Custom columns --------
    @admin.display(description='Driver', ordering='customer__fullName')
    def driver_name(self, obj):
        return obj.customer.fullName or '-'

    @admin.display(description='Phone', ordering='customer__phone')
    def driver_phone(self, obj):
        return obj.customer.phone or '-'

    @admin.display(description='Route')
    def route_info(self, obj):
        r = obj.schedule.route
        return f"{r.source_city} → {r.destination_city}"

    @admin.display(description='Seats')
    def seats_count(self, obj):
        return obj.booking_seats.count()

    @admin.display(description='Driver Income', ordering='total_amount')
    def driver_income_display(self, obj):
        try:
            income = obj.total_amount - obj.platform_amount
            color = '#0a8f3c' if income >= 0 else '#c0392b'
            return format_html(
                '<strong style="color:{};">Rs. {}</strong>',
                color, income
            )
        except Exception:
            return '-'

    # -------- Summary box under the changelist --------
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)
        try:
            qs = response.context_data['cl'].queryset
            totals = qs.aggregate(
                total=Coalesce(Sum('total_amount'), Value(0), output_field=DecimalField()),
                platform=Coalesce(Sum('platform_amount'), Value(0), output_field=DecimalField()),
            )
            response.context_data['summary'] = {
                'total': totals['total'],
                'platform': totals['platform'],
                'driver_income': totals['total'] - totals['platform'],
                'count': qs.count(),
            }
        except (AttributeError, KeyError):
            pass
        return response



@admin.register(BookingSeat)
class BookingSeatAdmin(admin.ModelAdmin):
    list_display = ('booking', 'seat', 'price')
    list_filter = ('seat',)
    search_fields = ('booking__booking_number', 'seat__seat_number')
    list_select_related = ('booking', 'seat')
    autocomplete_fields = ('booking', 'seat')