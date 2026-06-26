import pytest

from scripts.preflight_check import parse_symbols
from scripts.retrain_with_mlflow import maybe_register_model


def test_parse_symbols_normalizes_and_drops_empty_values():
    assert parse_symbols(" aapl, , msft ") == ["AAPL", "MSFT"]


def test_quality_gate_blocks_registration_when_rmse_too_high(monkeypatch):
    monkeypatch.setenv("MLFLOW_REGISTER_MODELS", "true")
    monkeypatch.setenv("MODEL_MAX_RMSE", "0.5")
    monkeypatch.setenv("ENFORCE_MODEL_QUALITY_GATE", "true")

    with pytest.raises(ValueError, match="registration blocked"):
        maybe_register_model(
            asset="AAPL",
            config=None,
            details={"metrics": {"rmse": 1.0}},
        )
