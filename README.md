# BigQuery Analytics Agent with MCP Toolbox on Cloud Run

A production-ready BigQuery AI Analytics Agent built with Google's **Agent Development Kit (ADK)** and integrated with the **MCP Toolbox for Databases** deployed on **Google Cloud Run**.

The agent provides natural language query capabilities, table schema discovery, and analytics execution over BigQuery datasets (such as `agent_analytics`), supported by full telemetry and audit logging via the **BigQuery Agent Analytics Plugin**.

---

## 🏗 System Architecture

```
+-------------------+           HTTP / SSE          +-----------------------+           ADC / IAM           +-------------------+
|   ADK AI Agent    | ---------------------------> |  MCP Toolbox          | ---------------------------> |  Google BigQuery  |
|  (Python / ADK)   |  (ToolboxToolset)             |  (Cloud Run Container)|  (bigquery.jobs, etc.)     |  (agent_analytics)|
+-------------------+                               +-----------------------+                               +-------------------+
          |
          v
+-----------------------------------+
| BigQuery Agent Analytics Plugin   |
| (Execution telemetry & audit logs)|
+-----------------------------------+
```

### Key Components

1. **ADK AI Agent (`app/agent.py`)**: Built using Python 3.12 and Google ADK (`google-adk`). Connects to MCP Toolbox via `ToolboxToolset` and enforces read-only Standard SQL execution constraints.
2. **MCP Toolbox on Cloud Run (`mcp-toolbox/`)**: Centralized, serverless control plane container running on Cloud Run, exposing secure database tools over HTTP/SSE.
3. **BigQuery Telemetry Plugin**: Uses `BigQueryAgentAnalyticsPlugin` to log conversation trajectories, tool calls, and LLM responses directly back to BigQuery.

---

## 📋 Prerequisites

Before getting started, ensure you have installed and configured:

- **Python**: `>= 3.11` (Python 3.12 recommended)
- **uv**: Fast Python package installer and dependency resolver ([Install uv](https://docs.astral.sh/uv/getting-started/installation/))
- **Google Cloud SDK (`gcloud`)**: Authenticated with access to BigQuery, Cloud Run, Cloud Build, and Artifact Registry.
- **Docker**: Optional for local container testing.
- **Google Agents CLI (`google-agents-cli`)**: Installed via `uv tool install google-agents-cli`.

---

## ⚙️ Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/guruvittal/mcptoolbox-bq-agent.git
   cd mcptoolbox-bq-agent
   ```

2. **Install Dependencies**:
   Use `uv` to create a virtual environment and synchronize dependencies:
   ```bash
   uv sync
   ```

3. **Authenticate Google Cloud Credentials**:
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

4. **Environment Configuration**:
   Create or update `.env` in the project root:
   ```env
   GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
   GOOGLE_CLOUD_LOCATION=global
   BQ_ANALYTICS_DATASET_ID=agent_analytics
   # Set after deploying MCP Toolbox:
   # TOOLBOX_SERVER_URL=https://mcp-bigquery-toolbox-xxxxxx-uc.a.run.app
   ```

---

## 🚀 Running the Agent

### 1. Local CLI Smoke Test
Run a quick query using `agents-cli`:
```bash
agents-cli run "What tables are available in the agent_analytics dataset?"
```

### 2. Interactive Web Playground
Launch the ADK interactive local developer playground:
```bash
agents-cli playground
```
This opens a web UI at `http://localhost:8501` to test streaming responses, view step-by-step tool calls, and inspect session state.

### 3. FastAPI Web Server
To run the agent HTTP service locally using FastAPI/Uvicorn:
```bash
uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8080 --reload
```

---

## 🧪 Testing & Code Quality

This repository includes unit tests, integration tests, linting tools, and ADK evaluation suites.

### 1. Unit & Integration Tests
Run tests using `pytest` via `uv`:

```bash
# Run unit and integration tests
uv run pytest tests/unit tests/integration

# Run tests with verbose output
uv run pytest -v
```

- **Unit Tests (`tests/unit/`)**: Quick component and function validation.
- **Integration Tests (`tests/integration/`)**: Validates streaming query output and runtime feedback handling.

### 2. Code Quality & Linting
Check formatting, imports, and code style:

```bash
# Check code style with agents-cli lint
agents-cli lint

# Or run Ruff directly
uv run ruff check .
```

### 3. ADK Evaluation Loop
Evaluate agent performance against predefined evaluation benchmark sets (`.evalset.json`):

```bash
# Run default evaluation set
agents-cli eval run

# Run specific evaluation set
agents-cli eval run --evalset tests/eval/evalsets/basic.evalset.json

# Run all evaluation sets in the project
agents-cli eval run --all
```

*Note: Evaluation criteria and rubric configurations are located in `tests/eval/eval_config.json`.*

---

## ☁️ Deployment Guide

### Step 1: Deploy MCP Toolbox to Google Cloud Run

The MCP Toolbox container exposes BigQuery tools for the ADK agent.

```bash
cd mcp-toolbox
chmod +x deploy.sh
./deploy.sh
```

Upon successful deployment, note the output Service URL:
```text
========================================================
 SUCCESS! MCP Toolbox deployed to Cloud Run:
 Service URL: https://mcp-bigquery-toolbox-xxxxxx-uc.a.run.app
========================================================
```

### Step 2: Deploy ADK Agent to Google Cloud Run

Link the ADK Agent to the deployed MCP Toolbox URL and deploy to Cloud Run:

```bash
cd ..
export TOOLBOX_SERVER_URL="https://mcp-bigquery-toolbox-xxxxxx-uc.a.run.app"
chmod +x deploy_agent.sh
./deploy_agent.sh
```

Alternatively, deploy using the `agents-cli`:
```bash
agents-cli deploy
```

---

## 📊 Observability & Analytics

The agent is configured with `BigQueryAgentAnalyticsPlugin`, which automatically tracks and records agent execution metrics in BigQuery:

- **Target Dataset**: `agent_analytics`
- **Location**: `us-east1` (or specified via `GOOGLE_CLOUD_LOCATION`)
- **Recorded Data**: User prompts, system responses, tool call inputs/outputs, latency, and session tokens.

---

## 📁 Repository Structure

```
bq-analytics-agent/
├── app/
│   ├── agent.py            # ADK Agent logic & ToolboxToolset integration
│   ├── fast_api_app.py     # FastAPI runner for Cloud Run deployment
│   └── agent_runtime_app.py # Agent Engine App wrapper
├── mcp-toolbox/
│   ├── tools.yaml          # MCP Toolbox database configuration
│   ├── Dockerfile          # MCP Toolbox container file
│   └── deploy.sh           # Deployment script for MCP Toolbox on Cloud Run
├── tests/
│   ├── unit/               # Unit test suite
│   ├── integration/        # Integration test suite
│   └── eval/               # Evaluation config and evalsets
├── deploy_agent.sh         # Deployment script for the ADK Agent on Cloud Run
├── pyproject.toml          # Project metadata and dependencies
└── README.md               # Project documentation
```
