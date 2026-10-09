from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):

    search_fields = ["email", "phone", "fullName",]

    list_display = ["id", "email", "phone", "fullName", "role", "is_active"]
    
    list_filter = ["is_active", "role"]

    def save_model(self, request, obj, form, change):
        if not change or "password" in form.changed_data:
            if not obj.password.startswith(("pbkdf2_", "argon2", "bcrypt")):
                obj.set_password(obj.password)

        super().save_model(request, obj, form, change)