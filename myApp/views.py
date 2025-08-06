from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required

import openai
from django.conf import settings

openai.api_key = settings.OPENAI_API_KEY


def landing_page(request):
    return render(request, "landing.html", {"is_authenticated": request.user.is_authenticated})


# views.py
from .forms import CustomSignupForm

def signup_view(request):
    if request.method == "POST":
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = CustomSignupForm()
    return render(request, "signup.html", {"form": form})




from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from openai import OpenAI
import os
import fitz  # PyMuPDF
import docx
from rest_framework.decorators import parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated


def extract_text_from_pdf(file):
    pdf = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in pdf:
        text += page.get_text()
    return text.strip()

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())



PROMPT_TEMPLATES = {
    "Plain": (
        "You are NeuroMed, a compassionate and intelligent medical assistant. "
        "Break down complex health info like you're speaking to a smart friend—clear, calm, a bit witty, but never robotic. "
        "Offer real insight. Don't hide behind disclaimers unless it's truly necessary."
    ),
    "Caregiver": (
        "You are NeuroMed, a warm and kind medical expert, like a favorite nurse who explains everything gently. "
        "Use metaphors, Taglish warmth, and calm assurance. Speak like someone who truly cares, especially if the user is tired or worried."
    ),
    "Faith": (
        "You are NeuroMed, a wise medical guide with a heart full of hope and faith. Explain medical concepts clearly, gently, and lovingly. "
        "End with a comforting blessing or Bible verse when appropriate. Bring light even in uncertainty."
    ),
    "Clinical": (
        "You are NeuroMed, a precise and knowledgeable assistant for clinicians. Use medical terminology and concise summaries. "
        "No unnecessary pleasantries—just clean, professional delivery for healthcare teams."
    ),
    "Bilingual": (
        "You are NeuroMed, a friendly medical expert who explains in Taglish. Speak clearly and kindly, as if talking to a Filipino family member who needs comfort and understanding. "
        "Use Tagalog-English naturally to make things easy to understand."
    ),
}


import base64
from openai import OpenAI
import tempfile


def extract_text_from_image(file_path: str) -> str:
    with open(file_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": "Extract all visible text from this image. Only return the text."},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{image_data}"
                }}
            ]}
        ]
    )

    return response.choices[0].message.content.strip()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def summarize_medical_record(request):
    uploaded_file = request.FILES.get("file")
    tone = request.data.get("tone", "Plain")

    if not uploaded_file:
        return Response({"error": "No file provided."}, status=400)

    file_name = uploaded_file.name.lower()
    text = ""

    try:
        if file_name.endswith(".pdf"):
            text = extract_text_from_pdf(uploaded_file)
        elif file_name.endswith(".docx"):
            text = extract_text_from_docx(uploaded_file)
        elif file_name.endswith(".txt"):
            text = uploaded_file.read().decode("utf-8")
        elif file_name.endswith((".jpg", ".jpeg", ".png", ".heic", ".webp")):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1]) as tmp:
                for chunk in uploaded_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            text = extract_text_from_image(tmp_path)
            os.remove(tmp_path)
        else:
            return Response({"error": "Unsupported file format."}, status=400)
    except Exception as e:
        return Response({"error": f"Failed to process file: {str(e)}"}, status=400)

    if not text.strip():
        return Response({"error": "Document is empty or unreadable."}, status=400)

    system_prompt = PROMPT_TEMPLATES.get(tone, PROMPT_TEMPLATES["Plain"])

    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.5
        )
        result = completion.choices[0].message.content.strip()

        MedicalSummary.objects.create(
            user=request.user,
            summary=result,
            tone=tone,
            uploaded_filename=uploaded_file.name
        )

        request.session["latest_summary"] = result
        request.session.modified = True

        return Response({"summary": result})
    except Exception as e:
        return Response({"error": str(e)}, status=500)


    


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import MedicalSummary

@login_required
def dashboard(request):
    summaries = request.user.summaries.all()  # via related_name
    return render(request, "dashboard.html", {"summaries": summaries})


from django.views.decorators.csrf import csrf_exempt
import json
import openai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

