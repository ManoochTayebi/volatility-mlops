PYTHON ?= python
SYMBOLS ?= AAPL,GOOGL,MSFT
TABLE ?= dbo.daily_stock_prices

.PHONY: install preflight ingest-full ingest-daily retrain pipeline serve mlflow-ui

install:
	$(PYTHON) -m pip install -r requirements.txt

preflight:
	$(PYTHON) scripts/preflight_check.py --symbols "$(SYMBOLS)" --table "$(TABLE)"

ingest-full:
	$(PYTHON) scripts/ingest_market_data.py --mode full --symbols "$(SYMBOLS)" --table "$(TABLE)"

ingest-daily:
	$(PYTHON) scripts/ingest_market_data.py --mode daily --symbols "$(SYMBOLS)" --table "$(TABLE)"

retrain:
	$(PYTHON) scripts/retrain_with_mlflow.py --symbols "$(SYMBOLS)"

pipeline:
	$(PYTHON) scripts/run_daily_pipeline.py --symbols "$(SYMBOLS)" --table "$(TABLE)"

serve:
	uvicorn backend.app:app --host 0.0.0.0 --port 8000

mlflow-ui:
	mlflow ui --backend-store-uri ./mlruns --port 5001
