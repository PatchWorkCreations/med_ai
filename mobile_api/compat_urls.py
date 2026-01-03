"""
Compatibility URLs matching iOS frontend expectations.
These routes match the exact paths the frontend expects.
"""
from django.urls import path
from . import compat_views

app_name = "mobile_api_compat"

urlpatterns = [
    # Config endpoint
    path('config/', compat_views.config, name='config'),
    
    # Auth endpoints
    path('auth/status/', compat_views.auth_status, name='auth_status'),
    path('login/', compat_views.login, name='login'),
    path('signup/', compat_views.signup, name='signup'),
    
    # User endpoints
    path('user/settings/', compat_views.user_settings, name='user_settings'),
    path('user/settings/update/', compat_views.user_settings_update, name='user_settings_update'),
    path('user/preferences/', compat_views.user_preferences, name='user_preferences'),
    path('user/preferences/update/', compat_views.user_preferences, name='user_preferences_update'),  # Alias for PUT
    
    # Chat endpoints
    path('chat/sessions/', compat_views.chat_sessions, name='chat_sessions'),
    path('chat/sessions/new/', compat_views.create_chat_session, name='create_chat_session'),
    path('chat/clear-session/', compat_views.clear_session, name='clear_session'),
    path('send-chat/', compat_views.send_chat, name='send_chat'),
    
    # Medical summary endpoints
    path('summarize/', compat_views.summarize, name='summarize'),
    
    # Tones endpoint
    path('tones/', compat_views.tones, name='tones'),
]

# Google auth endpoint (separate from /api/ prefix)
google_auth_urlpatterns = [
    path('google/', compat_views.google_signin, name='google_signin'),
]

