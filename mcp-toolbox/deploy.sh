#!/usr/bin/env bash
set -e

# Configuration defaults
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE_NAME="mcp-bigquery-toolbox"
REPOSITORY_NAME="mcp-toolbox-repo"
IMAGE_NAME="mcp-bigquery-toolbox"
TAG="latest"

if [ -z "$PROJECT_ID" ]; then
  echo "Error: GOOGLE_CLOUD_PROJECT is not set and no active gcloud project found."
  exit 1
fi

echo "========================================================"
echo " Deploying MCP Toolbox for BigQuery to Cloud Run"
echo " Project: $PROJECT_ID"
echo " Region:  $REGION"
echo " Service: $SERVICE_NAME"
echo "========================================================"

# Enable required Google Cloud APIs
echo "--> Enabling GCP Services..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  bigquery.googleapis.com \
  --project="$PROJECT_ID"

# Create Artifact Registry repository if it doesn't exist
echo "--> Ensuring Artifact Registry repository exists..."
if ! gcloud artifacts repositories describe "$REPOSITORY_NAME" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPOSITORY_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Repository for MCP Toolbox containers" \
    --project="$PROJECT_ID"
fi

IMAGE_URI="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY_NAME/$IMAGE_NAME:$TAG"

# Build image using Cloud Build
echo "--> Building container image via Cloud Build..."
gcloud builds submit . \
  --tag="$IMAGE_URI" \
  --project="$PROJECT_ID"

# Create dedicated service account if needed
SA_NAME="mcp-toolbox-sa"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "--> Creating Service Account $SA_NAME..."
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name="MCP Toolbox BigQuery Service Account" \
    --project="$PROJECT_ID"
fi

# Grant BigQuery roles to the Service Account
echo "--> Granting BigQuery permissions to Service Account..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/bigquery.user" \
  --condition=none >/dev/null 2>&1 || true

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/bigquery.dataViewer" \
  --condition=none >/dev/null 2>&1 || true

# Deploy to Cloud Run
echo "--> Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE_URI" \
  --platform=managed \
  --region="$REGION" \
  --service-account="$SA_EMAIL" \
  --set-env-vars="BIGQUERY_PROJECT_ID=$PROJECT_ID" \
  --allow-unauthenticated \
  --project="$PROJECT_ID"

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --platform=managed --region="$REGION" --project="$PROJECT_ID" --format='value(status.url)')

echo ""
echo "========================================================"
echo " SUCCESS! MCP Toolbox deployed to Cloud Run:"
echo " Service URL: $SERVICE_URL"
echo " Set this in your ADK Agent environment:"
echo "   export TOOLBOX_SERVER_URL=\"$SERVICE_URL\""
echo "========================================================"
