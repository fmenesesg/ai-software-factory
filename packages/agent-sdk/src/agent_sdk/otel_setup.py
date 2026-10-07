"""Configure OpenTelemetry TracerProvider from env (OTLP → collector/Jaeger)."""

from __future__ import annotations

import os


def configure_otel_from_env() -> bool:
    """Install OTLP exporter when OTEL_EXPORTER_OTLP_ENDPOINT is set.

    Returns True if a real TracerProvider was configured.
    """
    otlp_endpoint = (os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or "").strip()
    if not otlp_endpoint:
        return False

    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    current = trace.get_tracer_provider()
    if type(current).__name__ == "TracerProvider":
        return True

    service = (
        os.environ.get("OTEL_SERVICE_NAME")
        or (os.environ.get("ASF_UVICORN_APP") or "asf").split(":")[0]
    )
    resource = Resource.create(
        {
            "service.name": service,
            "service.namespace": os.environ.get("NAMESPACE_PREFIX", "asf"),
            "deployment.environment": os.environ.get("ASF_PROFILE", "kind-oss"),
        }
    )
    provider = TracerProvider(resource=resource)

    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        traces_endpoint = otlp_endpoint.rstrip("/")
        if not traces_endpoint.endswith("/v1/traces"):
            traces_endpoint = f"{traces_endpoint}/v1/traces"
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=traces_endpoint)))
        print(f"otel_setup: OTLP → {traces_endpoint}", flush=True)
    except ImportError:
        print("otel_setup: otlp http exporter missing", flush=True)
        return False

    trace.set_tracer_provider(provider)
    print(f"otel_setup: service.name={service}", flush=True)
    return True
