# Google Cloud Platform Deployment Guide

## Smart Parking App - Cloud Run Deployment

This guide will help you deploy your Smart Parking App to Google Cloud Run using the free tier.

---

## Prerequisites

1. **Google Cloud Account** (Free tier includes $300 credit for 90 days)
   - Sign up at: https://cloud.google.com/free

2. **Gemini API Key** (Free tier available)
   - Get it from: https://makersuite.google.com/app/apikey

3. **Google Cloud CLI** (gcloud)
   - Install from: https://cloud.google.com/sdk/docs/install

---

## Step 1: Install Google Cloud CLI

### Windows:
```powershell
# Download and run the installer
# https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe
```

### Linux/Mac:
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### Verify Installation:
```bash
gcloud --version
```

---

## Step 2: Initialize and Authenticate

```bash
# Login to your Google account
gcloud auth login

# Create a new project (or use existing)
gcloud projects create smart-parking-app-123 --name="Smart Parking App"

# Set the project
gcloud config set project smart-parking-app-123

# Set default region
gcloud config set run/region us-central1
```

---

## Step 3: Enable Required APIs

```bash
# Enable Cloud Run, Container Registry, and Cloud Build
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

---

## Step 4: Deploy Using the Script (Recommended)

### On Linux/Mac:
```bash
# Make the script executable
chmod +x deploy-gcp.sh

# Run the deployment script
./deploy-gcp.sh
```

### On Windows (PowerShell):
```powershell
# Install Git Bash or WSL, then run:
bash deploy-gcp.sh
```

The script will:
- ✅ Check prerequisites
- ✅ Enable required APIs
- ✅ Build your Docker container
- ✅ Deploy to Cloud Run
- ✅ Set environment variables
- ✅ Provide the live URL

---

## Step 5: Manual Deployment (Alternative)

If you prefer manual deployment:

```bash
# Set environment variables
$GEMINI_API_KEY="your_gemini_api_key_here"
$FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Deploy to Cloud Run
gcloud run deploy smart-parking-app \
    --source . \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars="GEMINI_API_KEY=$GEMINI_API_KEY,FLASK_SECRET_KEY=$FLASK_SECRET_KEY" \
    --memory 512Mi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0
```

---

## Step 6: Verify Deployment

After deployment, you'll get a URL like:
```
https://smart-parking-app-xxxxx.run.app
```

Test the endpoints:
- **Homepage**: https://your-url.run.app/
- **API Health**: https://your-url.run.app/api/lots
- **Owner Dashboard**: https://your-url.run.app/owner
- **Customer View**: https://your-url.run.app/customer

---

## Managing Your Deployment

### View Logs:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=smart-parking-app" --limit 50
```

### Update Environment Variables:
```bash
gcloud run services update smart-parking-app \
    --region us-central1 \
    --set-env-vars="GEMINI_API_KEY=new_key"
```

### Redeploy (after code changes):
```bash
gcloud run deploy smart-parking-app --source .
```

### Delete Service:
```bash
gcloud run services delete smart-parking-app --region us-central1
```

---

## Free Tier Limits

**Cloud Run Free Tier (Always Free):**
- ✅ 2 million requests per month
- ✅ 360,000 vCPU-seconds
- ✅ 180,000 GiB-seconds of memory
- ✅ 1 GB network egress per month

**For your app, this means:**
- ~1000-2000 daily active users (free)
- Auto-scales to 0 when not in use (no cost)
- Pay only when requests come in

---

## Troubleshooting

### Issue: Build fails
```bash
# Check Docker is working locally
docker build -t test-image .
docker run -p 8080:8080 test-image
```

### Issue: Environment variables not set
```bash
# Check current env vars
gcloud run services describe smart-parking-app --region us-central1 --format="value(spec.template.spec.containers[0].env)"
```

### Issue: Out of memory
```bash
# Increase memory allocation
gcloud run services update smart-parking-app --memory 1Gi
```

---

## Cost Optimization Tips

1. **Set min-instances to 0** (already done in script)
   - Container stops when not in use
   - No charges during idle time

2. **Use SQLite** (default setup)
   - No database hosting costs
   - Data persists in container

3. **Monitor usage**:
   ```bash
   gcloud monitoring dashboards list
   ```

4. **Set billing alerts**:
   - Go to: https://console.cloud.google.com/billing
   - Set up budget alerts

---

## Next Steps

### Optional Upgrades (Still Free):

1. **Add Custom Domain** (if you have one):
   ```bash
   gcloud beta run domain-mappings create --service smart-parking-app --domain your-domain.com
   ```

2. **Enable Cloud Firestore** (real-time updates):
   - Better for multi-user scenarios
   - Free tier: 50K reads, 20K writes per day

3. **Add Cloud Storage** (for images/files):
   - Free tier: 5 GB storage

---

## Support

- **GCP Documentation**: https://cloud.google.com/run/docs
- **Gemini API Docs**: https://ai.google.dev/docs
- **Pricing Calculator**: https://cloud.google.com/products/calculator

---

## Quick Command Reference

```bash
# View all services
gcloud run services list

# Get service URL
gcloud run services describe smart-parking-app --format='value(status.url)'

# View recent logs
gcloud logging read "resource.type=cloud_run_revision" --limit 10

# Scale to specific instances
gcloud run services update smart-parking-app --max-instances 5

# Check billing
gcloud billing accounts list
```

---

**Ready to deploy? Run:**
```bash
./deploy-gcp.sh
```

**Questions?** Check the troubleshooting section or GCP documentation.
