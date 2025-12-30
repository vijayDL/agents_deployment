"""Configuration management for the healthcare agent."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Calculate paths relative to this file
_THIS_DIR = Path(__file__).parent
_PROJECT_ROOT = _THIS_DIR.parent
_ENV_FILE = _PROJECT_ROOT / ".env.prod"


def _get_project() -> str:
    """Get project ID from environment, supporting alternative names."""
    return os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID", "")


def _get_location() -> str:
    """Get location from environment, supporting alternative names."""
    return os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GCP_LOCATION", "us-central1")


class AgentConfig(BaseSettings):
    """Global configuration loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    google_cloud_project: str = Field(default_factory=_get_project, description="Google Cloud project ID")
    google_cloud_location: str = Field(default_factory=_get_location, description="Google Cloud location")
    agent_name: str = Field(default="healthcare_agent", description="Agent name")


class DeploymentConfig(BaseModel):
    """Configuration for deployment."""

    agent_name: str
    project: str
    location: str
    staging_bucket: str
    requirements_file: str = "requirements.txt"
    extra_packages: list[str] = []


def load_config() -> DeploymentConfig:
    """Load deployment configuration from .env.prod."""
    if not _ENV_FILE.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {_ENV_FILE}\n"
            "Create .env.prod with required variables. See README.md for details."
        )

    load_dotenv(str(_ENV_FILE), override=True)
    print(f"Loaded config from: {_ENV_FILE}")

    staging_bucket = os.getenv("GOOGLE_CLOUD_STAGING_BUCKET")
    if not staging_bucket:
        raise ValueError("GOOGLE_CLOUD_STAGING_BUCKET is required in .env.prod")

    return DeploymentConfig(
        agent_name=os.getenv("AGENT_NAME", "Healthcare-agent"),
        project=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        staging_bucket=staging_bucket,
    )


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


# Global config instance
config = AgentConfig()
