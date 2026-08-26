
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from .models import (
    Hiace, HiaceRoute, HiaceRouteStop, HiaceRouteFare,
    HiaceSchedule, HiaceSeat, HiaceBooking, HiaceBookingSeat
)


@admin.register(Hiace)
class HiaceAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'hiace_name',
        'hiace_number',
        'hiace_type',
        'operator',
        'total_seats',
        'status',
        'created_at',
    ]
    list_filter = [
        'hiace_type',
        'status',
        'wifi',
        'charging',
        'ac',
        'created_at',
    ]
    search_fields = [
        'hiace_name',
        'hiace_number',
        'operator__email',
        'operator__fullName',
    ]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'operator',
                'hiace_name',
                'hiace_number',
                'hiace_type',
            )
        }),
        ('Seating Information', {
            'fields': (
                'total_seats',
                'seat_layout',
            )
        }),
        ('Amenities', {
            'fields': (
                'wifi',
                'charging',
                'ac',
            )
        }),
        ('Status', {
            'fields': (
                'status',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
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


@admin.register(HiaceRoute)
class HiaceRouteAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'source_city',
        'destination_city',
        'hiace',
        'operator',
        'distance',
        'duration',
        'status',
        'created_at',
        'total_stops',
        'total_fares',
    ]
    list_filter = [
        'status',
        'operator',
        'source_city',
        'destination_city',
        'created_at',
    ]
    search_fields = [
        'source_city__name',
        'destination_city__name',
        'hiace__hiace_name',
        'hiace__hiace_number',
        'operator__email',
        'operator__fullName',
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['hiace', 'source_city', 'destination_city', 'operator']
    fieldsets = (
        ('Route Information', {
            'fields': (
                'operator',
                'hiace',
                'source_city',
                'destination_city',
            )
        }),
        ('Route Details', {
            'fields': (
                'distance',
                'duration',
            )
        }),
        ('Status', {
            'fields': (
                'status',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
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


@admin.register(HiaceRouteStop)
class HiaceRouteStopAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'route',
        'city',
        'stop_order',
        'arrival_offset',
        'departure_offset',
        'is_boarding',
        'is_dropping',
    ]
    list_filter = [
        'is_boarding',
        'is_dropping',
        'city',
        'route',
    ]
    search_fields = [
        'city__name',
        'route__source_city__name',
        'route__destination_city__name',
    ]
    ordering = ['route', 'stop_order']


@admin.register(HiaceRouteFare)
class HiaceRouteFareAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'route',
        'from_stop',
        'to_stop',
        'fare',
    ]
    list_filter = ['route']
    search_fields = [
        'route__source_city__name',
        'route__destination_city__name',
        'from_stop__city__name',
        'to_stop__city__name',
    ]
    raw_id_fields = ['route', 'from_stop', 'to_stop']


@admin.register(HiaceSchedule)
class HiaceScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'route',
        'departure_datetime',
        'arrival_datetime',
        'status',
        'available_seats',
        'created_at',
    ]
    list_filter = [
        'status',
        'route',
        'departure_datetime',
        'arrival_datetime',
    ]
    search_fields = [
        'route__source_city__name',
        'route__destination_city__name',
        'route__hiace__hiace_name',
        'route__hiace__hiace_number',
    ]
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['route']
    fieldsets = (
        ('Schedule Information', {
            'fields': (
                'route',
                'departure_datetime',
                'arrival_datetime',
            )
        }),
        ('Status', {
            'fields': (
                'status',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
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


@admin.register(HiaceSeat)
class HiaceSeatAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'hiace',
        'seat_number',
        'seat_type',
        'row',
        'col',
        'extra_price',
        'is_window',
        'created_at',
    ]
    list_filter = [
        'seat_type',
        'is_window',
        'hiace',
    ]
    search_fields = [
        'seat_number',
        'hiace__hiace_name',
        'hiace__hiace_number',
    ]
    readonly_fields = ['created_at']
    raw_id_fields = ['hiace']


class HiaceBookingSeatInline(admin.TabularInline):
    model = HiaceBookingSeat
    extra = 0
    fields = ['seat', 'price']
    raw_id_fields = ['seat']
    readonly_fields = ['price']


@admin.register(HiaceBooking)
class HiaceBookingAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'booking_number',
        'customer',
        'schedule',
        'booking_status',
        'total_amount',
        'seat_count',
        'created_at',
        'expired_at',
    ]
    list_filter = [
        'booking_status',
        'schedule',
        'created_at',
        'expired_at',
    ]
    search_fields = [
        'booking_number',
        'customer__email',
        'customer__fullName',
        'schedule__route__source_city__name',
        'schedule__route__destination_city__name',
    ]
    readonly_fields = [
        'booking_number',
        'created_at',
        'qr_code_preview',
        'qr_token_display',
    ]
    raw_id_fields = ['customer', 'schedule', 'boarding_stop', 'dropping_stop']
    inlines = [HiaceBookingSeatInline]
    fieldsets = (
        ('Booking Information', {
            'fields': (
                'booking_number',
                'customer',
                'schedule',
            )
        }),
        ('Stops', {
            'fields': (
                'boarding_stop',
                'dropping_stop',
            )
        }),
        ('Payment Information', {
            'fields': (
                'subtotal',
                'discount',
                'tax',
                'platform_amount',
                'total_amount',
            )
        }),
        ('Status', {
            'fields': (
                'booking_status',
                'qr_code',
                'qr_code_preview',
                'qr_token',
                'qr_token_display',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'expired_at',
            ),
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

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(
            seat_count=Count('hiace_booking_seats')
        )

    def seat_count(self, obj):
        return obj.seat_count
    seat_count.short_description = 'Seats'
    seat_count.admin_order_field = 'seat_count'

    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html(
                '<img src="{}" width="100" height="100" style="border-radius: 8px;" />',
                obj.qr_code.url
            )
        return format_html('<span style="color: #94a3b8;">No QR Code</span>')
    qr_code_preview.short_description = 'QR Code Preview'

    def qr_token_display(self, obj):
        if obj.qr_token:
            return format_html(
                '<code style="background: #f1f5f9; padding: 4px 8px; border-radius: 4px;">{}</code>',
                obj.qr_token
            )
        return format_html('<span style="color: #94a3b8;">No Token</span>')
    qr_token_display.short_description = 'QR Token'

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


@admin.register(HiaceBookingSeat)
class HiaceBookingSeatAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'booking',
        'seat',
        'price',
    ]
    list_filter = ['booking', 'seat']
    search_fields = [
        'booking__booking_number',
        'seat__seat_number',
        'seat__hiace__hiace_name',
    ]
    raw_id_fields = ['booking', 'seat']