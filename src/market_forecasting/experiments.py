from __future__ import annotations

import importlib.util
import os
import sys
from datetime import date
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

DEFAULT_START_DATE = "2015-01-01"
DEFAULT_END_DATE = date.today().strftime("%Y-%m-%d")
TRADING_DAYS_PER_MONTH = 21
REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_MARKET_DATA_DIR = REPO_ROOT / "backend" / "data"
NOTEBOOK_MARKET_DATA_DIR = REPO_ROOT / "notebooks" / "market_forecasting" / "data"
DEEP_MODEL_DEPENDENCY_MESSAGE = (
    "The deep time-series model requires the `torch` package, but it is not installed "
    f"in the active Python environment: {sys.executable}. "
    "If you are running this notebook in Jupyter, switch to the repository `.venv` kernel "
    "or install PyTorch into the current kernel."
)


@dataclass(frozen=True)
class AssetDefinition:
    """Tradable symbol plus a user-facing label for notebook workflows."""

    symbol: str
    label: str
    twelvedata_symbol: str | None = None


DEFAULT_MULTI_ASSET_UNIVERSE: Dict[str, AssetDefinition] = {
    "GLD": AssetDefinition(symbol="GLD", label="Gold proxy via GLD ETF"),
    "BNO": AssetDefinition(symbol="BNO", label="Brent proxy via BNO ETF"),
    "NVDA": AssetDefinition(symbol="NVDA", label="NVIDIA"),
    "SPY": AssetDefinition(symbol="SPY", label="S&P 500 proxy via SPY ETF"),
}
DEFAULT_SINGLE_ASSET = AssetDefinition(symbol="SIDU", label="Sidus Space")


def _read_market_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["Date"])
    return _normalize_market_frame(frame)


def _normalize_market_frame(frame: pd.DataFrame) -> pd.DataFrame:
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

    required = ["Date", "Open", "High", "Low", "Close", "Volume"]
    for column in required:
        if column not in renamed.columns:
            renamed[column] = np.nan

    normalized = renamed[required].copy()
    normalized["Date"] = pd.to_datetime(normalized["Date"])
    for column in ["Open", "High", "Low", "Close", "Volume"]:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    normalized = (
        normalized.dropna(subset=["Date", "Open", "High", "Low", "Close"])
        .drop_duplicates(subset=["Date"], keep="last")
        .sort_values("Date")
        .set_index("Date")
    )
    normalized.index.name = "Date"
    return normalized


def _rows_to_market_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    return _normalize_market_frame(pd.DataFrame(rows))


