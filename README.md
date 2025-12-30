# Healthcare Intake Agent (Vertex AI Reasoning Engine)

An example deployment project for a Google ADK agent on Vertex AI Reasoning Engine. Uses **Gemini 2.5 Flash** with Firestore-backed session management.

---

## 1. Project Structure
```text
.
├── healthcare_agent/          # Core Logic Package
│   ├── agent.py               # Root Agent definition
│   └── __init__.py            # (Empty - Required for deployment)
├── deployment/                # Deployment utilities
│   ├── deploy.py              # Main deployment script
│   ├── app.py                 # AgentEngineApp wrapper
│   ├── config.py              # Configuration management
│   ├── tracing.py             # Cloud Trace integration
│   └── gcp/                   # GCP utilities
│       ├── apis.py            # API enablement
│       ├── storage.py         # Bucket management
│       └── iam.py             # Service account management
├── requirements.txt           # Dependencies
└── .env.prod                  # Configuration (create this)
```

---

## 2. Deployment Guide

### Step 1: Clone and Setup

```bash
git clone [YOUR_GITHUB_REPOSITORY_URL]
cd [YOUR_PROJECT_FOLDER_NAME]

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip3 install -r requirements.txt
```

### Step 2: Configure Environment

Create `.env.prod` in the project root:

```text
GOOGLE_CLOUD_PROJECT=[YOUR_GCP_PROJECT_ID]
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_CLOUD_STAGING_BUCKET=[YOUR_GCS_STAGING_BUCKET]
NUM_WORKERS=1
AGENT_NAME=Healthcare-bot
GOOGLE_GENAI_USE_VERTEXAI=TRUE
```

### Step 3: Authenticate with Google Cloud

```bash
gcloud auth login
gcloud config set project [YOUR_PROJECT_ID]
gcloud auth application-default login
```

### Step 4: Deploy

```bash
# Deploy to Vertex AI
python3 deployment/deploy.py

# Force recreate (if update fails)
python3 deployment/deploy.py --force-recreate
```

---

## 3. Testing the Agent

### Create a Session

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://[LOCATION]-aiplatform.googleapis.com/v1/projects/[PROJECT_ID]/locations/[LOCATION]/reasoningEngines/[ENGINE_ID]:query" \
  -d '{"classMethod": "create_session", "input": {"user_id": "test_user_01"}}'
```

### Send a Message (Streaming)

Replace `[SESSION_ID]` with the ID from the session creation response.

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://[LOCATION]-aiplatform.googleapis.com/v1/projects/[PROJECT_ID]/locations/[LOCATION]/reasoningEngines/[ENGINE_ID]:streamQuery?alt=sse" \
  -d '{"input": {"user_id": "test_user_01", "session_id": "[SESSION_ID]", "message": "Hello!"}}'
```

---

## 4. Troubleshooting

| Issue | Solution |
|-------|----------|
| `Refreshing tokens failed` | Re-run `gcloud auth application-default login` |
| IAM Permission Error | Ensure `Service Account User` and `Vertex AI Administrator` roles |
| `ModuleNotFoundError` | Activate `.venv` and run `pip3 install -r requirements.txt` |
| 400 InvalidArgument on deploy | Use `--force-recreate` flag or check `healthcare_agent/__init__.py` is empty |
