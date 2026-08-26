from django.contrib import admin
from .models import Route, RouteStop, RouteFare


class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 0
    ordering = ("stop_order",)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "bus",
        "source_city",
        "destination_city",
        "status",
    )
    list_filter = ("status",)
    search_fields = (
        "bus__bus_name",
        "source_city__name",
        "destination_city__name",
    )
    inlines = [RouteStopInline]


@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "route",
        "city",
        "stop_order",
        "arrival_offset",
        "departure_offset",
        "is_boarding",
        "is_dropping",
    )
    list_filter = ("route",)
    ordering = ("route", "stop_order")


@admin.register(RouteFare)
class RouteFareAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "route",
        "from_stop",
        "to_stop",
        "fare",
    )
    list_filter = ("route",)