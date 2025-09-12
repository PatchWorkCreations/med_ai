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
        "Speak gently, with warmth and where helpful. "
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


from urllib.parse import urlencode
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.html import escape
from django.core.mail import EmailMultiAlternatives
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

from django.shortcuts import render

def product_mockup(request):
    """
    Render the static NeuroMed AI dashboard mockup.
    """
    return render(request, "products/mockup.html")

# --- Demo Dashboard (shell + per-section include) ---

# Map route slugs -> section templates
SECTION_MAP = {
    "clinical":  "dashboard/sections/clinical.html",
    "frontdesk": "dashboard/sections/frontdesk.html",
    "rcm":       "dashboard/sections/rcm.html",
    "admin":     "dashboard/sections/admin.html",
}

# Optional: tiny scenario fixtures so the demo looks alive before uploads
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

# put near SECTION_MAP / SCENARIO_FIXTURES
FD_COLUMNS = ["New", "Screening", "Ready", "Scheduled"]

def demo_dashboard(request, section="clinical"):
    sec = (section or "clinical").lower()
    section_template = SECTION_MAP.get(sec, SECTION_MAP["clinical"])

    brand_name = request.GET.get("brand", "NeuroMed AI")
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
        "fd_columns": FD_COLUMNS,  # <-- add this
    }
    return render(request, "dashboard/base_dashboard.html", ctx)


# -----------------------------
# PORTAL (tenant) views
# -----------------------------
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth import logout, login, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.conf import settings
from django.urls import reverse
from django.core.mail import send_mail
from django.core.cache import cache
from django import forms
from django.utils.html import escape
from django.contrib.admin.views.decorators import staff_member_required

from .models import Org, OrgDomain, OrgMembership

User = get_user_model()

# Try to use your email-only login form if present; else default
try:
    from .forms import EmailAuthenticationForm as PortalLoginForm
except Exception:
    PortalLoginForm = None

# -----------------------------
# TENANT PORTAL (login, home)
# -----------------------------
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.conf import settings

from .models import OrgMembership, Org

def portal_home(request):
    if request.user.is_authenticated:
        return redirect("portal_dashboard")
    return redirect("portal_login")

class OrgLockedLoginView(DjangoLoginView):
    # use your new portal templates
    template_name = "account/portal_login.html"

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

from datetime import timedelta
from django.utils import timezone
# views.py
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Patient, Encounter

# views.py
from collections import defaultdict
from django.contrib.auth.decorators import login_required
from django.urls import reverse, NoReverseMatch
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render

from .models import Patient, Encounter

# myApp/views.py
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Patient, Encounter

# views.py

from datetime import timedelta
import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Patient, Encounter


# views.py
from datetime import timedelta
import json
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render
from django.urls import reverse

from .models import Patient, Encounter

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
        if enc.patient_id:
            return (getattr(enc.patient, "display_name", None)
                    or getattr(enc.patient, "full_name", None)
                    or "Anonymous")
        return _payload(enc).get("patient", {}).get("full_name") or "Anonymous"

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
        "frontdesk_board": frontdesk_board,   # <-- template should use this
    }
    return render(request, "dashboard/base_dashboard.html", ctx)


# myApp/views.py
import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

def _json_or_dict(val):
    if isinstance(val, dict):
        return val
    try:
        return json.loads(val or "{}")
    except Exception:
        return {}

@login_required(login_url="/portal/login/")
def portal_encounter_detail(request, pk: int):
    """Portal page to review a single encounter."""
    org = getattr(request, "org", None)

    # Prefer .all_objects if you use soft-deletes; otherwise .objects
    qs = getattr(Encounter, "all_objects", Encounter.objects).select_related("patient")

    # Scope by org when the model has an org field and the request has org
    try:
        has_org_field = any(f.name == "org" for f in Encounter._meta.fields)
    except Exception:
        has_org_field = False
    if has_org_field and org:
        qs = qs.filter(org=org)

    enc = get_object_or_404(qs, pk=pk)
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

# -----------------------------
# STAFF PWA SHELLS (/app/*)
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
# KIOSK (tokenized, no login)
# -----------------------------
from django.views.decorators.csrf import csrf_exempt
from django.core.signing import BadSignature, SignatureExpired, dumps, loads
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required

