from django.contrib import admin
from .models import Seat


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('seat_number', 'bus', 'seat_type')
    list_filter = ('seat_type', 'bus')
    search_fields = ('seat_number',)     
    list_select_related = ('bus',)
    ordering = ('seat_number',)