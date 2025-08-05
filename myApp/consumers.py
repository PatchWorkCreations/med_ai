import os
import json
import base64
import tempfile
import requests
import re
from channels.generic.websocket import AsyncWebsocketConsumer
from dotenv import load_dotenv
from openai import OpenAI
import asyncio

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("VOICE_ID_ENGLISH")

FILTERED_PHRASES = {"you", "uh", "um", "okay", "hi", "yes", "no", ""}

class VoiceAIConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

        warmup = "Hi! This is NeuraMed AI. You can start speaking anytime, and I’ll respond with care."
        greeting_audio = self.generate_tts(warmup)
        await self.send(text_data=json.dumps({
            "reply": warmup,
            "audio": greeting_audio
        }))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)

        if 'audio_input' in data:
            audio_b64 = data['audio_input']
            audio_bytes = base64.b64decode(audio_b64.split(',')[-1])

            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
                temp_audio.write(audio_bytes)
                temp_audio_path = temp_audio.name

            try:
                with open(temp_audio_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                    user_text = transcript.text.strip()
                    print(f"🎤 User said: {user_text}")
                    if len(user_text) < 3 or user_text.lower() in FILTERED_PHRASES:
                        print("⚠️ Skipped filler phrase.")
                        return
            finally:
                os.remove(temp_audio_path)
        else:
            user_text = data.get("message", "").strip()

        # Step 1: GPT Reply
        try:
            gpt_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": user_text}]
            )
            reply_text = gpt_response.choices[0].message.content.strip()
            print(f"🧠 GPT replied: {reply_text}")
        except Exception as e:
            print(f"❌ GPT error: {e}")
            reply_text = "Hmm. I’m having trouble answering that right now."

        # Step 2: Split into chunks
        segments = re.split(r'(?<=[.!?])\s+', reply_text)
        segments = [s for s in segments if s.strip()]

        # Step 3: Send sentence-by-sentence
        for segment in segments:
            audio_b64 = self.generate_tts(segment)
            if audio_b64:
                await self.send(text_data=json.dumps({
                    "reply": segment,
                    "audio": audio_b64
                }))
            await asyncio.sleep(0.3)

    def generate_tts(self, text):
        try:
            tts_response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "voice_settings": {
                        "stability": 0.4,
                        "similarity_boost": 0.7
                    }
                }
            )
            if tts_response.status_code != 200:
                print(f"❌ TTS failed: {tts_response.status_code}")
                return None

            print(f"🔊 TTS chunk size: {len(tts_response.content)} bytes")
            return base64.b64encode(tts_response.content).decode("utf-8")

        except Exception as e:
            print(f"❌ TTS error: {e}")
            return None
