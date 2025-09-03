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

ALLOWED_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".heic", ".webp")
USER_MEDIA_SUBDIR = getattr(settings, "USER_MEDIA_SUBDIR", "user_media")
SESSION_IMAGE_INDEX = "known_images"  # {lower_filename: relative_path_from_MEDIA_ROOT}
MAX_INDEXED_IMAGES = 100


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

def _resolve_indexed_image(request, filename: str) -> Path | None:
    idx = request.session.get(SESSION_IMAGE_INDEX, {})
    rel = idx.get(filename.lower())
    if not rel:
        return None
    p = Path(settings.MEDIA_ROOT) / rel
    return p if p.exists() else None

def _scan_user_media_for_name(user, filename: str) -> Path | None:
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
client = OpenAI()

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

def _parse_bilingual_code(t: str) -> str | None:
    # Accept forms like BilingualEsEn, BilingualFrEn, BilingualJaEn, etc.
    m = re.match(r"^Bilingual([A-Za-z]{2})En$", t or "")
    return m.group(1) if m else None


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


PROMPT_TEMPLATES = {
    "PlainClinical": (
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
        "You are NeuroMed, a comforting health companion. "
        "Speak gently, using Taglish warmth where helpful. "
        "Explain clearly, reassure kindly, and offer practical next steps. "
        "Always end by inviting the caregiver to share more about their concern."
    ),

    "Faith": (
        "You are NeuroMed, a faith-filled health companion. "
        "Provide clear medical explanations with hope and peace. "
        "When appropriate, close with a short Bible verse or brief prayer. "
        "Keep the tone open by asking if they’d like more guidance or encouragement."
    ),

    "Clinical": (
        "You are NeuroMed, a professional-grade medical assistant for clinicians. "
        "Be concise, precise, and correct in medical terminology. No fluff. "
        "Close with an offer for additional detail if needed (e.g., 'Want me to pull differential diagnoses?' or 'Need drug dosing ranges?')."
    ),

    "Bilingual": (
        "You are NeuroMed, a warm Taglish-speaking medical guide. "
        "Use natural Tagalog-English to make explanations crystal clear. "
        "End with a soft invitation to continue sharing, like 'Gusto mo bang dagdagan ang kwento mo?'"
    ),

    "Geriatric": (
        "You are NeuroMed, a geriatric-focused health companion. "
        "Be respectful, unhurried, and practical for older adults and their families. "
        "Watch for and address common geriatric issues: fall risk, frailty, polypharmacy, cognitive changes, "
        "continence, mobility, nutrition, advance care planning. "
        "Offer caregiver-friendly tips and gentle next steps (e.g., medication review, PT/OT, home safety, "
        "hearing/vision check, cognitive screening, goals-of-care discussion). "
        "If sensitive topics arise, suggest family huddles and shared decisions. "
        "End with a question that keeps the dialogue going, such as 'Would you like me to suggest some home adjustments?'"
    ),

    "EmotionalSupport": (
        "You are NeuroMed, an emotional support health companion. "
        "Your main role is to validate feelings, reduce fear, and provide clarity with compassion. "
        "Always begin by acknowledging emotions in a warm, human way. "
        "Keep language simple, reassuring, and kind, while still accurate. "
        "Offer one or two gentle next steps the person can take today. "
        "If there are urgent warning signs, highlight them briefly but calmly. "
        "Encourage self-kindness and remind the user they are not alone. "
        "Never provide diagnoses; instead, give comfort and safe guidance, "
        "and encourage professional care when needed. "
        "End with an open invitation like, 'Would you like me to walk with you through this a bit more?'"
    ),
}


def normalize_tone(tone: str | None) -> str:
    """
    Normalize tone names. Supports dynamic forms like BilingualEsEn, BilingualJaEn, etc.,
    and an 'Auto' mode. Defaults to PlainClinical.
    """
    if not tone:
        return "PlainClinical"
    t = str(tone).strip()

    # exact key match (case-insensitive)
    key = next((k for k in PROMPT_TEMPLATES.keys() if k.lower() == t.lower()), None)
    if key:
        return key

    # dynamic bilingual variants (e.g., BilingualEsEn, BilingualJaEn, BilingualKoEn, BilingualArEn)
    if _parse_bilingual_code(t):
        return t  # keep exact so get_system_prompt can handle it

    # explicit Auto
    if t.lower() == "auto":
        return "Auto"

    # legacy aliases
    if t.lower() in {"plain", "science", "default"}:
        return "PlainClinical"

    return "PlainClinical"



