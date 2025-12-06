"""Volume & Seasonality Agents - Market volume analysis aligned with seasonal patterns."""

import json
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from src.framework.base_agent import BaseAgent, AgentConfig, AgentRole, Message


class MarketVolumeMonitorAgent(BaseAgent):
    """Monitors market volumes across all asset classes and detects anomalies."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize market volume monitor agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_volume_system_prompt()
        super().__init__(config, message_bus)
        self.volume_history: Dict[str, deque] = {}
        self.volume_anomalies: List[Dict[str, Any]] = []
        self.market_volume_stats: Dict[str, Dict[str, float]] = {}
        self.volume_spikes: Dict[str, List[Dict[str, Any]]] = {}

    def _get_volume_system_prompt(self) -> str:
        """Get system prompt for volume monitor."""
        return """You are a Market Volume Specialist in a multi-agent trading system.

Your expertise:
1. Real-time volume monitoring across all asset classes
2. Volume anomaly detection (unusual activity)
3. Volume-weighted price analysis
4. Market participation levels by time and season
5. Volume trending and persistence

Your responsibilities:
- Track volumes across FX majors/crosses, bonds, equities, commodities
- Identify volume spikes indicating conviction or distribution
- Detect low-volume periods (market holidays, vacations)
- Monitor participation rate changes
- Alert when volume patterns deviate from normal
- Assess market liquidity conditions

