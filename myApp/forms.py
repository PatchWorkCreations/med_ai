# forms.py
from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, SetPasswordForm
from .models import Profile, BetaFeedback
import re

# forms.py
from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()

class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True})
    )

    def clean(self):
        email = (self.cleaned_data.get("username") or "").strip()
        password = (self.cleaned_data.get("password") or "")
        user_obj = User.objects.filter(email__iexact=email).only("username").first()
        login_name = user_obj.username if user_obj else None

        self.user_cache = (
            authenticate(self.request, username=login_name, password=password)
            if login_name else None
        )
        if self.user_cache is None:
            raise self.get_invalid_login_error()
        self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


# -----------------------
# Signup: keep usernames, but validate email uniqueness; save Profile.profession
# -----------------------
class CustomSignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name  = forms.CharField(max_length=150, required=True)
    # Optional field saved into Profile (NOT on User)
    profession = forms.CharField(max_length=100, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        # Note: do NOT include 'profession' here; it's not a field on auth.User
        fields = ["first_name", "last_name", "email", "username", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)  # UserCreationForm already sets hashed password
        user.email = self.cleaned_data["email"].strip().lower()
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name  = self.cleaned_data["last_name"].strip()
        if commit:
            user.save()
            Profile.objects.create(
                user=user,
                profession=self.cleaned_data.get("profession", "").strip()
            )
        return user


# -----------------------
# Beta Feedback (kept as-is, with small tidy)
# -----------------------
USE_CASE_CHOICES = [
    ("upload_summarize", "Upload file → Summarize"),
    ("multi_attachments", "Multiple attachments (staging tray)"),
    ("tone_selector", "Tone selector (Plain/Caregiver/Faith/Clinical/Bilingual)"),
    ("chat_qna", "Ask a question in the chat"),
    ("summary_modal", "Open ‘Full Summary’ modal"),
    ("search_sidebar", "Search summaries in sidebar"),
    ("new_chat_reset", "Start New Chat (resets context)"),
    ("drag_drop", "Drag & drop files into composer"),
    ("mic_dictation", "Mic dictation (speech to text)"),
    ("settings_update", "Update Settings (name/profession)"),
    ("sidebar_toggle", "Toggle sidebar on mobile"),
    ("loading_overlay", "Loading overlay/typing indicator"),
    ("error_handling", "Error state/failed reply handling"),
]
INPUT_TYPE_CHOICES = [
    ("dummy","Dummy text I wrote"),
    ("synthetic","Synthetic sample from app"),
    ("public","Public doc (no PHI)"),
    ("other","Other (no PHI)"),
]

class BetaFeedbackForm(forms.ModelForm):
    use_case_multi = forms.MultipleChoiceField(
        choices=USE_CASE_CHOICES,
        required=True,
        widget=forms.CheckboxSelectMultiple,
        label="What did you test today?"
    )

    class Meta:
        model = BetaFeedback
        fields = [
            "consent","role","email","device","browser",
            "input_type","ease","speed","accuracy","clarity","nps",
            "pros","cons","bugs","screenshot",
            "allow_contact","allow_anon",
        ]
        widgets = {
            "input_type": forms.Select(choices=INPUT_TYPE_CHOICES),
            "pros": forms.Textarea(attrs={"rows":3}),
            "cons": forms.Textarea(attrs={"rows":3}),
            "bugs": forms.Textarea(attrs={"rows":3}),
        }

    def clean(self):
        data = super().clean()
        if not data.get("consent"):
            raise forms.ValidationError("Consent is required (no PHI).")

        for f in ("ease","speed","accuracy","clarity"):
            v = data.get(f)
            if v is None or not (1 <= v <= 5):
                self.add_error(f, "Must be between 1 and 5.")

        nps = data.get("nps")
        if nps is None or not (0 <= nps <= 10):
            self.add_error("nps", "NPS must be between 0 and 10.")

        selected = data.get("use_case_multi", [])
        data["use_case"] = ", ".join(selected)
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.use_case = self.cleaned_data.get("use_case", "")
        if commit:
            obj.save()
        return obj


# -----------------------
# Password reset helpers (unchanged, but using get_user_model)
# -----------------------
class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        # normalize; keep success generic (no account enumeration)
        return self.cleaned_data["email"].lower().strip()

class OTPForm(forms.Form):
    email = forms.EmailField()
    code = forms.CharField(min_length=6, max_length=6)

class OTPSetPasswordForm(SetPasswordForm):
    """Same fields as SetPasswordForm: new_password1/new_password2"""
    pass


class DemoRequestForm(forms.Form):
    name = forms.CharField(max_length=120)
    email = forms.EmailField()
    company = forms.CharField(max_length=120, required=False)
    phone = forms.CharField(max_length=40, required=False)
    use_case = forms.ChoiceField(choices=USE_CASE_CHOICES, required=False)

    # Hidden/tracking fields (already in your template)
    website = forms.CharField(required=False, widget=forms.HiddenInput)
    utm_source = forms.CharField(required=False, widget=forms.HiddenInput)
    utm_medium = forms.CharField(required=False, widget=forms.HiddenInput)
    utm_campaign = forms.CharField(required=False, widget=forms.HiddenInput)
    utm_term = forms.CharField(required=False, widget=forms.HiddenInput)
    utm_content = forms.CharField(required=False, widget=forms.HiddenInput)



from django import forms
from .models import Org

class OrgCreateForm(forms.ModelForm):
    owner_email = forms.EmailField(help_text="Initial account owner email")
    class Meta:
        model = Org
        fields = ["name","slug","logo_url"]

class OrgSwitchForm(forms.Form):
    org = forms.ModelChoiceField(queryset=Org.objects.all())
