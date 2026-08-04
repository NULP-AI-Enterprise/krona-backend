from django.contrib import admin
from .models import Corpus, UserSubcorpus, FilteredSubcorpus, Text, TextMetadata, CorpusUserAccess, CorpusShare

admin.site.register(UserSubcorpus)
admin.site.register(FilteredSubcorpus)
admin.site.register(CorpusUserAccess)
admin.site.register(CorpusShare)


class BaseContentAdmin(admin.ModelAdmin):
    def _is_admin(self, request):
        return request.user.is_authenticated and getattr(request.user, 'role', None) in ['SUPER_ADMIN', 'ADMIN']

    def has_module_permission(self, request):
        return self._is_admin(request)

    def has_view_permission(self, request, obj=None):
        return self._is_admin(request)

    def has_add_permission(self, request):
        return self._is_admin(request)

    def has_change_permission(self, request, obj=None):
        return self._is_admin(request)

    def has_delete_permission(self, request, obj=None):
        return self._is_admin(request)


class CorpusUserAccessInline(admin.TabularInline):
    model = CorpusUserAccess
    extra = 1 

@admin.register(Corpus)
class CorpusAdmin(BaseContentAdmin):
    list_display = ['name', 'type', 'language', 'creator']
    
    inlines = [CorpusUserAccessInline]

class TextMetadataInline(admin.TabularInline):
    model = TextMetadata
    extra = 1

@admin.register(Text)
class TextAdmin(BaseContentAdmin):
    
    inlines = [TextMetadataInline]


