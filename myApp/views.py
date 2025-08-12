# myApp/views.py

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from django.contrib.auth.forms import UserCreationForm

from .models import MedicalSummary, Profile

# -------- Std libs
import os, io, json, base64, mimetypes, tempfile, traceback

# -------- Files / parsing
import fitz  # PyMuPDF
import docx
from PIL import Image

# -------- OpenAI
from openai import OpenAI
client = OpenAI()

# =============================
#         PROMPTS
# =============================
PROMPT_TEMPLATES = {
    "Plain": (
        "You are NeuroMed, a brilliant yet humble medical assistant. "
        "Speak with clarity, warmth, and intelligence—like a trusted doctor explaining things to a close friend. "
        "Avoid robotic phrasing and disclaimers. Be accurate but approachable."
    ),
    "Caregiver": (
        "You are NeuroMed, a comforting health companion. "
        "Speak gently, using Taglish warmth where helpful. "
        "Explain clearly, reassure kindly, and offer practical next steps."
    ),
    "Faith": (
        "You are NeuroMed, a faith-filled health companion. "
        "Provide clear medical explanations with hope and peace. "
        "When appropriate, close with a short Bible verse or brief prayer."
    ),
    "Clinical": (
        "You are NeuroMed, a professional-grade medical assistant for clinicians. "
        "Be concise, precise, and correct in medical terminology. No fluff."
    ),
    "Bilingual": (
        "You are NeuroMed, a warm Taglish-speaking medical guide. "
        "Use natural Tagalog-English to make explanations crystal clear."
    ),
}

VISION_FORMAT_PROMPT = (
    "\n\nFormat your findings like this:\n\n"
    "🧠 **Observed Structures**:\n"
    "- List key anatomical features and orientation.\n"
    "- Note symmetry/asymmetry, density patterns, artifacts.\n\n"
    "🔍 **Possible Findings**:\n"
    "- Describe abnormalities vs normal; suggest possible causes in a non-diagnostic, educational way.\n\n"
    "💡 **Explanation**:\n"
    "Explain warmly what this might mean for a concerned patient/family.\n\n"
    "🕊 **Next Steps**:\n"
    "- Suggest reasonable follow-up tests, referrals, or general health tips.\n"
)

# =============================
#      FILE TEXT EXTRACTORS
# =============================
def extract_text_from_pdf(file):
    pdf = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in pdf:
        text += page.get_text()
    return text.strip()

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

# =============================
#      IMAGE PREPROCESSING
# =============================
def preprocess_image_for_vision_api(image_path, resize_width=1024):
    with Image.open(image_path) as img:
        img = img.convert("L")  # grayscale
        if img.width > resize_width:
            w_percent = resize_width / float(img.width)
            h_size = int(float(img.height) * float(w_percent))
            img = img.resize((resize_width, h_size), Image.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        return base64.b64encode(buffer.getvalue()).decode()

# =============================
#  VISION INTERPRETATION (IMG)
# =============================
def extract_contextual_medical_insights_from_image(file_path: str, tone: str = "Plain") -> str:
    image_b64 = preprocess_image_for_vision_api(file_path)
    data_uri = f"data:image/png;base64,{image_b64}"
    system_prompt = PROMPT_TEMPLATES.get(tone, PROMPT_TEMPLATES["Plain"]) + VISION_FORMAT_PROMPT

    # First pass: interpret the actual image
    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.4,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please interpret this medical image directly and specifically."},
                    {"type": "image_url", "image_url": {"url": data_uri}}
                ]
            },
        ],
    )
    raw = resp.choices[0].message.content.strip()

    # Second pass: humanize/tone polish
    rewrite = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Rewrite warmly, clearly, and confidently—keep all details:\n\n{raw}"},
        ],
    )
    return rewrite.choices[0].message.content.strip()

