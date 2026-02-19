import uuid
import pytest
from unittest.mock import MagicMock
from app.tools.inventory import ApplianceInventory, get_inventory_summary, confirm_appliance_detection, update_appliance_details


@pytest.fixture(autouse=True)
def reset_inventory():
    """Reset inventory singleton before each test."""
    ApplianceInventory._instance = None
    ApplianceInventory._initialized = False
    yield
    ApplianceInventory._instance = None
    ApplianceInventory._initialized = False


def test_inventory_initialization():
    """Test that inventory initializes empty."""
    inventory = ApplianceInventory()
    assert len(inventory.appliances) == 0
    assert inventory.pending_appliance is None


def test_inventory_singleton():
    """Test that inventory uses singleton pattern."""
    inv1 = ApplianceInventory()
    inv2 = ApplianceInventory()
    inv1.appliances.append({"id": 1, "type": "oven"})
    assert len(inv2.appliances) == 1


@pytest.mark.asyncio
async def test_confirm_appliance_detection_accept():
    """Test confirming a detected appliance."""
    inventory = ApplianceInventory()
    inventory.pending_appliance = {
        "type": "refrigerator",
        "detected_at": "2026-02-19T10:00:00",
    }

    # Create mock ToolContext
    context = MagicMock()
    context.state = {}

    result = confirm_appliance_detection(
        user_wants_to_capture=True,
        tool_context=context
    )

    assert result["status"] == "confirmed"
    assert "appliance_id" in result
    # Appliance should still be pending until details are added
    assert inventory.pending_appliance is not None
    assert inventory.pending_appliance["status"] == "needs_details"


@pytest.mark.asyncio
async def test_confirm_appliance_detection_reject():
    """Test rejecting a detected appliance."""
    inventory = ApplianceInventory()
    inventory.pending_appliance = {"type": "dishwasher"}

    context = MagicMock()
    context.state = {}

    result = confirm_appliance_detection(
        user_wants_to_capture=False,
        tool_context=context
    )

    assert result["status"] == "rejected"
    assert inventory.pending_appliance is None


@pytest.mark.asyncio
async def test_update_appliance_details():
    """Test updating appliance with make and model."""
    inventory = ApplianceInventory()
    appliance_id = str(uuid.uuid4())
    inventory.pending_appliance = {
        "id": appliance_id,
        "type": "oven",
        "status": "needs_details"
    }

    context = MagicMock()
    context.state = {"current_appliance_id": appliance_id}

    result = update_appliance_details(
        make="Samsung",
        model="NE58F9500SS",
        tool_context=context
    )

    assert result["status"] == "completed"
    assert len(inventory.appliances) == 1
    assert inventory.appliances[0]["make"] == "Samsung"
    assert inventory.appliances[0]["model"] == "NE58F9500SS"
    assert inventory.pending_appliance is None
