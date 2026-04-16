import os
import base64
import json
import random
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from chains.agent_flow import AgentFlow
from tools.db_tool import DBTool
from config import LLM_MODEL, LLM_PROVIDER, GROQ_MODEL
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

class AnalyzeRequest(BaseModel):
    image_path: str | None = None
    image_data: str | None = None  # Base64 encoded image
    audio_data: str | None = None  # Base64 encoded audio
    child_id: str

class ChatRequest(BaseModel):
    text_input: str | None = None
    audio_data: str | None = None  # Base64 encoded audio
    child_id: str

class QuizRequest(BaseModel):
    topic: str  # basic, safety, experiments, logic, builder
    difficulty: str = "easy"  # easy, medium, hard
    count: int = 4
    language: str = "en"  # en, fr, ar (English, French, Arabic)

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

@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse(url="/dashboard/favicon.svg")

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

    print(
        "[CHAT] child_id=%s transcript=%s voice_url=%s tts_model=%s tts_error=%s"
        % (
            request.child_id,
            "yes" if result.get("transcript") else "no",
            result.get("voice_url"),
            result.get("tts_model"),
            result.get("tts_error"),
        )
    )
    
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

# Quiz generation prompt templates by topic and language
QUIZ_PROMPTS = {
    "en": {
        "basic": """Generate {count} multiple choice questions about basic electricity concepts for children aged 8-12.
Topics: voltage, current, circuits, batteries, how electricity flows.
Make questions educational but fun and easy to understand.

Format the response as a JSON array with this exact structure:
[
  {{
    "q": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 0
  }}
]

Requirements:
- Each question should have exactly 4 options
- Correct answer index must be between 0 and 3
- Questions should be age-appropriate and engaging
- Include a mix of conceptual and practical questions
- Difficulty level: {difficulty}""",

        "safety": """Generate {count} multiple choice questions about electricity safety for children aged 8-12.
Topics: water danger, touching wires, asking adults, safe unplugging, emergency procedures.
Make questions emphasize safety awareness in an engaging way.

Format the response as a JSON array with this exact structure:
[
  {{
    "q": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 0
  }}
]

Requirements:
- Each question should have exactly 4 options
- Correct answer index must be between 0 and 3
- Focus on real-world safety scenarios
- Include "what should you do" type questions
- Difficulty level: {difficulty}""",

        "experiments": """Generate {count} multiple choice questions about simple electricity experiments for children aged 8-12.
Topics: lemon battery, simple circuits, electromagnets, circuit components (LED, switch, resistor, battery).
Make questions about how experiments work and what components do.

Format the response as a JSON array with this exact structure:
[
  {{
    "q": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 0
  }}
]

Requirements:
- Each question should have exactly 4 options
- Correct answer index must be between 0 and 3
- Questions about experiment steps and outcomes
- Include component identification questions
- Difficulty level: {difficulty}""",

        "logic": """Generate {count} multiple choice questions about logic gates for children aged 8-12.
Topics: AND gate, OR gate, NAND gate, NOR gate, truth tables, binary (0 and 1).
Make questions about gate behavior with different input combinations.

Format the response as a JSON array with this exact structure:
[
  {{
    "q": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 0
  }}
]

Requirements:
- Each question should have exactly 4 options
- Correct answer index must be between 0 and 3
- Include questions about: what output when inputs are X and Y
- Mix of AND, OR, NAND, NOR gate questions
- Use binary notation (0 and 1)
- Difficulty level: {difficulty}""",

        "builder": """Generate {count} multiple choice questions about circuit building for children aged 8-12.
Topics: battery function, LED purpose, switch usage, resistor importance, series vs parallel, circuit symbols.
Make questions about how to build and troubleshoot circuits.

Format the response as a JSON array with this exact structure:
[
  {{
    "q": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct": 0
  }}
]

Requirements:
- Each question should have exactly 4 options
- Correct answer index must be between 0 and 3
- Include practical building questions
- Questions about component functions
- Troubleshooting scenarios
- Difficulty level: {difficulty}"""
    },
    "ar": {
        "basic": """أنشئ {count} أسئلة اختيار من متعدد باللغة العربية عن مفاهيم الكهرباء الأساسية للأطفال في سن 8-12 سنة.
المواضيع: الجهد، التيار، الدوائر، البطاريات، كيفية تدفق الكهرباء.
اجعل الأسئلة تعليمية وممتعة وسهلة الفهم.

صيغة الرد كمصفوفة JSON بهذا الهيكل الدقيق:
[
  {{
    "q": "نص السؤال هنا؟",
    "options": ["الخيار أ", "الخيار ب", "الخيار ج", "الخيار د"],
    "correct": 0
  }}
]

المتطلبات:
- كل سؤال يجب أن يحتوي على 4 خيارات بالضبط
- مؤشر الإجابة الصحيحة يجب أن يكون بين 0 و 3
- الأسئلة يجب أن تكون مناسبة للعمر وجذابة
- اخلط بين الأسئلة المفاهيمية والعملية
- مستوى الصعوبة: {difficulty}""",

        "safety": """أنشئ {count} أسئلة اختيار من متعدد باللغة العربية عن سلامة الكهرباء للأطفال في سن 8-12 سنة.
المواضيع: خطر الماء، لمس الأسلاك، طلب المساعدة من الكبار، فصل الأجهزة بأمان، إجراءات الطوارئ.
اجعل الأسئلة تركز على الوعي بالسلامة بطريقة جذابة.

صيغة الرد كمصفوفة JSON بهذا الهيكل الدقيق:
[
  {{
    "q": "نص السؤال هنا؟",
    "options": ["الخيار أ", "الخيار ب", "الخيار ج", "الخيار د"],
    "correct": 0
  }}
]

المتطلبات:
- كل سؤال يجب أن يحتوي على 4 خيارات بالضبط
- مؤشر الإجابة الصحيحة يجب أن يكون بين 0 و 3
- ركز على سيناريوهات السلامة الواقعية
- اخلط بين أسئلة "ماذا يجب أن تفعل"
- مستوى الصعوبة: {difficulty}""",

        "experiments": """أنشئ {count} أسئلة اختيار من متعدد باللغة العربية عن تجارب الكهرباء البسيطة للأطفال في سن 8-12 سنة.
المواضيع: بطارية الليمون، الدوائر البسيطة، المغناطيس الكهربائي، مكونات الدائرة (LED، مفتاح، مقاومة، بطارية).
اجعل الأسئلة عن كيفية عمل التجارب وماذا تفعل المكونات.

صيغة الرد كمصفوفة JSON بهذا الهيكل الدقيق:
[
  {{
    "q": "نص السؤال هنا؟",
    "options": ["الخيار أ", "الخيار ب", "الخيار ج", "الخيار د"],
    "correct": 0
  }}
]

المتطلبات:
- كل سؤال يجب أن يحتوي على 4 خيارات بالضبط
- مؤشر الإجابة الصحيحة يجب أن يكون بين 0 و 3
- أسئلة عن خطوات التجربة ونتائجها
- اخلط بين أسئلة التعرف على المكونات
- مستوى الصعوبة: {difficulty}""",

        "logic": """أنشئ {count} أسئلة اختيار من متعدد باللغة العربية عن البوابات المنطقية للأطفال في سن 8-12 سنة.
المواضيع: بوابة AND، بوابة OR، بوابة NAND، بوابة NOR، جداول الحقيقة، النظام الثنائي (0 و 1).
اجعل الأسئلة عن سلوك البوابات مع مجموعات مختلفة من المدخلات.

صيغة الرد كمصفوفة JSON بهذا الهيكل الدقيق:
[
  {{
    "q": "نص السؤال هنا؟",
    "options": ["الخيار أ", "الخيار ب", "الخيار ج", "الخيار د"],
    "correct": 0
  }}
]

المتطلبات:
- كل سؤال يجب أن يحتوي على 4 خيارات بالضبط
- مؤشر الإجابة الصحيحة يجب أن يكون بين 0 و 3
- اخلط بين أسئلة: ما هو المخرج عندما تكون المدخلات X و Y
- اخلط بين أسئلة بوابات AND و OR و NAND و NOR
- استخدم الترميز الثنائي (0 و 1)
- مستوى الصعوبة: {difficulty}""",

        "builder": """أنشئ {count} أسئلة اختيار من متعدد باللغة العربية عن بناء الدوائر للأطفال في سن 8-12 سنة.
المواضيع: وظيفة البطارية، غرض LED، استخدام المفتاح، أهمية المقاومة، التوصيل التسلسلي والتوازي، رموز الدائرة.
اجعل الأسئلة عن كيفية بناء الدوائر وإصلاحها.

صيغة الرد كمصفوفة JSON بهذا الهيكل الدقيق:
[
  {{
    "q": "نص السؤال هنا؟",
    "options": ["الخيار أ", "الخيار ب", "الخيار ج", "الخيار د"],
    "correct": 0
  }}
]

المتطلبات:
- كل سؤال يجب أن يحتوي على 4 خيارات بالضبط
- مؤشر الإجابة الصحيحة يجب أن يكون بين 0 و 3
- اخلط بين أسئلة البناء العملية
- أسئلة عن وظائف المكونات
- سيناريوهات استكشاف الأخطاء وإصلاحها
- مستوى الصعوبة: {difficulty}"""
    }
}

