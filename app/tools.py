"""Appliance inventory management tools for Gemini Live API."""
import uuid
from datetime import datetime
from typing import Any


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


# Global session state
_session_state = {
    "user_has_spoken": False,
    "current_appliance_id": None,
}


def detect_appliance(appliance_type: str) -> dict[str, Any]:
    """Record initial detection of an appliance.

    Args:
        appliance_type: Type of appliance detected (e.g., "refrigerator", "oven").

    Returns:
        Dictionary with detection status.
    """
    # GUARD: Only allow detection after user has spoken
    if not _session_state.get("user_has_spoken", False):
        return {
            "status": "error",
            "message": "Wait for user to speak before detecting appliances.",
        }

    inventory = ApplianceInventory()

    # Don't overwrite pending appliance
    if inventory.pending_appliance is not None:
        return {
            "status": "warning",
            "message": "Already processing an appliance. Finish current one first.",
        }

    inventory.pending_appliance = {
        "type": appliance_type,
        "detected_at": datetime.now().isoformat(),
        "status": "pending_confirmation",
    }

    return {
        "status": "detected",
        "message": f"Ask user if they want to add this {appliance_type}",
        "appliance_type": appliance_type,
    }


def get_inventory_summary() -> dict[str, Any]:
    """Get current appliance inventory summary.

    Returns:
        Dictionary containing total count and appliance list.
    """
    # GUARD: Only allow if user has explicitly asked
    if not _session_state.get("user_has_spoken", False):
        return {
            "status": "error",
            "message": "Wait for user to speak before checking inventory.",
        }

    inventory = ApplianceInventory()
    return {
        "status": "success",
        "total_appliances": len(inventory.appliances),
        "appliances": inventory.appliances,
    }


def confirm_appliance_detection(user_wants_to_capture: bool) -> dict[str, Any]:
    """Confirm whether to add detected appliance to inventory.

    Args:
        user_wants_to_capture: True if user confirms detection, False to skip.

    Returns:
        Dictionary with confirmation status and next steps.
    """
    inventory = ApplianceInventory()

    if inventory.pending_appliance is None:
        return {"status": "error", "message": "No pending appliance to confirm"}

    if user_wants_to_capture:
        # Generate unique ID and move to needs_details state
        appliance_id = str(uuid.uuid4())
        inventory.pending_appliance["id"] = appliance_id
        inventory.pending_appliance["status"] = "needs_details"
        inventory.pending_appliance["confirmed_at"] = datetime.now().isoformat()

        # Store in state for follow-up
        _session_state["current_appliance_id"] = appliance_id

        return {
            "status": "confirmed",
            "appliance_id": appliance_id,
            "message": "Please ask user for make and model information",
            "appliance_type": inventory.pending_appliance["type"],
        }
    else:
        # User rejected, clear pending
        inventory.pending_appliance = None
        return {"status": "rejected", "message": "Appliance skipped, continuing to scan"}


def update_appliance_details(make: str, model: str) -> dict[str, Any]:
    """Update pending appliance with make and model information.

    Args:
        make: Manufacturer/brand name.
        model: Model number or identifier.

    Returns:
        Dictionary with update status and appliance details.
    """
    inventory = ApplianceInventory()
    appliance_id = _session_state.get("current_appliance_id")

    if (
        inventory.pending_appliance is None
        or inventory.pending_appliance.get("id") != appliance_id
    ):
        return {"status": "error", "message": "No matching pending appliance found"}

    # Update with details
    inventory.pending_appliance["make"] = make
    inventory.pending_appliance["model"] = model
    inventory.pending_appliance["status"] = "completed"
    inventory.pending_appliance["completed_at"] = datetime.now().isoformat()

    # Move to main inventory
    inventory.appliances.append(inventory.pending_appliance.copy())
    inventory.pending_appliance = None

    # Clear from state
    _session_state["current_appliance_id"] = None

    return {
        "status": "completed",
        "message": f"Added {make} {model} to inventory",
        "total_appliances": len(inventory.appliances),
    }


def mark_user_has_spoken():
    """Mark that the user has spoken (for guard checks)."""
    _session_state["user_has_spoken"] = True


def reset_session():
    """Reset session state for new connection."""
    global _session_state
    _session_state = {
        "user_has_spoken": False,
        "current_appliance_id": None,
    }
