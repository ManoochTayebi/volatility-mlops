# Azure MLOps Setup

This branch is configured for an all-Azure MLOps deployment:

- Azure SQL Database stores market OHLCV data.
- Azure Machine Learning runs ingestion, retraining, and MLflow experiment tracking.
- Azure Blob Storage stores the latest trained model artifacts.
- Azure Container Registry stores the FastAPI/UI Docker image.
- Azure Container Apps serves the UI/API with scale-to-zero.

Cloud Shell is the terminal inside the Azure Portal website. Open it from the `>_` icon in the top navigation bar at `https://portal.azure.com` and choose **Bash**.

## 1. Create Azure Resources

In Azure Cloud Shell:

```bash
git clone https://github.com/ManoochTayebi/volatility-mlops.git
cd volatility-mlops
git checkout devel-Azure

az extension add --name ml --upgrade
az extension add --name containerapp --upgrade

export AZURE_LOCATION=francecentral
export AZURE_RESOURCE_GROUP=rg-volatility-mlops-dev
export AZURE_ML_WORKSPACE=mlw-volatility-mlops-dev
export AZURE_CONTAINER_APP_ENV=cae-volatility-mlops-dev
export AZURE_CONTAINER_APP=volatility-mlops-app
export AZURE_ACR_NAME=<globally-unique-acr-name>
export AZURE_STORAGE_ACCOUNT=<globally-unique-storage-name>
export AZURE_SQL_SERVER_NAME=<globally-unique-sql-server-name>
export AZURE_SQL_DATABASE=volatilitydb
export AZURE_SQL_ADMIN_USER=voladmin
export AZURE_SQL_ADMIN_PASSWORD='<strong-password>'
export AZURE_COMPUTE_TIER=dedicated

bash azure/setup_low_cost_resources.sh
```

The script creates:

- resource group
- storage account and Blob container
- Azure SQL server and Basic database
- Azure Container Registry Basic
- Azure ML workspace
- Azure ML CPU compute with min instances `0`
- Azure Container Apps environment

Keep the printed Azure SQL values for GitHub secrets. The storage connection string is intentionally hidden in the setup output; retrieve it only when adding the GitHub secret:

```bash
az storage account show-connection-string \
  --name "$AZURE_STORAGE_ACCOUNT" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --query connectionString \
  -o tsv
```

If a storage connection string is pasted into chat, logs, or any public place, rotate the storage key before using it.

## 2. Create GitHub Azure Credentials

In Cloud Shell:

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

az ad sp create-for-rbac \
  --name sp-volatility-mlops-github \
  --role contributor \
  --scopes /subscriptions/$SUBSCRIPTION_ID \
  --sdk-auth
```

Store the JSON output as this GitHub secret:

- `AZURE_CREDENTIALS`

## 3. Configure GitHub Secrets

In GitHub:

`Settings -> Secrets and variables -> Actions -> Secrets`

Add:

- `AZURE_CREDENTIALS`
- `AZURE_STORAGE_CONNECTION_STRING` from `az storage account show-connection-string`
- `AZURE_SQL_SERVER`
- `AZURE_SQL_DATABASE`
- `AZURE_SQL_USERNAME`
- `AZURE_SQL_PASSWORD`
- `TWELVE_DATA_API_KEY`

## 4. Configure GitHub Variables

In GitHub:

`Settings -> Secrets and variables -> Actions -> Variables`

Add:

- `AZURE_RESOURCE_GROUP=rg-volatility-mlops-dev`
- `AZURE_LOCATION=francecentral`
- `AZURE_ML_WORKSPACE=mlw-volatility-mlops-dev`
- `AZURE_COMPUTE_NAME=volatility-cpu-lowcost`
- `AZURE_COMPUTE_SIZE=Standard_DS2_v2`
- `AZURE_COMPUTE_TIER=dedicated`
- `AZURE_ACR_NAME=<your-acr-name>`
- `AZURE_CONTAINER_APP_ENV=cae-volatility-mlops-dev`
- `AZURE_CONTAINER_APP=volatility-mlops-app`
- `AZURE_SQL_TABLE=dbo.daily_stock_prices`
- `AZURE_MODEL_ARTIFACTS_CONTAINER=volatility-model-artifacts`
- `AZURE_MODEL_ARTIFACTS_PREFIX=latest`
- `SYMBOLS=AAPL,GOOGL,MSFT`

## 5. Run The Workflows

Run from GitHub Actions:

1. `Azure Container App Deploy`
2. `Azure MLOps Pipeline`

The first workflow publishes and deploys the UI/API container. The second workflow runs Azure ML ingestion/retraining, logs the experiment with MLflow in Azure ML, uploads fresh model artifacts to Blob Storage, and refreshes the Container App revision so serving picks up the latest artifacts.

To print the deployed UI/API URL from Cloud Shell:

```bash
az containerapp show \
  --name "$AZURE_CONTAINER_APP" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn \
  -o tsv
```

## Cost Controls

- Set an Azure budget alert at 25, 50, and 100 USD.
- Keep Azure ML compute min instances at `0`.
- Keep Container Apps min replicas at `0`.
- Use `dedicated` compute if your subscription has dedicated quota. Switch `AZURE_COMPUTE_TIER` to `low_priority` only after low-priority quota is available.
- Avoid AKS and Azure ML managed online endpoints for this project.
- Delete unused old images and artifact blobs if storage grows.
