import os
from dotenv import load_dotenv

# Load settings from .env
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
VLM_API_KEY = os.getenv("VLM_API_KEY")
VLM_BASE_URL = os.getenv("VLM_BASE_URL", "https://tokenfactory.esprit.tn/api")
VLM_MODEL = os.getenv("VLM_MODEL", "hosted_vllm/llava-1.5-7b-hf")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai or groq
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")
LLM_MODEL_70B = os.getenv("LLM_MODEL_70B", "hosted_vllm/Llama-3.1-70B-Instruct")
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "./memory/faiss_index")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")  # Local HuggingFace model
RISK_THRESHOLD_HIGH = float(os.getenv("RISK_THRESHOLD_HIGH", "0.75"))
RISK_THRESHOLD_MEDIUM = float(os.getenv("RISK_THRESHOLD_MEDIUM", "0.45"))
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Print configuration for verification
print(f"--- Configuration Loaded ---")
print(f"LLM Provider: {LLM_PROVIDER}")
print(f"LLM Model: {GROQ_MODEL if LLM_PROVIDER == 'groq' else LLM_MODEL}")
print(f"VLM Model: {VLM_MODEL}")
print(f"Groq API Key set: {'Yes' if GROQ_API_KEY else 'No'}")
print(f"VLM API Key set: {'Yes' if VLM_API_KEY else 'No'}")
print(f"----------------------------")
