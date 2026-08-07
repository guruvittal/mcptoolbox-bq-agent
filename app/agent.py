# ruff: noqa
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

import datetime
import logging
import os
from zoneinfo import ZoneInfo

import google.auth
from google.cloud import bigquery
from google.genai import types

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.plugins.bigquery_agent_analytics_plugin import (
    BigQueryAgentAnalyticsPlugin,
    BigQueryLoggerConfig,
)

# Setup GCP environment credentials & defaults
try:
    _, default_project = google.auth.default()
    if default_project:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", default_project)
except Exception:
    pass

os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")


def query_bigquery(sql_query: str) -> str:
    """Executes a Standard SQL SELECT query against BigQuery datasets (such as agent_analytics).

    Args:
        sql_query: A valid Standard SQL SELECT statement.

    Returns:
        A string representation of query results or an error message.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        return "Error: GOOGLE_CLOUD_PROJECT environment variable is not set."

    # Safety check: enforce read-only
    trimmed_query = sql_query.strip().upper()
    if not trimmed_query.startswith("SELECT") and not trimmed_query.startswith("WITH"):
        return "Error: Only read-only SELECT or WITH queries are permitted."

    try:
        client = bigquery.Client(project=project_id)
        query_job = client.query(sql_query)
        results = query_job.result(timeout=30)

        rows = [dict(row) for row in results]
        if not rows:
            return "Query executed successfully. No rows returned."

        if len(rows) > 50:
            return f"Returned first 50 rows of {len(rows)} total:\n" + str(rows[:50])
        return str(rows)
    except Exception as e:
        return f"BigQuery query error: {str(e)}"


# Tools list
tools = [query_bigquery]

# Dynamically connect to MCP Toolbox on Cloud Run if URL is provided
toolbox_url = os.environ.get("TOOLBOX_SERVER_URL")
if toolbox_url:
    try:
        from google.adk.tools.toolbox_toolset import ToolboxToolset

        toolbox = ToolboxToolset(server_url=toolbox_url)
        tools.append(toolbox)
        logging.info(f"Connected to MCP Toolbox at {toolbox_url}")
    except Exception as e:
        logging.warning(f"Could not initialize MCP Toolbox at {toolbox_url}: {e}")

root_agent = Agent(
    name="bq_analytics_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are a specialized BigQuery AI Analytics Agent for querying and analyzing the `agent_analytics` dataset.

Your primary responsibilities:
1. Query, inspect, and analyze BigQuery tables in the `agent_analytics` dataset.
2. Discover available tables and schemas using MCP Toolbox tools or BigQuery query tool.
3. Write clean, efficient Standard SQL queries.
4. Format your responses using clear Markdown tables, bullet points, and key insights.

Safety Constraints:
- Only execute read-only queries (SELECT or WITH statements).
- Do not attempt DDL/DML operations (CREATE, DROP, DELETE, UPDATE, INSERT).
""",
    tools=tools,
)

# Initialize BigQuery Analytics Plugin for ADK observability
_plugins = []
_project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
_dataset_id = os.environ.get("BQ_ANALYTICS_DATASET_ID", "agent_analytics")
_location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-east1")

if _project_id:
    try:
        bq = bigquery.Client(project=_project_id)
        bq.create_dataset(f"{_project_id}.{_dataset_id}", exists_ok=True)

        _plugins.append(
            BigQueryAgentAnalyticsPlugin(
                project_id=_project_id,
                dataset_id=_dataset_id,
                location=_location,
                config=BigQueryLoggerConfig(
                    gcs_bucket_name=os.environ.get("BQ_ANALYTICS_GCS_BUCKET"),
                    connection_id=os.environ.get("BQ_ANALYTICS_CONNECTION_ID"),
                ),
            )
        )
    except Exception as e:
        logging.warning(f"Failed to initialize BigQuery Analytics plugin: {e}")

app = App(
    root_agent=root_agent,
    name="app",
    plugins=_plugins,
)
