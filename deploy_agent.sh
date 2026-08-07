#!/usr/bin/env bash
set -e

# Configuration defaults
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE_NAME="bq-analytics-agent"
REPOSITORY_NAME="agent-repo"
IMAGE_NAME="bq-analytics-agent"
TAG="latest"
TOOLBOX_URL="${TOOLBOX_SERVER_URL:-}"

if [ -z "$PROJECT_ID" ]; then
  echo "Error: GOOGLE_CLOUD_PROJECT is not set and no active gcloud project found."
  exit 1
fi

echo "========================================================"
echo " Deploying ADK BigQuery Agent to Cloud Run"
echo " Project:     $PROJECT_ID"
echo " Region:      $REGION"
echo " Service:     $SERVICE_NAME"
echo " Toolbox URL: ${TOOLBOX_URL:-Not provided (using fallback BQ tool)}"
echo "========================================================"

# Enable required GCP APIs
echo "--> Enabling GCP Services..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  --project="$PROJECT_ID"

# Ensure Artifact Registry repository exists
echo "--> Ensuring Artifact Registry repository exists..."
if ! gcloud artifacts repositories describe "$REPOSITORY_NAME" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPOSITORY_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Repository for ADK Agent containers" \
    --project="$PROJECT_ID"
fi

IMAGE_URI="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY_NAME/$IMAGE_NAME:$TAG"

# Build image using Cloud Build
echo "--> Building container image via Cloud Build..."
gcloud builds submit . \
  --tag="$IMAGE_URI" \
  --project="$PROJECT_ID"

# Deploy to Cloud Run
echo "--> Deploying to Cloud Run..."
ENV_VARS="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=global,BQ_ANALYTICS_DATASET_ID=agent_analytics"
if [ -n "$TOOLBOX_URL" ]; then
  ENV_VARS="$ENV_VARS,TOOLBOX_SERVER_URL=$TOOLBOX_URL"
fi

gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE_URI" \
  --platform=managed \
  --region="$REGION" \
  --set-env-vars="$ENV_VARS" \
  --allow-unauthenticated \
  --project="$PROJECT_ID"

AGENT_URL=$(gcloud run services describe "$SERVICE_NAME" --platform=managed --region="$REGION" --project="$PROJECT_ID" --format='value(status.url)')

echo ""
echo "========================================================"
echo " SUCCESS! ADK BigQuery Agent deployed to Cloud Run:"
echo " Service URL: $AGENT_URL"
echo "========================================================"