def get_system_prompt(tone: str | None) -> str:
    t = normalize_tone(tone)

    # Dynamic bilingual (Bilingual??En)
    code = _parse_bilingual_code(t)
    if code:
        lang = BILINGUAL_LANGS.get(code, code)
        return make_bilingual_prompt(lang)

    # Auto-detect + English recap
    if t == "Auto":
        return AUTO_PROMPT

    return PROMPT_TEMPLATES.get(t, PROMPT_TEMPLATES["PlainClinical"])



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
def extract_contextual_medical_insights_from_image(file_path: str, tone: str = "PlainClinical") -> str:

    image_b64 = preprocess_image_for_vision_api(file_path)
    data_uri = f"data:image/png;base64,{image_b64}"
    system_prompt = get_system_prompt(tone) + VISION_FORMAT_PROMPT

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
    request.session["tone"] = tone


    # Friendly validation messages (no negative/error-y phrasing)
    if not uploaded_file:
        return Response({"message": "Please attach a file to continue."}, status=400)

    file_name = (uploaded_file.name or "").lower()
    system_prompt = get_system_prompt(tone)

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
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def send_chat(request):
    """
    Unified chat endpoint with tone + language support:
    - Accepts multiple files via `files[]` (new UI) or a single `file` (backward compatible).
    - Images → vision interpretation.
    - PDFs/DOCX/TXT → extract + summarize.
    - If user sends only files → return combined file summaries.
    - If user also sends a question → answer using the combined context + session history.
    - Supports tone + language (persistent via Profile).
    - Soft memory: QUICK → FULL upgrade if follow-up soon after.
    """
    # --- Tone handling (existing)
    tone = normalize_tone(
        request.data.get("tone") or request.session.get("tone") or "PlainClinical"
    )
    request.session["tone"] = tone

    # --- Language handling (new)
    lang = request.data.get("lang")
    if request.user.is_authenticated:
        from .models import Profile
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if lang:  # update preference if provided
            profile.language = lang
            profile.save()
        else:
            lang = profile.language or "en-US"
    else:
        lang = lang or "en-US"

    # --- Build system prompt with tone + language
    base_prompt = get_system_prompt(tone)
    system_prompt = (
        f"{base_prompt}\n\n"
        f"(Always respond in {lang} unless explicitly told otherwise.)"
    )

    # --- Message
    user_message = (request.data.get("message") or "").strip()

    # --- Collect files
    files = request.FILES.getlist("files[]")
    if not files and "file" in request.FILES:
        files = [request.FILES["file"]]
    has_files = bool(files)

    # --- Decide response mode
    mode, topic_hint = _classify_mode(user_message, has_files, request.session)
    header = f"ResponseMode: {mode}"
    if topic_hint:
        header += f"\nTopicHint: {topic_hint}"

    # --- Session context
    summary_context = request.session.get("latest_summary", "")
    chat_history = request.session.get(
        "chat_history",
        [{"role": "system", "content": system_prompt}, {"role": "system", "content": header}],
    )
    if not any(
        m.get("role") == "system"
        and str(m.get("content", "")).startswith("ResponseMode:")
        for m in chat_history
    ):
        chat_history.insert(1, {"role": "system", "content": header})

    # --- Process files
    combined_sections = []
    for f in files:
        fname, summary = summarize_single_file(
            f,
            tone=tone,
            system_prompt=system_prompt,
            user=request.user,
            request=request,
        )
        combined_sections.append(f"{fname}\n{summary}")

    combined_context = "\n\n".join(combined_sections).strip()

    # --- If only files
    if files and not user_message:
        request.session["latest_summary"] = combined_context or summary_context
        request.session["chat_history"] = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": header},
            {"role": "user", "content": f"(Here’s the latest medical context):\n{combined_context or summary_context}"},
        ]
        request.session["nm_last_mode"] = "FULL"
        request.session["nm_last_short_msg"] = ""
        request.session["nm_last_ts"] = _now_ts()
        request.session.modified = True

        if combined_context:
            return JsonResponse({"reply": combined_context})
        else:
            return JsonResponse(
                {"reply": "I couldn’t read any useful content from the attachments."}, status=400
            )

    # --- If no input at all
    if not files and not user_message:
        return JsonResponse({"reply": "Hmm… I didn’t catch that. Can you try again?"})

    # --- Prepare context
    if combined_context:
        chat_history = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": header},
            {"role": "user", "content": f"(Here’s the latest medical context):\n{combined_context}"},
        ]
        request.session["latest_summary"] = combined_context
    else:
        if summary_context and all(
            "(Here’s the" not in m.get("content", "") for m in chat_history if m.get("role") == "user"
        ):
            chat_history.append(
                {"role": "user", "content": f"(Here’s the medical context):\n{summary_context}"}
            )

    # --- Add user message
    chat_history.append({"role": "user", "content": user_message})

    try:
        # First pass
        raw = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.6,
            messages=chat_history,
        ).choices[0].message.content.strip()

        # Second pass (tone polish)
        reply = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": header},
                {"role": "user", "content": f"Rewrite warmly, clearly, and confidently:\n\n{raw}"},
            ],
        ).choices[0].message.content.strip()

        # Save trimmed history
        chat_history.append({"role": "assistant", "content": reply})
        request.session["chat_history"] = chat_history[-10:]

        # --- Soft-memory writeback
        if mode == "QUICK":
            request.session["nm_last_mode"] = "QUICK"
            request.session["nm_last_short_msg"] = user_message
            request.session["nm_last_ts"] = _now_ts()
        else:
            request.session["nm_last_mode"] = mode
            request.session["nm_last_short_msg"] = ""
            request.session["nm_last_ts"] = _now_ts()

        request.session.modified = True
        return JsonResponse({"reply": reply})

    except Exception:
        traceback.print_exc()
        return JsonResponse(
            {"reply": "Hi! Our system is busy right now due to a lot of users — please try again in a few minutes."},
            status=500,
        )

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
#      SESSION UTILITIES
# =============================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def clear_session(request):
    tone = normalize_tone(request.data.get("tone") or request.session.get("tone") or "PlainClinical")
    system_prompt = get_system_prompt(tone)
    request.session["chat_history"] = [{"role": "system", "content": system_prompt}]
    request.session["latest_summary"] = ""
    request.session.modified = True
    return Response({"status": "✅ New chat started!", "tone": tone})

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def reset_chat_session(request):
    # mirror of clear_session but AllowAny (if you expose this publicly)
    tone = normalize_tone(request.data.get("tone") or request.session.get("tone") or "PlainClinical")
    system_prompt = get_system_prompt(tone)
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
            resp = redirect("dashboard")
            resp.set_cookie("just_logged_in", "1", max_age=60, samesite="Lax", path="/")
            return resp
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
# views.py (auth section)
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.urls import reverse_lazy
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# ⬇️ REMOVE the old EmailOrUsernameAuthenticationForm import
# from .forms import EmailOrUsernameAuthenticationForm

# ⬇️ USE the email-only form instead
from .forms import EmailAuthenticationForm

class WarmLoginView(DjangoLoginView):
    template_name = "login.html"
    redirect_authenticated_user = True
    success_url = reverse_lazy("dashboard")
    authentication_form = EmailAuthenticationForm  # ← key line

    def form_valid(self, form):
        resp = super().form_valid(form)
        resp.set_cookie("just_logged_in", "1", max_age=60, samesite="Lax", path="/")
        return resp

    def get_success_url(self):
        url = super().get_success_url() or str(self.success_url)
        if "next" in self.request.GET:
            return url
        parts = list(urlparse(url))
        qs = parse_qs(parts[4]); qs.setdefault("welcome", ["1"])
        parts[4] = urlencode(qs, doseq=True)
        return urlunparse(parts)
    
# views.py (if you don’t already have these)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.http import JsonResponse

@api_view(["GET"])
@permission_classes([AllowAny])
def auth_status(request):
    return JsonResponse({"authenticated": bool(request.user.is_authenticated)})

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


