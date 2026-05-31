#!/usr/bin/env bash
set -euo pipefail

: "${AZURE_LOCATION:=francecentral}"
: "${AZURE_RESOURCE_GROUP:=rg-volatility-mlops-dev}"
: "${AZURE_ML_WORKSPACE:=mlw-volatility-mlops-dev}"
: "${AZURE_CONTAINER_APP_ENV:=cae-volatility-mlops-dev}"
: "${AZURE_CONTAINER_APP:=volatility-mlops-app}"
: "${AZURE_ACR_NAME:?Set AZURE_ACR_NAME to a globally unique ACR name, for example volmlops$RANDOM}"
: "${AZURE_STORAGE_ACCOUNT:?Set AZURE_STORAGE_ACCOUNT to a globally unique storage account name}"
: "${AZURE_MODEL_ARTIFACTS_CONTAINER:=volatility-model-artifacts}"
: "${AZURE_COMPUTE_NAME:=volatility-cpu-lowcost}"
: "${AZURE_COMPUTE_SIZE:=Standard_DS2_v2}"
: "${AZURE_SQL_SERVER_NAME:?Set AZURE_SQL_SERVER_NAME to a globally unique SQL server name}"
: "${AZURE_SQL_DATABASE:=volatilitydb}"
: "${AZURE_SQL_ADMIN_USER:=voladmin}"
: "${AZURE_SQL_ADMIN_PASSWORD:?Set AZURE_SQL_ADMIN_PASSWORD to a strong password}"

az group create \
  --name "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION"

az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.MachineLearningServices

echo "Waiting for required Azure resource providers to finish registration..."
az provider wait --namespace Microsoft.App --registered
az provider wait --namespace Microsoft.OperationalInsights --registered
az provider wait --namespace Microsoft.MachineLearningServices --registered

az storage account create \
  --name "$AZURE_STORAGE_ACCOUNT" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --min-tls-version TLS1_2

AZURE_STORAGE_CONNECTION_STRING="$(az storage account show-connection-string \
  --name "$AZURE_STORAGE_ACCOUNT" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --query connectionString \
  -o tsv)"

az storage container create \
  --name "$AZURE_MODEL_ARTIFACTS_CONTAINER" \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING"

az sql server create \
  --name "$AZURE_SQL_SERVER_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --admin-user "$AZURE_SQL_ADMIN_USER" \
  --admin-password "$AZURE_SQL_ADMIN_PASSWORD"

az sql server firewall-rule create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --server "$AZURE_SQL_SERVER_NAME" \
  --name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0

az sql db create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --server "$AZURE_SQL_SERVER_NAME" \
  --name "$AZURE_SQL_DATABASE" \
  --service-objective Basic \
  --backup-storage-redundancy Local

az acr create \
  --name "$AZURE_ACR_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --sku Basic \
  --admin-enabled true

az ml workspace create \
  --name "$AZURE_ML_WORKSPACE" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION"

az ml compute create \
  --name "$AZURE_COMPUTE_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$AZURE_ML_WORKSPACE" \
  --type amlcompute \
  --size "$AZURE_COMPUTE_SIZE" \
  --min-instances 0 \
  --max-instances 1 \
  --idle-time-before-scale-down 120 \
  --tier low_priority

az containerapp env create \
  --name "$AZURE_CONTAINER_APP_ENV" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION"

echo "Azure resources created."
echo "Add the printed/storage secrets to GitHub Actions before running the workflows."
echo "AZURE_STORAGE_CONNECTION_STRING=$AZURE_STORAGE_CONNECTION_STRING"
echo "AZURE_SQL_SERVER=${AZURE_SQL_SERVER_NAME}.database.windows.net"
echo "AZURE_SQL_DATABASE=$AZURE_SQL_DATABASE"
echo "AZURE_SQL_USERNAME=$AZURE_SQL_ADMIN_USER"
