import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def volatility_series() -> pd.Series:
    index = pd.date_range("2026-01-01", periods=80, freq="D")
    values = 0.2 + 0.01 * np.sin(np.arange(80) / 5)
    return pd.Series(values, index=index, name="realized_volatility")
