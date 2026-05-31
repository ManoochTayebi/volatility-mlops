################################################################################
###                                                                          ###
### Created by Mahdi Manoochehrtayebi, 2025                                  ###
###                                                                          ###
################################################################################

"""
Volatility prediction API - orchestrates neural volatility models.
"""

import numpy as np
from typing import Dict, List
import logging

# Import predictor class from dedicated module
from backend.predictor import VolatilityPredictor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_predictor = None


def get_predictor() -> VolatilityPredictor:
    """Create the predictor only when a prediction endpoint needs it."""
    global _predictor
    if _predictor is None:
        _predictor = VolatilityPredictor()
    return _predictor


def compute_asset_volatility(asset: str, days: int = 5, historical_period: int = 30) -> Dict:
    """
    Compute asset volatility predictions using the neural model.
    
    Parameters
    ----------
    asset : str
        Asset symbol (e.g., 'AAPL', 'GOOGL', 'MSFT')
    days : int
        Number of days to forecast (default: 5)
    historical_period : int
        Number of recent historical days to include in response (default: 30)
        
    Returns
    -------
    dict
        Contains historical and predicted volatility data with dates
    """
    try:
        predictor = get_predictor()
        # Get predictions using trained model
        predictions, predicted_dates = predictor.predict_multi_step(asset, days)
        
        # Load historical volatility for visualization context
        volatility_series = predictor.load_volatility_data(asset)
        historical_data = volatility_series.dropna()
        recent_historical = historical_data.tail(historical_period)
        
        return {
            "asset": asset,
            "historical_dates": recent_historical.index.strftime('%Y-%m-%d').tolist(),
            "historical_vol": recent_historical.values.tolist(),
            "predicted_dates": predicted_dates,
            "predicted_vol": predictions,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error computing asset volatility for {asset}: {str(e)}")
        return {
            "asset": asset,
            "error": str(e),
            "status": "error"
        }



def compute_portfolio_volatility(assets: List[str], days: int = 5, historical_period: int = 30) -> Dict:
    """
    Compute portfolio volatility predictions for multiple assets.
    
    Parameters
    ----------
    assets : List[str]
        List of asset symbols
    days : int
        Number of days to forecast
    historical_period : int
        Number of recent historical days to include
        
    Returns
    -------
    dict
        Contains portfolio and individual asset volatility predictions
    """
    try:
        predictor = get_predictor()
        # Get individual asset predictions and historical data
        asset_predictions = {}
        asset_historical_data = {}
        asset_dates = None
        historical_dates = None
        
        for asset in assets:
            predictions, dates = predictor.predict_multi_step(asset, days)
            asset_predictions[asset] = predictions
            if asset_dates is None:
                asset_dates = dates
            
            # Get historical data for each asset
            volatility_series = predictor.load_volatility_data(asset)
            if volatility_series is not None:
                recent_historical = volatility_series.dropna().tail(historical_period)
                hist_vol = recent_historical.values.tolist()
                hist_dates = recent_historical.index.strftime('%Y-%m-%d').tolist()
                
                asset_historical_data[asset] = hist_vol
                if historical_dates is None:
                    historical_dates = hist_dates
        
        # Compute portfolio volatility (equal weights, zero correlation assumption)
        weights = np.ones(len(assets)) / len(assets)
        portfolio_predictions = []
        
        for day in range(days):
            day_vols = np.array([asset_predictions[asset][day] for asset in assets])
            portfolio_vol = np.sqrt(np.sum((weights * day_vols) ** 2))
            portfolio_predictions.append(float(portfolio_vol))
        
        # Compute historical portfolio volatility
        historical_portfolio_vol = []
        if asset_historical_data and len(list(asset_historical_data.values())[0]) > 0:
            hist_length = len(list(asset_historical_data.values())[0])
            for day in range(hist_length):
                day_vols = np.array([asset_historical_data[asset][day] for asset in assets])
                portfolio_vol = np.sqrt(np.sum((weights * day_vols) ** 2))
                historical_portfolio_vol.append(float(portfolio_vol))
        
        return {
            "assets": assets,
            "weights": weights.tolist(),
            "predicted_dates": asset_dates,
            "historical_dates": historical_dates,
            "portfolio_vol": portfolio_predictions,
            "historical_portfolio_vol": historical_portfolio_vol,
            "individual_predictions": asset_predictions,
            "individual_historical": asset_historical_data,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error computing portfolio volatility: {str(e)}")
        return {
            "assets": assets,
            "error": str(e),
            "status": "error"
        }
