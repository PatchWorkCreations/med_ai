from django.urls import path
from . import views

app_name = "mobile_api"

urlpatterns = [
    # Auth endpoints
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('auth/status/', views.auth_status, name='auth_status'),
    path('health/', views.health, name='health'),
    
    # User endpoints
    path('user/settings/', views.user_settings, name='user_settings'),
    path('user/settings/update/', views.user_settings_update, name='user_settings_update'),
    path('user/preferences/', views.user_preferences, name='user_preferences'),
    path('user/preferences/update/', views.user_preferences_update, name='user_preferences_update'),
    
    # Chat endpoints
    path('chat/sessions/', views.chat_sessions, name='chat_sessions'),
    path('chat/sessions/new/', views.create_chat_session, name='create_chat_session'),
    path('chat/clear-session/', views.clear_session, name='clear_session'),
    path('send-chat/', views.send_chat, name='send_chat'),
    
    # Tone management
    path('tones/', views.tones, name='tones'),
    path('tones/<str:tone_id>/', views.tone_detail, name='tone_detail'),
    
    # Medical summaries
    path('summarize/', views.summarize, name='summarize'),
    
    # App configuration
    path('config/', views.config, name='config'),
]

