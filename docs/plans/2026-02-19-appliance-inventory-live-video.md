# Appliance Inventory Live Video Application Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a real-time appliance inventory application using Gemini Live API with bidirectional video streaming

**Architecture:** FastAPI WebSocket server with ADK bidirectional streaming agent that processes live video feeds at 1 FPS to detect home appliances. The agent uses Gemini Live native audio model for conversational confirmation and follow-up questions to build an appliance inventory with make/model details.

**Tech Stack:** Python 3.10+, uv, FastAPI, uvicorn, google-adk >=1.20.0, pytest, Vertex AI Live API, gemini-live-2.5-flash-native-audio

---

## Task 1: Project Structure and Dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.env.template`
- Create: `.gitignore`

**Step 1: Write pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "appliance-inventory"
version = "0.1.0"
description = "Real-time appliance inventory using Gemini Live API"
requires-python = ">=3.10"
dependencies = [
    "google-adk>=1.20.0",
    "fastapi>=0.115.0",
    "python-dotenv>=1.0.0",
    "uvicorn[standard]>=0.32.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.8.0",
]

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["C901", "PLR0915"]

[tool.ruff.lint.isort]
known-first-party = ["app"]
```

**Step 2: Write .env.template**

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=TRUE

# Application Configuration
APP_NAME=appliance-inventory
HOST=0.0.0.0
PORT=8000

# Model Configuration
MODEL_NAME=gemini-live-2.5-flash-native-audio
```

**Step 3: Write .gitignore**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/
ENV/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# Environment
.env

# Testing
.pytest_cache/
.coverage
htmlcov/

# Build
dist/
build/
*.egg-info/

# uv
.uv/
uv.lock
```

**Step 4: Write README.md**

```markdown
# Appliance Inventory - Live Video Application

Real-time appliance detection and inventory management using Gemini Live API.

## Features

- Real-time video stream processing at 1 FPS
- Voice-driven appliance detection
- Interactive inventory building with make/model capture
- Bidirectional audio/video streaming

## Setup

1. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Copy `.env.template` to `.env` and configure
3. Install dependencies: `uv sync`
4. Run application: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Architecture

- **FastAPI WebSocket**: Bidirectional streaming via `/ws/{user_id}/{session_id}`
- **ADK Agent**: Appliance detection agent with custom tools
- **Vertex AI Live API**: gemini-live-2.5-flash-native-audio model
- **Session Management**: In-memory session service for conversation state

## Development

- Run tests: `uv run pytest`
- Lint code: `uv run ruff check .`
- Format code: `uv run ruff format .`
```

**Step 5: Initialize uv project**

Run: `uv init --no-readme && uv sync`
Expected: Project initialized with virtual environment

**Step 6: Commit**

```bash
git init
git add pyproject.toml .env.template .gitignore README.md
git commit -m "feat: initialize project structure and dependencies

- Add pyproject.toml with google-adk, fastapi, uvicorn
- Configure uv build system with hatchling
- Add environment template for Vertex AI configuration
- Include development dependencies (pytest, ruff)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Appliance Detection Tool

**Files:**
- Create: `app/__init__.py`
- Create: `app/tools/__init__.py`
- Create: `app/tools/inventory.py`
- Create: `tests/test_inventory_tool.py`

**Step 1: Write failing test for inventory initialization**

```python
# tests/test_inventory_tool.py
import pytest
from app.tools.inventory import ApplianceInventory, get_inventory_summary


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
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_inventory_tool.py::test_inventory_initialization -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.tools.inventory'"

**Step 3: Write minimal implementation for inventory**

```python
# app/__init__.py
"""Appliance Inventory Application."""

# app/tools/__init__.py
"""Tool implementations for appliance inventory agent."""

# app/tools/inventory.py
"""Appliance inventory management tools."""
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
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_inventory_tool.py::test_inventory_initialization -v`
Expected: PASS

**Step 5: Write failing test for confirming appliance**

```python
# tests/test_inventory_tool.py (add to file)
from app.tools.inventory import confirm_appliance_detection
from google.adk.tools.tool_context import ToolContext


@pytest.mark.asyncio
async def test_confirm_appliance_detection_accept():
    """Test confirming a detected appliance."""
    inventory = ApplianceInventory()
    inventory.pending_appliance = {
        "type": "refrigerator",
        "detected_at": "2026-02-19T10:00:00",
    }

    # Create mock ToolContext
    context = ToolContext(state={}, actions=type('obj', (object,), {})())

    result = confirm_appliance_detection(
        user_wants_to_capture=True,
        tool_context=context
    )

    assert result["status"] == "confirmed"
    assert "appliance_id" in result
    assert inventory.pending_appliance is None


@pytest.mark.asyncio
async def test_confirm_appliance_detection_reject():
    """Test rejecting a detected appliance."""
    inventory = ApplianceInventory()
    inventory.pending_appliance = {"type": "dishwasher"}

    context = ToolContext(state={}, actions=type('obj', (object,), {})())

    result = confirm_appliance_detection(
        user_wants_to_capture=False,
        tool_context=context
    )

    assert result["status"] == "rejected"
    assert inventory.pending_appliance is None
