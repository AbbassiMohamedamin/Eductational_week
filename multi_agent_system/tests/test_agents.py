import pytest
from unittest.mock import MagicMock, patch
from agents.vision_agent import VisionAgent
from agents.cognitive_agent import CognitiveAgent
from agents.risk_agent import RiskAgent
from agents.decision_agent import DecisionAgent
from agents.recommendation_agent import RecommendationAgent

def test_vision_agent():
    agent = VisionAgent()
    # Mock tool response
    agent.tool._run = MagicMock(return_value='{"success": true, "data": {"objects": ["knife"], "risk_hint": "Danger"}}')
    result = agent.run("test.jpg")
    assert result["objects"] == ["knife"]

def test_cognitive_agent():
    agent = CognitiveAgent()
    # Mock tool response
    agent.tool._run = MagicMock(return_value='{"success": true, "data": {"name": "Alice", "age": 4}}')
    result = agent.run("child_001")
    assert result["name"] == "Alice"

def test_risk_agent():
    agent = RiskAgent()
    # Mock tool response
    agent.tool._run = MagicMock(return_value='{"success": true, "data": {"risk_score": 0.8}}')
    result = agent.run({"objects": ["knife"]}, {"age": 3})
    assert result["risk_score"] == 0.8

def test_decision_agent():
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = '{"action": "ALERT", "reasoning": "Test", "recommendation": "Check"}'
    mock_llm.invoke.return_value = mock_response
    
    agent = DecisionAgent(llm=mock_llm)
    result = agent.run({}, {"risk_score": 0.9}, {"id": "child_001"}, [])
    assert result["action"] == "ALERT"

def test_recommendation_agent():
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = '{"recommendations": ["test1", "test2"]}'
    mock_llm.invoke.return_value = mock_response
    
    agent = RecommendationAgent(llm=mock_llm)
    result = agent.run({"age": 4}, {"risk_hint": "test"}, {"action": "ALERT"})
    assert len(result["recommendations"]) == 2
