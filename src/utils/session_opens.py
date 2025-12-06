"""Session opening price tracking and analysis system.

Tracks price behavior at key market session opens:
- US Midnight Open (00:00 ET)
- London Open (08:00 ET)
- US AM Open / NYSE Open (09:30 ET)
- US PM Session (13:30 ET)
- London Close (16:00 ET)

Analyzes:
- Price relative to session opens
- Session reaction (expansion vs consolidation)
- Multi-timeframe opening prices (daily, weekly, monthly)
- Session character (bullish, bearish, balanced)
- Alignment with market cycle quarters
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import pytz


class SessionType(Enum):
    """Market sessions across time zones."""
    MIDNIGHT_OPEN = "midnight_open"          # 00:00 ET
    LONDON_OPEN = "london_open"              # 08:00 ET
    NYSE_OPEN = "nyse_open"                  # 09:30 ET
    US_PM_SESSION = "us_pm_session"          # 13:30 ET
    LONDON_CLOSE = "london_close"            # 16:00 ET


class SessionReaction(Enum):
    """How price reacted at session opening."""
    MOVED_AWAY = "moved_away"                # Price expanded from open
    LINGERED = "lingered"                    # Price stayed near open
    MEAN_REVERSION = "mean_reversion"        # Price returned to open
    EXPANSION = "expansion"                  # Strong directional move


class SessionCharacter(Enum):
    """Overall session character/tone."""
    STRONG_BULLISH = "strong_bullish"        # Above all opens
    WEAK_BULLISH = "weak_bullish"            # Above some opens
    NEUTRAL = "neutral"                      # Mixed signals
    WEAK_BEARISH = "weak_bearish"            # Below some opens
    STRONG_BEARISH = "strong_bearish"        # Below all opens


@dataclass
class SessionOpen:
    """Single session opening record."""
    session_type: SessionType
    timestamp: datetime
    open_price: float
    close_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    volume: Optional[float] = None

    @property
    def price_change(self) -> float:
        """Change from open if session closed."""
        if self.close_price:
            return self.close_price - self.open_price
        return 0.0

    @property
    def price_change_pct(self) -> float:
        """Percentage change from open."""
        if self.close_price and self.open_price > 0:
            return (self.price_change / self.open_price) * 100
        return 0.0


@dataclass
class SessionAnalysis:
    """Complete analysis of a session."""
    session_type: SessionType
    date: str  # YYYY-MM-DD
    timeframe: str  # "daily", "weekly", "monthly"
    open_price: float
    current_price: Optional[float]
    price_distance: float  # How far from open
    reaction: SessionReaction
    character: SessionCharacter
    expansion_factor: float  # Distance / ATR or volatility measure
    volume_profile: Dict[str, Any]
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeframeOpens:
    """Opening prices for one timeframe broken into sessions."""
    timeframe: str  # "daily", "weekly", "monthly"
    date: str
    sessions: Dict[SessionType, SessionOpen]
    overall_character: SessionCharacter
    strongest_session: SessionType
    sessions_above_midnight: int  # Count of sessions trading above midnight open
    alignment_with_cycle: Dict[str, Any] = field(default_factory=dict)


class SessionOpeningAnalyzer:
    """Analyzes session opening prices and reactions across timeframes."""

    # Session times in ET
    SESSION_TIMES = {
        SessionType.MIDNIGHT_OPEN: (0, 0),
        SessionType.LONDON_OPEN: (8, 0),
        SessionType.NYSE_OPEN: (9, 30),
        SessionType.US_PM_SESSION: (13, 30),
        SessionType.LONDON_CLOSE: (16, 0),
    }

    ET = pytz.timezone("US/Eastern")

    @staticmethod
    def detect_session_reaction(
        open_price: float,
        current_price: float,
        high_price: float,
        low_price: float,
        historical_volatility: Optional[float] = None
    ) -> Tuple[SessionReaction, float]:
        """
        Detect how price reacted at session opening.

        Args:
            open_price: Session opening price
            current_price: Current price
            high_price: Session high
            low_price: Session low
            historical_volatility: Optional ATR or volatility measure

        Returns:
            Tuple of (SessionReaction, expansion_factor)
        """
        price_distance = abs(current_price - open_price)
        session_range = high_price - low_price

        # Calculate expansion factor
        if historical_volatility and historical_volatility > 0:
            expansion_factor = price_distance / historical_volatility
        elif session_range > 0:
            expansion_factor = price_distance / session_range
        else:
            expansion_factor = 0.0

        # Determine reaction based on distance and time since open
        if expansion_factor < 0.2:
            # Price stayed very close to open
            reaction = SessionReaction.LINGERED
        elif abs(current_price - open_price) < (high_price - open_price) * 0.5:
            # Price moved away but returned significantly toward open
            reaction = SessionReaction.MEAN_REVERSION
        elif expansion_factor > 1.5:
            # Strong expansion from open
            reaction = SessionReaction.EXPANSION
        else:
            # Moderate move from open
            reaction = SessionReaction.MOVED_AWAY

        return reaction, expansion_factor

    @staticmethod
    def determine_session_character(
        price_vs_opens: Dict[SessionType, str]
    ) -> Tuple[SessionCharacter, SessionType]:
        """
        Determine overall session character from price vs multiple opens.

        Args:
            price_vs_opens: Dict like {"midnight_open": "above", "nyse_open": "below", ...}

        Returns:
            Tuple of (SessionCharacter, strongest_session_type)
        """
        above_count = sum(1 for v in price_vs_opens.values() if "above" in v)
        below_count = sum(1 for v in price_vs_opens.values() if "below" in v)
        total = above_count + below_count

        if total == 0:
            return SessionCharacter.NEUTRAL, SessionType.MIDNIGHT_OPEN

        # Find which session open current price is furthest from
        strongest = SessionType.MIDNIGHT_OPEN
        max_distance = 0

        if above_count / total > 0.75:
            character = SessionCharacter.STRONG_BULLISH
        elif above_count / total > 0.5:
            character = SessionCharacter.WEAK_BULLISH
        elif below_count / total > 0.75:
            character = SessionCharacter.STRONG_BEARISH
        elif below_count / total > 0.5:
            character = SessionCharacter.WEAK_BEARISH
        else:
            character = SessionCharacter.NEUTRAL

        return character, strongest

    @staticmethod
    def analyze_session_sequence(
        sessions: List[SessionOpen],
        timeframe: str = "daily"
    ) -> Dict[str, Any]:
        """
        Analyze how sessions progressed throughout the timeframe.

        Args:
            sessions: List of session opens in chronological order
            timeframe: "daily", "weekly", or "monthly"

        Returns:
            Sequence analysis with progression patterns
        """
        if not sessions or len(sessions) < 2:
            return {"error": "Need at least 2 sessions to analyze sequence"}

        # Analyze progression
        opening_prices = [s.open_price for s in sessions]
        session_changes = []

        for i in range(len(sessions) - 1):
            change = sessions[i + 1].open_price - sessions[i].open_price
            pct_change = (change / sessions[i].open_price) * 100 if sessions[i].open_price > 0 else 0
            session_changes.append({
                "from": sessions[i].session_type.value,
                "to": sessions[i + 1].session_type.value,
                "change": change,
                "change_pct": pct_change
            })

        # Determine progression character
        net_change = opening_prices[-1] - opening_prices[0]
        if net_change > 0:
            progression = "escalating"  # Opens getting higher
        elif net_change < 0:
            progression = "declining"  # Opens getting lower
        else:
            progression = "static"  # Opens similar

        # Volume analysis if available
        total_volume = sum(s.volume for s in sessions if s.volume)
        avg_volume = total_volume / len([s for s in sessions if s.volume]) if any(s.volume for s in sessions) else 0

        return {
            "timeframe": timeframe,
            "session_count": len(sessions),
            "first_open": opening_prices[0],
            "last_open": opening_prices[-1],
            "net_change": net_change,
            "net_change_pct": (net_change / opening_prices[0]) * 100 if opening_prices[0] > 0 else 0,
            "progression": progression,
            "session_transitions": session_changes,
            "total_volume": total_volume,
            "avg_volume": avg_volume,
            "high_open": max(opening_prices),
            "low_open": min(opening_prices),
            "open_range": max(opening_prices) - min(opening_prices)
        }

    @staticmethod
    def align_with_quarters(
        session_analysis: Dict[str, Any],
        quarterly_phases: List[str],
        quarter_number: int
    ) -> Dict[str, Any]:
        """
        Align session opening analysis with market cycle quarters.

        Args:
            session_analysis: Output from analyze_session_sequence
            quarterly_phases: List of phases ["accumulation", "markup", ...]
            quarter_number: Which quarter (1-4) we're analyzing

        Returns:
            Alignment analysis showing session behavior in context of cycle phase
        """
        quarter_phase = quarterly_phases[quarter_number - 1] if quarter_number <= len(quarterly_phases) else "unknown"

        # Interpretation based on phase and session progression
        if quarter_phase == "accumulation":
            expected_progression = "static"
            expected_volume = "increasing"
            interpretation = "Base building phase - expect choppy sessions, volume building"

            if session_analysis.get("progression") == "static":
                alignment_score = 85
                alignment_signal = "GOOD"
            elif session_analysis.get("progression") == "escalating":
                alignment_score = 60
                alignment_signal = "CAUTION - Premature breakout"
            else:
                alignment_score = 70
                alignment_signal = "ACCEPTABLE"

        elif quarter_phase == "markup":
            expected_progression = "escalating"
            expected_volume = "expanding"
            interpretation = "Uptrend - expect rising session opens, confirming strength"

            if session_analysis.get("progression") == "escalating":
                alignment_score = 90
                alignment_signal = "EXCELLENT"
            elif session_analysis.get("progression") == "static":
                alignment_score = 50
                alignment_signal = "WARNING - Momentum fading"
            else:
                alignment_score = 20
                alignment_signal = "REJECTION - Reversal likely"

        elif quarter_phase == "distribution":
            expected_progression = "declining"
            expected_volume = "declining"
            interpretation = "Distribution - expect lower opens, participation declining"

            if session_analysis.get("progression") == "declining":
                alignment_score = 85
                alignment_signal = "CONFIRMED"
            elif session_analysis.get("progression") == "escalating":
                alignment_score = 30
                alignment_signal = "FAILURE - Short squeeze likely"
            else:
                alignment_score = 60
                alignment_signal = "TRANSITION"

        elif quarter_phase == "markdown":
            expected_progression = "declining"
            expected_volume = "declining"
            interpretation = "Downtrend - expect lower opens, participation fading"

            if session_analysis.get("progression") == "declining":
                alignment_score = 90
                alignment_signal = "CONFIRMED"
            else:
                alignment_score = 60
                alignment_signal = "POSSIBLE BOUNCE"

        else:
            expected_progression = "neutral"
            expected_volume = "neutral"
            interpretation = "Neutral phase"
            alignment_score = 50
            alignment_signal = "UNCLEAR"

        return {
            "quarter": quarter_number,
            "quarter_phase": quarter_phase,
            "expected_progression": expected_progression,
            "actual_progression": session_analysis.get("progression"),
            "alignment_score": alignment_score,
            "alignment_signal": alignment_signal,
            "interpretation": interpretation,
            "net_session_change": session_analysis.get("net_change_pct", 0),
            "session_volume_character": session_analysis.get("avg_volume", 0),
            "forecast": f"{alignment_signal}: {interpretation}"
        }

    @staticmethod
    def build_session_dashboard(
        daily_sessions: List[SessionOpen],
        weekly_sessions: Optional[List[SessionOpen]] = None,
        monthly_sessions: Optional[List[SessionOpen]] = None,
        current_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Build comprehensive session analysis dashboard.

        Args:
            daily_sessions: Daily session opens
            weekly_sessions: Optional weekly session opens
            monthly_sessions: Optional monthly session opens
            current_price: Current market price

        Returns:
            Complete dashboard with all session metrics
        """
        dashboard = {
            "timestamp": datetime.utcnow().isoformat(),
            "current_price": current_price,
            "daily": SessionOpeningAnalyzer.analyze_session_sequence(daily_sessions, "daily") if daily_sessions else {},
            "weekly": SessionOpeningAnalyzer.analyze_session_sequence(weekly_sessions, "weekly") if weekly_sessions else {},
            "monthly": SessionOpeningAnalyzer.analyze_session_sequence(monthly_sessions, "monthly") if monthly_sessions else {},
        }

        # Price vs opens for current price
        if current_price and daily_sessions:
            price_vs_daily = {}
            for session in daily_sessions:
                delta = current_price - session.open_price
                pct = (delta / session.open_price) * 100 if session.open_price > 0 else 0
                if abs(pct) < 0.05:
                    state = "near"
                elif delta > 0:
                    state = "above"
                else:
                    state = "below"
                price_vs_daily[session.session_type.value] = f"{state} ({pct:+.2f}%)"

            dashboard["price_vs_daily_opens"] = price_vs_daily
            character, strongest = SessionOpeningAnalyzer.determine_session_character(price_vs_daily)
            dashboard["daily_character"] = character.value
            dashboard["strongest_open"] = strongest.value

        return dashboard
