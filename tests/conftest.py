import pytest

from app.appliance_agent.tools.inventory import ApplianceInventory


@pytest.fixture(autouse=True)
def reset_inventory():
    """Reset inventory singleton before each test."""
    inventory = ApplianceInventory()
    inventory.appliances.clear()
    inventory.pending_appliance = None
    ApplianceInventory._initialized = False
    yield
    inventory.appliances.clear()
    inventory.pending_appliance = None
    ApplianceInventory._initialized = False
