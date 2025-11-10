#!/bin/bash
# Azure Setup with Managed Identity (Federated Credentials)
# This script sets up everything needed for secure, keyless Azure deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================="
echo "🔐 Azure Secure Deployment Setup"
echo "   (Federated Credentials - No Keys!)"
echo "==========================================${NC}"
echo ""

# Configuration
RESOURCE_GROUP="smart-parking-rg"
LOCATION="eastus"
APP_NAME="smart-parking-app"
APP_SERVICE_PLAN="smart-parking-plan"
GITHUB_REPO="DefinitelyNotABot-del/smart-parking-app"

# Get current subscription ID
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "   Subscription ID: $SUBSCRIPTION_ID"
echo "   Tenant ID: $TENANT_ID"
echo "   Location: $LOCATION"
echo "   App Name: $APP_NAME"
echo ""

# Step 1: Create Resource Group
echo -e "${YELLOW}Step 1: Creating Resource Group...${NC}"
if az group exists --name $RESOURCE_GROUP | grep -q "false"; then
    az group create --name $RESOURCE_GROUP --location $LOCATION
    echo -e "${GREEN}✅ Resource group created${NC}"
else
    echo -e "${GREEN}✅ Resource group already exists${NC}"
fi
echo ""

# Step 2: Create App Service Plan (Free tier)
echo -e "${YELLOW}Step 2: Creating App Service Plan (Free tier)...${NC}"
if ! az appservice plan show --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP &>/dev/null; then
    az appservice plan create \
        --name $APP_SERVICE_PLAN \
        --resource-group $RESOURCE_GROUP \
        --sku F1 \
        --is-linux
    echo -e "${GREEN}✅ App Service Plan created (Free tier)${NC}"
else
    echo -e "${GREEN}✅ App Service Plan already exists${NC}"
fi
echo ""

# Step 3: Create Web App
echo -e "${YELLOW}Step 3: Creating Web App...${NC}"
if ! az webapp show --name $APP_NAME --resource-group $RESOURCE_GROUP &>/dev/null; then
    az webapp create \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --plan $APP_SERVICE_PLAN \
        --runtime "PYTHON:3.11"
    echo -e "${GREEN}✅ Web App created${NC}"
else
    echo -e "${GREEN}✅ Web App already exists${NC}"
fi
echo ""

# Step 4: Enable System-Assigned Managed Identity
echo -e "${YELLOW}Step 4: Enabling Managed Identity...${NC}"
az webapp identity assign \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP
echo -e "${GREEN}✅ Managed Identity enabled${NC}"
echo ""

# Step 5: Create App Registration for GitHub Actions
echo -e "${YELLOW}Step 5: Creating App Registration for GitHub Actions...${NC}"

# Create app registration
APP_ID=$(az ad app create \
    --display-name "github-actions-${APP_NAME}" \
    --query appId -o tsv)

echo "   App ID: $APP_ID"

# Create service principal
SP_OBJECT_ID=$(az ad sp create --id $APP_ID --query id -o tsv)
echo "   Service Principal created"

# Wait for propagation
echo "   Waiting for Azure AD propagation..."
sleep 10

# Assign Contributor role to subscription
az role assignment create \
    --assignee $APP_ID \
    --role Contributor \
    --scope /subscriptions/$SUBSCRIPTION_ID

echo -e "${GREEN}✅ App Registration created and permissions assigned${NC}"
echo ""

# Step 6: Configure Federated Credentials
echo -e "${YELLOW}Step 6: Setting up Federated Credentials (Keyless!)...${NC}"

# Create federated credential for main branch
az ad app federated-credential create \
    --id $APP_ID \
    --parameters "{
        \"name\": \"github-federated-credential\",
        \"issuer\": \"https://token.actions.githubusercontent.com\",
        \"subject\": \"repo:${GITHUB_REPO}:ref:refs/heads/main\",
        \"audiences\": [\"api://AzureADTokenExchange\"]
    }"

echo -e "${GREEN}✅ Federated Credentials configured${NC}"
echo "   GitHub Actions can now authenticate without any stored secrets!"
echo ""

# Step 7: Configure App Settings
echo -e "${YELLOW}Step 7: Configuring App Settings...${NC}"
az webapp config appsettings set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        SCM_DO_BUILD_DURING_DEPLOYMENT=true \
        WEBSITES_PORT=8000 \
        ENABLE_ORYX_BUILD=true

echo -e "${GREEN}✅ App Settings configured${NC}"
echo ""

# Summary
echo -e "${GREEN}=========================================="
echo "✅ Azure Setup Complete!"
echo "==========================================${NC}"
echo ""
echo -e "${YELLOW}📋 Add these secrets to your GitHub repository:${NC}"
echo "   Go to: https://github.com/${GITHUB_REPO}/settings/secrets/actions"
echo ""
echo "   Required secrets (3):"
echo ""
echo "   1️⃣  AZURE_CLIENT_ID"
echo "       $APP_ID"
echo ""
echo "   2️⃣  AZURE_TENANT_ID"
echo "       $TENANT_ID"
echo ""
echo "   3️⃣  AZURE_SUBSCRIPTION_ID"
echo "       $SUBSCRIPTION_ID"
echo ""
echo "   4️⃣  GEMINI_API_KEY"
echo "       (Your Gemini API key)"
echo ""
echo "   5️⃣  FLASK_SECRET_KEY"
echo "       (Generate with: python -c 'import secrets; print(secrets.token_hex(32))')"
echo ""
echo -e "${GREEN}🔒 Security Features:${NC}"
echo "   ✅ Federated Credentials (OIDC) - No service principal keys!"
echo "   ✅ Managed Identity for Azure resources"
echo "   ✅ Secrets stored only in GitHub (encrypted)"
echo "   ✅ Automatic credential rotation"
echo ""
echo -e "${YELLOW}💰 Cost Estimate:${NC}"
echo "   Free tier (F1): $0/month"
echo "   Basic tier (B1): ~$13/month (if you upgrade)"
echo ""
echo -e "${YELLOW}🚀 Next Steps:${NC}"
echo "   1. Add the secrets to GitHub (see above)"
echo "   2. Push code to main branch"
echo "   3. GitHub Actions will deploy automatically"
echo "   4. Access your app at: https://${APP_NAME}.azurewebsites.net"
echo ""
echo "=========================================="
