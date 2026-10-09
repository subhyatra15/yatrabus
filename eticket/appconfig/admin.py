# eticket/appconfig/admin.py
from django.contrib import admin
from .models import AppVersionConfig


@admin.register(AppVersionConfig)
class AppVersionConfigAdmin(admin.ModelAdmin):
    list_display = (
        "platform",
        "minimum_version",
        "latest_version",
        "mandatory",
        "updated_at",
    )
    list_editable = (
        "minimum_version",
        "latest_version",
        "mandatory",
    )
    list_filter = ("platform", "mandatory")
    search_fields = ("platform", "minimum_version", "latest_version")
    readonly_fields = ("updated_at",)

    fieldsets = (
        (
            "Platform",
            {
                "fields": ("platform",),
                "description": "Android and iOS are configured separately. "
                               "Create one row per platform.",
            },
        ),
        (
            "Version Control",
            {
                "fields": (
                    "minimum_version",
                    "latest_version",
                    "mandatory",
                ),
                "description": (
                    "• <b>minimum_version</b>: users below this version will "
                    "be forced to update (if mandatory is checked).<br>"
                    "• <b>latest_version</b>: users below this version but "
                    "at/above the minimum will see a soft prompt.<br>"
                    "• <b>mandatory</b>: turn OFF to make updates optional "
                    "even if the user is below the minimum."
                ),
            },
        ),
        (
            "Store & Message",
            {
                "fields": ("store_url", "update_message"),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("updated_at",),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, request):
        return AppVersionConfig.objects.count() < 2

    def has_delete_permission(self, request, obj=None):
        return False