Key metrics:
- Current volume vs 20-day average
- Volume momentum (accelerating/decelerating)
- Volume distribution (who's active - hedgers, specs, dealers)
- Volume-price relationship (confirmation or divergence)
- Session volume patterns (Tokyo, London, New York)"""

    async def update_volume(
        self,
        symbol: str,
        volume: float,
        timestamp: str,
        market_type: str = "forex"
    ):
        """Update volume data for a symbol."""
        if symbol not in self.volume_history:
            self.volume_history[symbol] = deque(maxlen=100)
            self.volume_spikes[symbol] = []

        volume_point = {
            "volume": volume,
            "timestamp": timestamp,
            "market_type": market_type
        }
        self.volume_history[symbol].append(volume_point)

        # Calculate statistics
        await self._calculate_volume_stats(symbol)

        # Check for anomalies
        await self._detect_volume_anomalies(symbol, volume)

    async def _calculate_volume_stats(self, symbol: str):
        """Calculate volume statistics."""
        if len(self.volume_history[symbol]) < 3:
            return

        volumes = [p["volume"] for p in list(self.volume_history[symbol])[-20:]]

        avg_volume = sum(volumes) / len(volumes)
        current_volume = volumes[-1]
        previous_volume = volumes[-2] if len(volumes) > 1 else avg_volume

        # Volume momentum
        volume_momentum = ((current_volume - avg_volume) / avg_volume) * 100 if avg_volume > 0 else 0

        self.market_volume_stats[symbol] = {
            "current_volume": current_volume,
            "average_volume": avg_volume,
            "volume_momentum_pct": volume_momentum,
            "volume_trend": "increasing" if current_volume > previous_volume else "decreasing",
            "volume_vs_avg": (current_volume / avg_volume) if avg_volume > 0 else 0
        }

    async def _detect_volume_anomalies(self, symbol: str, current_volume: float):
        """Detect volume anomalies."""
        if symbol not in self.market_volume_stats:
            return

        stats = self.market_volume_stats[symbol]
        volume_vs_avg = stats["volume_vs_avg"]

        # Check for spikes (>2x average) or droughts (<0.5x average)
        anomaly = None

        if volume_vs_avg > 2.0:
            anomaly = {
                "type": "volume_spike",
                "symbol": symbol,
                "magnitude": volume_vs_avg,
                "timestamp": datetime.utcnow().isoformat(),
                "volume": current_volume,
                "average": stats["average_volume"]
            }
        elif volume_vs_avg < 0.5:
            anomaly = {
                "type": "volume_drought",
                "symbol": symbol,
                "magnitude": volume_vs_avg,
                "timestamp": datetime.utcnow().isoformat(),
                "volume": current_volume,
                "average": stats["average_volume"]
            }

        if anomaly:
            self.volume_anomalies.append(anomaly)
            self.volume_spikes[symbol].append(anomaly)
            await self._broadcast_volume_alert(symbol, anomaly)

    async def _broadcast_volume_alert(self, symbol: str, anomaly: Dict[str, Any]):
        """Broadcast volume anomaly alert."""
        analysis_prompt = f"""Analyze this volume anomaly:

Symbol: {symbol}
Anomaly Type: {anomaly.get('type')}
Current Volume: {anomaly.get('volume')}
Historical Average: {anomaly.get('average')}
Magnitude: {anomaly.get('magnitude', 0):.2f}x average

Provide:
1. What likely caused this volume move
2. Market impact implications
3. Expected duration of anomaly
4. Trading implications (conviction vs noise)
5. Related instruments affected"""

        anomaly_analysis = await self.think(analysis_prompt)

        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],
            message_type="volume_anomaly_alert",
            content={
                "anomaly": anomaly,
                "analysis": anomaly_analysis,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await self.send_message(message)

    async def get_volume_stats(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get volume statistics."""
        if symbol:
            return self.market_volume_stats.get(symbol, {})

        return {pair: self.market_volume_stats[pair] for pair in self.market_volume_stats}

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "update_volume":
            await self.update_volume(
                task.get("symbol"),
                task.get("volume"),
                task.get("timestamp", datetime.utcnow().isoformat()),
                task.get("market_type", "forex")
            )
            return {"status": "volume_updated"}

        elif task_type == "get_stats":
            return {"stats": await self.get_volume_stats(task.get("symbol"))}

        elif task_type == "analyze_volume":
            symbol = task.get("symbol")
            analysis = await self.analyze(self.market_volume_stats.get(symbol, {}))
            return analysis

        return {"error": "Unknown task type"}


class SeasonalPatternAgent(BaseAgent):
    """Analyzes seasonal patterns and their historical impact on markets."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize seasonal pattern agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_seasonal_system_prompt()
        super().__init__(config, message_bus)
        self.seasonal_patterns: Dict[str, Dict[str, Any]] = {}
        self.historical_data: Dict[str, deque] = {}
        self.current_season: str = self._determine_current_season()
        self.seasonal_trades: List[Dict[str, Any]] = []

    def _get_seasonal_system_prompt(self) -> str:
        """Get system prompt for seasonal patterns."""
        return """You are a Seasonal Pattern Specialist in a multi-agent trading system.

Your expertise:
1. Seasonal patterns in markets (quarter-end, month-end, year-end)
2. Calendar effects (day-of-week, time-of-month, holiday patterns)
3. Historical seasonal performance by asset class
4. Seasonal volatility changes
5. Seasonal reversion and persistence

Your responsibilities:
- Track historical seasonal patterns
- Identify which periods show consistent trading biases
- Forecast seasonal strength/weakness
- Alert traders to seasonal turning points
- Assess seasonal effect persistence this year
- Adjust expectations for seasonal anomalies

Key seasonal periods:
- Month-end (often strong close into month-end)
- Quarter-end (position squaring, rebalancing)
- Year-end (window dressing, year-end rallies)
- Holiday periods (reduced liquidity, seasonal themes)
- Tax-loss harvesting season (late December)
- Summer doldrums (July-August volatility drops)
- Santa Claus rally (Dec 25 - Jan 6)
- Seasonality by hemisphere (northern vs southern)"""

    def _determine_current_season(self) -> str:
        """Determine current season."""
        month = datetime.utcnow().month

        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "autumn"

    async def record_seasonal_data(
        self,
        symbol: str,
        date: str,
        value: float,
        volume: Optional[float] = None
    ):
        """Record historical data for seasonal analysis."""
        if symbol not in self.historical_data:
            self.historical_data[symbol] = deque(maxlen=1000)

        self.historical_data[symbol].append({
            "date": date,
            "value": value,
            "volume": volume,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def identify_seasonal_patterns(self, symbol: str) -> Dict[str, Any]:
        """Identify seasonal patterns from historical data."""
        if symbol not in self.historical_data:
            return {"error": f"No historical data for {symbol}"}

        data = list(self.historical_data[symbol])

        if len(data) < 100:
            return {"error": "Insufficient data for seasonal analysis"}

        analysis_prompt = f"""Analyze seasonal patterns for {symbol}:

Historical Data Points: {len(data)}
Date Range: {data[0]['date']} to {data[-1]['date']}

Analyze:
1. Month-of-year patterns (which months are strongest/weakest)
2. Quarter-end effects (position changes into/out of quarter-end)
3. Year-end patterns (Santa Claus rally, year-end rallies)
4. Holiday effects (returns around major holidays)
5. Day-of-week patterns (if applicable)
6. Strength of seasonal patterns (consistency and magnitude)
7. Recent changes to seasonal patterns (is seasonality breaking down?)

Provide specific return expectations by seasonal period."""

        seasonal_analysis = await self.think(analysis_prompt)

        self.seasonal_patterns[symbol] = {
            "symbol": symbol,
            "analysis": seasonal_analysis,
            "timestamp": datetime.utcnow().isoformat(),
            "data_points": len(data)
        }

        return {
            "symbol": symbol,
            "seasonal_analysis": seasonal_analysis,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def forecast_seasonal_behavior(self, symbol: str) -> Dict[str, Any]:
        """Forecast expected behavior based on seasonal patterns."""
        if symbol not in self.seasonal_patterns:
            return {"error": f"No seasonal patterns identified for {symbol}"}

        pattern = self.seasonal_patterns[symbol]
        current_season = self._determine_current_season()

        forecast_prompt = f"""Forecast seasonal behavior for {symbol}:

Current Season: {current_season}
Current Month: {datetime.utcnow().strftime('%B')}
Current Day: {datetime.utcnow().strftime('%A')}

Historical Patterns:
{pattern.get('analysis', '')}

Provide:
1. Expected return direction for current period
2. Probability of seasonal strength (high/medium/low)
3. Key seasonal dates to watch
4. When seasonal pattern might reverse
5. Trading recommendations based on seasonality
6. Risk factors (when seasonality might fail)
7. Confluence with other seasonal signals"""

        seasonal_forecast = await self.think(forecast_prompt)

        return {
            "symbol": symbol,
            "season": current_season,
            "forecast": seasonal_forecast,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "record_data":
            await self.record_seasonal_data(
                task.get("symbol"),
                task.get("date"),
                task.get("value"),
                task.get("volume")
            )
            return {"status": "data_recorded"}

        elif task_type == "identify_patterns":
            result = await self.identify_seasonal_patterns(task.get("symbol"))
            return result

        elif task_type == "forecast":
            result = await self.forecast_seasonal_behavior(task.get("symbol"))
            return result

        return {"error": "Unknown task type"}


class VolumeSeasonalSyncAgent(BaseAgent):
    """Correlates volume patterns with seasonal patterns for trading signals."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize volume-seasonal sync agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_sync_system_prompt()
        super().__init__(config, message_bus)
        self.volume_seasonal_signals: List[Dict[str, Any]] = []
        self.sync_events: List[Dict[str, Any]] = []
        self.trading_recommendations: Dict[str, Dict[str, Any]] = {}

    def _get_sync_system_prompt(self) -> str:
        """Get system prompt for volume-seasonal sync."""
        return """You are a Volume-Seasonal Synchronization Specialist in a multi-agent trading system.

Your expertise:
1. Correlating volume patterns with seasonal patterns
2. Identifying when both confirm each other (strong signals)
3. Detecting when they diverge (warning signs)
4. Volume distribution across seasonal periods
5. Seasonal volume changes (holidays, vacation seasons)

Your responsibilities:
- Monitor volume-seasonal alignment
- Alert when both confirm strong moves
- Warn when divergences suggest caution
- Assess reliability of seasonal signals based on volume
- Recommend positioning based on confluence
- Track how volumes have changed by season over time

Key patterns:
- Low volume + strong seasonal trend = less reliable
- High volume + seasonal trend = strong signal
- Volume spike against seasonal trend = warning (reversal coming)
- Declining volume into seasonal event = distribution
- Rising volume into seasonal event = accumulation
- Seasonal holidays = volume typically drops (beware thin markets)"""

    async def analyze_volume_seasonal_sync(
        self,
        symbol: str,
        current_volume: float,
        volume_average: float,
        seasonal_forecast: str,
        current_season: str
    ) -> Dict[str, Any]:
        """Analyze volume-seasonal synchronization."""
        analysis_prompt = f"""Analyze volume-seasonal synchronization for {symbol}:

Current Volume: {current_volume}
Volume Average: {volume_average}
Volume Multiple: {(current_volume / volume_average):.2f}x

Current Season: {current_season}
Seasonal Forecast: {seasonal_forecast}

Provide:
1. Alignment score (0-100): how well do volume and seasonality align?
2. Signal strength: does this create a tradeable opportunity?
3. Conviction level: high/medium/low
4. Recommended action (BUY/SELL/HOLD/CAUTION)
5. Risk factors (when this could fail)
6. Expected move if signal is correct
7. Time frame for expected move
8. Confluence with other market factors"""

        sync_analysis = await self.think(analysis_prompt)

        signal = {
            "symbol": symbol,
            "volume": current_volume,
            "volume_multiple": current_volume / volume_average if volume_average > 0 else 0,
            "season": current_season,
            "seasonal_forecast": seasonal_forecast,
            "analysis": sync_analysis,
            "timestamp": datetime.utcnow().isoformat()
        }

        self.volume_seasonal_signals.append(signal)

        # Broadcast signal if it's strong
        if "HIGH" in sync_analysis.upper() or "STRONG" in sync_analysis.upper():
            await self._broadcast_sync_alert(signal)

        return signal

    async def _broadcast_sync_alert(self, signal: Dict[str, Any]):
        """Broadcast volume-seasonal sync alert."""
        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],
            message_type="volume_seasonal_sync_alert",
            content=signal
        )
        await self.send_message(message)

    async def identify_seasonal_volume_anomalies(
        self,
        symbol: str,
        historical_seasonal_volumes: Dict[str, float],
        current_volume: float,
        current_season: str
    ) -> Dict[str, Any]:
        """Identify when volume is anomalous for the season."""
        anomaly_prompt = f"""Identify seasonal volume anomalies for {symbol}:

Current Season: {current_season}
Current Volume: {current_volume}

Historical Seasonal Averages:
{json.dumps(historical_seasonal_volumes, indent=2)}

Season Average: {historical_seasonal_volumes.get(current_season, 'unknown')}

Provide:
1. Is current volume abnormal for this season? (YES/NO)
2. How much above/below seasonal average?
3. What could cause this anomaly?
4. What does it suggest about market interest?
5. How unusual is this (1st percentile, unusual, normal)?
6. Trading implications
7. Expected duration of anomaly"""

        anomaly_analysis = await self.think(anomaly_prompt)

        return {
            "symbol": symbol,
            "season": current_season,
            "current_volume": current_volume,
            "seasonal_average": historical_seasonal_volumes.get(current_season),
            "anomaly_analysis": anomaly_analysis,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def recommend_seasonal_trades(
        self,
        symbol: str,
        volume_condition: str,
        seasonal_outlook: str
    ) -> List[Dict[str, Any]]:
        """Recommend trades based on volume-seasonal confluence."""
        recommendation_prompt = f"""Recommend seasonal trades for {symbol}:

Volume Condition: {volume_condition}
Seasonal Outlook: {seasonal_outlook}

Provide specific trading recommendations:
1. Primary trade idea (BUY/SELL/HOLD)
2. Entry zones
3. Position sizing (relative to normal)
4. Stop loss levels
5. Profit targets
6. Time horizon
7. Expected confidence level
8. Key risks
9. Conditions that would invalidate the trade
10. Seasonal calendar events to watch"""

        recommendations = await self.think(recommendation_prompt)

        return [
            {
                "symbol": symbol,
                "volume_condition": volume_condition,
                "seasonal_outlook": seasonal_outlook,
                "recommendations": recommendations,
                "timestamp": datetime.utcnow().isoformat()
            }
        ]

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "analyze_sync":
            result = await self.analyze_volume_seasonal_sync(
                task.get("symbol"),
                task.get("current_volume"),
                task.get("volume_average"),
                task.get("seasonal_forecast"),
                task.get("current_season")
            )
            return result

        elif task_type == "identify_anomalies":
            result = await self.identify_seasonal_volume_anomalies(
                task.get("symbol"),
                task.get("historical_seasonal_volumes", {}),
                task.get("current_volume"),
                task.get("current_season")
            )
            return result

        elif task_type == "recommend_trades":
            result = await self.recommend_seasonal_trades(
                task.get("symbol"),
                task.get("volume_condition"),
                task.get("seasonal_outlook")
            )
            return result

        return {"error": "Unknown task type"}