from .models import Org  # make sure this import exists

_DEVICE_SALT = "nm-kiosk-device-v1"

def _make_device_token(org: Org, app: str, days=90) -> str:
    """Create a signed, opaque token containing {'org': <slug>, 'app': <name>}."""
    payload = {"org": org.slug, "app": app}
    return dumps(payload, salt=_DEVICE_SALT, compress=True)

# views.py
from django.core.signing import loads, BadSignature, SignatureExpired
from .models import Org

_DEVICE_SALT = "nm-kiosk-device-v1"

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


# ---------- Kiosk pages (no login required) ----------
def kiosk_intake(request):
    device = _get_device_from_request(request)
    if device:
        return render(request, "kiosk/intake.html", {"device": device})

    # If a token was passed in query, set cookie then render
    t = request.GET.get("t")
    if t:
        resp = render(request, "kiosk/intake.html", {"device": _read_device_token(t) or {}})
        resp.set_cookie("device_token", t, samesite="Lax", max_age=180 * 86400)
        return resp

    return render(request, "kiosk/token_required.html", status=403)

def kiosk_consent(request):
    device = _get_device_from_request(request)
    if device:
        return render(request, "kiosk/consent.html", {"device": device})

    t = request.GET.get("t")
    if t:
        resp = render(request, "kiosk/consent.html", {"device": _read_device_token(t) or {}})
        resp.set_cookie("device_token", t, samesite="Lax", max_age=180 * 86400)
        return resp

    return render(request, "kiosk/token_required.html", status=403)

# ---------- Ops / Launch Links (staff-only) ----------
def _org_from_request(request) -> Org | None:
    org = getattr(request, "org", None)
    if org:
        return org
    host = request.get_host().split(":")[0]
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

# views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.html import escape

@staff_member_required
def launch_device_revoke(request, token_id: str):
    """
    Placeholder revoke handler. If you later persist kiosk devices,
    do the real revoke here. For now we just confirm and go back.
    """
    messages.success(request, f"Device {escape(token_id)} revoked (stateless tokens demo).")
    return redirect("launch_links")


# -----------------------------
# API v1  (product endpoints)
# -----------------------------
# -----------------------------
# API v1  (product endpoints)
# -----------------------------
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model

from .models import OrgMembership, Patient, Encounter  # org-owned models

User = get_user_model()

# ---------- OpenAI wiring (reuses your conventions if available) ----------
try:
    # If you already centralize your OpenAI client + prompts, reuse them.
    from myApp.ai import client, get_system_prompt  # adjust path if needed
except Exception:
    # Fallback: minimal OpenAI client using OPENAI_API_KEY
    from openai import OpenAI

    client = OpenAI(api_key=getattr(settings, "OPENAI_API_KEY", None))

    def get_system_prompt(tone: str = "PlainClinical"):
        # Replace with your own system prompt if you have one
        return (
            "You are a concise, safety-aware clinical assistant. "
            "Be clear, neutral, and avoid firm diagnosis. "
            "Ask focused questions to collect clinical history."
        )

OPENAI_TRIAGE_MODEL = getattr(settings, "OPENAI_TRIAGE_MODEL", "gpt-4o-mini")
OPENAI_BRIEF_MODEL = getattr(settings, "OPENAI_BRIEF_MODEL", "gpt-4o-mini")
OPENAI_VISION_MODEL = getattr(settings, "OPENAI_VISION_MODEL", "gpt-4o")

# ---------- Prompt snippets ----------
TRIAGE_FORMAT_PROMPT = """
Return STRICT JSON with keys:
- "assistant": string  (your short, warm reply to the patient, ≤ 2 sentences)
- "fields": object with optional keys:
  - complaint: string
  - duration: string
  - severity: "mild" | "moderate" | "severe"
  - location: string
  - red_flags: string[]
  - next_questions: string[]
No extra text; only JSON.
"""

TRIAGE_SUMMARY_FORMAT_PROMPT = """
Given patient triage fields and a transcript, return STRICT JSON:
{
  "acuity": "low" | "medium" | "high",
  "red_flags": string[],
  "next_steps": string[],
  "one_sentence": string
}
Constraints:
- The one_sentence is ≤160 characters and clinically specific.
No extra text; only JSON.
"""

