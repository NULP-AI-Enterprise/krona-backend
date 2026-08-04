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


class IsSubcorpusOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role in ('SUPER_ADMIN', 'ADMIN'):
            return True
        return obj.creator == request.user


class HasSubcorpusAccess(BasePermission):
    def has_object_permission(self, request, view, obj):
        from corpus.models import SubcorpusAccessGrant
        if request.user.role in ('SUPER_ADMIN', 'ADMIN'):
            return True
        if obj.creator == request.user:
            return True
        return SubcorpusAccessGrant.objects.filter(
            subcorpus=obj, user=request.user
        ).exists()


class HasSubcorpusEditAccess(BasePermission):
    def has_object_permission(self, request, view, obj):
        from corpus.models import SubcorpusAccessGrant
        if request.user.role in ('SUPER_ADMIN', 'ADMIN'):
            return True
        if obj.creator == request.user:
            return True
        return SubcorpusAccessGrant.objects.filter(
            subcorpus=obj, user=request.user, permission_level='EDIT'
        ).exists()