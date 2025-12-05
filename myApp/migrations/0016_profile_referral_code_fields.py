# Generated manually for referral code system

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0015_campaign_pageview_entry_page_pageview_exit_page_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='personal_referral_code',
            field=models.CharField(blank=True, help_text="User's personal referral code that they can share with others", max_length=20, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='referred_by',
            field=models.ForeignKey(blank=True, help_text="User who referred this account (via referral code)", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='referrals', to=settings.AUTH_USER_MODEL),
        ),
    ]

