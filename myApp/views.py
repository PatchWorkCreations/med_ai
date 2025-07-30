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
        "You are a helpful, respectful AI assistant. Your job is to break down medical "
        "language into plain, human language—like you’re explaining it to a smart friend who’s not a doctor. "
        "Use simple words, clear sentences, and just enough wit to keep things from feeling like a textbook. "
        "No medical advice. Just clarity and calm, please."
    ),
    "Caregiver": (
        "You are a gentle, friendly AI who explains medical information like a wise nurse who also happens to be "
        "everyone’s favorite aunt. Be warm, clear, and kind. Use gentle metaphors, soft humor, and phrases that reassure. "
        "This person is tired and maybe scared. No diagnosis. Just kindness and truth."
    ),
    "Faith": (
        "You are a spiritually grounded AI assistant. Summarize the medical information gently and clearly. "
        "Add a light, uplifting message at the end—maybe a touch of humor, maybe a verse, maybe both. "
        "Make it feel like hope just walked in the room. No medical advice. Just heart and truth."
    ),
    "Clinical": (
        "You are a medical AI assistant summarizing clinical notes for healthcare professionals. "
        "Use concise, accurate, and medically appropriate language. Avoid over-explaining or humor."
    ),
    "Bilingual": (
        "You are an AI explaining a medical summary in both English and Tagalog (Taglish). "
        "Break things down simply, as if you’re talking to a Filipino family that needs clarity and comfort."
    ),
}

from .models import MedicalSummary

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def summarize_medical_record(request):
    uploaded_file = request.FILES.get("file")
    tone = request.data.get("tone", "Plain")

    if not uploaded_file:
        return Response({"error": "No file provided."}, status=400)

    # Extract text based on type
    if uploaded_file.name.endswith(".pdf"):
        text = extract_text_from_pdf(uploaded_file)
    elif uploaded_file.name.endswith(".docx"):
        text = extract_text_from_docx(uploaded_file)
    elif uploaded_file.name.endswith(".txt"):
        text = uploaded_file.read().decode("utf-8")
    else:
        return Response({"error": "Unsupported file format."}, status=400)

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

        # ✅ Save summary
        MedicalSummary.objects.create(
            user=request.user,
            summary=result,
            tone=tone,
            uploaded_filename=uploaded_file.name
        )

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
        data = request.data
        summary = data.get("summary", "")
        tone = data.get("tone", "Plain")

        if not summary.strip():
            return JsonResponse({"suggestions": []})

        tone_map = {
            "Plain": "Use calm, plain English like you’re explaining to a smart friend.",
            "Caregiver": "Be soft, warm, and reassuring — like a kind nurse or tita helping out.",
            "Faith": "Be hopeful, gentle, and lightly spiritual. You may include an uplifting verse or blessing.",
            "Clinical": "Be formal and to-the-point — ideal for medical teams.",
            "Bilingual": "Use Taglish and explain things simply as if to a Filipino family."
        }

        system_prompt = tone_map.get(tone, tone_map["Plain"])

        prompt = f"""
You are a warm and friendly AI health companion. You just read this summary:

\"\"\"{summary}\"\"\"

Now suggest 3 thoughtful follow-up questions a user might ask next — especially things they may not think to ask but probably should.

Only list the 3 questions. Don’t answer them yet.
"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
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

        tone_map = {
            "Plain": "Use calm, plain English like you're explaining to a smart friend.",
            "Caregiver": "Be soft, warm, and reassuring — like a kind nurse or tita helping out.",
            "Faith": "Be hopeful, gentle, and lightly spiritual. You may include an uplifting verse or blessing.",
            "Clinical": "Be formal and to-the-point — ideal for medical teams.",
            "Bilingual": "Use Taglish and explain things simply as if to a Filipino family."
        }

        system_prompt = tone_map.get(tone, tone_map["Plain"])

        prompt = f"""You are a friendly medical explainer.

Here’s the context:
\"\"\"{summary}\"\"\"

Now answer the question below in a way that matches this tone:
\"\"\"{system_prompt}\"\"\"

Q: {question}
A:"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6
        )

        return JsonResponse({"answer": response.choices[0].message.content})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"answer": "⚠️ Sorry, I couldn’t fetch that answer right now."})

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def send_chat(request):
    user_input = request.data.get("message", "")
    if not user_input:
        return JsonResponse({"reply": "Hmm... I didn’t catch that. Can you try again?"})

    session = request.session

    # Get or initialize chat history
    messages = session.get("chat_history", [
        {
            "role": "system",
            "content": (
                "You are a helpful medical assistant. Answer in a clear, compassionate way. "
                "Explain things simply, like you're talking to a smart friend who isn’t a doctor."
            )
        }
    ])

    # Append user input
    messages.append({"role": "user", "content": user_input})

    try:
        client = OpenAI()

        # Step 1: Get the raw answer
        raw_response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.6,
        )
        full_answer = raw_response.choices[0].message.content.strip()

        # Step 2: Ask GPT to rewrite it in a friendly, short format
        summary_prompt = f"""
Rewrite the following answer into a short, friendly explanation (under 150 words).
Keep it simple, slightly casual, and warm — like you're helping a friend understand.
Avoid clinical tone, avoid long paragraphs. Use light bullets if helpful.

Original:
\"\"\"{full_answer}\"\"\"
"""

        summary_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a health explainer who makes things short, friendly, and helpful."},
                {"role": "user", "content": summary_prompt}
            ],
            temperature=0.6,
        )

        trimmed_reply = summary_response.choices[0].message.content.strip()

        # Save reply and history
        messages.append({"role": "assistant", "content": trimmed_reply})
        session["chat_history"] = messages[-10:]

        return JsonResponse({"reply": trimmed_reply})
    except Exception as e:
        return JsonResponse({"reply": "⚠️ Something went wrong. Please try again later."})


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