#!/bin/bash

# Smart Parking App - Google Cloud Run Deployment Script
# This script automates the deployment to Google Cloud Run

set -e  # Exit on any error

echo "=========================================="
echo "Smart Parking App - GCP Deployment"
echo "=========================================="
echo ""

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-smart-parking-app}"
GEMINI_API_KEY="${GEMINI_API_KEY:-}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "❌ Error: Not authenticated with gcloud"
    echo "Please run: gcloud auth login"
    exit 1
fi

# Get or set project ID
if [ -z "$PROJECT_ID" ]; then
    echo "📋 Available GCP Projects:"
    gcloud projects list --format="table(projectId,name)"
    echo ""
    read -p "Enter your GCP Project ID: " PROJECT_ID
fi

# Set the project
echo "🔧 Setting GCP project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔌 Enabling required GCP APIs..."
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Get Gemini API key
if [ -z "$GEMINI_API_KEY" ]; then
    echo ""
    echo "🔑 Gemini API Key Required"
    echo "Get your key from: https://makersuite.google.com/app/apikey"
    read -p "Enter your Gemini API Key: " GEMINI_API_KEY
fi

# Generate a secure Flask secret key
FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Build and deploy to Cloud Run
echo ""
echo "🏗️  Building and deploying to Cloud Run..."
echo "   Service: $SERVICE_NAME"
echo "   Region: $REGION"
echo ""

gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars="GEMINI_API_KEY=$GEMINI_API_KEY,FLASK_SECRET_KEY=$FLASK_SECRET_KEY" \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')

echo ""
echo "=========================================="
echo "✅ Deployment Successful!"
echo "=========================================="
echo ""
echo "🌐 Your app is live at:"
echo "   $SERVICE_URL"
echo ""
echo "📊 View logs:"
echo "   gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\" --limit 50"
echo ""
echo "🔧 Update environment variables:"
echo "   gcloud run services update $SERVICE_NAME --region $REGION --set-env-vars=\"KEY=VALUE\""
echo ""
echo "=========================================="
