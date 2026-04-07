import json
import httpx
from typing import Any
from tools.base import BaseAgentTool, AgentToolResult
from config import ALERT_WEBHOOK_URL

class AlertTool(BaseAgentTool):
    name: str = "alert_tool"
    description: str = "Sends alerts to parent console and optional webhook. Input: JSON with severity, message, child_id, risk_score."

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

            severity = data.get("severity", "medium").upper()
            message = data.get("message", "Potential safety concern")
            child_id = data.get("child_id", "unknown")
            risk_score = data.get("risk_score", 0.0)

            # Always print to console
            print(f"\n[ALERT - {severity}] Child: {child_id} | Risk: {risk_score:.2f} | Message: {message}\n")

            webhook_sent = False
            if ALERT_WEBHOOK_URL:
                try:
                    with httpx.Client() as client:
                        response = client.post(ALERT_WEBHOOK_URL, json=data)
                        webhook_sent = response.status_code < 400
                except Exception as e:
                    print(f"Failed to send webhook: {e}")

            return AgentToolResult(success=True, data={
                "alert_sent": True,
                "webhook_sent": webhook_sent
            })
        except Exception as e:
            return AgentToolResult(success=False, error=str(e))
