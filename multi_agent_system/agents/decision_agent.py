import json
# from langchain.agents import json
import os
from langchain_groq import ChatGroq
from tools.risk_tool import RiskTool
from tools.db_tool import DBTool
from tools.alert_tool import AlertTool
import config

class DecisionAgent:
    def __init__(self, llm=None):
        if llm:
            self.llm = llm
        elif config.LLM_PROVIDER == "groq" and config.GROQ_API_KEY:
            self.llm = ChatGroq(model=config.GROQ_MODEL, groq_api_key=config.GROQ_API_KEY, temperature=0)
        else:
            self.llm = None
        
        self.tools = [RiskTool(), DBTool(), AlertTool()]
        # self.agent = initialize_agent(
        #     self.tools,
        #     self.llm,
        #     agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        #     verbose=True,
        #     handle_parsing_errors=True
        # )

    def run(self, vision_output: dict, risk_output: dict, child_context: dict, memory_context: list[dict]) -> dict:
        prompt = f"""
        You are a child safety decision AI. 
        
        Vision Data (VLM Description): {vision_output.get('risk_hint')}
        Objects Detected: {json.dumps(vision_output.get('objects', []))}
        Risk Score: {risk_output.get('risk_score')}
        Severity: {risk_output.get('severity')}
        Risk Reasons: {risk_output.get('reasons')}
        Child Context: {json.dumps(child_context)}
        Memory of Past Events: {json.dumps(memory_context)}
        
        Decision Rules:
        - ALERT (risk >= 0.75): Immediate danger. Call alert_tool and log to db_tool.
        - RECOMMEND (risk 0.45-0.75): Potential risk, needs guidance. Log to db_tool.
        - IGNORE (risk < 0.45): Safe environment. Log to db_tool.
        
        Always explain your reasoning.
        If alerting, call alert_tool.
        Always call db_tool to log the decision (action: log_alert, child_id: {child_context.get('id')}).
        
        Return your final answer as a JSON object with:
        "action": "ALERT" | "RECOMMEND" | "IGNORE",
        "reasoning": "Detailed explanation",
        "recommendation": "Brief suggestion for next steps"
        """
        
        try:
            if self.llm is None:
                return {
                    "action": "IGNORE",
                    "reasoning": "DecisionAgent LLM not initialized (missing API key)",
                    "recommendation": "Check configuration"
                }
            # Simplified LLM execution without ReAct for now due to dependency issues
            response = self.llm.invoke(prompt)
            
            # Extract content from response
            if hasattr(response, "content"):
                content = response.content
            else:
                content = str(response)
            
            # Try to parse the response as JSON if possible, otherwise wrap it
            try:
                # Look for JSON block in response
                if "{" in content and "}" in content:
                    json_str = content[content.find("{"):content.rfind("}")+1]
                    return json.loads(json_str)
                return {
                    "action": "RECOMMEND" if risk_output.get("risk_score", 0) >= 0.45 else "IGNORE",
                    "reasoning": content,
                    "recommendation": "Monitor closely"
                }
            except:
                return {
                    "action": "RECOMMEND" if risk_output.get("risk_score", 0) >= 0.45 else "IGNORE",
                    "reasoning": content,
                    "recommendation": "Monitor closely"
                }
        except Exception as e:
            # Fallback if LLM fails
            action = "IGNORE"
            if risk_output.get("risk_score", 0) >= 0.75:
                action = "ALERT"
            elif risk_output.get("risk_score", 0) >= 0.45:
                action = "RECOMMEND"
                
            return {
                "action": action,
                "reasoning": f"Fallback decision due to error: {str(e)}",
                "recommendation": "Manual check advised"
            }
