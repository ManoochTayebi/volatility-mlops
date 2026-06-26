# Volatility MLOps Platform

Production-style MLOps pipeline for market volatility forecasting with a neural time-series model, automated retraining, experiment tracking, and containerized API/UI delivery.

## Project Highlights

- End-to-end pipeline from market data ingestion to model-serving.
- Neural forecasting backend (GRU) optimized for fast retraining/inference.
- Experiment tracking and optional model registration via MLflow.
- Scheduled orchestration with GitHub Actions and Azure ML jobs.
- Dockerized FastAPI + web UI deployment on Azure Container Apps.
- CI checks with Pytest and Docker image build.
- Deployment smoke test against the live API health endpoint.
- Azure stack: Azure SQL, Azure ML, Blob Storage, ACR, Container Apps.

## Current Pipeline Status

Latest verified status on `main`:

```text
CI                         passing
Azure Container App Deploy passing
Azure MLOps Pipeline       blocked by Azure SQL login credentials
```

The Azure ML workflow logs in to Azure successfully, creates/uses the Azure ML compute target successfully, then fails during the SQL preflight step with an Azure SQL login error. Fix the GitHub repository secrets for Azure SQL, then rerun `Azure MLOps Pipeline`.

Most likely secrets to verify:

```text
AZURE_SQL_SERVER
AZURE_SQL_DATABASE
AZURE_SQL_USERNAME
AZURE_SQL_PASSWORD
```

## System Architecture

1. **Ingestion Layer**  
   Twelve Data OHLCV is ingested into Azure SQL Database.

2. **Training Layer**  
   Realized volatility is computed from Azure SQL-backed market data and GRU models are retrained.

3. **Experiment Layer**  
   Parameters, metrics, and artifacts are logged in MLflow/Azure ML.

4. **Serving Layer**  
   FastAPI exposes prediction endpoints and serves the frontend from Azure Container Apps.

## MLOps Capabilities

- **Versioned Codebase:** Git + GitHub workflows.
- **Data Lineage:** Azure SQL as source-of-truth for ingested market data.
- **Reproducible Runs:** environment-driven configs and pinned dependencies.
- **Automated Retraining:** scheduled and manual Azure ML jobs triggered by GitHub Actions.
- **Model Artifact Management:** generated model files are uploaded to Azure Blob Storage and are not committed to Git.
- **Experiment Traceability:** MLflow metrics/artifacts per training run.
- **Quality Gate:** optional RMSE threshold before MLflow model registration.
- **Operational Health Checks:** API health endpoint, preflight checks, and deployment smoke tests.

## Tech Stack

- **Data Source:** Twelve Data API  
- **Database:** Azure SQL Database  
- **ML Framework:** PyTorch (GRU)  
- **Experiment Tracking:** MLflow  
- **Orchestration/CI:** GitHub Actions + Azure ML Jobs  
- **API:** FastAPI  
- **Visualization/UI:** HTML/CSS/JavaScript + Plotly  
- **Containerization:** Docker + Docker Compose

## Repository Structure

```text
backend/
  app.py                  # FastAPI app + static frontend mounting
  compute.py              # API business logic
  predictor.py            # Inference engine
  nn_trainer.py           # Neural training pipeline (GRU)
scripts/
  ingest_market_data.py
  retrain_with_mlflow.py
  run_daily_pipeline.py
  smoke_test_api.py
src/
  azure_sql_connect.py
  twelve_data_client.py
.github/workflows/
  ci.yml
  azure-mlops-pipeline.yml
  azure-container-app-deploy.yml
azure/
  ml/
  sql/
frontend/
  index.html, asset.html, portfolio.html, result_*.html, app.js, style.css
tests/
```

## Quick Start

```bash
cp .env.example .env
# fill TWELVE_DATA_API_KEY and AZURE_SQL_* values

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the full local pipeline:

```bash
make preflight
make ingest-daily
make retrain
```

Training defaults to reading market data directly from Azure SQL:

- `MARKET_DATA_SOURCE=azure_sql`
- `AZURE_SQL_TABLE=dbo.daily_stock_prices`

## Tests and CI

Run tests locally:

```bash
python -m pytest -q
```

The `CI` workflow runs on push and pull requests:

```text
install dependencies
-> run pytest
-> build Docker image
```

## Run the Platform

### Local

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

- UI: `http://localhost:8000`
- API root: `http://localhost:8000/api`
- Health: `http://localhost:8000/api/health`

### Docker

```bash
docker compose up --build
```

- App/UI/API: `http://localhost:8000`
- MLflow UI: `http://localhost:5001`

### Azure Deployment

The Azure deployment workflow builds the Docker image, pushes it to Azure Container Registry, and serves it through Azure Container Apps. The Azure ML pipeline writes the latest trained model artifacts to Azure Blob Storage, then refreshes the Container App revision so the API/UI can load the newest artifacts at startup.

Use `Azure Container App Deploy` once to publish the UI/API. Use `Azure MLOps Pipeline` manually or on schedule for ingestion, retraining, MLflow tracking, artifact upload, and serving refresh.

After deployment, the workflow calls:

```bash
python scripts/smoke_test_api.py --base-url "$APP_BASE_URL"
```

The smoke test validates `/api/health` on the live app. The script retries during startup so new Azure Container App revisions have time to become reachable.

## Azure Resource Cleanup

Azure Container Apps may create a Log Analytics workspace for monitoring. During repeated deployment experiments, duplicate workspaces with names like this can appear:

```text
workspace-rgvolatilitymlopsdevRT4
workspace-rgvolatilitymlopsdevIDPZ
workspace-rgvolatilitymlopsdevinqb
```

You only need the Log Analytics workspace that is connected to the active Container Apps environment.

Before deleting any duplicate workspace:

1. Open the Container Apps environment, for example `cae-volatility-mlops-dev`.
2. Check which Log Analytics workspace is attached to it.
3. Keep the attached workspace.
4. Delete only the unused duplicate `workspace-rgvolatility...` resources.

For a cleaner long-term setup, create one fixed Log Analytics workspace, such as `law-volatility-mlops-dev`, and configure the Container Apps environment to use that workspace instead of relying on Azure-generated names.

## Quality Gate

Model registration can be protected with an RMSE threshold:

```text
MLFLOW_REGISTER_MODELS=true
MODEL_MAX_RMSE=0.05
ENFORCE_MODEL_QUALITY_GATE=true
```

If a trained model has RMSE above `MODEL_MAX_RMSE`, registration is blocked. If `ENFORCE_MODEL_QUALITY_GATE=true`, the retraining job fails instead of only skipping registration.

## Security and Secrets

- `.env` and `.env.*` are ignored by Git.
- `.env.example` is template-only (no real credentials).
- Use GitHub Secrets for CI/CD environment values.

Required GitHub secrets for the Azure workflows:

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

## Azure Setup

The `main` branch includes a low-cost all-Azure MLOps path using Azure SQL, Azure ML jobs, Azure Blob Storage, Azure Container Registry, and Azure Container Apps.

See `docs/azure_mlops_setup.md`.
