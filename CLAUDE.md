# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Self-Maintenance Rule

After every major change (new model, new page, new controller, route changes, migration changes, new test files, architectural shifts), update this CLAUDE.md file to reflect the current state. Specifically:

* Add new models/controllers/pages/routes to the relevant tables below
* Update test count if new tests are added
* Add any new gotchas or patterns to the "Gotchas & Pitfalls" section
* Update the "Current State" section if the status changes
* Keep this file as the single source of truth for AI sessions working on this project

## Project Overview

Real-time appliance inventory application using **Gemini Live API** with bidirectional video/audio streaming. Users walk through their homes with a camera, and an ADK agent detects appliances, confirms with the user via voice, and captures make/model details.

## Common Commands

### Development
```bash
# Install dependencies
uv sync

# Run application (http://localhost:8000)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests (all 21 tests)
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_inventory_tool.py -v

# Lint code
uv run ruff check .

# Auto-fix linting issues
uv run ruff check . --fix

# Format code
uv run ruff format .
```

### Configuration
- Copy `.env.template` to `.env` and configure Google Cloud credentials
- Required: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_GENAI_USE_VERTEXAI=TRUE`

## Architecture Overview

### Component Flow
1. **Web Browser** → Camera/mic access, captures video at **1 FPS** (critical: Gemini Live API constraint)
2. **FastAPI WebSocket** (`/ws/{user_id}/{session_id}`) → Bidirectional streaming server
3. **ADK Runner** → Executes agent with Live API, manages sessions (InMemorySessionService)
4. **Gemini Live API** → `gemini-live-2.5-flash-native-audio` model for video+audio processing
5. **Inventory Tools** → Singleton pattern manages appliance state across workflow

### Critical Technical Constraints

**Video Processing:**
- **Exactly 1 FPS capture rate** - Gemini Live API processes video at 1 FPS, sending faster wastes bandwidth
- JPEG encoding at 0.8 quality, resolution 1280x720
- Sent as base64-encoded JSON messages via WebSocket

**Audio Processing:**
- **16 kHz mono PCM 16-bit** - Required format for Gemini Live API
- Uses AudioWorklet (pcm-recorder-processor.js) with 4096-sample buffering
- Binary WebSocket messages for upstream audio, base64 for downstream

**Response Modality:**
- Native audio models **require** `response_modalities=["AUDIO"]`
- Detected automatically via `"native-audio" in model_name.lower()`

## Appliance Detection Workflow

The workflow spans 4 tools in `app/tools/inventory.py` and is orchestrated by the ADK agent:

### State Machine
```
1. detect_appliance(type) → Creates pending_appliance with status="pending_confirmation"
2. confirm_appliance_detection(bool) → If True: generates UUID, sets status="needs_details"
                                      → If False: clears pending_appliance
3. update_appliance_details(make, model) → Sets status="completed", moves to main inventory
4. get_inventory_summary() → Returns current inventory (read-only)
```

### Singleton Pattern (ApplianceInventory)
- **Critical:** Single shared state across all tool calls within a session
- `appliances: list[dict]` - Main inventory
- `pending_appliance: dict | None` - Temporary holding during workflow
- Reset between tests via `conftest.py` autouse fixture

### Agent Instruction Pattern
The agent in `app/appliance_agent/agent.py` has a comprehensive instruction that:
- Guides the conversational flow (detect → ask → confirm → get details → complete)
- Only processes **one appliance at a time** to avoid confusion
- Suggests users get closer to labels if make/model unclear
- Uses tool return messages to guide next steps

## WebSocket Bidirectional Streaming

### Upstream Task (Client → Agent)
Handles 3 message types in `app/main.py`:
- **Binary** (`message["bytes"]`) → Audio PCM chunks via `LiveRequestQueue.send_realtime()`
- **JSON text** (`data["type"] == "text"`) → User text messages via `send_content()`
- **JSON image** (`data["type"] == "image"`) → Base64 video frames via `send_content()`

### Downstream Task (Agent → Client)
- Async iterator over `runner.run_live()` yields events
- Events serialized as JSON via `event.model_dump_json(exclude_none=True)`
- Client processes: `server_content.model_turn.parts` for text/audio responses

### Concurrent Execution
Both tasks run concurrently via `asyncio.gather()` for full-duplex communication.

## Key Patterns & Conventions

### Test-Driven Development
All features implemented following TDD:
1. Write failing test
2. Run test to verify failure
3. Implement minimal code
4. Run test to verify pass
5. Refactor and commit

### Error Handling in Tools
Tools return structured dicts with `status` field:
- `"success"` / `"detected"` / `"confirmed"` / `"completed"` - Happy path
- `"error"` / `"warning"` - Error conditions with `message` field

### Agent Tool Integration
- Tools use `ToolContext` parameter for state management (`tool_context.state`)
- Agent automatically injects ToolContext when calling tools
- State persists across tool calls within a session

## Important Files

### Core Application
- `app/main.py` - FastAPI app, WebSocket endpoint, ADK Runner initialization
- `app/appliance_agent/agent.py` - ADK agent definition with Gemini Live model
- `app/tools/inventory.py` - 4 inventory management tools (detect, confirm, update, summary)

### Frontend
- `app/static/js/app.js` - Main WebSocket client, event handling, inventory updates
- `app/static/js/video-handler.js` - Camera access, 1 FPS capture (see `captureInterval = 1000ms`)
- `app/static/js/audio-recorder.js` - 16kHz PCM recording with AudioWorklet

### Testing
- `tests/conftest.py` - Singleton reset fixture (critical for test isolation)
- `tests/test_integration.py` - Full workflow tests (detect → confirm → update)

## Common Development Scenarios

### Adding a New Tool
1. Define function in `app/tools/inventory.py` with `ToolContext` parameter
2. Add comprehensive docstring (ADK uses this for tool discovery)
3. Import and add to `root_agent.tools` list in `app/appliance_agent/agent.py`
4. Update agent instruction if tool changes workflow
5. Write tests in `tests/test_inventory_tool.py`
6. Update `tests/test_appliance_agent.py` to expect new tool count

### Modifying Video Capture
- **Never change 1 FPS rate** - Gemini Live API constraint
- Modify resolution in `video-handler.js`: `getUserMedia({video: {width, height}})`
- Adjust JPEG quality: `canvas.toDataURL('image/jpeg', quality)` (0.0-1.0)

### Changing Audio Format
- Sample rate **must be 16kHz** for Gemini Live API
- Modify in `audio-recorder.js`: `AudioContext({sampleRate: 16000})`
- Buffer size can be adjusted in `pcm-recorder-processor.js` (currently 4096)

## Build System (uv)

- Python ≥3.10 required
- Build backend: hatchling
- Lock file: `uv.lock` (committed for reproducible builds)
- Virtual env: `.venv/` (gitignored)

## Deployment

See `DEPLOYMENT.md` for:
- Docker containerization
- Google Cloud Run deployment
- Vertex AI Agent Engine deployment
- Production environment variables

## Testing Philosophy

- **Unit tests:** Individual tool functions (13 tests in test_inventory_tool.py)
- **Integration tests:** Full workflow cycles (5 tests in test_integration.py)
- **Component tests:** Agent configuration, WebSocket endpoints
- **No mocking of ADK internals** - Use real ToolContext when possible
- **Singleton reset critical** - Every test must start with clean inventory state
