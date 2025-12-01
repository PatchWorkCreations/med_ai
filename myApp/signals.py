# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile, UserSignup

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        # Track signup if UserSignup doesn't exist (fallback for programmatic user creation)
        if not hasattr(instance, 'signup_record'):
            try:
                UserSignup.objects.create(
                    user=instance,
                    ip_address='',  # Will be set in view if available
                    user_agent='',
                    referer=''
                )
            except Exception:
                pass  # Don't block user creation if tracking fails

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
