import uuid
from unittest.mock import MagicMock

import pytest

from app.tools.inventory import (
    ApplianceInventory,
    confirm_appliance_detection,
    get_inventory_summary,
    update_appliance_details,
)


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


def test_confirm_appliance_detection_accept():
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


def test_confirm_appliance_detection_reject():
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


def test_update_appliance_details():
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


def test_confirm_appliance_detection_no_pending():
    """Test confirming when no appliance is pending."""
    inventory = ApplianceInventory()
    inventory.pending_appliance = None

    context = MagicMock()
    context.state = {}

    result = confirm_appliance_detection(True, context)

    assert result["status"] == "error"
    assert "No pending appliance" in result["message"]


def test_update_appliance_details_no_pending():
    """Test updating details when no appliance is pending."""
    inventory = ApplianceInventory()
    inventory.pending_appliance = None

    context = MagicMock()
    context.state = {"current_appliance_id": "some-id"}

    result = update_appliance_details("Samsung", "ABC123", context)

    assert result["status"] == "error"
    assert "No matching pending appliance" in result["message"]


def test_update_appliance_details_id_mismatch():
    """Test updating details when appliance ID doesn't match."""
    inventory = ApplianceInventory()
    inventory.pending_appliance = {
        "id": "correct-id",
        "type": "oven",
        "status": "needs_details"
    }

    context = MagicMock()
    context.state = {"current_appliance_id": "wrong-id"}

    result = update_appliance_details("Samsung", "ABC123", context)

    assert result["status"] == "error"
    assert "No matching pending appliance" in result["message"]


def test_get_inventory_summary_with_appliances():
    """Test getting summary with appliances in inventory."""
    inventory = ApplianceInventory()
    inventory.appliances = [
        {"id": "1", "type": "oven", "make": "GE", "model": "ABC"},
        {"id": "2", "type": "fridge", "make": "Samsung", "model": "XYZ"}
    ]

    result = get_inventory_summary()

    assert result["status"] == "success"
    assert result["total_appliances"] == 2
    assert len(result["appliances"]) == 2
