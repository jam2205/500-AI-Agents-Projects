"""Market Profile Agent - tracks weekly highs/lows and market structure."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from src.framework.base_agent import BaseAgent, AgentConfig, AgentRole, Message


@dataclass
class WeeklyProfile:
    """Weekly market profile structure."""
    week_start: str
    week_end: str
    high: float
    low: float
    high_time: str
    low_time: str
    close: float
    volume: int
    direction: str  # "up", "down", "sideways"
    profile_type: str  # "bull", "bear", "balanced"
    key_levels: Dict[str, float]
    alerts_generated: List[str]


class MarketProfileAgent(BaseAgent):
    """Agent that tracks market profile and price structure."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize the market profile agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_profile_system_prompt()

        super().__init__(config, message_bus)
        self.current_week_profile: Optional[WeeklyProfile] = None
        self.previous_week_profile: Optional[WeeklyProfile] = None
        self.price_history: List[Dict[str, Any]] = []
        self.weekly_profiles_history: List[WeeklyProfile] = []
        self.session_highs: Dict[str, float] = {}
        self.session_lows: Dict[str, float] = {}

    async def initialize(self):
        """Initialize the market profile agent."""
        self.state["status"] = "tracking"
        self.state["profiles_tracked"] = 0

    def _get_profile_system_prompt(self) -> str:
        """Get system prompt for market profile analysis."""
        return """You are a Market Profile Specialist agent in a multi-agent trading system.

Your responsibilities:
1. Track market structure (weekly highs, lows, and key levels)
2. Identify market direction and bias
3. Monitor price proximity to key levels
4. Alert other agents about directional changes and level breaks
5. Provide market context for trading decisions

You analyze:
- Weekly price structure (support/resistance)
- Trading range development
- Volume-weighted price levels
- Market bias (bullish, bearish, balanced)
- Key decision points

Your alerts guide:
- Market makers on liquidity provision strategies
- Traders on directional positioning
- Risk managers on level breaks
- Strategy developers on pattern identification"""

    async def update_price(
        self,
        symbol: str,
        price: float,
        timestamp: str,
        volume: Optional[int] = None,
        bid_ask: Optional[tuple] = None
    ):
        """Update price data."""
        price_point = {
            "symbol": symbol,
            "price": price,
            "timestamp": timestamp,
            "volume": volume,
            "bid_ask": bid_ask
        }
        self.price_history.append(price_point)

        # Update session tracking
        date_key = timestamp.split("T")[0]
        if date_key not in self.session_highs:
            self.session_highs[date_key] = price
            self.session_lows[date_key] = price
        else:
            self.session_highs[date_key] = max(self.session_highs[date_key], price)
            self.session_lows[date_key] = min(self.session_lows[date_key], price)

        # Check for key level breaks
        await self._check_key_level_breaks(symbol, price)

    async def _check_key_level_breaks(self, symbol: str, price: float):
        """Check if price is breaking key levels."""
        if not self.current_week_profile:
            return

        alerts = []

        # Check vs weekly high
        if price > self.current_week_profile.high:
            alerts.append(f"BREAK: Weekly high broken at {price}")
            self.current_week_profile.high = price
            self.current_week_profile.high_time = datetime.utcnow().isoformat()

        # Check vs weekly low
        if price < self.current_week_profile.low:
            alerts.append(f"BREAK: Weekly low broken at {price}")
            self.current_week_profile.low = price
            self.current_week_profile.low_time = datetime.utcnow().isoformat()

        # Alert if key level broken
        if alerts:
            await self._broadcast_level_alerts(symbol, price, alerts)

    async def _broadcast_level_alerts(
        self,
        symbol: str,
        price: float,
        alerts: List[str]
    ):
        """Broadcast level break alerts to all agents."""
        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],  # Broadcast
            message_type="market_level_alert",
            content={
                "symbol": symbol,
                "price": price,
                "alerts": alerts,
                "timestamp": datetime.utcnow().isoformat(),
                "profile": self._profile_to_dict(self.current_week_profile) if self.current_week_profile else None
            }
        )
        await self.send_message(message)

    async def set_weekly_profile(self, profile: WeeklyProfile):
        """Set the current week's profile."""
        self.previous_week_profile = self.current_week_profile
        self.current_week_profile = profile

        if self.previous_week_profile:
            self.weekly_profiles_history.append(self.previous_week_profile)

        # Generate directional alert
        await self._broadcast_weekly_profile_update(profile)

        self.state["profiles_tracked"] = len(self.weekly_profiles_history) + 1

    async def _broadcast_weekly_profile_update(self, profile: WeeklyProfile):
        """Broadcast weekly profile update to all agents."""
        # Analyze profile characteristics
        analysis_prompt = f"""Analyze this weekly market profile and provide brief strategic insights:

Week: {profile.week_start} to {profile.week_end}
High: {profile.high}
Low: {profile.low}
Direction: {profile.direction}
Profile Type: {profile.profile_type}

Provide:
1. One-line market bias assessment
2. Key trading levels to watch
3. Risk zones to avoid
4. Probability of continuation vs reversal"""

        strategic_insights = await self.think(analysis_prompt)

        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],  # Broadcast
            message_type="weekly_profile_update",
            content={
                "profile": self._profile_to_dict(profile),
                "strategic_insights": strategic_insights,
                "timestamp": datetime.utcnow().isoformat(),
                "direction_for_week": profile.direction
            }
        )
        await self.send_message(message)

    def _profile_to_dict(self, profile: WeeklyProfile) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "week_start": profile.week_start,
            "week_end": profile.week_end,
            "high": profile.high,
            "low": profile.low,
            "high_time": profile.high_time,
            "low_time": profile.low_time,
            "close": profile.close,
            "volume": profile.volume,
            "direction": profile.direction,
            "profile_type": profile.profile_type,
            "key_levels": profile.key_levels,
            "range": profile.high - profile.low
        }

    async def get_weekly_profile_for_week(
        self,
        week_start: str
    ) -> Optional[Dict[str, Any]]:
        """Get weekly profile for a specific week."""
        if self.current_week_profile and self.current_week_profile.week_start == week_start:
            return self._profile_to_dict(self.current_week_profile)

        for profile in self.weekly_profiles_history:
            if profile.week_start == week_start:
                return self._profile_to_dict(profile)

        return None

    async def get_recent_profiles(self, num_weeks: int = 4) -> List[Dict[str, Any]]:
        """Get recent weekly profiles."""
        profiles = []

        if self.current_week_profile:
            profiles.append(self._profile_to_dict(self.current_week_profile))

        # Add from history (most recent first)
        for profile in reversed(self.weekly_profiles_history[-num_weeks:]):
            profiles.append(self._profile_to_dict(profile))

        return profiles

    async def identify_key_levels(self, symbol: str) -> Dict[str, float]:
        """Identify key levels from price history."""
        if not self.price_history:
            return {}

        prices = [p["price"] for p in self.price_history]
        high = max(prices)
        low = min(prices)
        mid = (high + low) / 2

        # Calculate pivots
        previous_high = high
        previous_low = low
        previous_close = prices[-1] if prices else 0

        pivot = (previous_high + previous_low + previous_close) / 3
        r1 = (2 * pivot) - previous_low
        s1 = (2 * pivot) - previous_high
        r2 = pivot + (previous_high - previous_low)
        s2 = pivot - (previous_high - previous_low)

        return {
            "high": high,
            "low": low,
            "mid": mid,
            "pivot": pivot,
            "resistance_1": r1,
            "support_1": s1,
            "resistance_2": r2,
            "support_2": s2
        }

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "update_profile":
            profile = task.get("profile")
            await self.set_weekly_profile(profile)
            return {"status": "profile_updated"}

        elif task_type == "get_current_profile":
            if self.current_week_profile:
                return self._profile_to_dict(self.current_week_profile)
            return {"status": "no_profile"}

        elif task_type == "identify_levels":
            symbol = task.get("symbol", "unknown")
            levels = await self.identify_key_levels(symbol)
            return {"symbol": symbol, "key_levels": levels}

        elif task_type == "get_recent_profiles":
            weeks = task.get("weeks", 4)
            return {
                "recent_profiles": await self.get_recent_profiles(weeks)
            }

        return {"error": "Unknown task type"}

    async def get_market_direction_alert(self) -> Dict[str, Any]:
        """Get current market direction alert for broadcast."""
        if not self.current_week_profile:
            return {"status": "no_profile"}

        direction_prompt = f"""Based on this weekly profile, determine where price is heading:

Current Week:
- High: {self.current_week_profile.high}
- Low: {self.current_week_profile.low}
- Direction: {self.current_week_profile.direction}
- Type: {self.current_week_profile.profile_type}

Previous Week (if available):
- Direction: {self.previous_week_profile.direction if self.previous_week_profile else 'N/A'}

Provide:
1. Current directional bias (BULLISH/BEARISH/NEUTRAL)
2. Key level being tested
3. Probability of breaking high vs low
4. Alert for all trading groups"""

        direction_analysis = await self.think(direction_prompt)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "current_profile": self._profile_to_dict(self.current_week_profile),
            "directional_analysis": direction_analysis,
            "direction": self.current_week_profile.direction
        }

    async def broadcast_market_direction(self):
        """Broadcast market direction to all agents."""
        alert = await self.get_market_direction_alert()

        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],  # Broadcast
            message_type="market_direction_alert",
            content=alert
        )
        await self.send_message(message)