BRIEF_FORMAT_PROMPT = """
You will receive an encounter context (intake fields, transcript, and any prior notes).
Return STRICT JSON:
{
  "chief_complaint": string,
  "salient_history": string[],
  "ddx": string[],
  "recommended_questions": string[]
}
No extra text; only JSON.
"""

# ---------- Utilities ----------
def _safe_json(text, fallback=None):
    try:
        return json.loads(text)
    except Exception:
        return fallback or {}

def _merge_fields(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
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
    """
    Lightweight extraction so the UI updates even if LLM is down.
    """
    msg = (message or "").strip()
    low = msg.lower()

    # duration (e.g., "3 months", "2 weeks", "today", "yesterday")
    duration = None
    m = re.search(r"\b(\d+\s*(?:hour|day|week|month|year)s?)\b", low)
    if m:
        duration = m.group(1)
    if not duration:
        for kw in ["today", "yesterday", "last night", "this morning", "this week"]:
            if kw in low:
                duration = kw
                break

    # severity
    severity = None
    for word in ["mild", "moderate", "severe"]:
        if re.search(rf"\b{word}\b", low):
            severity = word
            break
    if not severity:
        if re.search(r"\b([0-9]|10)\/10\b", low):
            severity = re.search(r"\b([0-9]|10)\/10\b", low).group(0)

    # location
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

    # complaint: first ~12 words, if any symptom-y terms present
    complaint = None
    if any(k in low for k in ["pain", "swelling", "fever", "cough", "rash", "injury", "headache", "nausea", "vomit", "dizzy"]):
        complaint = " ".join(msg.split()[:12])

    # red flags demo set
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
    # Drop None values
    return {k: v for k, v in out.items() if v not in (None, "", [])}

def _default_actor_for_org(org) -> User | None:
    mem = OrgMembership.objects.filter(org=org, is_active=True).select_related("user").first()
    return mem.user if mem else User.objects.filter(is_superuser=True).first() or User.objects.first()

# views.py (add near your imports)
from django.db.models import Q

# ---- helpers -----------------
def _split_name(full_name: str):
    if not full_name:
        return ("", "")
    parts = str(full_name).strip().split()
    if len(parts) == 1:
        return (parts[0], "")
    return (" ".join(parts[:-1]), parts[-1])

def _upsert_patient(org, p: dict):
    """
    Upsert a Patient by (phone or email) and optional DOB.
    Returns Patient instance.
    Expected keys: full_name|first_name|last_name, phone, email, dob (YYYY-MM-DD), insurer, policy_id
    """
    from .models import Patient  # your org-owned Patient

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
        if dob   and not match.dob: match.dob, changed = dob, True
        # store insurance on patient or in encounter summary (your preference)
        insurer   = p.get("insurer") or p.get("insurance")
        policy_id = p.get("policy_id")
        if insurer and getattr(match, "insurer", None) != insurer:
            setattr(match, "insurer", insurer); changed = True
        if policy_id and getattr(match, "policy_id", None) != policy_id:
            setattr(match, "policy_id", policy_id); changed = True
        if changed: match.save(update_fields=None)
        return match

    # create new
    kwargs = dict(org=org, first_name=first or "", last_name=last or "")
    if phone: kwargs["phone"] = phone
    if email: kwargs["email"] = email
    if dob:   kwargs["dob"]   = dob
    insurer   = p.get("insurer") or p.get("insurance")
    policy_id = p.get("policy_id")
    if insurer:   kwargs["insurer"]   = insurer
    if policy_id: kwargs["policy_id"] = policy_id
    return Patient.objects.create(**kwargs)

# ---------- Upload (simple) ----------
@csrf_exempt
@require_http_methods(["POST"])
def api_v1_upload(request):
    """
    Accept a single file and return a temporary token/path.
    Replace with a real uploader (S3) later.
    """
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

# ---------- Encounters: unified fetch ----------
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
        "icd": enc.icd,
        "cpt": enc.cpt,
        "denials": enc.denials,
        "created_at": enc.created_at.isoformat(),
    }
    return JsonResponse(data)



# views.py
@csrf_exempt
@require_http_methods(["POST"])
def api_v1_encounter_move(request):
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad json"}, status=400)

    enc_id = body.get("id")
    # accept either "to" or "status"
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



