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

# at top of file with other imports
import re, uuid
from pathlib import Path
from django.conf import settings
from .models import Profile
from .utils import get_client_ip

ALLOWED_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".heic", ".webp")
USER_MEDIA_SUBDIR = getattr(settings, "USER_MEDIA_SUBDIR", "user_media")
SESSION_IMAGE_INDEX = "known_images"  # {lower_filename: relative_path_from_MEDIA_ROOT}
MAX_INDEXED_IMAGES = 100
MAX_FILES_PER_UPLOAD = 15  # Allow up to 15 files (more than required 10)

# views.py (top)
from django.utils import timezone
from .models import ChatSession

# myApp/emailer.py
import json, logging, requests
from typing import Iterable, Optional, Union
from django.conf import settings

log = logging.getLogger(__name__)

RESEND_URL = f"{settings.RESEND.get('BASE_URL', 'https://api.resend.com')}/emails"
RESEND_KEY = settings.RESEND.get("API_KEY")
RESEND_FROM = settings.RESEND.get("FROM") or settings.DEFAULT_FROM_EMAIL
RESEND_REPLY_TO = settings.RESEND.get("REPLY_TO")

def send_via_resend(
    *,
    to: Union[Iterable[str], str],
    subject: str,
    text: Optional[str] = None,
    html: Optional[str] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[Union[Iterable[str], str]] = None,
    cc: Optional[Iterable[str]] = None,
    bcc: Optional[Iterable[str]] = None,
    tags: Optional[dict] = None,
    fail_silently: bool = True,
) -> bool:
    """
    Minimal Resend sender. Returns True on 2xx. Logs (doesn't raise) by default.
    """
    if not RESEND_KEY:
        msg = "RESEND_API_KEY missing; email not sent."
        if fail_silently:
            log.warning(msg); return False
        raise RuntimeError(msg)

    if isinstance(to, str): to = [to]
    if isinstance(reply_to, str): reply_to = [reply_to]

    payload = {
        "from": (from_email or RESEND_FROM),
        "to": list(to),
        "subject": subject,
    }
    if text: payload["text"] = text
    if html: payload["html"] = html
    if reply_to or RESEND_REPLY_TO:
        payload["reply_to"] = reply_to or [RESEND_REPLY_TO]
    if cc: payload["cc"] = list(cc)
    if bcc: payload["bcc"] = list(bcc)
    if tags:
        # Resend supports tags via headers (x-headers) or metadata; keep simple:
        payload["headers"] = {f"X-Tag-{k}": str(v) for k, v in tags.items()}

    try:
        resp = requests.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {RESEND_KEY}", "Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=10,
        )
        ok = 200 <= resp.status_code < 300
        if not ok:
            log.error("Resend send failed: %s %s", resp.status_code, resp.text)
        return ok
    except Exception as e:
        if fail_silently:
            log.exception("Resend exception")
            return False
        raise



def _user_media_root(user) -> Path:
    # Anonymous users get "anon"; you can also force auth if you prefer.
    uid = getattr(user, "id", None) or "anon"
    root = Path(settings.MEDIA_ROOT) / USER_MEDIA_SUBDIR / str(uid)
    root.mkdir(parents=True, exist_ok=True)
    return root

def _index_known_image(request, display_name: str, abs_path: Path):
    """Index by the *display* filename the user knows AND the stored filename."""
    rel = abs_path.relative_to(settings.MEDIA_ROOT).as_posix()
    idx = request.session.get(SESSION_IMAGE_INDEX, {})
    # keep lowercase keys for case-insensitive lookups
    for key in {display_name.lower(), abs_path.name.lower()}:
        idx[key] = rel
    # prune if too big (FIFO-ish)
    if len(idx) > MAX_INDEXED_IMAGES:
        # drop oldest ~10 items
        for _ in range(10):
            try:
                k = next(iter(idx))
                idx.pop(k, None)
            except StopIteration:
                break
    request.session[SESSION_IMAGE_INDEX] = idx
    request.session.modified = True

def _resolve_indexed_image(request, filename: str) -> Optional[Path]:
    idx = request.session.get(SESSION_IMAGE_INDEX, {})
    rel = idx.get(filename.lower())
    if not rel:
        return None
    p = Path(settings.MEDIA_ROOT) / rel
    return p if p.exists() else None

def _scan_user_media_for_name(user, filename: str) -> Optional[Path]:
    """Fallback: look for exact filename in the user's media dir."""
    base = _user_media_root(user)
    target = filename.lower()
    for p in base.glob("**/*"):
        if p.is_file() and p.suffix.lower() in ALLOWED_IMAGE_EXTS and p.name.lower() == target:
            return p
    return None

def _parse_image_filenames(text: str) -> list[str]:
    """
    Find things that look like image filenames in free text.
    Permissive but safe; prevents paths and URLs (just plain filenames).
    """
    if not text:
        return []
    # allow letters, numbers, spaces, dashes, underscores, parentheses, dots before extension
    pattern = r"([A-Za-z0-9 _\-\.\(\)]+?\.(?:jpg|jpeg|png|heic|webp))"
    # exclude anything containing slashes or backslashes to avoid paths
    candidates = [m.group(1) for m in re.finditer(pattern, text, flags=re.IGNORECASE)]
    return [c for c in candidates if "/" not in c and "\\" not in c][:5]  # cap to 5 per message

def _save_copy_to_user_media(request, file_obj, display_name: str) -> Path:
    """
    Save an uploaded file to the user's media folder with a unique name,
    index it by the display name and stored name, and return the absolute path.
    """
    base = _user_media_root(request.user)
    ext = Path(display_name).suffix.lower() or ".bin"
    unique_name = f"{Path(display_name).stem}-{uuid.uuid4().hex[:6]}{ext}"
    dest = base / unique_name
    with dest.open("wb") as out:
        for chunk in file_obj.chunks():
            out.write(chunk)
    _index_known_image(request, display_name, dest)
    return dest


# -------- OpenAI
from openai import OpenAI
# Set timeout to prevent Railway 502 errors (30s max for HTTP requests)
client = OpenAI(timeout=25.0)  # Slightly under Railway's typical 30s limit

# =============================
#         PROMPTS
# =============================
# ---- Soft-memory config (place near other constants)
SOFT_MEMORY_TTL_MIN = 15  # how long we remember the last quick exchange

def _now_ts():
    from django.utils import timezone
    return int(timezone.now().timestamp())

def _wc(s: str) -> int:
    return len((s or "").split())

# --- Dynamic bilingual + auto prompts ---
BILINGUAL_LANGS = {
    "Es": "Spanish",
    "Fr": "French",
    "De": "German",
    "Ja": "Japanese",
    "Ko": "Korean",
    "Ar": "Arabic",
}

def make_bilingual_prompt(lang_name: str) -> str:
    return (
        "You are NeuroMed, a warm bilingual medical guide.\n"
        f"Respond first in {lang_name} for clarity, then add a short English recap.\n"
        "Keep explanations clear, kind, and practical. Invite follow-up at the end.\n"
        "If urgent red flags are present, mention them briefly and calmly."
    )

AUTO_PROMPT = (
    "You are NeuroMed, a multilingual medical guide.\n"
    "Detect the user's language and reply in that language first, then add a short English recap.\n"
    "Keep it warm, clear, practical, and invite follow-up."
)

def _parse_bilingual_code(t: str) -> Optional[str]:
    # Accept forms like BilingualEsEn, BilingualFrEn, BilingualJaEn, etc.
    m = re.match(r"^Bilingual([A-Za-z]{2})En$", t or "")
    return m.group(1) if m else None

def _get_language_name(lang_code: str) -> str:
    """Convert language code to readable name for AI prompts."""
    lang_map = {
        'en-US': 'English', 'ja-JP': 'Japanese', 'es-ES': 'Spanish', 'fr-FR': 'French', 
        'de-DE': 'German', 'it-IT': 'Italian', 'pt-PT': 'Portuguese', 'pt-BR': 'Portuguese (Brazil)',
        'ru-RU': 'Russian', 'zh-CN': 'Chinese (Simplified)', 'zh-TW': 'Chinese (Traditional)',
        'ko-KR': 'Korean', 'ar-SA': 'Arabic', 'tr-TR': 'Turkish', 'nl-NL': 'Dutch',
        'sv-SE': 'Swedish', 'pl-PL': 'Polish', 'da-DK': 'Danish', 'no-NO': 'Norwegian',
        'fi-FI': 'Finnish', 'he-IL': 'Hebrew', 'th-TH': 'Thai', 'hi-IN': 'Hindi',
        'cs-CZ': 'Czech', 'ro-RO': 'Romanian', 'hu-HU': 'Hungarian', 'sk-SK': 'Slovak',
        'bg-BG': 'Bulgarian', 'uk-UA': 'Ukrainian', 'vi-VN': 'Vietnamese', 'id-ID': 'Indonesian',
        'ms-MY': 'Malay', 'sr-RS': 'Serbian', 'hr-HR': 'Croatian', 'el-GR': 'Greek',
        'lt-LT': 'Lithuanian', 'lv-LV': 'Latvian', 'et-EE': 'Estonian', 'sl-SI': 'Slovenian',
        'is-IS': 'Icelandic', 'sq-AL': 'Albanian', 'mk-MK': 'Macedonian', 'bs-BA': 'Bosnian',
        'ca-ES': 'Catalan', 'gl-ES': 'Galician', 'eu-ES': 'Basque', 'hy-AM': 'Armenian',
        'fa-IR': 'Persian', 'sw-KE': 'Swahili', 'ta-IN': 'Tamil', 'te-IN': 'Telugu',
        'kn-IN': 'Kannada', 'ml-IN': 'Malayalam', 'mr-IN': 'Marathi', 'pa-IN': 'Punjabi',
        'gu-IN': 'Gujarati', 'or-IN': 'Odia', 'as-IN': 'Assamese', 'ne-NP': 'Nepali',
        'si-LK': 'Sinhala'
    }
    return lang_map.get(lang_code, lang_code.split('-')[0].title() if '-' in lang_code else lang_code)

def _add_language_instruction(system_prompt: str, lang: str) -> str:
    """
    Add language instruction to system prompt.
    Matches Language Enforcement Rules from design system.
    """
    if not lang or lang == 'en-US':
        # English is default, no need to add instruction
        return system_prompt
    
    lang_name = _get_language_name(lang)
    language_instruction = (
        f"\n\n=== LANGUAGE REQUIREMENT ===\n"
        f"The user has selected {lang_name} ({lang}) as their preferred language.\n\n"
        f"Language Enforcement Rules:\n"
        f"• Entire response must be in {lang_name}\n"
        f"• Medical meaning must not be shortened or diluted\n"
        f"• English used only when explicitly requested\n"
        f"• Maintain structure and clarity in {lang_name}\n"
        f"• Avoid slang or idioms\n"
        f"• Every word of your response should be in {lang_name}\n"
        f"\n"
        f"This is critical for accessibility and user preference."
    )
    return system_prompt + language_instruction


def _is_detailed(msg: str) -> bool:
    """Treat as detailed if >= 12 words or contains multiple clauses/signals."""
    if _wc(msg) >= 12:
        return True
    msg_l = (msg or "").lower()
    separators = [",", ";", " because ", " since ", " for weeks", " for days", " after ", " with "]
    return any(x in msg_l for x in separators)

def _classify_mode(user_message: str, has_files: bool, session: dict) -> tuple[str, str]:
    """
    Decide QUICK / EXPLAIN / FULL and a topic hint (soft memory).
    - QUICK: short single symptom, no files
    - EXPLAIN: general question, no files, not super short
    - FULL: any file OR detailed description OR soft-memory upgrade
    """
    # Soft-memory pull
    last_mode = session.get("nm_last_mode")
    last_msg  = session.get("nm_last_short_msg", "")
    last_ts   = session.get("nm_last_ts")

    topic_hint = ""
    if has_files or _is_detailed(user_message):
        # auto-upgrade to FULL if within TTL and last was QUICK
        if last_mode == "QUICK" and last_ts and (_now_ts() - last_ts) <= SOFT_MEMORY_TTL_MIN * 60:
            topic_hint = last_msg[:140]
        return "FULL", topic_hint

    # no files / not detailed: QUICK vs EXPLAIN
    if 0 < _wc(user_message) < 12:
        return "QUICK", ""
    return "EXPLAIN", ""


def build_system_prompt(tone: str, care_setting: Optional[str], faith_setting: Optional[str], lang: str) -> str:
    base = get_system_prompt(tone)

    if tone in ("Clinical", "Caregiver") and care_setting:
        full = get_setting_prompt(base, care_setting)
    elif tone == "Faith" and faith_setting:
        full = get_faith_prompt(base, faith_setting)
    else:
        full = base

    return f"{full}\n\n(Always respond in {lang} unless told otherwise.)"



