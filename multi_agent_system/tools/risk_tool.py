import json
from typing import Any
from tools.base import BaseAgentTool, AgentToolResult

class RiskTool(BaseAgentTool):
    name: str = "risk_tool"
    description: str = "Calculates risk score based on vision output and child context. Input: JSON with objects, risk_hint, child_context."

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

            objects = data.get("objects", [])
            risk_hint = data.get("risk_hint", "")
            child_context = data.get("child_context", {})
            age = child_context.get("age", 10)

            risk_score = 0.0
            reasons = []

            # Scoring logic
            dangerous_objects = ["knife", "scissors", "fire", "lighter", "stove"]
            for obj in objects:
                if obj in dangerous_objects:
                    risk_score += 0.3
                    reasons.append(f"Dangerous object detected: {obj}")

            if any(kw in risk_hint.lower() for kw in ["hazard", "danger", "risk", "hazard"]):
                risk_score += 0.2
                reasons.append("Vision agent flagged potential hazard")

            if age < 6:
                risk_score += 0.15
                reasons.append(f"High-risk age group: {age}")

            risk_score = min(risk_score, 1.0)
            
            severity = "low"
            if risk_score >= 0.75:
                severity = "high"
            elif risk_score >= 0.45:
                severity = "medium"

            return AgentToolResult(success=True, data={
                "risk_score": risk_score,
                "severity": severity,
                "reasons": reasons
            })
        except Exception as e:
            return AgentToolResult(success=False, error=str(e))
