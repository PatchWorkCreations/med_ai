from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.db import models

LANGUAGE_CHOICES = [
        ('en-US', 'English'),
        ('ja-JP', 'Japanese'),
        ('es-ES', 'Spanish'),
        ('fr-FR', 'French'),
        ('de-DE', 'German'),
        ('it-IT', 'Italian'),
        ('pt-PT', 'Portuguese (Portugal)'),
        ('pt-BR', 'Portuguese (Brazil)'),
        ('ru-RU', 'Russian'),
        ('zh-CN', 'Chinese (Simplified)'),
        ('zh-TW', 'Chinese (Traditional)'),
        ('ko-KR', 'Korean'),
        ('ar-SA', 'Arabic (Saudi Arabia)'),
        ('tr-TR', 'Turkish'),
        ('nl-NL', 'Dutch'),
        ('sv-SE', 'Swedish'),
        ('pl-PL', 'Polish'),
        ('da-DK', 'Danish'),
        ('no-NO', 'Norwegian'),
        ('fi-FI', 'Finnish'),
        ('he-IL', 'Hebrew'),
        ('th-TH', 'Thai'),
        ('hi-IN', 'Hindi'),
        ('cs-CZ', 'Czech'),
        ('ro-RO', 'Romanian'),
        ('hu-HU', 'Hungarian'),
        ('sk-SK', 'Slovak'),
        ('bg-BG', 'Bulgarian'),
        ('uk-UA', 'Ukrainian'),
        ('vi-VN', 'Vietnamese'),
        ('id-ID', 'Indonesian'),
        ('ms-MY', 'Malay'),
        ('sr-RS', 'Serbian'),
        ('hr-HR', 'Croatian'),
        ('el-GR', 'Greek'),
        ('lt-LT', 'Lithuanian'),
        ('lv-LV', 'Latvian'),
        ('et-EE', 'Estonian'),
        ('sl-SI', 'Slovenian'),
        ('is-IS', 'Icelandic'),
        ('sq-AL', 'Albanian'),
        ('mk-MK', 'Macedonian'),
        ('bs-BA', 'Bosnian'),
        ('ca-ES', 'Catalan'),
        ('gl-ES', 'Galician'),
        ('eu-ES', 'Basque'),
        ('hy-AM', 'Armenian'),
        ('fa-IR', 'Persian'),
        ('sw-KE', 'Swahili'),
        ('ta-IN', 'Tamil'),
        ('te-IN', 'Telugu'),
        ('kn-IN', 'Kannada'),
        ('ml-IN', 'Malayalam'),
        ('mr-IN', 'Marathi'),
        ('pa-IN', 'Punjabi'),
        ('gu-IN', 'Gujarati'),
        ('or-IN', 'Odia'),
        ('as-IN', 'Assamese'),
        ('ne-NP', 'Nepali'),
        ('si-LK', 'Sinhala'),
    ]

class MedicalSummary(models.Model):
    CARE_CHOICES = [
        ("hospital", "Hospital/Discharge"),
        ("ambulatory", "Ambulatory/Clinic"),
        ("urgent", "Urgent Care"),
    ]
    care_setting = models.CharField(
        max_length=16, choices=CARE_CHOICES, default="hospital", db_index=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="summaries")
    uploaded_filename = models.CharField(max_length=255)
    tone = models.CharField(max_length=50)
    raw_text = models.TextField()
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


from django.db import models
from django.contrib.auth.models import User

# models.py

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    profession = models.CharField(max_length=100, blank=True, null=True)
    display_name = models.CharField(max_length=100, blank=True, null=True)

    # ✅ New field
    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='en-US'
    )
    
    # Settings stored as JSON for flexibility
    # Note: Named 'user_settings' to avoid conflict with django.conf.settings
    user_settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="User settings: appearance, accent_color, spoken_language, voice, separate_voice_mode, show_additional_models, personalization, etc."
    )

    signup_ip = models.GenericIPAddressField(blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    signup_country = models.CharField(max_length=2, blank=True, null=True)     # e.g. "PH"
    last_login_country = models.CharField(max_length=2, blank=True, null=True) # e.g. "PH"

    # Referral code system
    personal_referral_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text="User's personal referral code that they can share with others"
    )
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='referrals',
        help_text="User who referred this account (via referral code)"
    )

    # Subscription fields
    plan = models.CharField(
        max_length=20,
        default='free',
        choices=[
            ('free', 'Free'),
            ('monthly', 'Monthly'),
            ('annual', 'Annual'),
            ('clinical', 'Clinical'),
        ],
        help_text="User's subscription plan"
    )
    subscription_status = models.CharField(
        max_length=20,
        default='inactive',
        choices=[
            ('active', 'Active'),
            ('past_due', 'Past Due'),
            ('canceled', 'Canceled'),
            ('inactive', 'Inactive'),
            ('manual', 'Manual'),
        ],
        help_text="Current subscription status"
    )
    subscription_ends_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the subscription period ends"
    )
    paypal_customer_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="PayPal customer ID (Payer ID)"
    )

    def __str__(self):
        return f"{self.display_name or self.user.username} Profile"