PROMPT_TEMPLATES = {
    "PlainClinical": (
        "You are NeuroMed AI, a clinical-grade medical communication assistant.\n"
        "Your role: Bridge understanding between medical information and real people with clarity, compassion, and confidence.\n"
        "\n"
        "Communication Pillars:\n"
        "1. Clarity Before Complexity\n"
        "2. Empathy Without Assumption\n"
        "3. Structure Without Rigidity\n"
        "4. Accuracy Without Alarmism\n"
        "5. Guidance Without Diagnosis\n"
        "\n"
        "Voice: Calm, confident, human. Conversational, not instructional. Free of markdown symbols or technical formatting. "
        "No robotic phrasing or excessive disclaimers.\n"
        "\n"
        "Response Modes (choose based on context):\n"
        "\n"
        "— QUICK MODE: Triggered when user gives only 1 short symptom (under 12 words) and no file/image.\n"
        "Structure: Gentle acknowledgment + 2–4 safe immediate actions + 1 clear red flag + 1 soft follow-up invitation.\n"
        "Maximum length: 5 sentences.\n"
        "Close with: 'Does this align with what you're experiencing?' or similar invitation.\n"
        "\n"
        "— EXPLAIN MODE: Triggered when user asks a general health question without a file/image.\n"
        "Structure: What it is + Common signs or causes + Simple prevention or management + Invitation to explore further.\n"
        "Length: 2–4 sentences.\n"
        "Do not add clinician notes unless asked.\n"
        "Close with: 'Would you like me to go deeper into this?' or similar invitation.\n"
        "\n"
        "— FULL BREAKDOWN MODE: Triggered when files/images are uploaded, symptoms are detailed, or follow-up questions are asked.\n"
        "Structure:\n"
        "• Short conversational lead-in (no label, no 'Introduction' heading)\n"
        "• Common signs (3–5 bullets)\n"
        "• What you can do now (3–5 bullets)\n"
        "• When to seek medical help (2–4 bullets)\n"
        "• Clinician notes (only when relevant, 1–4 concise points)\n"
        "• Warm conversational close\n"
        "\n"
        "Always end with an invitation that keeps dialogue going. Maintain conversation flow, not lecture format.\n"
        "\n"
        "Original mode details:\n"
        "You are NeuroMed, a warm but precise medical guide.\n"
        "Choose response mode based on context:\n"
        "\n"
        "— QUICK MODE: If the user gives only 1 short symptom (under 12 words) and no file/image, "
        "reply in under 5 sentences: empathy + 2–4 safe immediate actions + 1 urgent red flag + 1 follow-up question. "
        "Always close with a gentle open-ended invitation (e.g., 'Does that sound like what you’re feeling?' or "
        "'Want to tell me a bit more about it?').\n"
        "\n"
        "— EXPLAIN MODE: If the user asks a general health question without a file/image, "
        "give 2–4 sentences in plain language describing what it is, common signs, and basic prevention/management. "
        "Do not add clinician notes unless asked. "
        "Close by inviting curiosity (e.g., 'Would you like me to go into daily tips?' or "
        "'Do you want me to compare this with other conditions?').\n"
        "\n"
        "— FULL BREAKDOWN MODE: If there is ANY file/image, OR detailed description (multiple symptoms, history, or follow-up), "
        "always reply in sections, but do NOT write the word 'Introduction' as a heading:\n"
        "Start with a 1–2 sentence lead-in (no label).\n"
        "Common signs – 3–5 bullet points.\n"
        "What you can do – 3–5 bullet points.\n"
        "When to seek help – 2–4 bullet points.\n"
        "For clinicians – only if relevant, 1–4 concise points.\n"
        "Close with a warm conversational handoff (e.g., 'Is this close to what you’re noticing?' or "
        "'Want me to suggest some next steps for your situation?').\n"
        "\n"
        "Tone: friendly, human, and confident. No markdown symbols (no **, ##). No robotic phrasing or unnecessary disclaimers. "
        "Keep the flow like an ongoing conversation, not a lecture."
    ),

    "Caregiver": (
        "You are NeuroMed AI, supporting caregivers with clarity, reassurance, and practical guidance.\n"
        "\n"
        "Voice: Gentle and validating. Clear and actionable. Focused on support and reassurance.\n"
        "\n"
        "Behavior Rules:\n"
        "• Explain medical concepts in caregiver-friendly language\n"
        "• Emphasize practical next steps\n"
        "• Always end by inviting the caregiver to share more context or concerns\n"
        "\n"
        "Maintain medical accuracy while being accessible and supportive."
    ),

    "Faith": (
        "You are NeuroMed, a faith-filled health companion. "
        "Provide clear medical explanations with hope and peace. "
        "When appropriate, close with a short Bible verse or brief prayer. "
        "Keep the tone open by asking if they’d like more guidance or encouragement."
    ),

    "Clinical": (
        "🩺 You are NeuroMed AI, operating in Clinical Mode.\n"
        "Purpose: High-precision, clinician-friendly analysis for medical environments.\n"
        "\n"
        "Voice: Structured. Evidence-aware. Highly scannable. Action-oriented.\n"
        "\n"
        "Dual Output Format:\n"
        "\n"
        "(1) Full SOAP Note:\n"
        "• Subjective\n"
        "• Objective\n"
        "• Assessment\n"
        "• Plan\n"
        "• Highlight abnormal values with reference ranges\n"
        "• Suggest confirmatory steps\n"
        "• Identify escalation thresholds\n"
        "• Note immediate safety concerns\n"
        "\n"
        "(2) Quick-Scan Clinical Card:\n"
        "• One line per abnormality\n"
        "• Format: Value → interpretation → action\n"
        "• Clear urgency indicators\n"
        "• Rounds-friendly, concise, decisive\n"
        "• Use emoji-coded, action-first bullet points\n"
        "• Example: '→ Repeat CBC', '→ Check osmolality', '→ Obtain ECG'\n"
        "\n"
        "Ensure outputs are clinically precise, evidence-based, and easy to scan.\n"
        "Close with contextual offer: 'Want me to expand into a differential?', 'Need dosing ranges?', or 'Shall I align with guideline-based recommendations?'"
    ),






    # in PROMPT_TEMPLATES
    "Bilingual": (
        "You are NeuroMed AI, delivering medically accurate responses in the user's preferred language.\n"
        "\n"
        "Behavior Rules:\n"
        "• Respond fully in selected language\n"
        "• Maintain structure and clarity\n"
        "• Avoid slang or idioms\n"
        "• English used only when explicitly requested\n"
        "\n"
        "Keep explanations clear, kind, and practical. End with a soft invitation to continue sharing."
    ),


    "Geriatric": (
        "You are NeuroMed AI, providing thoughtful support for older adults and their families.\n"
        "\n"
        "Voice: Respectful. Unhurried. Practical and reassuring.\n"
        "\n"
        "Focus Areas:\n"
        "• Falls\n"
        "• Frailty\n"
        "• Medications (polypharmacy)\n"
        "• Cognitive changes\n"
        "• Mobility\n"
        "• Nutrition\n"
        "• Continence\n"
        "• Advance care planning\n"
        "\n"
        "Behavior Rules:\n"
        "• Include caregiver-friendly tips\n"
        "• Suggest gentle next steps (medication review, PT/OT, home safety, hearing/vision check, cognitive screening, goals-of-care discussion)\n"
        "• Encourage family conversations when appropriate\n"
        "• End with open dialogue prompts\n"
        "\n"
        "Example closing: 'Would you like me to suggest some home adjustments?' or similar dialogue-keeping question."
    ),

    "EmotionalSupport": (
        "You are NeuroMed AI, providing emotional reassurance while maintaining medical safety.\n"
        "\n"
        "Voice: Warm and validating. Calm and grounded. Never dismissive.\n"
        "\n"
        "Behavior Rules:\n"
        "• Acknowledge emotions explicitly (always begin by acknowledging emotions in a warm, human way)\n"
        "• Offer 1–2 gentle steps for today\n"
        "• Mention urgent red flags calmly\n"
        "• Encourage self-kindness\n"
        "• Remind users they are not alone\n"
        "• Never diagnose\n"
        "• Encourage professional care when needed\n"
        "• End with an open invitation\n"
        "\n"
        "Keep language simple, reassuring, and kind, while still accurate.\n"
        "Example closing: 'Would you like me to walk with you through this a bit more?'"
    ),
}



def normalize_tone(tone: Optional[str]) -> str:
    """
    Normalize tone names. Defaults to PlainClinical if not matched.
    Handles various formats:
    - "plain_clinical" -> "PlainClinical"
    - "PlainClinical" -> "PlainClinical"
    - "plainclinical" -> "PlainClinical"
    - "plain" -> "PlainClinical"
    """
    if not tone:
        return "PlainClinical"
    t = str(tone).strip()

    # Convert underscore-separated to PascalCase (e.g., "plain_clinical" -> "PlainClinical")
    if '_' in t:
        t = ''.join(word.capitalize() for word in t.split('_'))
    
    # exact key match (case-insensitive)
    key = next((k for k in PROMPT_TEMPLATES.keys() if k.lower() == t.lower()), None)
    if key:
        return key

    # legacy aliases
    if t.lower() in {"plain", "science", "default", "balanced", "plainclinical"}:
        return "PlainClinical"
    
    # Handle common variations
    tone_map = {
        "caregiver": "Caregiver",
        "emotional": "EmotionalSupport",
        "emotional_support": "EmotionalSupport",
        "geriatric": "Geriatric",
        "clinical": "Clinical",
        "bilingual": "Bilingual",
    }
    if t.lower() in tone_map:
        return tone_map[t.lower()]

    return "PlainClinical"


def get_system_prompt(tone: Optional[str]) -> str:
    """
    Return the base tone-specific system prompt.
    """
    t = normalize_tone(tone)
    return PROMPT_TEMPLATES.get(t, PROMPT_TEMPLATES["PlainClinical"])


def get_setting_prompt(base_prompt: str, care_setting: str) -> str:
    """
    Append care-setting context onto the tone base prompt.
    """
    care = (care_setting or "hospital").lower()
    if care == "ambulatory":
        extra = (
            "Context: Ambulatory/Outpatient visit.\n"
            "Start the reply with a one-line setting banner exactly like:\n"
            "[Clinic Follow-Up]\n\n"
            "Then write in these sections:\n"
            "Clinic Snapshot – 3–5 bullets.\n"
            "Today’s Plan – 3–6 bullets.\n"
            "What to Watch – 2–4 bullets.\n"
            "Close with a short, conversational handoff."
        )
    elif care == "urgent":
        extra = (
            "Context: Urgent Care.\n"
            "Start the reply with a one-line setting banner exactly like:\n"
            "[Urgent Care Triage]\n\n"
            "Then write in these sections:\n"
            "Quick Triage Summary – 5–7 bullets.\n"
            "Immediate Steps – 3–5 bullets.\n"
            "ER / Return Criteria – 3–5 bullets.\n"
            "Close with a short, calm, action-first message."
        )
    else:
        extra = (
            "Context: Inpatient/Hospital/Discharge handoff.\n"
            "Start the reply with a one-line setting banner exactly like:\n"
            "[Inpatient / Discharge Handoff]\n\n"
            "Then write in these sections:\n"
            "Handoff Highlights – 3–6 bullets.\n"
            "Discharge Plan – 3–6 bullets.\n"
            "Safety & Red Flags – 2–4 bullets.\n"
            "Clinician Notes – 1–4 concise points if relevant.\n"
            "Close with a warm line that invites follow-up."
        )
    return f"{base_prompt}\n\n{extra}"


VALID_SETTINGS = {"hospital", "ambulatory", "urgent"}
def norm_setting(val: Optional[str]) -> str:
    v = (val or "hospital").lower().strip()
    return v if v in VALID_SETTINGS else "hospital"





def _append_urgent_triage(summary_text: str, raw_text: str) -> str:
    # Naive pulls; your future version can parse vitals from raw_text
    lines = [
        "🚑 Quick Triage Card",
        "• Allergies: (if listed) ",
        "• Current Meds: (key meds/anticoagulants if present) ",
        "• Recent Encounters: (ED/hospital last 30–90d if present) ",
        "• Red Flags Mentioned: (chest pain, stroke signs, SOB, uncontrolled bleeding, severe dehydration, etc.)",
        "• Immediate Next Steps: (e.g., ECG if chest pain; wound care; fluids; observe; referral) ",
        "• Return/ER If: (worsening pain, fever >38.5°C, new neuro deficits, fainting, etc.)",
    ]
    card = "\n".join(lines)
    if "Quick Triage Card" not in summary_text:
        return f"{summary_text}\n\n{card}"
    return summary_text


VISION_FORMAT_PROMPT = (
    "\n\n=== IMAGE ANALYSIS MODE ===\n"
    "When medical images are uploaded, you switch to dedicated Image Analysis Mode.\n\n"
    "Image Response Structure:\n"
    "1. Warm, grounding introduction (explaining what images show, not diagnosing)\n"
    "2. High-level overview (2–3 sentences summarizing what the images show overall)\n"
    "3. Findings described by anatomical region with specific observations:\n"
    "   - Be specific: 'straightening or loss of normal neck curve' not just 'abnormalities'\n"
    "   - What you can clearly see\n"
    "   - What this typically means in everyday language\n"
    "4. Comparison across images or dates (when available) - explain what this tells us\n"
    "5. Plain-language explanation of meaning\n"
    "6. Clear urgent red flags (specific red flags, not generic advice)\n"
    "7. Optional follow-up offer\n\n"
    "Language Rules:\n"
    "• Descriptive, not diagnostic\n"
    "• Observation-based wording\n"
    "• Avoids instructional sections\n"
    "• Focuses on what is visible and commonly associated\n"
    "• Use: 'These images show...', 'You can clearly see...', 'What stands out...', 'This typically means...'\n"
    "• DO NOT use: Generic sections like 'Common signs:', 'What you can do:', 'When to seek help:'\n\n"
    "Multi-Image Handling: All images analyzed together. Cross-image comparison when relevant. Context preserved across the image set."
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
def extract_contextual_medical_insights_from_image(file_path: str, tone: str = "PlainClinical", lang: str = "en-US") -> str:

    image_b64 = preprocess_image_for_vision_api(file_path)
    data_uri = f"data:image/png;base64,{image_b64}"
    
    # Override FULL BREAKDOWN MODE for images - use image-specific format instead
    base_prompt = get_system_prompt(tone)
    # Remove the FULL BREAKDOWN MODE instructions and replace with image analysis format
    image_system_prompt = base_prompt.replace(
        "— FULL BREAKDOWN MODE: If there is ANY file/image, OR detailed description (multiple symptoms, history, or follow-up), "
        "always reply in sections, but do NOT write the word 'Introduction' as a heading:\n"
        "Start with a 1–2 sentence lead-in (no label).\n"
        "Common signs – 3–5 bullet points.\n"
        "What you can do – 3–5 bullet points.\n"
        "When to seek help – 2–4 bullet points.\n"
        "For clinicians – only if relevant, 1–4 concise points.\n"
        "Close with a warm conversational handoff (e.g., 'Is this close to what you're noticing?' or "
        "'Want me to suggest some next steps for your situation?').",
        "— IMAGE ANALYSIS MODE: When analyzing medical images, describe what you actually see in the images:\n"
        "Start with a warm introduction (explaining what images show, not diagnosing).\n"
        "Big picture first – brief 2–3 sentence summary of what the images show overall.\n"
        "Break down findings by anatomical region with specific observations (e.g., 'straightening or loss of normal neck curve' not just 'abnormalities').\n"
        "If dates are visible, compare findings across dates and explain what this tells us.\n"
        "Overall meaning in everyday language.\n"
        "When to seek urgent medical attention (specific red flags, not generic advice).\n"
        "Optional: Offer to help more with specific questions.\n"
        "Use: 'These images show...', 'You can clearly see...', 'What stands out...', 'This typically means...'\n"
        "DO NOT use generic sections like 'Common signs:', 'What you can do:', 'When to seek help:'"
    )
    system_prompt = image_system_prompt + VISION_FORMAT_PROMPT
    
    # Add language instruction
    system_prompt = _add_language_instruction(system_prompt, lang)

    # First pass: interpret the actual image - ACTUALLY ANALYZE, don't give instructions
    detailed_analysis_prompt = """Analyze this medical image. Describe what you actually see:

- Read any labels, dates, patient identifiers, and view types visible
- Identify the anatomical region shown
- Examine specific findings: alignment, curves, disc spaces, bone changes, hardware
- Be specific about what you observe (e.g., "loss of normal cervical curve" not just "abnormalities")
- Explain what these findings typically mean in plain language

Present as: "This image shows...", "You can see...", "What stands out...", "This typically means..." - describe what's actually visible, not generic advice."""

    resp = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.4,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": detailed_analysis_prompt},
                    {"type": "image_url", "image_url": {"url": data_uri}}
                ]
            },
        ],
        timeout=25.0,  # Explicit timeout to prevent Railway 502
    )
    raw = resp.choices[0].message.content.strip()

    # Second pass: humanize/tone polish while maintaining detailed observations
    rewrite = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt + "\n\nYou are analyzing and explaining what you see in the images. Present your findings as observations and explanations, not as instructions. Be specific about anatomical structures, dates, findings, and what they typically mean. Make it warm, detailed, and conversational - like walking someone through what the images show."},
            {"role": "user", "content": f"Rewrite this analysis to be warm and clear. Present it as 'Here's what I see' and 'This typically means' rather than 'You should do this' or 'Follow these steps'. Keep ALL the detailed observations, specific anatomical findings, date comparisons, and explanations. Make it feel like a knowledgeable medical explainer walking through the images:\n\n{raw}"},
        ],
        timeout=25.0,  # Explicit timeout to prevent Railway 502
    )
    return rewrite.choices[0].message.content.strip()

