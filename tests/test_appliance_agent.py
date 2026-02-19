# tests/test_appliance_agent.py
from app.appliance_agent.agent import root_agent


def test_agent_has_required_tools():
    """Test that agent has inventory management and video monitoring tools."""
    tool_names = [tool.__name__ if callable(tool) else tool.name for tool in root_agent.tools]
    assert len(root_agent.tools) == 6
    assert "monitor_video_stream" in tool_names
    assert "request_frame_analysis" in tool_names
    assert "detect_appliance" in tool_names
    assert "confirm_appliance_detection" in tool_names
    assert "update_appliance_details" in tool_names
    assert "get_inventory_summary" in tool_names


def test_agent_configuration():
    """Test agent is configured correctly."""
    assert root_agent.name == "appliance_inventory_agent"
    assert "native-audio" in root_agent.model or "gemini-live" in root_agent.model
    assert root_agent.description is not None
    assert len(root_agent.instruction) > 0
