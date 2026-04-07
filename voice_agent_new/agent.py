import time
import json
import os
from .mic import MicCapture
from .stt import WhisperSTT, VoiceInput
from .llm_client import JaisLLMClient
from .tts import OrpheusTTS
from vision_agent_new.vlm_client import SceneContext

class VoiceAgent:
    def __init__(self, mic: MicCapture, stt: WhisperSTT, llm_client: JaisLLMClient, tts: OrpheusTTS, shared_context_path: str):
        self.mic = mic
        self.stt = stt
        self.llm_client = llm_client
        self.tts = tts
        self.shared_context_path = shared_context_path

    def run(self):
        print("Starting Voice Agent...")
        try:
            while True:
                audio_bytes = self.mic.record_until_silence()
                if audio_bytes:
                    response = self.run_once(audio_bytes)
                    self.tts.speak(response, response.language)
                    print(f"Voice Agent exchange: {response}")
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Voice Agent shutting down...")
            self.mic.close()

    def run_once(self, audio_bytes: bytes) -> str:
        # Transcribe
        voice_input = self.stt.transcribe(audio_bytes)
        
        # Read latest SceneContext
        scene_context = self._read_context()
        
        # Get answer
        answer = self.llm_client.answer(voice_input.transcript, scene_context, voice_input.language)
        return answer

    def _read_context(self) -> SceneContext:
        if not os.path.exists(self.shared_context_path):
            return SceneContext(
                description="Child at desk.",
                objects=[],
                experiment_type="unknown",
                safety_concern="none"
            )
            
        with open(self.shared_context_path, 'r') as f:
            data = json.load(f)
            return SceneContext(**data)