# Set your OpenAI key securely (or via env)
openai.api_key = os.getenv("OPENAI_API_KEY")  # or use settings.OPENAI_KEY
import traceback


from openai import OpenAI
client = OpenAI()

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def smart_suggestions(request):
    try:
        summary = request.data.get("summary", "")
        tone = request.data.get("tone", "Plain")

        if not summary.strip():
            return JsonResponse({"suggestions": []})

        prompt = f"""
You just read this summary:

\"\"\"{summary}\"\"\"

List 3 thoughtful follow-up questions the user might want to ask next (things they may not think to ask, but should). Just list the questions.
"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": PROMPT_TEMPLATES.get(tone, PROMPT_TEMPLATES["Plain"])},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6
        )

        output = response.choices[0].message.content
        questions = [q.strip("- ").strip() for q in output.split("\n") if q.strip()]

        return JsonResponse({"suggestions": [{"question": q} for q in questions]})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


# 🔹 Answering a Specific Question
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def answer_question(request):
    try:
        question = request.data.get("question", "")
        summary = request.data.get("summary", "")
        tone = request.data.get("tone", "Plain")

        if not question:
            return JsonResponse({"answer": "I didn’t receive a question to answer."})

        prompt = f"""
You're NeuroMed, a wise and compassionate medical expert with deep knowledge in clinical and holistic care.
Here’s the context:
\"\"\"{summary}\"\"\"

Now answer this question clearly and gently:
Q: {question}
"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": PROMPT_TEMPLATES.get(tone, PROMPT_TEMPLATES["Plain"])},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
        )

        return JsonResponse({"answer": response.choices[0].message.content.strip()})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"answer": "⚠️ Sorry, something went wrong. Try again in a bit."})


# 🔹 Session Reset
@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def reset_chat_session(request):
    request.session["chat_history"] = [
        {"role": "system", "content": "You are NeuroMed, a friendly, kind, and wise health companion."}
    ]
    return JsonResponse({"message": "Session reset."})

    
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def send_chat(request):
    user_input = request.data.get("message", "")
    if not user_input:
        return JsonResponse({"reply": "Hmm... I didn’t catch that. Can you try again?"})

    session = request.session
    summary_context = session.get("latest_summary", "")

    messages = session.get("chat_history", [
        {
            "role": "system",
            "content": (
                "You are NeuroMed, a compassionate and highly intelligent medical expert. "
                "You speak kindly and clearly—like a trusted doctor explaining something to a friend. "
                "Avoid phrases like 'I am just an AI' unless absolutely needed. Never be cold. "
                "Be encouraging, helpful, and calm. If you don’t know something, still guide the person with care."
            )
        }
    ])

    if summary_context:
        messages.append({
            "role": "user",
            "content": f"(Here’s the medical context from a file):\n{summary_context}"
        })

    messages.append({"role": "user", "content": user_input})

    try:
        raw_response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.6,
        )
        full_answer = raw_response.choices[0].message.content.strip()

        # Token-efficient light rewrite
        summary_prompt = f"""
Shorten the following into a warm, human response. No disclaimers. Keep the tone like a caring doctor helping a friend. Max 180 words.

\"\"\"{full_answer}\"\"\"
"""

        summary_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a medical writer who sounds kind, clear, and confident."},
                {"role": "user", "content": summary_prompt}
            ],
            temperature=0.6,
        )

        trimmed_reply = summary_response.choices[0].message.content.strip()

        messages.append({"role": "assistant", "content": trimmed_reply})
        session["chat_history"] = messages[-10:]
        session.modified = True

        return JsonResponse({"reply": trimmed_reply})

    except Exception as e:
        return JsonResponse({
            "reply": "I'm having trouble responding right now, but hang in there. Try again in a bit, or upload another file—I’m right here with you."
        })
    



@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def reset_chat_session(request):
    request.session["chat_history"] = [
        {"role": "system", "content": "You are a friendly medical guide that explains things in a kind, calming way."}
    ]
    return JsonResponse({"message": "Session has been reset."})



def about_page(request):
    return render(request, "about.html")


from django.shortcuts import render

def speaking_view(request):
    return render(request, 'talking_ai/speaking.html')
