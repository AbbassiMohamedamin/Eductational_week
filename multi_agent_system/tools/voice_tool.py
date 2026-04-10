import os
import json
import base64
from typing import Any
from groq import Groq
from mistralai.client import Mistral
from tools.base import BaseAgentTool, AgentToolResult
import config

class VoiceTool(BaseAgentTool):
    name: str = "voice_tool"
    description: str = "Transcribes audio using Whisper, processes it with a high-capacity LLM, and generates an Arabic voice response. Input: audio_file_path (str), child_id (str)."

    def execute(self, **kwargs: Any) -> AgentToolResult:
        audio_path = kwargs.get("audio_file_path") or kwargs.get("input")
        text_input = kwargs.get("text_input")
        child_id = kwargs.get("child_id", "unknown")
        
        transcript_text = text_input
        groq_client = Groq(api_key=config.GROQ_API_KEY)

        if not transcript_text:
            if not audio_path:
                return AgentToolResult(success=False, error="audio_file_path or text_input is required")

            if not os.path.exists(audio_path):
                return AgentToolResult(success=False, error=f"Audio file not found: {audio_path}")

            try:
                # 1. Transcription with Groq Whisper (Ultra fast)
                with open(audio_path, "rb") as file:
                    transcription = groq_client.audio.transcriptions.create(
                        file=(os.path.basename(audio_path), file.read()),
                        model="whisper-large-v3",
                        language=config.STT_LANGUAGE,
                        temperature=0,
                        response_format="verbose_json",
                    )
                transcript_text = transcription.text
            except Exception as e:
                return AgentToolResult(success=False, error=f"STT Error: {str(e)}")
        
        if not transcript_text:
            return AgentToolResult(success=False, error="Could not obtain transcript")

        try:
            # 2. Processing with Llama-3.3-70B on Groq (Ultra fast - near zero latency)
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile", # Using Groq's super-fast Llama 3.3
                messages=[
                    {"role": "system", "content": "You are a friendly and helpful child safety assistant. Respond directly to the user's speech. Respond in Arabic only. Keep your response concise, warm, and safety-conscious. Your response will be read aloud to the child/parent."},
                    {"role": "user", "content": f"The user said: {transcript_text}"}
                ],
                temperature=0.7,
                max_tokens=300
            )

            analysis = response.choices[0].message.content

            # 3. Text-to-Speech with Mistral (primary) and Groq (fallback)
            os.makedirs("temp_uploads", exist_ok=True)
            voice_response_filename = f"voice_response_{child_id}.wav"
            voice_response_path = os.path.join("temp_uploads", voice_response_filename)

            voice_url = None
            tts_error = None
            tts_provider = "mistral"
            tts_model = config.MISTRAL_TTS_MODEL

            try:
                if not config.MISTRAL_TTS_API_KEY:
                    raise ValueError("mistral_tts API key is missing")

                mistral_client = Mistral(api_key=config.MISTRAL_TTS_API_KEY)
                tts_audio = mistral_client.audio.speech.complete(
                    model=config.MISTRAL_TTS_MODEL,
                    input=analysis,
                    response_format="wav",
                    stream=False,
                    voice_id=config.MISTRAL_TTS_VOICE_ID,
                )

                audio_payload = None
                if hasattr(tts_audio, "model_dump"):
                    payload_dict = tts_audio.model_dump()
                    audio_payload = payload_dict.get("audio_data")
                elif hasattr(tts_audio, "data"):
                    audio_payload = tts_audio.data
                elif isinstance(tts_audio, dict):
                    audio_payload = tts_audio.get("audio_data") or tts_audio.get("data")

                if isinstance(audio_payload, str):
                    audio_bytes = base64.b64decode(audio_payload)
                elif isinstance(audio_payload, (bytes, bytearray)):
                    audio_bytes = bytes(audio_payload)
                else:
                    raise ValueError("Unexpected Mistral TTS response format")

                with open(voice_response_path, "wb") as audio_file:
                    audio_file.write(audio_bytes)

                voice_url = f"/temp_uploads/{voice_response_filename}"
                print(f"[TTS] success provider=mistral model={config.MISTRAL_TTS_MODEL} voice={config.MISTRAL_TTS_VOICE_ID} file={voice_response_path}")
            except Exception as mistral_err:
                tts_provider = "groq-fallback"
                tts_model = config.TTS_MODEL
                tts_error = f"Mistral TTS failed: {str(mistral_err)}"
                print(f"[TTS] failed provider=mistral model={config.MISTRAL_TTS_MODEL} error={tts_error}")

                try:
                    tts_response = groq_client.audio.speech.create(
                        model=config.TTS_MODEL,
                        voice="fahad",
                        response_format="wav",
                        input=analysis,
                    )
                    tts_response.stream_to_file(voice_response_path)
                    voice_url = f"/temp_uploads/{voice_response_filename}"
                    tts_error = None
                    print(f"[TTS] success provider=groq-fallback model={config.TTS_MODEL} file={voice_response_path}")
                except Exception as groq_err:
                    tts_error = f"{tts_error}; Groq fallback failed: {str(groq_err)}"
                    print(f"[TTS] failed provider=groq-fallback model={config.TTS_MODEL} error={tts_error}")

            return AgentToolResult(success=True, data={
                "transcript": transcript_text,
                "analysis": analysis,
                "voice_url": voice_url,
                "tts_error": tts_error,
                "tts_model": tts_model,
                "tts_provider": tts_provider,
            })

        except Exception as e:
            return AgentToolResult(success=False, error=str(e))
