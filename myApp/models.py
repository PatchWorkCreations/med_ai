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

    signup_ip = models.GenericIPAddressField(blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    signup_country = models.CharField(max_length=2, blank=True, null=True)     # e.g. "PH"
    last_login_country = models.CharField(max_length=2, blank=True, null=True) # e.g. "PH"

    def __str__(self):
        return f"{self.display_name or self.user.username} Profile"

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    messages = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)


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

# Tip: next, migrate your other PHI models (Document, Task, Appointment, Claim,
# Message, MedicalSummary) to inherit OrgOwnedModel the same way.
