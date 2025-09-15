from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import product_views
from django.views.generic import RedirectView
from .views import LegalView, terms_redirect, privacy_redirect
from .views import WarmLoginView 
from django.urls import path, re_path
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

    path("api/auth/status/", views.auth_status, name="auth_status"),
    path("api/track", views.track_event, name="track_event"),

    path("landing/", views.landing, name="landing"),
    path("book-demo/", views.book_demo, name="book_demo"),


    path("products/mockup/", product_views.product_mockup, name="product_mockup"),

    path("demo/", product_views.demo_dashboard, {"section":"clinical"}, name="demo_dashboard_home"),
    path("demo/<slug:section>/", product_views.demo_dashboard, name="demo_dashboard"),


    path("api/summarize/", views.summarize_medical_record, name="summarize_medical_record"),
    path("api/chat/", views.send_chat, name="send_chat"),
    path("api/smart-suggestions/", views.smart_suggestions, name="smart_suggestions"),


    path("portal/", product_views.portal_home, name="portal_home"),
    path("portal/login/", product_views.OrgLockedLoginView.as_view(), name="portal_login"),
    path("portal/logout/", product_views.portal_logout, name="portal_logout"),
    path("portal/dashboard/", product_views.portal_dashboard, name="portal_dashboard"),

    # Portal OTP / password flow (names used in templates)
    path("portal/forgot/", product_views.portal_password_forgot, name="portal_password_forgot"),
    path("portal/otp/", product_views.portal_verify_otp, name="portal_password_otp"),
    path("portal/resend-otp/", product_views.portal_resend_otp, name="portal_resend_otp"),
    path("portal/reset/", product_views.portal_reset_password, name="portal_password_reset_otp"),

    path("portal/encounters/<int:pk>/", product_views.portal_encounter_detail, name="portal_encounter_detail"),

    # ------------------------------
    # Staff/dev tenant admin
    # ------------------------------
    path("dev/clients/new/", product_views.dev_client_create, name="dev_client_create"),
    path("dev/clients/<slug:slug>/", product_views.dev_client_detail, name="dev_client_detail"),
    path("dev/clients/<slug:slug>/users/new/", product_views.dev_client_user_create, name="dev_client_user_create"),
    path("dev/clients/<slug:slug>/users/reset/", product_views.dev_client_user_reset_password, name="dev_client_user_reset_password"),

    # ------------------------------
    # Staff PWA app shells (pin these)
    # ------------------------------
    path("app/triage", product_views.app_triage, name="app_triage"),
    path("app/frontdesk", product_views.app_frontdesk, name="app_frontdesk"),
    path("app/clinical", product_views.app_clinical, name="app_clinical"),
    path("app/diagnostics", product_views.app_diagnostics, name="app_diagnostics"),
    path("app/scribe", product_views.app_scribe, name="app_scribe"),
    path("app/coding", product_views.app_coding, name="app_coding"),
    path("app/care", product_views.app_care, name="app_care"),

    # ------------------------------
    # Kiosk (tokenized / no login)
    # ------------------------------
    path("kiosk/intake", product_views.kiosk_intake, name="kiosk_intake"),
    path("kiosk/consent", product_views.kiosk_consent, name="kiosk_consent"),

    # ------------------------------
    # Product API v1 (clean namespace)
    # ------------------------------
    path("api/v1/triage/chat", product_views.api_v1_triage_chat, name="api_v1_triage_chat"),
    path("api/v1/upload", product_views.api_v1_upload, name="api_v1_upload"),
    path("api/v1/encounters/<int:pk>", product_views.api_v1_encounter_get, name="api_v1_encounter_get"),
    path("api/v1/encounters/move", product_views.api_v1_encounter_move, name="api_v1_encounter_move"),

    path("api/v1/triage/submit", product_views.api_v1_triage_submit, name="api_v1_triage_submit"),
    path("api/v1/triage/<int:encounter_id>", product_views.api_v1_triage_get, name="api_v1_triage_get"),

    path("api/v1/scheduling/suggest", product_views.api_v1_sched_suggest, name="api_v1_sched_suggest"),
    path("api/v1/scheduling/book", product_views.api_v1_sched_book, name="api_v1_sched_book"),

    path("api/v1/clinical/chart-brief", product_views.api_v1_chart_brief, name="api_v1_chart_brief"),
    path("api/v1/diagnostics/interpret", product_views.api_v1_diag_interpret, name="api_v1_diag_interpret"),

    path("api/v1/coding/suggest", product_views.api_v1_coding_suggest, name="api_v1_coding_suggest"),
    path("api/v1/claim/draft", product_views.api_v1_claim_draft, name="api_v1_claim_draft"),

    path("api/v1/careplan/generate", product_views.api_v1_careplan_generate, name="api_v1_careplan_generate"),
    path("api/v1/messages/send", product_views.api_v1_messages_send, name="api_v1_messages_send"),

    # ------------------------------
    # Ops: Launch links & device control
    # ------------------------------
    path("ops/launch-links/", product_views.launch_links, name="launch_links"),
    path("ops/launch-links/new", product_views.launch_links_new, name="launch_links_new"),
    path("ops/devices/revoke/<str:token_id>", product_views.launch_device_revoke, name="launch_device_revoke"),

]


from django.urls import path
from myApp import views

handler404 = "myApp.views.page_not_found_view"
handler500 = "myApp.views.server_error_view"