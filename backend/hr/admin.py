from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    list_display  = ("username", "get_full_name", "department", "title", "employee_id", "is_active")
    list_filter   = ("department", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "employee_id")

    # Adds department, title, employee_id into the admin edit form
    fieldsets = UserAdmin.fieldsets + (
        ("Employee Info", {
            "fields": ("department", "title", "employee_id")
        }),
    )