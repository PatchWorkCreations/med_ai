from django.db import models
from django.contrib.auth.models import User

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
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    profession = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100, blank=True, null=True)

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
