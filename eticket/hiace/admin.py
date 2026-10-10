from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q, Sum, DecimalField, Value
from django.db.models.functions import Coalesce

from import_export import resources, fields
from import_export.admin import ExportMixin
from import_export.formats.base_formats import CSV, XLSX

from .models import (
    Hiace, HiaceRoute, HiaceRouteStop, HiaceRouteFare,
    HiaceSchedule, HiaceSeat, HiaceBooking, HiaceBookingSeat
)


# ============================================================
# 1. HiaceBookingResource — controls CSV/XLSX export columns
# ============================================================
class HiaceBookingResource(resources.ModelResource):
    booking_date = fields.Field(attribute='created_at', column_name='Date')
    username = fields.Field(attribute='customer__fullName', column_name='Driver Name')
    phone = fields.Field(attribute='customer__phone', column_name='Phone')
    hiace_name = fields.Field(attribute='schedule__route__hiace__hiace_name', column_name='Hiace')
    hiace_number = fields.Field(attribute='schedule__route__hiace__hiace_number', column_name='Hiace Number')
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
        model = HiaceBooking
        fields = (
            'booking_number', 'booking_date', 'username', 'phone',
            'hiace_name', 'hiace_number', 'route', 'departure',
            'seats', 'booking_status', 'subtotal', 'discount', 'tax',
            'platform_amount', 'total_amount', 'driver_income',
        )
        export_order = fields

    def dehydrate_seats(self, obj):
        return obj.hiace_booking_seats.count()

    def dehydrate_driver_income(self, obj):
        try:
            return float(obj.total_amount) - float(obj.platform_amount)
        except Exception:
            return 0.0


