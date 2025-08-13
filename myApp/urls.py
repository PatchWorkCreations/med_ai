from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.views.generic import RedirectView
from .views import LegalView, terms_redirect, privacy_redirect
from .views import WarmLoginView 

urlpatterns = [
    # Public Pages
    path('', views.landing_page, name='home'),
    path('signup/', views.signup_view, name='signup'),

    # Auth Pages
    path('login/', WarmLoginView.as_view(), name='login'),
    path("logout/", views.logout_view, name="logout"),
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
    

    path("legal/", LegalView.as_view(), name="legal"),
    # Optional convenience routes that jump to the correct section
    path("terms/", terms_redirect, name="terms"),
    path("privacy/", privacy_redirect, name="privacy"),

    path("password/forgot/", views.forgot_password, name="password_forgot"),
    path("password/otp/", views.verify_otp, name="password_otp"),
    path("password/otp/resend/", views.resend_otp, name="password_otp_resend"),
    path("password/reset/", views.reset_password, name="password_reset_otp"),
]
