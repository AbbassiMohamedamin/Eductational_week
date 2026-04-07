import multiprocessing
import time
from vision_agent_new.agent import VisionAgent
from vision_agent_new.camera import CameraCapture
from vision_agent_new.vlm_client import VLMClient
from voice_agent_new.agent import VoiceAgent
from voice_agent_new.mic import MicCapture
from voice_agent_new.stt import WhisperSTT
from voice_agent_new.llm_client import JaisLLMClient
from voice_agent_new.tts import OrpheusTTS
import config_new as config

def run_vision_agent():
    camera = CameraCapture()
    vlm_client = VLMClient(config.VLM_BASE_URL, config.VLM_API_KEY, config.VLM_MODEL, config.VLM_MOCK)
    agent = VisionAgent(camera, vlm_client, config.SHARED_CONTEXT_PATH, config.VISION_INTERVAL)
    agent.run()

def run_voice_agent():
    mic = MicCapture()
    stt = WhisperSTT(mock=config.STT_MOCK)
    llm_client = JaisLLMClient(config.LLM_BASE_URL, config.LLM_API_KEY, config.LLM_MODEL, config.LLM_MOCK)
    tts = OrpheusTTS(mock=config.TTS_MOCK)
    agent = VoiceAgent(mic, stt, llm_client, tts, config.SHARED_CONTEXT_PATH)
    agent.run()

if __name__ == "__main__":
    # Ensure shared context exists
    if not os.path.exists(config.SHARED_CONTEXT_PATH):
        with open(config.SHARED_CONTEXT_PATH, 'w') as f:
            f.write("{}")

    vision_process = multiprocessing.Process(target=run_vision_agent)
    voice_process = multiprocessing.Process(target=run_voice_agent)

    vision_process.start()
    voice_process.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        vision_process.terminate()
        voice_process.terminate()
        print("System shutdown.")
