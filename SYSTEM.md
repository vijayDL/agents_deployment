### `system.md` 

# ⚙️ System Architecture: Healthcare Intake Agent

This document details the internal logic, data flow, and architectural design of the Healthcare Intake Assistant. It serves as the primary technical reference for the agent's reasoning capabilities.

---

## 🎯 System Overview
The system is designed as a **Stateful AI Agent** that manages medical intake conversations. It does not just react to prompts; it maintains a structured state to collect patient symptoms systematically.

### Core Objectives:
- **Symptom Identification**: Extracting primary and secondary symptoms from natural language.
- **Contextual Memory**: Remembering user inputs across multiple turns.
- **Safety Boundaries**: Providing general health information while explicitly disclaiming professional medical advice.

---

## 🧩 Architectural Components

### 1. The Reasoning Engine (Brain)
- **Model**: `gemini-2..5-flash`
- **Orchestrator**: Google ADK `AdkApp`
- **Logic**: The agent uses a "Reasoning Loop" to determine if it has enough information to complete an intake or if it needs to ask follow-up questions.

### 2. Session Management (Memory)
Unlike standard LLM calls, this system is stateful.
- **Service**: `VertexAiSessionService`
- **Backend**: Google Firestore (Default).
- **Function**: Persists the `user_id` and `session_id` mapping, ensuring that if a user disconnects, their symptoms are still "known" by the agent upon return.



---

## 🔄 Data Flow: From User to Gemini

1. **Entry Point**: The user sends a message via the `streamQuery` endpoint.
2. **Session Retrieval**: The system fetches the conversation history from Firestore using the `session_id`.
3. **Prompt Augmentation**: The system combines the **System Instructions** (defined in `agent.py`) with the **History** and the **New Message**.
4. **Inference**: Gemini processes the package and generates a response.
5. **Storage**: The new response is saved back to the session history.
6. **Streaming**: The response is streamed back to the user via SSE (Server-Sent Events).



---

## 🛠️ Internal Code Modules

| File | Responsibility |
| :--- | :--- |
| `agent.py` | Contains the `root_agent` definition, system prompts, and tool registrations. |
| `deployment/config.py` | Manages environment-specific settings (GCP Project, Region, IDs). |
| `deployment/tracing.py` | Handles OpenTelemetry integration for Google Cloud Trace. |
| `utils/typing.py` | Defines Pydantic models for structured feedback and input validation. |

---

## 📈 Observability & Monitoring
- **Tracing**: All agent decisions are traced via **Cloud Trace**, allowing developers to see the latency of each LLM call.
- **Logging**: Structured logs are sent to **Cloud Logging** under the `aiplatform.googleapis.com/reasoning_engine` resource.
- **Feedback**: The `register_feedback` method allows users to submit "thumbs up/down" ratings which are stored as structured log entries.

---

## 🛡️ Security & Compliance
- **Authentication**: All access requires a valid OAuth2 Bearer Token.
- **IAM**: The system runs under a least-privileged Service Account with specific Vertex AI User permissions.
- **Data Privacy**: Conversation data is stored within the project's regional Firestore instance.



