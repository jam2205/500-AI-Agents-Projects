"""Anomaly Detection Tools - Statistical and behavioral anomaly detection."""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np
from datetime import datetime


class AnomalyType(Enum):
    """Type of anomaly detected."""
    STATISTICAL = "statistical"  # Price/volume deviation from mean
    VOLATILITY = "volatility"  # Unusual volatility change
    VOLUME = "volume"  # Unusual volume
    BEHAVIORAL = "behavioral"  # Pattern breaks or trend reversals
    MOMENTUM = "momentum"  # Sudden momentum changes


@dataclass
class PriceAnomaly:
    """Detected price anomaly."""
    anomaly_type: AnomalyType
    severity: float  # 0-1, how extreme is the anomaly
    z_score: float  # Standard deviations from mean
    current_value: float
    expected_range: Tuple[float, float]  # (min, max) expected range
    confidence: float  # 0-1 confidence in anomaly
    description: str
    details: Dict[str, Any] = None


@dataclass
class AnomalyAnalysis:
    """Results from anomaly detection."""
    timestamp: datetime
    symbol: str
    price_anomalies: List[PriceAnomaly]
    volume_anomalies: List[PriceAnomaly]
    volatility_anomalies: List[PriceAnomaly]
    behavioral_flags: List[Dict[str, Any]]
    momentum_anomalies: List[PriceAnomaly]
    overall_anomaly_score: float  # 0-1, 1 = maximum anomaly
    signals: List[str]
    confidence: float = 0.5
    details: Dict[str, Any] = None


