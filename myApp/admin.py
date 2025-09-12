from django.contrib import admin
from .models import BetaFeedback

@admin.register(BetaFeedback)
class BetaFeedbackAdmin(admin.ModelAdmin):
    list_display = ("created_at","role","device","browser","nps","allow_contact","allow_anon")
    list_filter = ("role","device","input_type","allow_contact","allow_anon")
    search_fields = ("email","use_case","pros","cons","bugs")

# myApp/admin.py
from django.contrib import admin, messages
from .models import Org, OrgDomain, OrgMembership

@admin.register(Org)
class OrgAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    actions = ["activate_org"]

    def activate_org(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} org(s).", level=messages.SUCCESS)
