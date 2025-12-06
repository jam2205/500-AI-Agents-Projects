"""Economic Calendar Agent - monitors economic events and their impact."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from src.framework.base_agent import BaseAgent, AgentConfig, AgentRole, Message


class EconomicEvent:
    """Represents an economic calendar event."""

    def __init__(
        self,
        event_id: str,
        name: str,
        country: str,
        currency: str,
        importance: str,  # "high", "medium", "low"
        scheduled_time: str,
        actual_value: Optional[str] = None,
        forecast_value: Optional[str] = None,
        previous_value: Optional[str] = None,
        impact: Optional[str] = None
    ):
        self.event_id = event_id
        self.name = name
        self.country = country
        self.currency = currency
        self.importance = importance
        self.scheduled_time = scheduled_time
        self.actual_value = actual_value
        self.forecast_value = forecast_value
        self.previous_value = previous_value
        self.impact = impact  # "beats", "misses", "meets"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "name": self.name,
            "country": self.country,
            "currency": self.currency,
            "importance": self.importance,
            "scheduled_time": self.scheduled_time,
            "actual_value": self.actual_value,
            "forecast_value": self.forecast_value,
            "previous_value": self.previous_value,
            "impact": self.impact
        }


class EconomicCalendarAgent(BaseAgent):
    """Agent that monitors economic calendar and alerts other agents."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize the economic calendar agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_economic_system_prompt()

        super().__init__(config, message_bus)
        self.upcoming_events: List[EconomicEvent] = []
        self.processed_events: List[EconomicEvent] = []
        self.event_impact_history: Dict[str, List[Dict[str, Any]]] = {}
        self.alert_thresholds = {
            "high": 0.5,      # Alert at 50% variance
            "medium": 1.0,    # Alert at 100% variance
            "low": 2.0        # Alert at 200% variance
        }

    async def initialize(self):
        """Initialize the economic calendar agent."""
        self.state["status"] = "monitoring"
        self.state["events_tracked"] = 0

    def _get_economic_system_prompt(self) -> str:
        """Get system prompt for economic analysis."""
        return """You are an Economic Calendar Specialist agent in a multi-agent trading system.

Your responsibilities:
1. Monitor economic calendar events from major economies
2. Assess impact of economic data releases on forex, bonds, and equities
3. Alert other trading agents of high-impact events
4. Analyze actual vs. forecast data to identify market-moving surprises
5. Track economic trends and their implications for trading

You operate with real-time economic data and provide:
- Pre-event analysis and positioning recommendations
- Real-time impact assessment
- Post-event analysis and follow-up implications

Key considerations:
- High-importance events can move markets significantly
- Surprises (beats/misses vs. forecast) create trading opportunities
- Some events have cumulative effects
- Central bank decisions require special attention
- Seasonal patterns affect event importance"""

    async def add_event(self, event: EconomicEvent):
        """Add an event to monitor."""
        self.upcoming_events.append(event)
        self.state["events_tracked"] = len(self.upcoming_events)

    async def update_event(self, event_id: str, updates: Dict[str, Any]):
        """Update an event with actual data."""
        for event in self.upcoming_events:
            if event.event_id == event_id:
                if "actual_value" in updates:
                    event.actual_value = updates["actual_value"]
                if "impact" in updates:
                    event.impact = updates["impact"]
                if "importance" in updates:
                    event.importance = updates["importance"]

                # Analyze the event
                await self._analyze_event(event)
                return event

        return None

    async def _analyze_event(self, event: EconomicEvent):
        """Analyze an economic event and determine market impact."""
        if not event.actual_value or not event.forecast_value:
            return

        # Calculate variance
        try:
            actual = float(event.actual_value)
            forecast = float(event.forecast_value)

            if forecast == 0:
                variance = float('inf')
            else:
                variance = abs((actual - forecast) / forecast)

            # Determine impact
            threshold = self.alert_thresholds.get(event.importance, 1.0)

            if variance > threshold:
                if actual > forecast:
                    event.impact = "beats"
                else:
                    event.impact = "misses"

                # Generate alert
                await self._alert_market_participants(event, variance)
            else:
                event.impact = "meets"

        except (ValueError, ZeroDivisionError):
            pass

    async def _alert_market_participants(
        self,
        event: EconomicEvent,
        variance: float
    ):
        """Alert other agents about significant economic events."""
        alert_message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],  # Broadcast
            message_type="economic_alert",
            content={
                "event": event.to_dict(),
                "variance": variance,
                "severity": self._calculate_severity(event.importance, variance),
                "market_impact": await self._assess_market_impact(event),
                "recommended_actions": await self._generate_recommendations(event)
            }
        )
        await self.send_message(alert_message)

    def _calculate_severity(self, importance: str, variance: float) -> str:
        """Calculate alert severity."""
        if importance == "high" and variance > 0.5:
            return "critical"
        elif importance == "high" or variance > 1.0:
            return "high"
        elif importance == "medium" or variance > 0.5:
            return "medium"
        return "low"

    async def _assess_market_impact(self, event: EconomicEvent) -> Dict[str, Any]:
        """Assess market impact of the event."""
        analysis_prompt = f"""Analyze the market impact of this economic event:

Event: {event.name}
Country: {event.country}
Importance: {event.importance}
Actual: {event.actual_value}
Forecast: {event.forecast_value}
Previous: {event.previous_value}
Impact: {event.impact}

Provide impact assessment for:
1. Currency pairs (e.g., EUR/USD, GBP/USD)
2. Bond markets (yields and duration)
3. Equity markets
4. Implied volatility

Be specific about direction and magnitude of expected moves."""

        market_impact = await self.think(analysis_prompt)
        return {"impact_analysis": market_impact}

    async def _generate_recommendations(
        self,
        event: EconomicEvent
    ) -> List[str]:
        """Generate trading recommendations for the event."""
        rec_prompt = f"""Based on this economic event, generate specific trading recommendations:

Event: {event.name}
Impact: {event.impact}
Variance from forecast: Large

Provide 3-5 actionable trading recommendations for:
- Forex traders
- Bond traders
- Equity traders
- Risk managers

Format as bullet points with specific instrument names and actions."""

        recommendations = await self.think(rec_prompt)
        return [
            "See detailed recommendations in analysis",
            f"Event: {event.name}",
            f"Impact Type: {event.impact}",
            f"Importance: {event.importance}"
        ]

    async def get_upcoming_events(
        self,
        days_ahead: int = 7,
        importance: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get upcoming events."""
        events = []
        cutoff_date = datetime.utcnow() + timedelta(days=days_ahead)

        for event in self.upcoming_events:
            event_time = datetime.fromisoformat(event.scheduled_time)
            if event_time <= cutoff_date:
                if importance is None or event.importance == importance:
                    events.append(event.to_dict())

        return sorted(
            events,
            key=lambda x: x["scheduled_time"]
        )

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "monitor_events":
            return await self._monitor_events_task()
        elif task_type == "analyze_event":
            event_id = task.get("event_id")
            return await self._analyze_single_event(event_id)
        elif task_type == "get_events":
            return {
                "upcoming_events": await self.get_upcoming_events(),
                "processed_events": len(self.processed_events)
            }

        return {"error": "Unknown task type"}

    async def _monitor_events_task(self) -> Dict[str, Any]:
        """Monitor upcoming events."""
        now = datetime.utcnow()
        upcoming_24h = []

        for event in self.upcoming_events:
            event_time = datetime.fromisoformat(event.scheduled_time)
            time_until = (event_time - now).total_seconds()

            if 0 < time_until < 86400:  # Within 24 hours
                upcoming_24h.append({
                    "event": event.to_dict(),
                    "minutes_until": int(time_until / 60)
                })

        if upcoming_24h:
            await self.broadcast_upcoming_events(upcoming_24h)

        return {
            "status": "monitoring",
            "events_in_24h": len(upcoming_24h)
        }

    async def broadcast_upcoming_events(self, events: List[Dict[str, Any]]):
        """Broadcast upcoming events to all agents."""
        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],  # Broadcast
            message_type="upcoming_events_24h",
            content={"events": events}
        )
        await self.send_message(message)

    async def _analyze_single_event(self, event_id: str) -> Dict[str, Any]:
        """Analyze a single event."""
        for event in self.upcoming_events + self.processed_events:
            if event.event_id == event_id:
                analysis = await self.analyze(event.to_dict())
                return analysis

        return {"error": f"Event {event_id} not found"}
