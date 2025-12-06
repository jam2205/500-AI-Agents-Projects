"""Market Cycle Analysis Agent - Detects accumulation/distribution cycles across timeframes.

Provides top-down market structure analysis using Wyckoff methodology with
quarterly breakdown of each timeframe for alignment and normalization.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.framework.base_agent import BaseAgent, AgentConfig, AgentRole, Message
from src.utils.market_cycles import (
    MarketCycleAnalyzer,
    TimeframeAnalysis,
    CyclePhase,
    MarketRegime,
)


class MarketCycleAgent(BaseAgent):
    """Analyzes market cycles using multi-timeframe quarterly breakdown.

    Detects Wyckoff phases:
    - Accumulation: Institutional buying, building base
    - Markup: Strong uptrend, participation expanding
    - Distribution: High volatility, profit-taking, transition
    - Markdown: Downtrend, participation declining
    """

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize market cycle agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_cycle_system_prompt()
        super().__init__(config, message_bus)
        self.cycle_analyses: Dict[str, Dict[str, TimeframeAnalysis]] = {}
        self.alignment_reports: List[Dict[str, Any]] = []
        self.manipulation_alerts: List[Dict[str, Any]] = []

    def _get_cycle_system_prompt(self) -> str:
        """Get system prompt for cycle analysis."""
        return """You are a Market Cycle Analyst in a multi-agent trading system.

Your expertise:
1. Wyckoff methodology and market phase analysis
2. Accumulation (institutional buying, low volatility base-building)
3. Markup (strong uptrend, expanding participation)
4. Distribution (transition phase, profit-taking)
5. Markdown (downtrend, declining participation)
6. Multi-timeframe alignment and confirmation

Your responsibilities:
- Analyze market structure using quarterly breakdown within each timeframe
- Detect which phase the market is in (daily, weekly, monthly)
- Align multiple timeframes to identify primary trend direction
- Detect manipulation patterns (false breakouts, volume traps)
- Provide framework for normalized trading across market regimes
- Alert when phases change (early warning system)
- Assess probability of phase continuation vs. reversal

Key frameworks:
- Accumulation: Best risk/reward for longs, pullbacks = entries
- Markup: Trend-following, don't fade, protect stops
- Distribution: Caution on new longs, watch for breakdown
- Markdown: Short bias, rally attempts offer exits, range trading possible

