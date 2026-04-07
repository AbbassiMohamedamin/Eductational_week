import json
import pytest
from tools.vision_tool import VisionTool
from tools.risk_tool import RiskTool
from tools.db_tool import DBTool
from tools.alert_tool import AlertTool

def test_vision_tool():
    tool = VisionTool()
    result_str = tool._run(image_path="kitchen_scene.jpg")
    result = json.loads(result_str)
    assert result["success"] is True
    assert "objects" in result["data"]
    assert "knife" in result["data"]["objects"]

def test_risk_tool():
    tool = RiskTool()
    
    # High risk
    input_data = {
        "objects": ["knife", "stove"],
        "risk_hint": "Dangerous objects near child",
        "child_context": {"age": 3}
    }
    result_str = tool._run(input=json.dumps(input_data))
    result = json.loads(result_str)
    assert result["success"] is True
    assert result["data"]["risk_score"] >= 0.75
    assert result["data"]["severity"] == "high"

    # Low risk
    input_data = {
        "objects": ["person", "chair"],
        "risk_hint": "Safe scene",
        "child_context": {"age": 10}
    }
    result_str = tool._run(input=json.dumps(input_data))
    result = json.loads(result_str)
    assert result["data"]["severity"] == "low"

def test_db_tool():
    tool = DBTool()
    
    # Get known child
    result_str = tool._run(action="get", child_id="child_001")
    result = json.loads(result_str)
    assert result["success"] is True
    assert result["data"]["name"] == "Alice"

    # Get unknown child
    result_str = tool._run(action="get", child_id="unknown")
    result = json.loads(result_str)
    assert result["success"] is False

    # Log alert
    result_str = tool._run(action="log_alert", child_id="child_001", data={"msg": "test"})
    result = json.loads(result_str)
    assert result["success"] is True

def test_alert_tool():
    tool = AlertTool()
    result_str = tool._run(severity="high", message="Test Alert", child_id="child_001", risk_score=0.9)
    result = json.loads(result_str)
    assert result["success"] is True
    assert result["data"]["alert_sent"] is True
