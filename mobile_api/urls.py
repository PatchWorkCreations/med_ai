from django.urls import path
from . import views

app_name = "mobile_api"

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('user/settings/', views.user_settings, name='user_settings'),
    path('auth/status/', views.auth_status, name='auth_status'),
    path('health/', views.health, name='health'),
    path('chat/sessions/', views.chat_sessions, name='chat_sessions'),
    path('send-chat/', views.send_chat, name='send_chat'),
    path('summarize/', views.summarize, name='summarize'),
]

