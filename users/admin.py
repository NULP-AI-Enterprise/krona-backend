from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'full_name', 'role', 'is_staff']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Персональна інформація', {'fields': ('full_name', 'phone_number', 'role')}),
        ('Права доступу', {'fields': ('is_staff', 'is_superuser', 'user_permissions')}),
        ('Важливі дати', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'phone_number', 'role', 'password'),
        }),
    )
    ordering = ['email']
    search_fields = ['email', 'full_name', 'phone_number']

    def _is_admin(self, request):
        return request.user.is_authenticated and getattr(request.user, 'role', None) in [CustomUser.Role.SUPER_ADMIN, CustomUser.Role.ADMIN]
    
    def has_module_permission(self, request):
        return self._is_admin(request)

    def has_view_permission(self, request, obj=None):
        return self._is_admin(request)

    def has_add_permission(self, request):
        return self._is_admin(request)

    def has_change_permission(self, request, obj=None):
        if not self._is_admin(request):
            return False
        if not obj:
            return True
            
        if request.user.role == CustomUser.Role.ADMIN and obj.role in [CustomUser.Role.SUPER_ADMIN, CustomUser.Role.ADMIN]:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        if not self._is_admin(request):
            return False
        if not obj:
            return True
            
        if request.user.role == CustomUser.Role.ADMIN and obj.role in [CustomUser.Role.SUPER_ADMIN, CustomUser.Role.ADMIN]:
            return False
        return True

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if getattr(request.user, 'role', None) == CustomUser.Role.ADMIN:
            if 'role' in form.base_fields:
                form.base_fields['role'].choices = [
                    (CustomUser.Role.COMPILER, 'Укладач'),
                    (CustomUser.Role.USER, 'Користувач'),
                ]
        return form
    
admin.site.register(CustomUser, CustomUserAdmin)