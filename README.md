# Volatility MLOps Platform

Production-style MLOps pipeline for market volatility forecasting with a neural time-series model, automated retraining, experiment tracking, and containerized API/UI delivery.

## Project Highlights

- End-to-end pipeline from market data ingestion to model-serving.
- Neural forecasting backend (GRU) optimized for fast retraining/inference.
- Experiment tracking and optional model registration via MLflow.
- Scheduled orchestration with GitHub Actions and Azure ML jobs.
- Dockerized FastAPI + web UI deployment on Azure Container Apps.
- Azure stack: Azure SQL, Azure ML, Blob Storage, ACR, Container Apps.

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
- **Operational Health Checks:** API health endpoint and preflight checks.

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
src/
  azure_sql_connect.py
  twelve_data_client.py
.github/workflows/
  azure-mlops-pipeline.yml
  azure-container-app-deploy.yml
azure/
  ml/
  sql/
frontend/
  index.html, asset.html, portfolio.html, result_*.html, app.js, style.css
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

## Security and Secrets

- `.env` and `.env.*` are ignored by Git.
- `.env.example` is template-only (no real credentials).
- Use GitHub Secrets for CI/CD environment values.

## Azure Setup

The `devel-Azure` branch includes a low-cost all-Azure MLOps path using Azure SQL, Azure ML jobs, Azure Blob Storage, Azure Container Registry, and Azure Container Apps.

See [docs/azure_mlops_setup.md](/Users/tayebi/Documents/Repositories/GitHub/volatility-mlops/docs/azure_mlops_setup.md).
