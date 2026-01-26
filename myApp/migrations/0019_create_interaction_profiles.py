# Generated manually for Adaptive Response System

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0018_profile_paypal_customer_id_profile_plan_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='InteractionProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ('verbosity_level', models.FloatField(default=0.5)),
                ('emotional_support', models.FloatField(default=0.5)),
                ('structure_preference', models.FloatField(default=0.5)),
                ('technical_depth', models.FloatField(default=0.5)),
                ('response_pacing', models.FloatField(default=0.5)),
                ('last_updated_at', models.DateTimeField(auto_now=True)),
                ('interaction_count', models.IntegerField(default=0)),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='interaction_profile', to='auth.user')),
            ],
            options={
                'db_table': 'interaction_profiles',
            },
        ),
        migrations.AddIndex(
            model_name='interactionprofile',
            index=models.Index(fields=['user'], name='interaction_user_idx'),
        ),
        migrations.AddIndex(
            model_name='interactionprofile',
            index=models.Index(fields=['session_id'], name='interaction_session_idx'),
        ),
    ]
