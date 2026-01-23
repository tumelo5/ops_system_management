from django.contrib import admin
from .models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'title', 'department', 'employment_status', 'email']
    list_filter = ['employment_status', 'department']
    search_fields = ['full_name', 'email']
    raw_id_fields = []  # Keep this empty to use dropdowns instead of popups