# =============================
#  SUMMARIZE (PDF/DOCX/TXT/IMG)
# =============================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def summarize_medical_record(request):
    uploaded_file = request.FILES.get("file")
    tone = request.data.get("tone", "Plain")
    if not uploaded_file:
        return Response({"error": "No file provided."}, status=400)

    file_name = uploaded_file.name.lower()
    system_prompt = PROMPT_TEMPLATES.get(tone, PROMPT_TEMPLATES["Plain"])

    try:
        # ---------- Images
        if file_name.endswith((".jpg", ".jpeg", ".png", ".heic", ".webp")):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1]) as tmp:
                for chunk in uploaded_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            try:
                summary = extract_contextual_medical_insights_from_image(tmp_path, tone=tone)
            finally:
                os.remove(tmp_path)

            # Save to DB
            MedicalSummary.objects.create(
                user=request.user,
                uploaded_filename=uploaded_file.name,
                tone=tone,
                raw_text="(Image file)",
                summary=summary,
            )

            # Persist to session for chat context
            request.session["latest_summary"] = summary
            request.session["chat_history"] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"(Here’s the medical context from an image):\n{summary}"}
            ]
            request.session.modified = True
            return Response({"summary": summary})

        # ---------- Text docs
        elif file_name.endswith(".pdf"):
            raw_text = extract_text_from_pdf(uploaded_file)
        elif file_name.endswith(".docx"):
            raw_text = extract_text_from_docx(uploaded_file)
        elif file_name.endswith(".txt"):
            raw_text = uploaded_file.read().decode("utf-8")
        else:
            return Response({"error": "Unsupported file format."}, status=400)

        if not raw_text.strip():
            return Response({"error": "Document is empty or unreadable."}, status=400)

        # Summarize text docs
        completion = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.4,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Summarize clearly and kindly for a patient/caregiver:\n\n{raw_text}"},
            ],
        )
        raw_summary = completion.choices[0].message.content.strip()

        polish = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Polish the tone—warm, clear, confident:\n\n{raw_summary}"},
            ],
        )
        summary = polish.choices[0].message.content.strip()

        MedicalSummary.objects.create(
            user=request.user,
            uploaded_filename=uploaded_file.name,
            tone=tone,
            raw_text=raw_text,
            summary=summary,
        )

        request.session["latest_summary"] = summary
        request.session["chat_history"] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"(Here’s the medical context from a file):\n{summary}"}
        ]
        request.session.modified = True

        return Response({"summary": summary})

    except Exception as e:
        traceback.print_exc()
        return Response({"error": f"Failed to process file: {str(e)}"}, status=400)

# =============================
#     CHAT (TEXT + FILES)
# =============================
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def send_chat(request):
    """
    Unified chat endpoint:
    - Accepts multiple files via `files[]` (new UI) or a single `file` (backward compatible).
    - Images → vision interpretation.
    - PDFs/DOCX/TXT → extract + summarize.
    - If user sends only files → return combined file summaries.
    - If user also sends a question → answer using the combined context + session history.
    """
    tone = request.data.get("tone", "Plain")
    system_prompt = PROMPT_TEMPLATES.get(tone, PROMPT_TEMPLATES["Plain"])
    user_message = (request.data.get("message") or "").strip()

    # Session context (keep it light)
    summary_context = request.session.get("latest_summary", "")
    chat_history = request.session.get("chat_history", [{"role": "system", "content": system_prompt}])

    # --- Collect files (multi or single for backward-compat)
    files = request.FILES.getlist("files[]")
    if not files and "file" in request.FILES:
        files = [request.FILES["file"]]

    combined_sections = []
    # --- Process each file
    for f in files:
        fname, summary = summarize_single_file(f, tone=tone, system_prompt=system_prompt, user=request.user)
        combined_sections.append(f"### {fname}\n{summary}")

    combined_context = "\n\n".join(combined_sections).strip()

    # --- If files were provided and no user message, just return the combined summaries
    if files and not user_message:
        # Update session with the combined summaries as the latest context
        request.session["latest_summary"] = combined_context or summary_context
        # Keep a small rolling chat history with context planted
        request.session["chat_history"] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"(Here’s the latest medical context):\n{combined_context or summary_context}"}
        ]
        request.session.modified = True

        if combined_context:
            return JsonResponse({"reply": combined_context})
        else:
            return JsonResponse({"reply": "I couldn’t read any useful content from the attachments."}, status=400)

    # --- If no files and no message
    if not files and not user_message:
        return JsonResponse({"reply": "Hmm… I didn’t catch that. Can you try again?"})

    # --- Prepare context for question/answer
    # Plant the most recent context if not present
    if combined_context:
        # New attachment context takes precedence this turn
        chat_history = [{"role": "system", "content": system_prompt}]
        chat_history.append({"role": "user", "content": f"(Here’s the latest medical context):\n{combined_context}"})
        # Also keep it in session for subsequent turns
        request.session["latest_summary"] = combined_context
    else:
        # If no new files, ensure we have prior context planted at least once
        if summary_context and all("(Here’s the" not in m.get("content", "") for m in chat_history if m.get("role") == "user"):
            chat_history.append({"role": "user", "content": f"(Here’s the medical context):\n{summary_context}"})

    chat_history.append({"role": "user", "content": user_message})

    try:
        # First pass: grounded answer
        raw = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.6,
            messages=chat_history,
        ).choices[0].message.content.strip()

        # Second pass: tone polish
        reply = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Rewrite warmly, clearly, and confidently:\n\n{raw}"},
            ],
        ).choices[0].message.content.strip()

        # Save trimmed history
        chat_history.append({"role": "assistant", "content": reply})
        request.session["chat_history"] = chat_history[-10:]
        request.session.modified = True

        return JsonResponse({"reply": reply})
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"reply": "I’m having trouble responding right now. Let’s try again in a bit."}, status=500)

