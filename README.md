# Healthcare Intake Agent (Vertex AI Reasoning Engine)

Deploy Google ADK agents to Vertex AI Agent Engine with clean separation between Agent and Deployment teams.

---

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.prod.example .env.prod
# Edit .env.prod with your GCP settings

# 3. Authenticate
gcloud auth login
gcloud auth application-default login

# 4. Deploy
uv run python deployment/deploy.py
```

> Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`

---

## Project Structure

```text
healthcare_agent/              # AGENT TEAM
├── agent.py                   # root_agent definition
└── requirements.txt           # Agent dependencies

deployment/                    # DEPLOYMENT TEAM
├── agent_config.yaml          # What agent to deploy
├── deploy.py                  # Deployment script
└── DEPLOY.md                  # Technical documentation
```

---

## Team Responsibilities

| Team | Maintains | No knowledge of |
|------|-----------|-----------------|
| **Agent Team** | `healthcare_agent/` (code + requirements) | Deployment infrastructure |
| **Deployment Team** | `deployment/agent_config.yaml` + `.env.prod` | Agent code internals |

---

## Configuration

### `.env.prod` (required)

```text
AGENT_NAME=Healthcare-bot
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_CLOUD_STAGING_BUCKET=your-bucket
```

### `deployment/agent_config.yaml`

```yaml
agent:
  source_package: "healthcare_agent"
  entrypoint_module: "healthcare_agent.agent"
  entrypoint_object: "root_agent"
  requirements_file: "healthcare_agent/requirements.txt"
  description: "Healthcare Intake Agent"
```

---

## Documentation

For technical details, see [deployment/DEPLOY.md](deployment/DEPLOY.md).
