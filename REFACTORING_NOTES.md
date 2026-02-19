# Refactoring to Direct GenAI SDK (v0.2.0)

## Overview

Refactored the application from using ADK's `Runner` and `LiveRequestQueue` to using the direct GenAI SDK `client.aio.live.connect()` approach, following the reference implementation at:
https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/multimodal-live-api/native-audio-websocket-demo-apps/plain-js-python-sdk-demo-app

## Key Changes

### 1. New Architecture (`app/gemini_live.py`)
- **Direct Live API Access**: Uses `genai.Client().aio.live.connect()` instead of ADK Runner
- **Queue-Based Streaming**: Separate queues for audio, video, and text input
- **Simplified Event Handling**: Events are now simple dictionaries instead of complex ADK events
- **Tool Execution**: Tools execute directly via function mapping, not through ADK tool context

**Benefits:**
- More control over session lifecycle
- Simpler event processing
- Better debugging (direct API access)
- Eliminates ADK abstraction layers that complicated streaming

### 2. Simplified Tools (`app/tools.py`)
- **No ADK Dependency**: Tools no longer depend on `ToolContext`
- **Global State**: Uses module-level state dictionary instead of ADK session service
- **Direct Function Calls**: Tools are regular Python functions, callable by both Live API and tests

**Key Functions:**
- `detect_appliance(appliance_type)` - Record appliance detection
- `confirm_appliance_detection(user_wants_to_capture)` - Confirm user wants to add
- `update_appliance_details(make, model)` - Add make/model info
- `get_inventory_summary()` - Get current inventory
- `mark_user_has_spoken()` - Enable tool guards after first user speech
- `reset_session()` - Reset state for new connection

### 3. Updated Backend (`app/main.py`)
- **Simplified WebSocket Endpoint**: `/ws` instead of `/ws/{user_id}/{session_id}`
- **Three Input Queues**: audio_input_queue, video_input_queue, text_input_queue
- **Two Concurrent Tasks**:
  - `receive_from_client()` - Routes incoming messages to appropriate queues
  - `run_session()` - Processes Live API events and forwards to client

**Event Flow:**
```
Client → WebSocket → receive_from_client() → Queues → GeminiLive.start_session()
                                                              ↓
Client ← WebSocket ← run_session() ← Events ← Live API Session
```

### 4. Updated Frontend (`app/static/js/app.js`)
- **Simpler Event Format**: Events are now `{type: "...", ...}` instead of ADK format
- **Event Types**:
  - `text_output` - Agent text response
  - `audio_output` - Agent audio response (base64 PCM)
  - `tool_call` - Tool was called
  - `inventory_updated` - Inventory changed (triggers UI refresh)
  - `turn_complete` - Conversation turn ended
  - `interrupted` - Agent was interrupted
  - `setup_complete` - Session setup finished

## Dependencies

Added `google-genai>=0.3.0` to replace direct ADK dependency for Live API streaming.

## Migration Notes

### Old Files (Backed Up)
- `app/main_old.py` - Original ADK-based implementation
- `app/static/js/app_old.js` - Original ADK event handling
- `app/appliance_agent/` - ADK agent configuration (kept for reference)

### New Files
- `app/gemini_live.py` - Live API wrapper
- `app/tools.py` - Standalone tool functions
- `app/main.py` - Refactored FastAPI server
- `app/static/js/app.js` - Updated event handling

## Testing

Run the server:
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected behavior:
1. Connect to `/ws`
2. Agent sends greeting automatically
3. User activates push-to-talk
4. Tools only execute after `mark_user_has_spoken()` is called
5. No hallucinated appliance detections (guards prevent premature tool calls)

## Differences from Reference Implementation

1. **Tool Integration**: Reference doesn't use tools; we integrate appliance detection tools
2. **Guards**: We added `user_has_spoken` guards to prevent premature tool execution
3. **Inventory Management**: Custom ApplianceInventory singleton for state persistence
4. **Push-to-Talk**: Activity signals integrated with tool guard activation

## Benefits of This Architecture

1. **No Hallucinations**: Tools can't execute until user speaks (guard mechanism)
2. **Direct Control**: No ADK abstraction between us and Live API
3. **Simpler Debugging**: Events are simple dictionaries, easy to log and inspect
4. **Better Performance**: Fewer layers, less overhead
5. **Reference-Aligned**: Follows Google's official example architecture

## Troubleshooting

### Issue: Tools executing too early
- **Cause**: `mark_user_has_spoken()` not called on activity_end
- **Fix**: Verify `activity_end` handler calls `mark_user_has_spoken()`

### Issue: Audio not playing
- **Cause**: Base64 encoding mismatch
- **Fix**: Frontend already handles URL-safe → standard base64 conversion

### Issue: Video frames flooding
- **Cause**: Sending frames too frequently
- **Fix**: Frontend captures at 1 FPS, backend sends with `turn_complete=False`

### Issue: Session state not resetting
- **Cause**: `reset_session()` not called on new connection
- **Fix**: Call `reset_session()` in `websocket_endpoint()` at start

### Issue: Audio garbled/overlapping (FIXED)
- **Cause**: All audio chunks playing simultaneously
- **Fix**: Implemented sequential playback with `onended` callbacks in audio-player.js
- **Status**: Resolved (app/static/js/audio-player.js:16-75)

### Issue: Meta-narration instead of natural greeting (FIXED)
- **Cause**: Agent describing what it would say instead of saying it
- **Fix**: Updated system instruction to "Speak naturally and conversationally. Never describe what you're about to say or think out loud."
- **Status**: Resolved (app/main.py:42-46)

### Issue: Audio clarity suboptimal (IN PROGRESS)
- **Cause**: AudioContext sample rate mismatch causing resampling artifacts
- **Fix**: Set AudioContext to 24kHz to match Live API output
- **Status**: Improved but not perfect yet (app/static/js/audio-player.js:3-6)
