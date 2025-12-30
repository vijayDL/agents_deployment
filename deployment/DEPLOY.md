# Deployment Guide: Healthcare Intake Reasoning Engine

Technical documentation for deploying the Healthcare Agent to **Google Vertex AI**.

---

## Technical Context

This project uses the **Google ADK (Agent Development Kit)** to deploy a Python-based agent as a **Vertex AI Reasoning Engine**.

### Tech Stack
- **Language**: Python 3.11 (Required for `cloudpickle` compatibility)
- **Model**: Gemini 2.5 Flash
- **Framework**: Google ADK / `AdkApp`
- **Infrastructure**: Vertex AI Reasoning Engine (Serverless)
- **Session Storage**: `VertexAiSessionService` (Firestore-backed)
- **Observability**: OpenTelemetry with Google Cloud Trace

---

## Development Workflow

### 1. Initial Agent Scaffolding (Local Setup)
The `adk` command-line tool generates the local folder structure:
```bash
adk create healthcare_agent
```

### 2. Cloud Deployment

The `deployment/` module handles deployment to Google Cloud:

```
deployment/
├── deploy.py      # Main entry point
├── app.py         # AgentEngineApp wrapper
├── config.py      # Configuration management
├── tracing.py     # Cloud Trace integration
└── gcp/           # GCP utilities (APIs, Storage, IAM)
```

Features:
- Automatic API enablement
- Service account management with IAM roles
- Staging bucket creation

---

## Environment Variables

Create `.env.prod` in the project root.

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CLOUD_PROJECT` | GCP Project ID | Yes |
| `GOOGLE_CLOUD_LOCATION` | Deployment Region (e.g., `us-central1`) | Yes |
| `GOOGLE_CLOUD_STAGING_BUCKET` | GCS bucket for staging artifacts | Yes |
| `NUM_WORKERS` | Worker count for the engine (default: 1) | No |
| `AGENT_NAME` | Display name for the agent | No |
| `GOOGLE_GENAI_USE_VERTEXAI` | Set to `TRUE` for Vertex AI | Yes |

---

## Critical Pre-Deployment Rules

### 1. Requirements Sanitization

Vertex AI fails if `requirements.txt` contains inline comments. The deployment script handles this automatically, but if needed manually:

```bash
# Mac/Linux
sed -i '' 's/ #.*//' requirements.txt
```

### 2. The "Slim Build" Architecture

- **`requirements.txt`**: Keep minimal (core libraries only)
- **`healthcare_agent/__init__.py`**: **MUST remain empty (0 bytes)**
- This ensures the Cloud environment is ready before importing agent code

---

## Deployment Commands

```bash
# Deploy to Vertex AI
python3 deployment/deploy.py

# Force recreate (deletes existing agent first)
python3 deployment/deploy.py --force-recreate
```

---

## Post-Deployment Testing

The agent uses a **Stateful Session Protocol**.

### 1. Create Session

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://[LOCATION]-aiplatform.googleapis.com/v1/projects/[PROJECT_ID]/locations/[LOCATION]/reasoningEngines/[ENGINE_ID]:query" \
  -d '{"classMethod": "create_session", "input": {"user_id": "[USER_NAME]"}}'
```

### 2. Stream Inference (SSE)

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://[LOCATION]-aiplatform.googleapis.com/v1/projects/[PROJECT_ID]/locations/[LOCATION]/reasoningEngines/[ENGINE_ID]:streamQuery?alt=sse" \
  -d '{"input": {"user_id": "[USER_NAME]", "session_id": "[SESSION_ID]", "message": "Hello!"}}'
```

---

## Important Constraints

| Rule | Reason |
|------|--------|
| `healthcare_agent/__init__.py` must be empty | Prevents `ModuleNotFoundError` during cloud build |
| Python 3.11 required | `cloudpickle` compatibility with Vertex AI |
| No hardcoded credentials | Use environment variables via `.env.prod` |
