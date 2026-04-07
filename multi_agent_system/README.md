# Child Safety Multi-Agent System (CS-MAS)

A production-ready LangChain Multi-Agent System for child safety monitoring and adaptive learning.

## Architecture

```text
+----------------+      +-------------------+      +-----------------+
|  Vision Agent  | ---> |  Cognitive Agent  | ---> |   Risk Agent    |
+----------------+      +-------------------+      +-----------------+
                                                           |
                                                           v
+----------------+      +-------------------+      +-----------------+
| Recommendation | <--- |  Decision Agent   | <--- |  Vector Store   |
|     Agent      |      |      (ReAct)      |      |     (FAISS)     |
+----------------+      +-------------------+      +-----------------+
        |                        |
        v                        v
+--------------------------------------------------------------------+
|                        FastAPI + WebSockets                        |
+--------------------------------------------------------------------+
```

## Features

- **Advanced Vision Analysis**: Uses LLaVA (Vision-Language Model) for deep scene understanding and hazard identification.
- **Dual LLM Support**: Optimized for Groq (Qwen 3) for reasoning and recommendations.
- **Adaptive Learning**: Cognitive agent tracks child development level.
- **Context-Aware Decisions**: ReAct agent combines vision descriptions, risk scores, and historical memory.
- **Persistent Memory**: FAISS-based RAG for historical event retrieval.
- **Live Dashboard**: WebSocket-powered real-time alert feed.

## Setup

1. **Clone the repository**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment**:
   Copy `.env.example` to `.env` and add your `OPENAI_API_KEY`.
4. **Run the API**:
   ```bash
   uvicorn api.main:app --reload
   ```
5. **Open Dashboard**:
   Open `dashboard/index.html` in your browser.

## API Endpoints

- `POST /analyze`: Trigger a full safety analysis.
  ```bash
  curl -X POST http://localhost:8000/analyze \
    -H "Content-Type: application/json" \
    -d '{"image_path": "kitchen.jpg", "child_id": "child_001"}'
  ```
- `GET /health`: Check system status.
- `GET /history/{child_id}`: Retrieve alert history.
- `WS /ws`: WebSocket for real-time updates.

## Testing

Run tests with pytest:
```bash
pytest tests/ -v
```

## Docker Deployment

```bash
docker-compose up --build
```
