from django.contrib import admin
from django.urls import path, include
from django.conf import settings

# iOS API routes - MUST be BEFORE myApp.urls to take precedence
# These routes are for iOS/mobile app and need to match first
from mobile_api import views as mobile_views
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # iOS/Mobile API routes - Processed FIRST to take precedence
    # Auth endpoints
    path('api/login/', mobile_views.login, name='mobile_api_login'),
    path('api/signup/', mobile_views.signup, name='mobile_api_signup'),
    path('api/auth/status/', mobile_views.auth_status, name='mobile_api_auth_status'),
    
    # User endpoints - NOTE: These are handled by myApp.urls for web app compatibility
    # Mobile-specific endpoints moved to /api/mobile/ prefix to avoid conflicts
    path('api/mobile/user/settings/', mobile_views.user_settings, name='mobile_api_user_settings'),
    path('api/mobile/user/settings/update/', mobile_views.user_settings_update, name='mobile_api_user_settings_update'),
    path('api/mobile/user/preferences/', mobile_views.user_preferences, name='mobile_api_user_preferences'),
    path('api/mobile/user/preferences/update/', mobile_views.user_preferences_update, name='mobile_api_user_preferences_update'),
    
    # Chat endpoints - NOTE: These are handled by myApp.urls for web app compatibility  
    # Mobile-specific endpoints moved to /api/mobile/ prefix to avoid conflicts
    path('api/mobile/chat/sessions/', mobile_views.chat_sessions, name='mobile_api_chat_sessions'),
    path('api/mobile/chat/sessions/new/', mobile_views.create_chat_session, name='mobile_api_create_session'),
    path('api/mobile/chat/clear-session/', mobile_views.clear_session, name='mobile_api_clear_session'),
    path('api/mobile/send-chat/', mobile_views.send_chat, name='mobile_api_send_chat'),
    
    # Tone management
    path('api/tones/', mobile_views.tones, name='mobile_api_tones'),
    path('api/tones/<str:tone_id>/', mobile_views.tone_detail, name='mobile_api_tone_detail'),
    
    # Medical summaries
    path('api/summarize/', mobile_views.summarize, name='mobile_api_summarize'),
    
    # App configuration
    path('api/config/', mobile_views.config, name='mobile_api_config'),
    
    # Main app routes (processed AFTER mobile_api routes)
    path('', include("myApp.urls")),
]

# Mobile API routes - isolated under /api/mobile/ to avoid conflicts with main site
# Only enabled if MOBILE_API_ENABLED feature flag is set
if getattr(settings, 'MOBILE_API_ENABLED', False):
    from mobile_api import compat_urls
    urlpatterns += [
        path('api/mobile/', include((compat_urls.urlpatterns, 'mobile_api_compat'))),
    ]
