"""Technical indicators for volume and price analysis.

This module provides calculations for:
- VWAP (Volume Weighted Average Price)
- TWAP (Time Weighted Average Price)
- OBV (On-Balance Volume)
- ATR (Average True Range)
- ADR (Average Daily Range)
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class OHLCV:
    """Open, High, Low, Close, Volume data point."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class IndicatorResult:
    """Result from technical indicator calculation."""
    symbol: str
    indicator_name: str
    timestamp: datetime
    value: float
    signal: str  # "bullish", "bearish", "neutral"
    strength: float  # 0-100, confidence level
    details: Dict[str, Any]


class TechnicalIndicators:
    """Technical indicators calculator for trading analysis."""

    @staticmethod
    def calculate_vwap(
        data: List[OHLCV],
        period: int = 14
    ) -> IndicatorResult:
        """
        Calculate Volume Weighted Average Price (VWAP).

        VWAP = Cumulative(Price × Volume) / Cumulative(Volume)
        Uses typical price = (High + Low + Close) / 3

        Args:
            data: List of OHLCV data points
            period: Not used for VWAP (uses all data), kept for consistency

        Returns:
            IndicatorResult with VWAP value and signal
        """
        if not data or len(data) < 1:
            raise ValueError("VWAP requires at least 1 data point")

        cumulative_pv = 0.0  # Cumulative price × volume
        cumulative_v = 0.0   # Cumulative volume

        for ohlcv in data:
            typical_price = (ohlcv.high + ohlcv.low + ohlcv.close) / 3
            cumulative_pv += typical_price * ohlcv.volume
            cumulative_v += ohlcv.volume

        vwap = cumulative_pv / cumulative_v if cumulative_v > 0 else data[-1].close

        # Signal generation: compare current price to VWAP
        current_price = data[-1].close
        if current_price > vwap * 1.002:  # 0.2% above VWAP
            signal = "bullish"
            strength = min(100, ((current_price - vwap) / vwap) * 1000)
        elif current_price < vwap * 0.998:  # 0.2% below VWAP
            signal = "bearish"
            strength = min(100, ((vwap - current_price) / vwap) * 1000)
        else:
            signal = "neutral"
            strength = 50

        return IndicatorResult(
            symbol="",
            indicator_name="VWAP",
            timestamp=data[-1].timestamp,
            value=vwap,
            signal=signal,
            strength=strength,
            details={
                "cumulative_volume": cumulative_v,
                "current_price": current_price,
                "deviation_pct": ((current_price - vwap) / vwap) * 100,
                "data_points": len(data)
            }
        )

    @staticmethod
    def calculate_twap(
        data: List[OHLCV],
        period: int = 14
    ) -> IndicatorResult:
        """
        Calculate Time Weighted Average Price (TWAP).

        TWAP = Sum(Price × Time Weight) / Sum(Time Weight)
        Recent prices weighted more heavily.

        Args:
            data: List of OHLCV data points
            period: Number of periods to use (default 14)

        Returns:
            IndicatorResult with TWAP value and signal
        """
        if not data:
            raise ValueError("TWAP requires at least 1 data point")

        # Use most recent 'period' candles
        data_to_use = data[-period:] if len(data) >= period else data

        weighted_sum = 0.0
        weight_sum = 0.0

        # Assign increasing weights to more recent bars
        for i, ohlcv in enumerate(data_to_use):
            weight = (i + 1) / len(data_to_use)  # Linear increasing weight
            typical_price = (ohlcv.high + ohlcv.low + ohlcv.close) / 3
            weighted_sum += typical_price * weight
            weight_sum += weight

        twap = weighted_sum / weight_sum if weight_sum > 0 else data[-1].close

        # Signal generation
        current_price = data[-1].close
        if current_price > twap * 1.002:
            signal = "bullish"
            strength = min(100, ((current_price - twap) / twap) * 1000)
        elif current_price < twap * 0.998:
            signal = "bearish"
            strength = min(100, ((twap - current_price) / twap) * 1000)
        else:
            signal = "neutral"
            strength = 50

        return IndicatorResult(
            symbol="",
            indicator_name="TWAP",
            timestamp=data[-1].timestamp,
            value=twap,
            signal=signal,
            strength=strength,
            details={
                "current_price": current_price,
                "period": len(data_to_use),
                "deviation_pct": ((current_price - twap) / twap) * 100,
                "trend": "up" if twap > data[0].close else "down"
            }
        )

    @staticmethod
    def calculate_obv(
        data: List[OHLCV],
        period: int = 14
    ) -> IndicatorResult:
        """
        Calculate On-Balance Volume (OBV).

        OBV = Previous OBV + (Volume if Close > Previous Close,
                              -Volume if Close < Previous Close,
                              0 if Close == Previous Close)

        OBV measures accumulation/distribution with volume as conviction indicator.

        Args:
            data: List of OHLCV data points
            period: Number of periods to use for signal (default 14)

        Returns:
            IndicatorResult with OBV value and signal
        """
        if not data or len(data) < 2:
            raise ValueError("OBV requires at least 2 data points")

        obv = 0.0
        obv_values = []

        # Calculate OBV line
        for i, ohlcv in enumerate(data):
            if i == 0:
                # First OBV starts at 0 or could start at volume
                obv = ohlcv.volume
            else:
                prev_close = data[i-1].close
                if ohlcv.close > prev_close:
                    obv += ohlcv.volume
                elif ohlcv.close < prev_close:
                    obv -= ohlcv.volume
                # If close == prev_close, no change to OBV

            obv_values.append(obv)

        current_obv = obv_values[-1]

        # Calculate OBV trend
        if len(obv_values) > period:
            obv_ma = sum(obv_values[-period:]) / period
            if current_obv > obv_ma:
                signal = "bullish"
                strength = min(100, ((current_obv - obv_ma) / abs(obv_ma)) * 100) if obv_ma != 0 else 50
            elif current_obv < obv_ma:
                signal = "bearish"
                strength = min(100, ((obv_ma - current_obv) / abs(obv_ma)) * 100) if obv_ma != 0 else 50
            else:
                signal = "neutral"
                strength = 50
        else:
            # Not enough data for MA comparison
            if current_obv > 0:
                signal = "bullish"
                strength = 50
            elif current_obv < 0:
                signal = "bearish"
                strength = 50
            else:
                signal = "neutral"
                strength = 50

        return IndicatorResult(
            symbol="",
            indicator_name="OBV",
            timestamp=data[-1].timestamp,
            value=current_obv,
            signal=signal,
            strength=strength,
            details={
                "obv_ma": sum(obv_values[-period:]) / period if len(obv_values) >= period else 0,
                "obv_trend": "up" if obv_values[-1] > obv_values[0] else "down",
                "volume_accumulation": "positive" if current_obv > 0 else "negative",
                "divergence_check": "compare with price trend"
            }
        )

    @staticmethod
    def calculate_atr(
        data: List[OHLCV],
        period: int = 14
    ) -> IndicatorResult:
        """
        Calculate Average True Range (ATR).

        True Range = max(High - Low,
                        abs(High - Previous Close),
                        abs(Low - Previous Close))
        ATR = SMA of True Range over period

        ATR measures volatility (not direction).

        Args:
            data: List of OHLCV data points (at least period + 1)
            period: Averaging period (default 14)

        Returns:
            IndicatorResult with ATR value and volatility signal
        """
        if not data or len(data) < period + 1:
            raise ValueError(f"ATR requires at least {period + 1} data points")

        true_ranges = []

        for i, ohlcv in enumerate(data):
            if i == 0:
                # For first bar, TR = High - Low
                tr = ohlcv.high - ohlcv.low
            else:
                prev_close = data[i-1].close
                high_low = ohlcv.high - ohlcv.low
                high_prev = abs(ohlcv.high - prev_close)
                low_prev = abs(ohlcv.low - prev_close)
                tr = max(high_low, high_prev, low_prev)

            true_ranges.append(tr)

        # Calculate ATR as SMA of true range
        atr = sum(true_ranges[-period:]) / period if len(true_ranges) >= period else 0

        # Compare current ATR to previous ATR for trend
        if len(true_ranges) >= period * 2:
            prev_atr = sum(true_ranges[-period*2:-period]) / period
            if atr > prev_atr * 1.1:
                signal = "increasing_volatility"
                strength = min(100, ((atr - prev_atr) / prev_atr) * 100)
            elif atr < prev_atr * 0.9:
                signal = "decreasing_volatility"
                strength = min(100, ((prev_atr - atr) / prev_atr) * 100)
            else:
                signal = "stable_volatility"
                strength = 50
        else:
            signal = "neutral"
            strength = 50

        current_price = data[-1].close
        atr_pct = (atr / current_price) * 100 if current_price > 0 else 0

        return IndicatorResult(
            symbol="",
            indicator_name="ATR",
            timestamp=data[-1].timestamp,
            value=atr,
            signal=signal,
            strength=strength,
            details={
                "atr_percent": atr_pct,
                "current_true_range": true_ranges[-1],
                "volatility_level": "high" if atr_pct > 2.5 else "medium" if atr_pct > 1.5 else "low",
                "period": period
            }
        )

    @staticmethod
    def calculate_adr(
        data: List[OHLCV],
        days: int = 5
    ) -> IndicatorResult:
        """
        Calculate Average Daily Range (ADR).

        ADR = Average of (High - Low) over last N days

        Useful for setting stop losses and take profits.

        Args:
            data: List of OHLCV data points (at least 'days' points)
            days: Number of days to average (default 5)

        Returns:
            IndicatorResult with ADR value and range signal
        """
        if not data or len(data) < days:
            raise ValueError(f"ADR requires at least {days} data points")

        # Get last 'days' periods
        recent_data = data[-days:]

        daily_ranges = []
        for ohlcv in recent_data:
            daily_range = ohlcv.high - ohlcv.low
            daily_ranges.append(daily_range)

        adr = sum(daily_ranges) / len(daily_ranges)

        # Compare current day range to ADR
        current_range = data[-1].high - data[-1].low

        if current_range > adr * 1.2:
            signal = "wide_range"
            strength = min(100, ((current_range - adr) / adr) * 100)
        elif current_range < adr * 0.8:
            signal = "narrow_range"
            strength = min(100, ((adr - current_range) / adr) * 100)
        else:
            signal = "typical_range"
            strength = 50

        current_price = data[-1].close
        adr_pct = (adr / current_price) * 100 if current_price > 0 else 0

        return IndicatorResult(
            symbol="",
            indicator_name="ADR",
            timestamp=data[-1].timestamp,
            value=adr,
            signal=signal,
            strength=strength,
            details={
                "adr_percent": adr_pct,
                "current_range": current_range,
                "range_expansion": "yes" if current_range > adr else "no",
                "days_analyzed": days,
                "typical_stop_distance": adr * 0.5
            }
        )

    @staticmethod
    def calculate_volume_profile(
        data: List[OHLCV],
        period: int = 20
    ) -> Dict[str, Any]:
        """
        Calculate volume profile metrics for recent period.

        Args:
            data: List of OHLCV data points
            period: Number of periods to analyze

        Returns:
            Dictionary with volume profile metrics
        """
        if not data or len(data) < period:
            raise ValueError(f"Volume profile requires at least {period} data points")

        recent_data = data[-period:]

        volumes = [ohlcv.volume for ohlcv in recent_data]
        prices = [ohlcv.close for ohlcv in recent_data]

        total_volume = sum(volumes)
        avg_volume = total_volume / len(volumes)
        max_volume = max(volumes)
        min_volume = min(volumes)

        # Volume trend
        first_half_vol = sum(volumes[:len(volumes)//2])
        second_half_vol = sum(volumes[len(volumes)//2:])
        volume_trend = "increasing" if second_half_vol > first_half_vol else "decreasing"

        # Price and volume correlation (simple check)
        price_trend = "up" if prices[-1] > prices[0] else "down"

        return {
            "period": period,
            "total_volume": total_volume,
            "average_volume": avg_volume,
            "max_volume": max_volume,
            "min_volume": min_volume,
            "volume_trend": volume_trend,
            "price_trend": price_trend,
            "vol_price_agreement": "yes" if (
                (volume_trend == "increasing" and price_trend == "up") or
                (volume_trend == "decreasing" and price_trend == "down")
            ) else "no"
        }

    @staticmethod
    def generate_combined_signal(
        symbol: str,
        vwap_result: IndicatorResult,
        twap_result: IndicatorResult,
        obv_result: IndicatorResult,
        atr_result: IndicatorResult,
        adr_result: IndicatorResult
    ) -> Dict[str, Any]:
        """
        Generate combined signal from all technical indicators.

        Args:
            symbol: Trading symbol
            vwap_result: VWAP indicator result
            twap_result: TWAP indicator result
            obv_result: OBV indicator result
            atr_result: ATR indicator result
            adr_result: ADR indicator result

        Returns:
            Combined signal dictionary
        """
        # Score each indicator
        scores = {
            "vwap": 100 if vwap_result.signal == "bullish" else 0 if vwap_result.signal == "bearish" else 50,
            "twap": 100 if twap_result.signal == "bullish" else 0 if twap_result.signal == "bearish" else 50,
            "obv": 100 if obv_result.signal == "bullish" else 0 if obv_result.signal == "bearish" else 50,
        }

        # Average price-based signals
        price_signal_score = sum(scores.values()) / len(scores)

        # Volume metrics
        volume_signal = "strong" if obv_result.signal == "bullish" and obv_result.strength > 60 else "weak"

        # Volatility metrics
        volatility = atr_result.details.get("volatility_level", "medium")
        range_type = adr_result.signal

        # Overall signal
        if price_signal_score > 70:
            overall_signal = "STRONG_BUY"
        elif price_signal_score > 60:
            overall_signal = "BUY"
        elif price_signal_score < 30:
            overall_signal = "STRONG_SELL"
        elif price_signal_score < 40:
            overall_signal = "SELL"
        else:
            overall_signal = "NEUTRAL"

        return {
            "symbol": symbol,
            "timestamp": vwap_result.timestamp,
            "overall_signal": overall_signal,
            "confidence": price_signal_score,
            "indicators": {
                "vwap": {"signal": vwap_result.signal, "value": vwap_result.value},
                "twap": {"signal": twap_result.signal, "value": twap_result.value},
                "obv": {"signal": obv_result.signal, "value": obv_result.value},
                "atr": {"signal": atr_result.signal, "value": atr_result.value},
                "adr": {"signal": adr_result.signal, "value": adr_result.value},
            },
            "volume_assessment": volume_signal,
            "volatility_assessment": {
                "trend": atr_result.signal,
                "level": volatility,
                "range_type": range_type
            },
            "summary": f"{volume_signal.upper()} volume with {volatility} volatility - {overall_signal}"
        }