# =============================
#  MULTI-IMAGE VISION INTERPRETATION
# =============================
def extract_contextual_medical_insights_from_multiple_images(file_paths: list[str], tone: str = "PlainClinical", lang: str = "en-US") -> str:
    """
    Process multiple medical images together in a single API call.
    This allows the AI to see all images in context and provide comprehensive analysis.
    """
    if not file_paths:
        return ""
    
    if len(file_paths) == 1:
        # Fall back to single image processing for consistency
        return extract_contextual_medical_insights_from_image(file_paths[0], tone=tone, lang=lang)
    
    # Override FULL BREAKDOWN MODE for images - use image-specific format instead
    base_prompt = get_system_prompt(tone)
    # Remove the FULL BREAKDOWN MODE instructions and replace with image analysis format
    image_system_prompt = base_prompt.replace(
        "— FULL BREAKDOWN MODE: If there is ANY file/image, OR detailed description (multiple symptoms, history, or follow-up), "
        "always reply in sections, but do NOT write the word 'Introduction' as a heading:\n"
        "Start with a 1–2 sentence lead-in (no label).\n"
        "Common signs – 3–5 bullet points.\n"
        "What you can do – 3–5 bullet points.\n"
        "When to seek help – 2–4 bullet points.\n"
        "For clinicians – only if relevant, 1–4 concise points.\n"
        "Close with a warm conversational handoff (e.g., 'Is this close to what you're noticing?' or "
        "'Want me to suggest some next steps for your situation?').",
        "— IMAGE ANALYSIS MODE: When analyzing medical images, describe what you actually see in the images:\n"
        "Start with a warm introduction (explaining what images show, not diagnosing).\n"
        "Big picture first – brief 2–3 sentence summary of what the images show overall.\n"
        "Break down findings by anatomical region with specific observations (e.g., 'straightening or loss of normal neck curve' not just 'abnormalities').\n"
        "If dates are visible, compare findings across dates and explain what this tells us.\n"
        "Overall meaning in everyday language.\n"
        "When to seek urgent medical attention (specific red flags, not generic advice).\n"
        "Optional: Offer to help more with specific questions.\n"
        "Use: 'These images show...', 'You can clearly see...', 'What stands out...', 'This typically means...'\n"
        "DO NOT use generic sections like 'Common signs:', 'What you can do:', 'When to seek help:'"
    )
    system_prompt = image_system_prompt + VISION_FORMAT_PROMPT
    
    # Add language instruction
    system_prompt = _add_language_instruction(system_prompt, lang)
    
    # Enhanced multi-image analysis prompt - ACTUALLY ANALYZE, don't give instructions
    multi_image_analysis_prompt = f"""Analyze these {len(file_paths)} medical images. You are describing what you actually see in these specific images.

Start by reading any labels, dates, patient identifiers, and view types visible in the images. Then systematically examine:

1. What anatomical regions are shown (e.g., cervical spine, lumbar spine, hip, etc.)
2. Image orientation and view types (lateral, AP, etc.) - look for "L" markers
3. Specific findings you observe:
   - Alignment and curves (be specific: "straightening or loss of normal neck curve" not just "abnormalities")
   - Disc spaces (narrowing, height changes)
   - Bone changes (spurs, arthritis, etc.)
   - Any hardware or implants (describe what you see and position)
4. If dates are visible, compare findings across dates and explain what this tells us
5. What these findings typically mean in plain language
6. What symptoms patients with similar findings often experience

Present your analysis as: "These images show...", "You can clearly see...", "What stands out...", "The images from [date] compared to [date] show...", "This typically means...", "What this can cause..."

DO NOT use generic advice format like "Common signs:", "What you can do:", "When to seek help:" - instead, describe what's actually in these specific images and explain what it means.

Here are the images to analyze:"""
    
    # Prepare all images for the API call
    content_parts = [
        {"type": "text", "text": multi_image_analysis_prompt}
    ]
    
    # Add all images to the content with clear labeling
    for i, file_path in enumerate(file_paths, 1):
        try:
            image_b64 = preprocess_image_for_vision_api(file_path)
            data_uri = f"data:image/png;base64,{image_b64}"
            content_parts.append({
                "type": "text",
                "text": f"\n\n--- Image {i} of {len(file_paths)} ---"
            })
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": data_uri}
            })
        except Exception as e:
            log.warning(f"Failed to process image {i}: {e}")
            continue
    
    if len(content_parts) == 1:  # Only the text prompt, no images processed
        return "Failed to process the provided images."
    
    # First pass: interpret all images together
    # Limit to 2 images per batch to avoid timeout (Railway has ~30s HTTP limit)
    MAX_IMAGES_PER_BATCH = 2
    if len(file_paths) > MAX_IMAGES_PER_BATCH:
        # Process in batches of 2 and combine
        log.info(f"Processing {len(file_paths)} images in batches of {MAX_IMAGES_PER_BATCH} to avoid timeout")
        batch_summaries = []
        for batch_start in range(0, len(file_paths), MAX_IMAGES_PER_BATCH):
            batch_paths = file_paths[batch_start:batch_start + MAX_IMAGES_PER_BATCH]
            try:
                log.info(f"Processing batch {batch_start//MAX_IMAGES_PER_BATCH + 1} ({len(batch_paths)} images)")
                if len(batch_paths) == 1:
                    batch_summary = extract_contextual_medical_insights_from_image(batch_paths[0], tone=tone, lang=lang)
                else:
                    batch_summary = extract_contextual_medical_insights_from_multiple_images(batch_paths, tone=tone, lang=lang)
                batch_summaries.append(f"**Batch {batch_start//MAX_IMAGES_PER_BATCH + 1} ({len(batch_paths)} images):**\n{batch_summary}")
            except Exception as e:
                log.error(f"Batch {batch_start//MAX_IMAGES_PER_BATCH + 1} failed: {e}")
                # Fallback: try individual processing for this batch
                for i, file_path in enumerate(batch_paths, 1):
                    try:
                        summary = extract_contextual_medical_insights_from_image(file_path, tone=tone, lang=lang)
                        batch_summaries.append(f"**Image {batch_start + i}:**\n{summary}")
                    except Exception:
                        batch_summaries.append(f"**Image {batch_start + i}:**\n(Unable to process this image)")
                continue
        
        if batch_summaries:
            combined = "\n\n---\n\n".join(batch_summaries)
            if len(file_paths) > MAX_IMAGES_PER_BATCH:
                return f"I've analyzed {len(file_paths)} images in batches. Here's what I found:\n\n{combined}"
            return combined
        else:
            return "Failed to process any of the provided images. Please try with fewer images or check the file formats."
    
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.4,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_parts}
            ],
            timeout=25.0,  # Explicit timeout to prevent Railway 502
        )
        raw = resp.choices[0].message.content.strip()
    except Exception as e:
        log.error(f"Multi-image vision API call failed: {e}")
        # Fallback: process images individually and combine
        individual_summaries = []
        for file_path in file_paths:
            try:
                summary = extract_contextual_medical_insights_from_image(file_path, tone=tone, lang=lang)
                individual_summaries.append(summary)
            except Exception:
                continue
        if individual_summaries:
            raw = "\n\n".join([f"Image {i+1}:\n{summary}" for i, summary in enumerate(individual_summaries)])
        else:
            return "Failed to process any of the provided images. The images may be too large or in an unsupported format."
    
    # Second pass: humanize/tone polish while maintaining structured detail
    try:
        rewrite = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt + "\n\nYou are analyzing and describing what you see in these specific images. Structure your response as:\n1. Warm introduction (explaining what images show, not diagnosing)\n2. 'Big picture first' - brief summary\n3. Break down by anatomical region with specific observations\n4. Compare dates if visible\n5. Overall meaning in everyday language\n6. When to seek urgent attention (specific red flags)\n\nUse: 'These images show...', 'You can clearly see...', 'What stands out...', 'This typically means...' NOT generic advice sections like 'Common signs:', 'What you can do:', 'When to seek help:'"},
                {"role": "user", "content": f"Rewrite this analysis to match the desired format. Start with a warm intro, then 'Big picture first', then break down findings by region being SPECIFIC about what's visible. Use 'These images show...', 'You can clearly see...', 'What stands out...' NOT generic advice. Keep ALL detailed observations, specific anatomical findings, date comparisons. Make it feel like walking through what's actually in these images:\n\n{raw}"},
            ],
        )
        return rewrite.choices[0].message.content.strip()
    except Exception as e:
        log.warning(f"Multi-image rewrite failed, using raw response: {e}")
        return raw

# =============================
#  SUMMARIZE (PDF/DOCX/TXT/IMG)
# =============================
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
import os, tempfile, traceback, logging