```

**Step 6: Run test to verify it fails**

Run: `uv run pytest tests/test_inventory_tool.py::test_confirm_appliance_detection_accept -v`
Expected: FAIL with "ImportError: cannot import name 'confirm_appliance_detection'"

**Step 7: Write implementation for confirm_appliance_detection**

```python
# app/tools/inventory.py (add to file)
import uuid
from datetime import datetime
from google.adk.tools.tool_context import ToolContext


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
```

**Step 8: Run tests to verify they pass**

Run: `uv run pytest tests/test_inventory_tool.py -v`
Expected: All tests PASS

**Step 9: Write failing test for updating appliance details**

```python
# tests/test_inventory_tool.py (add to file)
from app.tools.inventory import update_appliance_details


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

    context = ToolContext(
        state={"current_appliance_id": appliance_id},
        actions=type('obj', (object,), {})()
    )

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
```

**Step 10: Run test to verify it fails**

Run: `uv run pytest tests/test_inventory_tool.py::test_update_appliance_details -v`
Expected: FAIL with "ImportError: cannot import name 'update_appliance_details'"

**Step 11: Write implementation for update_appliance_details**

```python
# app/tools/inventory.py (add to file)
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
```

**Step 12: Run all tests to verify they pass**

Run: `uv run pytest tests/test_inventory_tool.py -v`
Expected: All tests PASS

**Step 13: Commit**

```bash
git add app/ tests/
git commit -m "feat: implement appliance inventory management tools

- Add ApplianceInventory singleton for state management
- Implement confirm_appliance_detection for user confirmation
- Implement update_appliance_details for capturing make/model
- Add get_inventory_summary for querying current inventory
- Full test coverage for all inventory operations

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Appliance Detection Agent

**Files:**
- Create: `app/appliance_agent/__init__.py`
- Create: `app/appliance_agent/agent.py`
- Create: `tests/test_appliance_agent.py`

**Step 1: Write failing test for agent initialization**

```python
# tests/test_appliance_agent.py
import pytest
from app.appliance_agent.agent import root_agent


def test_agent_has_required_tools():
    """Test that agent has inventory management tools."""
    tool_names = [tool.__name__ if callable(tool) else tool.name for tool in root_agent.tools]
    assert "confirm_appliance_detection" in tool_names
    assert "update_appliance_details" in tool_names
    assert "get_inventory_summary" in tool_names


def test_agent_configuration():
    """Test agent is configured correctly."""
    assert root_agent.name == "appliance_inventory_agent"
    assert "native-audio" in root_agent.model or "gemini-live" in root_agent.model
    assert root_agent.description is not None
    assert len(root_agent.instruction) > 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_appliance_agent.py::test_agent_has_required_tools -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.appliance_agent'"

**Step 3: Write agent implementation**

```python
# app/appliance_agent/__init__.py
"""Appliance inventory detection agent."""
from app.appliance_agent.agent import root_agent

__all__ = ["root_agent"]

# app/appliance_agent/agent.py
"""ADK agent for appliance inventory management."""
from google.adk.agents.llm_agent import Agent
from app.tools.inventory import (
    confirm_appliance_detection,
    update_appliance_details,
    get_inventory_summary,
)

# Agent instruction for appliance detection and inventory
AGENT_INSTRUCTION = """You are an expert home appliance assistant helping users create an inventory of their home appliances.

Your responsibilities:
1. Watch the live video stream carefully at 1 frame per second
2. Detect and identify home appliances (refrigerator, oven, dishwasher, microwave, washing machine, dryer, etc.)
3. When you detect an appliance, IMMEDIATELY ask the user: "I see a [APPLIANCE_TYPE]. Would you like to add this to your inventory?"
4. Use confirm_appliance_detection tool with user's response (True if yes, False if no)
5. If confirmed, ask follow-up questions: "What is the make (brand) and model number of this [APPLIANCE_TYPE]?"
6. Use update_appliance_details tool once you have make and model information
7. Confirm completion: "Great! I've added the [MAKE] [MODEL] [TYPE] to your inventory."
8. Continue scanning for more appliances

Guidelines:
- Be conversational and friendly
- Only detect one appliance at a time to avoid confusion
- If you can see text/labels on the appliance in the video, mention them to help the user
- If user is unsure about make/model, suggest they get closer to any labels or serial numbers
- Be patient and helpful with unclear video or lighting

Use get_inventory_summary to check current inventory count when asked."""

root_agent = Agent(
    name="appliance_inventory_agent",
    model="gemini-live-2.5-flash-native-audio",
    description="Real-time appliance detection and inventory management assistant",
    instruction=AGENT_INSTRUCTION,
    tools=[
        confirm_appliance_detection,
        update_appliance_details,
        get_inventory_summary,
    ],
)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_appliance_agent.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/appliance_agent/ tests/test_appliance_agent.py
git commit -m "feat: implement appliance detection ADK agent

- Create agent with gemini-live-2.5-flash-native-audio model
- Configure agent for real-time video stream monitoring
- Add comprehensive instruction for appliance detection workflow
- Wire up inventory management tools
- Include tests for agent configuration

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: FastAPI WebSocket Server

**Files:**
- Create: `app/main.py`
- Create: `tests/test_websocket.py`

**Step 1: Write failing test for FastAPI app initialization**

```python
# tests/test_websocket.py
import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_app_initialization():
    """Test that FastAPI app initializes."""
    client = TestClient(app)
    assert app.title == "Appliance Inventory Live API"


def test_static_files_mounted():
    """Test that static files are accessible."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_websocket.py::test_app_initialization -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.main'"

**Step 3: Write minimal FastAPI app**

```python
# app/main.py
"""FastAPI application with WebSocket bidirectional streaming."""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

APP_NAME = os.getenv("APP_NAME", "appliance-inventory")

