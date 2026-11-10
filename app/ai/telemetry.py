"""Send traces and our usage log to Application Insights (Lab 6, Task 3).

Opt-in: nothing imports this at import time, so tests and non-Azure runs never
need the monitoring packages or a network. Entry points call setup() once.
"""
import logging
import os

from app.ai.foundry_client import get_project_client

_configured = False


def setup() -> None:
    global _configured
    if _configured:
        return

    # Imported here so merely importing app.ai.telemetry stays cheap and safe.
    from azure.ai.projects.telemetry import AIProjectInstrumentor
    from azure.monitor.opentelemetry import configure_azure_monitor

    # The Foundry SDK tracing is experimental and must be switched on explicitly.
    os.environ.setdefault("AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING", "true")
    # D63: expense data is personal data, so traces carry metadata, not content.
    os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false")

    # Read the connection string from the project instead of copying it into
    # .env: one less value to leak, and it follows the project if it is rebuilt.
    connection_string = get_project_client().telemetry.get_application_insights_connection_string()

    # logger_name: attach the Azure Monitor log handler to OUR usage logger only,
    # not to the root logger, so SDK/HTTP library chatter does not become traces.
    # sampling_ratio=1.0: keep every trace. Azure Monitor's DEFAULT is a rate-limited
    # sampler (5 traces/second); in a quick loop it drops spans, and the Foundry
    # SDK's responses instrumentor then crashes on the dropped ("non-recording")
    # span with AttributeError. Verified offline: default records 16 of 20 spans in a
    # tight loop, ratio 1.0 records 20 of 20. At real volume, lower the ratio for cost.
    configure_azure_monitor(
        connection_string=connection_string,
        logger_name="expense_ai.usage",
        sampling_ratio=1.0,
    )
    AIProjectInstrumentor().instrument(enable_content_recording=False)
    logging.getLogger("expense_ai.usage").setLevel(logging.INFO)
    _configured = True


def flush() -> None:
    """Short scripts exit before the background exporter runs: push data now."""
    from opentelemetry import trace
    from opentelemetry._logs import get_logger_provider

    for provider in (trace.get_tracer_provider(), get_logger_provider()):
        force_flush = getattr(provider, "force_flush", None)
        if force_flush:
            force_flush()
