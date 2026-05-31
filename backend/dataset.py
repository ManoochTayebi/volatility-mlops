################################################################################
###                                                                          ###
### Created by Mahdi Manoochehrtayebi, 2025                                  ###
###                                                                          ###
################################################################################

"""
Dataset processing utilities for volatility modeling.
Handles data loading, preprocessing, and preparation for model training.
"""

import numpy as np
import pandas as pd
import torch
import os
from typing import Tuple, Optional
import logging
from dataclasses import dataclass

from src.azure_sql_connect import AzureSqlOperations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DataConfig:
    """Configuration for dataset processing."""
    window_size: int = 21
    train_test_split: float = 0.5  # Fraction of data for training
    rolling_window: int = 21  # For realized volatility computation
    
    
class DatasetProcessor:
    """
    Handles all data preprocessing for volatility modeling.
    
    Methods
    -------
    - compute_log_returns: Convert prices to log returns
    - compute_realized_volatility: Calculate rolling volatility from returns
    - prepare_sequences: Create recurrent-model-ready sequences
    - split_train_test: Split data into training and testing sets
    """
    
    def __init__(self, config: Optional[DataConfig] = None):
        """
        Initialize dataset processor.
        
        Parameters
        ----------
        config : DataConfig, optional
            Configuration parameters for data processing
        """
        self.config = config or DataConfig()
        
    @staticmethod
    def compute_log_returns(prices: pd.Series) -> pd.Series:
        """
        Compute log returns from price series.
        
        Parameters
        ----------
        prices : pd.Series
            Price time series
            
        Returns
        -------
        pd.Series
            Log returns
        """
        return np.log(prices / prices.shift(1)).dropna()
    
    def compute_realized_volatility(
        self, 
        prices: pd.Series, 
        window: Optional[int] = None
    ) -> pd.Series:
        """
        Compute realized volatility as rolling standard deviation of log returns.
        
        Parameters
        ----------
        prices : pd.Series
            Price time series with datetime index
        window : int, optional
            Rolling window size (default from config)
            
        Returns
        -------
        pd.Series
            Realized volatility series
        """
        window = window or self.config.rolling_window
        
        # Compute log returns
        log_returns = self.compute_log_returns(prices)
        
        # Compute rolling standard deviation
        realized_vol = log_returns.rolling(window=window).std().dropna()
        
        logger.info(f"Computed realized volatility: {len(realized_vol)} observations")
        return realized_vol
    
    def load_market_data(
        self, 
        asset: str, 
        data_folder: str = "backend/data",
        source: str = "azure_sql",
        table_name: str = "dbo.daily_stock_prices",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load market data from Azure SQL or CSV.
        
        Parameters
        ----------
        asset : str
            Asset symbol (e.g., 'AAPL', 'GOOGL', 'MSFT')
        data_folder : str
            Path to data folder
        source : str
            Data source: "azure_sql" (default) or "csv"
        table_name : str
            Azure SQL table name when source="azure_sql"
        start_date : str, optional
            Start date for data filtering (format: 'YYYY-MM-DD')
        end_date : str, optional
            End date for data filtering (format: 'YYYY-MM-DD')
            
        Returns
        -------
        pd.DataFrame
            Market data with datetime index
        """
        if source == "azure_sql":
            df = self._load_market_data_from_azure_sql(asset=asset, table_name=table_name)
        elif source == "csv":
            df = self._load_market_data_from_csv(asset=asset, data_folder=data_folder)
        else:
            raise ValueError(f"Unsupported market data source: {source}")

        # Filter by date range if specified
        if start_date is not None:
            start_date = pd.to_datetime(start_date)
            df = df[df.index >= start_date]
        if end_date is not None:
            end_date = pd.to_datetime(end_date)
            df = df[df.index <= end_date]

        logger.info(
            f"Loaded {len(df)} rows for {asset} from {source}"
            + (f" (from {start_date})" if start_date else "")
            + (f" (to {end_date})" if end_date else "")
        )
        return df

    def _load_market_data_from_csv(
        self,
        asset: str,
        data_folder: str,
    ) -> pd.DataFrame:
        file_path = os.path.join(data_folder, f"market_{asset.lower()}.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Market data not found: {file_path}")

        df = pd.read_csv(file_path, parse_dates=["Date"])
        return df.set_index("Date").sort_index()

    def _load_market_data_from_azure_sql(
        self,
        asset: str,
        table_name: str,
    ) -> pd.DataFrame:
        azure_sql = AzureSqlOperations()
        rows = azure_sql.fetch_symbol_rows(table_name=table_name, symbol=asset)
        if not rows:
            raise FileNotFoundError(
                f"No Azure SQL market data found for {asset} in table {table_name}"
            )

        frame = pd.DataFrame(rows)
        frame["datetime"] = pd.to_datetime(frame["datetime"])
        for col in ["open", "high", "low", "close", "volume"]:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")

        renamed = frame.rename(
            columns={
                "datetime": "Date",
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            }
        )
        renamed = renamed[["Date", "Open", "High", "Low", "Close", "Volume"]]
        return renamed.set_index("Date").sort_index()
    
    def prepare_sequences(
        self, 
        data: np.ndarray, 
        window_size: Optional[int] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for recurrent model training.
        
        Parameters
        ----------
        data : np.ndarray
            Time series data
        window_size : int, optional
            Sequence length (default from config)
            
        Returns
        -------
        X : np.ndarray
            Input sequences, shape (n_samples, window_size, 1)
        y : np.ndarray
            Target values, shape (n_samples,)
        """
        window_size = window_size or self.config.window_size
        
        X, y = [], []
        for i in range(window_size, len(data) - 1):
            X.append(data[i - window_size:i].reshape(-1, 1))
            y.append(data[i + 1])
        
        X = np.array(X)
        y = np.array(y)
        
        logger.info(f"Created sequences: X={X.shape}, y={y.shape}")
        return X, y
    
    def split_train_test(
        self, 
        X: np.ndarray, 
        y: np.ndarray, 
        data_length: int,
        split_ratio: Optional[float] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
        """
        Split data into training and testing sets.
        
        Parameters
        ----------
        X : np.ndarray
            Input sequences
        y : np.ndarray
            Target values
        data_length : int
            Original data length (before sequencing)
        split_ratio : float, optional
            Train/test split ratio (default from config)
            
        Returns
        -------
        X_train : np.ndarray
        y_train : np.ndarray
        X_test : np.ndarray
        y_test : np.ndarray
        n_train : int
            Number of training samples in original data
        """
        split_ratio = split_ratio or self.config.train_test_split
        
        n_train = int(data_length * split_ratio)
        split_point = max(0, n_train - self.config.window_size)
        
        X_train = X[:split_point]
        y_train = y[:split_point]
        X_test = X[split_point:]
        y_test = y[split_point:]
        
        logger.info(f"Train/Test split: {X_train.shape[0]}/{X_test.shape[0]} samples")
        logger.info(f"Split point: {split_point}, n_train: {n_train}")
        
        return X_train, y_train, X_test, y_test, n_train
    
    def save_volatility(
        self, 
        volatility: pd.Series, 
        asset: str, 
        save_folder: str = "backend/data/saved_volatilities"
    ) -> None:
        """
        Save realized volatility to disk.
        
        Parameters
        ----------
        volatility : pd.Series
            Realized volatility series
        asset : str
            Asset symbol
        save_folder : str
            Path to save folder
        """
        os.makedirs(save_folder, exist_ok=True)
        save_path = os.path.join(save_folder, f"realized_volatility_{asset.lower()}.pth")
        torch.save(volatility, save_path)
        logger.info(f"Saved volatility to {save_path}")
    
    def load_volatility(
        self, 
        asset: str, 
        data_folder: str = "backend/data/saved_volatilities"
    ) -> pd.Series:
        """
        Load realized volatility from disk.
        
        Parameters
        ----------
        asset : str
            Asset symbol
        data_folder : str
            Path to data folder
            
        Returns
        -------
        pd.Series
            Realized volatility series
        """
        vol_path = os.path.join(data_folder, f"realized_volatility_{asset.lower()}.pth")
        
        if not os.path.exists(vol_path):
            raise FileNotFoundError(f"Volatility data not found: {vol_path}")
        
        volatility = torch.load(vol_path)
        logger.info(f"Loaded volatility for {asset}: {len(volatility)} observations")
        return volatility
