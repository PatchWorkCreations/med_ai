from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile

class CustomSignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    # UI says optional → make it optional
    profession = forms.CharField(max_length=100, required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "username", "password1", "password2", "profession"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
            Profile.objects.create(
                user=user,
                profession=self.cleaned_data.get("profession", "")
            )
        return user

from django import forms
from .models import BetaFeedback

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
    # Not saved directly; we collapse this into the model's use_case string
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
            # "use_case" will be set in clean(); we won't expose the original text field
            "input_type",
            "ease","speed","accuracy","clarity","nps",
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

        # Ratings range checks
        for f in ("ease","speed","accuracy","clarity"):
            v = data.get(f)
            if v is None or not (1 <= v <= 5):
                self.add_error(f, "Must be between 1 and 5.")

        nps = data.get("nps")
        if nps is None or not (0 <= nps <= 10):
            self.add_error("nps", "NPS must be between 0 and 10.")

        # Collapse checklist → comma-separated string for model.use_case
        selected = data.get("use_case_multi", [])
        data["use_case"] = ", ".join(selected)  # fits your CharField
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        # Ensure collapsed value is written
        obj.use_case = self.cleaned_data.get("use_case", "")
        if commit:
            obj.save()
            # handle filefields m2m if ever added later
        return obj
