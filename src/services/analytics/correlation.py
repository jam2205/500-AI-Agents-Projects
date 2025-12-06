"""Correlation Analysis Tools - Cross-asset correlation, lead-lag, regime detection."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np
from datetime import datetime


@dataclass
class CorrelationAnalysis:
    """Results from correlation analysis."""
    timestamp: datetime
    symbol_pair: str  # "EURUSD vs ES"
    correlation: float  # Pearson correlation
    correlation_regime: str  # "high_positive", "moderate", "low", "high_negative"
    lead_lag_relationship: Optional[str] = None  # Which leads
    lead_lag_lag_periods: int = 0
    rolling_correlation_trend: str = "stable"  # "increasing", "decreasing", "stable"
    regime_change_detected: bool = False
    confidence: float = 0.0
    details: Dict[str, Any] = None


class CorrelationAnalyzer:
    """Analyzes cross-asset correlations and relationships."""

    @staticmethod
    def calculate_correlation(
        series1: List[float],
        series2: List[float],
        method: str = "pearson"
    ) -> float:
        """
        Calculate correlation between two series.

        Args:
            series1: First series
            series2: Second series
            method: "pearson", "spearman", or "kendall"

        Returns:
            Correlation coefficient (-1 to 1)
        """
        if len(series1) < 2 or len(series2) < 2:
            return 0.0

        s1 = np.array(series1)
        s2 = np.array(series2)

        if method == "pearson":
            correlation = float(np.corrcoef(s1, s2)[0, 1])
        elif method == "spearman":
            # Rank-based correlation
            ranks1 = np.argsort(np.argsort(s1))
            ranks2 = np.argsort(np.argsort(s2))
            correlation = float(np.corrcoef(ranks1, ranks2)[0, 1])
        else:
            correlation = float(np.corrcoef(s1, s2)[0, 1])

        # Handle NaN
        if np.isnan(correlation):
            return 0.0

        return correlation

    @staticmethod
    def rolling_correlation(
        series1: List[float],
        series2: List[float],
        window: int = 20
    ) -> List[float]:
        """
        Calculate rolling correlation.

        Args:
            series1: First series
            series2: Second series
            window: Rolling window size

        Returns:
            List of rolling correlation values
        """
        correlations = []

        for i in range(len(series1) - window + 1):
            s1 = series1[i:i+window]
            s2 = series2[i:i+window]
            corr = CorrelationAnalyzer.calculate_correlation(s1, s2)
            correlations.append(corr)

        return correlations

    @staticmethod
    def detect_lead_lag(
        leader: List[float],
        follower: List[float],
        max_lag: int = 10
    ) -> tuple:
        """
        Detect lead-lag relationship between series.

        Args:
            leader: Suspected leading series
            follower: Suspected following series
            max_lag: Maximum lags to test

        Returns:
            Tuple of (optimal_lag, max_correlation)
        """
        max_corr = 0.0
        optimal_lag = 0

        for lag in range(0, max_lag + 1):
            if lag == 0:
                corr = CorrelationAnalyzer.calculate_correlation(leader, follower)
            else:
                # Shift follower forward (follower lags leader)
                corr = CorrelationAnalyzer.calculate_correlation(
                    leader[:-lag],
                    follower[lag:]
                )

            if abs(corr) > abs(max_corr):
                max_corr = corr
                optimal_lag = lag

        return optimal_lag, max_corr

    @staticmethod
    def analyze_correlation_regime(correlation: float) -> str:
        """Classify correlation into regime."""
        if correlation > 0.7:
            return "high_positive"
        elif correlation > 0.3:
            return "moderate_positive"
        elif correlation > -0.3:
            return "low"
        elif correlation > -0.7:
            return "moderate_negative"
        else:
            return "high_negative"

    @staticmethod
    def detect_regime_change(
        rolling_corrs: List[float],
        threshold: float = 0.2
    ) -> bool:
        """
        Detect if correlation regime has changed.

        Args:
            rolling_corrs: Rolling correlation values
            threshold: Change threshold

        Returns:
            True if regime change detected
        """
        if len(rolling_corrs) < 10:
            return False

        recent = np.mean(rolling_corrs[-5:])  # Last 5
        historical = np.mean(rolling_corrs[:-5])  # Before that

        change = abs(recent - historical)

        return change > threshold

    @staticmethod
    def correlation_matrix(
        symbols: List[str],
        price_data: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """
        Calculate correlation matrix across multiple assets.

        Args:
            symbols: List of symbols
            price_data: Dict with symbol -> prices

        Returns:
            Correlation matrix and analysis
        """
        n = len(symbols)
        matrix = np.zeros((n, n))

        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                if i == j:
                    matrix[i, j] = 1.0
                else:
                    prices1 = price_data.get(sym1, [])
                    prices2 = price_data.get(sym2, [])

                    if prices1 and prices2:
                        matrix[i, j] = CorrelationAnalyzer.calculate_correlation(
                            prices1, prices2
                        )

        # Find strongest relationships
        strongest_positive = []
        strongest_negative = []

        for i in range(n):
            for j in range(i+1, n):
                corr = matrix[i, j]
                pair = f"{symbols[i]} vs {symbols[j]}"

                if corr > 0.5:
                    strongest_positive.append((pair, corr))
                elif corr < -0.5:
                    strongest_negative.append((pair, corr))

        strongest_positive.sort(key=lambda x: x[1], reverse=True)
        strongest_negative.sort(key=lambda x: x[1])

        return {
            "matrix": matrix.tolist(),
            "symbols": symbols,
            "strongest_positive": strongest_positive[:5],
            "strongest_negative": strongest_negative[:5],
        }

    @staticmethod
    def analyze_pair(
        symbol1: str,
        symbol2: str,
        prices1: List[float],
        prices2: List[float]
    ) -> CorrelationAnalysis:
        """
        Complete correlation analysis for a pair.

        Args:
            symbol1: First symbol
            symbol2: Second symbol
            prices1: Prices for symbol 1
            prices2: Prices for symbol 2

        Returns:
            Complete correlation analysis
        """
        # Current correlation
        correlation = CorrelationAnalyzer.calculate_correlation(prices1, prices2)
        regime = CorrelationAnalyzer.analyze_correlation_regime(correlation)

        # Rolling correlation
        rolling = CorrelationAnalyzer.rolling_correlation(prices1, prices2)

        # Trend in rolling correlation
        if len(rolling) >= 10:
            recent_avg = np.mean(rolling[-5:])
            prev_avg = np.mean(rolling[-10:-5])

            if recent_avg > prev_avg * 1.1:
                rolling_trend = "increasing"
            elif recent_avg < prev_avg * 0.9:
                rolling_trend = "decreasing"
            else:
                rolling_trend = "stable"

            regime_change = CorrelationAnalyzer.detect_regime_change(rolling)
        else:
            rolling_trend = "stable"
            regime_change = False

        # Lead-lag analysis
        lag1, corr1 = CorrelationAnalyzer.detect_lead_lag(prices1, prices2)
        lag2, corr2 = CorrelationAnalyzer.detect_lead_lag(prices2, prices1)

        if abs(corr1) > abs(corr2):
            lead_lag = f"{symbol1} leads {symbol2}"
            lag_periods = lag1
        else:
            lead_lag = f"{symbol2} leads {symbol1}"
            lag_periods = lag2

        return CorrelationAnalysis(
            timestamp=datetime.utcnow(),
            symbol_pair=f"{symbol1} vs {symbol2}",
            correlation=correlation,
            correlation_regime=regime,
            lead_lag_relationship=lead_lag,
            lead_lag_lag_periods=lag_periods,
            rolling_correlation_trend=rolling_trend,
            regime_change_detected=regime_change,
            confidence=min(100, len(prices1) / 5),
            details={
                "rolling_correlation_current": rolling[-1] if rolling else 0,
                "rolling_correlation_mean": float(np.mean(rolling)) if rolling else 0,
                "rolling_correlation_std": float(np.std(rolling)) if rolling else 0,
                "correlation_changes": rolling_trend,
            }
        )

    @staticmethod
    def correlation_signal(analysis: CorrelationAnalysis) -> Dict[str, Any]:
        """Generate trading signal from correlation analysis."""
        signals = []
        confidence = 50

        # Regime changes are important
        if analysis.regime_change_detected:
            signals.append("CORRELATION_REGIME_CHANGE")
            confidence += 20

        # High positive correlation breakdowns
        if analysis.correlation_regime == "high_positive" and analysis.rolling_correlation_trend == "decreasing":
            signals.append("CORRELATION_BREAKDOWN")
            signals.append("DIVERGENCE_LIKELY")
            confidence += 15

        # Low correlation expanding
        if analysis.correlation_regime == "low" and analysis.rolling_correlation_trend == "increasing":
            signals.append("CORRELATION_FORMING")
            confidence += 10

        # Lead-lag relationships useful for timing
        if analysis.lead_lag_lag_periods > 0:
            signals.append(f"LEAD_LAG_DETECTED_{analysis.lead_lag_lag_periods}_PERIODS")
            confidence += 10

        return {
            "signals": signals,
            "confidence": min(100, confidence),
            "recommendation": "CAUTION" if analysis.regime_change_detected else "NORMAL"
        }