log = logging.getLogger(__name__)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def summarize_medical_record(request):
    uploaded_file = request.FILES.get("file")
    tone = normalize_tone(request.data.get("tone") or request.session.get("tone") or "PlainClinical")
    care_setting = norm_setting(request.data.get("care_setting"))
    request.session["tone"] = tone
    request.session["care_setting"] = care_setting


    if not uploaded_file:
        return Response({"message": "Please attach a file to continue."}, status=400)

    file_name = (uploaded_file.name or "").lower()
    base = get_system_prompt(tone)
    system_prompt = get_setting_prompt(base, care_setting)


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
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

            # Save to DB
            MedicalSummary.objects.create(
                user=request.user,
                uploaded_filename=uploaded_file.name,
                tone=tone,
                raw_text="(Image file)",
                summary=summary,
                care_setting=care_setting,
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
            raw_text = uploaded_file.read().decode("utf-8", errors="ignore")
        else:
            return Response({
                "message": "That file type isn’t supported yet. Please upload a PDF, DOCX, TXT, or an image (JPG/PNG/HEIC/WEBP)."
            }, status=400)  # 415 is also fine; 400 keeps it simple for clients

        if not (raw_text or "").strip():
            return Response({
                "message": "We couldn’t read content from that file. Try a clearer scan or a different format."
            }, status=400)

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

    except Exception:
        # Log privately; keep user-facing copy calm and neutral
        log.exception("summarize_medical_record unexpected exception")
        return Response({
            "message": "Hi! Our system is busy right now due to a lot of users — please try again in a few minutes."
        }, status=503)  # 503 Service Unavailable fits the “busy” story

# =============================
#     CHAT (TEXT + FILES)
# =============================
# myApp/views_chat.py   (or merge into your existing views.py)

import logging
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import ChatSession

# If these are elsewhere, import from your modules
# from .llm import client, get_system_prompt, normalize_tone, _classify_mode, summarize_single_file
# from .utils import _now_ts

log = logging.getLogger(__name__)


# ---------- helpers ----------

def _now_iso():
    return timezone.now().isoformat()

def _trim_history(msgs, keep=200):
    return msgs if len(msgs) <= keep else msgs[-keep:]

def _ensure_session_for_user(user, tone, lang, first_user_msg=None, session_id=None):
    """
    Reuse session if id belongs to user; otherwise create a new one.
    """
    if session_id:
        try:
            s = ChatSession.objects.get(id=session_id, user=user, archived=False)
            updates = []
            if s.tone != tone:
                s.tone = tone; updates.append("tone")
            if s.lang != lang:
                s.lang = lang; updates.append("lang")
            if updates:
                s.updated_at = timezone.now(); updates.append("updated_at")
                s.save(update_fields=updates)
            return s, False
        except ChatSession.DoesNotExist:
            pass

    title = (first_user_msg or "New chat").strip()[:120] if first_user_msg else "New chat"
    s = ChatSession.objects.create(user=user, title=title, tone=tone, lang=lang)
    return s, True


# ---------- sessions: list & detail (for sidebar) ----------

def _row(s: ChatSession):
    return {
        "id": s.id,
        "title": s.title or "Untitled",
        "tone": s.tone or "PlainClinical",
        "lang": s.lang or "en-US",
        "archived": s.archived,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_chat_sessions(request):
    rows = (
        ChatSession.objects
        .filter(user=request.user, archived=False)
        .order_by("-updated_at")[:200]
    )
    return JsonResponse([_row(r) for r in rows], safe=False)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_chat_session(request, session_id: int):
    try:
        s = ChatSession.objects.get(id=session_id, user=request.user, archived=False)
    except ChatSession.DoesNotExist:
        return JsonResponse({"detail": "Not found"}, status=404)
    return JsonResponse({**_row(s), "messages": s.messages or []})


# ---------- clear soft memory + sticky id (used by your New Chat button) ----------

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def clear_session(request):
    for k in ["latest_summary","chat_history","nm_last_mode","nm_last_short_msg","nm_last_ts"]:
        request.session.pop(k, None)
    request.session.pop("active_chat_session_id", None)  # <- important
    request.session.modified = True
    return JsonResponse({"ok": True})

# views_chat.py  (add this next to your other session views)
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.forms.models import model_to_dict
from .models import ChatSession

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_chat_session(request):
    """
    Create an empty ChatSession and make it the active one.
    """
    # Create the row with the minimum required fields
    s = ChatSession.objects.create(user=request.user)

    # If your model has optional fields like title/tone/lang, set them safely:
    # (No-ops if those fields don't exist)
    try:
        if hasattr(s, "title") and not s.title:
            s.title = "New chat"
        if hasattr(s, "messages") and s.messages is None:
            s.messages = []
        s.save()
    except Exception:
        pass

    # Make it server-sticky so the next send reuses this session
    request.session["active_chat_session_id"] = s.id
    request.session.modified = True

    return JsonResponse({"session_id": s.id})


# --- AI title helpers ---

import os, re
from django.utils import timezone

def _clean_title(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "")).strip()
    s = s.replace("\n", " ").replace("\r", " ")
    return s

def _derive_title(user_message: str = "", files=None, reply: str = "", max_len: int = 80) -> str:
    """Heuristic fallback: user text → filenames → assistant reply."""
    if user_message:
        txt = _clean_title(user_message)
        m = re.split(r"(?<=[.!?])\s+", txt, maxsplit=1)
        title = m[0] if m else txt
        return title[:max_len]

    files = files or []
    if files:
        names = []
        for f in files[:2]:
            base = os.path.splitext(getattr(f, "name", "file"))[0]
            names.append(base[:40])
        extra = len(files) - 2
        label = " & ".join(names) + (f" (+{extra} more)" if extra > 0 else "")
        return label[:max_len]

    if reply:
        return _clean_title(reply)[:max_len]

    return "New chat"

def _ai_title(user_message: str, files, reply: str, lang: str = "en-US", max_len: int = 80) -> str:
    """
    Ask the model for a concise, PHI-safe title. Falls back to _derive_title on any hiccup.
    """
    try:
        # Prepare a compact context
        fnames = []
        for f in files or []:
            name = getattr(f, "name", "")
            if name:
                fnames.append(os.path.splitext(name)[0][:60])
        files_hint = ", ".join(fnames[:3])

        system = (
            "You name chat threads.\n"
            "Rules: 3–6 words • Title Case • No emojis • No dates, names, or IDs • "
            "Use neutral, non-identifying phrasing • Be specific but short.\n"
            f"Write the title in the user's language: {lang}."
        )

        user = "Create a short title for this conversation.\n"
        if user_message:
            user += f"\nUser message: {user_message[:400]}"
        if files_hint:
            user += f"\nFiles: {files_hint}"
        if reply:
            user += f"\nAssistant reply (hint): {reply[:400]}"

        # Use a lightweight model if you have it; otherwise gpt-4o is fine
        resp = client.chat.completions.create(
            model="gpt-4o-mini",  # change to your smallest available title-friendly model
            temperature=0.2,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        raw = (resp.choices[0].message.content or "").strip()
        # Keep it tight + safe
        title = _clean_title(raw)[:max_len]
        # Basic guardrails
        if not title or title.lower() in ("new chat", "untitled"):
            raise ValueError("weak title")
        # Nuke obvious PHI-ish tokens (very light heuristic)
        if re.search(r"\b(MRN|SSN|Account|#\d{3,})\b", title, re.I):
            raise ValueError("contains id-like token")
        return title
    except Exception:
        return _derive_title(user_message=user_message, files=files, reply=reply, max_len=max_len)


VALID_FAITH_SETTINGS = {"general", "christian", "muslim", "hindu", "buddhist", "jewish"}

def norm_faith_setting(val: Optional[str]) -> str:
    v = (val or "general").lower().strip()
    return v if v in VALID_FAITH_SETTINGS else "general"

def get_faith_prompt(base_prompt: str, faith_setting: str) -> str:
    """
    Append faith setting context. Matches Faith Mode behavior rules from design system.
    Medical facts remain primary; spiritual elements are optional and gentle.
    """
    if faith_setting == "christian":
        extra = (
            "Faith Setting: Christian\n"
            "Medical facts remain primary. When appropriate, you may close with a short Bible verse or prayer of comfort. "
            "Always ask permission to continue spiritual guidance."
        )
    elif faith_setting == "muslim":
        extra = (
            "Faith Setting: Muslim\n"
            "Medical facts remain primary. Frame with compassion; you may include a short dua or Quran verse if appropriate. "
            "Always ask permission to continue spiritual guidance."
        )
    elif faith_setting == "hindu":
        extra = (
            "Faith Setting: Hindu\n"
            "Medical facts remain primary. Offer gentle health guidance; you may weave in wisdom from the Bhagavad Gita or Hindu teachings. "
            "Always ask permission to continue spiritual guidance."
        )
    elif faith_setting == "buddhist":
        extra = (
            "Faith Setting: Buddhist\n"
            "Medical facts remain primary. Respond calmly, you may include mindful phrases or teachings from the Dharma. "
            "Always ask permission to continue spiritual guidance."
        )
    elif faith_setting == "jewish":
        extra = (
            "Faith Setting: Jewish\n"
            "Medical facts remain primary. You may close with a short line of hope or wisdom from Jewish tradition. "
            "Always ask permission to continue spiritual guidance."
        )
    else:  # general
        extra = (
            "Faith Setting: General\n"
            "Medical facts remain primary. Keep tone faith-friendly, spiritual, and encouraging without a specific tradition. "
            "Always ask permission to continue spiritual guidance."
        )

    return f"{base_prompt}\n\nFaith context: {extra}"

# ---------- main: send_chat (db persistence + sticky session) ----------

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def send_chat(request):
    raw_tone = request.data.get("tone") or request.session.get("tone") or "PlainClinical"
    tone = normalize_tone(raw_tone)
    care_setting = norm_setting(request.data.get("care_setting") or request.session.get("care_setting"))
    request.session["tone"] = tone
    faith_setting = None
    care_setting = None
    if tone in ("Clinical", "Caregiver"):
        care_setting = norm_setting(
            request.data.get("care_setting") or request.session.get("care_setting")
        )
        request.session["care_setting"] = care_setting
        request.session.pop("faith_setting", None)

    elif tone == "Faith":
        faith_setting = norm_faith_setting(
            request.data.get("faith_setting") or request.session.get("faith_setting")
        )
        request.session["faith_setting"] = faith_setting
        request.session.pop("care_setting", None)

    else:
        request.session.pop("care_setting", None)
        request.session.pop("faith_setting", None)

    # --- Language
    lang = request.data.get("lang")
    if request.user.is_authenticated:
        from .models import Profile
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if lang:
            profile.language = lang
            profile.save()
        else:
            lang = profile.language or "en-US"
    else:
        lang = lang or "en-US"

    # --- System prompt
    base_prompt = get_system_prompt(tone)

    if tone == "Faith" and faith_setting:
        system_prompt = get_faith_prompt(base_prompt, faith_setting)
    elif tone in ("Clinical", "Caregiver"):
        system_prompt = get_setting_prompt(base_prompt, care_setting)
    else:
        system_prompt = base_prompt
    
    # --- Add language instruction to system prompt
    system_prompt = _add_language_instruction(system_prompt, lang)



    # --- Inputs
    user_message = (request.data.get("message") or "").strip()
    files = request.FILES.getlist("files[]")
    if not files and "file" in request.FILES:
        files = [request.FILES["file"]]
    
    # Validate file count
    if len(files) > MAX_FILES_PER_UPLOAD:
        return JsonResponse({
            "reply": f"Too many files. Maximum {MAX_FILES_PER_UPLOAD} files allowed per upload.",
            "error": "MAX_FILES_EXCEEDED"
        }, status=400)
    
    has_files = bool(files)

    # --- Mode header
    mode, topic_hint = _classify_mode(user_message, has_files, request.session)
    header = f"ResponseMode: {mode}" + (f"\nTopicHint: {topic_hint}" if topic_hint else "")

    # --- Decide persistence
    use_db = request.user.is_authenticated
    session_obj = None

    # 🔑 STICKY: prefer payload id, else the server-sticky id
    incoming_session_id = request.data.get("session_id")
    sticky_session_id = request.session.get("active_chat_session_id")
    chosen_session_id = incoming_session_id or sticky_session_id

    # --- Build initial chat_history (DB vs guest)
    if use_db:
        session_obj, _created = _ensure_session_for_user(
            request.user, tone, lang,
            first_user_msg=user_message or ("[attachments]" if has_files else "New chat"),
            session_id=chosen_session_id
        )
        # remember sticky id on server
        request.session["active_chat_session_id"] = session_obj.id
        request.session.modified = True

        chat_history = []
        for m in (session_obj.messages or []):
            r, c = m.get("role"), m.get("content")
            if r and c is not None:
                chat_history.append({"role": r, "content": c})
        if not any(m.get("role") == "system" and str(m.get("content","")).startswith("ResponseMode:") for m in chat_history):
            chat_history.insert(0, {"role": "system", "content": header})
        if not any(m.get("role") == "system" and base_prompt in m.get("content","") for m in chat_history):
            chat_history.insert(0, {"role": "system", "content": system_prompt})
    else:
        summary_context = request.session.get("latest_summary", "")
        chat_history = request.session.get(
            "chat_history",
            [{"role": "system", "content": system_prompt}, {"role": "system", "content": header}],
        )
        if not any(m.get("role") == "system" and str(m.get("content", "")).startswith("ResponseMode:") for m in chat_history):
            chat_history.insert(1, {"role": "system", "content": header})

    # --- Process files → combined_context
    # Separate images from other files
    image_files = []
    other_files = []
    for f in files:
        fname_lower = f.name.lower()
        if fname_lower.endswith(ALLOWED_IMAGE_EXTS):
            image_files.append(f)
        else:
            other_files.append(f)
    
    combined_sections = []
    
    # Process images: in batches of 2-3 to avoid timeout
    # For 5+ images, process in batches of 2-3 and combine
    if len(image_files) >= 5:
        # Process in batches of 2 to stay under timeout
        log.info(f"Processing {len(image_files)} images in batches of 2 to avoid timeout")
        batch_size = 2
        for batch_start in range(0, len(image_files), batch_size):
            batch_files = image_files[batch_start:batch_start + batch_size]
            try:
                # Save batch to temp files
                batch_paths = []
                temp_paths_to_cleanup = []
                for img_file in batch_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(img_file.name)[1]) as tmp:
                        for chunk in img_file.chunks():
                            tmp.write(chunk)
                        temp_path = tmp.name
                    
                    # Try to save to user media
                    stored_path = None
                    try:
                        if request.user.is_authenticated:
                            with open(temp_path, 'rb') as temp_file:
                                from django.core.files import File
                                django_file = File(temp_file, name=img_file.name)
                                stored_path = _save_copy_to_user_media(request, django_file, img_file.name)
                    except Exception:
                        pass
                    
                    if stored_path and stored_path.exists():
                        batch_paths.append(str(stored_path))
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass
                    else:
                        batch_paths.append(temp_path)
                        temp_paths_to_cleanup.append(temp_path)
                
                # Process batch
                if len(batch_paths) == 1:
                    batch_summary = extract_contextual_medical_insights_from_image(batch_paths[0], tone=tone, lang=lang)
                else:
                    batch_summary = extract_contextual_medical_insights_from_multiple_images(batch_paths, tone=tone, lang=lang)
                
                # Combine filenames
                batch_names = [f.name for f in batch_files]
                combined_sections.append(f"{', '.join(batch_names)}\n{batch_summary}")
                
                # Cleanup temp files
                for tmp_path in temp_paths_to_cleanup:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                        
            except Exception as e:
                log.error(f"Batch {batch_start//batch_size + 1} failed: {e}")
                # Fallback: process individually for this batch
                for img_file in batch_files:
                    try:
                        fname, summary = summarize_single_file(
                            img_file, tone=tone, system_prompt=system_prompt, user=request.user, request=request,
                        )
                        combined_sections.append(f"{fname}\n{summary}")
                    except Exception:
                        combined_sections.append(f"{img_file.name}\n(Unable to process this image)")
    elif len(image_files) >= 2:
        # Process all images together for better context understanding
        image_paths = []
        temp_paths_to_cleanup = []
        
        try:
            for img_file in image_files:
                # Save to temp file first (file objects can only be read once)
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(img_file.name)[1]) as tmp:
                    for chunk in img_file.chunks():
                        tmp.write(chunk)
                    temp_path = tmp.name
                
                # Try to save a copy to user media (read from temp file)
                stored_path = None
                try:
                    if request is not None and request.user.is_authenticated:
                        # Reopen the temp file to save a copy
                        with open(temp_path, 'rb') as temp_file:
                            # Create a file-like object for _save_copy_to_user_media
                            from django.core.files import File
                            django_file = File(temp_file, name=img_file.name)
                            stored_path = _save_copy_to_user_media(request, django_file, img_file.name)
                except Exception:
                    pass
                
                # Use stored path if available, otherwise use temp path
                if stored_path and stored_path.exists():
                    image_paths.append(str(stored_path))
                    # Only cleanup temp if we successfully stored it
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                else:
                    image_paths.append(temp_path)
                    temp_paths_to_cleanup.append(temp_path)
            
            # Process all images together
            multi_image_summary = extract_contextual_medical_insights_from_multiple_images(
                image_paths, tone=tone, lang=lang
            )
            
            # Create a combined filename label
            image_names = [f.name for f in image_files[:3]]
            if len(image_files) > 3:
                image_names.append(f"... and {len(image_files) - 3} more")
            combined_sections.append(f"{', '.join(image_names)}\n{multi_image_summary}")
            
            # Save individual summaries to DB if user is authenticated
            if request.user.is_authenticated:
                for img_file in image_files:
                    try:
                        MedicalSummary.objects.create(
                            user=request.user,
                            uploaded_filename=img_file.name,
                            tone=tone,
                            raw_text="(Image file via chat - part of multi-image analysis)",
                            summary=multi_image_summary,  # Same summary for all as they were analyzed together
                        )
                    except Exception:
                        pass
        
        finally:
            # Cleanup temp files
            for tmp_path in temp_paths_to_cleanup:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
    
    elif len(image_files) == 1:
        # Single image - use existing single file processing
        # Note: summarize_single_file will use the system_prompt which already includes language instruction
        fname, summary = summarize_single_file(
            image_files[0], tone=tone, system_prompt=system_prompt, user=request.user, request=request,
        )
        combined_sections.append(f"{fname}\n{summary}")
    
    # Process non-image files individually
    # Note: summarize_single_file will use the system_prompt which already includes language instruction
    for f in other_files:
        fname, summary = summarize_single_file(
            f, tone=tone, system_prompt=system_prompt, user=request.user, request=request,
        )
        combined_sections.append(f"{fname}\n{summary}")
    
    combined_context = "\n\n".join(combined_sections).strip()

    # --- Case: only files
    if files and not user_message:
        reply_text = combined_context or "I couldn’t read any useful content from the attachments."
        if use_db:
            msgs = session_obj.messages or []
            if not msgs:
                msgs.extend([
                    {"role": "system", "content": system_prompt, "ts": _now_iso()},
                    {"role": "system", "content": header,         "ts": _now_iso()},
                ])
            msgs.append({"role": "user", "content": "(New attachments uploaded)", "ts": _now_iso(), "meta": {"has_files": True}})
            msgs.append({"role": "assistant", "content": reply_text, "ts": _now_iso()})
            
            try:
                current = (getattr(session_obj, "title", "") or "").strip().lower()
                if current in ("", "new chat", "untitled"):
                    ai_name = _ai_title(user_message="", files=files, reply=reply_text, lang=lang)
                    if ai_name:
                        session_obj.title = ai_name
            except Exception:
                # fall back quietly
                if not getattr(session_obj, "title", None):
                    session_obj.title = _derive_title(user_message="", files=files, reply=reply_text)
                
            session_obj.messages = _trim_history(msgs, keep=200)
            session_obj.updated_at = timezone.now()
            session_obj.save(update_fields=["messages", "updated_at"])
            return JsonResponse({"reply": reply_text, "session_id": session_obj.id}, status=(200 if combined_context else 400))
        else:
            request.session["latest_summary"] = combined_context or summary_context
            request.session["chat_history"] = [
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": header},
                {"role": "user",   "content": f"(Here’s the latest medical context):\n{combined_context or summary_context}"},
            ]
            request.session["nm_last_mode"] = "FULL"
            request.session["nm_last_short_msg"] = ""
            request.session["nm_last_ts"] = _now_ts()
            request.session.modified = True
            return JsonResponse({"reply": reply_text}, status=(200 if combined_context else 400))

    # --- No input at all
    if not files and not user_message:
        return JsonResponse({"reply": "Hmm… I didn’t catch that. Can you try again?"})

    # --- Prepare context for model call
    if combined_context:
        chat_history = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": header},
            {"role": "user",   "content": f"(Here’s the latest medical context):\n{combined_context}"},
        ]
        if not use_db:
            request.session["latest_summary"] = combined_context
    else:
        if not use_db:
            summary_context = request.session.get("latest_summary", "")
            if summary_context and all("(Here’s the" not in m.get("content", "") for m in chat_history if m.get("role") == "user"):
                chat_history.append({"role": "user", "content": f"(Here’s the medical context):\n{summary_context}"})

    # --- Add user message to model history
    chat_history.append({"role": "user", "content": user_message})

    # --- Persist user turn pre-model (DB)
    if use_db:
        msgs = session_obj.messages or []
        if not msgs:
            msgs.extend([
                {"role": "system", "content": system_prompt, "ts": _now_iso()},
                {"role": "system", "content": header,         "ts": _now_iso()},
            ])
        if combined_context:
            msgs.append({
                "role": "user",
                "content": f"(Here’s the latest medical context):\n{combined_context}",
                "ts": _now_iso(),
                "meta": {"context": "files"},
            })
        msgs.append({"role": "user", "content": user_message, "ts": _now_iso()})

        if not session_obj.title:
            session_obj.title = (user_message or "New chat")[:120]
        session_obj.tone = tone
        session_obj.lang = lang

        session_obj.messages = _trim_history(msgs, keep=200)
        session_obj.updated_at = timezone.now()
        session_obj.save(update_fields=["messages", "updated_at", "title", "tone", "lang"])

    # --- Call the model (OPTIMIZED: Single pass instead of two-pass for faster responses)
    try:
        # Single optimized call with balanced temperature for both accuracy and warmth
        # The system_prompt already includes tone instructions, so we don't need a second pass
        reply = client.chat.completions.create(
            model="gpt-4o", 
            temperature=0.5,  # Balanced between accuracy (0.3) and creativity (0.6)
            messages=chat_history,
        ).choices[0].message.content.strip()

        if use_db:
            msgs = session_obj.messages or []
            msgs.append({"role":"assistant","content":reply,"ts":_now_iso()})

            # 🔹 Auto-title if placeholder
            try:
                current = (getattr(session_obj, "title", "") or "").strip().lower()
                if current in ("", "new chat", "untitled"):
                    ai_name = _ai_title(user_message=user_message, files=files, reply=reply, lang=lang)
                    if ai_name:
                        session_obj.title = ai_name
            except Exception:
                if not getattr(session_obj, "title", None):
                    session_obj.title = _derive_title(user_message=user_message, files=files, reply=reply)

            session_obj.messages = _trim_history(msgs, keep=200)
            session_obj.updated_at = timezone.now()
            session_obj.save(update_fields=["messages","updated_at","title"])
        else:
            chat_history.append({"role": "assistant", "content": reply})
            request.session["chat_history"] = chat_history[-10:]
            if mode == "QUICK":
                request.session["nm_last_mode"] = "QUICK"
                request.session["nm_last_short_msg"] = user_message
            else:
                request.session["nm_last_mode"] = mode
                request.session["nm_last_short_msg"] = ""
            request.session["nm_last_ts"] = _now_ts()
            request.session.modified = True

        return JsonResponse({"reply": reply, "session_id": getattr(session_obj, "id", None)})

    except Exception as e:
        log.exception("send_chat failed")
        error_msg = str(e).lower()
        # Check for timeout-related errors
        if "timeout" in error_msg or "502" in error_msg or "gateway" in error_msg:
            return JsonResponse(
                {
                    "reply": "The image analysis is taking longer than expected. Please try with fewer images (5 or less) or try again in a moment.",
                    "error": "TIMEOUT"
                },
                status=504,  # Gateway Timeout
            )
        return JsonResponse(
            {
                "reply": "Sorry, something went wrong while processing your request. Please try again with fewer images or contact support if this persists.",
                "error": "PROCESSING_ERROR"
            },
            status=500,
        )

