from backend import compute


class FakePredictor:
    def predict_multi_step(self, asset, days):
        return [0.1] * days, [f"2026-01-{day + 1:02d}" for day in range(days)]

    def load_volatility_data(self, asset):
        import pandas as pd

        return pd.Series(
            [0.2, 0.21, 0.22],
            index=pd.date_range("2025-12-29", periods=3, freq="D"),
        )


def test_compute_asset_volatility_success(monkeypatch):
    monkeypatch.setattr(compute, "get_predictor", lambda: FakePredictor())

    result = compute.compute_asset_volatility("AAPL", days=2, historical_period=2)

    assert result["status"] == "success"
    assert result["asset"] == "AAPL"
    assert result["predicted_vol"] == [0.1, 0.1]
    assert len(result["historical_vol"]) == 2


def test_compute_portfolio_volatility_success(monkeypatch):
    monkeypatch.setattr(compute, "get_predictor", lambda: FakePredictor())

    result = compute.compute_portfolio_volatility(["AAPL", "MSFT"], days=2, historical_period=2)

    assert result["status"] == "success"
    assert result["assets"] == ["AAPL", "MSFT"]
    assert len(result["portfolio_vol"]) == 2
    assert set(result["individual_predictions"]) == {"AAPL", "MSFT"}
