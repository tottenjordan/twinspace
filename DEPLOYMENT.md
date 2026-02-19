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
