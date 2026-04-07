import json
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from vision_agent_new.vlm_client import SceneContext

class JaisLLMClient:
    def __init__(self, base_url: str, api_key: str, model: str, mock: bool = False):
        self.mock = mock
        self.client = None
        if not mock:
            self.client = ChatOpenAI(
                openai_api_base=base_url,
                openai_api_key=api_key,
                model_name=model,
                temperature=0.7
            )

    def answer(self, question: str, scene_context: SceneContext, language: str) -> str:
        if self.mock:
            return "Try connecting the resistor in series with the LED."
        
        system_prompt = f"""You are a friendly AI tutor helping a child aged 6-14 with their technology project.
The child is currently: {scene_context.description}
They are working on: {scene_context.experiment_type}

Rules:
- Answer in the same language the child used ({language})
- Use simple words a child can understand
- Be encouraging and positive
- If there is a safety concern, address it gently but clearly first
- Keep answers under 3 sentences
- If the child asks in Arabic, respond in Arabic"""

        # InceptionAI Jais integration...
        # response = self.client.invoke([ ... ])
        return "Friendly tutor response placeholder."
