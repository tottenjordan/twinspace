"""FastAPI application with WebSocket bidirectional streaming using Gemini Live API."""
import asyncio
import base64
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.gemini_live import GeminiLive
from app.tools import (
    ApplianceInventory,
    confirm_appliance_detection,
    detect_appliance,
    get_inventory_summary,
    mark_user_has_spoken,
    reset_session,
    update_appliance_details,
)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Appliance Inventory Live API",
    description="Real-time appliance detection using Gemini Live API",
    version="0.2.0",
)

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Agent instruction - Keep it simple!
SYSTEM_INSTRUCTION = """You are a friendly home appliance assistant.

Speak naturally and conversationally. Never describe what you're about to say or think out loud.

You help users catalog their home appliances by watching their video feed and asking questions to collect make and model information."""


@app.get("/")
async def index():
    """Serve main HTML page."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {
        "message": "Appliance Inventory Live API - WebSocket endpoint: /ws"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/inventory")
async def get_inventory():
    """Get current appliance inventory."""
    inventory = ApplianceInventory()
    return {"total": len(inventory.appliances), "appliances": inventory.appliances}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for bidirectional streaming with Gemini Live API.

    Handles:
    - Audio input (PCM 16-bit, 16kHz mono)
    - Video frames (JPEG, 1 FPS)
    - Push-to-talk activity signals
    """
    await websocket.accept()
    print("WebSocket connection accepted")

    # Reset session state for new connection
    reset_session()

    # Create input queues
    audio_input_queue = asyncio.Queue()
    video_input_queue = asyncio.Queue()
    text_input_queue = asyncio.Queue()

    # Audio output callback - send audio chunks to client
    async def audio_output_callback(audio_data: bytes):
        """Send audio output to client."""
        # Convert to URL-safe base64 for client
        base64_audio = base64.b64encode(audio_data).decode("utf-8")
        print(f">>> Audio output chunk: {len(audio_data)} bytes")
        await websocket.send_json(
            {
                "type": "audio_output",
                "data": base64_audio,
            }
        )

    # Interruption callback
    def on_interrupt():
        """Handle agent interruption."""
        print("Agent was interrupted")

    # Create Gemini Live client
    # Note: Use Live API specific model
    gemini_live = GeminiLive(
        model="gemini-2.5-flash-native-audio-preview-12-2025",
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[
            detect_appliance,
            confirm_appliance_detection,
            update_appliance_details,
            get_inventory_summary,
        ],
        input_sample_rate=16000,
        output_sample_rate=24000,
        voice_name="Puck",
    )

    # Track if we're in a conversation turn
    in_turn = False

    async def receive_from_client():
        """Receive messages from client and route to appropriate queues."""
        nonlocal in_turn
        try:
            while True:
                message = await websocket.receive()

                if "bytes" in message:
                    # Binary audio data (PCM 16-bit, 16kHz mono)
                    audio_chunk = message["bytes"]
                    print(f">>> Received audio chunk: {len(audio_chunk)} bytes")
                    await audio_input_queue.put(audio_chunk)

                elif "text" in message:
                    # JSON message (activity signals, images)
                    data = json.loads(message["text"])

                    if data["type"] == "activity_start":
                        # User started talking (push-to-talk pressed)
                        print("\n>>> User started talking (push-to-talk pressed)")
                        in_turn = True

                    elif data["type"] == "activity_end":
                        # User stopped talking (push-to-talk released)
                        print(">>> User stopped talking (push-to-talk released)")

                        # Mark that user has spoken (enables tool guards)
                        mark_user_has_spoken()
                        print(">>> Session activated - tools now enabled")

                        # Signal turn completion to Live API
                        # Empty string triggers turn_complete signal in send_text()
                        await text_input_queue.put("")
                        print(">>> Queued turn completion signal")

                        in_turn = False

                    elif data["type"] == "image":
                        # Decode base64 image
                        image_data = base64.b64decode(data["data"])

                        # Send to video queue
                        await video_input_queue.put(image_data)

                        # Log every 10th frame to avoid spam
                        frame_count = video_input_queue.qsize()
                        if frame_count % 10 == 0:
                            print(f">>> Video frame sent to Live API")

        except WebSocketDisconnect:
            print("Client disconnected")
        except Exception as e:
            print(f"Error in receive_from_client: {e}")
            import traceback

            traceback.print_exc()
        finally:
            # Send sentinels to stop sender tasks
            await audio_input_queue.put(None)
            await video_input_queue.put(None)
            await text_input_queue.put(None)

    async def run_session():
        """Run the Gemini Live session and forward events to client."""
        try:
            print("Starting Gemini Live session...")

            # Send initial greeting
            await text_input_queue.put("Greet the user warmly and let them know you can help catalog their home appliances.")
            print(">>> Queued initial greeting")

            # Start the session and process events
            async for event in gemini_live.start_session(
                audio_input_queue=audio_input_queue,
                video_input_queue=video_input_queue,
                text_input_queue=text_input_queue,
                audio_output_callback=audio_output_callback,
                on_interrupt=on_interrupt,
            ):
                # Forward events to client
                print(f">>> Event received: {event['type']}")

                if event["type"] == "text_output":
                    # Send text transcription to client
                    print(f">>> Text output: {event['text']}")
                    await websocket.send_json(
                        {
                            "type": "text_output",
                            "text": event["text"],
                        }
                    )

                elif event["type"] == "tool_call":
                    # Send tool call notification
                    await websocket.send_json(
                        {
                            "type": "tool_call",
                            "function_name": event["function_name"],
                            "args": event["args"],
                        }
                    )

                    # If tool completed an appliance, notify client to refresh
                    if (
                        event["function_name"] == "update_appliance_details"
                        and event["result"].get("status") == "completed"
                    ):
                        await websocket.send_json(
                            {
                                "type": "inventory_updated",
                                "total": event["result"]["total_appliances"],
                            }
                        )

                elif event["type"] == "turn_complete":
                    await websocket.send_json({"type": "turn_complete"})

                elif event["type"] == "interrupted":
                    await websocket.send_json({"type": "interrupted"})

                elif event["type"] == "setup_complete":
                    await websocket.send_json({"type": "setup_complete"})

                elif event["type"] == "error":
                    # Log and forward error
                    print(f"!!! ERROR EVENT: {event.get('error', 'Unknown error')}")
                    await websocket.send_json(event)

        except Exception as e:
            print(f"Error in run_session: {e}")
            import traceback

            traceback.print_exc()

    # Run both tasks concurrently
    receive_task = None
    try:
        receive_task = asyncio.create_task(receive_from_client())
        await run_session()
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Cancel receive task if still running
        if receive_task and not receive_task.done():
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket
        try:
            await websocket.close()
        except:
            pass

        print("WebSocket connection closed")
