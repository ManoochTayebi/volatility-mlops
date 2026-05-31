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

wait_for_provider() {
  local namespace="$1"
  local state=""
  local attempts=0

  while [ "$attempts" -lt 60 ]; do
    state="$(az provider show --namespace "$namespace" --query registrationState -o tsv 2>/dev/null || true)"
    echo "$namespace registration state: ${state:-unknown}"
    if [ "$state" = "Registered" ]; then
      return 0
    fi
    attempts=$((attempts + 1))
    sleep 10
  done

  echo "Timed out waiting for $namespace to register" >&2
  return 1
}

echo "Active Azure account:"
az account show --query "{name:name, id:id, state:state, tenantId:tenantId}" -o table

az group create \
  --name "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION"

az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.MachineLearningServices
az provider register --namespace Microsoft.Sql
az provider register --namespace Microsoft.Storage

echo "Waiting for required Azure resource providers to finish registration..."
wait_for_provider Microsoft.App
wait_for_provider Microsoft.ContainerRegistry
wait_for_provider Microsoft.OperationalInsights
wait_for_provider Microsoft.MachineLearningServices
wait_for_provider Microsoft.Sql
wait_for_provider Microsoft.Storage

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