# ---------- TRIAGE turn-by-turn (LLM + heuristics) ----------
def _llm_triage_turn(message: str, history: List[Dict[str, str]] | None = None, tone: str = "PlainClinical"):
    """
    Use OpenAI to generate a short assistant reply + structured 'fields' JSON.
    history format: [{role:'user'|'assistant', content:str}, ...]
    """
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
        fields = data.get("fields") or {}
        # Merge a heuristic backstop so UI updates even if extraction is partial
        fields = _merge_fields(_extract_fields_heuristic(message), fields)
        return assistant, fields
    except Exception:
        return default_reply, _extract_fields_heuristic(message)

TRIAGE_SYSTEM_PROMPT = """
You are a clinical intake assistant. Be concise, warm, and directive.
Safety first: if any red-flag symptoms are present (e.g., chest pain, shortness of breath, neuro deficits,
severe bleeding, anaphylaxis), advise urgent/ED care immediately.

RULES:
- Ask ONE question per turn.
- End every reply with exactly one question mark.
- Keep it short (1–2 sentences + the question).
- Prefer plain language.

SLOTS (collect in order): red_flags → duration → severity → location → onset → modifiers.
"""

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

def _next_slot(fields: dict) -> str | None:
    order = ["red_flags", "duration", "severity", "location", "onset", "modifiers"]
    for key in order:
        v = fields.get(key)
        if not v or (isinstance(v, list) and not v):
            return key
    return None

def _merge_fields(base: dict, new: dict) -> dict:
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
            combined = list(dict.fromkeys([*existing, *v]))  # de-dup, keep order
            out[k] = combined
        else:
            if _is_empty(out.get(k)) and not _is_empty(v):
                out[k] = v
    return out


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
@csrf_exempt
@require_http_methods(["POST"])
def api_v1_triage_chat(request):
    """
    Turn-by-turn triage with explicit end-of-flow (done) and escalation flags.
    Also binds org from kiosk device token if middleware didn't.
    """
    # <-- NEW: bind org from device token for kiosk flows
    _bind_org_from_device_token(request)

    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad json"}, status=400)

    message = (body.get("message") or "").strip()
    history = body.get("history") or []
    tone    = (body.get("tone") or "PlainClinical").strip()
    fields  = body.get("fields") or {}

    # Extract + merge
    extracted = _extract_fields_heuristic(message)
    try:
        llm_reply, llm_fields = _llm_triage_turn(message, history, tone)
        extracted = _merge_fields(extracted, llm_fields)
    except Exception:
        llm_reply = None
    fields = _merge_fields(fields, extracted)

    # Decide remaining slot
    slot = _next_slot(fields)
    good_enough = bool(fields.get("complaint")) and bool(fields.get("location")) and bool(
        fields.get("duration") or fields.get("severity")
    )
    done = (slot is None) or good_enough

    # Danger terms
    DANGER_TERMS = {"chest pain", "shortness of breath", "trouble breathing",
                    "weakness", "numbness", "severe bleeding", "anaphylaxis"}
    rf_text = " ".join([str(x).lower() for x in (fields.get("red_flags") or [])])
    escalate = any(term in rf_text for term in DANGER_TERMS)

    # Craft assistant text
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

    return JsonResponse({
        "assistant": assistant_text,
        "fields": fields,
        "slot": slot,
        "next_question": planned_question,
        "quick_options": QUICK_OPTIONS.get(slot, []),
        "done": bool(done and not escalate),
        "escalate": bool(escalate),
    })



