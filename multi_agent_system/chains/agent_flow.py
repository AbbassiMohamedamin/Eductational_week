import json
from agents.vision_agent import VisionAgent
from agents.cognitive_agent import CognitiveAgent
from agents.risk_agent import RiskAgent
from agents.decision_agent import DecisionAgent
from agents.recommendation_agent import RecommendationAgent
from agents.voice_agent import VoiceAgent
from memory.vector_store import VectorStore

class AgentFlow:
    def __init__(self):
        self.vision_agent = VisionAgent()
        self.cognitive_agent = CognitiveAgent()
        self.risk_agent = RiskAgent()
        self.decision_agent = DecisionAgent()
        self.recommendation_agent = RecommendationAgent()
        self.voice_agent = VoiceAgent()
        self.vector_store = VectorStore()

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
        
        # 5. Memory Retrieval
        query_text = f"Objects: {', '.join(vision_output.get('objects', []))}. Risk: {risk_output.get('severity')}"
        if voice_output:
            query_text += f". Audio: {voice_output.get('transcript')}"
        memory_context = self.vector_store.query(query_text)
        
        # 6. Decision Making
        decision_output = self.decision_agent.run(
            vision_output, 
            risk_output, 
            child_context, 
            memory_context
        )
        
        # 7. Recommendation Generation
        recommendations = self.recommendation_agent.run(child_context, vision_output, decision_output)
        
        # 8. Store in Memory
        event_summary = f"Action: {decision_output.get('action')}. Objects: {vision_output.get('objects')}. Reasoning: {decision_output.get('reasoning')}"
        if voice_output:
            event_summary += f". Voice Transcript: {voice_output.get('transcript')}"
            
        self.vector_store.add(event_summary, {
            "child_id": child_id,
            "risk_score": risk_output.get("risk_score"),
            "severity": risk_output.get("severity")
        })
        
        return {
            "vision": vision_output,
            "cognitive": child_context,
            "voice": voice_output,
            "risk": risk_output,
            "decision": decision_output,
            "recommendations": recommendations.get("recommendations", []),
            "stored_in_memory": True
        }
