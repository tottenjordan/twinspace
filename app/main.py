"""FastAPI application with WebSocket bidirectional streaming."""
import os
from pathlib import Path
import json
import base64
import asyncio
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.agents.live_request_queue import LiveRequestQueue
from google import genai
from google.genai import types
from app.appliance_agent import root_agent

# Load environment variables
load_dotenv()

APP_NAME = os.getenv("APP_NAME", "appliance-inventory")

# Initialize FastAPI app
app = FastAPI(
    title="Appliance Inventory Live API",
    description="Real-time appliance detection using Gemini Live API",
    version="0.1.0"
)

# Initialize ADK components
session_service = InMemorySessionService()
runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service
)

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def is_native_audio_model(model_name: str) -> bool:
    """Check if model uses native audio."""
    return "native-audio" in model_name.lower()


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
