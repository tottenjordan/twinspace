"""Appliance inventory management tools."""
import uuid
from datetime import datetime
from typing import Any

from google.adk.tools.tool_context import ToolContext


class ApplianceInventory:
    """Singleton inventory for storing detected appliances."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not ApplianceInventory._initialized:
            self.appliances: list[dict[str, Any]] = []
            self.pending_appliance: dict[str, Any] | None = None
            ApplianceInventory._initialized = True


def get_inventory_summary() -> dict[str, Any]:
    """Get current inventory summary.

    Returns:
        Dictionary containing total count and appliance list.
    """
    inventory = ApplianceInventory()
    return {
        "status": "success",
        "total_appliances": len(inventory.appliances),
        "appliances": inventory.appliances,
    }


def confirm_appliance_detection(
    user_wants_to_capture: bool,
    tool_context: ToolContext
) -> dict[str, Any]:
    """Confirm whether to add detected appliance to inventory.

    Args:
        user_wants_to_capture: True if user confirms detection, False to skip.
        tool_context: ADK tool context for state management.

    Returns:
        Dictionary with confirmation status and next steps.
    """
    inventory = ApplianceInventory()

    if inventory.pending_appliance is None:
        return {
            "status": "error",
            "message": "No pending appliance to confirm"
        }

    if user_wants_to_capture:
        # Generate unique ID and move to needs_details state
        appliance_id = str(uuid.uuid4())
        inventory.pending_appliance["id"] = appliance_id
        inventory.pending_appliance["status"] = "needs_details"
        inventory.pending_appliance["confirmed_at"] = datetime.now().isoformat()

        # Store in context for follow-up
        tool_context.state["current_appliance_id"] = appliance_id

        return {
            "status": "confirmed",
            "appliance_id": appliance_id,
            "message": "Please ask user for make and model information",
            "appliance_type": inventory.pending_appliance["type"]
        }
    else:
        # User rejected, clear pending
        inventory.pending_appliance = None
        return {
            "status": "rejected",
            "message": "Appliance skipped, continuing to scan"
        }


def update_appliance_details(
    make: str,
    model: str,
    tool_context: ToolContext
) -> dict[str, Any]:
    """Update pending appliance with make and model information.

    Args:
        make: Manufacturer/brand name.
        model: Model number or identifier.
        tool_context: ADK tool context for state management.

    Returns:
        Dictionary with update status and appliance details.
    """
    inventory = ApplianceInventory()
    appliance_id = tool_context.state.get("current_appliance_id")

    if inventory.pending_appliance is None or inventory.pending_appliance.get("id") != appliance_id:
        return {
            "status": "error",
            "message": "No matching pending appliance found"
        }

    # Update with details
    inventory.pending_appliance["make"] = make
    inventory.pending_appliance["model"] = model
    inventory.pending_appliance["status"] = "completed"
    inventory.pending_appliance["completed_at"] = datetime.now().isoformat()

    # Move to main inventory
    inventory.appliances.append(inventory.pending_appliance.copy())
    inventory.pending_appliance = None

    # Clear from context
    tool_context.state.pop("current_appliance_id", None)

    return {
        "status": "completed",
        "message": f"Added {make} {model} to inventory",
        "total_appliances": len(inventory.appliances)
    }
