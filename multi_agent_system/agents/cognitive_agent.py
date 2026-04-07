import json
from tools.db_tool import DBTool

class CognitiveAgent:
    def __init__(self):
        self.tool = DBTool()

    def run(self, child_id: str) -> dict:
        result_str = self.tool._run(action="get", child_id=child_id)
        result = json.loads(result_str)
        if result["success"]:
            return result["data"]
        # Default if not found
        return {"level": "beginner", "weakness": "unknown", "age": 5}
