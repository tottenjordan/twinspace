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
