"""Time Series Data Preparation for TimesFM and PatchTST Models.

Prepares market data (OHLCV + ATR/ADR + sessions) into format required by:
- TimesFM: Google's time series foundation model
- PatchTST: Patch-based transformer for time series forecasting

Handles:
- Feature engineering and normalization
- Multi-variate time series windows
- Session encoding (AM/PM, midnight, London, NYSE, etc.)
- Multi-timeframe data (daily, weekly, monthly)
- Scaling and preprocessing
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from datetime import datetime


@dataclass
class TimeSeriesWindow:
    """A prepared time series window ready for model input."""
    symbol: str
    timeframe: str
    timestamp: datetime
    sequence: np.ndarray  # Shape: (window_length, num_features)
    features: List[str]  # Names of features in order
    target: Optional[float] = None  # For supervised learning
    metadata: Dict[str, Any] = None

    @property
    def shape(self) -> Tuple[int, int]:
        """Return shape of sequence."""
        return self.sequence.shape

    @property
    def is_multivariate(self) -> bool:
        """Check if multivariate (multiple features)."""
        return self.sequence.shape[1] > 1


class TimeSeriesPreprocessor:
    """Preprocesses market data for time series models."""

    # Standard features order for consistency
    STANDARD_FEATURES = [
        "open", "high", "low", "close", "volume",
        "atr", "adr",
        "session_code",  # 0=midnight, 1=london, 2=nyse, 3=pm, 4=close
    ]

    def __init__(
        self,
        normalization: str = "minmax",  # "minmax", "zscore", "none"
        feature_list: Optional[List[str]] = None,
        window_length: int = 512,  # TimesFM default context length
    ):
        """
        Initialize preprocessor.

        Args:
            normalization: Type of scaling to apply
            feature_list: Features to include (None = use standard)
            window_length: Length of context window for model input
        """
        self.normalization = normalization
        self.features = feature_list or self.STANDARD_FEATURES
        self.window_length = window_length
        self.scalers: Dict[str, Dict[str, float]] = {}  # Per-symbol scaling params

    def _calculate_scaling_params(
        self,
        data: np.ndarray,
        feature_idx: int,
        symbol: str
    ) -> Dict[str, float]:
        """Calculate scaling parameters for a feature."""
        feature_data = data[:, feature_idx]

        if self.normalization == "minmax":
            min_val = float(np.min(feature_data))
            max_val = float(np.max(feature_data))
            return {
                "min": min_val,
                "max": max_val,
                "range": max_val - min_val
            }
        elif self.normalization == "zscore":
            mean = float(np.mean(feature_data))
            std = float(np.std(feature_data))
            return {
                "mean": mean,
                "std": std if std > 0 else 1.0
            }
        else:
            return {}

    def _normalize_feature(
        self,
        data: np.ndarray,
        feature_idx: int,
        symbol: str,
        fit: bool = False
    ) -> np.ndarray:
        """Normalize a single feature."""
        if self.normalization == "none":
            return data

        key = f"{symbol}_{self.features[feature_idx]}"

        if fit:
            params = self._calculate_scaling_params(data, feature_idx, symbol)
            self.scalers[key] = params
        else:
            params = self.scalers.get(key, {})

        feature_data = data[:, feature_idx].copy()

        if self.normalization == "minmax" and params:
            if params["range"] > 0:
                feature_data = (feature_data - params["min"]) / params["range"]
            else:
                feature_data = np.zeros_like(feature_data)

        elif self.normalization == "zscore" and params:
            feature_data = (feature_data - params["mean"]) / params["std"]

        data[:, feature_idx] = feature_data
        return data

    def prepare_ohlcv_window(
        self,
        symbol: str,
        ohlcv_data: List[Dict[str, Any]],
        atr_values: List[float],
        adr_values: List[float],
        session_codes: List[int],
        normalize: bool = True,
        fit_scalers: bool = False
    ) -> TimeSeriesWindow:
        """
        Prepare OHLCV data into a time series window.

        Args:
            symbol: Trading symbol
            ohlcv_data: List of dicts with "open", "high", "low", "close", "volume"
            atr_values: ATR values (one per bar)
            adr_values: ADR values (one per bar)
            session_codes: Session encoding (0-4 for 5 sessions)
            normalize: Whether to normalize features
            fit_scalers: Whether to fit new scalers (training) or use existing

        Returns:
            TimeSeriesWindow ready for model
        """
        if len(ohlcv_data) < self.window_length:
            raise ValueError(
                f"Need at least {self.window_length} bars, got {len(ohlcv_data)}"
            )

        # Extract last window_length bars
        window_data = ohlcv_data[-self.window_length:]
        window_atr = atr_values[-self.window_length:]
        window_adr = adr_values[-self.window_length:]
        window_sessions = session_codes[-self.window_length:]

        # Build feature matrix
        num_bars = len(window_data)
        num_features = len(self.features)
        matrix = np.zeros((num_bars, num_features), dtype=np.float32)

        for i, bar in enumerate(window_data):
            matrix[i, 0] = bar.get("open", 0)
            matrix[i, 1] = bar.get("high", 0)
            matrix[i, 2] = bar.get("low", 0)
            matrix[i, 3] = bar.get("close", 0)
            matrix[i, 4] = bar.get("volume", 0)
            matrix[i, 5] = window_atr[i]
            matrix[i, 6] = window_adr[i]
            matrix[i, 7] = window_sessions[i]

        # Normalize if requested
        if normalize:
            for feat_idx in range(num_features):
                matrix = self._normalize_feature(
                    matrix, feat_idx, symbol, fit=fit_scalers
                )

        timestamp = window_data[-1].get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return TimeSeriesWindow(
            symbol=symbol,
            timeframe="daily",
            timestamp=timestamp,
            sequence=matrix,
            features=self.features,
            metadata={
                "bars_in_window": num_bars,
                "last_close": float(window_data[-1]["close"]),
                "last_high": float(max(b["high"] for b in window_data)),
                "last_low": float(min(b["low"] for b in window_data)),
            }
        )

    def prepare_univariate_window(
        self,
        symbol: str,
        prices: List[float],
        normalize: bool = True,
        fit_scalers: bool = False
    ) -> TimeSeriesWindow:
        """
        Prepare univariate (single feature) time series window.

        Args:
            symbol: Trading symbol
            prices: List of prices (e.g., just closing prices)
            normalize: Whether to normalize
            fit_scalers: Whether to fit scalers

        Returns:
            TimeSeriesWindow with shape (window_length, 1)
        """
        if len(prices) < self.window_length:
            raise ValueError(
                f"Need at least {self.window_length} prices, got {len(prices)}"
            )

        # Get last window
        window_prices = np.array(prices[-self.window_length:], dtype=np.float32)
        matrix = window_prices.reshape(-1, 1)

        # Normalize
        if normalize:
            matrix = self._normalize_feature(
                matrix, 0, symbol, fit=fit_scalers
            )

        return TimeSeriesWindow(
            symbol=symbol,
            timeframe="daily",
            timestamp=datetime.utcnow(),
            sequence=matrix,
            features=["price"],
            metadata={"window_length": self.window_length}
        )

    def prepare_multiframe_window(
        self,
        symbol: str,
        daily_data: List[Dict[str, Any]],
        weekly_data: List[Dict[str, Any]],
        daily_atr: List[float],
        daily_adr: List[float],
        daily_sessions: List[int],
        normalize: bool = True
    ) -> Dict[str, TimeSeriesWindow]:
        """
        Prepare multi-timeframe data (daily + weekly).

        Args:
            symbol: Trading symbol
            daily_data: Daily OHLCV
            weekly_data: Weekly OHLCV
            daily_atr: Daily ATR values
            daily_adr: Daily ADR values
            daily_sessions: Session codes
            normalize: Whether to normalize

        Returns:
            Dict with "daily" and "weekly" TimeSeriesWindows
        """
        windows = {}

        # Daily window
        windows["daily"] = self.prepare_ohlcv_window(
            symbol, daily_data, daily_atr, daily_adr, daily_sessions,
            normalize=normalize, fit_scalers=True
        )

        # Weekly window (use same window_length but with weekly data)
        if len(weekly_data) >= self.window_length:
            # Pad weekly sessions with default value
            weekly_sessions = [2] * len(weekly_data)  # 2 = NYSE
            weekly_atr = [0.0] * len(weekly_data)  # Placeholder
            weekly_adr = [0.0] * len(weekly_data)  # Placeholder

            windows["weekly"] = self.prepare_ohlcv_window(
                symbol, weekly_data, weekly_atr, weekly_adr, weekly_sessions,
                normalize=normalize, fit_scalers=False
            )
            windows["weekly"].timeframe = "weekly"

        return windows


class TimeSeriesDataPipeline:
    """End-to-end pipeline for preparing data for forecasting models."""

    def __init__(
        self,
        window_length: int = 512,
        normalization: str = "minmax",
        batch_size: int = 32
    ):
        """
        Initialize pipeline.

        Args:
            window_length: Context length for models
            normalization: Scaling method
            batch_size: Batch size for processing
        """
        self.preprocessor = TimeSeriesPreprocessor(
            normalization=normalization,
            window_length=window_length
        )
        self.batch_size = batch_size
        self.windows: Dict[str, List[TimeSeriesWindow]] = {}

    def add_daily_data(
        self,
        symbol: str,
        ohlcv_data: List[Dict[str, Any]],
        atr_values: List[float],
        adr_values: List[float],
        session_codes: List[int],
        normalize: bool = True
    ) -> TimeSeriesWindow:
        """Add daily data to pipeline."""
        window = self.preprocessor.prepare_ohlcv_window(
            symbol, ohlcv_data, atr_values, adr_values, session_codes,
            normalize=normalize, fit_scalers=True
        )

        if symbol not in self.windows:
            self.windows[symbol] = []
        self.windows[symbol].append(window)

        return window

    def get_batch_for_model(
        self,
        symbol: str,
        model_type: str = "timesfm"  # "timesfm" or "patchtst"
    ) -> Dict[str, Any]:
        """
        Get batch ready for model API call.

        Args:
            symbol: Which symbol to get
            model_type: Type of model for format adjustments

        Returns:
            Dict with "input_sequence" and metadata for API call
        """
        if symbol not in self.windows or not self.windows[symbol]:
            raise ValueError(f"No data for symbol {symbol}")

        window = self.windows[symbol][-1]  # Get most recent

        # Convert to list format for JSON serialization
        input_sequence = window.sequence.tolist()

        payload = {
            "input_sequence": input_sequence,
            "features": window.features,
            "symbol": symbol,
            "timeframe": window.timeframe,
            "timestamp": window.timestamp.isoformat(),
        }

        # Model-specific adjustments
        if model_type == "timesfm":
            payload["prediction_length"] = 96  # 96 steps ahead
            payload["freq"] = "1h"
        elif model_type == "patchtst":
            payload["pred_len"] = 96
            payload["enc_in"] = window.shape[1]  # Number of features

        return payload

    def get_all_windows(self) -> Dict[str, List[TimeSeriesWindow]]:
        """Get all prepared windows."""
        return self.windows

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics on prepared data."""
        total_symbols = len(self.windows)
        total_windows = sum(len(w) for w in self.windows.values())

        return {
            "total_symbols": total_symbols,
            "total_windows": total_windows,
            "batch_size": self.batch_size,
            "symbols": list(self.windows.keys()),
            "window_length": self.preprocessor.window_length,
            "normalization": self.preprocessor.normalization,
        }


def encode_session(session_type: str) -> int:
    """Encode session type to integer code."""
    session_map = {
        "midnight_open": 0,
        "london_open": 1,
        "nyse_open": 2,
        "us_pm_session": 3,
        "london_close": 4,
    }
    return session_map.get(session_type, 2)  # Default to NYSE


def encode_am_pm(hour: int) -> int:
    """Encode hour to AM(0) or PM(1)."""
    return 0 if hour < 12 else 1
