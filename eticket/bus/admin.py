from django.contrib import admin
from django.utils.html import format_html
from .models import Bus


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = (
        'bus_name',
        'bus_number',
        'bus_type',
        'operator_name',
        'operator_phone',
        'total_seats',
        'status',
        'bus_image_preview',
    )

    list_filter = (
        'status',
        'bus_type',
        'operator',
    )

    search_fields = (
        'bus_name',
        'bus_number',
        'operator__fullName',
        'operator__phone',
    )

    list_select_related = ('operator',)

    ordering = ('bus_name',)

    list_per_page = 25

    readonly_fields = ('created_at', 'updated_at', 'bus_image_preview')
    fieldsets = (
        ('Basic Info', {
            'fields': ('operator', 'bus_name', 'bus_number', 'bus_type')
        }),
        ('Seat & Layout', {
            'fields': ('total_seats', 'seat_layout')
        }),
        ('Amenities', {
            'fields': ('wifi', 'charging', 'ac')
        }),
        ('Media', {
            'fields': ('busimage', 'bus_image_preview')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


    @admin.display(description='Operator', ordering='operator__fullName')
    def operator_name(self, obj):
        return obj.operator.fullName or '-'

    @admin.display(description='Phone', ordering='operator__phone')
    def operator_phone(self, obj):
        return obj.operator.phone or '-'

    @admin.display(description='Image')
    def bus_image_preview(self, obj):
        if obj.busimage:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:4px;" />',
                obj.busimage.url
            )
        return '-'