import os
from dotenv import load_dotenv

load_dotenv()

# VLM Config
VLM_BASE_URL = os.getenv("VLM_BASE_URL", "http://localhost:8000/v1")
VLM_API_KEY = os.getenv("VLM_API_KEY", "EMPTY")
VLM_MODEL = os.getenv("VLM_MODEL", "vision-model")
VLM_MOCK = os.getenv("VLM_MOCK", "true").lower() == "true"
VISION_INTERVAL = int(os.getenv("VISION_INTERVAL", "3"))

# LLM Config
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:8001/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "EMPTY")
LLM_MODEL = os.getenv("LLM_MODEL", "inceptionai/jais-adapted-70b-chat")
LLM_MOCK = os.getenv("LLM_MOCK", "true").lower() == "true"

# STT Config
STT_MOCK = os.getenv("STT_MOCK", "true").lower() == "true"

# TTS Config
TTS_MOCK = os.getenv("TTS_MOCK", "true").lower() == "true"

# Shared
SHARED_CONTEXT_PATH = os.path.abspath("shared_context.json")
