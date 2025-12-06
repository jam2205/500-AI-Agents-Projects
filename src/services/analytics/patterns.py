"""Pattern Recognition Tools - Support/resistance, chart patterns, fractals."""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np
from datetime import datetime


class PriceLevel(Enum):
    """Type of price level identified."""
    SUPPORT = "support"
    RESISTANCE = "resistance"
    PIVOT = "pivot"


@dataclass
class SupportResistanceLevel:
    """Support or resistance level."""
    price: float
    level_type: PriceLevel
    strength: float  # 0-1, how many times touched
    touches: int  # Number of times price tested
    last_test_bars_ago: int  # How many bars since last test
    confidence: float  # 0-1 confidence in the level
    details: Dict[str, Any] = None


@dataclass
class ChartPattern:
    """Identified chart pattern."""
    pattern_name: str  # "head_and_shoulders", "triangle", "wedge", "flag", "channel"
    start_bar: int  # Index where pattern started
    end_bar: int  # Index where pattern ended
    pattern_type: str  # "bullish", "bearish", "neutral"
    target_move: Optional[float] = None  # Projected move in points
    target_pct: Optional[float] = None  # Projected move in percentage
    confidence: float = 0.5  # 0-1 confidence
    breakout_direction: Optional[str] = None  # "up", "down", "none"
    details: Dict[str, Any] = None


@dataclass
class PatternAnalysis:
    """Results from pattern analysis."""
    timestamp: datetime
    symbol: str
    support_levels: List[SupportResistanceLevel]
    resistance_levels: List[SupportResistanceLevel]
    chart_patterns: List[ChartPattern]
    pivot_points: Dict[str, float]  # S2, S1, P, R1, R2
    fractal_patterns: List[Dict[str, Any]]  # Up and down fractals
    signals: List[str]
    confidence: float = 0.5
    details: Dict[str, Any] = None


