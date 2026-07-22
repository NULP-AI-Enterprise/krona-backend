from rest_framework.permissions import BasePermission

class RolePermission(BasePermission):
    allowed_roles = []

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role in self.allowed_roles 
        )

class IsSuperAdmin(RolePermission):
    allowed_roles = ["SUPER_ADMIN"]

class IsAdminOrHigher(RolePermission):
    allowed_roles = ["SUPER_ADMIN", "ADMIN"]

class IsCompilerOrHigher(RolePermission):
    allowed_roles = ["SUPER_ADMIN", "ADMIN", "COMPILER"]

class IsRegisteredUser(RolePermission):
    allowed_roles = ["SUPER_ADMIN", "ADMIN", "COMPILER", "USER"]