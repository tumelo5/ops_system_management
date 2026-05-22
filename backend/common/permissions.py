from rest_framework.permissions import BasePermission


class IsWarehouseAgent(BasePermission):
    message = "Access restricted to Warehouse department only."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.department == "warehouse"
        )


class IsHRStaff(BasePermission):
    message = "Access restricted to HR department only."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.department == "hr"
        )