"""Market Specialist Agents - Bond Analysts, Forex Specialists, Metalmarket Traders."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.framework.base_agent import BaseAgent, AgentConfig, AgentRole, Message


class BondAnalystAgent(BaseAgent):
    """Analyzes bond markets and fixed income opportunities."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize bond analyst agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_bond_system_prompt()
        super().__init__(config, message_bus)
        self.yield_curve_data: Dict[str, List[float]] = {}
        self.bond_holdings: List[Dict[str, Any]] = []
        self.duration_exposure: Dict[str, float] = {}

    def _get_bond_system_prompt(self) -> str:
        """Get system prompt for bond analysis."""
        return """You are a Bond Market Specialist in a multi-agent trading system.

Your expertise covers:
1. Yield curve analysis (shape, shifts, inversions)
2. Credit spreads (investment grade, high yield)
3. Duration and convexity strategies
4. Central bank policy impact on bonds
5. Interest rate forecasting
6. Bond risk management

Your responsibilities:
- Monitor economic data for rate implications
- Alert traders to curve shifts and opportunities
- Manage duration risk in the portfolio
- Identify credit value and risks
- Provide duration-weighted allocation recommendations

Key metrics you track:
- 2/10 spread (recession indicator)
- Credit spreads by sector
- Term premium levels
- Real yields vs nominal yields"""

    async def update_yield_curve(
        self,
        maturity_points: Dict[str, float]
    ):
        """Update yield curve data."""
        timestamp = datetime.utcnow().isoformat()
        self.yield_curve_data[timestamp] = maturity_points

        # Analyze curve
        await self._analyze_yield_curve(maturity_points)

    async def _analyze_yield_curve(self, yields: Dict[str, float]):
        """Analyze yield curve structure."""
        if len(yields) < 2:
            return

        analysis_prompt = f"""Analyze this yield curve:

{json.dumps(yields, indent=2)}

Provide:
1. Curve shape assessment (steep, flat, inverted)
2. Key risks and opportunities
3. Duration positioning recommendations
4. Expected rate move implications
5. Alerts for other agents"""

        curve_analysis = await self.think(analysis_prompt)

        # Alert other agents
        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],
            message_type="bond_analysis_update",
            content={
                "yield_curve": yields,
                "analysis": curve_analysis,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await self.send_message(message)

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "analyze_rates":
            rates = task.get("rates")
            analysis = await self.analyze({"rates": rates})
            return analysis

        elif task_type == "assess_duration":
            duration = task.get("duration")
            prompt = f"""Assess portfolio duration strategy given current environment:
Duration: {duration}
Provide sizing and hedging recommendations."""
            assessment = await self.think(prompt)
            return {"duration_assessment": assessment}

        elif task_type == "credit_analysis":
            spreads = task.get("spreads")
            analysis = await self.analyze({"credit_spreads": spreads})
            return analysis

        return {"error": "Unknown task type"}


class ForexSpecialistAgent(BaseAgent):
    """Analyzes forex markets and currency pairs."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize forex specialist agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_forex_system_prompt()
        super().__init__(config, message_bus)
        self.currency_pairs: Dict[str, Dict[str, Any]] = {}
        self.central_bank_policies: Dict[str, Dict[str, Any]] = {}
        self.carry_trade_analysis: Dict[str, float] = {}
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}

    def _get_forex_system_prompt(self) -> str:
        """Get system prompt for forex analysis."""
        return """You are a Forex Specialist in a multi-agent trading system.

Your expertise covers:
1. Currency pair analysis (majors, minors, exotics)
2. Central bank policy and interest rate differentials
3. Carry trade opportunities and risks
4. Technical levels and support/resistance
5. Currency correlation patterns
6. Geopolitical risk impact on currencies

Your responsibilities:
- Monitor central bank decisions and guidance
- Track interest rate differentials
- Identify carry trade opportunities
- Manage currency risk exposure
- Alert traders to key technical levels
- Analyze cross-currency basis and arbitrage

Key metrics:
- Interest rate carry differentials
- Relative economic strength
- Technical levels (support, resistance, pivots)
- Currency correlation shifts
- Implied volatility by pair"""

    async def update_currency_pair(
        self,
        pair: str,
        price: float,
        bid_ask_spread: Optional[float] = None,
        volume: Optional[int] = None
    ):
        """Update currency pair data."""
        self.currency_pairs[pair] = {
            "price": price,
            "timestamp": datetime.utcnow().isoformat(),
            "bid_ask_spread": bid_ask_spread,
            "volume": volume
        }

        # Check for alerts
        await self._check_technical_alerts(pair, price)

    async def _check_technical_alerts(self, pair: str, price: float):
        """Check for technical level alerts."""
        # This would integrate with market profile data
        alert_prompt = f"""Check for technical alerts on {pair} at price {price}:

Provide any alerts for key levels being tested."""
        alerts = await self.think(alert_prompt)

        if alerts and len(alerts) > 10:  # If there's meaningful content
            message = Message(
                sender_id=self.config.agent_id,
                sender_role=self.config.role,
                recipient_ids=[],
                message_type="forex_technical_alert",
                content={
                    "pair": pair,
                    "price": price,
                    "alerts": alerts,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            await self.send_message(message)

    async def analyze_carry_trade(
        self,
        base_currency: str,
        quote_currency: str,
        base_rate: float,
        quote_rate: float
    ) -> Dict[str, Any]:
        """Analyze carry trade opportunity."""
        carry_differential = base_rate - quote_rate
        self.carry_trade_analysis[f"{base_currency}/{quote_currency}"] = carry_differential

        analysis_prompt = f"""Analyze carry trade opportunity:

Currency Pair: {base_currency}/{quote_currency}
Base Currency Rate: {base_rate}%
Quote Currency Rate: {quote_rate}%
Carry Differential: {carry_differential}%

Provide:
1. Carry trade attractiveness (high/medium/low)
2. Risk factors
3. Hedge recommendations
4. Entry/exit zones"""

        analysis = await self.think(analysis_prompt)
        return {
            "pair": f"{base_currency}/{quote_currency}",
            "carry_differential": carry_differential,
            "analysis": analysis
        }

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "analyze_pair":
            pair = task.get("pair")
            technical_data = task.get("technical_data")
            analysis = await self.analyze(technical_data)
            return {"pair": pair, "analysis": analysis}

        elif task_type == "assess_carry":
            result = await self.analyze_carry_trade(
                task.get("base_currency"),
                task.get("quote_currency"),
                task.get("base_rate"),
                task.get("quote_rate")
            )
            return result

        elif task_type == "correlation_analysis":
            pairs = task.get("pairs")
            analysis = await self.analyze({"correlation_pairs": pairs})
            return analysis

        return {"error": "Unknown task type"}


class MetalMarketTraderAgent(BaseAgent):
    """Specializes in precious metals and commodity trading."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize metalmarket trader agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_metal_system_prompt()
        super().__init__(config, message_bus)
        self.metal_positions: Dict[str, float] = {}
        self.storage_costs: Dict[str, float] = {}
        self.futures_curve: Dict[str, List[float]] = {}
        self.mining_news: List[Dict[str, Any]] = []

    def _get_metal_system_prompt(self) -> str:
        """Get system prompt for metalmarket trading."""
        return """You are a Metal Market Specialist in a multi-agent trading system.

Your expertise covers:
1. Precious metals (gold, silver, platinum, palladium)
2. Industrial metals (copper, aluminum, zinc, nickel)
3. Futures curve analysis and contango/backwardation
4. Physical metal supply/demand dynamics
5. Mining activity and production cycles
6. Geopolitical factors affecting metals

Your responsibilities:
- Monitor supply/demand fundamentals
- Analyze futures curves for arbitrage opportunities
- Manage storage and financing costs
- Track mining production and exploration
- Identify technical opportunities
- Assess macro factors (inflation, currency, interest rates)

Key metrics:
- Spot prices and futures curves
- Open interest and volume
- Storage costs and convenience yields
- Production data and stockpiles
- USD strength impact
- Real yields correlation"""

    async def update_metal_position(
        self,
        metal: str,
        price: float,
        position_size: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update metal position."""
        self.metal_positions[metal] = {
            "price": price,
            "position_size": position_size,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        await self._analyze_position(metal, price, position_size)

    async def _analyze_position(
        self,
        metal: str,
        price: float,
        position_size: float
    ):
        """Analyze metal position."""
        analysis_prompt = f"""Analyze this metal position:

Metal: {metal}
Current Price: {price}
Position Size: {position_size}

Provide:
1. Risk assessment
2. Profit target zones
3. Stop loss levels
4. Hedge recommendations
5. Any macro concerns"""

        analysis = await self.think(analysis_prompt)

        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],
            message_type="metal_position_analysis",
            content={
                "metal": metal,
                "price": price,
                "position_size": position_size,
                "analysis": analysis,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await self.send_message(message)

    async def analyze_futures_curve(
        self,
        metal: str,
        contract_prices: Dict[str, float]
    ) -> Dict[str, Any]:
        """Analyze futures curve structure."""
        self.futures_curve[metal] = list(contract_prices.values())

        curve_analysis_prompt = f"""Analyze this {metal} futures curve:

Contract Prices:
{json.dumps(contract_prices, indent=2)}

Provide:
1. Curve structure (contango/backwardation degree)
2. Arbitrage opportunities
3. Financing costs implied
4. Market sentiment indication
5. Trading recommendations"""

        analysis = await self.think(curve_analysis_prompt)
        return {
            "metal": metal,
            "curve_structure": "contango" if list(contract_prices.values())[0] < list(contract_prices.values())[-1] else "backwardation",
            "analysis": analysis
        }

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "update_position":
            await self.update_metal_position(
                task.get("metal"),
                task.get("price"),
                task.get("position_size"),
                task.get("metadata")
            )
            return {"status": "position_updated"}

        elif task_type == "analyze_curve":
            result = await self.analyze_futures_curve(
                task.get("metal"),
                task.get("contract_prices")
            )
            return result

        elif task_type == "supply_demand":
            data = task.get("supply_demand_data")
            analysis = await self.analyze(data)
            return analysis

        return {"error": "Unknown task type"}
