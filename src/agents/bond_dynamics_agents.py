"""Short-Term Bond Dynamics Agents - Leading indicators for FX moves."""

import json
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from src.framework.base_agent import BaseAgent, AgentConfig, AgentRole, Message


class ShortTermBondMonitorAgent(BaseAgent):
    """Monitors short-term bond yields (2Y/3Y) and detects market-moving shifts."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize short-term bond monitor agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_bond_monitor_system_prompt()
        super().__init__(config, message_bus)
        self.yield_history: Dict[str, deque] = {
            "2Y": deque(maxlen=100),
            "3Y": deque(maxlen=100),
            "2Y3Y_spread": deque(maxlen=100)
        }
        self.momentum_indicators: Dict[str, float] = {}
        self.volatility_levels: Dict[str, float] = {}
        self.significant_moves: List[Dict[str, Any]] = []

    def _get_bond_monitor_system_prompt(self) -> str:
        """Get system prompt for short-term bond monitor."""
        return """You are a Short-Term Bond Market Specialist in a multi-agent trading system.

Your expertise:
1. 2Y and 3Y yield movements and their market impact
2. 2Y/3Y spread analysis and inversion signals
3. Momentum detection in yield curves
4. Volatility spikes in short-term rates
5. Market-moving vs noise differentiation

Your responsibilities:
- Track real-time 2Y/3Y yield movements
- Detect momentum shifts in short-term bonds
- Identify significant moves (>10bps moves)
- Monitor 2Y/3Y spread for curve shape changes
- Alert when bonds are moving the market
- Provide momentum indicators for other agents

Key signals you monitor:
- 2Y yield accelerating higher/lower
- 3Y yield diverging from 2Y
- 2Y/3Y spread widening/narrowing
- Velocity of yield moves (momentum)
- Volatility spikes indicating uncertainty
- Fed policy expectation changes reflected in 2Y"""

    async def update_yields(
        self,
        yield_2y: float,
        yield_3y: float,
        timestamp: str
    ):
        """Update yield data."""
        spread = yield_3y - yield_2y

        # Store in history
        self.yield_history["2Y"].append({
            "value": yield_2y,
            "timestamp": timestamp
        })
        self.yield_history["3Y"].append({
            "value": yield_3y,
            "timestamp": timestamp
        })
        self.yield_history["2Y3Y_spread"].append({
            "value": spread,
            "timestamp": timestamp
        })

        # Calculate momentum
        await self._calculate_momentum(yield_2y, yield_3y, spread)

        # Check for significant moves
        await self._detect_significant_moves(yield_2y, yield_3y, spread)

    async def _calculate_momentum(
        self,
        yield_2y: float,
        yield_3y: float,
        spread: float
    ):
        """Calculate momentum indicators."""
        if len(self.yield_history["2Y"]) < 3:
            return

        # Get last 3 values
        yields_2y = [p["value"] for p in list(self.yield_history["2Y"])[-3:]]
        yields_3y = [p["value"] for p in list(self.yield_history["3Y"])[-3:]]
        spreads = [p["value"] for p in list(self.yield_history["2Y3Y_spread"])[-3:]]

        # Calculate momentum (change over time)
        momentum_2y = yields_2y[-1] - yields_2y[0] if len(yields_2y) >= 2 else 0
        momentum_3y = yields_3y[-1] - yields_3y[0] if len(yields_3y) >= 2 else 0
        momentum_spread = spreads[-1] - spreads[0] if len(spreads) >= 2 else 0

        self.momentum_indicators = {
            "2Y_momentum": momentum_2y,
            "3Y_momentum": momentum_3y,
            "spread_momentum": momentum_spread,
            "direction_2Y": "rising" if momentum_2y > 0 else "falling",
            "direction_3Y": "rising" if momentum_3y > 0 else "falling",
            "spread_direction": "widening" if momentum_spread > 0 else "narrowing"
        }

        self.state["last_momentum"] = self.momentum_indicators

    async def _detect_significant_moves(
        self,
        yield_2y: float,
        yield_3y: float,
        spread: float
    ):
        """Detect significant yield moves."""
        if len(self.yield_history["2Y"]) < 2:
            return

        # Get previous values
        prev_2y = list(self.yield_history["2Y"])[-2]["value"]
        prev_3y = list(self.yield_history["3Y"])[-2]["value"]

        # Check for moves > 5bps
        move_2y = abs(yield_2y - prev_2y) * 100  # Convert to bps
        move_3y = abs(yield_3y - prev_3y) * 100

        significant_moves = []

        if move_2y > 5:
            significant_moves.append({
                "maturity": "2Y",
                "move_bps": move_2y,
                "direction": "up" if yield_2y > prev_2y else "down",
                "new_level": yield_2y
            })

        if move_3y > 5:
            significant_moves.append({
                "maturity": "3Y",
                "move_bps": move_3y,
                "direction": "up" if yield_3y > prev_3y else "down",
                "new_level": yield_3y
            })

        if significant_moves:
            self.significant_moves.append({
                "timestamp": datetime.utcnow().isoformat(),
                "moves": significant_moves
            })

            # Alert other agents
            await self._broadcast_significant_move_alert(significant_moves)

    async def _broadcast_significant_move_alert(self, moves: List[Dict[str, Any]]):
        """Broadcast alert about significant bond moves."""
        analysis_prompt = f"""Analyze this significant short-term bond move:

Moves:
{json.dumps(moves, indent=2)}

Momentum:
{json.dumps(self.momentum_indicators, indent=2)}

Provide assessment of:
1. Significance of the move
2. Likely driver (Fed expectation, data, technical, flows)
3. Market impact probability
4. FX currency pairs likely affected
5. Expected lag time to FX reaction"""

        impact_analysis = await self.think(analysis_prompt)

        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],  # Broadcast
            message_type="bond_momentum_alert",
            content={
                "moves": moves,
                "momentum": self.momentum_indicators,
                "impact_analysis": impact_analysis,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await self.send_message(message)

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "update_yields":
            await self.update_yields(
                task.get("yield_2y"),
                task.get("yield_3y"),
                task.get("timestamp", datetime.utcnow().isoformat())
            )
            return {"status": "yields_updated"}

        elif task_type == "get_momentum":
            return {
                "momentum": self.momentum_indicators,
                "recent_moves": self.significant_moves[-5:] if self.significant_moves else []
            }

        elif task_type == "analyze_momentum":
            analysis = await self.analyze(self.momentum_indicators)
            return analysis

        return {"error": "Unknown task type"}


class BondFXCorrelationAgent(BaseAgent):
    """Monitors correlation between short-term bonds and major FX pairs."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize bond-FX correlation agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_correlation_system_prompt()
        super().__init__(config, message_bus)
        self.correlations: Dict[str, Dict[str, float]] = {}
        self.correlation_history: Dict[str, deque] = {}
        self.correlation_breaks: List[Dict[str, Any]] = []
        self.major_pairs = ["EUR/USD", "GBP/USD", "JPY/USD", "AUD/USD", "NZD/USD"]
        self.crosses = ["EUR/GBP", "EUR/AUD", "GBP/AUD", "EUR/JPY"]

        # Initialize history tracking
        for pair in self.major_pairs + self.crosses:
            self.correlation_history[pair] = deque(maxlen=20)

    def _get_correlation_system_prompt(self) -> str:
        """Get system prompt for correlation agent."""
        return """You are a Bond-FX Correlation Specialist in a multi-agent trading system.

Your expertise:
1. Bond-currency pair relationships (2Y/3Y yields vs FX)
2. Normal vs distressed correlations
3. Correlation breakdown detection
4. Leading vs lagging relationships
5. Cross-correlation analysis (EUR, GBP, AUD, NZD)

Your responsibilities:
- Monitor real-time correlations between bonds and FX
- Detect when bonds lead currency movements
- Identify correlation breakdowns (mean reversion opportunities)
- Track which pairs move first when bonds move
- Alert when correlations strengthen or weaken
- Assess regime changes in bond-FX dynamics

Key relationships:
- Rising 2Y yields typically USD strength (positive correlation with USD pairs)
- 2Y yield > 3Y spread inversion can precede risk-off
- Rising carry pairs (AUD, NZD) correlate with risk appetite
- Inverse correlations with JPY during risk-off
- Cross correlations reveal relative central bank divergence"""

    async def update_correlation(
        self,
        pair: str,
        bond_metric: float,
        fx_price: float,
        timestamp: str
    ):
        """Update correlation data for a pair."""
        # Calculate correlation with recent history
        if pair not in self.correlation_history:
            self.correlation_history[pair] = deque(maxlen=20)

        self.correlation_history[pair].append({
            "bond_metric": bond_metric,
            "fx_price": fx_price,
            "timestamp": timestamp
        })

        # Calculate correlation if we have enough data
        if len(self.correlation_history[pair]) >= 5:
            correlation = self._calculate_correlation(pair)
            self.correlations[pair] = correlation

            # Check for correlation changes
            await self._check_correlation_change(pair, correlation)

    def _calculate_correlation(self, pair: str) -> float:
        """Calculate correlation between bonds and FX pair."""
        history = list(self.correlation_history[pair])

        if len(history) < 2:
            return 0.0

        bond_values = [h["bond_metric"] for h in history]
        fx_values = [h["fx_price"] for h in history]

        # Simple correlation calculation
        if len(bond_values) != len(fx_values):
            return 0.0

        # Normalize
        bond_mean = sum(bond_values) / len(bond_values)
        fx_mean = sum(fx_values) / len(fx_values)

        numerator = sum(
            (bond_values[i] - bond_mean) * (fx_values[i] - fx_mean)
            for i in range(len(bond_values))
        )

        bond_std = (sum((x - bond_mean) ** 2 for x in bond_values)) ** 0.5
        fx_std = (sum((x - fx_mean) ** 2 for x in fx_values)) ** 0.5

        if bond_std == 0 or fx_std == 0:
            return 0.0

        correlation = numerator / (bond_std * fx_std)
        return min(1.0, max(-1.0, correlation))  # Clamp to [-1, 1]

    async def _check_correlation_change(self, pair: str, current_correlation: float):
        """Check if correlation has changed significantly."""
        # Get previous correlation if available
        if len(self.correlation_history[pair]) >= 10:
            prev_history = list(self.correlation_history[pair])[-10:-5]
            if prev_history:
                prev_correlation = self._calculate_correlation_from_history(prev_history)

                if abs(current_correlation - prev_correlation) > 0.3:
                    await self._alert_correlation_shift(
                        pair,
                        prev_correlation,
                        current_correlation
                    )

    def _calculate_correlation_from_history(self, history: List[Dict[str, float]]) -> float:
        """Calculate correlation from specific history slice."""
        if len(history) < 2:
            return 0.0

        bond_values = [h["bond_metric"] for h in history]
        fx_values = [h["fx_price"] for h in history]

        bond_mean = sum(bond_values) / len(bond_values)
        fx_mean = sum(fx_values) / len(fx_values)

        numerator = sum(
            (bond_values[i] - bond_mean) * (fx_values[i] - fx_mean)
            for i in range(len(bond_values))
        )

        bond_std = (sum((x - bond_mean) ** 2 for x in bond_values)) ** 0.5
        fx_std = (sum((x - fx_mean) ** 2 for x in fx_values)) ** 0.5

        if bond_std == 0 or fx_std == 0:
            return 0.0

        return numerator / (bond_std * fx_std)

    async def _alert_correlation_shift(
        self,
        pair: str,
        previous_corr: float,
        current_corr: float
    ):
        """Alert about significant correlation change."""
        analysis_prompt = f"""Analyze this bond-FX correlation shift:

Pair: {pair}
Previous Correlation: {previous_corr:.3f}
Current Correlation: {current_corr:.3f}
Change: {(current_corr - previous_corr):.3f}

Provide:
1. What caused the correlation change
2. Regime implications (new normal?)
3. Trading opportunities from breakdown
4. Duration of expected change
5. Related pairs affected similarly"""

        correlation_analysis = await self.think(analysis_prompt)

        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],
            message_type="bond_fx_correlation_shift",
            content={
                "pair": pair,
                "previous_correlation": previous_corr,
                "current_correlation": current_corr,
                "analysis": correlation_analysis,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await self.send_message(message)

    async def get_correlation_matrix(self) -> Dict[str, float]:
        """Get current correlation matrix for all pairs."""
        return {pair: self.correlations.get(pair, 0.0) for pair in self.major_pairs + self.crosses}

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "update_correlation":
            await self.update_correlation(
                task.get("pair"),
                task.get("bond_metric"),
                task.get("fx_price"),
                task.get("timestamp", datetime.utcnow().isoformat())
            )
            return {"status": "correlation_updated"}

        elif task_type == "get_matrix":
            return {"correlation_matrix": await self.get_correlation_matrix()}

        elif task_type == "analyze_correlations":
            analysis = await self.analyze({"correlations": self.correlations})
            return analysis

        return {"error": "Unknown task type"}


class LagTimeDetectorAgent(BaseAgent):
    """Detects lead-lag relationships between bonds and FX pairs."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize lag time detector agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_lag_detector_system_prompt()
        super().__init__(config, message_bus)
        self.lag_measurements: Dict[str, deque] = {}
        self.detected_lags: Dict[str, Dict[str, Any]] = {}
        self.lead_indicators: List[Dict[str, Any]] = []

        # Major pairs to track lags for
        self.pairs_to_track = [
            "EUR/USD", "GBP/USD", "JPY/USD", "AUD/USD", "NZD/USD",
            "EUR/GBP", "EUR/AUD", "GBP/AUD"
        ]

        for pair in self.pairs_to_track:
            self.lag_measurements[pair] = deque(maxlen=50)

    def _get_lag_detector_system_prompt(self) -> str:
        """Get system prompt for lag time detector."""
        return """You are a Lead-Lag Time Specialist in a multi-agent trading system.

Your expertise:
1. Identifying which asset class leads (bonds typically lead FX)
2. Measuring lag times between bond moves and FX reactions
3. Detecting when lags expand or contract (regime changes)
4. Using lag timing for entry/exit signals
5. Identifying early signals of market moves

Your responsibilities:
- Monitor timing of bond moves vs FX reactions
- Measure average lag times by pair and condition
- Detect when patterns change (lag expansion = uncertainty)
- Identify which pairs follow bonds most reliably
- Alert when bonds move ahead of FX (early signal)
- Assess lead time persistence

Key insights:
- Bonds typically lead FX by 5-30 minutes in normal conditions
- Lag expands during uncertainty (wider spreads, slower reaction)
- Some pairs follow bonds faster than others (EUR/USD faster than exotics)
- Lag compression = high conviction moves
- Lag expansion = confusion, mean reversion likely"""

    async def record_movement(
        self,
        pair: str,
        bond_time: str,
        bond_move: float,
        fx_time: str,
        fx_move: float
    ):
        """Record a bond-FX movement pairing."""
        # Calculate lag in seconds
        bond_dt = datetime.fromisoformat(bond_time)
        fx_dt = datetime.fromisoformat(fx_time)
        lag_seconds = (fx_dt - bond_dt).total_seconds()

        measurement = {
            "bond_time": bond_time,
            "fx_time": fx_time,
            "bond_move": bond_move,
            "fx_move": fx_move,
            "lag_seconds": lag_seconds,
            "timestamp": datetime.utcnow().isoformat()
        }

        if pair not in self.lag_measurements:
            self.lag_measurements[pair] = deque(maxlen=50)

        self.lag_measurements[pair].append(measurement)

        # Analyze if we have enough data
        if len(self.lag_measurements[pair]) >= 5:
            await self._analyze_lag_pattern(pair)

    async def _analyze_lag_pattern(self, pair: str):
        """Analyze lag pattern for a pair."""
        measurements = list(self.lag_measurements[pair])

        # Calculate statistics
        lags = [m["lag_seconds"] for m in measurements]
        avg_lag = sum(lags) / len(lags)
        min_lag = min(lags)
        max_lag = max(lags)

        # Recent average (last 10)
        recent_lags = lags[-10:]
        recent_avg = sum(recent_lags) / len(recent_lags)

        # Trend
        lag_trend = "increasing" if recent_avg > avg_lag else "decreasing"

        lag_info = {
            "pair": pair,
            "average_lag_seconds": avg_lag,
            "recent_lag_seconds": recent_avg,
            "min_lag": min_lag,
            "max_lag": max_lag,
            "lag_trend": lag_trend,
            "samples": len(measurements)
        }

        self.detected_lags[pair] = lag_info

        # Check for significant changes
        if len(measurements) >= 15:
            early_avg = sum([m["lag_seconds"] for m in measurements[-15:-10]]) / 5
            late_avg = sum([m["lag_seconds"] for m in measurements[-5:]]) / 5

            if abs(late_avg - early_avg) > 10:  # More than 10 seconds change
                await self._alert_lag_change(pair, early_avg, late_avg)

    async def _alert_lag_change(self, pair: str, early_avg: float, late_avg: float):
        """Alert about significant lag time changes."""
        analysis_prompt = f"""Analyze this lag time change in {pair}:

Earlier Average Lag: {early_avg:.1f} seconds
Recent Average Lag: {late_avg:.1f} seconds
Change: {(late_avg - early_avg):.1f} seconds

Direction: {"expanding" if late_avg > early_avg else "contracting"}

Provide:
1. Interpretation of this change
2. Market regime implications
3. Effect on trading timing
4. When to expect next major move
5. Risk factors emerging"""

        lag_analysis = await self.think(analysis_prompt)

        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],
            message_type="lag_time_alert",
            content={
                "pair": pair,
                "earlier_lag": early_avg,
                "recent_lag": late_avg,
                "change_seconds": late_avg - early_avg,
                "analysis": lag_analysis,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await self.send_message(message)

    async def get_lag_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all detected lags."""
        return self.detected_lags

    async def predict_fx_move_timing(self, pair: str) -> Dict[str, Any]:
        """Predict when FX pair will react to bond move."""
        if pair not in self.detected_lags:
            return {"error": f"No lag data for {pair}"}

        lag_info = self.detected_lags[pair]

        prediction_prompt = f"""Predict FX reaction timing for {pair} based on lag analysis:

Average Lag: {lag_info.get('average_lag_seconds', 0):.1f} seconds
Recent Lag: {lag_info.get('recent_lag_seconds', 0):.1f} seconds
Lag Trend: {lag_info.get('lag_trend', 'unknown')}
Sample Size: {lag_info.get('samples', 0)}

Provide:
1. Expected move timing window
2. Confidence level
3. Early warning signals
4. Follow-up move probability
5. Mean reversion tendency"""

        timing_prediction = await self.think(prediction_prompt)

        return {
            "pair": pair,
            "lag_info": lag_info,
            "timing_prediction": timing_prediction,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "record_movement":
            await self.record_movement(
                task.get("pair"),
                task.get("bond_time"),
                task.get("bond_move"),
                task.get("fx_time"),
                task.get("fx_move")
            )
            return {"status": "movement_recorded"}

        elif task_type == "get_lags":
            return {"lags": await self.get_lag_summary()}

        elif task_type == "predict_timing":
            result = await self.predict_fx_move_timing(task.get("pair"))
            return result

        return {"error": "Unknown task type"}


class AssetRotationAlertAgent(BaseAgent):
    """Recommends asset rotation based on bond-FX dynamics."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize asset rotation alert agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_rotation_system_prompt()
        super().__init__(config, message_bus)
        self.rotation_recommendations: List[Dict[str, Any]] = []
        self.current_regime: Optional[str] = None
        self.correlation_regime: Optional[str] = None
        self.asset_attractiveness: Dict[str, float] = {}

    def _get_rotation_system_prompt(self) -> str:
        """Get system prompt for asset rotation."""
        return """You are an Asset Rotation Specialist in a multi-agent trading system.

Your expertise:
1. Identifying when to rotate between correlated assets
2. Understanding relative value across currency pairs
3. Detecting regime changes requiring position shifts
4. Timing entries into correlated asset moves
5. Managing carry and risk exposure during rotations

Your responsibilities:
- Monitor bond-driven regime changes
- Recommend which assets to favor based on correlations
- Alert when rotation opportunities emerge
- Assess relative value of major pairs vs crosses
- Manage risk during transition periods
- Coordinate with market makers on positioning

Key concepts:
- When bonds rise: USD pairs strengthen, carry pairs weaken
- When bonds fall: Risk-on regime favors AUD, NZD, EM
- Carry pairs outperform in low vol, underperform in high vol
- JPY weakness correlates with risk-on, strength with risk-off
- Crosses reveal relative central bank policy divergence"""

    async def analyze_rotation_opportunity(
        self,
        bond_direction: str,
        bond_momentum: float,
        correlation_regime: str,
        current_positions: Dict[str, float]
    ) -> Dict[str, Any]:
        """Analyze asset rotation opportunity."""
        analysis_prompt = f"""Analyze this asset rotation opportunity:

Bond Direction: {bond_direction}
Bond Momentum: {bond_momentum}
Correlation Regime: {correlation_regime}

Current Positions:
{json.dumps(current_positions, indent=2)}

Provide rotation recommendations:
1. Assets to increase exposure in
2. Assets to reduce/exit
3. Timing of rotation
4. Risk levels during transition
5. Hedge recommendations
6. Follow-up trades after rotation"""

        rotation_analysis = await self.think(analysis_prompt)

        recommendation = {
            "timestamp": datetime.utcnow().isoformat(),
            "bond_direction": bond_direction,
            "correlation_regime": correlation_regime,
            "recommendation": rotation_analysis
        }

        self.rotation_recommendations.append(recommendation)

        # Broadcast to traders
        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],
            message_type="asset_rotation_alert",
            content=recommendation
        )
        await self.send_message(message)

        return recommendation

    async def rate_asset_attractiveness(
        self,
        pairs: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """Rate attractiveness of different assets."""
        rating_prompt = f"""Rate the attractiveness of these currency pairs:

Pairs with metrics:
{json.dumps(pairs, indent=2)}

For each pair provide:
1. Attractiveness score (0-100)
2. Key drivers of the rating
3. Key risks
4. Carry consideration
5. Volatility consideration

Format as scores for each pair."""

        ratings = await self.think(rating_prompt)

        # Parse scores from response
        self.asset_attractiveness = {
            pair: 50.0 for pair in pairs.keys()
        }

        return {
            "ratings": self.asset_attractiveness,
            "detailed_analysis": ratings,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def detect_state_change(
        self,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect changes in market state requiring positioning changes."""
        state_analysis_prompt = f"""Analyze if market state has changed:

Current Market Data:
{json.dumps(market_data, indent=2)}

Previous State: {self.current_regime}

Provide:
1. Is state changing? (YES/NO)
2. New state definition (risk-on/risk-off/transition/rangebound)
3. Confidence level
4. Key signals indicating change
5. Positioning adjustments needed
6. Duration of new state expected
7. Triggers for reversal"""

        state_analysis = await self.think(state_analysis_prompt)

        return {
            "state_analysis": state_analysis,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def recommend_correlated_trades(
        self,
        initiating_pair: str,
        initiating_move: float,
        correlation_matrix: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Recommend trades in correlated assets when one moves."""
        trades_prompt = f"""Recommend correlated asset trades:

Initiating Pair: {initiating_pair}
Move Size: {initiating_move}

Correlation Matrix:
{json.dumps(correlation_matrix, indent=2)}

Provide trading recommendations for each highly correlated pair:
1. Trade direction
2. Expected move size (as % of initiating move)
3. Timing (immediate, wait for lag time, etc.)
4. Position size relative to initiator
5. Exit conditions
6. Risk management levels"""

        trade_recommendations = await self.think(trades_prompt)

        return [
            {
                "initiating_pair": initiating_pair,
                "recommendations": trade_recommendations,
                "timestamp": datetime.utcnow().isoformat()
            }
        ]

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "analyze_rotation":
            result = await self.analyze_rotation_opportunity(
                task.get("bond_direction"),
                task.get("bond_momentum", 0.0),
                task.get("correlation_regime", "normal"),
                task.get("current_positions", {})
            )
            return result

        elif task_type == "rate_assets":
            result = await self.rate_asset_attractiveness(task.get("pairs", {}))
            return result

        elif task_type == "detect_state_change":
            result = await self.detect_state_change(task.get("market_data", {}))
            return result

        elif task_type == "recommend_trades":
            result = await self.recommend_correlated_trades(
                task.get("initiating_pair"),
                task.get("initiating_move", 0.0),
                task.get("correlation_matrix", {})
            )
            return result

        return {"error": "Unknown task type"}
