import json
from typing import Any
from tools.base import BaseAgentTool, AgentToolResult

# In-memory mock DB
_MOCK_DB = {
    "children": {
        "child_001": {"id": "child_001", "name": "Alice", "age": 4, "level": "beginner", "weakness": "curiosity"},
        "child_002": {"id": "child_002", "name": "Bob", "age": 8, "level": "intermediate", "weakness": "attention"}
    },
    "alerts": []
}

class DBTool(BaseAgentTool):
    name: str = "db_tool"
    description: str = "Manages child records and alert history. Input: JSON with action (get|update|log_alert), child_id, and data (optional)."

    def execute(self, **kwargs: Any) -> AgentToolResult:
        try:
            # Handle string input if LangChain passes a single JSON string
            if "input" in kwargs and isinstance(kwargs["input"], str):
                try:
                    data = json.loads(kwargs["input"])
                except json.JSONDecodeError:
                    return AgentToolResult(success=False, error="Invalid JSON input")
            else:
                data = kwargs

            action = data.get("action")
            child_id = data.get("child_id")

            if action == "get":
                if child_id in _MOCK_DB["children"]:
                    return AgentToolResult(success=True, data=_MOCK_DB["children"][child_id])
                return AgentToolResult(success=False, error=f"Child {child_id} not found")

            elif action == "log_alert":
                alert_data = data.get("data", {})
                alert_data["child_id"] = child_id
                _MOCK_DB["alerts"].append(alert_data)
                return AgentToolResult(success=True, data={"alert_logged": True})

            elif action == "update":
                update_data = data.get("data", {})
                if child_id in _MOCK_DB["children"]:
                    _MOCK_DB["children"][child_id].update(update_data)
                    return AgentToolResult(success=True, data=_MOCK_DB["children"][child_id])
                return AgentToolResult(success=False, error=f"Child {child_id} not found")

            elif action == "get_alerts":
                alerts = [a for a in _MOCK_DB["alerts"] if a.get("child_id") == child_id]
                return AgentToolResult(success=True, data=alerts)

            return AgentToolResult(success=False, error=f"Unsupported action: {action}")
        except Exception as e:
            return AgentToolResult(success=False, error=str(e))