Multi-timeframe alignment:
- All same phase = STRONGEST signal (100% alignment)
- 2 out of 3 aligned = GOOD signal (66% alignment)
- Mixed phases = CAUTION - conflicting signals (unclear)
- Phase divergence = Reversal warning (lower TF changing direction)"""

    async def analyze_symbol(
        self,
        symbol: str,
        daily_data: List[Dict[str, float]],
        weekly_data: List[Dict[str, float]],
        monthly_data: Optional[List[Dict[str, float]]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a symbol across multiple timeframes with quarterly breakdown.

        Args:
            symbol: Trading symbol
            daily_data: Daily OHLCV data
            weekly_data: Weekly OHLCV data
            monthly_data: Optional monthly OHLCV data

        Returns:
            Complete analysis with phases, alignment, and framework
        """
        try:
            # Analyze each timeframe with quarterly breakdown
            daily_quarters, daily_summary = MarketCycleAnalyzer.break_into_quarters(
                daily_data, symbol, "daily"
            )
            weekly_quarters, weekly_summary = MarketCycleAnalyzer.break_into_quarters(
                weekly_data, symbol, "weekly"
            )

            # Determine overall phases
            daily_phase, daily_confidence = self._determine_overall_phase(daily_quarters)
            weekly_phase, weekly_confidence = self._determine_overall_phase(weekly_quarters)

            # Determine regimes
            daily_regime, daily_signals = MarketRegime.__class__.__bases__

            # Create timeframe analyses
            daily_analysis = TimeframeAnalysis(
                timeframe="daily",
                symbol=symbol,
                timestamp=datetime.utcnow(),
                overall_phase=daily_phase,
                overall_regime=MarketRegime.STRONG_UP,  # Placeholder
                quarters=daily_quarters,
                confidence=daily_confidence,
                signals=daily_signals if hasattr(daily_signals, '__iter__') else [],
                details=daily_summary
            )

            weekly_analysis = TimeframeAnalysis(
                timeframe="weekly",
                symbol=symbol,
                timestamp=datetime.utcnow(),
                overall_phase=weekly_phase,
                overall_regime=MarketRegime.STRONG_UP,  # Placeholder
                quarters=weekly_quarters,
                confidence=weekly_confidence,
                signals=[],
                details=weekly_summary
            )

            # Detect manipulations
            daily_manip = MarketCycleAnalyzer.detect_manipulation(daily_quarters, symbol)
            weekly_manip = MarketCycleAnalyzer.detect_manipulation(weekly_quarters, symbol)

            # Align timeframes
            alignment = MarketCycleAnalyzer.align_timeframes(
                daily_analysis,
                weekly_analysis,
                None
            )

            # Store analyses
            if symbol not in self.cycle_analyses:
                self.cycle_analyses[symbol] = {}
            self.cycle_analyses[symbol]["daily"] = daily_analysis
            self.cycle_analyses[symbol]["weekly"] = weekly_analysis

            # Store alignment
            self.alignment_reports.append(alignment)

            # Broadcast cycle analysis update
            message = Message(
                sender_id=self.config.agent_id,
                message_type="market_cycle_analysis",
                content={
                    "symbol": symbol,
                    "timestamp": datetime.utcnow().isoformat(),
                    "daily": {
                        "phase": daily_phase.value,
                        "confidence": daily_confidence,
                        "quarters": [self._quarter_to_dict(q) for q in daily_quarters],
                        "summary": daily_summary
                    },
                    "weekly": {
                        "phase": weekly_phase.value,
                        "confidence": weekly_confidence,
                        "quarters": [self._quarter_to_dict(q) for q in weekly_quarters],
                        "summary": weekly_summary
                    },
                    "manipulation": {
                        "daily": daily_manip,
                        "weekly": weekly_manip
                    },
                    "alignment": alignment
                }
            )
            await self.message_bus.publish(message)

            return {
                "success": True,
                "symbol": symbol,
                "daily_phase": daily_phase.value,
                "weekly_phase": weekly_phase.value,
                "alignment_score": alignment["alignment_score"],
                "trading_framework": alignment["trading_framework"],
                "manipulation_risk": {
                    "daily": daily_manip["risk_level"],
                    "weekly": weekly_manip["risk_level"]
                }
            }

        except Exception as e:
            return {"error": f"Cycle analysis failed: {str(e)}"}

    def _determine_overall_phase(
        self,
        quarters: List
    ) -> tuple:
        """Determine overall phase from quarters."""
        if not quarters:
            return CyclePhase.NEUTRAL, 0.0

        # Simple voting system: majority phase wins
        phases = [q.phase for q in quarters]
        phase_counts = {}
        for phase in phases:
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

        most_common_phase = max(phase_counts, key=phase_counts.get)
        confidence = (phase_counts[most_common_phase] / len(quarters)) * 100

        return most_common_phase, confidence

    def _quarter_to_dict(self, quarter) -> Dict[str, Any]:
        """Convert QuarterlyAnalysis to dict."""
        return {
            "quarter": quarter.quarter_number,
            "phase": quarter.phase.value,
            "strength": quarter.strength,
            "start_price": quarter.start_price,
            "end_price": quarter.end_price,
            "high": quarter.high,
            "low": quarter.low,
            "volume_total": quarter.volume_total,
            "details": quarter.details
        }

    async def detect_phase_change(
        self,
        symbol: str,
        current_phase: str,
        previous_phase: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Detect and analyze phase changes for early warning.

        Args:
            symbol: Trading symbol
            current_phase: Current phase
            previous_phase: Previous phase
            timeframe: Timeframe of the change

        Returns:
            Phase change analysis with implications
        """
        phase_change_analysis = f"""Analyze this phase change in {symbol}:

Timeframe: {timeframe}
Previous Phase: {previous_phase}
Current Phase: {current_phase}

Provide:
1. Significance of this phase change
2. Time until next phase expected
3. Trading opportunities during transition
4. Risk factors to watch
5. Confirmation signs to expect
6. Effect on lower timeframes"""

        analysis = await self.think(phase_change_analysis)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "previous_phase": previous_phase,
            "current_phase": current_phase,
            "analysis": analysis,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def assess_framework_strength(
        self,
        alignment_score: float,
        daily_confidence: float,
        weekly_confidence: float
    ) -> Dict[str, Any]:
        """
        Assess strength of trading framework for position sizing.

        Args:
            alignment_score: Multi-timeframe alignment (0-100)
            daily_confidence: Daily phase confidence (0-100)
            weekly_confidence: Weekly phase confidence (0-100)

        Returns:
            Framework strength assessment with position sizing guidance
        """
        # Weighted scoring: weekly is more important (60%), daily 40%
        framework_strength = (alignment_score * 0.5 +
                            weekly_confidence * 0.35 +
                            daily_confidence * 0.15)

        if framework_strength > 80:
            framework_quality = "excellent"
            position_size = "full"
            risk_level = "low"
        elif framework_strength > 70:
            framework_quality = "good"
            position_size = "3/4"
            risk_level = "medium"
        elif framework_strength > 60:
            framework_quality = "moderate"
            position_size = "1/2"
            risk_level = "elevated"
        elif framework_strength > 50:
            framework_quality = "weak"
            position_size = "1/4"
            risk_level = "high"
        else:
            framework_quality = "very_weak"
            position_size = "avoid"
            risk_level = "very_high"

        return {
            "framework_strength": framework_strength,
            "quality": framework_quality,
            "position_sizing": position_size,
            "risk_level": risk_level,
            "alignment_importance": f"Alignment score {alignment_score:.1f}% (most important)",
            "weekly_importance": f"Weekly confidence {weekly_confidence:.1f}% (important for direction)",
            "daily_importance": f"Daily confidence {daily_confidence:.1f}% (important for timing)"
        }

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute market cycle analysis tasks."""
        task_type = task.get("type")

        if task_type == "analyze_symbol":
            result = await self.analyze_symbol(
                task.get("symbol"),
                task.get("daily_data", []),
                task.get("weekly_data", []),
                task.get("monthly_data")
            )
            return result

        elif task_type == "detect_phase_change":
            result = await self.detect_phase_change(
                task.get("symbol"),
                task.get("current_phase"),
                task.get("previous_phase"),
                task.get("timeframe", "daily")
            )
            return result

        elif task_type == "assess_framework":
            result = await self.assess_framework_strength(
                task.get("alignment_score", 50),
                task.get("daily_confidence", 50),
                task.get("weekly_confidence", 50)
            )
            return result

        elif task_type == "get_cycle_analysis":
            symbol = task.get("symbol")
            if symbol in self.cycle_analyses:
                return {
                    "success": True,
                    "symbol": symbol,
                    "analyses": self.cycle_analyses[symbol]
                }
            return {"error": f"No cycle analysis for {symbol}"}

        return {"error": "Unknown task type"}
