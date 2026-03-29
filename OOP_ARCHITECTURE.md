# OOP Architecture Documentation

## Overview

The project uses a modular OOP backend for volatility forecasting with a **neural-only model** (GRU), separated into data processing, training, inference, and API orchestration.

## Core Components

### 1. Dataset Processing (`backend/dataset.py`)

- `DatasetProcessor`: loads market data, computes log returns and realized volatility, creates sequences, and handles train/test split.
- `DataConfig`: controls sequence window, split ratio, and rolling window.

### 2. Model Training (`backend/nn_trainer.py`)

- `TrainingConfig`: controls model and training hyperparameters.
- `VolatilityGRU` (aliased as `VolatilityModel`): compact recurrent model for faster training/inference.
- `NNTrainer`: trains/fine-tunes models, computes metrics (`mse`, `rmse`, `mae`), and saves model artifacts.

### 3. Inference (`backend/predictor.py`)

- `VolatilityPredictor`: loads trained models and volatility history, then performs multi-step forecasting iteratively.

### 4. API (`backend/compute.py`, `backend/app.py`)

- `compute.py`: business logic for asset and portfolio volatility outputs.
- `app.py`: FastAPI routes:
  - `/api`
  - `/api/asset_volatility`
  - `/api/portfolio_volatility`
  - `/api/health`

## Design Principles

1. Single responsibility per module.
2. Config-driven model/training behavior.
3. Backward-compatible interfaces where possible.
4. Faster training path through a compact neural architecture.

## Notes

- Previous GARCH/hybrid logic has been removed from runtime backend flow.
- Model artifacts are saved to `backend/data/nn_models`.
- Realized volatility artifacts are saved to `backend/data/saved_volatilities`.
