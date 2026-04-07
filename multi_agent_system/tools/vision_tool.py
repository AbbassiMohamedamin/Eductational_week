import json
import os
import httpx
import base64
from typing import Any
from openai import OpenAI
from ultralytics import YOLO
from tools.base import BaseAgentTool, AgentToolResult
from config import VLM_API_KEY, VLM_BASE_URL, VLM_MODEL

class VisionTool(BaseAgentTool):
    name: str = "vision_tool"
    description: str = "Analyzes images using YOLO for object detection and a VLM for safety context. Input: image_path (str)."
    _yolo_model: Any = None

    def _get_yolo(self):
        if self._yolo_model is None:
            self._yolo_model = YOLO("yolov8n.pt")
        return self._yolo_model

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def execute(self, **kwargs: Any) -> AgentToolResult:
        image_path = kwargs.get("image_path") or kwargs.get("input")
        if not image_path:
            return AgentToolResult(success=False, error="image_path is required")

        if not os.path.exists(image_path):
            # If path doesn't exist, we fallback to mock
            return self._mock_vision(image_path)

        try:
            # 1. Precise Object Detection with YOLO
            yolo_model = self._get_yolo()
            yolo_results = yolo_model(image_path, verbose=False)
            detected_objects = []
            
            for r in yolo_results:
                boxes = r.boxes
                for box in boxes:
                    # Get coordinates and class info
                    cls = int(box.cls[0])
                    label = yolo_model.names[cls]
                    conf = float(box.conf[0])
                    
                    if conf > 0.3: # Confidence threshold
                        # Normalized coordinates [x1, y1, x2, y2]
                        # r.orig_shape is (h, w)
                        h, w = r.orig_shape
                        coords = box.xyxy[0].tolist()
                        
                        detected_objects.append({
                            "label": label,
                            "confidence": conf,
                            "box": [
                                coords[0] / w, # xmin
                                coords[1] / h, # ymin
                                coords[2] / w, # xmax
                                coords[3] / h  # ymax
                            ]
                        })

            # 2. Safety Analysis with VLM
            http_client = httpx.Client(verify=False)
            client = OpenAI(
                api_key=VLM_API_KEY,
                base_url=VLM_BASE_URL,
                http_client=http_client
            )

            base64_image = self._encode_image(image_path)
            
            # Use detected objects to inform the VLM prompt
            obj_list_str = ", ".join([obj["label"] for obj in detected_objects])
            
            response = client.chat.completions.create(
                model=VLM_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Analyze this image for child safety. Detected objects: {obj_list_str}. Provide a brief safety description. Return JSON with 'description' (string)."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=300,
            )

            content = response.choices[0].message.content
            risk_hint = content
            
            # Try to parse JSON from content
            try:
                if "{" in content and "}" in content:
                    json_str = content[content.find("{"):content.rfind("}")+1]
                    data = json.loads(json_str)
                    risk_hint = data.get("description", content)
            except:
                pass

            return AgentToolResult(success=True, data={
                "objects": [obj["label"] for obj in detected_objects],
                "detections": detected_objects,
                "risk_hint": risk_hint
            })

        except Exception as e:
            print(f"Vision Error: {e}")
            return self._mock_vision(image_path)

    def _mock_vision(self, image_path: str) -> AgentToolResult:
        # Mock logic: detect objects based on filename keywords
        objects = ["person"]
        if "kitchen" in image_path.lower():
            objects.extend(["knife", "stove"])
        if "playground" in image_path.lower():
            objects.extend(["slide", "swing"])
        
        risk_hint = "Mock analysis completed"
        return AgentToolResult(success=True, data={"objects": objects, "risk_hint": risk_hint})
