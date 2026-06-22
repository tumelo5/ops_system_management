from rest_framework.permissions import BasePermission


class IsWarehouseAgent(BasePermission):
    message = "Access restricted to Warehouse department only."

    def has_permission(self, request, view):
        print("DEBUG user:", request.user)
        print("DEBUG authenticated:", request.user.is_authenticated)
        print("DEBUG department:", repr(request.user.department))
        return (
            request.user.is_authenticated and
            request.user.department == "warehouse"
        )


class IsRepairsAgent(BasePermission):
    message = "Access restricted to Repairs department only."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.department == "repairs"
        )


class IsStoresAgent(BasePermission):
    message = "Access restricted to Stores department only."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.department == "stores"
        )


class IsFinanceAgent(BasePermission):
    message = "Access restricted to Finance department only."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.department == "finance"
        )