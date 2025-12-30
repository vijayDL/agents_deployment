"""Agent Engine Application wrapper for Vertex AI deployment."""

import copy

from google.adk.sessions import VertexAiSessionService
from google.cloud import logging as google_cloud_logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, export
from vertexai.agent_engines import AdkApp

from deployment.config import config
from deployment.tracing import CloudTraceLoggingSpanExporter


def create_session_service() -> VertexAiSessionService:
    """Create a VertexAI session service for Firestore-backed persistence."""
    return VertexAiSessionService(
        project=config.google_cloud_project,
        location=config.google_cloud_location,
    )


class AgentEngineApp(AdkApp):
    """ADK Application wrapper with logging and tracing."""

    def set_up(self) -> None:
        """Set up logging and tracing."""
        super().set_up()

        # Cloud Logging
        logging_client = google_cloud_logging.Client()
        self.logger = logging_client.logger(__name__)

        # OpenTelemetry tracing
        provider = TracerProvider()
        processor = export.BatchSpanProcessor(
            CloudTraceLoggingSpanExporter(
                project_id=config.google_cloud_project,
                service_name=f"{config.agent_name}-service",
            )
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        self.enable_tracing = True

    def register_operations(self) -> dict[str, list[str]]:
        """Register available operations."""
        return super().register_operations()

    def clone(self) -> "AgentEngineApp":
        """Create a copy of this application."""
        attrs = self._tmpl_attrs
        return self.__class__(
            agent=copy.deepcopy(attrs["agent"]),
            session_service_builder=attrs.get("session_service_builder"),
        )
