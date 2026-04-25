# Volatility MLOps Platform

Production-style MLOps pipeline for market volatility forecasting with a neural time-series model, automated retraining, experiment tracking, and containerized API/UI delivery.

## Project Highlights

- End-to-end pipeline from market data ingestion to model-serving.
- Neural forecasting backend (GRU) optimized for fast retraining/inference.
- Experiment tracking and optional model registration via MLflow.
- Scheduled orchestration with GitHub Actions.
- Dockerized FastAPI + web UI deployment.
- Free-friendly stack: Supabase, GitHub Actions, MLflow local/file store.

## System Architecture

1. **Ingestion Layer**  
   Twelve Data OHLCV is ingested into Supabase.

2. **Data Sync Layer**  
   Optional CSV export from Supabase is available for debugging or local snapshots.

3. **Training Layer**  
   Realized volatility is computed from Supabase-backed market data and GRU models are retrained.

4. **Experiment Layer**  
   Parameters, metrics, and artifacts are logged in MLflow.

5. **Serving Layer**  
   FastAPI exposes prediction endpoints and serves the frontend.

## MLOps Capabilities

- **Versioned Codebase:** Git + GitHub workflows.
- **Data Lineage:** Supabase as source-of-truth for ingested market data.
- **Reproducible Runs:** environment-driven configs and pinned dependencies.
- **Automated Retraining:** scheduled and manual workflows in GitHub Actions.
- **Model Artifact Management:** persisted models in `backend/data/nn_models`.
- **Experiment Traceability:** MLflow metrics/artifacts per training run.
- **Operational Health Checks:** API health endpoint and preflight checks.

## Tech Stack

- **Data Source:** Twelve Data API  
- **Database:** Supabase (Postgres)  
- **ML Framework:** PyTorch (GRU)  
- **Experiment Tracking:** MLflow  
- **Orchestration/CI:** GitHub Actions  
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
  sync_market_data_from_supabase.py
  retrain_with_mlflow.py
  run_daily_pipeline.py
src/
  supabase_connect.py
  twelve_data_client.py
.github/workflows/
  daily-mlops-pipeline.yml
  manual-full-backfill.yml
SQL/
  supabase_schema.sql
frontend/
  index.html, asset.html, portfolio.html, result_*.html, app.js, style.css
```

## Quick Start

```bash
cp .env.example .env
# fill TWELVE_DATA_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the full local pipeline:

```bash
make preflight
make ingest-daily
make sync
make retrain
```

Training defaults to reading market data directly from Supabase:

- `MARKET_DATA_SOURCE=supabase`
- `SYNC_MARKET_CSV=false`

If you want local CSV snapshots as well, set:

```bash
SYNC_MARKET_CSV=true
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

### Auto-Published App Image

The daily GitHub Actions pipeline now builds and publishes an app image to GitHub Container Registry after retraining completes successfully. The image includes the refreshed `backend/data` artifacts produced during that run.

- Image: `ghcr.io/<owner>/<repo>-app:latest`
- Immutable tag: `ghcr.io/<owner>/<repo>-app:<git-sha>`

To run the published image on a Docker host:

```bash
docker compose -f docker-compose.deploy.yml up -d
```

Set `APP_IMAGE` if you want to pin a specific tag:

```bash
APP_IMAGE=ghcr.io/<owner>/<repo>-app:<git-sha> docker compose -f docker-compose.deploy.yml up -d
```

## Security and Secrets

- `.env` and `.env.*` are ignored by Git.
- `.env.example` is template-only (no real credentials).
- Use GitHub Secrets for CI/CD environment values.

## Supabase Setup

Execute the schema in:

```text
SQL/supabase_schema.sql
```

inside the Supabase SQL Editor.
