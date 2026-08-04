from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from corpus.views.health import health_check

urlpatterns = [
    path('api/health/', health_check),
    path('admin/', admin.site.urls),
    path('chaining/', include('smart_selects.urls')),
    path('', include('corpus.urls')),
    path('api/auth/', include('users.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
