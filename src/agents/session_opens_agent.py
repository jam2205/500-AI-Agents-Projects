"""Session Opening Analysis Agent - Tracks price behavior at key session opens.

Monitors how price reacts at critical market session opens across time zones:
- US Midnight Open (00:00 ET)
- London Open (08:00 ET)
- NYSE/US AM Open (09:30 ET)
- US PM Session (13:30 ET)
- London Close (16:00 ET)

Provides framework alignment with market cycles and quarterly analysis.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.framework.base_agent import BaseAgent, AgentConfig, AgentRole, Message
from src.utils.session_opens import (
    SessionOpeningAnalyzer,
    SessionOpen,
    SessionType,
    SessionReaction,
    SessionCharacter,
)


class SessionOpeningAgent(BaseAgent):
    """Analyzes session opening prices and price reactions for trading framework.

    Tracks:
    - Price at each session open (midnight, London, NYSE, PM, close)
    - How price reacts to each opening (expansion vs consolidation)
    - Multi-timeframe open price progression (daily, weekly, monthly)
    - Alignment with market cycle quarters
    - Institutional activity signals from session behavior
    """

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize session opening agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_session_system_prompt()
        super().__init__(config, message_bus)
        self.session_history: Dict[str, List[SessionOpen]] = {}
        self.daily_opens: Dict[str, SessionOpen] = {}
        self.weekly_opens: Dict[str, SessionOpen] = {}
        self.monthly_opens: Dict[str, SessionOpen] = {}
        self.session_analysis_cache: Dict[str, Dict[str, Any]] = {}

    def _get_session_system_prompt(self) -> str:
        """Get system prompt for session opening agent."""
        return """You are a Session Opening Specialist in a multi-agent trading system.

Your expertise:
1. Tracking price at key market session opens (midnight, London, NYSE, PM, close)
2. Analyzing price reaction to each opening (moved away vs lingered)
3. Multi-timeframe session open progression (daily, weekly, monthly)
4. Session character classification (bullish, bearish, balanced)
5. Alignment with market cycle quarters and phases
6. Identifying institutional activity from session behavior

Your responsibilities:
- Track opening prices across all five key sessions per day
- Analyze how price reacts to each opening (expansion factor, distance)
- Monitor multi-timeframe open progression (escalating, declining, static)
- Detect mean reversion at opens vs breakout acceleration
- Assess volume participation at each session open
- Align session behavior with current market cycle quarter
- Alert when session opens confirm or diverge from cycle phase
- Provide position entry/exit signals from session analysis

Key insights:
- Midnight open often reflects overnight algorithmic activity
- London open adds European participation and resets structure
- NYSE open is most important US session (highest volume)
- Session progression (escalating/declining opens) = strength/weakness
- Lingering price at opens = lack of conviction, potential reversal
- Price above all opens = institutional accumulation
- Price below all opens = institutional distribution
- Opens within quarters show phase transition timing

