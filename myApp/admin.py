from django.contrib import admin
from .models import BetaFeedback

@admin.register(BetaFeedback)
class BetaFeedbackAdmin(admin.ModelAdmin):
    list_display = ("created_at","role","device","browser","nps","allow_contact","allow_anon")
    list_filter = ("role","device","input_type","allow_contact","allow_anon")
    search_fields = ("email","use_case","pros","cons","bugs")