# =============================
#  SMART SUGGESTIONS / Q&A
# =============================
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def smart_suggestions(request):
    summary = request.data.get("summary", "") or request.session.get("latest_summary", "")
    tone = request.data.get("tone", "Plain")
    if not summary.strip():
        return JsonResponse({"suggestions": []})

    prompt = (
        "Based on the medical context below, suggest 3 thoughtful follow-up questions the user might ask next. "
        "Focus on proactive, useful questions a patient or caregiver might not think to ask.\n\n"
        f"{summary}"
    )

    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.6,
        messages=[
            {"role": "system", "content": PROMPT_TEMPLATES.get(tone, PROMPT_TEMPLATES["Plain"])},
            {"role": "user", "content": prompt},
        ],
    )
    lines = [l.strip("- ").strip() for l in resp.choices[0].message.content.split("\n") if l.strip()]
    return JsonResponse({"suggestions": [{"question": q} for q in lines[:3]]})

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def answer_question(request):
    question = request.data.get("question", "")
    summary = request.data.get("summary", "") or request.session.get("latest_summary", "")
    tone = request.data.get("tone", "Plain")
    if not question:
        return JsonResponse({"answer": "Could you repeat the question? I want to make sure I understand."})

    prompt = f"Context:\n{summary}\n\nAnswer clearly, warmly, and confidently:\nQ: {question}"
    raw = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.6,
        messages=[
            {"role": "system", "content": PROMPT_TEMPLATES.get(tone, PROMPT_TEMPLATES["Plain"])},
            {"role": "user", "content": prompt},
        ],
    ).choices[0].message.content.strip()

    polish = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        messages=[
            {"role": "system", "content": PROMPT_TEMPLATES.get(tone, PROMPT_TEMPLATES["Plain"])},
            {"role": "user", "content": f"Rewrite warmly, clearly, and confidently:\n\n{raw}"},
        ],
    ).choices[0].message.content.strip()

    return JsonResponse({"answer": polish})

# =============================
#      SESSION UTILITIES
# =============================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def clear_session(request):
    tone = request.session.get("tone", "Plain")
    system_prompt = PROMPT_TEMPLATES.get(tone, PROMPT_TEMPLATES["Plain"])
    request.session["chat_history"] = [{"role": "system", "content": system_prompt}]
    request.session["latest_summary"] = ""
    request.session.modified = True
    return Response({"status": "✅ New chat started!", "tone": tone})

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def reset_chat_session(request):
    # mirror of clear_session but AllowAny (if you expose this publicly)
    tone = request.session.get("tone", "Plain")
    system_prompt = PROMPT_TEMPLATES.get(tone, PROMPT_TEMPLATES["Plain"])
    request.session["chat_history"] = [{"role": "system", "content": system_prompt}]
    request.session["latest_summary"] = ""
    request.session.modified = True
    return JsonResponse({"message": "✅ New chat started fresh.", "tone": tone})

# =============================
#       BASIC PAGES / AUTH
# =============================
def landing_page(request):
    return render(request, "landing_page.html")

def about_page(request):
    return render(request, "about.html")

def speaking_view(request):
    return render(request, 'talking_ai/speaking.html')

from django.shortcuts import render, redirect
from .forms import CustomSignupForm

def signup_view(request):
    if request.method == "POST":
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("dashboard")
    else:
        form = CustomSignupForm()
    return render(request, "signup.html", {"form": form})


# =============================
#       DASHBOARD + SETTINGS
# =============================
from django.contrib.auth.decorators import login_required

