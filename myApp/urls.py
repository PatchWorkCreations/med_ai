from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.views.generic import RedirectView

urlpatterns = [
    # Public Pages
    path('', views.landing_page, name='home'),
    path('signup/', views.signup_view, name='signup'),

    # Auth Pages
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='login.html',
            redirect_authenticated_user=True
        ),
        name='login'
    ),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    # Authenticated Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # API Endpoints
    path("api/summarize/", views.summarize_medical_record, name="summarize"),
    path("api/smart-suggestions/", views.smart_suggestions, name="smart_suggestions"),
    path("api/answer-question/", views.answer_question, name="answer_question"),
    path("api/send-chat/", views.send_chat, name="send_chat"),

     path('about/', views.about_page, name='about'),

     path('speak/', views.speaking_view, name='speaking-page'),


      path("api/user/settings/", views.get_user_settings, name="get_user_settings"),
    path("api/user/settings/update/", views.update_user_settings, name="update_user_settings"),
    path("clear-session/", views.clear_session, name="clear-session"),

    path('accounts/login/', RedirectView.as_view(url='/login/', permanent=False)),

        path("beta/", views.beta_feedback, name="beta_feedback"),
    path("beta/thanks/", views.beta_thanks, name="beta_thanks"),
    # new JSON endpoint:
    path("beta/api/submit/", views.beta_feedback_api, name="beta_feedback_api"),
    
]
