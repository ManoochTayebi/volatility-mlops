# Market Forecasting Notebooks

This folder contains two notebook workflows for directional forecasting and price forecasting:

- `single_asset_forecasting.ipynb`
- `multi_asset_forecasting.ipynb`

The notebooks compare two model families for each horizon:

- Technical forecast: a tree-based regressor trained on technical indicators.
- Deep forecast: a PyTorch transformer trained on rolling sequences of engineered features.

If a notebook kernel does not have `torch`, the package import now still works, and the notebook includes a dependency-check cell that shows the active Python executable. Use the repository `.venv` as the notebook kernel if you want the deep model to run.

## Data flow

The notebooks reuse the repository's existing market-data stack:

1. Read local CSVs from `backend/data` when available.
2. Fall back to Supabase if credentials are configured.
3. Fall back to TwelveData if an API key is configured.

When a symbol is fetched remotely, a CSV cache is written into `notebooks/market_forecasting/data/`.

## Default asset set

The multi-asset notebook uses tradable proxies:

- `GLD` for gold exposure
- `BNO` for Brent oil exposure
- `NVDA` for NVIDIA
- `SPY` for S&P 500 exposure

Using proxies keeps the workflow aligned with tradeable daily instruments. If you want exact spot or futures symbols later, you can swap the `AssetDefinition` values in the notebook config cell.