# ============================================================
# 2. HiaceAdmin (unchanged)
# ============================================================
@admin.register(Hiace)
class HiaceAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'hiace_name', 'hiace_number', 'hiace_type',
        'operator', 'total_seats', 'status', 'created_at',
    ]
    list_filter = [
        'hiace_type', 'status', 'wifi', 'charging', 'ac', 'created_at',
    ]
    search_fields = [
        'hiace_name', 'hiace_number', 'operator__email', 'operator__fullName',
    ]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('operator', 'hiace_name', 'hiace_number', 'hiace_type')
        }),
        ('Seating Information', {
            'fields': ('total_seats', 'seat_layout')
        }),
        ('Amenities', {
            'fields': ('wifi', 'charging', 'ac')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['activate_hiace', 'deactivate_hiace']

    def activate_hiace(self, request, queryset):
        queryset.update(status='ACTIVE')
        self.message_user(request, f"{queryset.count()} Hiace(s) activated successfully.")
    activate_hiace.short_description = "Activate selected Hiace"

    def deactivate_hiace(self, request, queryset):
        queryset.update(status='INACTIVE')
        self.message_user(request, f"{queryset.count()} Hiace(s) deactivated successfully.")
    deactivate_hiace.short_description = "Deactivate selected Hiace"


# ============================================================
# 3. HiaceRouteAdmin (unchanged)
# ============================================================
@admin.register(HiaceRoute)
class HiaceRouteAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'source_city', 'destination_city', 'hiace', 'operator',
        'distance', 'duration', 'status', 'created_at',
        'total_stops', 'total_fares',
    ]
    list_filter = [
        'status', 'operator', 'source_city', 'destination_city', 'created_at',
    ]
    search_fields = [
        'source_city__name', 'destination_city__name',
        'hiace__hiace_name', 'hiace__hiace_number',
        'operator__email', 'operator__fullName',
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['hiace', 'source_city', 'destination_city', 'operator']
    fieldsets = (
        ('Route Information', {
            'fields': ('operator', 'hiace', 'source_city', 'destination_city')
        }),
        ('Route Details', {
            'fields': ('distance', 'duration')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            total_stops=Count('stops'),
            total_fares=Count('fares')
        )

    def total_stops(self, obj):
        return obj.total_stops
    total_stops.short_description = 'Stops'
    total_stops.admin_order_field = 'total_stops'

    def total_fares(self, obj):
        return obj.total_fares
    total_fares.short_description = 'Fares'
    total_fares.admin_order_field = 'total_fares'


class HiaceRouteStopInline(admin.TabularInline):
    model = HiaceRouteStop
    extra = 1
    fields = ['city', 'stop_order', 'arrival_offset', 'departure_offset', 'is_boarding', 'is_dropping']
    ordering = ['stop_order']


class HiaceRouteFareInline(admin.TabularInline):
    model = HiaceRouteFare
    extra = 1
    fields = ['from_stop', 'to_stop', 'fare']
    raw_id_fields = ['from_stop', 'to_stop']


# ============================================================
# 4. HiaceRouteStopAdmin (unchanged)
# ============================================================
@admin.register(HiaceRouteStop)
class HiaceRouteStopAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'route', 'city', 'stop_order',
        'arrival_offset', 'departure_offset',
        'is_boarding', 'is_dropping',
    ]
    list_filter = ['is_boarding', 'is_dropping', 'city', 'route']
    search_fields = [
        'city__name', 'route__source_city__name', 'route__destination_city__name',
    ]
    ordering = ['route', 'stop_order']


# ============================================================
# 5. HiaceRouteFareAdmin (unchanged)
# ============================================================
@admin.register(HiaceRouteFare)
class HiaceRouteFareAdmin(admin.ModelAdmin):
    list_display = ['id', 'route', 'from_stop', 'to_stop', 'fare']
    list_filter = ['route']
    search_fields = [
        'route__source_city__name', 'route__destination_city__name',
        'from_stop__city__name', 'to_stop__city__name',
    ]
    raw_id_fields = ['route', 'from_stop', 'to_stop']


# ============================================================
# 6. HiaceScheduleAdmin (unchanged)
# ============================================================
@admin.register(HiaceSchedule)
class HiaceScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'route', 'departure_datetime', 'arrival_datetime',
        'status', 'available_seats', 'created_at',
    ]
    list_filter = [
        'status', 'route', 'departure_datetime', 'arrival_datetime',
    ]
    search_fields = [
        'route__source_city__name', 'route__destination_city__name',
        'route__hiace__hiace_name', 'route__hiace__hiace_number',
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['route']
    fieldsets = (
        ('Schedule Information', {
            'fields': ('route', 'departure_datetime', 'arrival_datetime')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    actions = ['cancel_schedule', 'activate_schedule']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            booked_seats=Count('hiace_bookings__hiace_booking_seats', filter=Q(
                hiace_bookings__booking_status__in=['PENDING', 'PAID']
            ))
        )

    def available_seats(self, obj):
        total_seats = obj.route.hiace.total_seats
        booked = getattr(obj, 'booked_seats', 0)
        available = total_seats - booked
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            'green' if available > 5 else 'orange' if available > 0 else 'red',
            available
        )
    available_seats.short_description = 'Available Seats'
    available_seats.admin_order_field = 'booked_seats'

    def cancel_schedule(self, request, queryset):
        queryset.update(status='CANCELLED')
        self.message_user(request, f"{queryset.count()} Schedule(s) cancelled successfully.")
    cancel_schedule.short_description = "Cancel selected schedules"

    def activate_schedule(self, request, queryset):
        queryset.update(status='ACTIVE')
        self.message_user(request, f"{queryset.count()} Schedule(s) activated successfully.")
    activate_schedule.short_description = "Activate selected schedules"


# ============================================================
# 7. HiaceSeatAdmin (unchanged)
# ============================================================
@admin.register(HiaceSeat)
class HiaceSeatAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'hiace', 'seat_number', 'seat_type',
        'row', 'col', 'extra_price', 'is_window', 'created_at',
    ]
    list_filter = ['seat_type', 'is_window', 'hiace']
    search_fields = [
        'seat_number', 'hiace__hiace_name', 'hiace__hiace_number',
    ]
    readonly_fields = ['created_at']
    raw_id_fields = ['hiace']


class HiaceBookingSeatInline(admin.TabularInline):
    model = HiaceBookingSeat
    extra = 0
    fields = ['seat', 'price']
    raw_id_fields = ['seat']
    readonly_fields = ['price']


# ============================================================
# 8. HiaceBookingAdmin — UPGRADED with export + income + summary
# ============================================================
@admin.register(HiaceBooking)
class HiaceBookingAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = HiaceBookingResource
    formats = [CSV, XLSX]

    list_display = [
        'id',
        'booking_number',
        'created_at',
        'driver_name',
        'driver_phone',
        'hiace_info',
        'route_info',
        'booking_status',
        'total_amount',
        'platform_amount',
        'driver_income_display',
        'seat_count',
    ]

    list_filter = [
        'booking_status',
        'created_at',
        'expired_at',
        'schedule__route__source_city',
        'schedule__route__destination_city',
        'schedule__route__hiace',
    ]
    date_hierarchy = 'created_at'

    search_fields = [
        'booking_number',
        'customer__fullName',
        'customer__phone',
        'customer__email',
        'schedule__route__source_city__name',
        'schedule__route__destination_city__name',
        'schedule__route__hiace__hiace_name',
        'schedule__route__hiace__hiace_number',
    ]

    list_select_related = (
        'customer',
        'schedule',
        'schedule__route',
        'schedule__route__hiace',
        'schedule__route__source_city',
        'schedule__route__destination_city',
    )

    readonly_fields = [
        'booking_number',
        'created_at',
        'qr_code_preview',
        'qr_token_display',
    ]

    raw_id_fields = [
        'customer',
        'schedule',
        'boarding_stop',
        'dropping_stop',
    ]

    inlines = [HiaceBookingSeatInline]

    fieldsets = (
        ('Booking Information', {
            'fields': ('booking_number', 'customer', 'schedule')
        }),
        ('Stops', {
            'fields': ('boarding_stop', 'dropping_stop')
        }),
        ('Payment Information', {
            'fields': ('subtotal', 'discount', 'tax', 'platform_amount', 'total_amount')
        }),
        ('Status', {
            'fields': ('booking_status', 'qr_code', 'qr_code_preview', 'qr_token_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expired_at'),
            'classes': ('collapse',)
        }),
    )

    actions = [
        'mark_as_paid',
        'mark_as_completed',
        'mark_as_cancelled',
        'mark_as_refunded',
        'mark_as_expired',
    ]

    # -------- Queryset with seat count --------
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            seat_count=Count('hiace_booking_seats')
        )

    # -------- Display columns --------
    @admin.display(description='Driver', ordering='customer__fullName')
    def driver_name(self, obj):
        return obj.customer.fullName or '-'

    @admin.display(description='Phone', ordering='customer__phone')
    def driver_phone(self, obj):
        return obj.customer.phone or '-'

    @admin.display(description='Hiace')
    def hiace_info(self, obj):
        h = obj.schedule.route.hiace
        return f"{h.hiace_name} ({h.hiace_number})"

    @admin.display(description='Route')
    def route_info(self, obj):
        r = obj.schedule.route
        return f"{r.source_city} → {r.destination_city}"

    @admin.display(description='Seats', ordering='seat_count')
    def seat_count(self, obj):
        return getattr(obj, 'seat_count', 0)

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

    # -------- QR helpers (unchanged) --------
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html(
                '<img src="{}" width="100" height="100" style="border-radius: 8px;" />',
                obj.qr_code.url
            )
        return format_html(
            '<span style="color: #94a3b8;">{}</span>',
            'No QR Code'
        )
    qr_code_preview.short_description = 'QR Code Preview'

    def qr_token_display(self, obj):
        if obj.qr_token:
            return format_html(
                '<code style="background: #f1f5f9; padding: 4px 8px; border-radius: 4px;">{}</code>',
                obj.qr_token
            )
        return format_html(
            '<span style="color: #94a3b8;">{}</span>',
            'No Token'
        )
    qr_token_display.short_description = 'QR Token'

    # -------- Bulk status actions --------
    def mark_as_paid(self, request, queryset):
        queryset.update(booking_status='PAID')
        self.message_user(request, f"{queryset.count()} Booking(s) marked as PAID.")
    mark_as_paid.short_description = "Mark selected as PAID"

    def mark_as_completed(self, request, queryset):
        queryset.update(booking_status='COMPLETED')
        self.message_user(request, f"{queryset.count()} Booking(s) marked as COMPLETED.")
    mark_as_completed.short_description = "Mark selected as COMPLETED"

    def mark_as_cancelled(self, request, queryset):
        queryset.update(booking_status='CANCELLED')
        self.message_user(request, f"{queryset.count()} Booking(s) marked as CANCELLED.")
    mark_as_cancelled.short_description = "Mark selected as CANCELLED"

    def mark_as_refunded(self, request, queryset):
        queryset.update(booking_status='REFUNDED')
        self.message_user(request, f"{queryset.count()} Booking(s) marked as REFUNDED.")
    mark_as_refunded.short_description = "Mark selected as REFUNDED"

    def mark_as_expired(self, request, queryset):
        queryset.update(booking_status='EXPIRED')
        self.message_user(request, f"{queryset.count()} Booking(s) marked as EXPIRED.")
    mark_as_expired.short_description = "Mark selected as EXPIRED"

    # -------- Summary box on changelist --------
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


# ============================================================
# 9. HiaceBookingSeatAdmin (unchanged)
# ============================================================
@admin.register(HiaceBookingSeat)
class HiaceBookingSeatAdmin(admin.ModelAdmin):
    list_display = ['id', 'booking', 'seat', 'price']
    list_filter = ['booking', 'seat']
    search_fields = [
        'booking__booking_number',
        'seat__seat_number',
        'seat__hiace__hiace_name',
    ]
    raw_id_fields = ['booking', 'seat']