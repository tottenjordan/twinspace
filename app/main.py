"""FastAPI application with WebSocket bidirectional streaming."""
import asyncio
import base64
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.adk import Runner
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.genai.types import Modality

from app.appliance_agent import root_agent
from app.appliance_agent.tools.video_monitor import VideoFrameBuffer

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
    msg = "Appliance Inventory Live API - WebSocket endpoint: /ws/{user_id}/{session_id}"
    return {"message": msg}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "app": APP_NAME}


@app.get("/api/inventory")
async def get_inventory():
    """Get current appliance inventory."""
    from app.appliance_agent.tools.inventory import ApplianceInventory
    inventory = ApplianceInventory()
    return {
        "total": len(inventory.appliances),
        "appliances": inventory.appliances
    }


@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
    proactivity: bool | None = Query(default=True),
    affective_dialog: bool | None = Query(default=False),
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

    # Create session explicitly before starting live stream
    print(f"Creating session: user={user_id}, session={session_id}")
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
        state={"user_has_spoken": False}  # Track user interaction for certain tools
    )
    print(f"Session created successfully: {session_id}")

    # Determine response modality based on model
    # Note: Live API only allows ONE response modality
    # For native audio models, use AUDIO - text transcriptions come via output_transcription
    model_name = root_agent.model
    response_modalities = [Modality.AUDIO] if is_native_audio_model(model_name) else [Modality.TEXT]

    # Create RunConfig for Live API
    # Note: session_resumption removed so each connection starts fresh
    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=response_modalities,
        enable_affective_dialog=affective_dialog,
    )

    # Disable proactivity for push-to-talk - agent should only respond when user speaks
    # if proactivity:
    #     run_config.proactivity = types.ProactivityConfig()

    # Create LiveRequestQueue for message passing
    live_request_queue = LiveRequestQueue()

    # Send initial greeting to trigger agent introduction
    live_request_queue.send_content(
        genai.types.Content(
            role="user",
            parts=[genai.types.Part(text="Hi")]
        )
    )
    print("Sent initial greeting to agent")

    async def upstream_task():
        """Receive messages from client and forward to agent."""
        try:
            print("Upstream: Starting message receive loop...")
            print("Upstream: Waiting for user input (push-to-talk)...")

            while True:
                message = await websocket.receive()

                if "bytes" in message:
                    # Binary audio data (PCM 16-bit, 16kHz mono)
                    # For Live API, send audio via send_realtime with Blob format
                    audio_chunk = message["bytes"]
                    try:
                        # Wrap audio chunk in Blob object for LiveClientRealtimeInput
                        # Note: send_realtime is synchronous, not async
                        live_request_queue.send_realtime(
                            types.LiveClientRealtimeInput(
                                mediaChunks=[
                                    types.Blob(
                                        mime_type="audio/pcm",
                                        data=audio_chunk
                                    )
                                ]
                            )
                        )
                    except Exception as e:
                        print(f"Error sending audio chunk: {e}")
                elif "text" in message:
                    # JSON message (text, image, etc.)
                    data = json.loads(message["text"])

                    if data["type"] == "activity_start":
                        # User started talking (push-to-talk pressed)
                        print("\n>>> User started talking (push-to-talk pressed)")
                        live_request_queue.send_activity_start()
                        print(">>> Activity start signal sent to Live API")
                    elif data["type"] == "activity_end":
                        # User stopped talking (push-to-talk released)
                        print("\n>>> User stopped talking (push-to-talk released)")

                        # Activate the session - allow tools to run now that user has spoken
                        session = await session_service.get_session(
                            app_name=APP_NAME,
                            user_id=user_id,
                            session_id=session_id
                        )
                        session.state["user_has_spoken"] = True
                        print(">>> Session activated - tools now enabled")

                        live_request_queue.send_activity_end()
                        print(">>> Activity end signal sent to Live API")
                        print(">>> Waiting for agent response...\n")
                    elif data["type"] == "image":
                        # Decode base64 image
                        image_data = base64.b64decode(data["data"])
                        mime_type = data.get("mimeType", "image/jpeg")

                        # Add frame to buffer for monitoring
                        video_buffer = VideoFrameBuffer()
                        video_buffer.add_frame(image_data, mime_type)

                        # Log every 10th frame to avoid spam
                        total_frames = video_buffer.get_total_frames()
                        if total_frames % 10 == 0:
                            print(f">>> Video frame #{total_frames} sent to Live API (1 FPS)")

                        # send_content is synchronous
                        live_request_queue.send_content(
                            genai.types.Content(
                                role="user",
                                parts=[
                                    genai.types.Part(
                                        inline_data=genai.types.Blob(
                                            mime_type=mime_type,
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
            # close is synchronous
            live_request_queue.close()

    async def downstream_task():
        """Receive events from agent and forward to client."""
        try:
            print(f"Starting run_live for session {session_id}")
            print(f"Config: streaming_mode={run_config.streaming_mode}, "
                  f"response_modalities={run_config.response_modalities}, "
                  f"proactivity={run_config.proactivity}")

            event_count = 0
            event_type_counts = {}
            async for event in runner.run_live(
                user_id=user_id,
                session_id=session_id,
                live_request_queue=live_request_queue,
                run_config=run_config,
            ):
                # Log event for debugging
                event_count += 1
                event_type = type(event).__name__
                event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

                print(f"\n=== Event #{event_count} received: {event_type} ===")

                # Check what's in the event
                event_data = {}
                for attr in ['content', 'server_content', 'output_transcription', 'tool_call',
                            'tool_response', 'turn_complete', 'model_version']:
                    if hasattr(event, attr):
                        val = getattr(event, attr)
                        if val is not None:
                            event_data[attr] = str(val)[:100]  # First 100 chars

                if event_data:
                    print(f"Event data: {event_data}")
                else:
                    print("Event has no recognized content fields")

                # Print summary every 20 events or on turn_complete
                if event_count % 20 == 0 or (hasattr(event, 'turn_complete') and event.turn_complete):
                    print(f"\n--- Event Summary (after {event_count} events) ---")
                    for etype, count in sorted(event_type_counts.items()):
                        print(f"  {etype}: {count}")
                    print("---\n")

                # Check for content field (agent responses)
                if hasattr(event, 'content') and event.content:
                    print(f"!!! AGENT CONTENT DETECTED !!!")
                    print(f"Content type: {type(event.content)}")
                    if hasattr(event.content, 'parts'):
                        print(f"Parts count: {len(event.content.parts) if event.content.parts else 0}")
                        for i, part in enumerate(event.content.parts or []):
                            if hasattr(part, 'text') and part.text:
                                print(f"!!! AGENT TEXT RESPONSE: {part.text}")
                            if hasattr(part, 'inline_data'):
                                print(f"!!! AGENT AUDIO RESPONSE (inline_data present)")

                if hasattr(event, 'server_content') and event.server_content:
                    print(f"Server content type: {type(event.server_content)}")
                    if hasattr(event.server_content, 'model_turn'):
                        model_turn = event.server_content.model_turn
                        print(f"Model turn: {model_turn}")
                        if model_turn and hasattr(model_turn, 'parts'):
                            parts_count = len(model_turn.parts) if model_turn.parts else 0
                            print(f"Parts count: {parts_count}")
                            for i, part in enumerate(model_turn.parts or []):
                                if hasattr(part, 'text') and part.text:
                                    print(f"Part {i} text: {part.text[:100]}...")
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    print(f"Part {i} has inline_data (audio)")

                if hasattr(event, 'tool_call') and event.tool_call:
                    print(f"Tool call: {event.tool_call}")

                if hasattr(event, 'tool_response') and event.tool_response:
                    print(f"Tool response: {event.tool_response}")

                # Serialize event and send to client
                event_json = event.model_dump_json(exclude_none=True)
                # Log first 200 chars of JSON to see what's being sent
                print(f"Sending to client: {event_json[:200]}...")
                await websocket.send_text(event_json)
                print("Sent event to client\n")

        except Exception as e:
            print(f"Downstream error: {e}")
            import traceback
            traceback.print_exc()

    # Run upstream and downstream tasks concurrently
    try:
        await asyncio.gather(
            upstream_task(),
            downstream_task(),
        )
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: user={user_id}, session={session_id}")
    finally:
        # close is synchronous
        live_request_queue.close()
