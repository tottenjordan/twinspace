# Project Status - Appliance Inventory Live Video App

**Last Updated:** 2026-02-19

## Current State: 🟡 PARTIAL - Audio Greeting Working, Clarity Issues

### ✅ What's Working

1. **Live API Connection**
   - FastAPI WebSocket endpoint (`/ws`) successfully connects to Gemini Live API
   - Bidirectional streaming established (audio, video, text)
   - Session lifecycle management functional

2. **Audio Pipeline**
   - PCM audio input (16kHz, 16-bit mono) from browser microphone
   - PCM audio output (24kHz, 16-bit mono) from Live API
   - Sequential audio chunk playback (no overlapping)
   - AudioContext configured to 24kHz sample rate

3. **Video Streaming**
   - Camera access and JPEG frame capture (1 FPS)
   - Base64 encoding and WebSocket transmission
   - Frames sent to Live API via `send_realtime_input()`

4. **Push-to-Talk**
   - Activity signals (activity_start/activity_end) implemented
   - Tool guard system prevents premature execution
   - Turn completion signaling works

5. **Tools**
   - `detect_appliance()` - Records appliance detection
   - `confirm_appliance_detection()` - User confirmation
   - `update_appliance_details()` - Capture make/model
   - `get_inventory_summary()` - Current inventory
   - Guard mechanism prevents hallucinations

6. **Frontend UI**
   - Web interface at http://localhost:8000
   - Connect button triggers greeting
   - Live API events display
   - Conversation panel shows text
   - Inventory display functional

### 🟡 Partial / In Progress

1. **Initial Greeting**
   - Greeting is generated and sent
   - Audio plays but **clarity is still suboptimal**
   - Sequential playback implemented (no more garbling from overlap)
   - System instruction updated to prevent meta-narration
   - **Issue:** Audio quality not crystal clear yet

2. **Audio Quality**
   - AudioContext sample rate now matches (24kHz)
   - Data validation added
   - **Still needs:** Further investigation into clarity issues
   - Possible causes: Browser resampling, PCM decoding, chunk boundaries

### ❌ Not Yet Implemented

1. **Full Appliance Detection Workflow**
   - Need to test complete flow: detection → confirmation → details → inventory
   - Need to verify tools execute correctly with video context
   - Need to test multiple appliance captures

2. **Error Handling**
   - WebSocket reconnection on disconnect
   - Live API error recovery
   - Audio/video stream failure handling

3. **Production Features**
   - Session persistence
   - Inventory export
   - Multi-user support
   - Deployment configuration

## Architecture Summary

### Backend (Python)
- **FastAPI** - HTTP server and WebSocket handler
- **GenAI SDK** - Direct Live API connection via `client.aio.live.connect()`
- **Three Input Queues** - Separate audio, video, text queues
- **Event Queue Pattern** - Async event processing and forwarding

### Frontend (JavaScript)
- **Vanilla JS** - No framework dependencies
- **WebSocket Client** - Bidirectional communication
- **AudioPlayer** - Sequential PCM playback with 24kHz AudioContext
- **AudioRecorder** - Microphone capture with AudioWorklet
- **VideoHandler** - Camera access and 1 FPS frame capture

### Key Files
```
app/
├── main.py              # FastAPI WebSocket endpoint
├── gemini_live.py       # Live API wrapper
├── tools.py             # Appliance detection tools
└── static/
    ├── index.html       # UI
    └── js/
        ├── app.js               # Main application logic
        ├── audio-player.js      # Audio playback (24kHz)
        ├── audio-recorder.js    # Microphone capture
        └── video-handler.js     # Camera handling
```

## Next Steps (Priority Order)

### High Priority
1. **Fix Audio Clarity** - Investigate remaining audio quality issues
   - Check browser audio pipeline
   - Verify PCM decoding is correct
   - Test different chunk sizes
   - Consider using Web Audio API gain nodes

2. **Test Full Workflow** - End-to-end appliance detection
   - User shows appliance to camera
   - Agent detects and asks for confirmation
   - Collect make/model information
   - Verify inventory updates

### Medium Priority
3. **Error Handling** - Add robustness
   - WebSocket reconnection logic
   - Live API timeout handling
   - Audio/video stream error recovery

4. **User Experience** - Polish the interface
   - Loading states
   - Better error messages
   - Visual feedback during detection

### Low Priority
5. **Testing** - Add automated tests
   - Unit tests for tools
   - Integration tests for WebSocket
   - End-to-end workflow tests

6. **Documentation** - Improve docs
   - API documentation
   - Deployment guide
   - User manual

## Known Issues

1. **Audio Clarity** - Greeting audio plays but quality is suboptimal
   - Symptom: Audio sounds slightly garbled or unclear
   - Investigation: Sample rate matching implemented, validation added
   - Status: In progress

2. **Meta-Narration** (FIXED) - Agent was describing what it would say instead of saying it
   - Solution: Updated system instruction to prevent meta-narration
   - Status: Resolved

3. **Audio Overlapping** (FIXED) - Chunks played simultaneously causing garbled sound
   - Solution: Sequential playback with `onended` callbacks
   - Status: Resolved

## Performance Metrics

- **Initial greeting time:** ~2-3 seconds from button click
- **Audio chunk size:** 1920 bytes (typical), 46080 bytes (first chunk)
- **Video frame rate:** 1 FPS
- **WebSocket latency:** Low (<100ms typical)

## Technical Decisions

### Why Direct GenAI SDK vs ADK?
- **More control** over session lifecycle
- **Simpler debugging** with direct API access
- **Better performance** with fewer abstraction layers
- **Follows reference implementation** from Google

### Why Event Queue Pattern?
- **Decouples** event generation from processing
- **Allows** async tasks to run concurrently
- **Prevents** TaskGroup deadlocks
- **Simplifies** event forwarding to client

### Why 24kHz Audio?
- **Matches** Live API output sample rate
- **Eliminates** browser resampling artifacts
- **Lower latency** than 48kHz
- **Good quality** for speech

## Dependencies

```toml
[project.dependencies]
google-genai>=0.3.0      # Live API support
google-adk>=1.20.0       # (unused, can be removed)
fastapi>=0.115.0         # WebSocket server
uvicorn[standard]>=0.32.0 # ASGI server
python-dotenv>=1.0.0     # Environment config
```

## Running the Application

```bash
# Start server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Access UI
http://localhost:8000

# Click "Connect to AI" to start session
```

## Environment Variables

```bash
# Required
GOOGLE_API_KEY=your-api-key-here  # For Google AI (Gemini API)

# OR for Vertex AI
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=1
```