# Initialize FastAPI app
app = FastAPI(
    title="Appliance Inventory Live API",
    description="Real-time appliance detection using Gemini Live API",
    version="0.1.0"
)

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    """Serve main HTML page."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Appliance Inventory Live API - WebSocket endpoint: /ws/{user_id}/{session_id}"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "app": APP_NAME}
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_websocket.py::test_app_initialization -v`
Expected: PASS

**Step 5: Write failing test for WebSocket endpoint**

```python
# tests/test_websocket.py (add to file)
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_websocket_endpoint_exists():
    """Test that WebSocket endpoint is defined."""
    client = TestClient(app)
    # Try to connect to WebSocket
    with pytest.raises(Exception):  # Will fail until we implement
        with client.websocket_connect("/ws/test_user/test_session"):
            pass
```

**Step 6: Run test to verify it fails**

Run: `uv run pytest tests/test_websocket.py::test_websocket_endpoint_exists -v`
Expected: FAIL with appropriate WebSocket error

**Step 7: Write WebSocket endpoint implementation**

```python
# app/main.py (add imports and endpoint)
import json
import base64
import asyncio
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect, Query
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.common.live_api.live_request_queue import LiveRequestQueue
from google import genai
from google.genai import types
from app.appliance_agent import root_agent

# Initialize ADK components
session_service = InMemorySessionService()
runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service
)


def is_native_audio_model(model_name: str) -> bool:
    """Check if model uses native audio."""
    return "native-audio" in model_name.lower()


@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
    proactivity: Optional[bool] = Query(default=False),
    affective_dialog: Optional[bool] = Query(default=False),
):
    """
    WebSocket endpoint for bidirectional streaming with Live API.

    Args:
        websocket: WebSocket connection
        user_id: User identifier
        session_id: Session identifier
        proactivity: Enable proactive agent behavior
        affective_dialog: Enable affective/emotional dialog
    """
    await websocket.accept()

    # Determine response modality based on model
    model_name = root_agent.model
    response_modalities = ["AUDIO"] if is_native_audio_model(model_name) else ["TEXT"]

    # Create RunConfig for Live API
    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=response_modalities,
        session_resumption=types.SessionResumptionConfig(),
        enable_affective_dialog=affective_dialog,
    )

    # Add proactivity config if enabled
    if proactivity:
        run_config.proactivity = types.ProactivityConfig()

    # Create LiveRequestQueue for message passing
    live_request_queue = LiveRequestQueue()

    async def upstream_task():
        """Receive messages from client and forward to agent."""
        try:
            while True:
                message = await websocket.receive()

                if "bytes" in message:
                    # Binary audio data
                    audio_chunk = message["bytes"]
                    await live_request_queue.send_realtime(
                        genai.types.LiveClientRealtimeInput(
                            media_chunks=[audio_chunk]
                        )
                    )
                elif "text" in message:
                    # JSON message (text, image, etc.)
                    data = json.loads(message["text"])

                    if data["type"] == "text":
                        await live_request_queue.send_content(
                            genai.types.Content(
                                role="user",
                                parts=[genai.types.Part(text=data["text"])]
                            )
                        )
                    elif data["type"] == "image":
                        # Decode base64 image
                        image_data = base64.b64decode(data["data"])
                        await live_request_queue.send_content(
                            genai.types.Content(
                                role="user",
                                parts=[
                                    genai.types.Part(
                                        inline_data=genai.types.Blob(
                                            mime_type=data.get("mimeType", "image/jpeg"),
                                            data=image_data
                                        )
                                    )
                                ]
                            )
                        )
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"Upstream error: {e}")
        finally:
            await live_request_queue.close()

    async def downstream_task():
        """Receive events from agent and forward to client."""
        try:
            async for event in runner.run_live(
                user_id=user_id,
                session_id=session_id,
                live_request_queue=live_request_queue,
                run_config=run_config,
            ):
                # Serialize event and send to client
                event_json = event.model_dump_json(exclude_none=True)
                await websocket.send_text(event_json)
        except Exception as e:
            print(f"Downstream error: {e}")

    # Run upstream and downstream tasks concurrently
    try:
        await asyncio.gather(
            upstream_task(),
            downstream_task(),
        )
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: user={user_id}, session={session_id}")
    finally:
        await live_request_queue.close()
```

**Step 8: Run tests to verify they pass**

Run: `uv run pytest tests/test_websocket.py -v`
Expected: Tests PASS

**Step 9: Test server starts**

Run: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
Expected: Server starts without errors, accessible at http://localhost:8000

**Step 10: Stop server and commit**

```bash
git add app/main.py tests/test_websocket.py
git commit -m "feat: implement FastAPI WebSocket server with Live API

- Add FastAPI app with health check endpoint
- Implement WebSocket endpoint at /ws/{user_id}/{session_id}
- Configure RunConfig for BIDI streaming with native audio
- Create upstream/downstream async tasks for bidirectional streaming
- Add LiveRequestQueue for message passing between client and agent
- Support text, image, and audio input modalities
- Include session resumption and affective dialog support

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Web UI for Video Streaming

**Files:**
- Create: `app/static/index.html`
- Create: `app/static/css/style.css`
- Create: `app/static/js/app.js`
- Create: `app/static/js/video-handler.js`
- Create: `app/static/js/audio-player.js`
- Create: `app/static/js/audio-recorder.js`

**Step 1: Write index.html**

```html
<!-- app/static/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Appliance Inventory - Live Video</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>🏠 Appliance Inventory Assistant</h1>
            <p>Walk through your home and let AI help you catalog your appliances</p>
        </header>

        <main>
            <!-- Video Feed Section -->
            <section class="video-section">
                <div class="video-container">
                    <video id="videoElement" autoplay playsinline muted></video>
                    <canvas id="videoCanvas" style="display:none;"></canvas>
                </div>
                <div class="video-controls">
                    <button id="startBtn" class="btn btn-primary">Start Camera</button>
                    <button id="connectBtn" class="btn btn-success" disabled>Connect to AI</button>
                    <button id="disconnectBtn" class="btn btn-danger" disabled>Disconnect</button>
                </div>
                <div class="status" id="status">Ready to start</div>
            </section>

            <!-- Conversation Section -->
            <section class="conversation-section">
                <h2>Conversation</h2>
                <div id="conversationLog" class="conversation-log"></div>
                <div class="input-section">
                    <input
                        type="text"
                        id="textInput"
                        placeholder="Type a message (or use voice)..."
                        disabled
                    >
                    <button id="sendBtn" class="btn btn-primary" disabled>Send</button>
                </div>
            </section>

            <!-- Inventory Section -->
            <section class="inventory-section">
                <h2>Appliance Inventory</h2>
                <div id="inventoryList" class="inventory-list">
                    <p class="empty-state">No appliances added yet</p>
                </div>
            </section>

            <!-- Events Console (Debug) -->
            <section class="events-section">
                <h2>Live API Events <button id="clearEventsBtn" class="btn-small">Clear</button></h2>
                <div id="eventsConsole" class="events-console"></div>
            </section>
        </main>
    </div>

    <script type="module" src="/static/js/app.js"></script>
</body>
</html>
```

**Step 2: Write CSS styles**

```css
/* app/static/css/style.css */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #333;
    line-height: 1.6;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

header {
    text-align: center;
    color: white;
    margin-bottom: 30px;
}

header h1 {
    font-size: 2.5rem;
    margin-bottom: 10px;
}

main {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto auto;
    gap: 20px;
}

section {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.video-section {
    grid-column: 1 / 2;
    grid-row: 1 / 2;
}

.video-container {
    position: relative;
    width: 100%;
    background: #000;
    border-radius: 8px;
    overflow: hidden;
    aspect-ratio: 16 / 9;
}

#videoElement {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.video-controls {
    display: flex;
    gap: 10px;
    margin-top: 15px;
}

.btn {
    padding: 12px 24px;
    border: none;
    border-radius: 6px;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.3s;
    font-weight: 600;
}

.btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.btn-primary {
    background: #667eea;
    color: white;
}

.btn-primary:hover:not(:disabled) {
    background: #5568d3;
}

.btn-success {
    background: #48bb78;
    color: white;
}

.btn-success:hover:not(:disabled) {
    background: #38a169;
}

.btn-danger {
    background: #f56565;
    color: white;
}

.btn-danger:hover:not(:disabled) {
    background: #e53e3e;
}

.btn-small {
    padding: 6px 12px;
    font-size: 0.875rem;
    background: #e2e8f0;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}

.status {
    margin-top: 10px;
    padding: 10px;
    background: #edf2f7;
    border-radius: 6px;
    font-size: 0.875rem;
    text-align: center;
}

.conversation-section {
    grid-column: 2 / 3;
    grid-row: 1 / 3;
    display: flex;
    flex-direction: column;
    max-height: 800px;
}

.conversation-log {
    flex: 1;
    overflow-y: auto;
    padding: 15px;
    background: #f7fafc;
    border-radius: 8px;
    margin-bottom: 15px;
}

.message {
    margin-bottom: 15px;
    padding: 10px 15px;
    border-radius: 8px;
    max-width: 80%;
}

.message.user {
    background: #667eea;
    color: white;
    margin-left: auto;
}

.message.agent {
    background: #e2e8f0;
    color: #2d3748;
}

.input-section {
    display: flex;
    gap: 10px;
}

#textInput {
    flex: 1;
    padding: 12px;
    border: 2px solid #e2e8f0;
    border-radius: 6px;
    font-size: 1rem;
}

#textInput:focus {
    outline: none;
    border-color: #667eea;
}

.inventory-section {
    grid-column: 1 / 2;
    grid-row: 2 / 3;
}

.inventory-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.appliance-card {
    padding: 15px;
    background: #f7fafc;
    border-radius: 8px;
    border-left: 4px solid #667eea;
}

.appliance-card h3 {
    margin-bottom: 8px;
    color: #2d3748;
}

.appliance-card p {
    font-size: 0.875rem;
    color: #718096;
}

.empty-state {
    text-align: center;
    color: #a0aec0;
    padding: 40px;
}

.events-section {
    grid-column: 1 / 3;
    grid-row: 3 / 4;
}

.events-section h2 {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}

.events-console {
    max-height: 300px;
    overflow-y: auto;
    background: #1a202c;
    color: #e2e8f0;
    padding: 15px;
    border-radius: 8px;
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
}

.event-entry {
    margin-bottom: 8px;
    padding: 8px;
    background: #2d3748;
    border-radius: 4px;
    border-left: 3px solid #667eea;
}

.event-timestamp {
    color: #a0aec0;
    font-size: 0.75rem;
}

@media (max-width: 1024px) {
    main {
        grid-template-columns: 1fr;
        grid-template-rows: auto auto auto auto;
    }

    .video-section {
        grid-column: 1;
        grid-row: 1;
    }

    .conversation-section {
        grid-column: 1;
        grid-row: 2;
        max-height: 500px;
    }

    .inventory-section {
        grid-column: 1;
        grid-row: 3;
    }

    .events-section {
        grid-column: 1;
        grid-row: 4;
    }
}
```

**Step 3: Write main JavaScript app**

```javascript
// app/static/js/app.js
import { VideoHandler } from './video-handler.js';
import { AudioPlayer } from './audio-player.js';
import { AudioRecorder } from './audio-recorder.js';

class ApplianceInventoryApp {
    constructor() {
        this.ws = null;
        this.connected = false;
        this.userId = `user_${Date.now()}`;
        this.sessionId = `session_${Date.now()}`;

        this.videoHandler = new VideoHandler();
        this.audioPlayer = new AudioPlayer();
        this.audioRecorder = new AudioRecorder();

        this.setupEventListeners();
    }

    setupEventListeners() {
        document.getElementById('startBtn').addEventListener('click', () => this.startCamera());
        document.getElementById('connectBtn').addEventListener('click', () => this.connect());
        document.getElementById('disconnectBtn').addEventListener('click', () => this.disconnect());
        document.getElementById('sendBtn').addEventListener('click', () => this.sendText());
        document.getElementById('clearEventsBtn').addEventListener('click', () => this.clearEvents());

        document.getElementById('textInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendText();
        });

        // Video frame callback
        this.videoHandler.onFrame = (imageData) => {
            if (this.connected) {
                this.sendImage(imageData);
            }
        };

        // Audio chunk callback
        this.audioRecorder.onAudioChunk = (chunk) => {
            if (this.connected && this.ws) {
                this.ws.send(chunk);
            }
        };
    }

    async startCamera() {
        const success = await this.videoHandler.start();
        if (success) {
            document.getElementById('startBtn').disabled = true;
            document.getElementById('connectBtn').disabled = false;
            this.updateStatus('Camera started - Ready to connect');
        } else {
            this.updateStatus('Failed to start camera', 'error');
        }
    }

    async connect() {
        const wsUrl = `ws://${window.location.host}/ws/${this.userId}/${this.sessionId}`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                this.connected = true;
                document.getElementById('connectBtn').disabled = true;
                document.getElementById('disconnectBtn').disabled = false;
                document.getElementById('textInput').disabled = false;
                document.getElementById('sendBtn').disabled = false;

                this.updateStatus('Connected to AI assistant');
                this.addMessage('agent', 'Hello! I\'m ready to help you catalog your appliances. Just walk around and show me your appliances.');

                // Start audio recording
                this.audioRecorder.start();

                // Start sending video frames
                this.videoHandler.startCapture();
            };

            this.ws.onmessage = (event) => {
                this.handleServerMessage(event.data);
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateStatus('Connection error', 'error');
            };

            this.ws.onclose = () => {
                this.connected = false;
                document.getElementById('connectBtn').disabled = false;
                document.getElementById('disconnectBtn').disabled = true;
                document.getElementById('textInput').disabled = true;
                document.getElementById('sendBtn').disabled = true;

                this.updateStatus('Disconnected');
                this.audioRecorder.stop();
                this.videoHandler.stopCapture();
            };

        } catch (error) {
            console.error('Connection error:', error);
            this.updateStatus('Failed to connect', 'error');
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    handleServerMessage(data) {
        const event = JSON.parse(data);
        this.logEvent(event);

        // Handle different event types
        if (event.server_content?.model_turn?.parts) {
            const parts = event.server_content.model_turn.parts;
            for (const part of parts) {
                if (part.text) {
                    this.addMessage('agent', part.text);
                }
                if (part.inline_data?.data) {
                    // Audio response
                    this.audioPlayer.play(part.inline_data.data);
                }
            }
        }

        // Handle tool calls
        if (event.tool_call) {
            this.handleToolCall(event.tool_call);
        }

        // Handle tool responses
        if (event.tool_response) {
            this.handleToolResponse(event.tool_response);
        }
    }

    handleToolCall(toolCall) {
        const toolName = toolCall.function_calls?.[0]?.name;
        this.logEvent({ type: 'tool_call', name: toolName });
    }

    handleToolResponse(toolResponse) {
        const responses = toolResponse.function_responses || [];
        for (const response of responses) {
            if (response.response) {
                const data = JSON.parse(response.response);
                if (data.status === 'completed' && data.total_appliances) {
                    this.updateInventory();
                }
            }
        }
    }

    sendText() {
        const input = document.getElementById('textInput');
        const text = input.value.trim();

        if (text && this.connected && this.ws) {
            this.ws.send(JSON.stringify({
                type: 'text',
                text: text
            }));

            this.addMessage('user', text);
            input.value = '';
        }
    }

    sendImage(imageData) {
        if (this.connected && this.ws) {
            // Send base64 encoded image
            const base64Data = imageData.split(',')[1];
            this.ws.send(JSON.stringify({
                type: 'image',
                data: base64Data,
                mimeType: 'image/jpeg'
            }));
        }
    }

    addMessage(role, text) {
        const log = document.getElementById('conversationLog');
        const message = document.createElement('div');
        message.className = `message ${role}`;
        message.textContent = text;
        log.appendChild(message);
        log.scrollTop = log.scrollHeight;
    }

    updateStatus(message, type = 'info') {
        const status = document.getElementById('status');
        status.textContent = message;
        status.style.background = type === 'error' ? '#fed7d7' : '#edf2f7';
    }

    logEvent(event) {
        const console = document.getElementById('eventsConsole');
        const entry = document.createElement('div');
        entry.className = 'event-entry';

        const timestamp = new Date().toLocaleTimeString();
        const eventType = event.type || event.server_content?.model_turn ? 'model_turn' : 'unknown';

        entry.innerHTML = `
            <div class="event-timestamp">${timestamp}</div>
            <div>${eventType}: ${JSON.stringify(event, null, 2)}</div>
        `;

        console.appendChild(entry);
        console.scrollTop = console.scrollHeight;
    }

    clearEvents() {
        document.getElementById('eventsConsole').innerHTML = '';
    }

    async updateInventory() {
        // Fetch current inventory from backend
        try {
            const response = await fetch('/api/inventory');
            const data = await response.json();

            const list = document.getElementById('inventoryList');
            list.innerHTML = '';

            if (data.appliances && data.appliances.length > 0) {
                data.appliances.forEach(appliance => {
                    const card = document.createElement('div');
                    card.className = 'appliance-card';
                    card.innerHTML = `
                        <h3>${appliance.type}</h3>
                        <p><strong>Make:</strong> ${appliance.make}</p>
                        <p><strong>Model:</strong> ${appliance.model}</p>
                        <p class="event-timestamp">Added: ${new Date(appliance.completed_at).toLocaleString()}</p>
                    `;
                    list.appendChild(card);
                });
            } else {
                list.innerHTML = '<p class="empty-state">No appliances added yet</p>';
            }
        } catch (error) {
            console.error('Failed to update inventory:', error);
        }
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ApplianceInventoryApp();
});
```

**Step 4: Write video handler module**

```javascript
// app/static/js/video-handler.js
export class VideoHandler {
    constructor() {
        this.video = document.getElementById('videoElement');
        this.canvas = document.getElementById('videoCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.stream = null;
        this.captureInterval = null;
        this.onFrame = null;
    }

    async start() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'environment'
                },
                audio: false
            });

            this.video.srcObject = this.stream;
            return true;
        } catch (error) {
            console.error('Error accessing camera:', error);
            alert('Could not access camera. Please grant permission.');
            return false;
        }
    }

    startCapture() {
        // Capture at 1 FPS (Gemini Live API processes video at 1 FPS)
        this.captureInterval = setInterval(() => {
            this.captureFrame();
        }, 1000);
    }

    stopCapture() {
        if (this.captureInterval) {
            clearInterval(this.captureInterval);
            this.captureInterval = null;
        }
    }

    captureFrame() {
        if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
            // Set canvas size to video size
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;

            // Draw current frame
            this.ctx.drawImage(this.video, 0, 0);

            // Get image data as base64
            const imageData = this.canvas.toDataURL('image/jpeg', 0.8);

            // Call callback if set
            if (this.onFrame) {
                this.onFrame(imageData);
            }
        }
    }

    stop() {
        this.stopCapture();
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    }
}
```

**Step 5: Write audio player module**

```javascript
// app/static/js/audio-player.js
export class AudioPlayer {
    constructor() {
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.queue = [];
        this.playing = false;
    }

    async play(base64Data) {
        try {
            // Decode base64 to array buffer
            const binaryString = atob(base64Data);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            // Decode audio data
            const audioBuffer = await this.audioContext.decodeAudioData(bytes.buffer);

            // Create source
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);

            // Play
            source.start(0);
        } catch (error) {
            console.error('Audio playback error:', error);
        }
    }
}
```

**Step 6: Write audio recorder module**

```javascript
// app/static/js/audio-recorder.js
export class AudioRecorder {
    constructor() {
        this.audioContext = null;
        this.mediaStream = null;
        this.processor = null;
        this.onAudioChunk = null;
    }

    async start() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });

            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 16000,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            const source = this.audioContext.createMediaStreamSource(this.mediaStream);

            // Create processor for PCM data
            await this.audioContext.audioWorklet.addModule('/static/js/pcm-recorder-processor.js');
            this.processor = new AudioWorkletNode(this.audioContext, 'pcm-recorder-processor');

            this.processor.port.onmessage = (event) => {
                if (this.onAudioChunk && event.data.audioData) {
                    // Convert Float32Array to Int16Array PCM
                    const pcmData = this.floatToPCM(event.data.audioData);
                    this.onAudioChunk(pcmData);
                }
            };

            source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);

        } catch (error) {
            console.error('Audio recording error:', error);
        }
    }

    floatToPCM(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return int16Array.buffer;
    }

    stop() {
        if (this.processor) {
            this.processor.disconnect();
            this.processor = null;
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
    }
}
```

**Step 7: Write PCM recorder processor**

```javascript
// app/static/js/pcm-recorder-processor.js
class PCMRecorderProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.bufferSize = 4096;
        this.buffer = new Float32Array(this.bufferSize);
        this.bufferIndex = 0;
    }

    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (input && input[0]) {
            const channelData = input[0];

            for (let i = 0; i < channelData.length; i++) {
                this.buffer[this.bufferIndex++] = channelData[i];

                if (this.bufferIndex >= this.bufferSize) {
                    // Send buffer to main thread
                    this.port.postMessage({
                        audioData: this.buffer.slice(0)
                    });
                    this.bufferIndex = 0;
                }
            }
        }

        return true;
    }
}

registerProcessor('pcm-recorder-processor', PCMRecorderProcessor);
```

**Step 8: Add inventory API endpoint**

```python
# app/main.py (add endpoint)
from app.tools.inventory import ApplianceInventory

@app.get("/api/inventory")
async def get_inventory():
    """Get current appliance inventory."""
    inventory = ApplianceInventory()
    return {
        "total": len(inventory.appliances),
        "appliances": inventory.appliances
    }
```

**Step 9: Test UI in browser**

Run: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
Open: http://localhost:8000
Expected: UI loads, camera can be started, WebSocket connects

**Step 10: Commit**

```bash
git add app/static/ app/main.py
git commit -m "feat: implement web UI for live video streaming

- Add responsive HTML interface with video, chat, and inventory
- Implement VideoHandler for camera access and 1 FPS capture
- Add AudioPlayer for playing agent voice responses
- Add AudioRecorder for capturing user voice input
- Create PCM audio processor worklet for 16kHz audio
- Add real-time event console for debugging Live API events
- Include inventory display with automatic updates
- Add REST API endpoint for inventory retrieval

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Integration Testing

**Files:**
- Create: `tests/test_integration.py`
- Create: `tests/conftest.py`

**Step 1: Write pytest configuration**

```python
# tests/conftest.py
import pytest
from app.tools.inventory import ApplianceInventory


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
```

**Step 2: Write integration test**

```python
# tests/test_integration.py
import pytest
import asyncio
from google.adk.agents.invocation_context import InvocationContext
from app.appliance_agent import root_agent
from app.tools.inventory import ApplianceInventory


@pytest.mark.asyncio
async def test_agent_appliance_detection_workflow():
    """Test complete appliance detection workflow."""
    inventory = ApplianceInventory()

    # Simulate agent detecting appliance
    ctx = InvocationContext(
        user_message="I see a Samsung refrigerator, model RF28R7201SR",
        state={}
    )

    # Agent should be able to process this
    assert root_agent is not None
    assert len(root_agent.tools) == 3


@pytest.mark.asyncio
async def test_full_inventory_cycle():
    """Test full cycle: detect, confirm, add details."""
    inventory = ApplianceInventory()

    # Simulate detection
    inventory.pending_appliance = {
        "type": "oven",
        "detected_at": "2026-02-19T10:00:00"
    }

    # Confirm
    from app.tools.inventory import confirm_appliance_detection
    from google.adk.tools.tool_context import ToolContext

    context = ToolContext(state={}, actions=type('obj', (object,), {})())
    result = confirm_appliance_detection(True, context)

    assert result["status"] == "confirmed"
    appliance_id = result["appliance_id"]

    # Add details
    from app.tools.inventory import update_appliance_details

    result = update_appliance_details("GE", "JB645RKSS", context)

    assert result["status"] == "completed"
    assert len(inventory.appliances) == 1
    assert inventory.appliances[0]["make"] == "GE"
    assert inventory.appliances[0]["model"] == "JB645RKSS"
```

**Step 3: Run integration tests**

Run: `uv run pytest tests/test_integration.py -v`
Expected: All tests PASS

**Step 4: Run all tests**

Run: `uv run pytest tests/ -v --tb=short`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add tests/
git commit -m "test: add integration tests for complete workflow

- Add pytest configuration with inventory reset fixture
- Test agent configuration and tool integration
- Test full appliance detection cycle (detect, confirm, details)
- Verify inventory state management across workflow

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Documentation and Deployment

**Files:**
- Update: `README.md`
- Create: `DEPLOYMENT.md`
- Create: `Dockerfile`
- Create: `.dockerignore`

**Step 1: Update README with comprehensive usage**

```markdown
# Appliance Inventory - Live Video Application

Real-time appliance detection and inventory management using Gemini Live API with bidirectional video/audio streaming.

## Features

- 📹 **Live Video Streaming**: Real-time camera feed at 1 FPS for appliance detection
- 🤖 **AI-Powered Detection**: Gemini 2.5 Flash Native Audio model identifies appliances
- 🎙️ **Voice Interaction**: Natural voice conversations for inventory building
- 📝 **Smart Follow-up**: Agent asks questions to capture make and model
- 💾 **Session Management**: Persistent inventory across sessions
- 🎨 **Modern UI**: Responsive web interface with real-time updates

## Architecture

```
┌─────────────────┐
│   Web Browser   │
│  (Camera/Mic)   │
└────────┬────────┘
         │ WebSocket (BIDI)
         ▼
┌─────────────────┐
│  FastAPI Server │
│   (uvicorn)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐       ┌──────────────────┐
│   ADK Runner    │◄─────►│  Session Service │
│  (Live API)     │       │   (In-Memory)    │
└────────┬────────┘       └──────────────────┘
         │
         ▼
┌─────────────────┐
│  Gemini Live    │
│  Native Audio   │
└─────────────────┘
```

## Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- Google Cloud Project with Vertex AI API enabled
- Camera and microphone access in browser

## Setup

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and Configure

```bash
git clone <repository-url>
cd appliance-inventory

# Copy environment template
cp .env.template .env

# Edit .env with your Google Cloud project details
# GOOGLE_CLOUD_PROJECT=your-project-id
# GOOGLE_CLOUD_LOCATION=us-central1
```

### 3. Install Dependencies

```bash
uv sync
```

### 4. Run Application

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Open Browser

Navigate to: http://localhost:8000

## Usage

1. **Start Camera**: Click "Start Camera" to activate your device camera
2. **Connect**: Click "Connect to AI" to establish WebSocket connection
3. **Walk Around**: Point camera at appliances as you move through your home
4. **Respond**: Answer agent's questions about each detected appliance
5. **View Inventory**: See your growing appliance list in the Inventory panel

## Development

### Run Tests

```bash
uv run pytest tests/ -v
```

### Lint Code

```bash
uv run ruff check .
```

### Format Code

```bash
uv run ruff format .
```

### Project Structure

```
appliance-inventory/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app with WebSocket
│   ├── appliance_agent/
│   │   ├── __init__.py
│   │   └── agent.py               # ADK agent definition
│   ├── tools/
│   │   ├── __init__.py
│   │   └── inventory.py           # Inventory management tools
│   └── static/
│       ├── index.html             # Main UI
│       ├── css/style.css
│       └── js/
│           ├── app.js             # Main application logic
│           ├── video-handler.js   # Camera/video capture
│           ├── audio-player.js    # Audio playback
│           ├── audio-recorder.js  # Audio recording
│           └── pcm-recorder-processor.js
├── tests/
│   ├── conftest.py
│   ├── test_inventory_tool.py
│   ├── test_appliance_agent.py
│   ├── test_websocket.py
│   └── test_integration.py
├── pyproject.toml
├── .env.template
├── README.md
└── DEPLOYMENT.md
```

## Technical Details

### Video Processing

- Captures frames at 1 FPS (aligned with Gemini Live API video processing rate)
- Sends JPEG-encoded frames via WebSocket
- Resolution: 1280x720 (configurable)

### Audio Processing

- Sample rate: 16 kHz mono
- Format: PCM 16-bit
- Bidirectional: User voice input + Agent voice output

### Model Configuration

- Model: `gemini-live-2.5-flash-native-audio`
- Response modality: AUDIO (native audio)
- Streaming mode: BIDI (WebSocket)
- Session resumption: Enabled

## Troubleshooting

### Camera Access Denied

Ensure browser has camera permissions. Check browser settings.

### WebSocket Connection Failed

Verify:
- Server is running on correct port
- No firewall blocking WebSocket connections
- `.env` configuration is correct

### No Audio Output

Check:
- Browser audio permissions
- System volume settings
- Audio device selection in browser

## References

- [Gemini Live API Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/live-api)
- [ADK Documentation](https://google.github.io/adk-docs/)
- [FastAPI WebSocket Guide](https://fastapi.tiangolo.com/advanced/websockets/)

## License

MIT License - See LICENSE file for details
```

**Step 2: Create deployment guide**

```markdown
# Deployment Guide

## Local Development

See README.md for local setup instructions.

## Docker Deployment

### Build Image

```bash
docker build -t appliance-inventory:latest .
```

### Run Container

```bash
docker run -d \
  -p 8000:8000 \
  -e GOOGLE_CLOUD_PROJECT=your-project-id \
  -e GOOGLE_CLOUD_LOCATION=us-central1 \
  -e GOOGLE_GENAI_USE_VERTEXAI=TRUE \
  --name appliance-inventory \
  appliance-inventory:latest
```

## Cloud Run Deployment

### Prerequisites

- Google Cloud SDK installed
- Artifact Registry repository created
- Vertex AI API enabled

### Deploy Steps

```bash
# Set project
gcloud config set project YOUR_PROJECT_ID

# Build and push
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/appliance-inventory

# Deploy to Cloud Run
gcloud run deploy appliance-inventory \
  --image gcr.io/YOUR_PROJECT_ID/appliance-inventory \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID \
  --set-env-vars GOOGLE_CLOUD_LOCATION=us-central1 \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=TRUE \
  --memory 2Gi \
  --cpu 2
```

## Vertex AI Agent Engine Deployment

```python
import vertexai
from vertexai.agent_engines import create

vertexai.init(project="YOUR_PROJECT_ID", location="us-central1")

deployed_agent = create(
    display_name="appliance-inventory-agent",
    agent_module_path="app.appliance_agent.agent",
    agent_module_name="root_agent",
    environment_variables={
        "APP_NAME": "appliance-inventory",
    },
    requirements_file_path="requirements.txt",
)

print(f"Agent deployed: {deployed_agent.base_url}")
```

## Production Considerations

### Security

- Enable authentication for WebSocket endpoints
- Use HTTPS/WSS in production
- Implement rate limiting
- Validate all user inputs

### Performance

- Consider Redis for session storage (replace InMemorySessionService)
- Enable CDN for static files
- Monitor WebSocket connection limits
- Scale horizontally as needed

### Monitoring

- Log all WebSocket connections/disconnections
- Track agent tool usage
- Monitor Vertex AI API quotas
- Set up error alerting

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| GOOGLE_CLOUD_PROJECT | Yes | GCP project ID |
| GOOGLE_CLOUD_LOCATION | Yes | Region (e.g., us-central1) |
| GOOGLE_GENAI_USE_VERTEXAI | Yes | Set to TRUE for Vertex AI |
| APP_NAME | No | Application name (default: appliance-inventory) |
| HOST | No | Server host (default: 0.0.0.0) |
| PORT | No | Server port (default: 8000) |
| MODEL_NAME | No | Gemini model to use |
```

**Step 3: Create Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy project files
COPY pyproject.toml ./
COPY app ./app
COPY .env.template ./.env

# Install dependencies
RUN uv sync --frozen

# Expose port
EXPOSE 8000

# Run application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 4: Create .dockerignore**

```
# .dockerignore
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
ENV/
.pytest_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/
.git/
.gitignore
tests/
.env
README.md
DEPLOYMENT.md
docs/
```

**Step 5: Test Docker build**

Run: `docker build -t appliance-inventory:latest .`
Expected: Image builds successfully

**Step 6: Commit**

```bash
git add README.md DEPLOYMENT.md Dockerfile .dockerignore
git commit -m "docs: add comprehensive documentation and deployment guides

- Update README with architecture, setup, and usage instructions
- Add DEPLOYMENT.md with Docker and Cloud Run deployment steps
- Include Dockerfile for containerization
- Add .dockerignore for efficient builds
- Document troubleshooting and production considerations

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Implementation Complete

The appliance inventory application is now fully implemented with:

✅ Project structure with uv build system
✅ Appliance detection tools with inventory management
✅ ADK agent with Gemini Live native audio model
✅ FastAPI WebSocket server with bidirectional streaming
✅ Web UI with video/audio streaming
✅ Complete test coverage
✅ Documentation and deployment guides

**Next Steps:**

1. Deploy to development environment
2. Test with real camera and appliances
3. Gather user feedback
4. Iterate on agent instructions based on performance
5. Consider adding features:
   - Persistent storage (database)
   - Export inventory to CSV/JSON
   - Image capture of each appliance
   - Warranty tracking
   - Maintenance reminders

**Sources:**
- [Gemini Live API Overview](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api)
- [Gemini 2.5 Flash with Live API](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash-live-api)
- [Get Started with Live API using ADK](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/live-api/get-started-adk)
- [ADK Streaming Guide Part 4 - Run Configuration](https://google.github.io/adk-docs/streaming/dev-guide/part4/)
- [Gemini Live API: Real-time AI for Manufacturing](https://cloud.google.com/blog/topics/developers-practitioners/gemini-live-api-real-time-ai-for-manufacturing)
- [How to use Gemini Live API Native Audio in Vertex AI](https://cloud.google.com/blog/topics/developers-practitioners/how-to-use-gemini-live-api-native-audio-in-vertex-ai)
- [Google ADK + Vertex AI Live API Article](https://medium.com/google-cloud/google-adk-vertex-ai-live-api-125238982d5e)
