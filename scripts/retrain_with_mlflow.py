import argparse
import os
import sys
from dataclasses import asdict
from typing import TYPE_CHECKING, Dict, List

import mlflow
import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if TYPE_CHECKING:
    from backend.nn_trainer import TrainingConfig


def parse_symbols(raw_symbols: str) -> List[str]:
    return [s.strip().upper() for s in raw_symbols.split(",") if s.strip()]


def create_training_config(asset: str) -> "TrainingConfig":
    from backend.nn_trainer import TrainingConfig

    return TrainingConfig(
        asset_name=asset,
        window_size=int(os.getenv("WINDOW_SIZE", "21")),
        train_test_split=float(os.getenv("TRAIN_TEST_SPLIT", "0.5")),
        rolling_window=int(os.getenv("ROLLING_WINDOW", "21")),
        rnn_hidden_size=int(os.getenv("RNN_HIDDEN_SIZE", os.getenv("LSTM_HIDDEN_SIZE", "24"))),
        rnn_num_layers=int(os.getenv("RNN_NUM_LAYERS", os.getenv("LSTM_NUM_LAYERS", "1"))),
        fc_hidden_size=int(os.getenv("FC_HIDDEN_SIZE", "12")),
        dropout=float(os.getenv("DROPOUT", "0.1")),
        batch_size=int(os.getenv("BATCH_SIZE", "64")),
        learning_rate=float(os.getenv("LEARNING_RATE", "0.001")),
        epochs=int(os.getenv("EPOCHS", "20")),
        data_folder=os.getenv("DATA_FOLDER", "backend/data"),
        model_save_folder=os.getenv("MODEL_SAVE_FOLDER", "backend/data/nn_models"),
        volatility_save_folder=os.getenv("VOLATILITY_SAVE_FOLDER", "backend/data/saved_volatilities"),
    )


def compute_and_save_volatility(asset: str, config: "TrainingConfig") -> pd.Series:
    from backend.dataset import DataConfig, DatasetProcessor

    data_processor = DatasetProcessor(
        DataConfig(
            window_size=config.window_size,
            train_test_split=config.train_test_split,
            rolling_window=config.rolling_window,
        )
    )

    market_data = data_processor.load_market_data(asset=asset, data_folder=config.data_folder)
    volatility = data_processor.compute_realized_volatility(prices=market_data["Close"], window=config.rolling_window)
    data_processor.save_volatility(volatility=volatility, asset=asset, save_folder=config.volatility_save_folder)
    return volatility


def log_asset_run(asset: str, config: "TrainingConfig", details: Dict, volatility_path: str) -> None:
    mlflow.log_params({f"cfg_{k}": v for k, v in asdict(config).items()})
    mlflow.log_metric("mse", details["metrics"]["mse"])
    mlflow.log_metric("rmse", details["metrics"]["rmse"])
    mlflow.log_metric("mae", details["metrics"]["mae"])
    mlflow.log_metric("num_predictions", len(details["combined_preds"]))

    mlflow.log_artifact(details["model_path"], artifact_path=f"models/{asset.lower()}")
    if os.path.exists(volatility_path):
        mlflow.log_artifact(volatility_path, artifact_path=f"volatility/{asset.lower()}")

def maybe_register_model(asset: str, config: "TrainingConfig", details: Dict) -> None:
    register = os.getenv("MLFLOW_REGISTER_MODELS", "false").lower() == "true"
    if not register:
        return

    import torch
    from backend.nn_trainer import VolatilityModel

    model = VolatilityModel(config)
    model.load_state_dict(torch.load(details["model_path"], map_location="cpu"))
    model.eval()

    artifact_path = f"registered_model/{asset.lower()}"
    mlflow.pytorch.log_model(pytorch_model=model, artifact_path=artifact_path)

    run = mlflow.active_run()
    if run is None:
        return

    model_name_prefix = os.getenv("MLFLOW_MODEL_NAME_PREFIX", "volatility-nn")
    model_name = f"{model_name_prefix}-{asset.lower()}"
    model_uri = f"runs:/{run.info.run_id}/{artifact_path}"

    try:
        result = mlflow.register_model(model_uri=model_uri, name=model_name)
        print(f"[{asset}] registered model version {result.version} as {model_name}")
    except Exception as exc:
        print(f"[{asset}] model registration skipped: {exc}")



def run(symbols: List[str]) -> None:
    load_dotenv()
    from backend.nn_trainer import NNTrainer

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
    experiment = os.getenv("MLFLOW_EXPERIMENT_NAME", "volatility-nn")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment)

    with mlflow.start_run(run_name="scheduled-retraining"):
        mlflow.set_tag("pipeline", "supabase-gha-mlflow")

        for symbol in symbols:
            config = create_training_config(symbol)
            with mlflow.start_run(run_name=f"train-{symbol}", nested=True):
                volatility = compute_and_save_volatility(symbol, config)
                trainer = NNTrainer(config)
                _, _, details = trainer.train_or_finetune(
                    asset_name=symbol,
                    volatility_series=volatility,
                    fine_tuning=True,
                    return_details=True,
                )

                volatility_path = os.path.join(
                    config.volatility_save_folder,
                    f"realized_volatility_{symbol.lower()}.pth",
                )
                log_asset_run(symbol, config, details, volatility_path)
                maybe_register_model(symbol, config, details)
                print(
                    f"[{symbol}] rmse={details['metrics']['rmse']:.6f}, "
                    f"mae={details['metrics']['mae']:.6f}, "
                    f"mse={details['metrics']['mse']:.6f}"
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrain volatility models and log runs to MLflow")
    parser.add_argument("--symbols", default=os.getenv("SYMBOLS", "AAPL,GOOGL,MSFT"))
    args = parser.parse_args()

    run(parse_symbols(args.symbols))


if __name__ == "__main__":
    main()