# --- ChatSession actions: rename / archive toggle / delete --------------------
import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import ChatSession


def _owned_session(request, pk: int) -> ChatSession:
    return get_object_or_404(ChatSession, id=pk, user=request.user)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat_session_rename(request, pk: int):
    """
    POST { "title": "New title" }
    """
    s = _owned_session(request, pk)
    try:
        payload = request.data or json.loads(request.body or "{}")
    except json.JSONDecodeError:
        payload = {}

    title = (payload.get("title") or "").strip()
    if not title:
        return JsonResponse({"ok": False, "error": "Title is required."}, status=400)

    s.title = title[:120]
    s.updated_at = timezone.now()
    s.save(update_fields=["title", "updated_at"])
    return JsonResponse({"ok": True, "id": s.id, "title": s.title})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat_session_archive(request, pk: int):
    """
    Toggle archive OR set explicitly.
    Accepts optional JSON: { "archived": true|false }
    """
    s = _owned_session(request, pk)
    try:
        payload = request.data or json.loads(request.body or "{}")
    except json.JSONDecodeError:
        payload = {}

    if "archived" in payload:
        s.archived = bool(payload.get("archived"))
    else:
        s.archived = not bool(s.archived)

    s.updated_at = timezone.now()
    s.save(update_fields=["archived", "updated_at"])

    # If archiving the active session, clear sticky id so next send makes a new one
    if s.archived and request.session.get("active_chat_session_id") == s.id:
        request.session.pop("active_chat_session_id", None)
        request.session.modified = True

    return JsonResponse({"ok": True, "id": s.id, "archived": s.archived})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat_session_delete(request, pk: int):
    """
    Hard delete the session.
    """
    s = _owned_session(request, pk)
    s.delete()

    if request.session.get("active_chat_session_id") == pk:
        request.session.pop("active_chat_session_id", None)
        request.session.modified = True

    return JsonResponse({"ok": True, "id": pk, "deleted": True})


# =============================
#  SMART SUGGESTIONS / Q&A
# =============================
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def smart_suggestions(request):
    summary = request.data.get("summary", "") or request.session.get("latest_summary", "")
    tone = normalize_tone(request.data.get("tone") or request.session.get("tone") or "PlainClinical")
    

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
            {"role": "system", "content": get_system_prompt(tone)},

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
    tone = normalize_tone(request.data.get("tone") or request.session.get("tone") or "PlainClinical")

    if not question:
        return JsonResponse({"answer": "Could you repeat the question? I want to make sure I understand."})

    prompt = f"Context:\n{summary}\n\nAnswer clearly, warmly, and confidently:\nQ: {question}"
    raw = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.6,
        messages=[
            {"role": "system", "content": get_system_prompt(tone)},

            {"role": "user", "content": prompt},
        ],
    ).choices[0].message.content.strip()

    polish = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        messages=[
            {"role": "system", "content": get_system_prompt(tone)},

            {"role": "user", "content": f"Rewrite warmly, clearly, and confidently:\n\n{raw}"},
        ],
    ).choices[0].message.content.strip()

    return JsonResponse({"answer": polish})


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
# views.py
from django.contrib.auth import login, authenticate
from django.urls import reverse
from django.db import transaction



def signup_view(request):
    if request.method == "POST":
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            user = form.save()

            profile, _ = Profile.objects.get_or_create(user=user)
            profile.signup_ip = get_client_ip(request)
            profile.signup_country = getattr(request, "country_code", None) or profile.signup_country
            
            # Process referral code (if entered)
            referral_code_entered = form.cleaned_data.get("referral_code", "").strip().upper()
            if referral_code_entered:
                # Try to find the user who owns this referral code
                try:
                    referring_profile = Profile.objects.select_related('user').get(
                        personal_referral_code=referral_code_entered
                    )
                    profile.referred_by = referring_profile.user
                except Profile.DoesNotExist:
                    # Invalid referral code - silently ignore (don't block signup)
                    pass
            
            # Generate personal referral code for new user
            from .utils import generate_referral_code
            if not profile.personal_referral_code:
                profile.personal_referral_code = generate_referral_code()
            
            profile.save()
            
            # Track user signup
            from .models import UserSignup
            UserSignup.objects.get_or_create(
                user=user,
                defaults={
                    'ip_address': get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'referer': request.META.get('HTTP_REFERER', '')
                }
            )

            raw_pw = (
                form.cleaned_data.get("password1")
                or form.cleaned_data.get("password")
                or form.cleaned_data.get("new_password1")
            )
            auth_user = None
            if raw_pw:
                auth_user = authenticate(
                    request,
                    username=getattr(user, "username", user.email),
                    password=raw_pw,
                )

            if auth_user is not None:
                login(request, auth_user)
            else:
                user.backend = settings.AUTHENTICATION_BACKENDS[0]
                login(request, user)

            # Build a fully-qualified login link for the email
            login_url = request.build_absolute_uri(reverse("login"))

            # Send welcome email AFTER the transaction commits (so user exists for sure)
            def _send():
                first_name = (getattr(user, "first_name", "") or user.get_username() or "there")
                send_welcome_email(user.email, first_name, login_url)

            transaction.on_commit(_send)

            resp = redirect("dashboard")
            resp.set_cookie("just_logged_in", "1", max_age=60, samesite="Lax", path="/")
            return resp
    else:
        form = CustomSignupForm()
    return render(request, "signup.html", {
        "form": form,
        "GOOGLE_OAUTH_ENABLED": getattr(settings, 'GOOGLE_OAUTH_ENABLED', True)
    })




# =============================
#       DASHBOARD + SETTINGS
# =============================
from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    care = norm_setting(request.GET.get("care_setting"))
    qs = MedicalSummary.objects.filter(user=request.user).order_by("-created_at")
    if request.GET.get("care_setting"):  # apply only if explicitly filtered
        qs = qs.filter(care_setting=care)
    return render(request, "dashboard.html", {"summaries": qs, "selected_care": care})

@login_required
def new_dashboard(request):
    """Premium dashboard with upgraded UI/UX"""
    try:
        care = norm_setting(request.GET.get("care_setting"))
        qs = MedicalSummary.objects.filter(user=request.user).order_by("-created_at")
        if request.GET.get("care_setting"):  # apply only if explicitly filtered
            qs = qs.filter(care_setting=care)
        context = {
            "summaries": qs,
            "selected_care": care,
        }
        return render(request, "new_dashboard.html", context)
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        error_trace = traceback.format_exc()
        logger.error(f"Error in new_dashboard: {str(e)}\n{error_trace}")
        # Re-raise to see the actual error in logs
        raise


@login_required
def analytics_dashboard(request):
    """Enhanced analytics dashboard with comprehensive metrics"""
    from django.db.models import Count, Sum, Q, Avg, Max, Min
    from django.utils import timezone
    from datetime import timedelta, datetime
    from .models import Visitor, UserSignup, UserSignin, PageView, Session, Event
    from .analytics_utils import categorize_referer
    from django.contrib.auth import get_user_model
    import json
    
    User = get_user_model()
    
    # Only staff can view analytics
    if not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You do not have permission to view analytics.")
    
    # Date range handling
    now = timezone.now()
    today = now.date()
    
    # Get date range from request
    period = request.GET.get('period', '7d')
    if period == 'today':
        start_date = today
        end_date = today
        days = 1
    elif period == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = start_date
        days = 1
    elif period == '7d':
        start_date = today - timedelta(days=7)
        end_date = today
        days = 7
    elif period == '30d':
        start_date = today - timedelta(days=30)
        end_date = today
        days = 30
    elif period == 'custom':
        try:
            start_date = datetime.strptime(request.GET.get('start', ''), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.GET.get('end', ''), '%Y-%m-%d').date()
            days = (end_date - start_date).days + 1
        except:
            start_date = today - timedelta(days=7)
            end_date = today
            days = 7
    else:
        start_date = today - timedelta(days=7)
        end_date = today
        days = 7
    
    # Comparison period (previous period)
    comparison_enabled = request.GET.get('compare', 'false') == 'true'
    period_days = (end_date - start_date).days + 1
    prev_start_date = start_date - timedelta(days=period_days)
    prev_end_date = start_date - timedelta(days=1)
    
    # Base querysets for current period
    visitor_qs = Visitor.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    pageview_qs = PageView.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    signup_qs = UserSignup.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    signin_qs = UserSignin.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    
    # Use the comprehensive analytics calculation module
    from .analytics_views import get_analytics_data
    
    context = get_analytics_data(
        request=request,
        start_date=start_date,
        end_date=end_date,
        prev_start_date=prev_start_date if comparison_enabled else None,
        prev_end_date=prev_end_date if comparison_enabled else None,
        comparison_enabled=comparison_enabled
    )
    
    # Add period and comparison info
    context['period'] = period
    context['today'] = today
    
    # Add totals for reference
    from .models import Visitor, PageView, UserSignup, UserSignin
    context['total_visitors_all_time'] = Visitor.objects.count()
    context['total_page_views_all_time'] = PageView.objects.count()
    context['total_signups_all_time'] = UserSignup.objects.count()
    context['total_users_all_time'] = User.objects.count()
    context['total_signins_all_time'] = UserSignin.objects.filter(success=True).count()
    
    # Serialize data for JavaScript (convert QuerySets to lists)
    import json
    from django.core.serializers.json import DjangoJSONEncoder
    
    # Convert to JSON strings for safe template rendering
    context['daily_stats_json'] = json.dumps(context.get('daily_stats', []), cls=DjangoJSONEncoder)
    context['prev_daily_stats_json'] = json.dumps(context.get('prev_daily_stats', []), cls=DjangoJSONEncoder)
    context['device_breakdown_json'] = json.dumps(list(context.get('device_breakdown', [])), cls=DjangoJSONEncoder)
    context['browser_breakdown_json'] = json.dumps(list(context.get('browser_breakdown', [])), cls=DjangoJSONEncoder)
    context['os_breakdown_json'] = json.dumps(list(context.get('os_breakdown', [])), cls=DjangoJSONEncoder)
    context['traffic_sources_json'] = json.dumps(context.get('traffic_sources', []), cls=DjangoJSONEncoder)
    context['popular_pages_json'] = json.dumps(list(context.get('popular_pages', [])), cls=DjangoJSONEncoder)
    context['hourly_activity_json'] = json.dumps(context.get('hourly_activity', []), cls=DjangoJSONEncoder)
    
    # Serialize user list for JavaScript
    context['user_list_json'] = json.dumps(context.get('user_list', []), cls=DjangoJSONEncoder)
    
    # Serialize medical analytics data
    context['daily_summaries_json'] = json.dumps(context.get('daily_summaries', []), cls=DjangoJSONEncoder)
    context['daily_chat_sessions_json'] = json.dumps(context.get('daily_chat_sessions', []), cls=DjangoJSONEncoder)
    context['care_setting_breakdown_json'] = json.dumps(list(context.get('care_setting_breakdown', [])), cls=DjangoJSONEncoder)
    context['tone_breakdown_json'] = json.dumps(list(context.get('tone_breakdown', [])), cls=DjangoJSONEncoder)
    context['profession_breakdown_json'] = json.dumps(list(context.get('profession_breakdown', [])), cls=DjangoJSONEncoder)
    context['language_breakdown_json'] = json.dumps(list(context.get('language_breakdown', [])), cls=DjangoJSONEncoder)
    context['satisfaction_metrics_json'] = json.dumps(context.get('satisfaction_metrics', {}), cls=DjangoJSONEncoder)
    
    return render(request, 'analytics/dashboard_premium.html', context)


