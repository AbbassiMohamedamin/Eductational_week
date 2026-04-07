import os
import base64
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from chains.agent_flow import AgentFlow
from tools.db_tool import DBTool
from config import LLM_MODEL, LLM_PROVIDER, GROQ_MODEL

class AnalyzeRequest(BaseModel):
    image_path: str | None = None
    image_data: str | None = None  # Base64 encoded image
    audio_data: str | None = None  # Base64 encoded audio
    child_id: str

class ChatRequest(BaseModel):
    text_input: str | None = None
    audio_data: str | None = None  # Base64 encoded audio
    child_id: str

# In-memory store for websocket clients
_CLIENTS: list[WebSocket] = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    active_model = GROQ_MODEL if LLM_PROVIDER == "groq" else LLM_MODEL
    print(f"Starting Multi-Agent System with {active_model}")
    yield
    # Shutdown logic
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the dashboard and temporary uploads as static files
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")
app.mount("/temp_uploads", StaticFiles(directory="temp_uploads"), name="temp_uploads")

@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard/auth/sign-in.html")

flow = AgentFlow()
db_tool = DBTool()

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    image_path = request.image_path
    audio_path = None
    
    # If base64 image data is provided, save it to a temporary file
    if request.image_data:
        # Create temp directory if it doesn't exist
        os.makedirs("temp_uploads", exist_ok=True)
        image_path = os.path.join("temp_uploads", f"capture_{request.child_id}.jpg")
        
        # Strip header if present (e.g., data:image/jpeg;base64,...)
        header = "base64,"
        data = request.image_data
        if header in data:
            data = data.split(header)[1]
            
        with open(image_path, "wb") as f:
            f.write(base64.b64decode(data))

    # If base64 audio data is provided, save it to a temporary file
    if request.audio_data:
        os.makedirs("temp_uploads", exist_ok=True)
        audio_path = os.path.join("temp_uploads", f"audio_{request.child_id}.webm")
        
        header = "base64,"
        data = request.audio_data
        if header in data:
            data = data.split(header)[1]
            
        with open(audio_path, "wb") as f:
            f.write(base64.b64decode(data))
            
    if not image_path:
        return {"error": "No image_path or image_data provided"}
        
    result = flow.run(image_path, request.child_id, audio_path)
    
    # Broadcast to all connected clients
    for client in _CLIENTS:
        try:
            await client.send_json(result)
        except:
            _CLIENTS.remove(client)
            
    return result

@app.post("/chat")
async def chat(request: ChatRequest):
    audio_path = None
    
    # If base64 audio data is provided, save it to a temporary file
    if request.audio_data:
        os.makedirs("temp_uploads", exist_ok=True)
        audio_path = os.path.join("temp_uploads", f"chat_audio_{request.child_id}.webm")
        
        header = "base64,"
        data = request.audio_data
        if header in data:
            data = data.split(header)[1]
            
        with open(audio_path, "wb") as f:
            f.write(base64.b64decode(data))
            
    # Run only the voice agent for speed
    voice_agent = flow.voice_agent
    result = voice_agent.run(audio_path, request.child_id, request.text_input)
    
    # Broadcast to all connected clients
    for client in _CLIENTS:
        try:
            await client.send_json({"type": "chat", "data": result})
        except:
            _CLIENTS.remove(client)
            
    return result

@app.get("/health")
async def health():
    return {"status": "ok", "model": LLM_MODEL}

@app.get("/history/{child_id}")
async def history(child_id: str):
    result_str = db_tool._run(action="get_alerts", child_id=child_id)
    result = json.loads(result_str)
    if result["success"]:
        return result["data"]
    return []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _CLIENTS.append(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        _CLIENTS.remove(websocket)