from django.utils import timezone

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    messages = models.JSONField(default=list)  # [{role, content, ts, meta?}]
    updated_at = models.DateTimeField(auto_now=True)

    # 🔹 New (safe defaults)
    title = models.CharField(max_length=200, blank=True, default="")
    tone  = models.CharField(max_length=50, blank=True, default="PlainClinical")
    lang  = models.CharField(max_length=10, blank=True, default="en-US")
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    archived = models.BooleanField(default=False)

    class Meta:
        ordering = ['-updated_at']


class InteractionProfile(models.Model):
    """
    Tracks user communication preferences (inferred, not configured).
    Profiles are context-sensitive, not identity-defining.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='interaction_profile'
    )
    session_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    
    # Preference dimensions (0.0 to 1.0 scale)
    verbosity_level = models.FloatField(default=0.5)  # 0=low, 1=high
    emotional_support = models.FloatField(default=0.5)  # 0=low, 1=high
    structure_preference = models.FloatField(default=0.5)  # 0=freeform, 1=stepwise
    technical_depth = models.FloatField(default=0.5)  # 0=low, 1=high
    response_pacing = models.FloatField(default=0.5)  # 0=fast, 1=normal
    
    # Metadata
    last_updated_at = models.DateTimeField(auto_now=True)
    interaction_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'interaction_profiles'
        indexes = [
            models.Index(fields=['user'], name='interaction_user_idx'),
            models.Index(fields=['session_id'], name='interaction_session_idx'),
        ]
    
    def __str__(self):
        if self.user:
            return f"InteractionProfile for {self.user.username}"
        return f"InteractionProfile for session {self.session_id}"

import uuid
from django.db import models

class BetaFeedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Consent & meta
    consent = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    # Profile
    role = models.CharField(max_length=32)
    email = models.EmailField(blank=True, null=True)
    device = models.CharField(max_length=32)
    browser = models.CharField(max_length=64)

    # Usage
    use_case = models.CharField(max_length=200)
    input_type = models.CharField(max_length=64)

    # Ratings
    ease = models.PositiveSmallIntegerField(default=3)
    speed = models.PositiveSmallIntegerField(default=3)
    accuracy = models.PositiveSmallIntegerField(default=3)
    clarity = models.PositiveSmallIntegerField(default=3)
    nps = models.PositiveSmallIntegerField()

    # Open feedback
    pros = models.TextField(blank=True)
    cons = models.TextField(blank=True)
    bugs = models.TextField(blank=True)

    # Attachment
    screenshot = models.ImageField(upload_to="beta_screens/", blank=True, null=True)

    # Permissions
    allow_contact = models.BooleanField(default=False)
    allow_anon = models.BooleanField(default=True)

    def __str__(self):
        return f"Feedback {self.id} — {self.role}"

# myApp/models.py
# --- Multi-tenancy core (models only) ---

from threading import local
from django.conf import settings
from django.db import models

# ---------------------------------------------------------------------
# Thread-local org context (set by middleware; used by scoped managers)
# ---------------------------------------------------------------------
_thread = local()

def set_current_org(org):  # middleware will call this
    setattr(_thread, "org", org)

def get_current_org():
    return getattr(_thread, "org", None)

# ---------------------------------------------------------------------
# Organizations and domain mapping (host -> org)
# ---------------------------------------------------------------------
class Org(models.Model):
    name       = models.CharField(max_length=120)
    slug       = models.SlugField(unique=True)  # e.g., "mercycare"
    is_active  = models.BooleanField(default=True)
    # Branding / plan (optional but handy)
    logo_url   = models.URLField(blank=True, default="")
    theme      = models.JSONField(default=dict, blank=True)   # {"primary":"#0b3b36", ...}
    plan       = models.CharField(max_length=40, default="standard")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class OrgDomain(models.Model):
    """
    Maps a fully-qualified host to an Org, e.g.:
      - "mercycare.neuromedai.org"
      - "portal.mercycareclinic.com"
    The middleware will look up request.get_host() here.
    """
    org        = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="domains")
    domain     = models.CharField(max_length=255, unique=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Organization Domain"
        verbose_name_plural = "Organization Domains"

    def __str__(self):
        return self.domain

# ---------------------------------------------------------------------
# Memberships and roles
# ---------------------------------------------------------------------
class OrgMembership(models.Model):
    ROLE_CHOICES = [
        ("OWNER", "Owner"),
        ("ADMIN", "Admin"),
        ("CLINICIAN", "Clinician"),
        ("FRONT_DESK", "Front Desk"),
        ("CODER", "Coder"),
        ("VIEWER", "Viewer"),
    ]
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    org        = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="memberships")
    role       = models.CharField(max_length=20, choices=ROLE_CHOICES, default="VIEWER")
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "org")]

    def __str__(self):
        return f"{self.user} @ {self.org} ({self.role})"

# ---------------------------------------------------------------------
# Scoped managers (auto-filter by current org)
# ---------------------------------------------------------------------
class OrgQuerySet(models.QuerySet):
    def for_current_org(self):
        org = get_current_org()
        return self.filter(org=org) if org else self.none()

class OrgManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        org = get_current_org()
        return qs.filter(org=org) if org else qs.none()

class OrgAllManager(models.Manager):
    """Unscoped manager for admin/maintenance jobs ONLY."""
    def get_queryset(self):
        return super().get_queryset()

class OrgOwnedModel(models.Model):
    """Base for any row that belongs to a specific organization."""
    org = models.ForeignKey(Org, on_delete=models.CASCADE, related_name="%(class)ss")

    # Default manager: always scoped to the current org
    objects = OrgManager()
    # Admin-only escape hatch
    all_objects = OrgAllManager()

    class Meta:
        abstract = True

# ---------------------------------------------------------------------
# Example domain models (org-owned)
# ---------------------------------------------------------------------
class Patient(OrgOwnedModel):
    first_name = models.CharField(max_length=80)
    last_name  = models.CharField(max_length=80)
    dob        = models.DateField(null=True, blank=True)
    mrn        = models.CharField(max_length=64, blank=True, default="")
    phone      = models.CharField(max_length=30, blank=True, default="")
    email      = models.EmailField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["org", "mrn"], name="uniq_mrn_per_org")
        ]
        indexes = [
            models.Index(fields=["org", "last_name", "first_name"]),
        ]

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"

class Encounter(OrgOwnedModel):
    STATUS_CHOICES = [
        ("new", "New"),
        ("screening", "Screening"),
        ("ready", "Ready"),
        ("scheduled", "Scheduled"),
        ("closed", "Closed"),
    ]
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="encounters")
    patient    = models.ForeignKey(Patient, null=True, blank=True, on_delete=models.SET_NULL)
    reason     = models.CharField(max_length=255, blank=True, default="General")
    status     = models.CharField(max_length=16, choices=STATUS_CHOICES, default="new")
    priority   = models.CharField(max_length=16, default="medium")
    summary    = models.TextField(blank=True, default="")
    icd        = models.JSONField(default=list, blank=True)
    cpt        = models.JSONField(default=list, blank=True)
    denials    = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["org", "status"]),
            models.Index(fields=["org", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.org.slug}] Encounter #{self.id} – {self.reason}"


# ---------------------------------------------------------------------
# Website Activity Tracking Models
# ---------------------------------------------------------------------
from django.utils import timezone
from datetime import timedelta

class Visitor(models.Model):
    """Track website visitors and page views"""
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    referer = models.URLField(blank=True)
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=10, default='GET')
    session_key = models.CharField(max_length=100, blank=True)
    is_unique = models.BooleanField(default=True, help_text="First visit from this IP in 24 hours")
    
    # Enhanced tracking fields
    country = models.CharField(max_length=2, blank=True, help_text="Country code (e.g., US, UK)")
    city = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=20, blank=True, choices=[
        ('desktop', 'Desktop'),
        ('mobile', 'Mobile'),
        ('tablet', 'Tablet'),
        ('other', 'Other'),
    ])
    browser = models.CharField(max_length=50, blank=True, help_text="Browser name (Chrome, Firefox, etc.)")
    os = models.CharField(max_length=50, blank=True, help_text="Operating system")
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    utm_term = models.CharField(max_length=100, blank=True)
    utm_content = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['path', 'created_at']),
        ]
        verbose_name = "Visitor"
        verbose_name_plural = "Visitors"
    
    def __str__(self):
        return f"{self.ip_address} - {self.path} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class UserSignup(models.Model):
    """Track user signups/registrations"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='signup_record')
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    referer = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "User Signup"
        verbose_name_plural = "User Signups"
    
    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class UserSignin(models.Model):
    """Track user login activity"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='signin_records')
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
        verbose_name = "User Signin"
        verbose_name_plural = "User Signins"
    
    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.user.username} - {status} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class PageView(models.Model):
    """Track individual page views with more detail"""
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name='page_views', null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    path = models.CharField(max_length=500)
    page_title = models.CharField(max_length=200, blank=True)
    duration = models.IntegerField(default=0, help_text="Time spent on page in seconds")
    
    # Enhanced tracking fields
    referer = models.URLField(blank=True, help_text="Referrer URL")
    exit_page = models.BooleanField(default=False, help_text="Is this an exit page?")
    entry_page = models.BooleanField(default=False, help_text="Is this an entry page?")
    scroll_depth = models.IntegerField(default=0, help_text="Scroll percentage (0-100)")
    time_on_page = models.IntegerField(default=0, help_text="Time on page in seconds")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['path', '-created_at']),
        ]
        verbose_name = "Page View"
        verbose_name_plural = "Page Views"
    
    def __str__(self):
        return f"{self.path} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class Session(models.Model):
    """Track user sessions for analytics"""
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name='sessions', null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=100, db_index=True, help_text="Custom session identifier")
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0, help_text="Session duration in seconds")
    page_count = models.IntegerField(default=0, help_text="Number of pages viewed")
    is_bounce = models.BooleanField(default=False, help_text="Single page visit")
    referer = models.URLField(blank=True)
    entry_page = models.CharField(max_length=500, blank=True)
    exit_page = models.CharField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['-started_at']),
            models.Index(fields=['session_id']),
        ]
        verbose_name = "Session"
        verbose_name_plural = "Sessions"
    
    def __str__(self):
        return f"Session {self.session_id} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"


class Event(models.Model):
    """Track custom events (clicks, downloads, etc.)"""
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name='events', null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session = models.ForeignKey(Session, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=50, db_index=True, help_text="click, download, submit, etc.")
    event_name = models.CharField(max_length=100, help_text="Name of the event")
    properties = models.JSONField(default=dict, blank=True, help_text="Additional event properties")
    path = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['event_type', '-created_at']),
        ]
        verbose_name = "Event"
        verbose_name_plural = "Events"
    
    def __str__(self):
        return f"{self.event_name} ({self.event_type}) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class Campaign(models.Model):
    """Track marketing campaigns"""
    name = models.CharField(max_length=100)
    utm_source = models.CharField(max_length=100)
    utm_medium = models.CharField(max_length=100)
    utm_campaign = models.CharField(max_length=100, unique=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"
    
    def __str__(self):
        return f"{self.name} ({self.utm_campaign})"


# =============================
# Subscription & Payment Models
# =============================

class Subscription(models.Model):
    """Tracks user subscriptions"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.CharField(
        max_length=20,
        choices=[
            ('monthly', 'Monthly'),
            ('annual', 'Annual'),
            ('clinical', 'Clinical'),
        ]
    )
    paypal_subscription_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        help_text="PayPal subscription ID"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('past_due', 'Past Due'),
            ('canceled', 'Canceled'),
            ('inactive', 'Inactive'),
            ('manual', 'Manual'),
        ],
        default='inactive'
    )
    current_period_end = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the current billing period ends"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.plan} ({self.status})"


class Payment(models.Model):
    """Tracks payment transactions"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments"
    )
    paypal_order_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="PayPal order ID"
    )
    paypal_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="PayPal transaction ID"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount in USD"
    )
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ],
        default='pending'
    )
    plan_id = models.CharField(
        max_length=20,
        help_text="Plan ID (monthly, annual, clinical)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['paypal_order_id']),
        ]

    def __str__(self):
        return f"{self.user.username} - ${self.amount} - {self.status}"