@login_required(login_url='/login/')
def dashboard(request):
    summaries = MedicalSummary.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "dashboard.html", {"summaries": summaries})

@login_required
def get_user_settings(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return JsonResponse({
        "display_name": profile.display_name or request.user.first_name or request.user.username,
        "profession": profile.profession or "",
    })

@login_required
def update_user_settings(request):
    if request.method == "POST":
        data = json.loads(request.body)
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.display_name = data.get("display_name", profile.display_name)
        profile.profession = data.get("profession", profile.profession)
        profile.save()
        return JsonResponse({"status": "success"})
    return JsonResponse({"error": "Invalid request"}, status=400)


def summarize_text_block(raw_text: str, system_prompt: str) -> str:
    """Summarize then tone-polish a text block."""
    if not raw_text.strip():
        return "The document appears empty or unreadable."
    completion = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.4,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Summarize clearly and kindly for a patient/caregiver:\n\n{raw_text}"},
        ],
    )
    raw_summary = completion.choices[0].message.content.strip()

    polish = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Polish the tone—warm, clear, confident:\n\n{raw_summary}"},
        ],
    )
    return polish.choices[0].message.content.strip()


def summarize_single_file(file_obj, tone: str, system_prompt: str, user=None) -> tuple[str, str]:
    """
    Returns (filename, summary) for an uploaded file (image or doc).
    Saves to DB if user is authenticated.
    """
    fname = file_obj.name
    lower = fname.lower()

    # Images → vision
    if lower.endswith((".jpg", ".jpeg", ".png", ".heic", ".webp")):
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(lower)[1]) as tmp:
            for chunk in file_obj.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        try:
            summary = extract_contextual_medical_insights_from_image(tmp_path, tone=tone)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        if user and user.is_authenticated:
            MedicalSummary.objects.create(
                user=user,
                uploaded_filename=fname,
                tone=tone,
                raw_text="(Image file via chat)",
                summary=summary,
            )
        return fname, summary

    # Docs → extract + summarize
    if lower.endswith(".pdf"):
        raw_text = extract_text_from_pdf(file_obj)
    elif lower.endswith(".docx"):
        raw_text = extract_text_from_docx(file_obj)
    elif lower.endswith(".txt"):
        raw_text = file_obj.read().decode("utf-8", errors="ignore")
    else:
        return fname, "Unsupported file format."

    summary = summarize_text_block(raw_text, system_prompt)

    if user and user.is_authenticated:
        MedicalSummary.objects.create(
            user=user,
            uploaded_filename=fname,
            tone=tone,
            raw_text=raw_text,
            summary=summary,
        )
    return fname, summary


from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import BetaFeedbackForm

def beta_feedback(request):
    if request.method == "POST":
        form = BetaFeedbackForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Thanks! Your feedback was submitted.")
            return redirect("beta_thanks")
    else:
        form = BetaFeedbackForm()
    return render(request, "beta/feedback.html", {"form": form})

def beta_thanks(request):
    return render(request, "beta/thanks.html")


from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .forms import BetaFeedbackForm

@require_POST
def beta_feedback_api(request):
    """
    Accepts multipart FormData; returns JSON {success, id?, created_at?, errors?}
    """
    form = BetaFeedbackForm(request.POST, request.FILES)

    if form.is_valid():
        obj = form.save()
        return JsonResponse(
            {"success": True, "id": str(obj.id), "created_at": obj.created_at.isoformat()},
            status=201
        )

    # Flatten errors a bit for nicer toasts
    errors = {f: [str(e) for e in errs] for f, errs in form.errors.items()}
    return JsonResponse({"success": False, "errors": errors}, status=400)


from datetime import date
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect

class LegalView(TemplateView):
    """
    Renders the single-page 'Terms of Use & Privacy Policy' template.
    """
    template_name = "legal/terms_privacy.html"

    # Optional: pass an effective date from server-side
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["effective_date"] = date.today()  # or a fixed date, e.g., date(2025, 8, 11)
        return ctx


def terms_redirect(_request):
    # Django can't append fragments via reverse(), so use a raw redirect.
    return HttpResponseRedirect("/legal/#terms")


def privacy_redirect(_request):
    return HttpResponseRedirect("/legal/#privacy")



# views.py
import random
import string
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import SetPasswordForm
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone
from django import forms

User = get_user_model()

