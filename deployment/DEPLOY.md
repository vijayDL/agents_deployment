# Deployment Guide: Vertex AI Agent Engine

Technical documentation for deploying agents to **Google Vertex AI Agent Engine**.

---

## Architecture Overview

This project separates concerns between **Agent Team** and **Deployment Team**:

```
Agent Team                         Deployment Team
─────────────                      ────────────────
healthcare_agent/                  deployment/
├── agent.py (root_agent)          ├── agent_config.yaml
└── requirements.txt               ├── deploy.py
                                   └── .env.prod
```

- **Agent Team**: Writes agent code, no deployment knowledge needed
- **Deployment Team**: Configures and deploys via YAML, no code imports needed

---

## Tech Stack

- **Language**: Python 3.11 (Required for `cloudpickle` compatibility)
- **Model**: Gemini 2.5 Flash
- **Framework**: Google ADK / `AdkApp`
- **Infrastructure**: Vertex AI Reasoning Engine (Serverless)
- **Session Storage**: `VertexAiSessionService` (Firestore-backed)
- **Package Manager**: uv (local dev)

---

## Configuration Files

### 1. Agent Specification (`deployment/agent_config.yaml`)

Defines which agent to deploy without code imports:

```yaml
agent:
  source_package: "healthcare_agent"
  entrypoint_module: "healthcare_agent.agent"
  entrypoint_object: "root_agent"
  requirements_file: "healthcare_agent/requirements.txt"
  description: "Healthcare Intake Agent"

env_vars: {}
```

| Field | Description |
|-------|-------------|
| `source_package` | Package directory to bundle |
| `entrypoint_module` | Python module path |
| `entrypoint_object` | Agent object name to load |
| `requirements_file` | Agent runtime dependencies |
| `description` | Display in Vertex AI console |
| `env_vars` | Additional environment variables |

### 2. Environment Variables (`.env.prod`)

All variables are **required** (no defaults):

```text
AGENT_NAME=Healthcare-bot
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_CLOUD_STAGING_BUCKET=your-staging-bucket
```

---

## Deployment Commands

```bash
# Install dependencies
uv sync

# Deploy to Vertex AI
uv run python deployment/deploy.py

# Force recreate (deletes existing agent first)
uv run python deployment/deploy.py --force-recreate
```

---

## Deployment Flow

The `deploy.py` script:

1. Loads `.env.prod` (GCP settings)
2. Loads `agent_config.yaml` (agent specification)
3. Enables required GCP APIs
4. Creates/reuses staging bucket
5. Sets up service account with IAM roles
6. **Dynamically loads agent** from `entrypoint_module:entrypoint_object`
7. Deploys to Vertex AI Agent Engine
8. Saves metadata to `logs/deployment_metadata.json`

---

## Deploying a Different Agent

To deploy a new agent, the Deployment Team only updates `agent_config.yaml`:

```yaml
agent:
  source_package: "my_new_agent"
  entrypoint_module: "my_new_agent.main"
  entrypoint_object: "agent"
  requirements_file: "my_new_agent/requirements.txt"
  description: "My New Agent"
```

No changes to `deploy.py` required.

---

## Post-Deployment Testing

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

## Troubleshooting

Check logs at: https://console.cloud.google.com/logs/

---

## Important Constraints

| Rule | Reason |
|------|--------|
| `healthcare_agent/__init__.py` must be empty | Prevents `ModuleNotFoundError` during cloud build |
| Python 3.11 required | `cloudpickle` compatibility with Vertex AI |
| No hardcoded credentials | Use `.env.prod` for all config |
| All env vars required | No defaults in code |
