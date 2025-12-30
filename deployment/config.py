"""Configuration management for deployment.

This module provides clean separation between:
- Agent team: Maintains agent code and agent-specific requirements
- Deployment team: Configures deployment via YAML (no code imports needed)

All values must be explicitly set - no hardcoded defaults.
"""

import importlib
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Calculate paths relative to this file
_THIS_DIR = Path(__file__).parent
_PROJECT_ROOT = _THIS_DIR.parent
_ENV_FILE = _PROJECT_ROOT / ".env.prod"
_AGENT_CONFIG_FILE = _THIS_DIR / "agent_config.yaml"


def _require_env(var_name: str) -> str:
    """Get required environment variable or raise error."""
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Required environment variable '{var_name}' is not set in .env.prod")
    return value


class AgentSpec(BaseModel):
    """Agent specification - what the deployment team configures.

    This allows deployment without importing agent code directly.
    The agent is loaded dynamically at deployment time.
    """
    source_package: str = Field(description="Package containing the agent code")
    entrypoint_module: str = Field(description="Module path (e.g., 'healthcare_agent.agent')")
    entrypoint_object: str = Field(description="Object name (e.g., 'root_agent')")
    requirements_file: str = Field(description="Path to agent requirements file")
    description: str = Field(description="Agent description for Vertex AI console")


class AgentConfigFile(BaseModel):
    """Schema for agent_config.yaml file."""
    agent: AgentSpec
    env_vars: dict[str, str] = Field(default_factory=dict)


class DeploymentConfig(BaseModel):
    """Complete deployment configuration combining env and agent config."""

    # From environment (.env.prod)
    agent_name: str
    project: str
    location: str
    staging_bucket: str

    # From agent_config.yaml
    agent_spec: AgentSpec
    env_vars: dict[str, str] = Field(default_factory=dict)


def load_agent_config() -> AgentConfigFile:
    """Load agent configuration from agent_config.yaml."""
    if not _AGENT_CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Agent config not found: {_AGENT_CONFIG_FILE}\n"
            "Create agent_config.yaml with agent specification. See DEPLOY.md for details."
        )

    with open(_AGENT_CONFIG_FILE) as f:
        data = yaml.safe_load(f)

    return AgentConfigFile(**data)


def load_config() -> DeploymentConfig:
    """Load complete deployment configuration.

    Combines:
    - Environment variables from .env.prod (GCP settings)
    - Agent specification from agent_config.yaml (what to deploy)

    All environment variables are required - no defaults.
    """
    # Load environment config
    if not _ENV_FILE.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {_ENV_FILE}\n"
            "Create .env.prod with required variables. See README.md for details."
        )

    load_dotenv(str(_ENV_FILE), override=True)
    print(f"Loaded env config from: {_ENV_FILE}")

    # Load agent config
    agent_config = load_agent_config()
    print(f"Loaded agent config from: {_AGENT_CONFIG_FILE}")

    # Get required env vars (will raise if not set)
    agent_name = _require_env("AGENT_NAME")
    project = _require_env("GOOGLE_CLOUD_PROJECT")
    location = _require_env("GOOGLE_CLOUD_LOCATION")
    staging_bucket = _require_env("GOOGLE_CLOUD_STAGING_BUCKET")

    # Merge env_vars from yaml with GCP-specific vars
    env_vars = dict(agent_config.env_vars)
    env_vars.update({
        "GCP_PROJECT_ID": project,
        "GCP_LOCATION": location,
        "AGENT_NAME": agent_name,
    })

    return DeploymentConfig(
        agent_name=agent_name,
        project=project,
        location=location,
        staging_bucket=staging_bucket,
        agent_spec=agent_config.agent,
        env_vars=env_vars,
    )


def load_agent_from_spec(agent_spec: AgentSpec):
    """Dynamically load agent object from specification.

    This is the key function that enables separation of concerns:
    - Deployment team specifies module/object in config
    - Agent is loaded dynamically without hardcoded imports

    Args:
        agent_spec: Agent specification with module path and object name

    Returns:
        The agent object (ADK Agent instance)

    Raises:
        ImportError: If module cannot be imported
        AttributeError: If object not found in module
        ValueError: If object is None
    """
    # Import the module dynamically
    module = importlib.import_module(agent_spec.entrypoint_module)

    # Get the agent object
    agent = getattr(module, agent_spec.entrypoint_object)

    if agent is None:
        raise ValueError(
            f"Agent object '{agent_spec.entrypoint_object}' "
            f"in module '{agent_spec.entrypoint_module}' is None"
        )

    return agent


def update_env_file(var_name: str, value: str) -> None:
    """Update or add a variable in .env.prod."""
    lines = _ENV_FILE.read_text().splitlines() if _ENV_FILE.exists() else []

    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{var_name}="):
            lines[i] = f"{var_name}={value}"
            updated = True
            break

    if not updated:
        lines.append(f"{var_name}={value}")

    _ENV_FILE.write_text("\n".join(lines) + "\n")