@app.post("/quiz/generate")
async def generate_quiz(request: QuizRequest):
    """Generate dynamic quiz questions using AI"""
    try:
        # Validate language (default to English)
        lang = request.language if request.language in QUIZ_PROMPTS else "en"
        
        # Validate topic
        if request.topic not in QUIZ_PROMPTS[lang]:
            return {
                "error": f"Invalid topic. Choose from: {', '.join(QUIZ_PROMPTS[lang].keys())}",
                "questions": []
            }
        
        # Initialize LLM with higher temperature for more variety
        llm = ChatGroq(
            model=GROQ_MODEL,
            temperature=0.9,  # Higher temperature for maximum variety
            max_tokens=2000
        )
        
        # Get prompt template for the topic and language
        prompt_template = QUIZ_PROMPTS[lang][request.topic]
        prompt = prompt_template.format(
            count=request.count,
            difficulty=request.difficulty
        )
        
        # Generate questions using random seed for variety
        seed = random.randint(1, 100000)
        random.seed(seed)
        
        # System message based on language
        system_messages = {
            "en": "You are an educational quiz generator. Generate fun quiz questions about electricity for kids. You MUST respond with ONLY a valid JSON array - no other text, no markdown formatting, no explanation. Just the raw JSON array.",
            "ar": "أنت مولد اختبارات تعليمية. أنشئ أسئلة اختبار ممتعة عن الكهرباء للأطفال. يجب أن ترد فقط بمصفوفة JSON صالحة - لا نص آخر، لا تنسيق markdown، لا شرح. فقط مصفوفة JSON الخام."
        }
        
        messages = [
            ("system", system_messages.get(lang, system_messages["en"])),
            ("human", f"{prompt}\n\nMake these questions unique and different from previous ones. Random seed: {seed}")
        ]
        
        print(f"[QUIZ] Generating {request.count} questions for topic: {request.topic} in {lang} (seed: {seed})")
        
        response = llm.invoke(messages)
        content = response.content.strip()
        
        print(f"[QUIZ] Raw response length: {len(content)} chars")
        print(f"[QUIZ] Response preview: {content[:200]}...")
        
        # Handle empty response
        if not content:
            raise ValueError("Empty response from LLM")
        
        # Extract JSON from response (handle potential markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Find JSON array in content (look for [ ... ])
        start_idx = content.find('[')
        end_idx = content.rfind(']')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            content = content[start_idx:end_idx+1]
        
        print(f"[QUIZ] Extracted JSON: {content[:100]}...")
        
        # Parse JSON
        questions = json.loads(content)
        
        # Validate structure
        if not isinstance(questions, list):
            raise ValueError(f"Response is not a list, got: {type(questions)}")
        
        if len(questions) == 0:
            raise ValueError("Empty questions list")
        
        for i, q in enumerate(questions):
            if not all(k in q for k in ["q", "options", "correct"]):
                raise ValueError(f"Question {i} missing required fields: {q.keys()}")
            if len(q["options"]) != 4:
                raise ValueError(f"Question {i} must have exactly 4 options, got {len(q['options'])}")
            if not (0 <= q["correct"] <= 3):
                raise ValueError(f"Question {i} correct answer index must be 0-3, got {q['correct']}")
        
        print(f"[QUIZ] Successfully generated {len(questions)} questions")
        
        return {
            "topic": request.topic,
            "difficulty": request.difficulty,
            "language": lang,
            "questions": questions,
            "seed": seed,
            "ai_generated": True
        }
        
    except Exception as e:
        print(f"[QUIZ ERROR] Failed to generate quiz: {e}")
        # Fallback to static questions if AI generation fails
        fallback_questions = {
            "en": {
                "basic": [
                    {"q": "What pushes electricity through wires?", "options": ["Voltage", "Current", "Resistance", "Power"], "correct": 0},
                    {"q": "What is the unit of electric current?", "options": ["Volts", "Amps", "Watts", "Ohms"], "correct": 1},
                    {"q": "What does a circuit need to work?", "options": ["Only a battery", "Battery, load, and wires", "Just wires", "Only a switch"], "correct": 1},
                    {"q": "If voltage is like water pressure, current is like:", "options": ["Pipe size", "Water amount", "Water color", "Pipe material"], "correct": 1}
                ],
                "safety": [
                    {"q": "What should you do before doing electricity experiments?", "options": ["Start immediately", "Ask an adult", "Use wet hands", "Touch all wires"], "correct": 1},
                    {"q": "Why is water dangerous with electricity?", "options": ["It makes electricity flow", "It changes color", "It smells bad", "It makes noise"], "correct": 0},
                    {"q": "How should you unplug a device?", "options": ["Pull the wire", "Pull the plug", "Cut the wire", "Leave it plugged"], "correct": 1},
                    {"q": "Can you touch exposed wires?", "options": ["Yes, if they look safe", "No, never", "Only with one hand", "Only low voltage"], "correct": 1}
                ],
                "experiments": [
                    {"q": "What do you need for a lemon battery?", "options": ["Just a lemon", "Copper and zinc", "Only water", "Salt and sugar"], "correct": 1},
                    {"q": "What happens when you close a switch in a circuit?", "options": ["The light turns on", "The battery dies", "Nothing happens", "The wire gets hot"], "correct": 0},
                    {"q": "What does an electromagnet need?", "options": ["Just a nail", "Wire wrapped around a nail", "Only a battery", "A magnet"], "correct": 1},
                    {"q": "Which way does electricity flow in a circuit?", "options": ["From + to -", "From - to +", "Both ways", "It does not flow"], "correct": 0}
                ],
                "logic": [
                    {"q": "AND gate output is 1 when:", "options": ["Both inputs are 1", "One input is 1", "No inputs are 1", "Any input is 0"], "correct": 0},
                    {"q": "OR gate output is 0 when:", "options": ["Both inputs are 0", "One input is 1", "Both inputs are 1", "Any input is 1"], "correct": 0},
                    {"q": "NAND is the opposite of:", "options": ["OR", "AND", "NOR", "XOR"], "correct": 1},
                    {"q": "NOR gate output is 1 when:", "options": ["Both inputs are 0", "One input is 1", "Both inputs are 1", "Any input is 1"], "correct": 0}
                ],
                "builder": [
                    {"q": "What does a battery do in a circuit?", "options": ["Stores energy", "Provides power", "Blocks current", "Makes light"], "correct": 1},
                    {"q": "What happens if you don't use a resistor with an LED?", "options": ["LED gets brighter", "LED may burn out", "Nothing happens", "Battery lasts longer"], "correct": 1},
                    {"q": "What does a switch do?", "options": ["Makes power", "Controls flow", "Stores energy", "Changes color"], "correct": 1},
                    {"q": "LED stands for:", "options": ["Light Emitting Diode", "Little Electric Dot", "Light Energy Device", "Low Electricity Drain"], "correct": 0}
                ]
            },
            "ar": {
                "basic": [
                    {"q": "ما الذي يدفع الكهرباء عبر الأسلاك؟", "options": ["الجهد", "التيار", "المقاومة", "القوة"], "correct": 0},
                    {"q": "ما هي وحدة التيار الكهربائي؟", "options": ["فولت", "أمبير", "واط", "أوم"], "correct": 1},
                    {"q": "ماذا يحتاج الدائرة للعمل؟", "options": ["بطارية فقط", "بطارية وحمل وأسلاك", "أسلاك فقط", "مفتاح فقط"], "correct": 1},
                    {"q": "إذا كان الجهد مثل ضغط الماء، فالتيار مثل:", "options": ["حجم الأنبوب", "كمية الماء", "لون الماء", "مادة الأنبوب"], "correct": 1}
                ],
                "safety": [
                    {"q": "ماذا يجب أن تفعل قبل تجارب الكهرباء؟", "options": ["البدء فوراً", "طلب المساعدة من الكبار", "استخدام يدين مبللتين", "لمس جميع الأسلاك"], "correct": 1},
                    {"q": "لماذا الماء خطير مع الكهرباء؟", "options": ["يجعل الكهرباء تتدفق", "يغير اللون", "رائحته سيئة", "يصدر صوتاً"], "correct": 0},
                    {"q": "كيف يجب أن تفصل الجهاز؟", "options": ["سحب السلك", "سحب القابس", "قطع السلك", "تركه موصولاً"], "correct": 1},
                    {"q": "هل يمكنك لمس الأسلاك المكشوفة؟", "options": ["نعم، إذا بدا آمنًا", "لا، أبدًا", "بيد واحدة فقط", "جهد منخفض فقط"], "correct": 1}
                ],
                "experiments": [
                    {"q": "ماذا تحتاج لبطارية الليمون؟", "options": ["ليمونة فقط", "نحاس و زنك", "ماء فقط", "ملح وسكر"], "correct": 1},
                    {"q": "ماذا يحدث عند إغلاق المفتاح في الدائرة؟", "options": ["يضيء الضوء", "تموت البطارية", "لا يحدث شيء", "يسخن السلك"], "correct": 0},
                    {"q": "ماذا يحتاج المغناطيس الكهربائي؟", "options": ["مسمار فقط", "سلك ملفوف حول مسمار", "بطارية فقط", "مغناطيس"], "correct": 1},
                    {"q": "أي اتجاه تتدفق فيه الكهرباء في الدائرة؟", "options": ["من + إلى -", "من - إلى +", "في كلا الاتجاهين", "لا تتدفق"], "correct": 0}
                ],
                "logic": [
                    {"q": "مخرج بوابة AND يساوي 1 عندما:", "options": ["كل المدخلات 1", "مدخل واحد 1", "لا مدخلات 1", "أي مدخل 0"], "correct": 0},
                    {"q": "مخرج بوابة OR يساوي 0 عندما:", "options": ["كل المدخلات 0", "مدخل واحد 1", "كل المدخلات 1", "أي مدخل 1"], "correct": 0},
                    {"q": "NAND هي عكس:", "options": ["OR", "AND", "NOR", "XOR"], "correct": 1},
                    {"q": "مخرج بوابة NOR يساوي 1 عندما:", "options": ["كل المدخلات 0", "مدخل واحد 1", "كل المدخلات 1", "أي مدخل 1"], "correct": 0}
                ],
                "builder": [
                    {"q": "ماذا تفعل البطارية في الدائرة؟", "options": ["تخزن الطاقة", "توفير الطاقة", "تمنع التيار", "تصنع الضوء"], "correct": 1},
                    {"q": "ماذا يحدث إذا لم تستخدم مقاومة مع LED؟", "options": ["LED يصبح أكثر إضاءة", "LED قد يحترق", "لا يحدث شيء", "البطارية تدوم أطول"], "correct": 1},
                    {"q": "ماذا يفعل المفتاح؟", "options": ["يصنع الطاقة", "يتحكم في التدفق", "يخزن الطاقة", "يغير اللون"], "correct": 1},
                    {"q": "LED تعني:", "options": ["ديود باعث للضوء", "نقطة كهربائية صغيرة", "جهاز طاقة ضوئي", "استنزاف كهربائي منخفض"], "correct": 0}
                ]
            }
        }
        
        # Get fallback questions for the requested language
        lang_fallback = fallback_questions.get(lang, fallback_questions["en"])
        
        return {
            "topic": request.topic,
            "difficulty": request.difficulty,
            "language": lang,
            "questions": lang_fallback.get(request.topic, []),
            "fallback": True,
            "error": str(e)
        }

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