# ---------- TRIAGE (submit to create Encounter + AI summary) ----------
@csrf_exempt
@require_http_methods(["POST"])
def api_v1_triage_submit(request):
    """
    Submit triage into an Encounter.
    Accepts optional 'patient' block to create/link a Patient.
    Binds org from kiosk device token (cookie/query/header) or from body.kiosk_token.
    """
    # 1) Bind org from device token (cookie/query/header)
    _bind_org_from_device_token(request)

    # 2) Parse body
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad json"}, status=400)

    # 3) Fallback: bind org from explicit kiosk_token in the body (if not yet bound)
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

    # 4) Pick an actor (first active member or superuser fallback)
    actor = _default_actor_for_org(org)
    if not actor:
        return JsonResponse({"error": "no active users in org"}, status=400)

    # 5) Normalize transcript
    transcript = []
    for turn in history:
        r = "assistant" if (turn.get("role") == "assistant") else "user"
        c = (turn.get("content") or "").strip()
        if c:
            transcript.append({"role": r, "content": c})
    if message:
        transcript.append({"role": "user", "content": message})

    # 6) Upsert/link patient (optional; don’t block encounter on failure)
    patient_obj = None
    try:
        has_any = any(bool((patient_in.get(k) or "").strip())
                      for k in ("full_name", "first_name", "last_name", "email", "phone", "dob", "insurer", "policy_id"))
        if has_any:
            patient_obj = _upsert_patient(org, patient_in)
    except Exception:
        patient_obj = None  # keep going

    # 7) AI summary (two-pass), with safe fallback
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

    # 8) Compose encounter payload
    payload = {
        "fields": fields,
        "transcript": transcript,
        "triage": triage_ai,
        # carry a shallow patient block for UI regardless of match
        "patient": {
            "full_name": (getattr(patient_obj, "full_name", None) or patient_in.get("full_name") or "Anonymous"),
            "insurer":   (getattr(patient_obj, "insurer", None)   or patient_in.get("insurer")),
            "email":     (getattr(patient_obj, "email", None)     or patient_in.get("email")),
            "phone":     (getattr(patient_obj, "phone", None)     or patient_in.get("phone")),
        },
    }

    # Reason: prefer complaint → one_sentence → default
    reason = (
        (fields.get("complaint") or "").strip()
        or (triage_ai.get("one_sentence") or "").strip()
        or "Patient-reported symptoms"
    )

    # 9) Create encounter (use all_objects when available)
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

    # 10) Response
    return JsonResponse({
        "encounter_id": enc.id,
        "status": enc.status,
        "reason": enc.reason,
        **triage_ai
    }, status=201)




@require_http_methods(["GET"])
def api_v1_triage_get(request, encounter_id: int):
    org = getattr(request, "org", None)
    try:
        enc = Encounter.all_objects.get(pk=encounter_id, org=org)
    except Encounter.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    payload = _safe_json(enc.summary or "{}", {})
    triage = payload.get("triage") or {}
    return JsonResponse({"encounter_id": enc.id, "triage": triage, "payload": payload})


# ---------- SCHEDULING ----------
@csrf_exempt
@require_http_methods(["POST"])
def api_v1_sched_suggest(request):
    # TODO integrate real rules/availability
    return JsonResponse({
        "suggestions": [
            {"slot": "2025-09-12T09:30:00", "type": "New patient"},
            {"slot": "2025-09-12T14:15:00", "type": "Follow-up"},
        ]
    })


@csrf_exempt
@require_http_methods(["POST"])
def api_v1_sched_book(request):
    # TODO: persist Appointment(org-owned)
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad json"}, status=400)
    return JsonResponse({"ok": True, "appointment_id": "apt_demo_001", "echo": body})


# ---------- CLINICAL BRIEF ----------
@csrf_exempt
@require_http_methods(["POST"])
def api_v1_chart_brief(request):
    """
    Body: { encounter_id: int }
    Uses prior triage payload to generate a clinician-facing brief.
    """
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad json"}, status=400)

    enc_id = body.get("encounter_id")
    if not enc_id:
        return JsonResponse({"error": "encounter_id required"}, status=400)

    org = getattr(request, "org", None)
    try:
        enc = Encounter.all_objects.get(pk=enc_id, org=org)
    except Encounter.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    payload = _safe_json(enc.summary or "{}", {})
    fields = payload.get("fields") or {}
    transcript = payload.get("transcript") or []

    # AI brief
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
        # fallback
        brief = {
            "chief_complaint": fields.get("complaint") or "N/A",
            "salient_history": ["Structured brief unavailable; showing captured intake only."],
            "ddx": ["n/a"],
            "recommended_questions": ["Onset/duration?", "Severity?", "Aggravating factors?"],
        }

    return JsonResponse({"encounter_id": enc.id, "brief": brief})