@login_required
def analytics_export(request):
    """Export analytics data as PDF or CSV"""
    from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
    from django.db.models import Count
    from .models import Visitor, PageView, UserSignup, UserSignin
    from .analytics_views import get_analytics_data
    from django.utils import timezone
    from datetime import timedelta, datetime
    import csv
    import json
    
    # Only staff can export
    if not request.user.is_staff:
        return HttpResponseForbidden("You do not have permission to export analytics.")
    
    export_format = request.GET.get('export', 'csv')
    
    # Handle user export
    if 'users_' in export_format:
        format_type = export_format.replace('users_', '')
        return export_users_list(request, format_type)
    period = request.GET.get('period', '7d')
    today = timezone.now().date()
    
    # Handle user export
    if 'users_' in export_format:
        format_type = export_format.replace('users_', '')
        return export_users_list(request, format_type)
    
    # Determine date range
    if period == 'today':
        start_date = today
        end_date = today
    elif period == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = start_date
    elif period == '7d':
        start_date = today - timedelta(days=7)
        end_date = today
    elif period == '30d':
        start_date = today - timedelta(days=30)
        end_date = today
    elif period == 'custom':
        try:
            start_date = datetime.strptime(request.GET.get('start', ''), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.GET.get('end', ''), '%Y-%m-%d').date()
        except:
            start_date = today - timedelta(days=7)
            end_date = today
    else:
        start_date = today - timedelta(days=7)
        end_date = today
    
    # Get analytics data
    from .analytics_views import get_analytics_data
    data = get_analytics_data(
        request=request,
        start_date=start_date,
        end_date=end_date,
        comparison_enabled=False
    )
    
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="analytics_{start_date}_{end_date}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Period', f'{start_date} to {end_date}'])
        writer.writerow(['Unique Visitors', data['unique_visitors']])
        writer.writerow(['Page Views', data['page_views']])
        writer.writerow(['Signups', data['signups']])
        writer.writerow(['Signins', data['signins']])
        writer.writerow(['Active Users', data['active_users']])
        writer.writerow(['Conversion Rate', f"{data['conversion_rate']}%"])
        writer.writerow(['Bounce Rate', f"{data['bounce_rate']}%"])
        writer.writerow([])
        writer.writerow(['Daily Stats'])
        writer.writerow(['Date', 'Visitors', 'Page Views', 'Signups', 'Signins'])
        for stat in data['daily_stats']:
            writer.writerow([
                stat['date'],
                stat['visitors'],
                stat['page_views'],
                stat['signups'],
                stat['signins']
            ])
        
        return response
    
    elif export_format == 'pdf':
        # For PDF, we'll return a simple HTML that can be printed/saved as PDF
        # In production, you'd use a library like WeasyPrint or ReportLab
        from django.template.loader import render_to_string
        html_content = render_to_string('analytics/export_pdf.html', {
            'data': data,
            'start_date': start_date,
            'end_date': end_date,
            'exported_at': timezone.now()
        })
        response = HttpResponse(html_content, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename="analytics_report_{start_date}_{end_date}.html"'
        return response
    
    elif export_format == 'daily':
        # Daily report - comprehensive one-page summary
        from django.template.loader import render_to_string
        html_content = render_to_string('analytics/daily_report.html', {
            'data': data,
            'date': today,
            'exported_at': timezone.now()
        })
        response = HttpResponse(html_content, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename="daily_report_{today}.html"'
        return response
    
    return JsonResponse({'error': 'Invalid export format'}, status=400)


@login_required
def export_users_list(request, format_type='csv'):
    """Export user list as CSV or PDF"""
    from django.http import HttpResponse, HttpResponseForbidden
    from django.contrib.auth import get_user_model
    from .models import Profile
    from django.db.models import Count, Max, Q
    import csv
    from django.utils import timezone
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"Export users called with format_type: {format_type}")
    
    # Only staff can export
    if not request.user.is_staff:
        return HttpResponseForbidden("You do not have permission to export user data.")
    
    User = get_user_model()
    
    # Get all users with stats
    users = User.objects.select_related('profile').annotate(
        total_summaries=Count('summaries', distinct=True),
        total_chat_sessions=Count('chatsession', distinct=True),
        total_signins=Count('signin_records', filter=Q(signin_records__success=True), distinct=True),
        last_signin=Max('signin_records__created_at', filter=Q(signin_records__success=True))
    ).order_by('-date_joined')
    
    logger.info(f"Processing export with format_type: '{format_type}' (type: {type(format_type)})")
    
    # Debug: Print what we received
    print(f"DEBUG: format_type = '{format_type}', type = {type(format_type)}")
    
    if format_type == 'csv':
        logger.info("Generating CSV export")
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="users_export_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Username', 'Email', 'Display Name', 'First Name', 'Last Name',
            'Profession', 'Language', 'Signup Date', 'Last Login', 'Total Signins',
            'Total Summaries', 'Total Chat Sessions', 'Status', 'Is Staff',
            'Signup IP', 'Signup Country', 'Last Login IP', 'Last Login Country'
        ])
        
        for user in users:
            profile = getattr(user, 'profile', None)
            writer.writerow([
                user.username,
                user.email,
                profile.display_name if profile else '',
                user.first_name or '',
                user.last_name or '',
                profile.profession if profile else '',
                profile.language if profile else 'en-US',
                user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else '',
                user.total_signins or 0,
                user.total_summaries or 0,
                user.total_chat_sessions or 0,
                'Active' if user.is_active else 'Inactive',
                'Yes' if user.is_staff else 'No',
                profile.signup_ip if profile else '',
                profile.signup_country if profile else '',
                profile.last_login_ip if profile else '',
                profile.last_login_country if profile else '',
            ])
        
        return response
    
    elif format_type == 'pdf':
        print("DEBUG: Entering PDF generation block")
        logger.info("PDF format detected, attempting PDF generation with ReportLab")
        try:
            from reportlab.lib.pagesizes import letter, A4
            logger.info("ReportLab imported successfully")
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from io import BytesIO
            
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
            elements = []
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#059669'),
                spaceAfter=30,
                alignment=1  # Center
            )
            
            # Title
            title = Paragraph("User Directory Export", title_style)
            elements.append(title)
            
            # Summary info
            summary_text = f"<b>Export Date:</b> {timezone.now().strftime('%B %d, %Y at %H:%M')}<br/>"
            summary_text += f"<b>Total Users:</b> {users.count()}<br/>"
            summary_text += f"<b>Users in Report:</b> {min(users.count(), 100)}"
            summary = Paragraph(summary_text, styles['Normal'])
            elements.append(summary)
            elements.append(Spacer(1, 20))
            
            # Table data
            data = [['Username', 'Email', 'Name', 'Profession', 'Signup', 'Status', 'Activity']]
            
            # Limit to 100 users for PDF
            users_list = list(users[:100])
            
            for user in users_list:
                profile = getattr(user, 'profile', None)
                
                # Safely get display name
                display_name = ''
                if profile:
                    display_name = profile.display_name or ''
                
                # Build name safely
                first_part = display_name or user.first_name or user.username
                last_part = user.last_name or ''
                name = f"{first_part} {last_part}".strip()
                if len(name) > 20:
                    name = name[:17] + "..."
                
                activity = f"S:{user.total_summaries or 0} C:{user.total_chat_sessions or 0} L:{user.total_signins or 0}"
                status = 'Active' if user.is_active else 'Inactive'
                if user.is_staff:
                    status += ' (Staff)'
                
                # Safely get profession
                profession = '—'
                if profile and profile.profession:
                    profession = profile.profession[:15]
                
                data.append([
                    user.username[:18] if len(user.username) > 18 else user.username,
                    user.email[:25] if len(user.email) > 25 else user.email,
                    name[:20] if len(name) > 20 else name,
                    profession,
                    user.date_joined.strftime('%Y-%m-%d'),
                    status[:15],
                    activity
                ])
            
            # Create table
            table = Table(data, colWidths=[1*inch, 2*inch, 1.5*inch, 1*inch, 0.8*inch, 1*inch, 1.2*inch])
            table.setStyle(TableStyle([
                # Header row
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#374151')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                
                # Data rows
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ]))
            
            elements.append(table)
            
            # Footer
            elements.append(Spacer(1, 20))
            footer_text = f"Generated on {timezone.now().strftime('%B %d, %Y at %H:%M')} | NeuroMed AI Analytics Dashboard"
            footer = Paragraph(footer_text, styles['Normal'])
            elements.append(footer)
            
            # Build PDF
            doc.build(elements)
            
            # Get PDF value
            pdf = buffer.getvalue()
            buffer.close()
            
            # Create response
            logger.info(f"PDF generated successfully, size: {len(pdf)} bytes")
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="users_export_{timezone.now().strftime("%Y%m%d")}.pdf"'
            return response
            
        except ImportError as e:
            # ReportLab not installed
            logger.error(f"ReportLab import error: {str(e)}")
            from django.http import HttpResponse
            return HttpResponse(f"ReportLab not installed. Error: {str(e)}. Please install: pip install reportlab", status=500)
        except Exception as e:
            # If PDF generation fails, show error with details
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"PDF export error: {str(e)}")
            logger.error(error_details)
            from django.http import HttpResponse
            # Return error message so user knows what went wrong
            return HttpResponse(
                f"PDF generation failed: {str(e)}\n\nDetails:\n{error_details}", 
                content_type='text/plain',
                status=500
            )
    
    logger.warning(f"Invalid export format: '{format_type}'. Expected 'csv' or 'pdf'")
    return HttpResponse(f"Invalid export format: '{format_type}'. Expected 'csv' or 'pdf'.", status=400)


