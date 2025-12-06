"""Trading Agents - Market Makers, Quant Traders, Risk Managers."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.framework.base_agent import BaseAgent, AgentConfig, AgentRole, Message


class MarketMakerAgent(BaseAgent):
    """Market maker agent providing liquidity and managing bid-ask spreads."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize market maker agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_market_maker_system_prompt()
        super().__init__(config, message_bus)
        self.order_book: Dict[str, Dict[str, List[tuple]]] = {}
        self.spread_inventory: Dict[str, Dict[str, float]] = {}
        self.bid_ask_data: List[Dict[str, Any]] = []

    def _get_market_maker_system_prompt(self) -> str:
        """Get system prompt for market maker."""
        return """You are a Market Maker agent in a multi-agent trading system.

Your responsibilities:
1. Provide continuous two-way quotes (bid and ask)
2. Manage inventory to keep neutral position
3. Adjust spreads based on volatility and volume
4. Monitor order imbalances
5. Optimize pricing for profitability
6. Manage risk from inventory accumulation

Key metrics:
- Bid-ask spread (tighten/widen based on volatility)
- Order flow imbalance (inventory skew)
- Turnover rate and velocity
- Realized vs mark spreads
- Execution quality

You respond to:
- Market profile updates (adjust spreads for direction)
- Economic alerts (widen spreads for events)
- Volume alerts (adjust size for participation)
- Risk manager alerts (reduce inventory risk)"""

    async def update_quote(
        self,
        symbol: str,
        bid: float,
        ask: float,
        bid_size: Optional[float] = None,
        ask_size: Optional[float] = None
    ):
        """Update market maker quotes."""
        if symbol not in self.bid_ask_data:
            self.bid_ask_data.append({})

        self.bid_ask_data.append({
            "symbol": symbol,
            "bid": bid,
            "ask": ask,
            "mid": (bid + ask) / 2,
            "spread": ask - bid,
            "spread_pct": ((ask - bid) / ((bid + ask) / 2)) * 100,
            "bid_size": bid_size,
            "ask_size": ask_size,
            "timestamp": datetime.utcnow().isoformat()
        })

        self.state["last_update"] = datetime.utcnow().isoformat()

    async def adjust_spreads(
        self,
        symbol: str,
        volatility: float,
        volume: float
    ):
        """Adjust spreads based on market conditions."""
        adjust_prompt = f"""Adjust bid-ask spreads for {symbol}:

Volatility: {volatility}
Volume: {volume}

Provide:
1. Recommended spread (in basis points)
2. Bid/Ask sizing
3. Inventory risk level
4. Actions needed"""

        adjustment_logic = await self.think(adjust_prompt)

        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],
            message_type="spread_adjustment",
            content={
                "symbol": symbol,
                "volatility": volatility,
                "volume": volume,
                "adjustment_logic": adjustment_logic,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await self.send_message(message)

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "quote_update":
            await self.update_quote(
                task.get("symbol"),
                task.get("bid"),
                task.get("ask"),
                task.get("bid_size"),
                task.get("ask_size")
            )
            return {"status": "quote_updated"}

        elif task_type == "spread_analysis":
            symbol = task.get("symbol")
            analysis = await self.analyze({"symbol": symbol})
            return analysis

        return {"error": "Unknown task type"}


class QuantTraderAgent(BaseAgent):
    """Quantitative trader using algorithms and models."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize quant trader agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_quant_system_prompt()
        super().__init__(config, message_bus)
        self.models: Dict[str, Dict[str, Any]] = {}
        self.signals: List[Dict[str, Any]] = []
        self.backtest_results: Dict[str, Dict[str, float]] = {}
        self.active_strategies: Dict[str, Dict[str, Any]] = {}

    def _get_quant_system_prompt(self) -> str:
        """Get system prompt for quant trader."""
        return """You are a Quantitative Trader in a multi-agent trading system.

Your expertise:
1. Develop and test trading algorithms
2. Analyze statistical patterns in price action
3. Create signal models for entries/exits
4. Manage mean reversion and momentum strategies
5. Optimize position sizing and risk
6. Backtest strategies rigorously

Your strategies respond to:
- Market profile updates (adjust strategy bias)
- Economic alerts (pause/hedge around events)
- Data science insights (incorporate new patterns)
- Performance analysis (refine models based on results)
- Risk alerts (reduce exposure when risk spikes)

Key outputs:
- Trading signals (entry/exit recommendations)
- Probability estimates (win rate, expectancy)
- Position sizing guidance
- Risk metrics and drawdown projections"""

    async def generate_signal(
        self,
        symbol: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate trading signal from data."""
        signal_prompt = f"""Generate trading signal for {symbol}:

Market Data:
{json.dumps(data, indent=2)}

Provide:
1. Signal (BUY/SELL/NEUTRAL)
2. Confidence level (0-100%)
3. Entry zone
4. Stop loss level
5. Target zone
6. Risk/reward ratio"""

        signal_analysis = await self.think(signal_prompt)

        signal = {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "analysis": signal_analysis,
            "data_used": data
        }
        self.signals.append(signal)

        return signal

    async def backtest_strategy(
        self,
        strategy_name: str,
        rules: Dict[str, Any],
        historical_data: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Backtest a strategy."""
        backtest_prompt = f"""Backtest this strategy:

Strategy: {strategy_name}
Rules: {json.dumps(rules, indent=2)}

Analyze {len(historical_data)} data points and provide:
1. Total return
2. Win rate
3. Profit factor
4. Maximum drawdown
5. Sharpe ratio estimate
6. Sample trades analysis"""

        backtest_results = await self.think(backtest_prompt)

        # Store results
        self.backtest_results[strategy_name] = {
            "timestamp": datetime.utcnow().isoformat(),
            "analysis": backtest_results
        }

        return {
            "strategy": strategy_name,
            "backtest_analysis": backtest_results
        }

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "generate_signal":
            result = await self.generate_signal(
                task.get("symbol"),
                task.get("data")
            )
            return result

        elif task_type == "backtest":
            result = await self.backtest_strategy(
                task.get("strategy_name"),
                task.get("rules"),
                task.get("historical_data", [])
            )
            return result

        elif task_type == "model_analysis":
            symbol = task.get("symbol")
            analysis = await self.analyze({"symbol": symbol})
            return analysis

        return {"error": "Unknown task type"}


class RiskManagerAgent(BaseAgent):
    """Risk manager monitoring portfolio risk and compliance."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize risk manager agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_risk_system_prompt()
        super().__init__(config, message_bus)
        self.portfolio_positions: Dict[str, float] = {}
        self.risk_limits: Dict[str, float] = {}
        self.var_metrics: Dict[str, float] = {}
        self.breach_alerts: List[Dict[str, Any]] = []

    def _get_risk_system_prompt(self) -> str:
        """Get system prompt for risk manager."""
        return """You are a Risk Manager in a multi-agent trading system.

Your responsibilities:
1. Monitor portfolio-level risk metrics
2. Enforce position limits and exposure caps
3. Calculate Value at Risk (VaR) and stress scenarios
4. Identify concentration risks
5. Manage correlation risks
6. Alert traders to limit breaches

Risk metrics tracked:
- Value at Risk (VaR) at 95% and 99% confidence
- Expected shortfall (CVaR)
- Concentration by instrument/sector/geography
- Delta/gamma/vega exposure (for derivatives)
- Liquidity risk and margin requirements
- Correlation shifts and diversification benefits

You alert traders when:
- Single position exceeds limit
- Portfolio VaR exceeds threshold
- Concentration risk becomes problematic
- Margin utilization is high
- Correlation structure breaks
- Liquidity risk increases"""

    async def update_position(
        self,
        symbol: str,
        position_size: float,
        price: float,
        risk_metadata: Optional[Dict[str, Any]] = None
    ):
        """Update position for risk tracking."""
        self.portfolio_positions[symbol] = {
            "size": position_size,
            "price": price,
            "notional": position_size * price,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": risk_metadata or {}
        }

        await self._calculate_position_risk(symbol, position_size, price)

    async def _calculate_position_risk(
        self,
        symbol: str,
        position_size: float,
        price: float
    ):
        """Calculate risk for a position."""
        risk_prompt = f"""Assess risk for position:

Symbol: {symbol}
Size: {position_size}
Price: {price}
Notional: {position_size * price}

Provide:
1. Stop loss level (hard stop)
2. Position limit (relative to portfolio)
3. Concentration risk
4. Estimated value at risk (1% move)
5. Stress scenario (10% market move)"""

        risk_analysis = await self.think(risk_prompt)

        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],
            message_type="position_risk_analysis",
            content={
                "symbol": symbol,
                "size": position_size,
                "price": price,
                "risk_analysis": risk_analysis,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await self.send_message(message)

    async def calculate_portfolio_var(
        self,
        confidence_level: float = 0.95
    ) -> Dict[str, float]:
        """Calculate portfolio VaR."""
        total_notional = sum(
            p["notional"] for p in self.portfolio_positions.values()
        )

        var_prompt = f"""Calculate portfolio VaR:

Total Notional: {total_notional}
Confidence Level: {confidence_level}
Number of positions: {len(self.portfolio_positions)}

Provide:
1. VaR amount
2. VaR percentage of portfolio
3. Expected shortfall (CVaR)
4. Concentration contribution to VaR
5. Recommendations"""

        var_analysis = await self.think(var_prompt)

        return {
            "total_notional": total_notional,
            "confidence_level": confidence_level,
            "var_analysis": var_analysis
        }

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "update_position":
            await self.update_position(
                task.get("symbol"),
                task.get("position_size"),
                task.get("price"),
                task.get("metadata")
            )
            return {"status": "position_updated"}

        elif task_type == "calculate_var":
            result = await self.calculate_portfolio_var(
                task.get("confidence_level", 0.95)
            )
            return result

        elif task_type == "risk_report":
            analysis = await self.analyze({"positions": self.portfolio_positions})
            return analysis

        return {"error": "Unknown task type"}
