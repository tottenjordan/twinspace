from unittest.mock import MagicMock

from app.appliance_agent import root_agent
from app.tools.inventory import (
    ApplianceInventory,
    confirm_appliance_detection,
    detect_appliance,
    update_appliance_details,
)


def test_agent_appliance_detection_workflow():
    """Test complete appliance detection workflow."""
    # Agent should be properly configured
    assert root_agent is not None
    assert len(root_agent.tools) == 6


def test_full_inventory_cycle():
    """Test full cycle: detect, confirm, add details."""
    inventory = ApplianceInventory()

    context = MagicMock()
    context.state = {}

    # Step 1: Detect appliance
    result = detect_appliance("oven", context)
    assert result["status"] == "detected"

    # Step 2: Confirm
    result = confirm_appliance_detection(True, context)
    assert result["status"] == "confirmed"

    # Step 3: Add details
    result = update_appliance_details("GE", "JB645RKSS", context)

    assert result["status"] == "completed"
    assert len(inventory.appliances) == 1
    assert inventory.appliances[0]["make"] == "GE"
    assert inventory.appliances[0]["model"] == "JB645RKSS"


def test_multiple_appliances_workflow():
    """Test detecting and adding multiple appliances."""
    inventory = ApplianceInventory()
    context = MagicMock()
    context.state = {}

    # Add first appliance
    detect_appliance("refrigerator", context)
    confirm_appliance_detection(True, context)
    appliance_id_1 = inventory.pending_appliance["id"]
    context.state["current_appliance_id"] = appliance_id_1
    update_appliance_details("Samsung", "RF28R7201SR", context)

    assert len(inventory.appliances) == 1
    assert inventory.appliances[0]["type"] == "refrigerator"

    # Add second appliance
    context.state = {}
    detect_appliance("dishwasher", context)
    confirm_appliance_detection(True, context)
    appliance_id_2 = inventory.pending_appliance["id"]
    context.state["current_appliance_id"] = appliance_id_2
    update_appliance_details("LG", "LDTE5678SS", context)

    assert len(inventory.appliances) == 2
    assert inventory.appliances[1]["type"] == "dishwasher"


def test_workflow_with_rejection():
    """Test workflow where user rejects an appliance."""
    inventory = ApplianceInventory()
    context = MagicMock()
    context.state = {}

    # Detect an appliance
    detect_appliance("microwave", context)
    assert inventory.pending_appliance is not None

    # User rejects it
    result = confirm_appliance_detection(False, context)
    assert result["status"] == "rejected"
    assert inventory.pending_appliance is None
    assert len(inventory.appliances) == 0


def test_agent_tool_integration():
    """Test that agent has all required tools."""
    tool_names = [tool.__name__ if callable(tool) else tool.name for tool in root_agent.tools]

    assert "detect_appliance" in tool_names
    assert "confirm_appliance_detection" in tool_names
    assert "update_appliance_details" in tool_names
    assert "get_inventory_summary" in tool_names