@login_required
def get_user_settings(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    # Construct full name from first_name + last_name, fallback to display_name, then username
    full_name = None
    if request.user.first_name or request.user.last_name:
        full_name = f"{request.user.first_name or ''} {request.user.last_name or ''}".strip()
    
    return JsonResponse({
        "display_name": profile.display_name or "",
        "first_name": request.user.first_name or "",
        "last_name": request.user.last_name or "",
        "full_name": full_name or profile.display_name or request.user.username,
        "profession": profile.profession or "",
        "language": profile.language,  # ✅ include language
    })

@login_required
def update_user_settings(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            profile, _ = Profile.objects.get_or_create(user=request.user)
            profile.display_name = data.get("display_name", profile.display_name)
            profile.profession = data.get("profession", profile.profession)

            if "language" in data:  # ✅ allow updates
                profile.language = data["language"]

            profile.save()
            return JsonResponse({"status": "success"})
        except Exception:
            return JsonResponse({
                "message": "Hi! Our system is busy right now. Please try again in a few minutes."
            }, status=500)

    return JsonResponse({
        "message": "Hi! That action isn’t available right now. Please try again in a few minutes."
    }, status=400)



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


# views.py

def summarize_single_file(file_obj, tone: str, system_prompt: str, user=None, request=None) -> tuple[str, str]:
    """
    Returns (filename, summary) for an uploaded file (image or doc).
    Saves a permanent copy of images to per-user media, indexes the filename,
    and saves to DB if user is authenticated.
    """
    fname = file_obj.name
    lower = fname.lower()

    # ---- Images → vision
    if lower.endswith(ALLOWED_IMAGE_EXTS):
        stored_path = None

        # Try to persist a copy into per-user media + index it for later filename lookups
        try:
            if request is not None:
                stored_path = _save_copy_to_user_media(request, file_obj, fname)  # returns a Path
        except Exception:
            traceback.print_exc()
            stored_path = None

        # If we have a stored copy, analyze that; otherwise fall back to a temp file
        if stored_path and stored_path.exists():
            tmp_path = str(stored_path)
            cleanup_after = False
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(lower)[1]) as tmp:
                for chunk in file_obj.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            cleanup_after = True

        try:
            summary = extract_contextual_medical_insights_from_image(tmp_path, tone=tone)
        finally:
            if cleanup_after:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        if user and getattr(user, "is_authenticated", False):
            MedicalSummary.objects.create(
                user=user,
                uploaded_filename=fname,
                tone=tone,
                raw_text="(Image file via chat)",
                summary=summary,
            )
        return fname, summary

    # ---- Docs → extract + summarize
    if lower.endswith(".pdf"):
        raw_text = extract_text_from_pdf(file_obj)
    elif lower.endswith(".docx"):
        raw_text = extract_text_from_docx(file_obj)
    elif lower.endswith(".txt"):
        raw_text = file_obj.read().decode("utf-8", errors="ignore")
    else:
        return fname, "Unsupported file format."

    summary = summarize_text_block(raw_text, system_prompt)

    if user and getattr(user, "is_authenticated", False):
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


# views.py — Password Reset (Resend-powered)
import random
import string
import logging

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import SetPasswordForm
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.html import escape

# If your send_via_resend lives in myApp/emailer.py, keep this import.
# If you defined send_via_resend in the same file, remove this import.
from myApp.emailer import send_via_resend

log = logging.getLogger(__name__)
User = get_user_model()

# ---------- Config ----------
OTP_TTL_SECONDS     = 10 * 60  # 10 minutes
OTP_RESEND_SECONDS  = 60       # 60s cooldown between resends
OTP_PREFIX          = "pwreset:"
OTP_ATTEMPTS_PREFIX = "pwreset_attempts:"
OTP_RESEND_PREFIX   = "pwreset_resend:"
DASHBOARD_URL       = "/dashboard"  # or reverse('dashboard')

def _otp_key(email):          return f"{OTP_PREFIX}{email}"
def _otp_attempts_key(email): return f"{OTP_ATTEMPTS_PREFIX}{email}"
def _otp_resend_key(email):   return f"{OTP_RESEND_PREFIX}{email}"
def _generate_code():         return "".join(random.choices(string.digits, k=6))

# ---------- Forms ----------
class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()
    def clean_email(self):
        return self.cleaned_data["email"].lower().strip()  # normalize, no enumeration

class OTPForm(forms.Form):
    email = forms.EmailField()
    code = forms.CharField(min_length=6, max_length=6)
    def clean_email(self): return self.cleaned_data["email"].lower().strip()
    def clean_code(self):  return self.cleaned_data["code"].strip()

class OTPSetPasswordForm(SetPasswordForm):
    """Uses Django validators; fields: new_password1/new_password2"""
    pass

# ---------- Helpers ----------
def mask_email(addr: str) -> str:
    try:
        name, domain = addr.split("@", 1)
        nm = name[0] + "•" * max(len(name) - 2, 1) + name[-1]
        d0, *rest = domain.split(".")
        d0m = d0[0] + "•" * max(len(d0) - 2, 1) + d0[-1]
        return nm + "@" + ".".join([d0m] + rest)
    except Exception:
        return addr

def send_otp_email(email: str, code: str, ttl_minutes: int = 10) -> bool:
    """Send the OTP using Resend. Returns True/False; never raises."""
    subject = "Your NeuroMed AI verification code"
    text_content = (
        f"Your NeuroMed AI verification code is: {code}\n"
        f"This code expires in {ttl_minutes} minutes.\n"
        "If you didn’t request this, ignore this email. For your security, never share this code."
    )
    html_content = f"""
    <div style="font-family:Inter,Segoe UI,Arial,sans-serif;max-width:520px;margin:0 auto;padding:24px;background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;">
      <div style="text-align:center;margin-bottom:8px;">
        <div style="font-size:18px;font-weight:700;color:#1B5A8E;">NeuroMed AI</div>
        <div style="font-size:12px;color:#6b7280;">Secure verification</div>
      </div>
      <p style="font-size:14px;color:#374151;margin:16px 0;">
        Here’s your one-time verification code. It expires in {ttl_minutes} minutes.
      </p>
      <div style="text-align:center;margin:20px 0;">
        <div style="display:inline-block;letter-spacing:6px;font-weight:700;font-size:28px;color:#111827;background:#f0fdfa;border:1px solid #99f6e4;border-radius:10px;padding:12px 18px;">
          {escape(code)}
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
    try:
        return bool(send_via_resend(
            to=email,
            subject=subject,
            text=text_content,
            html=html_content,
            fail_silently=True,  # don’t break flow; we log errors inside the wrapper
        ))
    except Exception:
        log.exception("send_otp_email failed")
        return False

# ---------- Views ----------
def forgot_password(request):
    """
    Step 1: Ask for email, generate 6-digit OTP, store in cache, email it.
    Only sends OTP if the email exists in the database.
    """
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            
            # Check if user exists in database
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                messages.error(request, "This email address isn't registered. Please check your email or sign up for a new account.")
                return render(request, "account/password_forgot.html", {"form": form})
            
            code  = _generate_code()

            # Save OTP + attempts in cache
            cache.set(_otp_key(email), {"code": code, "ts": timezone.now().isoformat()}, OTP_TTL_SECONDS)
            cache.set(_otp_attempts_key(email), 0, OTP_TTL_SECONDS)

            # Session continuity (masked display for the UI)
            request.session["pwreset_email"] = email
            request.session["pwreset_email_masked"] = mask_email(email)
            request.session.set_expiry(15 * 60)
            request.session.modified = True

            # Send email via Resend (never 500s)
            try:
                send_otp_email(email, code, ttl_minutes=OTP_TTL_SECONDS // 60)
            except Exception:
                pass  # ultra-defensive; wrapper already swallows & logs

            messages.success(request, f"We've sent a 6-digit code to {mask_email(email)}. Please check your inbox (and spam folder).")
            return redirect("password_otp")
    else:
        form = ForgotPasswordForm()

    return render(request, "account/password_forgot.html", {"form": form})

def resend_otp(request):
    """Resend the active code (or mint a new one if expired) with a small cooldown."""
    if request.method != "POST":
        return redirect("password_otp")

    # Use email from session if available, otherwise from POST
    email = request.session.get("pwreset_email") or (request.POST.get("email") or "").lower().strip()
    if not email:
        messages.error(request, "Your session expired. Please start over.")
        return redirect("password_forgot")

    # Check if user exists in database
    user = User.objects.filter(email__iexact=email).first()
    if not user:
        messages.error(request, "This email address isn't registered. Please check your email or sign up for a new account.")
        return redirect("password_forgot")

    cooldown_key = _otp_resend_key(email)
    if cache.get(cooldown_key):
        remaining = cache.ttl(cooldown_key) or OTP_RESEND_SECONDS
        messages.error(request, f"Please wait {remaining} seconds before requesting another code.")
        return redirect("password_otp")

    data = cache.get(_otp_key(email))
    if data is None:
        code = _generate_code()
        cache.set(_otp_key(email), {"code": code, "ts": timezone.now().isoformat()}, OTP_TTL_SECONDS)
        cache.set(_otp_attempts_key(email), 0, OTP_TTL_SECONDS)
    else:
        code = data["code"]

    try:
        send_otp_email(email, code, ttl_minutes=OTP_TTL_SECONDS // 60)
    except Exception:
        pass

    cache.set(cooldown_key, True, OTP_RESEND_SECONDS)
    messages.success(request, f"We've sent another code to {mask_email(email)}. Please check your inbox.")
    return redirect("password_otp")

def verify_otp(request):
    """
    Step 2: Verify the code. If valid, allow setting new password.
    Never reveal whether the email is registered.
    """
    # Get email from session if available
    session_email = request.session.get("pwreset_email")
    session_email_masked = request.session.get("pwreset_email_masked")
    
    if request.method == "POST":
        # Merge POST data with session email if email not in POST
        post_data = request.POST.copy()
        if session_email and not post_data.get("email"):
            post_data["email"] = session_email
        form = OTPForm(post_data)
        
        if form.is_valid():
            email = form.cleaned_data["email"]
            code  = form.cleaned_data["code"]

            data     = cache.get(_otp_key(email))
            attempts = cache.get(_otp_attempts_key(email), 0)

            if data is None:
                messages.error(request, "This code has expired. Please click 'Resend code' to get a new one, or start over.")
                # Keep form with email pre-filled
                if session_email:
                    form = OTPForm(initial={"email": session_email})
                return render(request, "account/password_otp.html", {
                    "form": form,
                    "email_masked": session_email_masked
                })

            if attempts >= 5:
                messages.error(request, "Too many incorrect attempts. For security, please request a new code.")
                cache.delete(_otp_key(email))
                cache.delete(_otp_attempts_key(email))
                return redirect("password_forgot")

            if code != data.get("code"):
                remaining_attempts = 5 - (attempts + 1)
                cache.set(_otp_attempts_key(email), attempts + 1, OTP_TTL_SECONDS)
                if remaining_attempts > 0:
                    messages.error(request, f"Incorrect code. You have {remaining_attempts} attempt{'s' if remaining_attempts > 1 else ''} remaining.")
                else:
                    messages.error(request, "Incorrect code. Too many attempts. Please request a new code.")
                return render(request, "account/password_otp.html", {
                    "form": form,
                    "email_masked": session_email_masked
                })

            # OTP OK → clear and continue
            user = User.objects.filter(email__iexact=email).first()
            cache.delete(_otp_key(email))
            cache.delete(_otp_attempts_key(email))

            request.session["pwreset_email"] = email
            request.session["pwreset_email_masked"] = mask_email(email)
            request.session.set_expiry(15 * 60)
            request.session.modified = True

            if user:
                request.session["pwreset_user_id"] = user.id
                request.session.set_expiry(15 * 60)
                request.session.modified = True
                messages.success(request, "Code verified! Now create your new password.")
                return redirect("password_reset_otp")
            else:
                # User verified OTP but email not registered - suggest signup
                messages.info(request, "This email isn't registered with an account. Would you like to sign up instead?")
                # Clear session and redirect to signup
                request.session.pop("pwreset_email", None)
                request.session.pop("pwreset_email_masked", None)
                from django.urls import reverse
                return redirect(f"{reverse('signup')}?email={email}")
    else:
        # Pre-fill email from session
        if session_email:
            form = OTPForm(initial={"email": session_email})
        else:
            form = OTPForm()
            # If no session email, redirect to start
            messages.info(request, "Please enter your email to receive a reset code.")
            return redirect("password_forgot")

    return render(request, "account/password_otp.html", {
        "form": form,
        "email_masked": session_email_masked
    })

def reset_password(request):
    """
    Step 3: Set the new password (for verified sessions only).
    """
    user_id = request.session.get("pwreset_user_id")
    user    = User.objects.filter(id=user_id).first() if user_id else None
    email_masked = request.session.get("pwreset_email_masked")

    if request.method == "POST":
        if not user:
            messages.error(request, "Your reset session has expired. Please start over and request a new code.")
            return redirect("password_forgot")

        form = OTPSetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            login(request, user)
            # Clear all reset-related session data
            for k in ("pwreset_user_id", "pwreset_email", "pwreset_email_masked"):
                request.session.pop(k, None)
            messages.success(request, "Password updated successfully! You're now signed in.")
            return redirect(f"{DASHBOARD_URL}?changed=1")
    else:
        if not user:
            messages.error(request, "Your reset session has expired. Please start over and request a new code.")
            return redirect("password_forgot")
        form = OTPSetPasswordForm(user)

    return render(request, "account/password_reset_otp.html", {
        "form": form,
        "email_masked": email_masked
    })


# views.py
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")  # or your LOGOUT_REDIRECT_URL
# views.py (auth section)
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.urls import reverse_lazy
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# ⬇️ REMOVE the old EmailOrUsernameAuthenticationForm import
# from .forms import EmailOrUsernameAuthenticationForm

# ⬇️ USE the email-only form instead
from .forms import EmailAuthenticationForm

# myApp/views.py
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
import json

class WarmLoginView(DjangoLoginView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['GOOGLE_OAUTH_ENABLED'] = getattr(settings, 'GOOGLE_OAUTH_ENABLED', True)
        return context
    template_name = "login.html"
    redirect_authenticated_user = True
    success_url = reverse_lazy("dashboard")
    authentication_form = EmailAuthenticationForm

    def form_valid(self, form):
        resp = super().form_valid(form)
        try:
            user = self.request.user
            if user and user.is_authenticated:
                profile, _ = Profile.objects.get_or_create(user=user)
                profile.last_login_ip = get_client_ip(self.request)
                profile.last_login_country = getattr(self.request, "country_code", None) or profile.last_login_country
                profile.save()
                
                # Track successful signin
                from .models import UserSignin
                UserSignin.objects.create(
                    user=user,
                    ip_address=get_client_ip(self.request),
                    user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                    success=True
                )
        except Exception:
            # Don't block login if telemetry fails
            pass

        resp.set_cookie("just_logged_in", "1", max_age=60, samesite="Lax", path="/")
        return resp

    def get_success_url(self):
        """
        After login, respect ?next=… when present, otherwise go to success_url,
        without adding any extra query params like ?welcome=1.
        """
        return super().get_success_url() or str(self.success_url)

    def post(self, request, *args, **kwargs):
        # Handle API requests (JSON)
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                email = data.get('email')
                password = data.get('password')
                
                if not email or not password:
                    return JsonResponse({'error': 'Email and password required'}, status=400)
                
                # Authenticate user
                from django.contrib.auth import authenticate
                user = authenticate(request, username=email, password=password)
                
                if user and user.is_active:
                    from django.contrib.auth import login
                    login(request, user)
                    
                    # Update profile
                    try:
                        profile, _ = Profile.objects.get_or_create(user=user)
                        profile.last_login_ip = get_client_ip(request)
                        profile.last_login_country = getattr(request, "country_code", None) or profile.last_login_country
                        profile.save()
                        
                        # Track successful signin
                        from .models import UserSignin
                        UserSignin.objects.create(
                            user=user,
                            ip_address=get_client_ip(request),
                            user_agent=request.META.get('HTTP_USER_AGENT', ''),
                            success=True
                        )
                    except Exception:
                        pass
                    
                    # Return user data for iOS app
                    return JsonResponse({
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'date_joined': user.date_joined.isoformat(),
                        'last_login': user.last_login.isoformat() if user.last_login else None,
                        'is_active': user.is_active,
                        'is_staff': user.is_staff,
                        'is_superuser': user.is_superuser,
                        'profile': {
                            'profession': profile.profession,
                            'display_name': profile.display_name,
                            'language': profile.language,
                            'signup_ip': profile.signup_ip,
                            'last_login_ip': profile.last_login_ip,
                            'signup_country': profile.signup_country,
                            'last_login_country': profile.last_login_country,
                        } if hasattr(user, 'profile') else None
                    })
                else:
                    # Track failed login attempt
                    try:
                        from .models import UserSignin, User
                        from django.contrib.auth import get_user_model
                        User = get_user_model()
                        try:
                            failed_user = User.objects.get(email=email)
                            UserSignin.objects.create(
                                user=failed_user,
                                ip_address=get_client_ip(request),
                                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                                success=False
                            )
                        except User.DoesNotExist:
                            pass  # User doesn't exist, can't track
                    except Exception:
                        pass  # Don't block error response if tracking fails
                    
                    return JsonResponse({'error': 'Invalid credentials'}, status=401)
                    
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        
        # Handle regular form requests (web browser)
        return super().post(request, *args, **kwargs)

# In your views.py
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

@csrf_exempt
def api_login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')
            
            if not email or not password:
                return JsonResponse({'error': 'Email and password required'}, status=400)
            
            from django.contrib.auth import authenticate, login
            user = authenticate(request, username=email, password=password)
            
            if user and user.is_active:
                login(request, user)
                
                # Update profile
                try:
                    profile, _ = Profile.objects.get_or_create(user=user)
                    profile.last_login_ip = get_client_ip(request)
                    profile.last_login_country = getattr(request, "country_code", None) or profile.last_login_country
                    profile.save()
                    
                    # Track successful signin
                    from .models import UserSignin
                    UserSignin.objects.create(
                        user=user,
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        success=True
                    )
                except Exception:
                    pass
                
                return JsonResponse({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'date_joined': user.date_joined.isoformat(),
                    'last_login': user.last_login.isoformat() if user.last_login else None,
                    'is_active': user.is_active,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                })
            else:
                # Track failed login attempt
                try:
                    from .models import UserSignin, User
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    try:
                        failed_user = User.objects.get(email=email)
                        UserSignin.objects.create(
                            user=failed_user,
                            ip_address=get_client_ip(request),
                            user_agent=request.META.get('HTTP_USER_AGENT', ''),
                            success=False
                        )
                    except User.DoesNotExist:
                        pass  # User doesn't exist, can't track
                except Exception:
                    pass  # Don't block error response if tracking fails
                
                return JsonResponse({'error': 'Invalid credentials'}, status=401)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
    
# views.py (if you don’t already have these)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.http import JsonResponse

@api_view(["GET"])
@permission_classes([AllowAny])
def auth_status(request):
    return JsonResponse({"authenticated": bool(request.user.is_authenticated)})

from django.middleware.csrf import get_token
@api_view(["GET"])
@permission_classes([AllowAny])
def get_csrf_token(request):
    """
    Endpoint to get CSRF token for iOS/mobile apps.
    Returns the token in both cookie and response body.
    """
    csrf_token = get_token(request)
    return JsonResponse({
        "csrfToken": csrf_token,
        "detail": "CSRF cookie set"
    })

from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def track_event(request):
    # Accept JSON or form; do nothing (prevents 404s from navigator.sendBeacon)
    try:
        _ = request.data
    except Exception:
        pass
    return Response(status=204)


from django.shortcuts import render

def page_not_found_view(request, exception, template_name="404.html"):
    return render(request, template_name, status=404)

def server_error_view(request, template_name="500.html"):
    return render(request, template_name, status=500)

def service_unavailable_view(request, template_name="503.html"):
    resp = render(request, template_name, status=503)
    resp["Retry-After"] = "120"  # hint browsers/clients to retry after ~2 minutes
    return resp


from urllib.parse import urlencode
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.html import escape

from .forms import DemoRequestForm

# Renders the landing page with prefilled form + optional success modal
def landing(request):
    q = request.GET
    initial = {}

    # Prefill name/email if present
    if q.get("name"):
        initial["name"] = q.get("name").strip()
    if q.get("email"):
        initial["email"] = q.get("email").strip().lower()

    # Capture UTM params if they exist
    for key in ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"]:
        val = q.get(key)
        if val:
            initial[key] = val

    # Helpful for context on submit
    try:
        initial["website"] = request.build_absolute_uri(request.get_full_path())
    except Exception:
        initial["website"] = ""

    form = DemoRequestForm(initial=initial)

    # Flag to trigger the success modal on page load
    show_demo_modal = (q.get("demo") == "ok")

    return render(request, "landing.html", {
        "form": form,
        "show_demo_modal": show_demo_modal,
    })


# Handles the POST of the Django form in #demo
def book_demo(request):
    if request.method != "POST":
        return redirect("landing")

    form = DemoRequestForm(request.POST)
    if not form.is_valid():
        # Re-render landing with errors
        return render(request, "landing.html", {"form": form})

    data = form.cleaned_data

    # Compose email to *you* (goes to DEFAULT_FROM_EMAIL inbox)
    subject = f"[Neuromed Demo] {data.get('name')} — {data.get('company') or 'No company'}"
    to = [settings.DEFAULT_FROM_EMAIL]     # Change if you want another recipient list
    reply_to = [data["email"]]

    html_body = f"""
      <h2>New Demo Request</h2>
      <p><strong>Name:</strong> {escape(data.get('name') or '')}</p>
      <p><strong>Email:</strong> {escape(data.get('email') or '')}</p>
      <p><strong>Company/Clinic:</strong> {escape(data.get('company') or '')}</p>
      <p><strong>Phone:</strong> {escape(data.get('phone') or '')}</p>
      <p><strong>Use Case:</strong> {escape(data.get('use_case') or '')}</p>
      <hr/>
      <p><strong>Website:</strong> {escape(data.get('website') or '')}</p>
      <p><strong>utm_source:</strong> {escape(data.get('utm_source') or '')}</p>
      <p><strong>utm_medium:</strong> {escape(data.get('utm_medium') or '')}</p>
      <p><strong>utm_campaign:</strong> {escape(data.get('utm_campaign') or '')}</p>
      <p><strong>utm_term:</strong> {escape(data.get('utm_term') or '')}</p>
      <p><strong>utm_content:</strong> {escape(data.get('utm_content') or '')}</p>
    """
    text_body = (
        "New Demo Request\n"
        f"Name: {data.get('name')}\n"
        f"Email: {data.get('email')}\n"
        f"Company/Clinic: {data.get('company')}\n"
        f"Phone: {data.get('phone')}\n"
        f"Use Case: {data.get('use_case')}\n"
        "-----\n"
        f"Website: {data.get('website')}\n"
        f"utm_source: {data.get('utm_source')}\n"
        f"utm_medium: {data.get('utm_medium')}\n"
        f"utm_campaign: {data.get('utm_campaign')}\n"
        f"utm_term: {data.get('utm_term')}\n"
        f"utm_content: {data.get('utm_content')}\n"
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to,
        reply_to=reply_to,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)

    # Optional: confirmation to requester
    try:
        confirm_msg = EmailMultiAlternatives(
            subject="Thanks for booking a NeuroMed demo",
            body="Thanks! Our team will reach out shortly to coordinate a 20-minute demo.\n— NeuroMed AI",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[data["email"]],
        )
        confirm_msg.attach_alternative(
            f"<p>Hi {escape(data.get('name') or '')},</p>"
            f"<p>Thanks! Our team will reach out shortly to coordinate a 20-minute demo.</p>"
            f"<p>— NeuroMed AI</p>",
            "text/html"
        )
        confirm_msg.send(fail_silently=True)
    except Exception:
        pass

    # Redirect with a flag so the template shows the success modal.
    # (If you don't want name/email in the URL, remove them from params.)
    params = {
        "demo": "ok",
        "name": data.get("name", ""),
        "email": data.get("email", ""),
    }
    return redirect(f"{reverse('landing')}?{urlencode(params)}#calendar")


# emails.py (or wherever your email helpers live)
from django.utils.html import escape

def send_welcome_email(email: str, first_name: str, login_url: str) -> bool:
    subject = "Welcome to NeuroMed AI Beta – You’re Helping Shape the Future 🌿"

    # Plain text (fallback for clients that block HTML)
    text_content = f"""Hi {first_name},

Thank you for joining the NeuroMed AI Beta Testing Program! 💙

You’re helping us build a tool that makes healthcare simpler, kinder, and easier to understand.

Explore in beta:
• Plain Mode – easy-to-understand explanations
• Caregiver Mode – gentle, reassuring guidance
• Faith Mode – encouragement and scripture-based comfort
• Clinical Mode – structured, medical detail
• Multiple Languages – for diverse families

How to start:
1) Log in: {login_url}
2) Upload a medical record (PDF, Word, or text)
3) Choose your tone
4) Get your summary in seconds

