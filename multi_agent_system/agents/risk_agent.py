import json
from tools.risk_tool import RiskTool

class RiskAgent:
    def __init__(self):
        self.tool = RiskTool()

    def run(self, vision_output: dict, child_context: dict) -> dict:
        input_data = {
            "objects": vision_output.get("objects", []),
            "risk_hint": vision_output.get("risk_hint", ""),
            "child_context": child_context
        }
        result_str = self.tool._run(input=json.dumps(input_data))
        result = json.loads(result_str)
        if result["success"]:
            return result["data"]
        return {"risk_score": 0.0, "severity": "low", "reasons": ["Risk analysis failed"]}
