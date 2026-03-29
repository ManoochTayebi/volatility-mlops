################################################################################
###                                                                          ###
### Created by Mahdi Manoochehrtayebi, 2025                                  ###
###                                                                          ###
################################################################################

"""
Neural volatility trainer.

This module trains a compact GRU-based network for volatility forecasting.
"""

import os
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from backend.dataset import DataConfig, DatasetProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configuration parameters for neural volatility training."""
    asset_name: str = "AAPL"
    window_size: int = 21
    train_test_split: float = 0.5
    rolling_window: int = 21

    # Compact recurrent architecture tuned for faster training/inference.
    rnn_hidden_size: int = 24
    rnn_num_layers: int = 1
    fc_hidden_size: int = 12
    dropout: float = 0.1

    batch_size: int = 64
    learning_rate: float = 1e-3
    epochs: int = 20

    data_folder: str = "backend/data"
    model_save_folder: str = "backend/data/nn_models"
    volatility_save_folder: str = "backend/data/saved_volatilities"


class VolatilityDataset(Dataset):
    """Dataset class for volatility time series data."""

    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.X[idx], self.y[idx]


class VolatilityGRU(nn.Module):
    """Compact GRU model for fast volatility prediction."""

    def __init__(self, config: TrainingConfig):
        super().__init__()
        self.config = config
        self.gru = nn.GRU(
            input_size=1,
            hidden_size=config.rnn_hidden_size,
            num_layers=config.rnn_num_layers,
            batch_first=True,
            dropout=config.dropout if config.rnn_num_layers > 1 else 0.0,
        )
        self.norm = nn.LayerNorm(config.rnn_hidden_size)
        self.fc = nn.Sequential(
            nn.Linear(config.rnn_hidden_size, config.fc_hidden_size),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.fc_hidden_size, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.gru(x)
        features = self.norm(out[:, -1, :])
        return self.fc(features).squeeze(-1)


# Export alias used across training and inference modules.
VolatilityModel = VolatilityGRU


class NNTrainer:
    """
    Main class for training and managing neural volatility models.
    """

    def __init__(self, config: TrainingConfig):
        self.config = config
        self.model_dir = config.model_save_folder
        os.makedirs(self.model_dir, exist_ok=True)

        data_config = DataConfig(
            window_size=config.window_size,
            train_test_split=config.train_test_split,
            rolling_window=config.rolling_window,
        )
        self.data_processor = DatasetProcessor(data_config)

    def prepare_data(
        self, volatility_series: pd.Series
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
        values = volatility_series.dropna().values
        n_total = len(values)

        logger.info(f"Total data points: {n_total}")
        logger.info(f"Window size: {self.config.window_size}")
        logger.info(f"Train/test split: {self.config.train_test_split}")

        X, y = self.data_processor.prepare_sequences(values, self.config.window_size)
        X_train, y_train, X_test, y_test, n_train = self.data_processor.split_train_test(
            X, y, n_total, self.config.train_test_split
        )
        return X_train, y_train, X_test, y_test, n_train

    def train_or_finetune(
        self,
        asset_name: Optional[str] = None,
        volatility_series: Optional[pd.Series] = None,
        fine_tuning: bool = False,
        return_details: bool = False,
    ) -> Union[Tuple[np.ndarray, int], Tuple[np.ndarray, int, Dict[str, Any]]]:
        asset_name = asset_name or self.config.asset_name

        if volatility_series is None:
            volatility_series = self.data_processor.load_volatility(
                asset_name, self.config.volatility_save_folder
            )

        X_train, y_train, X_test, y_test, n_train = self.prepare_data(volatility_series)

        logger.info(f"Training data: X={X_train.shape}, y={y_train.shape}")
        logger.info(f"Testing data: X={X_test.shape}, y={y_test.shape}")

        train_ds = VolatilityDataset(X_train, y_train)
        train_dl = DataLoader(train_ds, batch_size=self.config.batch_size, shuffle=True)
        if len(train_dl) == 0:
            raise ValueError("Training dataset is empty. Check window size and data length.")

        model = VolatilityGRU(self.config)
        model_path = os.path.join(self.model_dir, f"nn_model_{asset_name.lower()}.pth")

        if fine_tuning and os.path.exists(model_path):
            logger.info(f"Fine-tuning existing model for {asset_name}")
            try:
                model.load_state_dict(torch.load(model_path, map_location="cpu"))
            except RuntimeError as exc:
                logger.warning(
                    "Checkpoint for %s is incompatible with current architecture. "
                    "Falling back to training from scratch. Details: %s",
                    asset_name,
                    exc,
                )
        else:
            logger.info(f"Training new model for {asset_name}")

        optimizer = torch.optim.Adam(model.parameters(), lr=self.config.learning_rate)
        loss_fn = nn.MSELoss()

        for epoch in range(self.config.epochs):
            model.train()
            total_loss = 0.0
            for xb, yb in train_dl:
                optimizer.zero_grad()
                pred = model(xb)
                loss = loss_fn(pred, yb)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            avg_loss = total_loss / len(train_dl)
            if epoch % 5 == 0:
                logger.info(f"Epoch {epoch}/{self.config.epochs}: Loss = {avg_loss:.6f}")

        model.eval()
        with torch.no_grad():
            preds = model(torch.tensor(X_test, dtype=torch.float32)).numpy()

        torch.save(model.state_dict(), model_path)
        logger.info(f"Model saved to {model_path}")

        y_test_aligned = y_test[: len(preds)]
        mse = float(np.mean((preds - y_test_aligned) ** 2))
        metrics = {
            "mse": mse,
            "rmse": float(np.sqrt(mse)),
            "mae": float(np.mean(np.abs(preds - y_test_aligned))),
        }

        details = {
            "asset": asset_name,
            "metrics": metrics,
            "model_path": model_path,
            "y_test": y_test_aligned,
            "combined_preds": preds,
            "n_train": n_train,
        }

        if return_details:
            return preds, n_train, details
        return preds, n_train


def main() -> Dict[str, Any]:
    """Main execution function for standalone training."""
    config = TrainingConfig(asset_name="AAPL")
    trainer = NNTrainer(config)

    predictions, n_train = trainer.train_or_finetune(
        asset_name=config.asset_name,
        fine_tuning=True,
    )

    volatility_series = trainer.data_processor.load_volatility(
        config.asset_name, config.volatility_save_folder
    )

    return {
        "predictions": predictions,
        "test_index": n_train + 1,
        "test_dates": volatility_series.index[n_train + 1 : n_train + 1 + len(predictions)],
    }


if __name__ == "__main__":
    main()
