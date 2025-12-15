from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-6_$3$%3_hxmh@la&^k7g%()ol5nwsc(ne9f#0^_f^lo^yp7-vp'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG=True

ALLOWED_HOSTS = [
    "neuromedai.org", ".neuromedai.org",
    "medai-production-21ae.up.railway.app",
    "localhost", "127.0.0.1",
    ".localtest.me",          # ← allow any *.localtest.me subdomain
    ".lvh.me",                # ← optional alt to localtest.me
]

CSRF_TRUSTED_ORIGINS = [
    "https://neuromedai.org",
    "https://*.neuromedai.org",
    "https://medai-production-21ae.up.railway.app",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://*.localtest.me:8000",  # ← add
    "http://*.lvh.me:8000",        # ← optional
]


import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'myApp',
    'widget_tweaks',
    'channels',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'myProject.middleware.BusyModeMiddleware',
    'myApp.middleware.VisitorTrackingMiddleware',  # Track website visitors
    'myApp.middleware.CurrentOrgByHostMiddleware',
    'myApp.middleware.EnforceOrgMembershipMiddleware',
    'myApp.middleware.CountryMiddleware',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

ROOT_URLCONF = 'myProject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'myProject.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True  # Railway requires SSL for Postgres
    )
}



# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True



STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Optional if you're collecting from multiple apps:
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]



DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}


AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]


LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'


ASGI_APPLICATION = 'myProject.asgi.application'

# Optional: Define channel layers (needed if you use Redis later)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}


# Auth redirects
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/new/'
LOGOUT_REDIRECT_URL = '/'


# ensure Pillow installed: pip install Pillow
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# settings.py
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",   # table name
        "TIMEOUT": 10 * 60,           # 10 minutes (OTP TTL)
    }
}


SESSION_COOKIE_SECURE = False      # True only in HTTPS
CSRF_COOKIE_SECURE = False         # True only in HTTPS
SESSION_COOKIE_AGE = 15 * 60       # 15 minutes is plenty for reset
SESSION_SAVE_EVERY_REQUEST = True

# CSRF settings for iOS/mobile app
CSRF_COOKIE_HTTPONLY = False       # Allow JavaScript/native apps to read the cookie
CSRF_COOKIE_SAMESITE = 'Lax'       # 'None' if you need cross-site requests (requires HTTPS)
CSRF_COOKIE_NAME = 'csrftoken'     # Default name, explicit for clarity
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'  # Default header name Django expects


import os
import environ
import os

# If you still use Django's send_mail elsewhere, keep it from tripping in prod:
DEBUG = os.environ.get("DEBUG", "False").lower() in ("1","true","yes")

# Not strictly required for Resend (we’ll call the HTTP API), but safe defaults:
EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend" if DEBUG
    else "django.core.mail.backends.dummy.EmailBackend"
)

# Useful for emails you render or any fallback usage
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL") or os.environ.get("RESEND_FROM")

# Resend config (used by your utility function)
RESEND = {
    "API_KEY": os.environ.get("RESEND_API_KEY"),
    "FROM": os.environ.get("RESEND_FROM"),
    "REPLY_TO": os.environ.get("RESEND_REPLY_TO"),
    "BASE_URL": os.environ.get("RESEND_BASE_URL", "https://api.resend.com"),
}

# Google OAuth Configuration
# Get these from: https://console.cloud.google.com/apis/credentials
# After creating OAuth 2.0 Client ID, add to .env file:
# GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
# GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
# Enable/disable Google OAuth (set to "true" to enable, "false" to disable)
# Set to "false" in production until OAuth app verification is complete
# Local: GOOGLE_OAUTH_ENABLED=true
# Production: GOOGLE_OAUTH_ENABLED=false (until verified)
GOOGLE_OAUTH_ENABLED = os.getenv("GOOGLE_OAUTH_ENABLED", "true").lower() in ("true", "1", "yes")