def _cache_market_frame(frame: pd.DataFrame, symbol: str, cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_path = cache_dir / f"market_{symbol.lower()}.csv"
    frame.reset_index().to_csv(output_path, index=False)


def describe_market_data_sources(
    symbol: str,
    *,
    cache_dir: Path = NOTEBOOK_MARKET_DATA_DIR,
) -> pd.DataFrame:
    """Summarize which data sources are immediately available for a symbol."""

    lower_symbol = symbol.lower()
    backend_csv = LOCAL_MARKET_DATA_DIR / f"market_{lower_symbol}.csv"
    notebook_cache = cache_dir / f"market_{lower_symbol}.csv"

    rows = [
        {
            "source": "backend_csv",
            "available": backend_csv.exists(),
            "details": str(backend_csv),
        },
        {
            "source": "notebook_cache",
            "available": notebook_cache.exists(),
            "details": str(notebook_cache),
        },
        {
            "source": "supabase_env",
            "available": bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY")),
            "details": "requires SUPABASE_URL and SUPABASE_SERVICE_KEY",
        },
        {
            "source": "twelvedata_env",
            "available": bool(os.getenv("TWELVE_DATA_API_KEY")),
            "details": "requires TWELVE_DATA_API_KEY",
        },
    ]
    return pd.DataFrame(rows)


def describe_runtime_dependencies() -> pd.DataFrame:
    """Show which packages are available in the current notebook kernel."""

    packages = [
        ("numpy", importlib.util.find_spec("numpy") is not None),
        ("pandas", importlib.util.find_spec("pandas") is not None),
        ("scikit-learn", importlib.util.find_spec("sklearn") is not None),
        ("torch", importlib.util.find_spec("torch") is not None),
    ]
    return pd.DataFrame(
        [
            {"package": package, "available": available, "python_executable": sys.executable}
            for package, available in packages
        ]
    )


def _optional_deep_backend():
    try:
        from . import deep_models
    except ModuleNotFoundError as exc:
        if exc.name == "torch":
            return None
        raise
    return deep_models


def _optional_supabase_operations():
    try:
        from src.supabase_connect import SupabaseOperations
    except ModuleNotFoundError:
        return None
    return SupabaseOperations


def _optional_twelvedata_client():
    try:
        from src.twelve_data_client import TwelveDataClient
    except ModuleNotFoundError:
        return None
    return TwelveDataClient


def _require_deep_backend():
    deep_backend = _optional_deep_backend()
    if deep_backend is None:
        raise ModuleNotFoundError(DEEP_MODEL_DEPENDENCY_MESSAGE)
    return deep_backend


def _default_device() -> str:
    deep_backend = _optional_deep_backend()
    if deep_backend is None:
        return "cpu"
    return "cuda" if deep_backend.cuda_available() else "cpu"


def is_deep_model_available() -> bool:
    return _optional_deep_backend() is not None


def load_market_history(
    symbol: str,
    *,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    cache_dir: Path = NOTEBOOK_MARKET_DATA_DIR,
    twelvedata_symbol: str | None = None,
) -> pd.DataFrame:
    """Load history from local CSV, then Supabase, then TwelveData if needed."""

    lower_symbol = symbol.lower()
    local_candidates = [
        LOCAL_MARKET_DATA_DIR / f"market_{lower_symbol}.csv",
        cache_dir / f"market_{lower_symbol}.csv",
    ]
    attempted_sources: list[str] = []

    for candidate in local_candidates:
        attempted_sources.append(f"local_csv:{candidate}")
        if candidate.exists():
            frame = _read_market_csv(candidate)
            return frame.loc[start_date:end_date].copy()

    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"):
        attempted_sources.append("supabase")
        try:
            supabase_cls = _optional_supabase_operations()
            if supabase_cls is None:
                attempted_sources.append("supabase_import_missing")
            else:
                supabase = supabase_cls()
                rows = supabase.fetch_symbol_rows(
                    table_name=os.getenv("SUPABASE_TABLE", "daily_stock_prices"),
                    symbol=symbol,
                )
                frame = _rows_to_market_frame(rows)
                if not frame.empty:
                    _cache_market_frame(frame, symbol, cache_dir)
                    return frame.loc[start_date:end_date].copy()
        except Exception as exc:
            attempted_sources.append(f"supabase_error:{exc}")

    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if api_key:
        attempted_sources.append("twelvedata")
        twelve_data_client_cls = _optional_twelvedata_client()
        if twelve_data_client_cls is None:
            attempted_sources.append("twelvedata_import_missing")
        else:
            client = twelve_data_client_cls(api_key=api_key)
            frame = client.fetch_daily_series(
                symbol=twelvedata_symbol or symbol,
                start_date=start_date,
                end_date=end_date,
                outputsize=5000,
            )
            if not frame.empty:
                _cache_market_frame(_normalize_market_frame(frame), symbol, cache_dir)
                return _normalize_market_frame(frame).loc[start_date:end_date].copy()

    availability = describe_market_data_sources(symbol, cache_dir=cache_dir)
    availability_summary = availability.to_dict(orient="records")
    raise FileNotFoundError(
        f"Could not load history for {symbol}. "
        f"Attempted sources: {attempted_sources}. "
        f"Availability snapshot: {availability_summary}."
    )


def load_asset_universe(
    assets: Mapping[str, AssetDefinition] | None = None,
    *,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    cache_dir: Path = NOTEBOOK_MARKET_DATA_DIR,
) -> Dict[str, pd.DataFrame]:
    assets = assets or DEFAULT_MULTI_ASSET_UNIVERSE
    loaded: Dict[str, pd.DataFrame] = {}
    for asset in assets.values():
        loaded[asset.symbol] = load_market_history(
            asset.symbol,
            start_date=start_date,
            end_date=end_date,
            cache_dir=cache_dir,
            twelvedata_symbol=asset.twelvedata_symbol,
        )
    return loaded


def _rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    rolling_mean = series.rolling(window).mean()
    rolling_std = series.rolling(window).std()
    return (series - rolling_mean) / rolling_std.replace(0.0, np.nan)


def _compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    relative_strength = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100 - (100 / (1 + relative_strength))


def _compute_atr(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    prev_close = frame["Close"].shift(1)
    true_range = pd.concat(
        [
            frame["High"] - frame["Low"],
            (frame["High"] - prev_close).abs(),
            (frame["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window).mean()


def _build_asset_feature_frame(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    close = frame["Close"]
    volume = frame["Volume"].replace(0.0, np.nan)
    log_return = np.log(close).diff()

    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=26, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    sma_20 = close.rolling(20).mean()
    bollinger_std = close.rolling(20).std()
    atr_14 = _compute_atr(frame, 14)

    features = pd.DataFrame(index=frame.index)
    features[f"{prefix}_log_price"] = np.log(close)
    features[f"{prefix}_log_return_1"] = log_return
    features[f"{prefix}_log_return_5"] = np.log(close / close.shift(5))
    features[f"{prefix}_log_return_10"] = np.log(close / close.shift(10))
    features[f"{prefix}_log_return_21"] = np.log(close / close.shift(21))
    features[f"{prefix}_sma_gap_5"] = close / close.rolling(5).mean() - 1.0
    features[f"{prefix}_sma_gap_10"] = close / close.rolling(10).mean() - 1.0
    features[f"{prefix}_sma_gap_21"] = close / close.rolling(21).mean() - 1.0
    features[f"{prefix}_ema_gap_12"] = close / ema_fast - 1.0
    features[f"{prefix}_ema_gap_26"] = close / ema_slow - 1.0
    features[f"{prefix}_macd"] = macd
    features[f"{prefix}_macd_signal"] = macd_signal
    features[f"{prefix}_macd_hist"] = macd - macd_signal
    features[f"{prefix}_rsi_14"] = _compute_rsi(close, 14)
    features[f"{prefix}_bollinger_z_20"] = (close - sma_20) / bollinger_std.replace(0.0, np.nan)
    features[f"{prefix}_volatility_5"] = log_return.rolling(5).std()
    features[f"{prefix}_volatility_10"] = log_return.rolling(10).std()
    features[f"{prefix}_volatility_21"] = log_return.rolling(21).std()
    features[f"{prefix}_range_pct"] = (frame["High"] - frame["Low"]) / close
    features[f"{prefix}_open_close_gap"] = close / frame["Open"] - 1.0
    features[f"{prefix}_atr_ratio_14"] = atr_14 / close
    features[f"{prefix}_volume_change_5"] = np.log(volume / volume.shift(5))
    features[f"{prefix}_volume_z_21"] = _rolling_zscore(np.log(volume), 21)
    features[f"{prefix}_weekday"] = frame.index.weekday
    features[f"{prefix}_month"] = frame.index.month
    return features.shift(1)


def _build_single_asset_dataset(frame: pd.DataFrame, symbol: str, horizons: Sequence[int]) -> pd.DataFrame:
    prefix = symbol.lower()
    dataset = _build_asset_feature_frame(frame, prefix=prefix)
    dataset["target_close"] = frame["Close"]
    for horizon in horizons:
        dataset[f"target_return_{horizon}d"] = np.log(frame["Close"].shift(-horizon) / frame["Close"])
    return dataset


def _build_multi_asset_dataset(
    asset_frames: Mapping[str, pd.DataFrame],
    target_symbol: str,
    horizons: Sequence[int],
) -> pd.DataFrame:
    feature_frames = []
    close_frame = pd.concat({symbol: frame["Close"] for symbol, frame in asset_frames.items()}, axis=1).dropna()
    close_frame.columns = list(asset_frames.keys())

    for symbol, frame in asset_frames.items():
        feature_frames.append(_build_asset_feature_frame(frame, prefix=symbol.lower()))

    merged = pd.concat(feature_frames, axis=1, join="inner").sort_index()
    merged["target_close"] = close_frame[target_symbol].reindex(merged.index)

    target_prefix = target_symbol.lower()
    for other_symbol in asset_frames:
        if other_symbol == target_symbol:
            continue
        other_prefix = other_symbol.lower()
        ratio = merged[f"{target_prefix}_log_price"] - merged[f"{other_prefix}_log_price"]
        merged[f"{target_prefix}_vs_{other_prefix}_ratio_z20"] = _rolling_zscore(ratio, 20)
        merged[f"{target_prefix}_vs_{other_prefix}_spread_5"] = (
            merged[f"{target_prefix}_log_return_5"] - merged[f"{other_prefix}_log_return_5"]
        )
        merged[f"{target_prefix}_vs_{other_prefix}_spread_21"] = (
            merged[f"{target_prefix}_log_return_21"] - merged[f"{other_prefix}_log_return_21"]
        )

    for horizon in horizons:
        merged[f"target_return_{horizon}d"] = np.log(
            merged["target_close"].shift(-horizon) / merged["target_close"]
        )

    return merged


def _business_horizon_label(horizon: int) -> str:
    return "next_day" if horizon == 1 else f"next_{horizon}d"


def _choose_signal(predicted_log_return: float, target_std: float) -> str:
    threshold = max(target_std * 0.15, 0.0)
    if predicted_log_return > threshold:
        return "LONG"
    if predicted_log_return < -threshold:
        return "SHORT"
    return "HOLD"


def _regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    errors = y_true - y_pred
    rmse = float(np.sqrt(np.mean(np.square(errors))))
    mae = float(np.mean(np.abs(errors)))
    direction = float(np.mean(np.sign(y_true) == np.sign(y_pred)))
    correlation = float(np.corrcoef(y_true, y_pred)[0, 1]) if len(y_true) > 1 else float("nan")
    return {
        "rmse": rmse,
        "mae": mae,
        "directional_accuracy": direction,
        "correlation": correlation,
    }


def _build_tabular_model(random_state: int) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=500,
                    max_depth=6,
                    min_samples_leaf=8,
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def _build_sequences(
    features: np.ndarray,
    targets: np.ndarray,
    lookback: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sequence_features: list[np.ndarray] = []
    sequence_targets: list[float] = []
    positions: list[int] = []

    for index in range(lookback, len(features)):
        sequence_features.append(features[index - lookback : index])
        sequence_targets.append(float(targets[index]))
        positions.append(index)

    return (
        np.asarray(sequence_features, dtype=np.float32),
        np.asarray(sequence_targets, dtype=np.float32),
        np.asarray(positions, dtype=np.int64),
    )


def _standardize_features(train_features: pd.DataFrame, features: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    mean = train_features.mean()
    std = train_features.std().replace(0.0, 1.0).fillna(1.0)
    standardized = (features - mean) / std
    return standardized.fillna(0.0), mean, std


def _sequence_backtest(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    lookback: int,
    split_index: int,
    epochs: int,
    learning_rate: float,
    device: str,
    random_state: int,
) -> tuple[np.ndarray, pd.Index]:
    deep_backend = _require_deep_backend()
    train_features = features.iloc[:split_index]
    standardized, _, _ = _standardize_features(train_features, features)

    target_train = target.iloc[:split_index]
    target_mean = float(target_train.mean())
    target_std = float(target_train.std()) or 1.0
    target_scaled = ((target - target_mean) / target_std).to_numpy(dtype=np.float32)

    X_seq, y_seq, positions = _build_sequences(standardized.to_numpy(dtype=np.float32), target_scaled, lookback)
    train_mask = positions < split_index
    test_mask = positions >= split_index

    if train_mask.sum() < 10 or test_mask.sum() == 0:
        raise ValueError("Not enough observations for deep sequence training. Try a longer history.")

    model = deep_backend.train_sequence_model(
        X_seq[train_mask],
        y_seq[train_mask],
        epochs=epochs,
        learning_rate=learning_rate,
        device=device,
        random_state=random_state,
    )
    test_scaled_predictions = deep_backend.predict_sequence_model(model, X_seq[test_mask], device=device)
    test_predictions = test_scaled_predictions * target_std + target_mean
    test_index = features.index[positions[test_mask]]
    return test_predictions, test_index


def _fit_sequence_forecaster(
    features: pd.DataFrame,
    target: pd.Series,
    *,
    lookback: int,
    epochs: int,
    learning_rate: float,
    device: str,
    random_state: int,
) -> tuple[Any, pd.Series, pd.Series, float, float]:
    deep_backend = _require_deep_backend()
    standardized, feature_mean, feature_std = _standardize_features(features, features)
    target_mean = float(target.mean())
    target_std = float(target.std()) or 1.0
    target_scaled = ((target - target_mean) / target_std).to_numpy(dtype=np.float32)
    X_seq, y_seq, _ = _build_sequences(standardized.to_numpy(dtype=np.float32), target_scaled, lookback)
    if len(X_seq) < 10:
        raise ValueError("Not enough observations for deep sequence training. Try a longer history.")

    model = deep_backend.train_sequence_model(
        X_seq,
        y_seq,
        epochs=epochs,
        learning_rate=learning_rate,
        device=device,
        random_state=random_state,
    )
    return model, feature_mean, feature_std, target_mean, target_std


def _predict_latest_sequence(
    model: Any,
    all_features: pd.DataFrame,
    *,
    feature_mean: pd.Series,
    feature_std: pd.Series,
    target_mean: float,
    target_std: float,
    lookback: int,
    device: str,
) -> float:
    deep_backend = _require_deep_backend()
    standardized = ((all_features - feature_mean) / feature_std).fillna(0.0)
    latest_window = standardized.iloc[-lookback:].to_numpy(dtype=np.float32)
    prediction = deep_backend.predict_sequence_model(model, latest_window[None, :, :], device=device)[0]
    return float(prediction * target_std + target_mean)


def _forecast_payload(
    *,
    prediction: float,
    last_close: float,
    as_of_date: pd.Timestamp,
    horizon: int,
    target_std: float,
) -> Dict[str, Any]:
    simple_return = float(np.expm1(prediction))
    target_date = pd.bdate_range(as_of_date, periods=horizon + 1)[-1]
    return {
        "as_of_date": as_of_date.strftime("%Y-%m-%d"),
        "target_date": target_date.strftime("%Y-%m-%d"),
        "predicted_log_return": float(prediction),
        "predicted_simple_return": simple_return,
        "predicted_price": float(last_close * np.exp(prediction)),
        "signal": _choose_signal(prediction, target_std),
    }


def _run_experiment(
    feature_frame: pd.DataFrame,
    *,
    horizon: int,
    lookback: int,
    test_size: float,
    epochs: int,
    learning_rate: float,
    random_state: int,
    device: str,
) -> Dict[str, Any]:
    target_column = f"target_return_{horizon}d"
    all_target_columns = [column for column in feature_frame.columns if column.startswith("target_return_")]
    features = feature_frame.drop(columns=["target_close", *all_target_columns]).replace([np.inf, -np.inf], np.nan)
    supervised = features.join(feature_frame[[target_column, "target_close"]], how="inner").dropna()
    if len(supervised) < max(lookback * 3, 120):
        raise ValueError("Not enough data after feature engineering. Use a longer history window.")

    supervised_features = supervised.drop(columns=[target_column, "target_close"])
    target = supervised[target_column]
    close_values = supervised["target_close"]
    split_index = max(lookback + 10, int(len(supervised_features) * (1 - test_size)))
    if split_index >= len(supervised_features) - 5:
        split_index = len(supervised_features) - 5

    X_train = supervised_features.iloc[:split_index]
    y_train = target.iloc[:split_index]
    X_test = supervised_features.iloc[split_index:]
    y_test = target.iloc[split_index:]
    close_test = close_values.iloc[split_index:]

    technical_model = _build_tabular_model(random_state=random_state)
    technical_model.fit(X_train, y_train)
    technical_test_predictions = technical_model.predict(X_test)
    technical_metrics = _regression_metrics(y_test.to_numpy(), technical_test_predictions)
    deep_available = is_deep_model_available()
    deep_error: str | None = None

    if deep_available:
        deep_test_predictions, deep_test_index = _sequence_backtest(
            supervised_features,
            target,
            lookback=lookback,
            split_index=split_index,
            epochs=epochs,
            learning_rate=learning_rate,
            device=device,
            random_state=random_state,
        )
        aligned_y_test = y_test.loc[deep_test_index]
        deep_metrics = _regression_metrics(aligned_y_test.to_numpy(), deep_test_predictions)
    else:
        deep_test_predictions = np.asarray([], dtype=float)
        deep_test_index = pd.Index([], dtype="datetime64[ns]")
        aligned_y_test = y_test.iloc[0:0]
        deep_metrics = None
        deep_error = DEEP_MODEL_DEPENDENCY_MESSAGE

    full_technical_model = _build_tabular_model(random_state=random_state)
    full_technical_model.fit(supervised_features, target)
    latest_features = features.dropna().iloc[-1:]
    latest_close = float(feature_frame["target_close"].dropna().iloc[-1])
    latest_date = feature_frame["target_close"].dropna().index[-1]
    technical_latest_prediction = float(full_technical_model.predict(latest_features)[0])

    if deep_available:
        deep_model, feature_mean, feature_std, target_mean, target_std = _fit_sequence_forecaster(
            supervised_features,
            target,
            lookback=lookback,
            epochs=epochs,
            learning_rate=learning_rate,
            device=device,
            random_state=random_state,
        )
        latest_sequence_prediction = _predict_latest_sequence(
            deep_model,
            features.dropna(),
            feature_mean=feature_mean,
            feature_std=feature_std,
            target_mean=target_mean,
            target_std=target_std,
            lookback=lookback,
            device=device,
        )
    else:
        latest_sequence_prediction = None

    feature_names = supervised_features.columns
    feature_importance = pd.Series(
        full_technical_model.named_steps["model"].feature_importances_,
        index=feature_names,
    ).sort_values(ascending=False)

    technical_backtest = pd.DataFrame(
        {
            "actual_log_return": y_test,
            "technical_pred_log_return": technical_test_predictions,
            "current_close": close_test,
        },
        index=y_test.index,
    )
    combined_backtest = technical_backtest.copy()
    if deep_available:
        deep_backtest = pd.DataFrame(
            {
                "actual_log_return": aligned_y_test,
                "deep_pred_log_return": deep_test_predictions,
                "current_close": close_values.loc[deep_test_index],
            },
            index=deep_test_index,
        )
        combined_backtest = combined_backtest.join(
            deep_backtest[["deep_pred_log_return"]],
            how="left",
        )
    combined_backtest["actual_price"] = combined_backtest["current_close"] * np.exp(
        combined_backtest["actual_log_return"]
    )
    combined_backtest["technical_pred_price"] = combined_backtest["current_close"] * np.exp(
        combined_backtest["technical_pred_log_return"]
    )
    if deep_available:
        combined_backtest["deep_pred_price"] = combined_backtest["current_close"] * np.exp(
            combined_backtest["deep_pred_log_return"]
        )

    return {
        "horizon_days": horizon,
        "horizon_label": _business_horizon_label(horizon),
        "technical_metrics": technical_metrics,
        "deep_metrics": deep_metrics,
        "deep_available": deep_available,
        "deep_error": deep_error,
        "technical_forecast": _forecast_payload(
            prediction=technical_latest_prediction,
            last_close=latest_close,
            as_of_date=latest_date,
            horizon=horizon,
            target_std=float(target.std()),
        ),
        "deep_forecast": (
            _forecast_payload(
                prediction=latest_sequence_prediction,
                last_close=latest_close,
                as_of_date=latest_date,
                horizon=horizon,
                target_std=float(target.std()),
            )
            if deep_available and latest_sequence_prediction is not None
            else None
        ),
        "feature_importance": feature_importance,
        "backtest": combined_backtest,
    }


def compute_lead_lag_relationships(
    asset_frames: Mapping[str, pd.DataFrame],
    *,
    target_symbol: str,
    horizon: int = 1,
    max_lag: int = 5,
) -> pd.DataFrame:
    close_frame = pd.concat({symbol: frame["Close"] for symbol, frame in asset_frames.items()}, axis=1).dropna()
    close_frame.columns = list(asset_frames.keys())
    returns = np.log(close_frame).diff()
    future_target = np.log(close_frame[target_symbol].shift(-horizon) / close_frame[target_symbol])

    rows: list[dict[str, Any]] = []
    for symbol in returns.columns:
        for lag in range(max_lag + 1):
            correlation = returns[symbol].shift(lag).corr(future_target)
            rows.append(
                {
                    "asset": symbol,
                    "lag_days": lag,
                    "corr_with_target_forward_return": correlation,
                }
            )

    return pd.DataFrame(rows).sort_values(
        ["corr_with_target_forward_return", "lag_days"],
        ascending=[False, True],
    )


def run_single_asset_experiment(
    *,
    asset: AssetDefinition | None = None,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    horizons: Sequence[int] = (1, TRADING_DAYS_PER_MONTH),
    lookback: int = 60,
    test_size: float = 0.2,
    epochs: int = 35,
    learning_rate: float = 1e-3,
    random_state: int = 42,
    device: str | None = None,
) -> Dict[int, Dict[str, Any]]:
    asset = asset or DEFAULT_SINGLE_ASSET
    device = device or _default_device()

    frame = load_market_history(
        asset.symbol,
        start_date=start_date,
        end_date=end_date,
        twelvedata_symbol=asset.twelvedata_symbol,
    )
    dataset = _build_single_asset_dataset(frame, symbol=asset.symbol, horizons=horizons)

    return {
        horizon: _run_experiment(
            dataset,
            horizon=horizon,
            lookback=lookback,
            test_size=test_size,
            epochs=epochs,
            learning_rate=learning_rate,
            random_state=random_state,
            device=device,
        )
        for horizon in horizons
    }


def run_multi_asset_experiment(
    *,
    assets: Mapping[str, AssetDefinition] | None = None,
    target_symbol: str = "NVDA",
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    horizons: Sequence[int] = (1, TRADING_DAYS_PER_MONTH),
    lookback: int = 60,
    test_size: float = 0.2,
    epochs: int = 35,
    learning_rate: float = 1e-3,
    random_state: int = 42,
    device: str | None = None,
) -> tuple[Dict[int, Dict[str, Any]], Dict[str, pd.DataFrame]]:
    assets = assets or DEFAULT_MULTI_ASSET_UNIVERSE
    device = device or _default_device()
    asset_frames = load_asset_universe(
        assets,
        start_date=start_date,
        end_date=end_date,
    )
    dataset = _build_multi_asset_dataset(asset_frames, target_symbol=target_symbol, horizons=horizons)

    results = {
        horizon: _run_experiment(
            dataset,
            horizon=horizon,
            lookback=lookback,
            test_size=test_size,
            epochs=epochs,
            learning_rate=learning_rate,
            random_state=random_state,
            device=device,
        )
        for horizon in horizons
    }
    return results, asset_frames


def summarize_experiment_results(results: Mapping[int, Mapping[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for horizon, payload in results.items():
        for model_name in ("technical", "deep"):
            metrics = payload[f"{model_name}_metrics"]
            forecast = payload[f"{model_name}_forecast"]
            if metrics is None or forecast is None:
                continue
            rows.append(
                {
                    "horizon_days": horizon,
                    "model": model_name,
                    "rmse": metrics["rmse"],
                    "mae": metrics["mae"],
                    "directional_accuracy": metrics["directional_accuracy"],
                    "correlation": metrics["correlation"],
                    "latest_signal": forecast["signal"],
                    "latest_predicted_return": forecast["predicted_simple_return"],
                    "latest_predicted_price": forecast["predicted_price"],
                }
            )
    return pd.DataFrame(rows).sort_values(["horizon_days", "model"]).reset_index(drop=True)