# ---------- DIAGNOSTICS ----------
@csrf_exempt
@require_http_methods(["POST"])
def api_v1_diag_interpret(request):
    """
    Accept file(s) and return interpretation.
    If images are provided, we can (optionally) call a vision model later.
    For now, a safe demo reply is returned.
    """
    if not request.FILES:
        return JsonResponse({"error": "no files uploaded"}, status=400)

    names = [f.name for f in request.FILES.getlist("files")]

    # (Optional) Upgrade to real vision call later like your sample.
    # For now: simple placeholder to keep contract stable.
    findings = {
        "observed": ["example: joint space narrowing medial compartment"],
        "possible": ["example: degenerative OA"],
        "next": ["example: weight-bearing x-ray", "example: PT referral"],
    }
    return JsonResponse({"files": names, "findings": findings})


# ---------- CODING ----------
@csrf_exempt
@require_http_methods(["POST"])
def api_v1_coding_suggest(request):
    # TODO: map from brief/soap to ICD/CPT with rationales
    return JsonResponse({
        "icd": [{"code": "M17.11", "desc": "Unilateral primary osteoarthritis, right knee", "why": "pain + x-ray OA"}],
        "cpt": [{"code": "99213", "desc": "Established patient, low MDM", "why": "stable chronic illness"}],
    })


@csrf_exempt
@require_http_methods(["POST"])
def api_v1_claim_draft(request):
    # TODO: persist ClaimDraft(org-owned)
    return JsonResponse({"claim_id": "clm_demo_001", "status": "draft"})


# ---------- CARE PLAN & MESSAGES ----------
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
    # TODO: enqueue sms/email via per-org provider keys
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"error": "bad json"}, status=400)
    return JsonResponse({"queued": True, "id": "msg_demo_001", "echo": body})


# -----------------------------
# OTP / Password Reset (PORTAL)
# -----------------------------
# Uses your existing helpers and forms already defined earlier:
# - ForgotPasswordForm, OTPForm, OTPSetPasswordForm
# - _otp_key, _otp_attempts_key, _otp_resend_key
# - _generate_code, mask_email, send_otp_email, OTP_TTL_SECONDS
# - DASHBOARD_URL (your existing post-login landing)
# --- imports you need near the top of views.py (if not already there)
from django.core.cache import cache
from django.contrib.auth import get_user_model, login
from django.contrib import messages
from django.shortcuts import render, redirect

User = get_user_model()


# -----------------------------
# PORTAL password reset (OTP)
# -----------------------------
# -----------------------------
# PORTAL password reset (OTP)
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
# STAFF-ONLY tenant admin views
# -----------------------------

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


def _primary_domain(org: Org) -> str | None:
    dom = org.domains.filter(is_primary=True).first()
    return dom.domain if dom else None


def _portal_login_url_for(org: Org) -> str:
    domain = _primary_domain(org) or "neuromedai.org"
    return f"https://{domain}/portal/login/"


def _email_credentials(to_email: str, org: Org, password: str | None):
    try:
        subject = f"Your NeuroMed AI Portal Access – {org.name}"
        login_url = _portal_login_url_for(org)
        if password:
            text = (
                f"Welcome to {org.name} on NeuroMed AI.\n\n"
                f"Portal: {login_url}\n"
                f"Email: {to_email}\n"
                f"Temporary Password: {password}\n\n"
                "For security, please sign in and change your password.\n"
            )
        else:
            text = (
                f"Your NeuroMed AI portal is ready for {org.name}.\n\n"
                f"Portal: {login_url}\n"
                f"Email: {to_email}\n\n"
                "If you need a password reset, reply to this email."
            )
        send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=True)
    except Exception:
        pass


@staff_member_required
def dev_client_create(request):
    """
    Create a new Org + primary OrgDomain + OWNER user (if not exists).
    Show temp password on screen and optionally email it.
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
    """
    Overview page: domains, members, and quick actions.
    """
    org = Org.objects.get(slug=slug)
    members = OrgMembership.objects.filter(org=org).select_related("user")
    return render(request, "dev/client_detail.html", {"org": org, "members": members})


@staff_member_required
def dev_client_user_create(request, slug):
    """
    Create a user inside an org with a role and (optional) temp password.
    """
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
    """
    Reset a user's password inside an org (doesn't change membership).
    """
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
