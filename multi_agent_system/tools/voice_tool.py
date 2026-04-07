import os
import json
from typing import Any
from groq import Groq
from openai import OpenAI
import httpx
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

            # 3. Text-to-Speech (Arabic) with Groq
            os.makedirs("temp_uploads", exist_ok=True)
            voice_response_filename = f"voice_response_{child_id}.wav"
            voice_response_path = os.path.join("temp_uploads", voice_response_filename)
            
            try:
                tts_response = groq_client.audio.speech.create(
                    model="canopylabs/orpheus-arabic-saudi",
                    voice="fahad",
                    response_format="wav",
                    input=analysis,
                )
                tts_response.stream_to_file(voice_response_path)
                voice_url = f"/temp_uploads/{voice_response_filename}"
            except Exception as tts_err:
                # Log TTS error silently but return null voice_url
                voice_url = None

            return AgentToolResult(success=True, data={
                "transcript": transcript_text,
                "analysis": analysis,
                "voice_url": voice_url
            })

        except Exception as e:
            return AgentToolResult(success=False, error=str(e))
