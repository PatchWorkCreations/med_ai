# AI-Connected send_chat implementation for mobile_api
# Replace the stub send_chat function in compat_views.py with this

from rest_framework.decorators import api_view, parser_classes, authentication_classes, permission_classes
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from django.utils import timezone
import uuid

@api_view(['POST'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def send_chat(request):
    """
    Send a chat message - CONNECTED TO REAL AI.
    POST /api/send-chat/
    
    Accepts:
    - message: user text
    - tone: PlainClinical (default), Caregiver, Faith, Clinical, etc.
    - lang: language code (default: en-US)
    - care_setting: hospital|ambulatory|urgent (for Clinical/Caregiver)
    - faith_setting: general|christian|muslim|etc (for Faith)
    - session_id: optional thread ID
    - files[] or file: attachments (multipart)
    
    Returns: ChatMessage format {id, role, content, timestamp, session_id, metadata}
    """
    # Import real AI logic from myApp
    from myApp.views import (
        normalize_tone,
        get_system_prompt,
        get_setting_prompt,
        get_faith_prompt,
        norm_setting,
        norm_faith_setting,
        _classify_mode,
        _now_ts,
        _now_iso,
        _trim_history,
        _ensure_session_for_user,
        summarize_single_file
    )
    from openai import OpenAI
    
    client = OpenAI()
    
    # Extract parameters (use 'lang' not 'language' per contract)
    user_message = (request.data.get("message") or "").strip()
    tone = normalize_tone(request.data.get("tone"))
    lang = request.data.get("lang", "en-US")
    care_setting = request.data.get("care_setting")
    faith_setting = request.data.get("faith_setting")
    incoming_session_id = request.data.get("session_id")
    
    # Get files
    files = request.FILES.getlist("files[]") or (
        [request.FILES["file"]] if "file" in request.FILES else []
    )
    has_files = bool(files)
    
    if not user_message and not has_files:
        return Response({"error": "message or files required"}, status=400)
    
    print(f"💬 CHAT: User={request.user.username}, Msg={user_message[:50] if user_message else '[files only]'}..., Tone={tone}, Lang={lang}")
    
    # Classify mode (QUICK/EXPLAIN/FULL)
    mode, topic_hint = _classify_mode(user_message, has_files, request.session)
    print(f"📊 CHAT: Mode={mode}, Files={len(files)}, TopicHint={topic_hint[:30] if topic_hint else 'none'}...")
    
    # Build system prompt with layers
    base_prompt = get_system_prompt(tone)
    
    if tone == "Faith" and faith_setting:
        system_prompt = get_faith_prompt(base_prompt, norm_faith_setting(faith_setting))
    elif tone in ("Clinical", "Caregiver") and care_setting:
        system_prompt = get_setting_prompt(base_prompt, norm_setting(care_setting))
    else:
        system_prompt = base_prompt
    
    # Add language instruction
    system_prompt = f"{system_prompt}\n\n(Always respond in {lang} unless told otherwise.)"
    
    # Add mode header
    header = f"ResponseMode: {mode}" + (f"\nTopicHint: {topic_hint}" if topic_hint else "")
    
    # Get or create session
    sticky_session_id = request.session.get("active_chat_session_id")
    chosen_session_id = incoming_session_id or sticky_session_id
    
    session_obj, created = _ensure_session_for_user(
        request.user, 
        tone, 
        lang,
        first_user_msg=user_message or "[attachments]",
        session_id=chosen_session_id
    )
    
    # Make it sticky
    request.session["active_chat_session_id"] = session_obj.id
    request.session.modified = True
    
    print(f"📝 CHAT: Session={session_obj.id}, Created={created}")
    
    # Build chat history from session
    chat_history = []
    for m in (session_obj.messages or []):
        r, c = m.get("role"), m.get("content")
        if r and c is not None:
            chat_history.append({"role": r, "content": c})
    
    # Ensure system prompts are present
    if not any(m.get("role") == "system" and header in m.get("content", "") for m in chat_history):
        chat_history.insert(0, {"role": "system", "content": header})
    if not any(m.get("role") == "system" and base_prompt in m.get("content", "") for m in chat_history):
        chat_history.insert(0, {"role": "system", "content": system_prompt})
    
    # Process files if any
    combined_sections = []
    for f in files:
        fname, summary = summarize_single_file(
            f, tone=tone, system_prompt=system_prompt, 
            user=request.user, request=request
        )
        combined_sections.append(f"{fname}\n{summary}")
    combined_context = "\n\n".join(combined_sections).strip()
    
    if combined_context:
        chat_history.append({
            "role": "user",
            "content": f"(Here's the latest medical context):\n{combined_context}"
        })
    
    # Add user message
    if user_message:
        chat_history.append({"role": "user", "content": user_message})
    
    print(f"🤖 CHAT: Calling OpenAI with {len(chat_history)} messages...")
    
    # Call OpenAI - OPTIMIZED: Single pass for faster responses
    try:
        # Single optimized call with balanced temperature for both accuracy and warmth
        # The system_prompt already includes tone instructions, so we don't need a second pass
        polished = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.5,  # Balanced between accuracy (0.3) and creativity (0.6)
            messages=chat_history,
        ).choices[0].message.content.strip()
        
        print(f"✅ CHAT: AI response generated ({len(polished)} chars)")
        
        # Save to session
        msgs = session_obj.messages or []
        if not msgs:
            msgs.extend([
                {"role": "system", "content": system_prompt, "ts": _now_iso()},
                {"role": "system", "content": header, "ts": _now_iso()},
            ])
        
        if combined_context:
            msgs.append({
                "role": "user",
                "content": f"(Here's the latest medical context):\n{combined_context}",
                "ts": _now_iso(),
                "meta": {"context": "files"}
            })
        
        if user_message:
            msgs.append({"role": "user", "content": user_message, "ts": _now_iso()})
        
        msgs.append({"role": "assistant", "content": polished, "ts": _now_iso()})
        
        session_obj.messages = _trim_history(msgs, keep=200)
        session_obj.updated_at = timezone.now()
        session_obj.save(update_fields=["messages", "updated_at"])
        
        # Update soft memory for mode upgrades
        if mode == "QUICK":
            request.session["nm_last_mode"] = "QUICK"
            request.session["nm_last_short_msg"] = user_message
        else:
            request.session["nm_last_mode"] = mode
            request.session["nm_last_short_msg"] = ""
        request.session["nm_last_ts"] = _now_ts()
        request.session.modified = True
        
        # Return iOS-friendly ChatMessage format
        return Response({
            "id": str(uuid.uuid4()),
            "role": "assistant",
            "content": polished,
            "timestamp": timezone.now().isoformat(),
            "session_id": session_obj.id,
            "metadata": None
        }, status=200)
        
    except Exception as e:
        print(f"❌ CHAT ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return Response({
            "error": "System is busy right now. Please try again in a moment."
        }, status=503)