# ---------- Config ----------
OTP_TTL_SECONDS = 10 * 60          # 10 minutes
OTP_RESEND_SECONDS = 60            # 60s cooldown between resends
OTP_PREFIX = "pwreset:"
OTP_ATTEMPTS_PREFIX = "pwreset_attempts:"
OTP_RESEND_PREFIX = "pwreset_resend:"
DASHBOARD_URL = "/dashboard"       # change to reverse('dashboard') if you have a named route

def _otp_key(email): return f"{OTP_PREFIX}{email}"
def _otp_attempts_key(email): return f"{OTP_ATTEMPTS_PREFIX}{email}"
def _otp_resend_key(email): return f"{OTP_RESEND_PREFIX}{email}"

def _generate_code():
    return "".join(random.choices(string.digits, k=6))


# ---------- Forms (kept here to be drop-in) ----------
class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        # Normalize but don't reveal existence
        return self.cleaned_data["email"].lower().strip()


class OTPForm(forms.Form):
    email = forms.EmailField()
    code = forms.CharField(min_length=6, max_length=6)

    def clean_email(self):
        return self.cleaned_data["email"].lower().strip()

    def clean_code(self):
        return self.cleaned_data["code"].strip()


class OTPSetPasswordForm(SetPasswordForm):
    """Uses Django's password validators; fields: new_password1/new_password2"""
    pass


# ---------- Views ----------
# --- updated forgot_password view (drop-in replacement) ---
from django.utils import timezone
from django.core.cache import cache
from django.contrib import messages

def forgot_password(request):
    """
    Step 1: Ask for email, generate 6-digit OTP, store in cache, email it.
    We never reveal whether the email exists.
    """
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]  # already normalized in clean_email()
            code = _generate_code()

            # Save OTP + attempts in cache
            cache.set(_otp_key(email), {"code": code, "ts": timezone.now().isoformat()}, OTP_TTL_SECONDS)
            cache.set(_otp_attempts_key(email), 0, OTP_TTL_SECONDS)

            # Store email (and a masked display version) in session for continuity
            request.session["pwreset_email"] = email
            request.session["pwreset_email_masked"] = mask_email(email)
            request.session.set_expiry(15 * 60)
            request.session.modified = True

            # Send branded email (HTML + text)
            send_otp_email(email, code, ttl_minutes=OTP_TTL_SECONDS // 60)

            

            # Always generic to avoid account enumeration
            messages.success(request, "If the email exists, we’ve sent a 6-digit code. Please check your inbox.")
            return redirect("password_otp")
    else:
        form = ForgotPasswordForm()

    return render(request, "account/password_forgot.html", {"form": form})



def resend_otp(request):
    """
    Resend code with a server-side cooldown to prevent abuse.
    """
    if request.method != "POST":
        return redirect("password_otp")

    email = (request.POST.get("email") or "").lower().strip()
    if not email:
        messages.error(request, "Please enter your email to resend the code.")
        return redirect("password_otp")

    cooldown_key = _otp_resend_key(email)
    if cache.get(cooldown_key):
        messages.error(request, "Please wait a moment before requesting another code.")
        return redirect("password_otp")

    data = cache.get(_otp_key(email))
    if data is None:
        # Generate a fresh code if the previous expired
        code = _generate_code()
        cache.set(_otp_key(email), {"code": code, "ts": timezone.now().isoformat()}, OTP_TTL_SECONDS)
        cache.set(_otp_attempts_key(email), 0, OTP_TTL_SECONDS)
    else:
        # Reuse active code so user isn’t confused seeing multiple codes
        code = data["code"]

    subject = "Your NeuroMed AI password reset code"
    body = f"Your one-time code is: {code}\nThis code expires in 10 minutes."
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=True)

    cache.set(cooldown_key, True, OTP_RESEND_SECONDS)
    messages.success(request, "We’ve sent another code if the email exists. Please check your inbox.")
    return redirect("password_otp")

# views.py (replace your verify_otp with this version)

