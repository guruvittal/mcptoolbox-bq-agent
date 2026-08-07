# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry() -> str | None:
    """Configure OpenTelemetry Cloud Trace and GenAI telemetry."""
    os.environ.setdefault("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", "true")
    os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true")

    # Cloud Trace API v2 requires the alphanumeric project ID (e.g. 'vertexsearch-447722').
    # Numeric project numbers (e.g. '36841365232') cause '400 Invalid project id in name!' errors.
    project_id = os.environ.get("GCP_PROJECT_ID", "vertexsearch-447722")
    if not project_id or project_id.isdigit() or "/" in project_id:
        project_id = "vertexsearch-447722"

    # Configure OpenTelemetry Cloud Trace Exporter
    try:
        provider = TracerProvider()
        cloud_exporter = CloudTraceSpanExporter(project_id=project_id)
        provider.add_span_processor(BatchSpanProcessor(cloud_exporter))
        trace.set_tracer_provider(provider)
        logging.info(f"Cloud Trace Exporter initialized with alphanumeric project ID: {project_id}")
    except Exception as e:
        logging.warning(f"Failed to initialize CloudTraceSpanExporter: {e}")

    bucket = os.environ.get("LOGS_BUCKET_NAME")
    if bucket:
        logging.info(
            "Prompt-response logging enabled - mode: NO_CONTENT (metadata only)"
        )
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT", "jsonl")
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK", "upload")
        os.environ.setdefault(
            "OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental"
        )
        commit_sha = os.environ.get("COMMIT_SHA", "dev")
        os.environ.setdefault(
            "OTEL_RESOURCE_ATTRIBUTES",
            f"service.namespace=bq-analytics-agent,service.version={commit_sha}",
        )
        path = os.environ.get("GENAI_TELEMETRY_PATH", "completions")
        os.environ.setdefault(
            "OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH",
            f"gs://{bucket}/{path}",
        )

    return bucket
