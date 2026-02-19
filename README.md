# Appliance Inventory - Live Video Application

Real-time appliance detection and inventory management using Gemini Live API with bidirectional video/audio streaming.

## Features

- 📹 **Live Video Streaming**: Real-time camera feed at 1 FPS for appliance detection
- 🤖 **AI-Powered Detection**: Gemini 2.5 Flash Native Audio model identifies appliances
- 🎙️ **Push-to-Talk Voice**: Natural voice conversations for inventory building
- 📝 **Smart Follow-up**: Agent asks questions to capture make and model
- 💾 **Session Management**: In-memory inventory during session
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
│                 │
│  ┌───────────┐  │
│  │ Audio Q   │  │
│  │ Video Q   │  │
│  │ Text Q    │  │
│  └───────────┘  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  GeminiLive     │
│  Wrapper        │
│  (GenAI SDK)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Gemini Live    │
│  2.5 Flash      │
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
3. **Initial Greeting**: Agent greets you automatically
4. **Push to Talk**: Hold button while speaking about appliances
5. **Walk Around**: Point camera at appliances as you move through your home
6. **Respond**: Answer agent's questions about each detected appliance
7. **View Inventory**: See your growing appliance list in the Inventory panel

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
│   ├── main.py                    # FastAPI WebSocket endpoint
│   ├── gemini_live.py             # Live API wrapper
│   ├── tools.py                   # Appliance detection tools
│   └── static/
│       ├── index.html             # Main UI
│       ├── css/style.css
│       └── js/
│           ├── app.js                      # Main application logic
│           ├── video-handler.js            # Camera/video capture
│           ├── audio-player.js             # Audio playback (24kHz)
│           ├── audio-recorder.js           # Audio recording (16kHz)
│           └── pcm-recorder-processor.js   # AudioWorklet processor
├── docs/
│   ├── architecture/
│   │   └── generate_diagram.py
│   └── plans/
│       └── 2026-02-19-appliance-inventory-live-video.md
├── tests/
│   ├── conftest.py
│   └── test_websocket.py
├── pyproject.toml
├── .env.template
├── README.md
├── STATUS.md                      # Current project status
├── REFACTORING_NOTES.md           # Refactoring history
└── DEPLOYMENT.md
```

## Technical Details

### Video Processing

- Captures frames at 1 FPS (aligned with Gemini Live API video processing rate)
- Format: JPEG-encoded frames
- Transmission: Base64 over WebSocket
- Resolution: 1280x720 (configurable)

### Audio Processing

**Input (User → API):**
- Sample rate: 16 kHz mono
- Format: PCM 16-bit little-endian
- Transmission: Binary WebSocket frames

**Output (API → User):**
- Sample rate: 24 kHz mono
- Format: PCM 16-bit little-endian
- Playback: Web Audio API with AudioContext at 24kHz
- Queueing: Sequential playback using `onended` callbacks

### Model Configuration

- Model: `gemini-2.5-flash-native-audio-preview-12-2025`
- Response modality: AUDIO (native audio)
- Voice: Puck
- Streaming: Bidirectional via `client.aio.live.connect()`
- Session: Fresh per WebSocket connection

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