def verify_otp(request):
    if request.method == "POST":
        form = OTPForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            code = form.cleaned_data["code"]

            data = cache.get(_otp_key(email))
            attempts = cache.get(_otp_attempts_key(email), 0)

            if data is None:
                messages.error(request, "Code expired or invalid. Please request a new one.")
                return redirect("password_forgot")

            if attempts >= 5:
                messages.error(request, "Too many attempts. Please request a new code.")
                cache.delete(_otp_key(email)); cache.delete(_otp_attempts_key(email))
                return redirect("password_forgot")

            if code != data.get("code"):
                cache.set(_otp_attempts_key(email), attempts + 1, OTP_TTL_SECONDS)
                messages.error(request, "Incorrect code. Please try again.")
                return render(request, "account/password_otp.html", {"form": form})

            # OTP OK
            user = User.objects.filter(email__iexact=email).first()

            # Clear OTP now to prevent reuse
            cache.delete(_otp_key(email)); cache.delete(_otp_attempts_key(email))

            # Always remember the email (nice to prefill / debug)
            request.session["pwreset_email"] = email
            request.session.set_expiry(15 * 60)
            request.session.modified = True

            if user:
                request.session["pwreset_user_id"] = user.id
                request.session.set_expiry(15 * 60)
                request.session.modified = True
                return redirect("password_reset_otp")
            else:
                # Keep them on the OTP page with a generic message.
                # (Prevents “expired” confusion while avoiding account enumeration.)
                messages.success(request, "Code verified. If this email is registered, you can now set a new password.")
                return render(request, "account/password_otp.html", {"form": form})

    else:
        form = OTPForm()

    return render(request, "account/password_otp.html", {"form": form})


def reset_password(request):
    user_id = request.session.get("pwreset_user_id")
    user = User.objects.filter(id=user_id).first() if user_id else None

    if request.method == "POST":
        if not user:
            messages.error(request, "Your reset session expired (or the email isn’t registered). Please request a new code.")
            return redirect("password_forgot")

        form = OTPSetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            login(request, user)
            for k in ("pwreset_user_id", "pwreset_email"):
                request.session.pop(k, None)
            messages.success(request, "Password updated successfully.")
            return redirect(f"{DASHBOARD_URL}?changed=1")
    else:
        if not user:
            messages.error(request, "Your reset session expired (or the email isn’t registered). Please request a new code.")
            return redirect("password_forgot")
        form = OTPSetPasswordForm(user)

    return render(request, "account/password_reset_otp.html", {"form": form})

# --- helpers (top of views.py or near your other helpers) ---
from django.core.mail import EmailMultiAlternatives

def mask_email(addr: str) -> str:
    try:
        name, domain = addr.split("@", 1)
        nm = name[0] + "•" * max(len(name) - 2, 1) + name[-1]
        d0, *rest = domain.split(".")
        d0m = d0[0] + "•" * max(len(d0) - 2, 1) + d0[-1]
        return nm + "@" + ".".join([d0m] + rest)
    except Exception:
        return addr

def send_otp_email(email: str, code: str, ttl_minutes: int = 10):
    subject = "Your NeuroMed AI verification code"
    from_email = settings.DEFAULT_FROM_EMAIL
    to = [email]

    text_content = (
        f"Your NeuroMed AI verification code is: {code}\n"
        f"This code expires in {ttl_minutes} minutes.\n"
        "If you didn’t request this, ignore this email. "
        "For your security, never share this code."
    )

    html_content = f"""
    <div style="font-family:Inter,Segoe UI,Arial,sans-serif;max-width:520px;margin:0 auto;padding:24px;background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;">
      <div style="text-align:center;margin-bottom:8px;">
        <div style="font-size:18px;font-weight:700;color:#0f766e;">NeuroMed AI</div>
        <div style="font-size:12px;color:#6b7280;">Secure verification</div>
      </div>
      <p style="font-size:14px;color:#374151;margin:16px 0;">
        Here’s your one-time verification code. It expires in {ttl_minutes} minutes.
      </p>
      <div style="text-align:center;margin:20px 0;">
        <div style="display:inline-block;letter-spacing:6px;font-weight:700;font-size:28px;color:#111827;background:#f0fdfa;border:1px solid #99f6e4;border-radius:10px;padding:12px 18px;">
          {code}
        </div>
      </div>
      <p style="font-size:12px;color:#6b7280;margin:14px 0;">
        Didn’t request this? You can ignore this email. For your security, never share this code.
      </p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:16px 0;" />
      <p style="font-size:11px;color:#9ca3af;margin:0;">
        You’re receiving this because a password reset was requested on your account.
      </p>
    </div>
    """

    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send(fail_silently=True)  # don’t blow up the flow if SMTP hiccups


# views.py
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")  # or your LOGOUT_REDIRECT_URL
