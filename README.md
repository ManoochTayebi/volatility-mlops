# Volatility MLOps Platform

Production-style MLOps platform for market volatility forecasting. The project ingests market data, stores it in Azure SQL, trains neural volatility models with Azure ML, tracks experiments with MLflow, publishes model artifacts to Azure Blob Storage, and serves predictions through a containerized FastAPI + web UI application on Azure Container Apps.

## Platform Dashboard

| Area | Status | Notes |
| --- | --- | --- |
| CI | Passing | Runs Pytest and builds the Docker image on `main`. |
| API/UI deployment | Passing | Builds and deploys the FastAPI + frontend container to Azure Container Apps. |
| Deployment smoke test | Passing | Validates the live `/api/health` endpoint after deployment. |
| Azure ML retraining | Blocked | Azure ML job starts correctly, but Azure SQL rejects the configured SQL login. |
| Model registry gate | Available | Optional RMSE threshold before MLflow model registration. |
| Artifact serving | Available | Latest model artifacts are expected in Azure Blob Storage. |

Current cloud blocker:

```text
Azure MLOps Pipeline -> Azure SQL preflight -> Login failed for user
```

Verify the GitHub secrets used by the Azure ML workflow:

```text
AZURE_SQL_SERVER
AZURE_SQL_DATABASE
AZURE_SQL_USERNAME
AZURE_SQL_PASSWORD
```

## Architecture

```text
Twelve Data API
   -> ingestion scripts
   -> Azure SQL Database
   -> Azure ML training job
   -> MLflow tracking + optional model registration
   -> Azure Blob Storage model artifacts
   -> Azure Container Apps
   -> FastAPI + frontend
```

## MLOps Capabilities

| Capability | Implementation |
| --- | --- |
| Source control | GitHub `main` branch with CI/CD workflows |
| Data source | Twelve Data OHLCV market data |
| Data store | Azure SQL Database |
| Training | PyTorch GRU volatility forecasting model |
| Experiment tracking | MLflow metrics, parameters, and artifacts |
| Orchestration | GitHub Actions and Azure ML jobs |
| Model artifacts | Azure Blob Storage |
| Serving | FastAPI API and static frontend |
| Deployment | Docker image pushed to ACR and deployed to Azure Container Apps |
| Validation | Pytest, preflight checks, live smoke test |
| Quality gate | Optional RMSE threshold before model registration |

## Repository Structure

```text
backend/
  app.py                  # FastAPI app and static frontend mounting
  compute.py              # API business logic
  predictor.py            # Inference engine
  nn_trainer.py           # GRU training pipeline

frontend/
  index.html
  asset.html
  portfolio.html
  result_*.html
  app.js
  style.css

scripts/
  ingest_market_data.py
  preflight_check.py
  retrain_with_mlflow.py
  run_daily_pipeline.py
  smoke_test_api.py

src/
  azure_sql_connect.py
  twelve_data_client.py

azure/
  ml/
  sql/

.github/workflows/
  ci.yml
  azure-mlops-pipeline.yml
  azure-container-app-deploy.yml

tests/
```

## Local Development

Create the environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a local `.env` from the template:

```bash
cp .env.example .env
```

Run tests:

```bash
python -m pytest -q
```

Run the API and frontend locally:

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Local endpoints:

```text
UI          http://localhost:8000
API root    http://localhost:8000/api
Health      http://localhost:8000/api/health
```

Run with Docker:

```bash
docker compose up --build
```

Docker endpoints:

```text
App/UI/API  http://localhost:8000
MLflow UI   http://localhost:5001
```

## Pipeline Workflows

### CI

Workflow:

```text
.github/workflows/ci.yml
```

Runs on:

```text
push to main
pull request
manual dispatch
```

Steps:

```text
checkout
install dependencies
run pytest
build Docker image
```

### Azure Container App Deploy

Workflow:

```text
.github/workflows/azure-container-app-deploy.yml
```

Responsibilities:

```text
login to Azure
build Docker image
push image to Azure Container Registry
deploy/update Azure Container App
attach runtime secrets
run live API smoke test
```

The smoke test calls:

```bash
python scripts/smoke_test_api.py --base-url "$APP_BASE_URL"
```

It validates:

```text
GET /api/health -> {"status": "ok", ...}
```

### Azure MLOps Pipeline

Workflow:

```text
.github/workflows/azure-mlops-pipeline.yml
```

Responsibilities:

```text
login to Azure
ensure Azure ML compute exists
submit Azure ML job
run data preflight
ingest market data
train volatility models
log metrics and artifacts
upload latest model artifacts to Blob Storage
refresh the serving app revision
```

This workflow is currently blocked by Azure SQL authentication. Azure login and Azure ML compute creation are working.

## Configuration

Required GitHub secrets:

```text
AZURE_CREDENTIALS
TWELVE_DATA_API_KEY
AZURE_SQL_SERVER
AZURE_SQL_DATABASE
AZURE_SQL_USERNAME
AZURE_SQL_PASSWORD
AZURE_STORAGE_CONNECTION_STRING
```

Common GitHub repository variables:

```text
AZURE_RESOURCE_GROUP
AZURE_LOCATION
AZURE_ML_WORKSPACE
AZURE_COMPUTE_NAME
AZURE_COMPUTE_SIZE
AZURE_COMPUTE_TIER
AZURE_ACR_NAME
AZURE_CONTAINER_APP
AZURE_CONTAINER_APP_ENV
AZURE_SQL_TABLE
AZURE_MODEL_ARTIFACTS_CONTAINER
AZURE_MODEL_ARTIFACTS_PREFIX
SYMBOLS
```

Recommended development defaults:

```text
AZURE_COMPUTE_SIZE=Standard_DS2_v2
AZURE_COMPUTE_TIER=dedicated
AZURE_MODEL_ARTIFACTS_CONTAINER=volatility-model-artifacts
AZURE_MODEL_ARTIFACTS_PREFIX=latest
AZURE_SQL_TABLE=dbo.daily_stock_prices
SYMBOLS=AAPL,GOOGL,MSFT
```

## Model Quality Gate

Model registration can be protected with an RMSE threshold:

```text
MLFLOW_REGISTER_MODELS=true
MODEL_MAX_RMSE=0.05
ENFORCE_MODEL_QUALITY_GATE=true
```

Behavior:

```text
RMSE <= MODEL_MAX_RMSE -> model registration allowed
RMSE > MODEL_MAX_RMSE  -> model registration blocked
ENFORCE_MODEL_QUALITY_GATE=true -> training job fails when the gate is not met
```

## Operational Notes

Cost-aware defaults are used where possible:

```text
Azure ML compute: min instances 0, max instances 1
Container App: min replicas 0, max replicas 1
Small development VM size: Standard_DS2_v2
```

Infrastructure resources should be managed intentionally:

```text
Use one resource group for the dev environment.
Use one Container Apps environment for the serving app.
Use one Log Analytics workspace for Container Apps monitoring.
Keep generated model artifacts in Blob Storage, not Git.
Keep credentials in GitHub Secrets or local .env files only.
```

## Security

- `.env` and `.env.*` are ignored by Git.
- `.env.example` is a template and must not contain real credentials.
- GitHub Secrets are used for CI/CD credentials.
- Azure SQL credentials are validated by the preflight step before ingestion/training.
- Model and data artifacts are externalized to Azure services.

## Azure Setup

The `main` branch contains a low-cost Azure path using:

```text
Azure SQL Database
Azure Machine Learning
Azure Blob Storage
Azure Container Registry
Azure Container Apps
Log Analytics
```

Detailed Azure setup notes are available in:

```text
docs/azure_mlops_setup.md
```
