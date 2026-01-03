from django.contrib import admin
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("myApp.urls")),
]

# Mobile API routes - isolated under /api/mobile/ to avoid conflicts with main site
# Only enabled if MOBILE_API_ENABLED feature flag is set
if getattr(settings, 'MOBILE_API_ENABLED', False):
    from mobile_api import compat_urls
    urlpatterns += [
        path('api/mobile/', include((compat_urls.urlpatterns, 'mobile_api_compat'))),
    ]
