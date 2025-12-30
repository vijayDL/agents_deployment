"""Runtime configuration for the healthcare agent."""

import os


class Config:
    """Simple runtime configuration from environment variables."""

    @property
    def google_cloud_project(self) -> str:
        return os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID", "")

    @property
    def google_cloud_location(self) -> str:
        return os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GCP_LOCATION", "us-central1")

    @property
    def agent_name(self) -> str:
        return os.getenv("AGENT_NAME", "healthcare_agent")


config = Config()
