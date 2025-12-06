"""Volatility Analysis Tools - GARCH, Realized Volatility, Forecasting.

Provides advanced volatility estimation and forecasting capabilities.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from datetime import datetime


@dataclass
class VolatilityMetrics:
    """Volatility analysis results."""
    timestamp: datetime
    symbol: str
    timeframe: str
    realized_volatility: float  # Historical volatility
    parkinson_volatility: float  # High-low based
    garman_klass_volatility: float  # OHLC based
    rogers_satchell_volatility: float  # OHLC based
    garch_estimate: float  # GARCH(1,1) estimate
    garch_forecast_1h: float  # 1-hour ahead forecast
    garch_forecast_1d: float  # 1-day ahead forecast
    volatility_trend: str  # "increasing", "stable", "decreasing"
    percentile_rank: float  # 0-100, where 100 = highest vol
    details: Dict[str, Any] = None


class VolatilityAnalyzer:
    """Comprehensive volatility analysis."""

    @staticmethod
    def realized_volatility(
        returns: List[float],
        period: int = 20
    ) -> float:
        """
        Calculate realized volatility (historical standard deviation).

        Args:
            returns: List of log returns
            period: Lookback period

        Returns:
            Realized volatility (annualized)
        """
        if len(returns) < period:
            return 0.0

        recent_returns = returns[-period:]
        daily_vol = np.std(recent_returns)
        annual_vol = daily_vol * np.sqrt(252)  # Annualize

        return float(annual_vol)

    @staticmethod
    def parkinson_volatility(
        highs: List[float],
        lows: List[float],
        period: int = 20
    ) -> float:
        """
        Calculate Parkinson volatility (uses high-low).

        More efficient than close-based volatility.

        Args:
            highs: List of high prices
            lows: List of low prices
            period: Lookback period

        Returns:
            Parkinson volatility (annualized)
        """
        if len(highs) < period or len(lows) < period:
            return 0.0

        recent_highs = highs[-period:]
        recent_lows = lows[-period:]

        hl_ratio = np.log(np.array(recent_highs) / np.array(recent_lows))
        parkinson = np.sqrt(np.mean(hl_ratio ** 2) / (4 * np.log(2)))
        annual_vol = parkinson * np.sqrt(252)

        return float(annual_vol)

    @staticmethod
    def garman_klass_volatility(
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 20
    ) -> float:
        """
        Calculate Garman-Klass volatility (uses OHLC).

        More efficient than close-only, less dependent on gaps.

        Args:
            opens: Open prices
            highs: High prices
            lows: Low prices
            closes: Close prices
            period: Lookback period

        Returns:
            Garman-Klass volatility (annualized)
        """
        if len(closes) < period:
            return 0.0

        o = np.array(opens[-period:])
        h = np.array(highs[-period:])
        l = np.array(lows[-period:])
        c = np.array(closes[-period:])

        # Garman-Klass formula
        hl = np.log(h / l)
        co = np.log(c / o)

        gk = 0.5 * np.mean(hl ** 2) - (2 * np.log(2) - 1) * np.mean(co ** 2)
        gk_vol = np.sqrt(np.abs(gk)) * np.sqrt(252)

        return float(gk_vol)

    @staticmethod
    def rogers_satchell_volatility(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int = 20
    ) -> float:
        """
        Calculate Rogers-Satchell volatility (drift-independent).

        Uses high-low-close, doesn't assume zero drift.

        Args:
            highs: High prices
            lows: Low prices
            closes: Close prices
            period: Lookback period

        Returns:
            Rogers-Satchell volatility (annualized)
        """
        if len(closes) < period:
            return 0.0

        h = np.array(highs[-period:])
        l = np.array(lows[-period:])
        c = np.array(closes[-period:])

        hc = np.log(h / c)
        lc = np.log(l / c)

        rs = np.sqrt(np.mean(hc * lc))
        rs_vol = rs * np.sqrt(252)

        return float(rs_vol)

    @staticmethod
    def garch_volatility(
        returns: List[float],
        p: int = 1,
        q: int = 1,
        forecast_horizon: int = 1
    ) -> Tuple[float, List[float]]:
        """
        Estimate GARCH(p,q) volatility.

        Simple GARCH(1,1) implementation without heavy dependencies.

        Args:
            returns: Log returns
            p: AR order
            q: MA order
            forecast_horizon: Steps ahead to forecast

        Returns:
            Tuple of (current_volatility, forecast_path)
        """
        if len(returns) < 20:
            return 0.0, [0.0] * forecast_horizon

        # GARCH(1,1) parameters (typical values)
        omega = 0.0001  # Constant
        alpha = 0.05   # Shock term weight
        beta = 0.94    # Persistence

        # Calculate conditional variance
        returns_array = np.array(returns)
        variances = []

        # Initial variance
        current_var = np.var(returns_array)

        for ret in returns_array[-252:]:  # Last year of data
            current_var = omega + alpha * (ret ** 2) + beta * current_var
            variances.append(current_var)

        # Current volatility estimate
        current_vol = float(np.sqrt(current_var) * np.sqrt(252))

        # Forecast volatility path (mean reversion to long-run vol)
        long_run_var = omega / (1 - alpha - beta) if (1 - alpha - beta) > 0 else current_var
        forecast_path = []

        forecast_var = current_var
        for h in range(forecast_horizon):
            # Mean revert
            forecast_var = long_run_var + (alpha + beta) * (forecast_var - long_run_var)
            forecast_vol = float(np.sqrt(forecast_var) * np.sqrt(252))
            forecast_path.append(forecast_vol)

        return current_vol, forecast_path

    @staticmethod
    def analyze_symbol(
        symbol: str,
        timeframe: str,
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float],
        historical_volatilities: Optional[List[float]] = None
    ) -> VolatilityMetrics:
        """
        Comprehensive volatility analysis for a symbol.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (daily, weekly, monthly)
            opens: Open prices
            highs: High prices
            lows: Low prices
            closes: Close prices
            volumes: Volumes
            historical_volatilities: Previous vol readings for ranking

        Returns:
            VolatilityMetrics with all analysis
        """
        # Calculate returns
        log_returns = np.log(np.array(closes[1:]) / np.array(closes[:-1])).tolist()

        # Calculate different volatility measures
        realized_vol = VolatilityAnalyzer.realized_volatility(log_returns)
        parkinson_vol = VolatilityAnalyzer.parkinson_volatility(highs, lows)
        gk_vol = VolatilityAnalyzer.garman_klass_volatility(opens, highs, lows, closes)
        rs_vol = VolatilityAnalyzer.rogers_satchell_volatility(highs, lows, closes)

        # GARCH forecast
        garch_vol, garch_forecast = VolatilityAnalyzer.garch_volatility(
            log_returns, forecast_horizon=2
        )

        # Determine trend
        if len(log_returns) >= 20:
            recent_vol = VolatilityAnalyzer.realized_volatility(log_returns[-10:])
            prev_vol = VolatilityAnalyzer.realized_volatility(log_returns[-20:-10])

            if recent_vol > prev_vol * 1.1:
                vol_trend = "increasing"
            elif recent_vol < prev_vol * 0.9:
                vol_trend = "decreasing"
            else:
                vol_trend = "stable"
        else:
            vol_trend = "stable"

        # Calculate percentile rank
        if historical_volatilities:
            all_vols = historical_volatilities + [realized_vol]
            percentile = (len([v for v in all_vols if v < realized_vol]) / len(all_vols)) * 100
        else:
            percentile = 50.0

        return VolatilityMetrics(
            timestamp=datetime.utcnow(),
            symbol=symbol,
            timeframe=timeframe,
            realized_volatility=realized_vol,
            parkinson_volatility=parkinson_vol,
            garman_klass_volatility=gk_vol,
            rogers_satchell_volatility=rs_vol,
            garch_estimate=garch_vol,
            garch_forecast_1h=garch_forecast[0] if garch_forecast else 0,
            garch_forecast_1d=garch_forecast[1] if len(garch_forecast) > 1 else 0,
            volatility_trend=vol_trend,
            percentile_rank=percentile,
            details={
                "log_returns_mean": float(np.mean(log_returns)),
                "log_returns_std": float(np.std(log_returns)),
                "skewness": float(np.mean([(r - np.mean(log_returns))**3 for r in log_returns]) / (np.std(log_returns)**3)) if np.std(log_returns) > 0 else 0,
                "kurtosis": float(np.mean([(r - np.mean(log_returns))**4 for r in log_returns]) / (np.std(log_returns)**4)) if np.std(log_returns) > 0 else 0,
                "max_return": float(np.max(log_returns)),
                "min_return": float(np.min(log_returns)),
            }
        )

    @staticmethod
    def volatility_signal(metrics: VolatilityMetrics) -> Dict[str, Any]:
        """Generate trading signal from volatility metrics."""
        signals = []
        confidence = 50

        # High volatility regime
        if metrics.percentile_rank > 75:
            signals.append("HIGH_VOLATILITY_REGIME")
            confidence += 15

        # Volatility expansion
        if metrics.volatility_trend == "increasing":
            signals.append("VOLATILITY_EXPANDING")
            confidence += 10

        # Low volatility (breakout coming?)
        if metrics.percentile_rank < 25:
            signals.append("LOW_VOLATILITY_REGIME")
            signals.append("BREAKOUT_POTENTIAL")
            confidence += 15

        # GARCH forecast rising
        if metrics.garch_forecast_1d > metrics.garch_estimate * 1.05:
            signals.append("VOL_FORECAST_RISING")
            confidence += 10

        return {
            "signals": signals,
            "confidence": min(100, confidence),
            "recommendation": "REDUCE_SIZE" if metrics.percentile_rank > 75 else "NORMAL" if metrics.percentile_rank > 25 else "PREPARE_BREAKOUT"
        }
