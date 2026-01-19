# product_views.py
from __future__ import annotations

import json, os, re, uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, dumps, loads
from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, NoReverseMatch
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.contrib.auth import get_user_model, login
from django.contrib import messages
from django.shortcuts import render, redirect
from django.shortcuts import render
from .forms import ForgotPasswordForm  
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
from .models import Org, OrgDomain, OrgMembership

User = get_user_model()

# Try to use your email-only login form if present; else default
try:
    from .forms import EmailAuthenticationForm as PortalLoginForm
except Exception:
    PortalLoginForm = None

User = get_user_model()

# ---------- Config ----------
OTP_TTL_SECONDS = 10 * 60          # 10 minutes
OTP_RESEND_SECONDS = 60            # 60s cooldown between resends
OTP_PREFIX = "pwreset:"
OTP_ATTEMPTS_PREFIX = "pwreset_attempts:"
OTP_RESEND_PREFIX = "pwreset_resend:"
DASHBOARD_URL = "/dashboard/new/"       # change to reverse('new_dashboard') if you have a named route

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



User = get_user_model()

from .models import (
    Org, OrgDomain, OrgMembership,
    Patient, Encounter,
)

User = get_user_model()

# -----------------------------
# Optional portal login form
# -----------------------------

def portal_password_forgot(request):
    """
    Step 1: Ask for email, generate OTP, email it.
    Template: account/_portal_password_forgot.html
    """
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()
            code = _generate_code()

            cache.set(_otp_key(email), {"code": code}, OTP_TTL_SECONDS)
            cache.set(_otp_attempts_key(email), 0, OTP_TTL_SECONDS)

            request.session["pwreset_email"] = email
            request.session["pwreset_email_masked"] = mask_email(email)
            request.session.set_expiry(15 * 60)
            request.session.modified = True

            send_otp_email(email, code, ttl_minutes=OTP_TTL_SECONDS // 60)
            messages.success(request, "If the email exists, we’ve sent a 6-digit code.")
            # URL name must match urls.py: name="portal_password_otp"
            return redirect("portal_password_otp")
    else:
        form = ForgotPasswordForm()

    return render(request, "account/_portal_password_forgot.html", {"form": form})


def portal_resend_otp(request):
    """
    Resend code with cooldown.
    """
    if request.method != "POST":
        # URL name must match urls.py
        return redirect("portal_password_otp")

    email = (request.POST.get("email") or "").lower().strip()
    if not email:
        messages.error(request, "Please enter your email to resend the code.")
        return redirect("portal_password_otp")

    cooldown_key = _otp_resend_key(email)
    if cache.get(cooldown_key):
        messages.error(request, "Please wait a moment before requesting another code.")
        return redirect("portal_password_otp")

    data = cache.get(_otp_key(email))
    if data is None:
        code = _generate_code()
        cache.set(_otp_key(email), {"code": code}, OTP_TTL_SECONDS)
        cache.set(_otp_attempts_key(email), 0, OTP_TTL_SECONDS)
    else:
        code = data["code"]

    send_otp_email(email, code, ttl_minutes=OTP_TTL_SECONDS // 60)
    cache.set(cooldown_key, True, 60)  # 60s cooldown

    messages.success(request, "We’ve sent another code if the email exists. Please check your inbox.")
    return redirect("portal_password_otp")


def portal_verify_otp(request):
    """
    Step 2: Verify code.
    Template: account/_portal_password_otp.html
    """
    if request.method == "POST":
        form = OTPForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()
            code = form.cleaned_data["code"].strip()

            data = cache.get(_otp_key(email))
            attempts = cache.get(_otp_attempts_key(email), 0)

            if data is None:
                messages.error(request, "Code expired or invalid. Please request a new one.")
                # URL name must match urls.py: name="portal_password_forgot"
                return redirect("portal_password_forgot")

            if attempts >= 5:
                messages.error(request, "Too many attempts. Please request a new code.")
                cache.delete(_otp_key(email)); cache.delete(_otp_attempts_key(email))
                return redirect("portal_password_forgot")

            if code != data.get("code"):
                cache.set(_otp_attempts_key(email), attempts + 1, OTP_TTL_SECONDS)
                messages.error(request, "Incorrect code. Please try again.")
                return render(request, "account/_portal_password_otp.html", {"form": form})

            # OTP OK
            user = User.objects.filter(email__iexact=email).first()

            cache.delete(_otp_key(email)); cache.delete(_otp_attempts_key(email))
            request.session["pwreset_email"] = email
            request.session.set_expiry(15 * 60)
            request.session.modified = True

            if user:
                request.session["pwreset_user_id"] = user.id
                request.session.set_expiry(15 * 60)
                request.session.modified = True
                # URL name must match urls.py: name="portal_password_reset_otp"
                return redirect("portal_password_reset_otp")
            else:
                messages.success(request, "Code verified. If this email is registered, you can now set a new password.")
                return render(request, "account/_portal_password_otp.html", {"form": form})
    else:
        form = OTPForm()

    return render(request, "account/_portal_password_otp.html", {"form": form})


def portal_reset_password(request):
    """
    Step 3: Set a new password.
    Template: account/_portal_password_reset_otp.html
    """
    user_id = request.session.get("pwreset_user_id")
    user = User.objects.filter(id=user_id).first() if user_id else None

    if request.method == "POST":
        if not user:
            messages.error(request, "Your reset session expired (or the email isn’t registered). Please request a new code.")
            return redirect("portal_password_forgot")

        form = OTPSetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            login(request, user)
            for k in ("pwreset_user_id", "pwreset_email"):
                request.session.pop(k, None)
            messages.success(request, "Password updated successfully.")
            return redirect("portal_dashboard")
    else:
        if not user:
            messages.error(request, "Your reset session expired (or the email isn’t registered). Please request a new code.")
            return redirect("portal_password_forgot")
        form = OTPSetPasswordForm(user)

    return render(request, "account/_portal_password_reset_otp.html", {"form": form})

# -----------------------------
# Product mockup & demo dashboard
# -----------------------------
def product_mockup(request):
    """Render the static NeuroMed Aira dashboard mockup."""
    return render(request, "products/mockup.html")

# --- Demo Dashboard (shell + per-section include) ---
SECTION_MAP = {
    "clinical":  "dashboard/sections/clinical.html",
    "frontdesk": "dashboard/sections/frontdesk.html",
    "rcm":       "dashboard/sections/rcm.html",
    "admin":     "dashboard/sections/admin.html",
}

SCENARIO_FIXTURES = {
    "Knee MRI (Outpatient)": (
        "Visit reason: chronic right knee pain after basketball.\n"
        "History: 6 months, intermittent swelling; worse with stairs and squats.\n"
        "Imaging: MRI suggests medial meniscus tear; mild effusion, no fracture.\n"
        "Plan: ortho referral, RICE, NSAIDs PRN, PT strengthening; discuss arthroscopy if conservative care fails."
    ),
    "Chest pain (ED)": (
        "48M with substernal pressure, 30 mins, diaphoresis. Risk: HTN, smoker.\n"
        "ECG non-diagnostic; serial troponins pending. HEART score moderate.\n"
        "Plan: ASA given, nitro PRN, observation + stress testing vs CTA based on enzymes."
    ),
    "Diabetes follow-up (Primary Care)": (
        "T2DM; A1c 8.2% (↑). BP 134/82. BMI 31.\n"
        "Plan: reinforce lifestyle; start GLP-1 RA; labs: CMP, lipids; foot exam, retinal screen referral."
    ),
    "GI procedure (Endoscopy)": (
        "Indication: chronic GERD + anemia. EGD planned with biopsy.\n"
        "Consent obtained; NPO verified; anticoagulation held per protocol."
    ),
    "Spanish consult (Pediatrics)": (
        "Consulta pediátrica por tos y fiebre baja. Examen pulmonar claro.\n"
        "Plan: líquidos, antipirético según peso, señales de alarma explicadas a la familia."
    ),
}

FD_COLUMNS = ["New", "Screening", "Ready", "Scheduled"]

def demo_dashboard(request, section="clinical"):
    sec = (section or "clinical").lower()
    section_template = SECTION_MAP.get(sec, SECTION_MAP["clinical"])

    brand_name = request.GET.get("brand", "NeuroMed Aira")
    scenario   = request.GET.get("scenario", "Knee MRI (Outpatient)")
    language   = request.GET.get("lang", "en-US")

    draft_summary = request.session.get("latest_summary", "").strip()
    if not draft_summary:
        draft_summary = SCENARIO_FIXTURES.get(scenario, "")

    ctx = {
        "active_section": sec,
        "section_template": section_template,
        "brand_name": brand_name,
        "scenario": scenario,
        "language": language,
        "draft_summary": draft_summary,
        "fd_columns": FD_COLUMNS,
    }
    return render(request, "dashboard/base_dashboard.html", ctx)


# -----------------------------
# Portal (tenant) views
# -----------------------------
def portal_home(request):
    if request.user.is_authenticated:
        return redirect("portal_dashboard")
    return redirect("portal_login")

class OrgLockedLoginView(DjangoLoginView):
    # Use your portal template
    template_name = "account/portal_login.html"
    if PortalLoginForm:
        authentication_form = PortalLoginForm

    def form_valid(self, form):
        resp = super().form_valid(form)
        org = getattr(self.request, "org", None)
        if not org:
            messages.error(self.request, "This portal is not configured for an organization.")
            logout(self.request)
            return redirect("portal_login")

        is_member = OrgMembership.objects.filter(
            user=self.request.user, org=org, is_active=True
        ).exists()
        if not is_member:
            logout(self.request)
            messages.error(self.request, "You don’t have access to this organization.")
            return redirect("portal_login")
        return resp

    def get_success_url(self):
        return "/portal/dashboard/"

def portal_logout(request):
    logout(request)
    return redirect("portal_login")


@login_required(login_url="/portal/login/")
@ensure_csrf_cookie
def portal_dashboard(request):
    org = getattr(request, "org", None)
    active_section = request.GET.get("section") or "admin"

    # --- topline stats (scoped to org when present) ---
    today = timezone.localdate()
    E = getattr(Encounter, "all_objects", Encounter.objects)
    P = Patient.objects
    try:
        base_e = E.filter(org=org) if org else E.all()
        base_p = P.filter(org=org) if org else P.all()
        encounters_today = base_e.filter(created_at__date=today).count()
        patients_total   = base_p.count()
        open_triage      = base_e.filter(status="new").count()
        ready            = base_e.filter(status="ready").count()
        scheduled        = base_e.filter(status="scheduled").count()
    except Exception:
        encounters_today = patients_total = open_triage = ready = scheduled = 0

    stats = {
        "encounters_today": encounters_today,
        "patients_total": patients_total,
        "open_triage": open_triage,
        "ready": ready,
        "scheduled": scheduled,
        "accuracy_rate": 98.7,
        "avg_response_s": 2.3,
    }

    staff_links = {
        "Triage":      request.build_absolute_uri(reverse("app_triage")),
        "Front Desk":  request.build_absolute_uri(reverse("app_frontdesk")),
        "Clinical":    request.build_absolute_uri(reverse("app_clinical")),
        "Diagnostics": request.build_absolute_uri(reverse("app_diagnostics")),
        "Scribe":      request.build_absolute_uri(reverse("app_scribe")),
        "Coding":      request.build_absolute_uri(reverse("app_coding")),
        "Care":        request.build_absolute_uri(reverse("app_care")),
    }

    # -------- Front Desk board (REAL data) --------
    columns = [
        {"label": "New",       "key": "new"},
        {"label": "Screening", "key": "screening"},
        {"label": "Ready",     "key": "ready"},
        {"label": "Scheduled", "key": "scheduled"},
    ]
    groups = {c["key"]: [] for c in columns}

    cutoff = timezone.now() - timedelta(days=14)
    qs = (E.select_related("patient")
            .filter(created_at__gte=cutoff)
            .order_by("-created_at"))
    if org:
        qs = qs.filter(org=org)

    def _safe_json(text, fallback=None):
        try:
            return json.loads(text)
        except Exception:
            return fallback or {}

    def _payload(enc):
        try:
            return enc.summary if isinstance(enc.summary, dict) else json.loads(enc.summary or "{}")
        except Exception:
            return {}

    def _reason(enc):
        if enc.reason:
            return enc.reason
        p = _payload(enc)
        return (p.get("triage", {}).get("one_sentence")
                or p.get("fields", {}).get("complaint")
                or "Patient-reported symptoms")

    def _insurer(enc):
        if enc.patient_id and getattr(enc.patient, "insurer", None):
            return enc.patient.insurer
        return _payload(enc).get("patient", {}).get("insurer") or "Self-pay"

    def _name(enc):
        # If a Patient is linked, build a name from first/last as a safe fallback
        if enc.patient_id and getattr(enc, "patient", None):
            first = (getattr(enc.patient, "first_name", "") or "").strip()
            last  = (getattr(enc.patient, "last_name", "") or "").strip()
            combined = (first + " " + last).strip()
            return (
                getattr(enc.patient, "display_name", None)   # if your model defines it
                or getattr(enc.patient, "full_name", None)   # if you added a property
                or combined
                or "Anonymous"
            )

        # If no Patient object is linked yet, use the summary payload
        p = (_payload(enc).get("patient") or {})
        fl = ((p.get("first_name", "") or "") + " " + (p.get("last_name", "") or "")).strip()
        return p.get("full_name") or fl or "Anonymous"


    for enc in qs:
        key = (enc.status or "new").lower()
        if key not in groups:
            key = "new"
        groups[key].append({
            "id": enc.id,
            "name": _name(enc),
            "reason": _reason(enc),
            "insurer": _insurer(enc),
            "priority": (enc.priority or "medium").lower(),
            "created_at": enc.created_at,
        })

    frontdesk_board = [
        {"label": c["label"], "key": c["key"], "items": groups[c["key"]]}
        for c in columns
    ]

    ctx = {
        "active_section": active_section,
        "stats": stats,
        "staff_links": staff_links,
        "frontdesk_board": frontdesk_board,
    }
    return render(request, "dashboard/base_dashboard.html", ctx)


# -----------------------------
# Staff PWA shells (/app/*)
# -----------------------------
@login_required(login_url="/portal/login/")
def app_triage(request):        return render(request, "apps/triage.html")

@login_required(login_url="/portal/login/")
def app_frontdesk(request):     return render(request, "apps/frontdesk.html")

@login_required(login_url="/portal/login/")
def app_clinical(request):      return render(request, "apps/clinical.html")

@login_required(login_url="/portal/login/")
def app_diagnostics(request):   return render(request, "apps/diagnostics.html")

@login_required(login_url="/portal/login/")
def app_scribe(request):        return render(request, "apps/scribe.html")

@login_required(login_url="/portal/login/")
def app_coding(request):        return render(request, "apps/coding.html")

@login_required(login_url="/portal/login/")
def app_care(request):          return render(request, "apps/care.html")


# -----------------------------
# Kiosk (tokenized, no login)
# -----------------------------
_DEVICE_SALT = "nm-kiosk-device-v1"

def _make_device_token(org: Org, app: str, days=90) -> str:
    """Create a signed, opaque token containing {'org': <slug>, 'app': <name>}."""
    payload = {"org": org.slug, "app": app}
    return dumps(payload, salt=_DEVICE_SALT, compress=True)

def _read_device_token(token: str, max_age_days=180):
    try:
        return loads(token, salt=_DEVICE_SALT, max_age=max_age_days * 86400)
    except (BadSignature, SignatureExpired):
        return None

def _get_device_from_request(request):
    """
    Reads the kiosk device token from ?t=, cookie, or header.
    If request.org is missing and token is valid, attach it.
    Returns dict like {"org": "<slug>", "app": "intake"} or None.
    """
    token = (
        request.GET.get("t")
        or request.COOKIES.get("device_token")
        or request.headers.get("X-Device-Token")
    )
    if not token:
        return None

    data = _read_device_token(token)
    if not data:
        return None

    # Bind org from token if middleware didn't do it
    if not getattr(request, "org", None):
        try:
            request.org = Org.objects.get(slug=data.get("org"))
        except Org.DoesNotExist:
            return None

    # Safety: token org must match bound org
    if data.get("org") != request.org.slug:
        return None

    return data

def _bind_org_from_device_token(request):
    """
    Convenience: ensure request.org is set using the device token if needed.
    Returns org or None.
    """
    if getattr(request, "org", None):
        return request.org
    device = _get_device_from_request(request)
    return getattr(request, "org", None)

def kiosk_intake(request):
    t = request.GET.get("t")
    device = _get_device_from_request(request)

    if device:
        resp = render(request, "kiosk/intake.html", {"device": device})
        if t:
            resp.set_cookie("device_token", t, samesite="Lax", max_age=180 * 86400, secure=not settings.DEBUG)
        return resp

    if t:
        decoded = _read_device_token(t)
        if not decoded:
            return render(request, "kiosk/token_required.html", status=403)
        resp = render(request, "kiosk/intake.html", {"device": decoded})
        resp.set_cookie("device_token", t, samesite="Lax", max_age=180 * 86400, secure=not settings.DEBUG)
        return resp

    return render(request, "kiosk/token_required.html", status=403)

def kiosk_consent(request):
    t = request.GET.get("t")
    device = _get_device_from_request(request)

    if device:
        resp = render(request, "kiosk/consent.html", {"device": device})
        if t:
            resp.set_cookie("device_token", t, samesite="Lax", max_age=180 * 86400, secure=not settings.DEBUG)
        return resp

    if t:
        decoded = _read_device_token(t)
        if not decoded:
            return render(request, "kiosk/token_required.html", status=403)
        resp = render(request, "kiosk/consent.html", {"device": decoded})
        resp.set_cookie("device_token", t, samesite="Lax", max_age=180 * 86400, secure=not settings.DEBUG)
        return resp

    return render(request, "kiosk/token_required.html", status=403)


# -----------------------------
# Ops: Launch links & device control
# -----------------------------
def _primary_domain(org: Org) -> Optional[str]:
    dom = org.domains.filter(is_primary=True).first()
    return dom.domain if dom else None

def _portal_login_url_for(org: Org) -> str:
    domain = _primary_domain(org) or "neuromedai.org"
    return f"https://{domain}/portal/login/"

def _email_credentials(to_email: str, org: Org, password: Optional[str]):
    try:
        subject = f"Your NeuroMed Aira Portal Access – {org.name}"
        login_url = _portal_login_url_for(org)
        if password:
            text = (
                f"Welcome to {org.name} on NeuroMed Aira.\n\n"
                f"Portal: {login_url}\n"
                f"Email: {to_email}\n"
                f"Temporary Password: {password}\n\n"
                "For security, please sign in and change your password.\n"
            )
        else:
            text = (
                f"Your NeuroMed Aira portal is ready for {org.name}.\n\n"
                f"Portal: {login_url}\n"
                f"Email: {to_email}\n\n"
                "If you need a password reset, reply to this email."
            )
        send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=True)
    except Exception:
        pass

def _org_from_request(request) -> Org | None:
    org = getattr(request, "org", None)
    if org:
        return org
    host = request.get_host().split(":")[0]
    # Ensure OrgDomain has related_name="domains" for this to work:
    return Org.objects.filter(domains__domain__iexact=host).first() or Org.objects.first()

@staff_member_required
def launch_links(request):
    org = _org_from_request(request)
    if not org:
        messages.error(request, "No organizations exist yet.")
        return redirect("/")

    staff_links = {
        "Triage":      request.build_absolute_uri("/app/triage"),
        "Front Desk":  request.build_absolute_uri("/app/frontdesk"),
        "Clinical":    request.build_absolute_uri("/app/clinical"),
        "Diagnostics": request.build_absolute_uri("/app/diagnostics"),
        "Scribe":      request.build_absolute_uri("/app/scribe"),
        "Coding":      request.build_absolute_uri("/app/coding"),
        "Care":        request.build_absolute_uri("/app/care"),
    }
    return render(request, "admin/launch_links.html", {"org": org, "staff_links": staff_links})

@staff_member_required
def launch_links_new(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    org = _org_from_request(request)
    if not org:
        return JsonResponse({"ok": False, "error": "no org bound"}, status=400)

    app = request.POST.get("app") or "intake"  # "intake" | "consent"
    token = _make_device_token(org, app)
    url = request.build_absolute_uri(f"/kiosk/{app}?t={token}")
    return JsonResponse({"ok": True, "url": url, "token": token})

@staff_member_required
def launch_device_revoke(request, token_id: str):
    messages.success(request, f"Device {escape(token_id)} revoked (stateless tokens demo).")
    return redirect("launch_links")


# -----------------------------
# Shared helpers (JSON & fields)
# -----------------------------
def _safe_json(text, fallback=None):
    try:
        return json.loads(text)
    except Exception:
        return fallback or {}

def _merge_fields_generic(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prefer existing non-empty values; for lists, union with de-dupe.
    """
    out = dict(existing or {})
    for k, v in (new or {}).items():
        if v in (None, "", [], {}):
            continue
        if isinstance(v, list):
            cur = out.get(k) or []
            out[k] = list(dict.fromkeys([*cur, *v]))
        else:
            if not out.get(k):
                out[k] = v
    return out

def _extract_fields_heuristic(message: str) -> Dict[str, Any]:
    msg = (message or "").strip()
    low = msg.lower()

    duration = None
    m = re.search(r"\b(\d+\s*(?:hour|day|week|month|year)s?)\b", low)
    if m:
        duration = m.group(1)
    if not duration:
        for kw in ["today", "yesterday", "last night", "this morning", "this week"]:
            if kw in low:
                duration = kw
                break

    severity = None
    for word in ["mild", "moderate", "severe"]:
        if re.search(rf"\b{word}\b", low):
            severity = word
            break
    if not severity:
        if re.search(r"\b([0-9]|10)\/10\b", low):
            severity = re.search(r"\b([0-9]|10)\/10\b", low).group(0)

    location = None
    for part in ["knee", "back", "chest", "head", "ankle", "shoulder", "abdomen", "stomach", "throat", "ear", "eye", "neck", "hip", "wrist", "elbow", "lower back"]:
        if re.search(rf"\b{part}\b", low):
            side = ""
            for s in ["right", "left", "lower", "upper", "mid", "central"]:
                if re.search(rf"\b{s}\b", low):
                    side = s + " "
                    break
            location = (side + part).strip()
            break

    complaint = None
    if any(k in low for k in ["pain", "swelling", "fever", "cough", "rash", "injury", "headache", "nausea", "vomit", "dizzy"]):
        complaint = " ".join(msg.split()[:12])

        # red flags demo set
    # red flags demo set (positive cues)
    red_flags = []
    for key, label in [
        ("chest pain", "chest pain"),
        ("shortness of breath", "shortness of breath"),
        ("trouble breathing", "shortness of breath"),
        ("numb", "numbness/weakness"),
        ("weak", "numbness/weakness"),
        ("faint", "fainting"),
        ("vision loss", "vision loss"),
        ("severe headache", "severe headache"),
        ("bleeding", "severe bleeding"),
        ("allergy", "anaphylaxis"),
        ("anaphylaxis", "anaphylaxis"),
    ]:
        if key in low:
            red_flags.append(label)

    # negative intent → explicitly say "none" so _next_slot() advances
    if not red_flags:
        neg_markers = [
            "none", "nope", "nah", "nothing", "not really",
            "no red flags", "no danger", "no emergency"
        ]
        if any(kw in low for kw in neg_markers):
            red_flags = ["none"]



    next_questions = []
    if not duration: next_questions.append("When did this start?")
    if not severity: next_questions.append("How severe is it (mild, moderate, or severe)?")
    if not location: next_questions.append("Where exactly is it located?")
    if not next_questions:
        next_questions = ["What makes it better or worse?"]

    out = {
        "complaint": complaint,
        "duration": duration,
        "severity": severity,
        "location": location,
        "red_flags": red_flags,
        "next_questions": next_questions[:2],
    }
    return {k: v for k, v in out.items() if v not in (None, "", [])}

def _default_actor_for_org(org) -> User | None:
    mem = OrgMembership.objects.filter(org=org, is_active=True).select_related("user").first()
    return mem.user if mem else User.objects.filter(is_superuser=True).first() or User.objects.first()

def _split_name(full_name: str):
    if not full_name:
        return ("", "")
    parts = str(full_name).strip().split()
    if len(parts) == 1:
        return (parts[0], "")
    return (" ".join(parts[:-1]), parts[-1])

def _upsert_patient(org, p: dict):
    first = p.get("first_name")
    last  = p.get("last_name")
    full  = p.get("full_name")
    if full and not (first or last):
        first, last = _split_name(full)

    phone = (p.get("phone") or "").strip()
    email = (p.get("email") or "").strip().lower()
    dob   = p.get("dob") or None

    q = Q(org=org)
    if phone:
        q &= Q(phone__iexact=phone)
    if email:
        q |= Q(org=org, email__iexact=email)

    match = Patient.objects.filter(q).order_by("-id").first() if (phone or email) else None
    if match:
        changed = False
        if first and match.first_name != first: match.first_name, changed = first, True
        if last  and match.last_name  != last:  match.last_name,  changed = last, True
        if phone and (match.phone or "").lower() != phone.lower(): match.phone, changed = phone, True
        if email and (match.email or "").lower() != email.lower(): match.email, changed = email, True
        if dob   and not getattr(match, "dob", None): match.dob, changed = dob, True
        insurer   = p.get("insurer") or p.get("insurance")
        policy_id = p.get("policy_id")
        if insurer and getattr(match, "insurer", None) != insurer:
            setattr(match, "insurer", insurer); changed = True
        if policy_id and getattr(match, "policy_id", None) != policy_id:
            setattr(match, "policy_id", policy_id); changed = True
        if changed: match.save(update_fields=None)
        return match

    kwargs = dict(org=org, first_name=first or "", last_name=last or "")
    if phone: kwargs["phone"] = phone
    if email: kwargs["email"] = email
    if dob:   kwargs["dob"]   = dob
    insurer   = p.get("insurer") or p.get("insurance")
    policy_id = p.get("policy_id")
    if insurer:   kwargs["insurer"]   = insurer
    if policy_id: kwargs["policy_id"] = policy_id
    return Patient.objects.create(**kwargs)


# -----------------------------
# Uploads
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def api_v1_upload(request):
    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"error": "file missing"}, status=400)

    org = getattr(request, "org", None)
    base = Path(settings.MEDIA_ROOT) / "org_uploads" / (org.slug if org else "unknown")
    base.mkdir(parents=True, exist_ok=True)
    ext = Path(f.name).suffix or ".bin"
    dest = base / f"{uuid.uuid4().hex}{ext}"
    with dest.open("wb") as out:
        for chunk in f.chunks():
            out.write(chunk)

    return JsonResponse({"ok": True, "upload_token": dest.name})


# -----------------------------
# Encounters: fetch & move
# -----------------------------
@require_http_methods(["GET"])
def api_v1_encounter_get(request, pk: int):
    _bind_org_from_device_token(request)
    org = getattr(request, "org", None)

    E = getattr(Encounter, "all_objects", Encounter.objects)
    try:
        enc = E.get(pk=pk, org=org) if org else E.get(pk=pk)
    except Encounter.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    data = {
        "id": enc.id,
        "org": getattr(enc.org, "slug", None),
        "patient": enc.patient.id if enc.patient_id else None,
        "reason": enc.reason,
        "status": enc.status,
        "priority": enc.priority,
        "summary": _safe_json(enc.summary or "{}", {}),
        "icd": getattr(enc, "icd", None),
        "cpt": getattr(enc, "cpt", None),
        "denials": getattr(enc, "denials", None),
        "created_at": enc.created_at.isoformat(),
    }
    return JsonResponse(data)

@csrf_exempt
@require_http_methods(["POST"])
def api_v1_encounter_move(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad json"}, status=400)

    enc_id = body.get("id")
    status = (body.get("status") or body.get("to") or "").strip().lower()
    if not enc_id or status not in {"new","screening","ready","scheduled"}:
        return JsonResponse({"error": "bad params"}, status=400)

    org = getattr(request, "org", None)
    E = getattr(Encounter, "all_objects", Encounter.objects)
    try:
        enc = E.get(pk=enc_id, org=org) if org else E.get(pk=enc_id)
    except Encounter.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    enc.status = status
    enc.save(update_fields=["status"])
    return JsonResponse({"ok": True, "id": enc.id, "status": enc.status})


# -----------------------------
# TRIAGE (turn-by-turn)
# -----------------------------
try:
    # Prefer your centralized OpenAI client if you have it
    from myApp.ai import client, get_system_prompt  # adjust path if needed
except Exception:
    from openai import OpenAI
    client = OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", None))

    def get_system_prompt(tone: str = "PlainClinical"):
        return (
            "You are a concise, safety-aware clinical assistant. "
            "Be clear, neutral, and avoid firm diagnosis. "
            "Ask focused questions to collect clinical history."
        )

OPENAI_TRIAGE_MODEL = getattr(settings, "OPENAI_TRIAGE_MODEL", "gpt-4o-mini")
OPENAI_BRIEF_MODEL  = getattr(settings, "OPENAI_BRIEF_MODEL",  "gpt-4o-mini")
OPENAI_VISION_MODEL = getattr(settings, "OPENAI_VISION_MODEL", "gpt-4o")

TRIAGE_FORMAT_PROMPT = """
Return STRICT JSON with keys:
- "assistant": string
- "fields": object with optional keys: complaint, duration, severity, location, red_flags[], next_questions[]
No extra text; only JSON.
"""

def _merge_fields_triage(base: dict, new: dict) -> dict:
    """
    Merge triage fields:
    - prefer existing non-empty scalars, otherwise take new
    - for lists, union with original order preserved
    """
    base = dict(base or {})
    new  = dict(new or {})
    out  = dict(base)

    def _is_empty(v):
        return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, (list, tuple, set)) and len(v) == 0)

    for k, v in new.items():
        if isinstance(v, list):
            existing = out.get(k) or []
            combined = list(dict.fromkeys([*existing, *v]))
            out[k] = combined
        else:
            if _is_empty(out.get(k)) and not _is_empty(v):
                out[k] = v
    return out

def _normalize_negatives(fields: dict, message: str) -> dict:
    """If user denies danger symptoms (e.g., 'none'), set red_flags=['none']."""
    out = dict(fields or {})
    low = (message or "").lower()
    rf = out.get("red_flags")
    rf_list = rf if isinstance(rf, list) else ([rf] if rf else [])
    if not rf_list:
        neg_markers = [
            "none", "nope", "nah", "nothing", "not really",
            "no red flags", "no danger", "no emergency"
        ]
        if any(kw in low for kw in neg_markers):
            out["red_flags"] = ["none"]
    return out


def _llm_triage_turn(message: str, history: Optional[List[Dict[str, str]]] = None, tone: str = "PlainClinical"):
    history = history or []
    default_reply = "Thanks—how long has this been going on, and is the pain mild, moderate, or severe?"
    sys_prompt = get_system_prompt(tone) + "\n" + TRIAGE_FORMAT_PROMPT

    try:
        msgs = [{"role": "system", "content": sys_prompt}]
        for h in history[-10:]:
            role = "assistant" if h.get("role") == "assistant" else "user"
            msgs.append({"role": role, "content": h.get("content", "")})
        if message:
            msgs.append({"role": "user", "content": message})

        resp = client.chat.completions.create(
            model=OPENAI_TRIAGE_MODEL,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=msgs,
        )
        data = _safe_json(resp.choices[0].message.content, {})
        assistant = (data.get("assistant") or default_reply).strip()

        # Merge LLM fields with heuristic backstop
        fields = data.get("fields") or {}
        fields = _merge_fields_triage(_extract_fields_heuristic(message), fields)

        # normalize negatives so we don't loop on red_flags
        fields = _normalize_negatives(fields, message)

        return assistant, fields
    except Exception:
        fields = _extract_fields_heuristic(message)
        fields = _normalize_negatives(fields, message)
        return default_reply, fields



QUESTION_TEMPLATES = {
    "red_flags": "Are you having any danger symptoms right now, like severe chest pain, trouble breathing, new weakness or numbness, heavy bleeding, or a severe allergic reaction?",
    "duration":  "How long has this been going on (hours, days, weeks, months)?",
    "severity":  "How severe is it right now: mild, moderate, or severe?",
    "location":  "Where do you feel it most (e.g., right knee, lower back, chest)?",
    "onset":     "Did it start suddenly or gradually?",
    "modifiers": "What makes it better or worse (movement, rest, medicines)?",
}

QUICK_OPTIONS = {
    "severity": ["mild", "moderate", "severe"],
    "duration": ["hours", "days", "weeks", "months"],
    "red_flags": ["none", "chest pain", "trouble breathing", "weakness/numbness", "severe bleeding", "anaphylaxis"],
}

def _next_slot(fields: dict) -> Optional[str]:
    order = ["red_flags", "duration", "severity", "location", "onset", "modifiers"]
    for key in order:
        v = fields.get(key)
        if not v or (isinstance(v, list) and not v):
            return key
    return None

@csrf_exempt
@require_http_methods(["POST"])
def api_v1_triage_chat(request):
    """
    Turn-by-turn triage with explicit end-of-flow (done) and escalation flags.
    Binds org via kiosk device token if middleware didn't.
    NOTE: No autosave here. Encounter creation happens only in /api/v1/triage/submit.
    """
    # Bind org from cookie/query/header token if present
    _bind_org_from_device_token(request)

    # --- parse body ---
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad json"}, status=400)

    message    = (body.get("message") or "").strip()
    history    = body.get("history") or []
    tone       = (body.get("tone") or "PlainClinical").strip()
    fields_in  = body.get("fields") or {}
    kiosk_tok  = body.get("kiosk_token")

    # If org still missing, try body.kiosk_token
    if not getattr(request, "org", None) and kiosk_tok:
        data = _read_device_token(kiosk_tok)
        if data:
            try:
                request.org = Org.objects.get(slug=data.get("org"))
            except Org.DoesNotExist:
                pass

    # --- extract / merge fields ---
    extracted = _extract_fields_heuristic(message)
    try:
        llm_reply, llm_fields = _llm_triage_turn(message, history, tone)
        extracted = _merge_fields_triage(extracted, llm_fields)
    except Exception:
        llm_reply = None

    fields = _merge_fields_triage(fields_in, extracted)
    fields = _normalize_negatives(fields, message)  # normalize "none" etc.

    # --- next slot / completion ---
    slot = _next_slot(fields)
    good_enough = bool(fields.get("complaint")) and bool(fields.get("location")) and bool(
        fields.get("duration") or fields.get("severity")
    )
    done = (slot is None) or good_enough

    # --- escalation detection ---
    DANGER_TERMS = {
        "chest pain", "shortness of breath", "trouble breathing",
        "weakness", "numbness", "severe bleeding", "anaphylaxis"
    }
    rf_text = " ".join([str(x).lower() for x in (fields.get("red_flags") or [])])
    escalate = any(term in rf_text for term in DANGER_TERMS)

    # --- craft assistant text ---
    if escalate:
        assistant_text = (
            "Based on what you shared, it’s safest to seek urgent care now. "
            "If you have emergency symptoms, call your local emergency number. "
            "I can stop here and send what we have to the clinic for follow-up."
        )
        planned_question = None
    elif done:
        assistant_text = (
            "Thank you. I have what I need to brief your care team. "
            "Please tap “Finish & send to clinic.” We’ll make sure you’re looked after."
        )
        planned_question = None
    else:
        planned_question = QUESTION_TEMPLATES.get(slot) or "Is there anything else important I should know?"
        assistant_text = (llm_reply or f"Thanks. {planned_question}").strip()
        if "?" not in assistant_text or not assistant_text.rstrip().endswith("?"):
            assistant_text = assistant_text.rstrip(".") + " " + planned_question

    # --- reply (no created_encounter_id here) ---
    return JsonResponse({
        "assistant": assistant_text,
        "fields": fields,
        "slot": slot,
        "next_question": planned_question,
        "quick_options": QUICK_OPTIONS.get(slot, []),
        "done": bool(done and not escalate),
        "escalate": bool(escalate),
    })



# -----------------------------
# TRIAGE (submit → Encounter)
# -----------------------------
TRIAGE_SUMMARY_FORMAT_PROMPT = """
Given patient triage fields and a transcript, return STRICT JSON:
{
  "acuity": "low" | "medium" | "high",
  "red_flags": string[],
  "next_steps": string[],
  "one_sentence": string
}
The one_sentence is ≤160 chars and clinically specific. No extra text; only JSON.
"""

@csrf_exempt
@require_http_methods(["POST"])
def api_v1_triage_submit(request):
    """
    Submit triage into an Encounter.
    Accepts optional 'patient' block to create/link a Patient.
    Binds org from kiosk device token (cookie/query/header) or from body.kiosk_token.
    """
    _bind_org_from_device_token(request)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad json"}, status=400)

    if not getattr(request, "org", None):
        tok = body.get("kiosk_token")
        if tok:
            data = _read_device_token(tok)
            if data:
                try:
                    request.org = Org.objects.get(slug=data.get("org"))
                except Org.DoesNotExist:
                    pass

    org = getattr(request, "org", None)
    if not org:
        return JsonResponse({"error": "org not found for host"}, status=400)

    message = (body.get("message") or "").strip()
    history = body.get("history") or []
    fields  = body.get("fields") or {}
    patient_in = body.get("patient") or {}

    if not (message or history):
        return JsonResponse({"error": "message or history required"}, status=400)

    actor = _default_actor_for_org(org)
    if not actor:
        return JsonResponse({"error": "no active users in org"}, status=400)

    transcript = []
    for turn in history:
        r = "assistant" if (turn.get("role") == "assistant") else "user"
        c = (turn.get("content") or "").strip()
        if c:
            transcript.append({"role": r, "content": c})
    if message:
        transcript.append({"role": "user", "content": message})

    patient_obj = None
    try:
        has_any = any(bool((patient_in.get(k) or "").strip())
                      for k in ("full_name", "first_name", "last_name", "email", "phone", "dob", "insurer", "policy_id"))
        if has_any:
            patient_obj = _upsert_patient(org, patient_in)
    except Exception:
        patient_obj = None

    # AI summary with safe fallback
    triage_ai = None
    try:
        sys1 = get_system_prompt("PlainClinical") + "\n" + TRIAGE_SUMMARY_FORMAT_PROMPT
        resp = client.chat.completions.create(
            model=OPENAI_TRIAGE_MODEL,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": sys1},
                {"role": "user", "content": f"FIELDS:\n{json.dumps(fields, ensure_ascii=False)}\n\nTRANSCRIPT:\n{json.dumps(transcript, ensure_ascii=False)}"},
            ],
        )
        triage_ai = _safe_json(resp.choices[0].message.content, {})

        if triage_ai.get("one_sentence"):
            rewrite = client.chat.completions.create(
                model=OPENAI_TRIAGE_MODEL,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": get_system_prompt("PlainClinical")},
                    {"role": "user", "content": f"Rewrite warmly, clearly, ≤160 chars; keep clinical specificity:\n\n{triage_ai['one_sentence']}"},
                ],
            )
            triage_ai["one_sentence"] = (rewrite.choices[0].message.content or triage_ai["one_sentence"]).strip()
    except Exception:
        triage_ai = None

    if not triage_ai:
        preview = (message or (transcript[-1]["content"] if transcript else ""))[:160]
        triage_ai = {
            "acuity": "low",
            "red_flags": fields.get("red_flags", []) or ["none obvious"],
            "next_steps": ["clinic within 48–72h", "self-care as appropriate"],
            "one_sentence": preview or "Patient-reported symptoms.",
        }

    payload = {
        "fields": fields,
        "transcript": transcript,
        "triage": triage_ai,
        "patient": {
            "full_name": (getattr(patient_obj, "full_name", None) or patient_in.get("full_name") or "Anonymous"),
            "insurer":   (getattr(patient_obj, "insurer", None)   or patient_in.get("insurer")),
            "email":     (getattr(patient_obj, "email", None)     or patient_in.get("email")),
            "phone":     (getattr(patient_obj, "phone", None)     or patient_in.get("phone")),
        },
    }

    reason = (
        (fields.get("complaint") or "").strip()
        or (triage_ai.get("one_sentence") or "").strip()
        or "Patient-reported symptoms"
    )

    E = getattr(Encounter, "all_objects", Encounter.objects)
    enc_kwargs = dict(
        org=org,
        user=actor,
        reason=reason,
        status="new",
        priority="medium",
        summary=json.dumps(payload, ensure_ascii=False),
    )
    if patient_obj:
        enc_kwargs["patient"] = patient_obj

    enc = E.create(**enc_kwargs)

    return JsonResponse({
        "encounter_id": enc.id,
        "status": enc.status,
        "reason": enc.reason,
        **triage_ai
    }, status=201)

@require_http_methods(["GET"])
def api_v1_triage_get(request, encounter_id: int):
    org = getattr(request, "org", None)
    E = getattr(Encounter, "all_objects", Encounter.objects)
    try:
        enc = E.get(pk=encounter_id, org=org) if org else E.get(pk=encounter_id)
    except Encounter.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    payload = _safe_json(enc.summary or "{}", {})
    triage = payload.get("triage") or {}
    return JsonResponse({"encounter_id": enc.id, "triage": triage, "payload": payload})


# -----------------------------
# Scheduling (demo)
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def api_v1_sched_suggest(request):
    return JsonResponse({
        "suggestions": [
            {"slot": "2025-09-12T09:30:00", "type": "New patient"},
            {"slot": "2025-09-12T14:15:00", "type": "Follow-up"},
        ]
    })

@csrf_exempt
@require_http_methods(["POST"])
def api_v1_sched_book(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad json"}, status=400)
    return JsonResponse({"ok": True, "appointment_id": "apt_demo_001", "echo": body})


# -----------------------------
# Clinical brief (from triage)
# -----------------------------
BRIEF_FORMAT_PROMPT = """
Return STRICT JSON:
{
  "chief_complaint": string,
  "salient_history": string[],
  "ddx": string[],
  "recommended_questions": string[]
}
No extra text; only JSON.
"""

@csrf_exempt
@require_http_methods(["POST"])
def api_v1_chart_brief(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad json"}, status=400)

    enc_id = body.get("encounter_id")
    if not enc_id:
        return JsonResponse({"error": "encounter_id required"}, status=400)

    org = getattr(request, "org", None)
    E = getattr(Encounter, "all_objects", Encounter.objects)
    try:
        enc = E.get(pk=enc_id, org=org) if org else E.get(pk=enc_id)
    except Encounter.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    payload = _safe_json(enc.summary or "{}", {})
    fields = payload.get("fields") or {}
    transcript = payload.get("transcript") or []

    brief = None
    try:
        sys = get_system_prompt("PlainClinical") + "\n" + BRIEF_FORMAT_PROMPT
        resp = client.chat.completions.create(
            model=OPENAI_BRIEF_MODEL,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": f"FIELDS:\n{json.dumps(fields, ensure_ascii=False)}\n\nTRANSCRIPT:\n{json.dumps(transcript, ensure_ascii=False)}"},
            ],
        )
        brief = _safe_json(resp.choices[0].message.content, {})
    except Exception:
        brief = {
            "chief_complaint": fields.get("complaint") or "N/A",
            "salient_history": ["Structured brief unavailable; showing captured intake only."],
            "ddx": ["n/a"],
            "recommended_questions": ["Onset/duration?", "Severity?", "Aggravating factors?"],
        }

    return JsonResponse({"encounter_id": enc.id, "brief": brief})


# -----------------------------
# Diagnostics (demo)
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def api_v1_diag_interpret(request):
    if not request.FILES:
        return JsonResponse({"error": "no files uploaded"}, status=400)

    names = [f.name for f in request.FILES.getlist("files")]
    findings = {
        "observed": ["example: joint space narrowing medial compartment"],
        "possible": ["example: degenerative OA"],
        "next": ["example: weight-bearing x-ray", "example: PT referral"],
    }
    return JsonResponse({"files": names, "findings": findings})


# -----------------------------
# Coding & Claims (demo)
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def api_v1_coding_suggest(request):
    return JsonResponse({
        "icd": [{"code": "M17.11", "desc": "Unilateral primary osteoarthritis, right knee", "why": "pain + x-ray OA"}],
        "cpt": [{"code": "99213", "desc": "Established patient, low MDM", "why": "stable chronic illness"}],
    })

@csrf_exempt
@require_http_methods(["POST"])
def api_v1_claim_draft(request):
    return JsonResponse({"claim_id": "clm_demo_001", "status": "draft"})


# -----------------------------
# Care plan & Messages (demo)
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def api_v1_careplan_generate(request):
    return JsonResponse({
        "plan": [
            {"task": "RICE protocol 48h", "channel": "printable"},
            {"task": "PT evaluation in 2 weeks", "channel": "sms"},
        ]
    })

@csrf_exempt
@require_http_methods(["POST"])
def api_v1_messages_send(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad json"}, status=400)
    return JsonResponse({"queued": True, "id": "msg_demo_001", "echo": body})


from django.shortcuts import get_object_or_404  # you already have this at top

def _json_or_dict(val):
    if isinstance(val, dict):
        return val
    try:
        import json
        return json.loads(val or "{}")
    except Exception:
        return {}

@login_required(login_url="/portal/login/")
def portal_encounter_detail(request, pk: int):
    """Portal page to review a single encounter (org-scoped)."""
    org = getattr(request, "org", None)

    # Prefer all_objects if you use soft-deletes; otherwise .objects
    E = getattr(Encounter, "all_objects", Encounter.objects).select_related("patient")

    # Scope by org when the model has an org field and org is bound
    try:
        has_org_field = any(f.name == "org" for f in Encounter._meta.fields)
    except Exception:
        has_org_field = False
    if has_org_field and org:
        E = E.filter(org=org)

    enc = get_object_or_404(E, pk=pk)

    payload = _json_or_dict(enc.summary)
    triage = payload.get("triage", {}) or {}
    fields = payload.get("fields", {}) or {}
    transcript = payload.get("transcript", []) or []

    context = {
        "enc": enc,
        "patient": getattr(enc, "patient", None),
        "triage": triage,
        "fields": fields,
        "transcript": transcript,
    }
    return render(request, "portal/encounter_detail.html", context)


# ==== Staff/dev tenant admin (create orgs, users) ====
from django import forms
from django.contrib.admin.views.decorators import staff_member_required

class CreateClientForm(forms.Form):
    name = forms.CharField(max_length=120, help_text="Display name, e.g., MercyCare Clinic")
    slug = forms.SlugField(help_text="Unique key, e.g., mercycare")
    primary_domain = forms.CharField(
        max_length=255,
        help_text="Full host, e.g., mercycare.neuromedai.org",
    )
    owner_email = forms.EmailField(help_text="Initial account owner")
    send_email = forms.BooleanField(required=False, initial=True)

class CreateClientUserForm(forms.Form):
    email = forms.EmailField()
    role = forms.ChoiceField(choices=OrgMembership.ROLE_CHOICES, initial="CLINICIAN")
    set_temp_password = forms.BooleanField(required=False, initial=True)
    send_email = forms.BooleanField(required=False, initial=True)

class ResetClientUserPasswordForm(forms.Form):
    email = forms.EmailField()
    send_email = forms.BooleanField(required=False, initial=True)

def _gen_password(length=12):
    import secrets, string
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

@staff_member_required
def dev_client_create(request):
    """
    Create a new Org + primary OrgDomain + OWNER user (if not exists).
    Show temp password and optionally email it.
    """
    if request.method == "POST":
        form = CreateClientForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"].strip()
            slug = form.cleaned_data["slug"].strip()
            primary_domain = form.cleaned_data["primary_domain"].lower().strip()
            owner_email = form.cleaned_data["owner_email"].lower().strip()
            send_email_flag = form.cleaned_data["send_email"]

            org, created = Org.objects.get_or_create(slug=slug, defaults={"name": name})
            if not created:
                org.name = name
                org.save()

            OrgDomain.objects.update_or_create(
                org=org, domain=primary_domain, defaults={"is_primary": True}
            )

            owner, user_created = User.objects.get_or_create(
                email=owner_email, defaults={"username": owner_email}
            )

            # Membership (OWNER)
            OrgMembership.objects.get_or_create(org=org, user=owner, defaults={"role": "OWNER"})

            temp_password = None
            if user_created:
                temp_password = _gen_password()
                owner.set_password(temp_password)
                owner.save()

            if send_email_flag:
                _email_credentials(owner_email, org, temp_password)

            messages.success(
                request,
                f"Client '{escape(org.name)}' created at https://{escape(primary_domain)}/portal/."
                + (f" Owner temp password: {temp_password}" if temp_password else " Owner already existed (password unchanged).")
            )
            return redirect(reverse("dev_client_detail", args=[org.slug]))
    else:
        form = CreateClientForm()

    return render(request, "dev/client_create.html", {"form": form})

@staff_member_required
def dev_client_detail(request, slug):
    """Overview page: domains, members, and quick actions."""
    org = Org.objects.get(slug=slug)
    members = OrgMembership.objects.filter(org=org).select_related("user")
    return render(request, "dev/client_detail.html", {"org": org, "members": members})

@staff_member_required
def dev_client_user_create(request, slug):
    """Create a user inside an org with a role and (optional) temp password."""
    org = Org.objects.get(slug=slug)

    if request.method == "POST":
        form = CreateClientUserForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()
            role = form.cleaned_data["role"]
            set_temp = form.cleaned_data["set_temp_password"]
            send_mail_flag = form.cleaned_data["send_email"]

            user, created = User.objects.get_or_create(email=email, defaults={"username": email})

            temp_password = None
            if set_temp:
                temp_password = _gen_password()
                user.set_password(temp_password)
                user.save()

            OrgMembership.objects.get_or_create(org=org, user=user, defaults={"role": role})

            if send_mail_flag:
                _email_credentials(email, org, temp_password)

            messages.success(
                request,
                f"User {escape(email)} added to {escape(org.name)} as {role}."
                + (f" Temp password: {temp_password}" if temp_password else "")
            )
            return redirect(reverse("dev_client_detail", args=[org.slug]))
    else:
        form = CreateClientUserForm()

    return render(request, "dev/client_user_create.html", {"form": form, "org": org})

@staff_member_required
def dev_client_user_reset_password(request, slug):
    """Reset a user's password inside an org (doesn't change membership)."""
    org = Org.objects.get(slug=slug)

    if request.method == "POST":
        form = ResetClientUserPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower().strip()
            send_mail_flag = form.cleaned_data["send_email"]

            user = User.objects.filter(email=email).first()
            if not user:
                messages.error(request, "No user with that email.")
                return redirect(reverse("dev_client_detail", args=[org.slug]))

            if not OrgMembership.objects.filter(org=org, user=user, is_active=True).exists():
                messages.error(request, "That user is not a member of this organization.")
                return redirect(reverse("dev_client_detail", args=[org.slug]))

            temp_password = _gen_password()
            user.set_password(temp_password)
            user.save()

            if send_mail_flag:
                _email_credentials(email, org, temp_password)

            messages.success(request, f"Password reset. Temp password: {temp_password}")
            return redirect(reverse("dev_client_detail", args=[org.slug]))
    else:
        form = ResetClientUserPasswordForm()

    return render(request, "dev/client_user_reset_password.html", {"form": form, "org": org})