class PatternAnalyzer:
    """Identifies chart patterns and price levels."""

    @staticmethod
    def find_support_resistance(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        lookback: int = 50,
        min_touches: int = 2
    ) -> Tuple[List[SupportResistanceLevel], List[SupportResistanceLevel]]:
        """
        Find support and resistance levels using swing analysis.

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            lookback: Number of bars to analyze
            min_touches: Minimum touches required for a level

        Returns:
            Tuple of (support_levels, resistance_levels)
        """
        if len(highs) < lookback:
            return [], []

        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        recent_closes = closes[-lookback:]

        # Find swing highs and lows
        swing_highs = []
        swing_lows = []

        for i in range(1, len(recent_highs) - 1):
            # Swing high: higher high on both sides
            if recent_highs[i] > recent_highs[i-1] and recent_highs[i] > recent_highs[i+1]:
                swing_highs.append((i, recent_highs[i]))

            # Swing low: lower low on both sides
            if recent_lows[i] < recent_lows[i-1] and recent_lows[i] < recent_lows[i+1]:
                swing_lows.append((i, recent_lows[i]))

        # Cluster similar prices into levels
        support_levels = PatternAnalyzer._cluster_levels(swing_lows, recent_lows, PriceLevel.SUPPORT)
        resistance_levels = PatternAnalyzer._cluster_levels(swing_highs, recent_highs, PriceLevel.RESISTANCE)

        # Filter by minimum touches
        support_levels = [s for s in support_levels if s.touches >= min_touches]
        resistance_levels = [r for r in resistance_levels if r.touches >= min_touches]

        return support_levels, resistance_levels

    @staticmethod
    def _cluster_levels(
        swings: List[Tuple[int, float]],
        price_data: List[float],
        level_type: PriceLevel,
        tolerance_pct: float = 0.5
    ) -> List[SupportResistanceLevel]:
        """Cluster swings into distinct price levels."""
        if not swings:
            return []

        levels = []
        used = set()

        for i, (bar_idx, price) in enumerate(swings):
            if i in used:
                continue

            # Find all swings within tolerance
            tolerance = price * tolerance_pct / 100
            cluster = [price]
            cluster_indices = [bar_idx]

            for j in range(i + 1, len(swings)):
                if j in used:
                    continue
                if abs(swings[j][1] - price) < tolerance:
                    cluster.append(swings[j][1])
                    cluster_indices.append(swings[j][0])
                    used.add(j)

            # Calculate cluster statistics
            cluster_price = float(np.mean(cluster))
            touches = len(cluster)
            last_test = len(price_data) - 1 - max(cluster_indices)

            # Calculate strength (how close price currently is)
            strength = 1.0 - min(abs(price_data[-1] - cluster_price) / (cluster_price * 0.02), 1.0)

            levels.append(SupportResistanceLevel(
                price=cluster_price,
                level_type=level_type,
                strength=max(0, strength),
                touches=touches,
                last_test_bars_ago=last_test,
                confidence=min(touches / 3, 1.0),
                details={"cluster_size": len(cluster)}
            ))

            used.add(i)

        # Sort by strength
        levels.sort(key=lambda x: x.strength, reverse=True)
        return levels

    @staticmethod
    def identify_chart_patterns(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        lookback: int = 50
    ) -> List[ChartPattern]:
        """
        Identify chart patterns (triangles, wedges, flags, channels).

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            lookback: Number of bars to analyze

        Returns:
            List of identified patterns
        """
        patterns = []

        if len(highs) < lookback:
            return patterns

        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        recent_closes = closes[-lookback:]

        # Detect triangles (converging highs and lows)
        patterns.extend(PatternAnalyzer._detect_triangles(recent_highs, recent_lows))

        # Detect channels (parallel support and resistance)
        patterns.extend(PatternAnalyzer._detect_channels(recent_highs, recent_lows))

        # Detect wedges (narrowing range with slope)
        patterns.extend(PatternAnalyzer._detect_wedges(recent_highs, recent_lows, recent_closes))

        # Detect flags (small consolidation after move)
        patterns.extend(PatternAnalyzer._detect_flags(recent_highs, recent_lows, recent_closes))

        return patterns

    @staticmethod
    def _detect_triangles(highs: List[float], lows: List[float]) -> List[ChartPattern]:
        """Detect triangle patterns (ascending, descending, symmetric)."""
        patterns = []

        if len(highs) < 20:
            return patterns

        # Last 20 bars
        recent_highs = highs[-20:]
        recent_lows = lows[-20:]

        # Calculate slope of highs and lows
        x = np.arange(len(recent_highs))
        high_slope = np.polyfit(x, recent_highs, 1)[0]
        low_slope = np.polyfit(x, recent_lows, 1)[0]

        # Symmetric triangle: high slope negative, low slope positive
        if high_slope < -0.01 and low_slope > 0.01:
            range_start = recent_highs[0] - recent_lows[0]
            range_end = recent_highs[-1] - recent_lows[-1]

            if range_end < range_start * 0.5:  # Converging
                target_move = range_start * 0.8
                patterns.append(ChartPattern(
                    pattern_name="symmetric_triangle",
                    start_bar=len(highs) - 20,
                    end_bar=len(highs) - 1,
                    pattern_type="neutral",
                    target_move=target_move,
                    target_pct=(target_move / recent_closes[-1]) * 100,
                    confidence=0.6,
                    details={"high_slope": float(high_slope), "low_slope": float(low_slope)}
                ))

        # Ascending triangle: high slope flat/positive, low slope positive
        if low_slope > 0.01 and abs(high_slope) < 0.01:
            patterns.append(ChartPattern(
                pattern_name="ascending_triangle",
                start_bar=len(highs) - 20,
                end_bar=len(highs) - 1,
                pattern_type="bullish",
                target_move=recent_highs[-1] - recent_lows[-20],
                confidence=0.65,
                breakout_direction="up"
            ))

        # Descending triangle: high slope negative, low slope flat
        if high_slope < -0.01 and abs(low_slope) < 0.01:
            patterns.append(ChartPattern(
                pattern_name="descending_triangle",
                start_bar=len(highs) - 20,
                end_bar=len(highs) - 1,
                pattern_type="bearish",
                target_move=recent_highs[-20] - recent_lows[-1],
                confidence=0.65,
                breakout_direction="down"
            ))

        return patterns

    @staticmethod
    def _detect_channels(highs: List[float], lows: List[float]) -> List[ChartPattern]:
        """Detect channel patterns (parallel lines)."""
        patterns = []

        if len(highs) < 20:
            return patterns

        recent_highs = highs[-20:]
        recent_lows = lows[-20:]
        x = np.arange(len(recent_highs))

        high_slope = np.polyfit(x, recent_highs, 1)[0]
        low_slope = np.polyfit(x, recent_lows, 1)[0]

        # Parallel slopes indicate channel
        if abs(high_slope - low_slope) < 0.005:
            if abs(high_slope) > 0.01:
                channel_type = "bullish" if high_slope > 0 else "bearish"
                patterns.append(ChartPattern(
                    pattern_name="channel",
                    start_bar=len(highs) - 20,
                    end_bar=len(highs) - 1,
                    pattern_type=channel_type,
                    confidence=0.6,
                    details={"slope": float(high_slope)}
                ))

        return patterns

    @staticmethod
    def _detect_wedges(highs: List[float], lows: List[float], closes: List[float]) -> List[ChartPattern]:
        """Detect wedge patterns (converging range with slope)."""
        patterns = []

        if len(highs) < 20:
            return patterns

        recent_highs = highs[-20:]
        recent_lows = lows[-20:]
        recent_closes = closes[-20:]
        x = np.arange(len(recent_highs))

        high_slope = np.polyfit(x, recent_highs, 1)[0]
        low_slope = np.polyfit(x, recent_lows, 1)[0]

        # Both slopes should have same sign (both positive or both negative)
        if high_slope * low_slope > 0:
            range_start = recent_highs[0] - recent_lows[0]
            range_end = recent_highs[-1] - recent_lows[-1]

            if range_end < range_start * 0.5:  # Converging
                mid_price = (recent_highs[-1] + recent_lows[-1]) / 2
                if recent_closes[-1] > mid_price:
                    pattern_type = "bullish"
                else:
                    pattern_type = "bearish"

                patterns.append(ChartPattern(
                    pattern_name="wedge",
                    start_bar=len(highs) - 20,
                    end_bar=len(highs) - 1,
                    pattern_type=pattern_type,
                    confidence=0.55,
                    details={"range_compression": float(range_end / range_start)}
                ))

        return patterns

    @staticmethod
    def _detect_flags(highs: List[float], lows: List[float], closes: List[float]) -> List[ChartPattern]:
        """Detect flag patterns (consolidation after move)."""
        patterns = []

        if len(highs) < 20:
            return patterns

        recent_highs = highs[-20:]
        recent_lows = lows[-20:]
        recent_closes = closes[-20:]

        # Flag: small range (consolidation) following larger move
        mid_range = (recent_highs[-10:] - recent_lows[-10:]).mean()
        earlier_range = (recent_highs[-20:-10] - recent_lows[-20:-10]).mean()

        if mid_range < earlier_range * 0.5 and earlier_range > 0:
            # Calculate move direction before consolidation
            earlier_close = recent_closes[-20]
            recent_close = recent_closes[-10]

            if recent_close > earlier_close:
                pattern_type = "bullish"
            else:
                pattern_type = "bearish"

            patterns.append(ChartPattern(
                pattern_name="flag",
                start_bar=len(highs) - 20,
                end_bar=len(highs) - 1,
                pattern_type=pattern_type,
                confidence=0.5,
                breakout_direction="up" if pattern_type == "bullish" else "down",
                details={"consolidation_range": float(mid_range)}
            ))

        return patterns

    @staticmethod
    def calculate_pivots(high: float, low: float, close: float) -> Dict[str, float]:
        """
        Calculate pivot point levels (S2, S1, P, R1, R2).

        Args:
            high: Highest price in period
            low: Lowest price in period
            close: Closing price of period

        Returns:
            Dictionary with pivot levels
        """
        pivot = (high + low + close) / 3
        range_hl = high - low

        s1 = (2 * pivot) - high
        r1 = (2 * pivot) - low
        s2 = pivot - range_hl
        r2 = pivot + range_hl

        return {
            "S2": s2,
            "S1": s1,
            "P": pivot,
            "R1": r1,
            "R2": r2,
        }

    @staticmethod
    def detect_fractals(highs: List[float], lows: List[float]) -> List[Dict[str, Any]]:
        """
        Detect fractal patterns (Bill Williams fractals).
        Up fractal: High with 2 lower highs on each side.
        Down fractal: Low with 2 higher lows on each side.

        Args:
            highs: List of high prices
            lows: List of low prices

        Returns:
            List of fractal patterns
        """
        fractals = []

        if len(highs) < 5:
            return fractals

        for i in range(2, len(highs) - 2):
            # Up fractal (peak)
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                fractals.append({
                    "type": "up_fractal",
                    "price": highs[i],
                    "bar_index": i,
                    "bars_ago": len(highs) - 1 - i,
                    "description": f"Peak at {highs[i]}"
                })

            # Down fractal (trough)
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                fractals.append({
                    "type": "down_fractal",
                    "price": lows[i],
                    "bar_index": i,
                    "bars_ago": len(lows) - 1 - i,
                    "description": f"Trough at {lows[i]}"
                })

        return fractals

    @staticmethod
    def analyze_patterns(
        symbol: str,
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> PatternAnalysis:
        """
        Complete pattern analysis.

        Args:
            symbol: Trading symbol
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices

        Returns:
            Complete pattern analysis
        """
        # Find support/resistance
        support_levels, resistance_levels = PatternAnalyzer.find_support_resistance(
            highs, lows, closes
        )

        # Identify chart patterns
        chart_patterns = PatternAnalyzer.identify_chart_patterns(highs, lows, closes)

        # Calculate pivot points (based on most recent bar)
        pivot_points = PatternAnalyzer.calculate_pivots(highs[-1], lows[-1], closes[-1])

        # Detect fractals
        fractals = PatternAnalyzer.detect_fractals(highs, lows)

        # Generate signals
        signals = []
        confidence = 50

        # Signal from support/resistance proximity
        if support_levels:
            nearest_support = min(support_levels, key=lambda x: abs(closes[-1] - x.price))
            if nearest_support.strength > 0.7:
                signals.append("STRONG_SUPPORT_NEARBY")
                confidence += 15

        if resistance_levels:
            nearest_resistance = min(resistance_levels, key=lambda x: abs(closes[-1] - x.price))
            if nearest_resistance.strength > 0.7:
                signals.append("STRONG_RESISTANCE_NEARBY")
                confidence += 15

        # Signals from chart patterns
        for pattern in chart_patterns:
            if pattern.pattern_type == "bullish" and pattern.confidence > 0.6:
                signals.append(f"BULLISH_{pattern.pattern_name.upper()}")
                confidence += 10

            if pattern.pattern_type == "bearish" and pattern.confidence > 0.6:
                signals.append(f"BEARISH_{pattern.pattern_name.upper()}")
                confidence -= 10

        return PatternAnalysis(
            timestamp=datetime.utcnow(),
            symbol=symbol,
            support_levels=support_levels[:3],  # Top 3
            resistance_levels=resistance_levels[:3],  # Top 3
            chart_patterns=chart_patterns,
            pivot_points=pivot_points,
            fractal_patterns=fractals[-5:] if fractals else [],  # Last 5 fractals
            signals=signals,
            confidence=min(100, max(0, confidence)),
            details={
                "total_support_levels": len(support_levels),
                "total_resistance_levels": len(resistance_levels),
                "total_patterns": len(chart_patterns),
                "total_fractals": len(fractals),
            }
        )
