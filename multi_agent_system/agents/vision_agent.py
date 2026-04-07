import json
from tools.vision_tool import VisionTool

class VisionAgent:
    def __init__(self):
        self.tool = VisionTool()

    def run(self, image_path: str) -> dict:
        result_str = self.tool._run(image_path=image_path)
        result = json.loads(result_str)
        if result["success"]:
            return result["data"]
        return {"objects": [], "detections": [], "risk_hint": "Vision analysis failed"}
