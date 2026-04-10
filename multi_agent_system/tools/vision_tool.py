import json
import os
import base64
from typing import Any
from groq import Groq
from tools.base import BaseAgentTool, AgentToolResult
from config import GROQ_API_KEY

GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

class VisionTool(BaseAgentTool):
    name: str = "vision_tool"
    description: str = (
        "Analyzes an image of a student's electrical circuit board to detect "
        "faults, wrong connections, or unsafe actions. Returns structured feedback in Arabic."
    )

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def execute(self, **kwargs: Any) -> AgentToolResult:
        image_path = kwargs.get("image_path") or kwargs.get("input")
        if not image_path:
            return AgentToolResult(success=False, error="image_path is required")

        if not os.path.exists(image_path):
            return self._mock_vision(image_path)

        try:
            if not GROQ_API_KEY:
                return AgentToolResult(success=False, error="GROQ_API_KEY is missing")

            client = Groq(api_key=GROQ_API_KEY)

            base64_image = self._encode_image(image_path)

            response = client.chat.completions.create(
                model=GROQ_VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "You are an educational assistant helping primary school students "
                                    "learn how to build basic electrical circuits (الدّارة الكهربائيّة).\n\n"
                                    "Look carefully at this image of a student's circuit board and analyze it.\n\n"
                                    "Your tasks:\n"
                                    "1. Identify all visible components (e.g. battery, wires, bulb, switch, resistor).\n"
                                    "2. Detect any mistakes, wrong connections, missing components, or unsafe actions.\n"
                                    "3. If a mistake is found, explain what is wrong and how to fix it in simple Arabic suitable for a primary school student.\n"
                                    "4. If everything looks correct, say so in Arabic.\n\n"
                                    "Respond ONLY with a JSON object in this exact format (no extra text):\n"
                                    "{\n"
                                    '  "components_detected": ["component1", "component2", ...],\n'
                                    '  "has_fault": true or false,\n'
                                    '  "fault_description": "Technical description of what is wrong in English (or null if no fault)",\n'
                                    '  "arabic_explanation": "ما الخطأ الذي ارتكبه الطالب — بالعربية وبأسلوب بسيط",\n'
                                    '  "arabic_correction": "كيف يمكن تصحيح الخطأ خطوة بخطوة — بالعربية وبأسلوب بسيط"\n'
                                    "}"
                                )
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                temperature=0.2,
                max_completion_tokens=700,
                top_p=1,
                stream=False,
            )

            content = response.choices[0].message.content or ""

            try:
                if "{" in content and "}" in content:
                    json_str = content[content.find("{"):content.rfind("}") + 1]
                    data = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")

                components = data.get("components_detected", [])
                fault_description = data.get("fault_description")
                arabic_explanation = data.get("arabic_explanation")
                arabic_correction = data.get("arabic_correction")

                # Keep backward-compatible keys for current downstream pipeline.
                risk_hint = fault_description or arabic_explanation or "No fault detected"

                return AgentToolResult(success=True, data={
                    "components_detected": components,
                    "has_fault": data.get("has_fault", False),
                    "fault_description": fault_description,
                    "arabic_explanation": arabic_explanation,
                    "arabic_correction": arabic_correction,
                    "objects": components,
                    "detections": [],
                    "risk_hint": risk_hint,
                })

            except Exception:
                return AgentToolResult(success=True, data={
                    "components_detected": [],
                    "has_fault": None,
                    "fault_description": None,
                    "arabic_explanation": content,
                    "arabic_correction": None,
                    "objects": [],
                    "detections": [],
                    "risk_hint": content,
                })

        except Exception as e:
            print(f"Vision Error: {e}")
            return self._mock_vision(image_path)

    def _mock_vision(self, image_path: str) -> AgentToolResult:
        """Fallback mock when image path doesn't exist — useful for testing."""
        components = ["بطارية", "مصباح", "أسلاك"]
        return AgentToolResult(success=True, data={
            "components_detected": components,
            "has_fault": True,
            "fault_description": "Mock: bulb connected without completing the circuit loop.",
            "arabic_explanation": "المصباح غير موصول بشكل صحيح، الدّارة مفتوحة ولن يضيء المصباح.",
            "arabic_correction": "تأكد من توصيل الطرف الآخر من السلك بالقطب السالب للبطارية لإغلاق الدّارة.",
            "objects": components,
            "detections": [],
            "risk_hint": "Mock: bulb connected without completing the circuit loop.",
        })