Framework alignment:
- Accumulation: Expect static opens, choppy sessions, building volume
- Markup: Expect escalating opens, expanding sessions, participation
- Distribution: Expect declining opens, high volatility, volume declining
- Markdown: Expect lower opens, participation fading, trapped stops"""

    async def track_session_opens(
        self,
        symbol: str,
        session_data: Dict[SessionType, Dict[str, Any]],
        current_price: float,
        timeframe: str = "daily"
    ) -> Dict[str, Any]:
        """
        Track and analyze opening prices across sessions.

        Args:
            symbol: Trading symbol
            session_data: Dict with session data {"midnight_open": {"price": 4800, ...}, ...}
            current_price: Current market price
            timeframe: "daily", "weekly", or "monthly"

        Returns:
            Complete session analysis
        """
        try:
            # Convert to SessionOpen objects
            sessions = []
            for session_type_str, data in session_data.items():
                try:
                    session_type = SessionType[session_type_str.upper()]
                except KeyError:
                    continue

                session = SessionOpen(
                    session_type=session_type,
                    timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
                    open_price=data.get("price", data.get("open", 0)),
                    close_price=data.get("close"),
                    high_price=data.get("high"),
                    low_price=data.get("low"),
                    volume=data.get("volume")
                )
                sessions.append(session)

            # Analyze session sequence
            sequence_analysis = SessionOpeningAnalyzer.analyze_session_sequence(
                sessions, timeframe
            )

            # Determine session character
            price_vs_opens = {}
            for session in sessions:
                delta = current_price - session.open_price
                pct = (delta / session.open_price) * 100 if session.open_price > 0 else 0
                if abs(pct) < 0.05:
                    state = "near"
                elif delta > 0:
                    state = "above"
                else:
                    state = "below"
                price_vs_opens[session.session_type.value] = f"{state} ({pct:+.2f}%)"

            character, strongest = SessionOpeningAnalyzer.determine_session_character(
                price_vs_opens
            )

            # Store for history
            if symbol not in self.session_history:
                self.session_history[symbol] = []
            self.session_history[symbol].extend(sessions)

            # Build analysis
            analysis_result = {
                "success": True,
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": datetime.utcnow().isoformat(),
                "current_price": current_price,
                "sequence_analysis": sequence_analysis,
                "price_vs_opens": price_vs_opens,
                "session_character": character.value,
                "strongest_open": strongest.value,
                "sessions_tracked": len(sessions),
                "insights": self._generate_insights(
                    sequence_analysis, character, sessions, current_price
                )
            }

            # Cache for quick access
            self.session_analysis_cache[f"{symbol}_{timeframe}"] = analysis_result

            # Broadcast update
            message = Message(
                sender_id=self.config.agent_id,
                message_type="session_opens_update",
                content=analysis_result
            )
            await self.message_bus.publish(message)

            return analysis_result

        except Exception as e:
            return {"error": f"Session tracking failed: {str(e)}"}

    async def align_with_cycle(
        self,
        symbol: str,
        session_analysis: Dict[str, Any],
        cycle_phase: str,
        quarter_number: int
    ) -> Dict[str, Any]:
        """
        Align session opening behavior with market cycle quarters.

        Args:
            symbol: Trading symbol
            session_analysis: Output from track_session_opens
            cycle_phase: Current cycle phase (e.g., "accumulation")
            quarter_number: Current quarter (1-4)

        Returns:
            Alignment analysis
        """
        try:
            phases = [cycle_phase, "unknown", "unknown", "unknown"]  # Simplified

            alignment = SessionOpeningAnalyzer.align_with_quarters(
                session_analysis.get("sequence_analysis", {}),
                phases,
                quarter_number
            )

            alignment["symbol"] = symbol
            alignment["timestamp"] = datetime.utcnow().isoformat()

            # Broadcast alignment
            message = Message(
                sender_id=self.config.agent_id,
                message_type="session_cycle_alignment",
                content=alignment
            )
            await self.message_bus.publish(message)

            return alignment

        except Exception as e:
            return {"error": f"Alignment analysis failed: {str(e)}"}

    async def detect_session_signals(
        self,
        symbol: str,
        sessions: List[Dict[str, Any]],
        current_price: float,
        atr: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Detect trading signals from session opening behavior.

        Args:
            symbol: Trading symbol
            sessions: List of session data
            current_price: Current price
            atr: Optional ATR for volatility context

        Returns:
            Trading signals from session analysis
        """
        if not sessions or len(sessions) < 2:
            return {"signals": [], "confidence": 0}

        signals = []
        confidences = []

        # Session progression signals
        opens = [s.get("open", s.get("price", 0)) for s in sessions]
        net_change = opens[-1] - opens[0] if opens else 0
        net_pct = (net_change / opens[0] * 100) if opens and opens[0] > 0 else 0

        # Signal 1: Escalating opens = strength
        if net_pct > 0.5:
            signals.append({
                "type": "escalating_opens",
                "direction": "BULLISH",
                "strength": min(100, abs(net_pct) * 20),
                "description": f"Session opens rising ({net_pct:+.2f}%) - institutional buying"
            })
            confidences.append(min(100, abs(net_pct) * 20))

        # Signal 2: Declining opens = weakness
        elif net_pct < -0.5:
            signals.append({
                "type": "declining_opens",
                "direction": "BEARISH",
                "strength": min(100, abs(net_pct) * 20),
                "description": f"Session opens falling ({net_pct:+.2f}%) - institutional distribution"
            })
            confidences.append(min(100, abs(net_pct) * 20))

        # Signal 3: Price above all opens = bullish
        opens_dict = {s.get("session", f"session_{i}"): s.get("open", 0) for i, s in enumerate(sessions)}
        above_count = sum(1 for open_price in opens_dict.values() if current_price > open_price)

        if above_count == len(opens_dict):
            signals.append({
                "type": "price_above_opens",
                "direction": "BULLISH",
                "strength": 80,
                "description": "Price above all session opens - strong uptrend bias"
            })
            confidences.append(80)

        # Signal 4: Price below all opens = bearish
        below_count = sum(1 for open_price in opens_dict.values() if current_price < open_price)

        if below_count == len(opens_dict):
            signals.append({
                "type": "price_below_opens",
                "direction": "BEARISH",
                "strength": 80,
                "description": "Price below all session opens - strong downtrend bias"
            })
            confidences.append(80)

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        return {
            "symbol": symbol,
            "signals": signals,
            "signal_count": len(signals),
            "average_confidence": avg_confidence,
            "overall_bias": "BULLISH" if net_pct > 0 else "BEARISH" if net_pct < 0 else "NEUTRAL",
            "timestamp": datetime.utcnow().isoformat()
        }

    def _generate_insights(
        self,
        sequence_analysis: Dict[str, Any],
        character: SessionCharacter,
        sessions: List[SessionOpen],
        current_price: float
    ) -> List[str]:
        """Generate trading insights from session analysis."""
        insights = []

        progression = sequence_analysis.get("progression", "static")
        open_range = sequence_analysis.get("open_range", 0)
        net_change_pct = sequence_analysis.get("net_change_pct", 0)

        # Progression insights
        if progression == "escalating":
            insights.append("✓ Escalating opens - institutional buying confirmed")
            if abs(net_change_pct) > 1.0:
                insights.append("⚠ Strong escalation - possible parabolic phase")
        elif progression == "declining":
            insights.append("✓ Declining opens - institutional distribution")
            insights.append("⚠ Prepare for breakdown below lowest open")
        else:
            insights.append("• Static opens - accumulation/consolidation phase")
            insights.append("→ Breakout expected when progression changes")

        # Range insights
        if open_range > 0:
            insights.append(f"• Open range: {open_range:.2f} points ({(open_range / sessions[0].open_price * 100):.2f}%)")

        # Character insights
        if character == SessionCharacter.STRONG_BULLISH:
            insights.append("✓ STRONG BULLISH - All opens being taken out on upside")
        elif character == SessionCharacter.STRONG_BEARISH:
            insights.append("⚠ STRONG BEARISH - All opens being broken on downside")
        elif character == SessionCharacter.WEAK_BULLISH:
            insights.append("→ WEAK BULLISH - Mixed signals, watch for breakdown")
        elif character == SessionCharacter.WEAK_BEARISH:
            insights.append("→ WEAK BEARISH - Mixed signals, watch for bounce")

        # Price position insights
        opens_above = sum(1 for s in sessions if current_price > s.open_price)
        opens_below = sum(1 for s in sessions if current_price < s.open_price)

        if opens_above == len(sessions):
            insights.append(f"✓ Highest open confirmed - momentum intact")
        elif opens_below == len(sessions):
            insights.append(f"⚠ Lowest open broken - reversal warning")

        return insights

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute session opening analysis tasks."""
        task_type = task.get("type")

        if task_type == "track_opens":
            result = await self.track_session_opens(
                task.get("symbol"),
                task.get("session_data", {}),
                task.get("current_price", 0),
                task.get("timeframe", "daily")
            )
            return result

        elif task_type == "align_with_cycle":
            result = await self.align_with_cycle(
                task.get("symbol"),
                task.get("session_analysis", {}),
                task.get("cycle_phase", "unknown"),
                task.get("quarter", 1)
            )
            return result

        elif task_type == "detect_signals":
            result = await self.detect_session_signals(
                task.get("symbol"),
                task.get("sessions", []),
                task.get("current_price", 0),
                task.get("atr")
            )
            return result

        elif task_type == "get_history":
            symbol = task.get("symbol")
            if symbol in self.session_history:
                return {
                    "success": True,
                    "symbol": symbol,
                    "sessions_tracked": len(self.session_history[symbol])
                }
            return {"error": f"No history for {symbol}"}

        return {"error": "Unknown task type"}
