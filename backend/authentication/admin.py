from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    # Add department and is_demo to the list display
    list_display = ("username", "email", "full_name", "department", "is_demo", "is_active", "is_staff")
    list_filter = ("department", "is_demo", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")

    # Add department and is_demo fields to the user edit form
    fieldsets = UserAdmin.fieldsets + (
        ("Department & Demo", {
            "fields": ("department", "is_demo"),
        }),
    )

    # Add department and is_demo to the user creation form
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Department & Demo", {
            "fields": ("department", "is_demo"),
        }),
    )

    def full_name(self, obj):
        return obj.get_full_name()
    full_name.short_description = "Full Name"