import json
import os
from typing import Optional, Dict, List
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

class SceneContext(BaseModel):
    description: str
    objects: List[str]
    experiment_type: str
    safety_concern: str

class VLMClient:
    def __init__(self, base_url: str, api_key: str, model: str, mock: bool = False):
        self.mock = mock
        self.client = None
        if not mock:
            self.client = ChatOpenAI(
                openai_api_base=base_url,
                openai_api_key=api_key,
                model_name=model,
                temperature=0.0
            )

    def describe_scene(self, frame_b64: str) -> SceneContext:
        if self.mock:
            return SceneContext(
                description="The child is looking at a circuit board.",
                objects=["resistor", "LED", "battery"],
                experiment_type="electronics",
                safety_concern="none"
            )
        
        system_prompt = "You are an AI assistant helping children aged 6–14 with science and technology projects. Analyse this image and return a JSON description of: what the child is doing, what objects/components you see, what type of experiment it is (electronics/chemistry/robotics/coding/other), and whether there is any safety concern. Be encouraging and child-friendly."
        
        # VLM multimodal call (assuming compatible API)
        # Construct messages...
        # ...
        # (For now, use placeholder for actual multimodal construction)
        # response = self.client.invoke([ ... ])
        
        # Simplified for mock or limited VLM API:
        return SceneContext(
            description="Child working on an experiment.",
            objects=["various"],
            experiment_type="unknown",
            safety_concern="none"
        )
