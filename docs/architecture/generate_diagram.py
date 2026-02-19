import os
import sys
from google import genai
from google.genai import types

# Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = "global"  # required for gemini-3-pro-image-preview
OUTPUT_FILE = "docs/architecture/twinspace_architecture.png"

if not PROJECT_ID:
    print("Error: GOOGLE_CLOUD_PROJECT environment variable not set.")
    sys.exit(1)

PROMPT = """
Generate a professional, clean architecture diagram in the style of official
Google Cloud Platform documentation. Use GCP brand colors: blue (#4285F4),
green (#34A853), yellow (#FBBC05), red (#EA4335), with a clean white background.

Title: "Twinspace Appliance Inventory Architecture"

The diagram should show these components connected by clean arrows:

TOP ROW (Entry Points):
- "User Client" (Web Browser): Camera/Microphone access, WebSocket connection (Color: Red)

MIDDLE ROW (Core Platform):
- "Load Balancer" (Cloud Load Balancing): HTTP/HTTPS ingress (Color: Teal)
- "App Server" (Cloud Run): FastAPI + Uvicorn, Stream handling (Color: Green)
- "ADK Runner" (Agent Runtime): Manages agent lifecycle (Color: Blue)

BOTTOM ROW (Backend Services):
- "Session Service" (Redis): State management (Color: Orange)
- "Gemini Live API" (Vertex AI): Multimodal AI model, storage and processing (Color: Purple)
- "Tools" (Function Tools): Inventory, Video Monitor (Color: Green)

Connections:
- User Client -> Load Balancer (HTTPS/WSS)
- Load Balancer -> App Server (HTTP/WS)
- App Server <-> ADK Runner (Internal)
- ADK Runner <-> Session Service (Read/Write)
- ADK Runner <-> Gemini Live API (Bidi Stream)
- ADK Runner <-> Tools (Tool Calls)

Use Google Cloud product icon style. Clean lines, no 3D effects, modern flat
design. Landscape orientation. Include the Google Cloud logo watermark at
bottom left.
"""

def generate_diagram():
    print(f"Generating diagram using project {PROJECT_ID}...")
    
    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=PROMPT,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
        )
        
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                with open(OUTPUT_FILE, "wb") as f:
                    f.write(part.inline_data.data)
                print(f"Diagram saved to {OUTPUT_FILE}")
                return True
                
    except Exception as e:
        print(f"Error generating diagram: {e}")
        return False

if __name__ == "__main__":
    generate_diagram()
