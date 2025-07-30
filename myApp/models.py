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

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    profession = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user.username} Profile"


class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    messages = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)