class AnomalyDetector:
    """Detects statistical and behavioral anomalies in price/volume data."""

    @staticmethod
    def detect_statistical_anomalies(
        prices: List[float],
        lookback: int = 50,
        z_threshold: float = 2.0
    ) -> Tuple[List[PriceAnomaly], float]:
        """
        Detect price anomalies using statistical methods (Z-score).

        Args:
            prices: List of prices
            lookback: Number of bars for baseline calculation
            z_threshold: Z-score threshold for anomaly

        Returns:
            Tuple of (anomalies, z_score_of_current)
        """
        anomalies = []

        if len(prices) < lookback:
            return anomalies, 0.0

        baseline = prices[-lookback:-1]
        current = prices[-1]

        mean = np.mean(baseline)
        std = np.std(baseline)

        if std == 0:
            return anomalies, 0.0

        z_score = (current - mean) / std

        if abs(z_score) > z_threshold:
            severity = min(abs(z_score) / 3.0, 1.0)  # Normalize to 0-1
            lower_bound = mean - (z_threshold * std)
            upper_bound = mean + (z_threshold * std)

            anomalies.append(PriceAnomaly(
                anomaly_type=AnomalyType.STATISTICAL,
                severity=severity,
                z_score=z_score,
                current_value=current,
                expected_range=(lower_bound, upper_bound),
                confidence=min(abs(z_score) / 4.0, 1.0),
                description=f"Price deviation: {z_score:.2f} std devs from mean",
                details={
                    "mean": float(mean),
                    "std": float(std),
                    "lookback_bars": lookback
                }
            ))

        return anomalies, z_score

    @staticmethod
    def detect_volume_anomalies(
        volumes: List[float],
        lookback: int = 50,
        multiplier: float = 1.5
    ) -> List[PriceAnomaly]:
        """
        Detect unusual volume.

        Args:
            volumes: List of volumes
            lookback: Number of bars for baseline
            multiplier: Volume multiplier threshold (1.5x normal)

        Returns:
            List of volume anomalies
        """
        anomalies = []

        if len(volumes) < lookback:
            return anomalies

        baseline_volume = np.mean(volumes[-lookback:-1])
        current_volume = volumes[-1]

        if baseline_volume == 0:
            return anomalies

        volume_ratio = current_volume / baseline_volume

        if volume_ratio > multiplier:
            severity = min((volume_ratio - 1.0) / 2.0, 1.0)

            anomalies.append(PriceAnomaly(
                anomaly_type=AnomalyType.VOLUME,
                severity=severity,
                z_score=volume_ratio,
                current_value=current_volume,
                expected_range=(0, baseline_volume * multiplier),
                confidence=min((volume_ratio - 1.0) / 1.5, 1.0),
                description=f"Unusual volume: {volume_ratio:.2f}x normal",
                details={
                    "baseline_volume": float(baseline_volume),
                    "current_volume": float(current_volume),
                    "ratio": float(volume_ratio)
                }
            ))

        return anomalies

    @staticmethod
    def detect_volatility_anomalies(
        closes: List[float],
        lookback: int = 50,
        volatility_threshold: float = 1.5
    ) -> List[PriceAnomaly]:
        """
        Detect volatility regime changes.

        Args:
            closes: List of close prices
            lookback: Number of bars for baseline
            volatility_threshold: Multiplier for vol threshold (1.5x normal)

        Returns:
            List of volatility anomalies
        """
        anomalies = []

        if len(closes) < lookback:
            return anomalies

        # Calculate returns
        returns = np.diff(closes) / closes[:-1]

        baseline_vol = np.std(returns[-lookback:-1])
        recent_vol = np.std(returns[-5:])

        if baseline_vol == 0:
            return anomalies

        vol_ratio = recent_vol / baseline_vol

        if vol_ratio > volatility_threshold:
            severity = min((vol_ratio - 1.0) / 1.5, 1.0)

            anomalies.append(PriceAnomaly(
                anomaly_type=AnomalyType.VOLATILITY,
                severity=severity,
                z_score=vol_ratio,
                current_value=recent_vol,
                expected_range=(0, baseline_vol * volatility_threshold),
                confidence=min((vol_ratio - 1.0), 1.0),
                description=f"Volatility spike: {vol_ratio:.2f}x normal",
                details={
                    "baseline_volatility": float(baseline_vol),
                    "recent_volatility": float(recent_vol),
                    "ratio": float(vol_ratio),
                    "lookback_bars": lookback
                }
            ))

        return anomalies

    @staticmethod
    def detect_momentum_anomalies(
        closes: List[float],
        lookback: int = 50,
        threshold: float = 2.0
    ) -> List[PriceAnomaly]:
        """
        Detect momentum (rate of change) anomalies.

        Args:
            closes: List of close prices
            lookback: Number of bars for baseline
            threshold: Z-score threshold

        Returns:
            List of momentum anomalies
        """
        anomalies = []

        if len(closes) < lookback:
            return anomalies

        # Calculate momentum (rate of change)
        momentum = np.diff(closes[-lookback:]) / closes[-lookback:-1]

        baseline_momentum = np.mean(momentum[:-1])
        baseline_std = np.std(momentum[:-1])
        current_momentum = momentum[-1]

        if baseline_std == 0:
            return anomalies

        z_score = (current_momentum - baseline_momentum) / baseline_std

        if abs(z_score) > threshold:
            severity = min(abs(z_score) / 3.0, 1.0)

            expected_min = baseline_momentum - (threshold * baseline_std)
            expected_max = baseline_momentum + (threshold * baseline_std)

            anomalies.append(PriceAnomaly(
                anomaly_type=AnomalyType.MOMENTUM,
                severity=severity,
                z_score=z_score,
                current_value=current_momentum,
                expected_range=(expected_min, expected_max),
                confidence=min(abs(z_score) / 4.0, 1.0),
                description=f"Momentum anomaly: {z_score:.2f} std devs from baseline",
                details={
                    "baseline_momentum": float(baseline_momentum),
                    "current_momentum": float(current_momentum),
                    "std": float(baseline_std)
                }
            ))

        return anomalies

    @staticmethod
    def detect_behavioral_anomalies(
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float],
        lookback: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Detect behavioral anomalies (pattern breaks, unusual candles).

        Args:
            opens, highs, lows, closes: OHLC data
            volumes: Volume data
            lookback: Number of bars for analysis

        Returns:
            List of behavioral anomalies
        """
        flags = []

        if len(closes) < lookback:
            return flags

        # Check for reversal candles (opposite direction from trend)
        recent_opens = opens[-lookback:]
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        recent_closes = closes[-lookback:]
        recent_volumes = volumes[-lookback:]

        # Trend direction (slope of closes)
        x = np.arange(len(recent_closes) - 1)
        trend_slope = np.polyfit(x[:-5], recent_closes[:-5], 1)[0]

        current_open = recent_opens[-1]
        current_close = recent_closes[-1]
        current_high = recent_highs[-1]
        current_low = recent_lows[-1]
        current_volume = recent_volumes[-1]
        avg_volume = np.mean(recent_volumes[:-1])

        # Reversal candle: large body opposite to trend
        candle_size = abs(current_close - current_open)
        avg_candle_size = np.mean([abs(recent_closes[i] - recent_opens[i]) for i in range(-lookback, -1)])

        if candle_size > avg_candle_size * 1.5:
            if (trend_slope > 0 and current_close < current_open) or \
               (trend_slope < 0 and current_close > current_open):
                flags.append({
                    "type": "reversal_candle",
                    "severity": min(candle_size / (avg_candle_size * 2), 1.0),
                    "description": f"Large reversal candle: {candle_size:.2f}",
                    "bars_ago": 0
                })

        # Gap detection
        if len(recent_closes) >= 2:
            prev_close = recent_closes[-2]
            current_open = recent_opens[-1]
            gap = abs(current_open - prev_close) / prev_close

            if gap > 0.01:  # > 1% gap
                flags.append({
                    "type": "gap",
                    "severity": min(gap / 0.05, 1.0),  # Normalize to 5% gap = severity 1
                    "description": f"Price gap: {gap * 100:.2f}%",
                    "bars_ago": 0
                })

        # Breakaway volume
        if current_volume > avg_volume * 1.5:
            # Check if price is moving away from recent range
            recent_range = max(recent_highs[-10:]) - min(recent_lows[-10:])
            current_move_from_low = current_close - min(recent_lows[-10:])

            if current_move_from_low > recent_range * 0.7:
                flags.append({
                    "type": "breakaway_volume",
                    "severity": min((current_volume / avg_volume - 1) / 1, 1.0),
                    "description": f"High volume breakaway: {current_volume / avg_volume:.2f}x",
                    "bars_ago": 0
                })

        # Wicks pattern (rejection at extremes)
        wick_size = current_high - current_low
        body_size = abs(current_close - current_open)

        if wick_size > 0 and body_size > 0:
            wick_ratio = wick_size / body_size

            if wick_ratio > 2.5:  # Large wicks relative to body
                flags.append({
                    "type": "rejection_wick",
                    "severity": min(wick_ratio / 4, 1.0),
                    "description": f"Large wicks (rejection): {wick_ratio:.2f}x body",
                    "bars_ago": 0
                })

        return flags

    @staticmethod
    def analyze_anomalies(
        symbol: str,
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float]
    ) -> AnomalyAnalysis:
        """
        Complete anomaly analysis.

        Args:
            symbol: Trading symbol
            opens, highs, lows, closes, volumes: OHLCV data

        Returns:
            Complete anomaly analysis
        """
        # Detect various anomalies
        price_anomalies, price_z = AnomalyDetector.detect_statistical_anomalies(closes)
        volume_anomalies = AnomalyDetector.detect_volume_anomalies(volumes)
        volatility_anomalies = AnomalyDetector.detect_volatility_anomalies(closes)
        momentum_anomalies = AnomalyDetector.detect_momentum_anomalies(closes)
        behavioral_flags = AnomalyDetector.detect_behavioral_anomalies(
            opens, highs, lows, closes, volumes
        )

        # Calculate overall anomaly score (0-1)
        anomaly_count = (len(price_anomalies) + len(volume_anomalies) +
                        len(volatility_anomalies) + len(momentum_anomalies) +
                        len(behavioral_flags))
        overall_score = min(anomaly_count / 5, 1.0)  # Max 5 anomalies = 1.0

        # Generate signals
        signals = []
        confidence = 50

        if price_anomalies:
            signals.append("PRICE_ANOMALY_DETECTED")
            confidence += 20

        if volume_anomalies:
            signals.append("VOLUME_ANOMALY_DETECTED")
            confidence += 15

        if volatility_anomalies:
            signals.append("VOLATILITY_ANOMALY_DETECTED")
            confidence += 15

        if momentum_anomalies:
            signals.append("MOMENTUM_ANOMALY_DETECTED")
            confidence += 10

        if behavioral_flags:
            for flag in behavioral_flags:
                if flag["type"] == "reversal_candle":
                    signals.append("REVERSAL_CANDLE_DETECTED")
                elif flag["type"] == "gap":
                    signals.append("PRICE_GAP_DETECTED")
                elif flag["type"] == "breakaway_volume":
                    signals.append("BREAKAWAY_MOVE")
                elif flag["type"] == "rejection_wick":
                    signals.append("REJECTION_DETECTED")

        return AnomalyAnalysis(
            timestamp=datetime.utcnow(),
            symbol=symbol,
            price_anomalies=price_anomalies,
            volume_anomalies=volume_anomalies,
            volatility_anomalies=volatility_anomalies,
            behavioral_flags=behavioral_flags,
            momentum_anomalies=momentum_anomalies,
            overall_anomaly_score=overall_score,
            signals=signals,
            confidence=min(confidence, 100),
            details={
                "total_anomalies": anomaly_count,
                "price_z_score": float(price_z),
                "anomaly_types": {
                    "price": len(price_anomalies),
                    "volume": len(volume_anomalies),
                    "volatility": len(volatility_anomalies),
                    "momentum": len(momentum_anomalies),
                    "behavioral": len(behavioral_flags)
                }
            }
        )
