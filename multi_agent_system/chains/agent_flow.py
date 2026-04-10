from agents.vision_agent import VisionAgent
from agents.cognitive_agent import CognitiveAgent
from agents.risk_agent import RiskAgent
from agents.decision_agent import DecisionAgent
from agents.recommendation_agent import RecommendationAgent
from agents.voice_agent import VoiceAgent

# How many past events to include in the decision agent's context
MEMORY_WINDOW = 5

class AgentFlow:
    def __init__(self):
        self.vision_agent = VisionAgent()
        self.cognitive_agent = CognitiveAgent()
        self.risk_agent = RiskAgent()
        self.decision_agent = DecisionAgent()
        self.recommendation_agent = RecommendationAgent()
        self.voice_agent = VoiceAgent()

        # Simple in-memory event log — no local embedding model needed.
        self._event_log: list[dict] = []

    def _get_recent_events(self, k: int = MEMORY_WINDOW) -> list[dict]:
        """Return the last k events as plain dicts for prompt injection."""
        return self._event_log[-k:]

    def _store_event(
        self,
        decision_output: dict,
        vision_output: dict,
        risk_output: dict,
        voice_output: dict | None,
        child_id: str,
    ):
        """Append a summary of the current run to the in-memory log."""
        event = {
            "child_id": child_id,
            "action": decision_output.get("action"),
            "severity": risk_output.get("severity"),
            "risk_score": risk_output.get("risk_score"),
            "objects": vision_output.get("objects", []),
            "reasoning": decision_output.get("reasoning"),
        }
        if voice_output:
            event["transcript"] = voice_output.get("transcript")

        self._event_log.append(event)

    def run(self, image_path: str, child_id: str, audio_path: str | None = None) -> dict:
        # 1. Vision Analysis
        vision_output = self.vision_agent.run(image_path)
        
        # 2. Cognitive Context
        child_context = self.cognitive_agent.run(child_id)

        # 3. Voice Analysis (if audio provided)
        voice_output = None
        if audio_path:
            voice_output = self.voice_agent.run(audio_path, child_id)
        
        # 4. Risk Assessment
        risk_output = self.risk_agent.run(vision_output, child_context)

        # 5. Memory — last N events passed directly as context
        memory_context = self._get_recent_events()
        
        # 6. Decision Making
        decision_output = self.decision_agent.run(
            vision_output, 
            risk_output, 
            child_context, 
            memory_context
        )
        
        # 7. Recommendation Generation
        recommendations = self.recommendation_agent.run(child_context, vision_output, decision_output)

        # 8. Store current event in memory
        self._store_event(decision_output, vision_output, risk_output, voice_output, child_id)
        
        return {
            "vision": vision_output,
            "cognitive": child_context,
            "voice": voice_output,
            "risk": risk_output,
            "decision": decision_output,
            "recommendations": recommendations.get("recommendations", []),
            "stored_in_memory": True
        }
