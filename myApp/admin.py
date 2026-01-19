# --- Users admin (replace your block with this) ---
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Exists, OuterRef
from django.contrib import messages

from .models import Profile, BetaFeedback, Subscription, Payment

User = get_user_model()

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fk_name = "user"
    extra = 0
    fields = (
        "display_name",
        "profession",
        "language",
        "signup_ip",
        "signup_country",
        "last_login_ip",
        "last_login_country",
    )
    readonly_fields = ("signup_ip", "signup_country", "last_login_ip", "last_login_country")

class BetaTesterFilter(admin.SimpleListFilter):
    title = "beta tester"
    parameter_name = "beta"
    def lookups(self, request, model_admin):
        return (("yes", "Has BetaFeedback"), ("no", "No BetaFeedback"))
    def queryset(self, request, qs):
        betas = BetaFeedback.objects.filter(email__iexact=OuterRef("email"))
        qs = qs.annotate(_has_beta=Exists(betas))
        if self.value() == "yes":
            return qs.filter(_has_beta=True)
        if self.value() == "no":
            return qs.filter(_has_beta=False)
        return qs

class HasProfileFilter(admin.SimpleListFilter):
    title = "has profile"
    parameter_name = "has_profile"
    def lookups(self, request, model_admin):
        return (("yes", "Yes"), ("no", "No"))
    def queryset(self, request, qs):
        if self.value() == "yes":
            return qs.filter(profile__isnull=False)
        if self.value() == "no":
            return qs.filter(profile__isnull=True)
        return qs

# Unregister the default registration before re-registering
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = (
        "username","email","first_name","last_name","is_staff",
        "date_joined","last_login",
        "profile_language","profile_signup_ip","profile_last_login_ip","profile_countries","is_beta_tester",
    )
    list_select_related = ("profile",)
    list_filter = ("is_staff","is_superuser","is_active", BetaTesterFilter, HasProfileFilter, ("date_joined", admin.DateFieldListFilter))
    search_fields = ("username","email","first_name","last_name","profile__display_name","profile__profession")
    ordering = ("-date_joined",)

    @admin.display(description="Lang")
    def profile_language(self, obj):
        return getattr(getattr(obj, "profile", None), "language", "—")

    @admin.display(description="Signup IP")
    def profile_signup_ip(self, obj):
        return getattr(getattr(obj, "profile", None), "signup_ip", "—")

    @admin.display(description="Last login IP")
    def profile_last_login_ip(self, obj):
        return getattr(getattr(obj, "profile", None), "last_login_ip", "—")

    @admin.display(description="Country")
    def profile_countries(self, obj):
        p = getattr(obj, "profile", None)
        if not p:
            return "—"
        parts = []
        if p.signup_country: parts.append(f"🆕 {p.signup_country}")
        if p.last_login_country: parts.append(f"🔑 {p.last_login_country}")
        return " / ".join(parts) or "—"

    @admin.display(description="Beta?", boolean=True)
    def is_beta_tester(self, obj):
        return BetaFeedback.objects.filter(email__iexact=obj.email).exists()

    actions = ["create_missing_profiles"]
    def create_missing_profiles(self, request, queryset):
        created = 0
        for u in queryset:
            Profile.objects.get_or_create(user=u)
            created += 1
        self.message_user(request, f"Ensured profiles for {created} user(s).", level=messages.SUCCESS)

admin.site.register(User, UserAdmin)

# Subscription and Payment admin
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'current_period_end', 'created_at')
    list_filter = ('plan', 'status', 'created_at')
    search_fields = ('user__username', 'user__email', 'paypal_subscription_id')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan_id', 'amount', 'currency', 'status', 'created_at', 'paid_at')
    list_filter = ('status', 'plan_id', 'created_at')
    search_fields = ('user__username', 'user__email', 'paypal_order_id', 'paypal_transaction_id')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
