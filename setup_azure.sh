#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# --- USER CONFIGURATION ---
# !! Change these values to your own unique names !!
# Note: Names for ACR, Key Vault, and Postgres must be globally unique across Azure.

# Resource Group and Location
RESOURCE_GROUP="smartparking-rg"
LOCATION="eastus" # e.g., "eastus", "westeurope"

# Azure Container Registry (ACR)
ACR_NAME="smartparkingacr$(openssl rand -hex 4)" # Appending a random string to help ensure uniqueness

# Azure Key Vault
KEY_VAULT_NAME="smartparking-kv-$(openssl rand -hex 4)"

# Azure PostgreSQL Database
POSTGRES_SERVER_NAME="smartparking-db-$(openssl rand -hex 4)"
DATABASE_NAME="parking_db"
POSTGRES_ADMIN_USER="db_admin"

# Azure Container App
CONTAINER_APP_ENV="smartparking-env"
CONTAINER_APP_NAME="smartparking-app"

# --- SCRIPT ---

echo "--- Starting Azure Resource Provisioning ---"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "ACR Name: $ACR_NAME"
echo "Key Vault Name: $KEY_VAULT_NAME"
echo "Postgres Server: $POSTGRES_SERVER_NAME"
echo "Container App: $CONTAINER_APP_NAME"
echo "-------------------------------------------"

# 1. Create Resource Group
echo "Creating Resource Group: $RESOURCE_GROUP..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" -o table

# 2. Create Azure Container Registry (ACR)
echo "Creating ACR: $ACR_NAME..."
az acr create --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true -o table

# 3. Create Azure Database for PostgreSQL (Flexible Server)
echo "Creating PostgreSQL Server: $POSTGRES_SERVER_NAME..."
echo "You will be prompted to create a password for the database. REMEMBER THIS PASSWORD."
az postgres flexible-server create --resource-group "$RESOURCE_GROUP" \
  --name "$POSTGRES_SERVER_NAME" \
  --location "$LOCATION" \
  --database-name "$DATABASE_NAME" \
  --admin-user "$POSTGRES_ADMIN_USER" \
  --version 14 \
  --sku-name Standard_B1ms \
  --public-access "0.0.0.0" # Allows access from any IP. For production, restrict this.
  
echo "Configuring Postgres firewall to allow access from Azure services..."
az postgres flexible-server firewall-rule create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$POSTGRES_SERVER_NAME" \
  --rule-name "AllowAzureServices" \
  --start-ip-address "0.0.0.0" \
  --end-ip-address "0.0.0.0"

# 4. Create Azure Key Vault
echo "Creating Key Vault: $KEY_VAULT_NAME..."
az keyvault create --resource-group "$RESOURCE_GROUP" \
  --name "$KEY_VAULT_NAME" \
  --location "$LOCATION" \
  --sku standard -o table

# 5. Create Container App Environment
echo "Creating Container App Environment: $CONTAINER_APP_ENV..."
az containerapp env create --resource-group "$RESOURCE_GROUP" \
  --name "$CONTAINER_APP_ENV" \
  --location "$LOCATION" -o table

# 6. Create the Container App (initially with a placeholder image)
echo "Creating Container App: $CONTAINER_APP_NAME..."
APP_IDENTITY=$(az containerapp create --resource-group "$RESOURCE_GROUP" \
  --name "$CONTAINER_APP_NAME" \
  --environment "$CONTAINER_APP_ENV" \
  --image mcr.microsoft.com/k8s/aci/helloworld:latest \
  --target-port 8080 \
  --ingress 'external' \
  --registry-server "$ACR_NAME.azurecr.io" \
  --system-assigned \
  --query "identity.principalId" -o tsv)

echo "Container App created with Managed Identity Principal ID: $APP_IDENTITY"

# 7. Grant Container App's Managed Identity access to Key Vault
echo "Granting Container App access to Key Vault..."
az keyvault set-policy --resource-group "$RESOURCE_GROUP" \
  --name "$KEY_VAULT_NAME" \
  --object-id "$APP_IDENTITY" \
  --secret-permissions get list

# 8. Grant Container App's Managed Identity access to ACR (Pull rights)
echo "Granting Container App access to ACR..."
az role assignment create \
  --assignee "$APP_IDENTITY" \
  --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ContainerRegistry/registries/$ACR_NAME" \
  --role "AcrPull"

# 9. Create Service Principal for GitHub Actions
echo "Creating Service Principal for GitHub Actions..."
SP_JSON=$(az ad sp create-for-rbac --name "github-actions-${RESOURCE_GROUP}" \
  --role "Contributor" \
  --scopes "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP" \
  --sdk-auth)

# --- FINAL INSTRUCTIONS ---
echo "---"
echo "✅ Azure setup is complete!"
echo "---"

echo "🔴 ACTION REQUIRED: Add GitHub Secret"
echo "1. Go to your GitHub repo settings > Secrets and variables > Actions."
echo "2. Create a new secret named: AZURE_CREDENTIALS"
echo "3. Paste the ENTIRE JSON block below into the secret's value:"
echo ""
echo "$SP_JSON"
echo ""
echo "---"

echo "🔴 ACTION REQUIRED: Set Your Secrets in Key Vault"
echo "Please run the following commands in your terminal."
echo "REPLACE '<YourPassword>', '<YourGeminiKey>', etc. with your actual secrets."
echo ""
echo "# 1. Construct your full DATABASE_URL (replace <YourPassword> with the password you created)"
POSTGRES_HOST="$POSTGRES_SERVER_NAME.postgres.database.azure.com"
DATABASE_URL="postgres://$POSTGRES_ADMIN_USER:<YourPassword>@$POSTGRES_HOST/$DATABASE_NAME?sslmode=require"
echo "Example DATABASE_URL: $DATABASE_URL"
echo ""
echo "# 2. Set the secrets in Key Vault (use the URL from above)"
echo "az keyvault secret set --vault-name \"$KEY_VAULT_NAME\" --name \"DATABASE-URL\" --value \"<YourDatabaseURL>\""
echo "az keyvault secret set --vault-name \"$KEY_VAULT_NAME\" --name \"GEMINI-API-KEY\" --value \"<YourGeminiKey>\""
echo "az keyvault secret set --vault-name \"$KEY_VAULT_NAME\" --name \"FLASK-SECRET-KEY\" --value \"$(openssl rand -hex 32)\""
echo ""
echo "---"
echo "Once you have set the GitHub secret and Key Vault secrets, push your code to the 'main' branch to trigger the deployment."