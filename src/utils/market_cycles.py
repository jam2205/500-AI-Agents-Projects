"""Market cycle analysis utilities for accumulation, distribution, and manipulation detection.

This module provides tools for:
- Detecting Wyckoff-style accumulation/distribution phases
- Multi-timeframe cycle analysis
- Quarterly phase breakdowns within each timeframe
- Market manipulation detection
- Cycle normalization and alignment
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from collections import deque


class CyclePhase(Enum):
    """Market cycle phases based on Wyckoff method."""
    ACCUMULATION = "accumulation"
    MARKUP = "markup"
    DISTRIBUTION = "distribution"
    MARKDOWN = "markdown"
    NEUTRAL = "neutral"


class MarketRegime(Enum):
    """Overall market regime/condition."""
    STRONG_UP = "strong_uptrend"
    WEAK_UP = "weak_uptrend"
    STRONG_DOWN = "strong_downtrend"
    WEAK_DOWN = "weak_downtrend"
    CONSOLIDATION = "consolidation"
    TRANSITION = "transition"


@dataclass
class QuarterlyAnalysis:
    """Analysis of a single quarter within a timeframe."""
    quarter_number: int  # 1-4
    start_price: float
    end_price: float
    high: float
    low: float
    volume_total: float
    volume_avg: float
    phase: CyclePhase
    strength: float  # 0-100, conviction level
    details: Dict[str, Any]


@dataclass
class TimeframeAnalysis:
    """Complete analysis of one timeframe broken into quarters."""
    timeframe: str  # "daily", "weekly", "monthly"
    symbol: str
    timestamp: datetime
    overall_phase: CyclePhase
    overall_regime: MarketRegime
    quarters: List[QuarterlyAnalysis]
    confidence: float  # 0-100
    signals: List[str]
    details: Dict[str, Any]


class MarketCycleAnalyzer:
    """Analyzes market cycles using multi-timeframe quarterly breakdown."""

    @staticmethod
    def detect_phase_from_price_action(
        open_prices: List[float],
        high_prices: List[float],
        low_prices: List[float],
        close_prices: List[float],
        volumes: List[float]
    ) -> Tuple[CyclePhase, float]:
        """
        Detect phase from price action within a period.

        Wyckoff Phases:
        - Accumulation: Low volatility, mixed direction, increasing volume
        - Markup: Strong uptrend, higher highs/lows, expansion
        - Distribution: High volatility, resistance, declining volume into strength
        - Markdown: Downtrend, lower lows, declining participation
        - Neutral: Choppy, no clear direction

        Args:
            open_prices: List of opening prices
            high_prices: List of high prices
            low_prices: List of low prices
            close_prices: List of closing prices
            volumes: List of volumes

        Returns:
            Tuple of (CyclePhase, confidence_0_to_100)
        """
        if not close_prices or len(close_prices) < 2:
            return CyclePhase.NEUTRAL, 0.0

        # Calculate trend
        price_change = close_prices[-1] - close_prices[0]
        price_direction = "up" if price_change > 0 else "down" if price_change < 0 else "flat"

        # Calculate volatility
        ranges = [h - l for h, l in zip(high_prices, low_prices)]
        avg_range = sum(ranges) / len(ranges) if ranges else 0
        volatility = avg_range / close_prices[0] if close_prices[0] > 0 else 0

        # Analyze volume pattern
        avg_volume = sum(volumes) / len(volumes) if volumes else 0
        recent_volumes = volumes[-len(volumes)//2:]
        early_volumes = volumes[:len(volumes)//2]
        recent_avg_vol = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 0
        early_avg_vol = sum(early_volumes) / len(early_volumes) if early_volumes else 0
        vol_trend = "increasing" if recent_avg_vol > early_avg_vol else "decreasing"

        # Analyze price pattern - look at higher highs/lows
        higher_highs = sum(1 for i in range(1, len(high_prices)) if high_prices[i] > high_prices[i-1])
        higher_lows = sum(1 for i in range(1, len(low_prices)) if low_prices[i] > low_prices[i-1])
        lower_highs = sum(1 for i in range(1, len(high_prices)) if high_prices[i] < high_prices[i-1])
        lower_lows = sum(1 for i in range(1, len(low_prices)) if low_prices[i] < low_prices[i-1])

        # Detect phases
        phase_scores = {
            CyclePhase.ACCUMULATION: 0.0,
            CyclePhase.MARKUP: 0.0,
            CyclePhase.DISTRIBUTION: 0.0,
            CyclePhase.MARKDOWN: 0.0,
            CyclePhase.NEUTRAL: 0.0,
        }

        # Accumulation: Low volatility, up movement, volume increasing
        if volatility < 0.02 and price_direction == "up" and vol_trend == "increasing":
            phase_scores[CyclePhase.ACCUMULATION] = 85.0
        elif volatility < 0.03 and price_direction == "up":
            phase_scores[CyclePhase.ACCUMULATION] = 60.0

        # Markup: Strong up, higher highs/lows, good volume
        if price_direction == "up" and higher_highs > lower_highs and vol_trend == "increasing":
            phase_scores[CyclePhase.MARKUP] = min(100.0, 50.0 + (higher_highs - lower_highs) * 5)

        # Distribution: High volatility, sideways to down, volume declining
        if volatility > 0.03 and price_direction in ["flat", "down"] and vol_trend == "decreasing":
            phase_scores[CyclePhase.DISTRIBUTION] = 80.0
        elif volatility > 0.025 and (higher_highs == lower_highs):
            phase_scores[CyclePhase.DISTRIBUTION] = 60.0

        # Markdown: Down trend, lower lows, volume may vary
        if price_direction == "down" and lower_lows > higher_lows:
            phase_scores[CyclePhase.MARKDOWN] = min(100.0, 50.0 + (lower_lows - higher_lows) * 5)

        # Neutral: If no clear pattern
        if max(phase_scores.values()) < 50.0 or volatility > 0.05:
            phase_scores[CyclePhase.NEUTRAL] = 70.0

        # Find highest scoring phase
        best_phase = max(phase_scores, key=phase_scores.get)
        confidence = phase_scores[best_phase]

        return best_phase, confidence

    @staticmethod
    def break_into_quarters(
        data: List[Dict[str, float]],
        symbol: str,
        timeframe: str
    ) -> Tuple[List[QuarterlyAnalysis], Dict[str, Any]]:
        """
        Break price action into 4 quarters and analyze each.

        Args:
            data: List of OHLCV data points
            symbol: Trading symbol
            timeframe: Timeframe name (daily, weekly, monthly)

        Returns:
            Tuple of (list of quarterly analyses, summary details)
        """
        if not data or len(data) < 4:
            return [], {"error": "Need at least 4 data points for quarterly analysis"}

        # Split data into 4 quarters
        quarter_size = len(data) // 4
        remainder = len(data) % 4
        quarters_data = []

        start_idx = 0
        for q in range(4):
            # Distribute remainder across quarters
            end_idx = start_idx + quarter_size + (1 if q < remainder else 0)
            quarters_data.append(data[start_idx:end_idx])
            start_idx = end_idx

        # Analyze each quarter
        quarterly_analyses = []
        for q_idx, q_data in enumerate(quarters_data):
            if not q_data:
                continue

            opens = [bar.get("open", 0) for bar in q_data]
            highs = [bar.get("high", 0) for bar in q_data]
            lows = [bar.get("low", 0) for bar in q_data]
            closes = [bar.get("close", 0) for bar in q_data]
            volumes = [bar.get("volume", 0) for bar in q_data]

            # Detect phase
            phase, strength = MarketCycleAnalyzer.detect_phase_from_price_action(
                opens, highs, lows, closes, volumes
            )

            # Analyze quarter
            q_analysis = QuarterlyAnalysis(
                quarter_number=q_idx + 1,
                start_price=closes[0] if closes else 0,
                end_price=closes[-1] if closes else 0,
                high=max(highs) if highs else 0,
                low=min(lows) if lows else 0,
                volume_total=sum(volumes),
                volume_avg=sum(volumes) / len(volumes) if volumes else 0,
                phase=phase,
                strength=strength,
                details={
                    "bars_in_quarter": len(q_data),
                    "price_change": closes[-1] - closes[0] if closes else 0,
                    "price_change_pct": ((closes[-1] - closes[0]) / closes[0] * 100) if closes and closes[0] != 0 else 0,
                    "range": max(highs) - min(lows) if highs and lows else 0,
                    "volatility": (max(highs) - min(lows)) / closes[0] if closes and closes[0] > 0 else 0,
                }
            )
            quarterly_analyses.append(q_analysis)

        # Calculate summary
        summary = {
            "quarters_analyzed": len(quarterly_analyses),
            "phases": [q.phase.value for q in quarterly_analyses],
            "avg_strength": sum(q.strength for q in quarterly_analyses) / len(quarterly_analyses) if quarterly_analyses else 0,
            "total_volume": sum(q.volume_total for q in quarterly_analyses),
            "overall_price_change": (quarterly_analyses[-1].end_price - quarterly_analyses[0].start_price) if quarterly_analyses else 0,
        }

        return quarterly_analyses, summary

    @staticmethod
    def determine_overall_regime(
        phases: List[CyclePhase],
        price_changes: List[float],
        volumes: List[float]
    ) -> Tuple[MarketRegime, List[str]]:
        """
        Determine overall market regime from multi-timeframe phases.

        Args:
            phases: List of phases from different timeframes
            price_changes: Price changes from different timeframes
            volumes: Average volumes from different timeframes

        Returns:
            Tuple of (MarketRegime, list of supporting signals)
        """
        signals = []

        # Count phases
        markup_count = sum(1 for p in phases if p == CyclePhase.MARKUP)
        markdown_count = sum(1 for p in phases if p == CyclePhase.MARKDOWN)
        accumulation_count = sum(1 for p in phases if p == CyclePhase.ACCUMULATION)
        distribution_count = sum(1 for p in phases if p == CyclePhase.DISTRIBUTION)

        # Analyze price direction
        avg_price_change = sum(price_changes) / len(price_changes) if price_changes else 0
        price_direction = "up" if avg_price_change > 0 else "down" if avg_price_change < 0 else "flat"

        # Analyze volume
        avg_volume = sum(volumes) / len(volumes) if volumes else 0
        volume_trend = "high" if avg_volume > sum(volumes) / len(volumes) * 1.2 else "normal"

        # Determine regime
        if markup_count >= 2 and price_direction == "up":
            regime = MarketRegime.STRONG_UP
            signals.append("Multiple timeframes in markup phase")
            signals.append("Strong uptrend with expanding volume")
        elif markup_count >= 1 and price_direction == "up":
            regime = MarketRegime.WEAK_UP
            signals.append("Partial markup phase presence")
            signals.append("Uptrend needs confirmation from higher timeframes")
        elif markdown_count >= 2 and price_direction == "down":
            regime = MarketRegime.STRONG_DOWN
            signals.append("Multiple timeframes in markdown phase")
            signals.append("Strong downtrend with declining participation")
        elif markdown_count >= 1 and price_direction == "down":
            regime = MarketRegime.WEAK_DOWN
            signals.append("Partial markdown phase presence")
            signals.append("Downtrend needs confirmation from higher timeframes")
        elif accumulation_count >= 2:
            regime = MarketRegime.CONSOLIDATION
            signals.append("Accumulation across multiple timeframes")
            signals.append("Building base for future move")
        elif distribution_count >= 2:
            regime = MarketRegime.CONSOLIDATION
            signals.append("Distribution phase detected")
            signals.append("Potential reversal coming")
        else:
            regime = MarketRegime.TRANSITION
            signals.append("Mixed phase signals across timeframes")
            signals.append("Regime clarification expected soon")

        return regime, signals

    @staticmethod
    def detect_manipulation(
        quarters: List[QuarterlyAnalysis],
        symbol: str
    ) -> Dict[str, Any]:
        """
        Detect potential market manipulation patterns.

        Patterns include:
        - Sudden volume surge followed by reversal (trap)
        - Price extremes on declining volume (fake breakout)
        - Wide range bars followed by breakout (false signal)

        Args:
            quarters: List of quarterly analyses
            symbol: Trading symbol

        Returns:
            Manipulation analysis results
        """
        manipulations = []
        confidence_sum = 0

        if len(quarters) < 2:
            return {"manipulations": [], "total_signals": 0}

        for i in range(len(quarters) - 1):
            current = quarters[i]
            next_q = quarters[i + 1]

            # Pattern 1: High volume spike followed by reversal
            vol_spike = current.volume_total > current.volume_avg * 2.5
            direction_reversal = (
                (current.phase == CyclePhase.MARKUP and next_q.phase == CyclePhase.MARKDOWN) or
                (current.phase == CyclePhase.MARKDOWN and next_q.phase == CyclePhase.MARKUP)
            )
            if vol_spike and direction_reversal:
                manipulations.append({
                    "type": "volume_trap",
                    "quarter": current.quarter_number,
                    "description": f"Volume spike ({current.volume_total / current.volume_avg:.1f}x average) followed by direction reversal",
                    "confidence": 75.0
                })
                confidence_sum += 75.0

            # Pattern 2: Extreme price on declining volume
            price_extreme = abs(current.details.get("price_change_pct", 0)) > 5.0
            vol_declining = current.volume_total < current.volume_avg
            if price_extreme and vol_declining:
                manipulations.append({
                    "type": "fake_move",
                    "quarter": current.quarter_number,
                    "description": f"Extreme price move ({current.details.get('price_change_pct', 0):.2f}%) on declining volume",
                    "confidence": 65.0
                })
                confidence_sum += 65.0

        avg_confidence = confidence_sum / len(manipulations) if manipulations else 0

        return {
            "symbol": symbol,
            "manipulations": manipulations,
            "total_signals": len(manipulations),
            "average_confidence": avg_confidence,
            "risk_level": "high" if len(manipulations) >= 3 else "medium" if len(manipulations) >= 1 else "low"
        }

    @staticmethod
    def align_timeframes(
        daily_analysis: TimeframeAnalysis,
        weekly_analysis: TimeframeAnalysis,
        monthly_analysis: Optional[TimeframeAnalysis] = None
    ) -> Dict[str, Any]:
        """
        Align multiple timeframe analyses for normalized trading framework.

        Args:
            daily_analysis: Daily timeframe analysis
            weekly_analysis: Weekly timeframe analysis
            monthly_analysis: Optional monthly timeframe analysis

        Returns:
            Alignment report with framework signals
        """
        all_analyses = [daily_analysis, weekly_analysis]
        if monthly_analysis:
            all_analyses.append(monthly_analysis)

        # Extract phases
        phases = [a.overall_phase for a in all_analyses]
        timeframes = [a.timeframe for a in all_analyses]

        # Perfect alignment: all same phase
        all_same = len(set(phases)) == 1
        alignment_score = 100.0 if all_same else 60.0 if len(set(phases)) == 2 else 30.0

        # Find highest timeframe phase (more significant)
        phase_hierarchy = {
            CyclePhase.ACCUMULATION: 1,
            CyclePhase.MARKUP: 2,
            CyclePhase.DISTRIBUTION: 3,
            CyclePhase.MARKDOWN: 4,
            CyclePhase.NEUTRAL: 0,
        }
        highest_phase = max(all_analyses, key=lambda x: phase_hierarchy.get(x.overall_phase, 0)).overall_phase

        alignment_signals = []
        if all_same:
            alignment_signals.append(f"Perfect alignment: All timeframes in {highest_phase.value}")
        else:
            alignment_signals.append(f"Partial alignment: Higher TFs favor {highest_phase.value}")
            alignment_signals.append(f"Daily: {daily_analysis.overall_phase.value}")
            alignment_signals.append(f"Weekly: {weekly_analysis.overall_phase.value}")

        return {
            "alignment_score": alignment_score,
            "dominant_phase": highest_phase.value,
            "phases_by_timeframe": dict(zip(timeframes, [p.value for p in phases])),
            "signals": alignment_signals,
            "framework_confidence": min(100.0, alignment_score + sum(a.confidence for a in all_analyses) / len(all_analyses)),
            "trading_framework": {
                "primary_direction": "BUY" if highest_phase == CyclePhase.MARKUP else "SELL" if highest_phase == CyclePhase.MARKDOWN else "HOLD",
                "strength": "STRONG" if all_same else "WEAK",
                "pullback_opportunity": highest_phase == CyclePhase.ACCUMULATION,
                "reversal_risk": highest_phase == CyclePhase.DISTRIBUTION,
            }
        }