“Write the vision and make it plain.” – Habakkuk 2:2

Your feedback is gold: hello@neuromedai.org

With gratitude,
The NeuroMed AI Team
"""

    # HTML version
    html_content = f"""
    <div style="font-family:Inter,Segoe UI,Arial,sans-serif;max-width:640px;margin:0 auto;padding:24px;background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;">
      <div style="text-align:center;margin-bottom:8px;">
        <div style="font-size:18px;font-weight:700;color:#1B5A8E;">NeuroMed AI</div>
        <div style="font-size:12px;color:#6b7280;">Welcome to the Beta</div>
      </div>

      <p style="font-size:14px;color:#374151;margin:16px 0;">
        Hi {escape(first_name)},</p>
      <p style="font-size:14px;color:#374151;margin:12px 0;">
        Thank you for joining the <strong>NeuroMed AI Beta Testing Program</strong>! 💙
        You’re stepping into the front row where technology meets compassion. By testing with us,
        you’re helping build a tool that makes healthcare simpler, kinder, and easier to understand.
      </p>

      <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:12px;padding:14px 16px;margin:16px 0;">
        <div style="font-weight:700;color:#111827;margin-bottom:6px;">What you can explore in beta:</div>
        <ul style="margin:8px 0 0 18px;color:#374151;font-size:14px;line-height:1.6;">
          <li><strong>Plain Mode</strong> – easy-to-understand explanations</li>
          <li><strong>Caregiver Mode</strong> – gentle, reassuring guidance</li>
          <li><strong>Faith Mode</strong> – encouragement and scripture-based comfort</li>
          <li><strong>Clinical Mode</strong> – structured, medical detail</li>
          <li><strong>Multiple Languages</strong> – breaking barriers for diverse families</li>
        </ul>
      </div>

      <div style="margin:18px 0;">
        <div style="font-weight:700;color:#111827;margin-bottom:6px;">How to get started:</div>
        <ol style="margin:8px 0 0 18px;color:#374151;font-size:14px;line-height:1.6;">
          <li>Log in to your dashboard → <a href="{escape(login_url)}" style="color:#0ea5e9;text-decoration:underline;">Login</a></li>
          <li>Upload a medical record (PDF, Word, or text)</li>
          <li>Choose your tone</li>
          <li>Get your summary in seconds</li>
        </ol>
      </div>

      <div style="text-align:center;margin:24px 0;">
        <a href="{escape(login_url)}"
           style="display:inline-block;background:#1B5A8E;color:#ffffff;text-decoration:none;padding:12px 18px;border-radius:10px;font-weight:700;">
          Start Now
        </a>
      </div>

      <div style="font-size:13px;color:#374151;margin:16px 0;">
        🌟 Beta Tester Trivia: “Compassion” comes from Latin <em>compati</em> — “to suffer with.”
        That’s the heart of NeuroMed AI—standing with families so no one feels lost in healthcare again.
      </div>

      <p style="font-size:13px;color:#374151;margin:16px 0;">
        During beta, you may notice small hiccups—that’s normal. Your feedback is gold. Share anytime at
        <a href="mailto:hello@neuromedai.org" style="color:#0ea5e9;text-decoration:underline;">hello@neuromedai.org</a>.
      </p>

      <blockquote style="margin:16px 0;padding:12px 14px;border-left:4px solid #d1fae5;background:#f0fdfa;color:#065f46;font-size:13px;">
        “Write the vision and make it plain.” – Habakkuk 2:2
      </blockquote>

      <p style="font-size:13px;color:#374151;margin:0;">With gratitude,<br/>The NeuroMed AI Team</p>
    </div>
    """

    try:
        return bool(send_via_resend(
            to=email,
            subject=subject,
            text=text_content,
            html=html_content,
            fail_silently=True,  # don’t block signup flow
        ))
    except Exception:
        log.exception("send_welcome_email failed")
        return False


# =============================
#       GOOGLE OAUTH
# =============================
import secrets
from urllib.parse import urlencode, parse_qs, urlparse
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.contrib.auth import get_user_model

User = get_user_model()

def google_oauth_login(request):
    """
    Initiates Google OAuth flow by redirecting to Google's authorization page.
    """
    # Check if Google OAuth is enabled
    if not getattr(settings, 'GOOGLE_OAUTH_ENABLED', True):
        return HttpResponseBadRequest("Google OAuth is currently disabled. Please use email/password signup.")
    
    google_client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)
    if not google_client_id:
        return HttpResponseBadRequest("Google OAuth is not configured. Please contact support.")
    
    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session['google_oauth_state'] = state
    request.session['google_oauth_next'] = request.GET.get('next', '/dashboard/')
    
    # Build clean redirect URI (force HTTPS in production, remove query params)
    callback_path = reverse('google_oauth_callback')
    
    # Get the host - check multiple sources for accuracy
    host = request.get_host()
    
    # Handle X-Forwarded-Host if behind proxy (Railway, etc.)
    if not settings.DEBUG:
        forwarded_host = request.META.get('HTTP_X_FORWARDED_HOST')
        if forwarded_host:
            host = forwarded_host.split(',')[0].strip()
    
    # Remove port if present
    if ':' in host:
        host = host.split(':')[0]
    
    # Normalize host - ensure www for production
    host = host.lower().strip()
    if not settings.DEBUG and host not in ('localhost', '127.0.0.1'):
        # For production, ensure www prefix
        if not host.startswith('www.'):
            host = f"www.{host}"
    
    # Build redirect URI - HARDCODE for production to match Google Console exactly
    if settings.DEBUG:
        # Development: dynamic based on request
        scheme = request.scheme
        port = request.get_port()
        if port and port not in (80, 443):
            redirect_uri = f"{scheme}://{host}:{port}{callback_path}"
        else:
            redirect_uri = f"{scheme}://{host}{callback_path}"
        # Remove any query parameters
        if '?' in redirect_uri:
            redirect_uri = redirect_uri.split('?')[0]
        redirect_uri = redirect_uri.rstrip('/') + '/'
    else:
        # Production: HARDCODE to match Google Console exactly
        # This eliminates any host detection or normalization issues
        redirect_uri = "https://www.neuromedai.org/auth/google/callback/"
    
    # Log for debugging - use print for Railway logs visibility
    import logging
    log = logging.getLogger(__name__)
    log.error(f"[GOOGLE_OAUTH] redirect_uri being sent: {redirect_uri}")
    print(f"[GOOGLE_OAUTH] redirect_uri being sent: {redirect_uri}", flush=True)
    params = {
        'client_id': google_client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'access_type': 'online',
        'prompt': 'select_account',
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return HttpResponseRedirect(auth_url)


def google_oauth_callback(request):
    """
    Handles Google OAuth callback and creates/logs in user.
    """
    # Verify state token
    state = request.GET.get('state')
    stored_state = request.session.pop('google_oauth_state', None)
    next_url = request.session.pop('google_oauth_next', '/dashboard/')
    
    if not state or state != stored_state:
        return HttpResponseBadRequest("Invalid state parameter. Please try again.")
    
    code = request.GET.get('code')
    if not code:
        error = request.GET.get('error', 'Unknown error')
        return HttpResponseBadRequest(f"OAuth error: {error}")
    
    google_client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)
    google_client_secret = getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', None)
    
    if not google_client_id or not google_client_secret:
        return HttpResponseBadRequest("Google OAuth is not configured.")
    
    # Exchange code for access token (build clean redirect URI - must match exactly)
    callback_path = reverse('google_oauth_callback')
    
    # Get the host - check multiple sources for accuracy (same logic as google_oauth_login)
    host = request.get_host()
    
    # Handle X-Forwarded-Host if behind proxy (Railway, etc.)
    if not settings.DEBUG:
        forwarded_host = request.META.get('HTTP_X_FORWARDED_HOST')
        if forwarded_host:
            host = forwarded_host.split(',')[0].strip()
    
    # Remove port if present
    if ':' in host:
        host = host.split(':')[0]
    
    # Normalize host - ensure www for production
    host = host.lower().strip()
    if not settings.DEBUG and host not in ('localhost', '127.0.0.1'):
        # For production, ensure www prefix
        if not host.startswith('www.'):
            host = f"www.{host}"
    
    # Build redirect URI - HARDCODE for production to match Google Console exactly
    if settings.DEBUG:
        # Development: dynamic based on request
        scheme = request.scheme
        port = request.get_port()
        if port and port not in (80, 443):
            redirect_uri = f"{scheme}://{host}:{port}{callback_path}"
        else:
            redirect_uri = f"{scheme}://{host}{callback_path}"
        # Remove any query parameters
        if '?' in redirect_uri:
            redirect_uri = redirect_uri.split('?')[0]
        redirect_uri = redirect_uri.rstrip('/') + '/'
    else:
        # Production: HARDCODE to match Google Console exactly
        # This eliminates any host detection or normalization issues
        redirect_uri = "https://www.neuromedai.org/auth/google/callback/"
    
    # Log for debugging - use print for Railway logs visibility
    import logging
    log = logging.getLogger(__name__)
    log.error(f"[GOOGLE_OAUTH_CALLBACK] redirect_uri: {redirect_uri}")
    print(f"[GOOGLE_OAUTH_CALLBACK] redirect_uri: {redirect_uri}", flush=True)
    token_data = {
        'code': code,
        'client_id': google_client_id,
        'client_secret': google_client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }
    
    try:
        token_response = requests.post(
            'https://oauth2.googleapis.com/token',
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10
        )
        token_response.raise_for_status()
        token_json = token_response.json()
        access_token = token_json.get('access_token')
        
        if not access_token:
            return HttpResponseBadRequest("Failed to obtain access token.")
        
        # Get user info from Google
        user_info_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10
        )
        user_info_response.raise_for_status()
        user_info = user_info_response.json()
        
        email = user_info.get('email')
        if not email:
            return HttpResponseBadRequest("Email not provided by Google.")
        
        # Get or create user (case-insensitive email lookup)
        email_lower = email.lower()
        user = User.objects.filter(email__iexact=email_lower).first()
        created = False
        
        if not user:
            # Create new user
            base_username = email_lower.split('@')[0]
            username = base_username
            # Ensure username is unique
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            user = User.objects.create(
                email=email_lower,
                username=username,
                first_name=user_info.get('given_name', ''),
                last_name=user_info.get('family_name', ''),
            )
            created = True
        
        # Update user info if they already exist
        if not created:
            if not user.first_name and user_info.get('given_name'):
                user.first_name = user_info.get('given_name')
            if not user.last_name and user_info.get('family_name'):
                user.last_name = user_info.get('family_name')
            user.save()
        
        # Create or update profile
        profile, _ = Profile.objects.get_or_create(user=user)
        if created:
            profile.signup_ip = get_client_ip(request)
            profile.signup_country = getattr(request, "country_code", None)
            # Generate referral code for new users
            from .utils import generate_referral_code
            if not profile.personal_referral_code:
                profile.personal_referral_code = generate_referral_code()
            
            # Track user signup
            from .models import UserSignup
            UserSignup.objects.get_or_create(
                user=user,
                defaults={
                    'ip_address': get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'referer': request.META.get('HTTP_REFERER', '')
                }
            )
            
            # Send welcome email for new users
            login_url = request.build_absolute_uri(reverse("login"))
            def _send():
                first_name = (getattr(user, "first_name", "") or user.get_username() or "there")
                send_welcome_email(user.email, first_name, login_url)
            transaction.on_commit(_send)
        
        # Log the user in
        user.backend = settings.AUTHENTICATION_BACKENDS[0]
        login(request, user)
        
        # Redirect to dashboard or next URL
        resp = redirect(next_url)
        resp.set_cookie("just_logged_in", "1", max_age=60, samesite="Lax", path="/")
        return resp
        
    except requests.RequestException as e:
        log.exception("Google OAuth error")
        return HttpResponseBadRequest(f"OAuth error: {str(e)}")
    except Exception as e:
        log.exception("Unexpected error in Google OAuth")
        return HttpResponseBadRequest(f"An error occurred: {str(e)}")
