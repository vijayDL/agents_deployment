"""
OpenTelemetry tracing utilities for Google Cloud Trace.
"""

import logging
from collections.abc import Sequence

from google.cloud import trace_v1
from google.protobuf import timestamp_pb2
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

logger = logging.getLogger(__name__)


class CloudTraceLoggingSpanExporter(SpanExporter):
    """
    OpenTelemetry span exporter that sends traces to Google Cloud Trace.
    """

    def __init__(self, project_id: str, service_name: str) -> None:
        self.project_id = project_id
        self.service_name = service_name
        self.client = trace_v1.TraceServiceClient()

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export spans to Google Cloud Trace."""
        if not spans:
            return SpanExportResult.SUCCESS

        try:
            traces: dict[str, trace_v1.Trace] = {}

            for span in spans:
                trace_id = format(span.context.trace_id, "032x")
                span_id = format(span.context.span_id, "016x")

                if trace_id not in traces:
                    traces[trace_id] = trace_v1.Trace(
                        project_id=self.project_id,
                        trace_id=trace_id,
                        spans=[],
                    )

                # Convert timestamps
                start_time = timestamp_pb2.Timestamp()
                start_time.FromNanoseconds(span.start_time)
                end_time = timestamp_pb2.Timestamp()
                end_time.FromNanoseconds(span.end_time)

                trace_span = trace_v1.TraceSpan(
                    span_id=int(span_id, 16),
                    name=span.name,
                    start_time=start_time,
                    end_time=end_time,
                    labels={
                        "service.name": self.service_name,
                        **{str(k): str(v) for k, v in (span.attributes or {}).items()},
                    },
                )

                if span.parent and span.parent.span_id:
                    trace_span.parent_span_id = span.parent.span_id

                traces[trace_id].spans.append(trace_span)

            # Batch write traces
            if traces:
                self.client.patch_traces(
                    project_id=self.project_id,
                    traces=trace_v1.Traces(traces=list(traces.values())),
                )

            return SpanExportResult.SUCCESS

        except Exception as e:
            logger.warning(f"Failed to export spans to Cloud Trace: {e}")
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        """Shutdown the exporter."""
        pass

