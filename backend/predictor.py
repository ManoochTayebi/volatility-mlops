################################################################################
###                                                                          ###
### Created by Mahdi Manoochehrtayebi, 2025                                  ###
###                                                                          ###
################################################################################

"""
Volatility prediction engine - loads models and makes predictions.
"""

import numpy as np
import pandas as pd
import torch
import os
from typing import List, Tuple
import logging
from datetime import timedelta

from backend.nn_trainer import VolatilityModel, TrainingConfig
from backend.dataset import DatasetProcessor, DataConfig
from backend.azure_artifacts import download_artifacts_if_configured

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Production configuration constants
WINDOW_SIZE = 21


class VolatilityPredictor:
    """
    Loads trained models and makes volatility predictions.
    Uses fixed production parameters from compute.py workflow.
    """
    
    def __init__(self):
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_dir = os.path.join(backend_dir, "data", "nn_models")
        self.volatility_dir = os.path.join(backend_dir, "data", "saved_volatilities")
        self.models = {}  # Cache for loaded models
        self.volatility_data = {}  # Cache for volatility data

        download_artifacts_if_configured(target_root=os.path.join(backend_dir, "data"))
        
        # Align serving-time architecture with training-time env configuration.
        self.config = TrainingConfig(
            window_size=int(os.getenv("WINDOW_SIZE", str(WINDOW_SIZE))),
            train_test_split=float(os.getenv("TRAIN_TEST_SPLIT", "0.5")),
            rolling_window=int(os.getenv("ROLLING_WINDOW", "21")),
            rnn_hidden_size=int(os.getenv("RNN_HIDDEN_SIZE", os.getenv("LSTM_HIDDEN_SIZE", "24"))),
            rnn_num_layers=int(os.getenv("RNN_NUM_LAYERS", os.getenv("LSTM_NUM_LAYERS", "1"))),
            fc_hidden_size=int(os.getenv("FC_HIDDEN_SIZE", "12")),
            dropout=float(os.getenv("DROPOUT", "0.1")),
        )
        
        # Initialize dataset processor for data handling
        data_config = DataConfig(
            window_size=self.config.window_size,
            train_test_split=self.config.train_test_split,
            rolling_window=self.config.rolling_window
        )
        self.data_processor = DatasetProcessor(data_config)
        
    def load_model(self, asset: str) -> VolatilityModel:
        """
        Load a trained neural model for the given asset.
        
        Parameters
        ----------
        asset : str
            Asset symbol (e.g., 'AAPL', 'GOOGL', 'MSFT')
            
        Returns
        -------
        VolatilityModel
            Loaded model in evaluation mode
        """
        if asset in self.models:
            return self.models[asset]
            
        model_path = os.path.join(self.model_dir, f"nn_model_{asset.lower()}.pth")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found for asset {asset} at {model_path}")
        
        # Use VolatilityModel from nn_trainer with production config
        model = VolatilityModel(self.config)
        try:
            model.load_state_dict(torch.load(model_path, map_location='cpu'))
        except RuntimeError as exc:
            raise RuntimeError(
                f"Incompatible model checkpoint for {asset}. "
                "Please run `make retrain` to regenerate GRU-compatible models."
            ) from exc
        model.eval()
        self.models[asset] = model
        logger.info(f"Loaded neural model for {asset}")
        return model
    
    def load_volatility_data(self, asset: str) -> pd.Series:
        """
        Load realized volatility data for the given asset.
        Uses DatasetProcessor for consistent file handling.
        
        Parameters
        ----------
        asset : str
            Asset symbol
            
        Returns
        -------
        pd.Series
            Realized volatility time series
        """
        if asset in self.volatility_data:
            return self.volatility_data[asset]
            
        # Use data processor for loading
        volatility_data = self.data_processor.load_volatility(asset, self.volatility_dir)
        self.volatility_data[asset] = volatility_data
        logger.info(f"Loaded volatility data for {asset}: {len(volatility_data)} observations")
        return volatility_data
    
    def prepare_sequence(self, data: np.ndarray, window_size: int = WINDOW_SIZE) -> np.ndarray:
        """Prepare the last sequence for neural prediction."""
        window_size = self.config.window_size if window_size == WINDOW_SIZE else window_size
        if len(data) < window_size:
            raise ValueError(f"Not enough data points. Need at least {window_size}, got {len(data)}")
        
        sequence = data[-window_size:].reshape(1, window_size, 1)
        return sequence
    
    def predict_next_volatility(self, asset: str, current_data: np.ndarray) -> float:
        """
        Predict the next volatility value for an asset using the neural model.
        
        Parameters
        ----------
        asset : str
            Asset symbol (e.g., 'AAPL')
        current_data : np.ndarray
            Historical volatility data
            
        Returns
        -------
        float
            Neural model prediction
        """
        # Load neural model
        model = self.load_model(asset)
        
        model_input = self.prepare_sequence(current_data)
        with torch.no_grad():
            pred = model(torch.tensor(model_input, dtype=torch.float32)).numpy()[0]
        return float(pred)
    
    def predict_multi_step(self, asset: str, days: int) -> Tuple[List[float], List[str]]:
        """
        Predict volatility for multiple days ahead using iterative forecasting.
        
        Parameters
        ----------
        asset : str
            Asset symbol
        days : int
            Number of days to forecast
            
        Returns
        -------
        predictions : List[float]
            Predicted volatilities
        dates : List[str]
            Corresponding date strings
        """
        volatility_series = self.load_volatility_data(asset)
        current_data = volatility_series.dropna().values.copy()
        
        predictions = []
        dates = []
        last_date = volatility_series.index[-1]
        
        for i in range(days):
            # Predict next volatility
            next_vol = self.predict_next_volatility(asset, current_data)
            predictions.append(next_vol)
            
            # Generate next date
            next_date = last_date + timedelta(days=i+1)
            dates.append(next_date.strftime('%Y-%m-%d'))
            
            # Update data for next iteration
            current_data = np.append(current_data, next_vol)
        
        return predictions, dates
