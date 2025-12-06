"""Research Agents - Data Scientists, Psychologists, Strategy Testers."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.framework.base_agent import BaseAgent, AgentConfig, AgentRole, Message


class DataScienceAgent(BaseAgent):
    """Data science agent for analysis, modeling, and pattern recognition."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize data science agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_data_science_system_prompt()
        super().__init__(config, message_bus)
        self.models: Dict[str, Dict[str, Any]] = {}
        self.pattern_library: Dict[str, Dict[str, Any]] = {}
        self.correlation_studies: List[Dict[str, Any]] = []

    def _get_data_science_system_prompt(self) -> str:
        """Get system prompt for data scientist."""
        return """You are a Data Science specialist in a multi-agent trading system.

Your expertise:
1. Statistical modeling and hypothesis testing
2. Machine learning for pattern recognition
3. Time series analysis and forecasting
4. Correlation and causality analysis
5. Outlier detection and anomaly analysis
6. Data quality assessment

Your responsibilities:
- Analyze market microstructure (order flow, spreads)
- Identify repeating patterns in price action
- Build models for volatility prediction
- Analyze factor relationships (interest rates, USD, equities)
- Detect regime changes and structural breaks
- Provide data-driven insights for strategy development

Key analyses:
- Correlation matrices and principal components
- Volatility clustering and persistence
- Order flow and its predictive power
- Technical indicator effectiveness
- Mean reversion vs momentum evidence"""

    async def analyze_patterns(
        self,
        data: Dict[str, Any],
        pattern_type: str = "price_action"
    ) -> Dict[str, Any]:
        """Analyze data for patterns."""
        analysis_prompt = f"""Analyze this data for {pattern_type} patterns:

Data Summary:
{json.dumps(data, indent=2)}

Provide:
1. Identified patterns
2. Statistical significance
3. Historical frequency
4. Win rate if tradeable
5. Associated risks
6. Recommendations for exploitation"""

        pattern_analysis = await self.think(analysis_prompt)

        self.pattern_library[f"{pattern_type}_{datetime.utcnow().timestamp()}"] = {
            "pattern_type": pattern_type,
            "analysis": pattern_analysis,
            "data_sample": data
        }

        return {
            "pattern_type": pattern_type,
            "analysis": pattern_analysis,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def build_correlation_model(
        self,
        variables: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """Build correlation model from variables."""
        correlation_prompt = f"""Analyze correlations between these variables:

Variables:
{json.dumps({k: f"[{len(v)} data points]" for k, v in variables.items()}, indent=2)}

Provide:
1. Correlation matrix summary
2. Principal components (if applicable)
3. Stable vs unstable correlations
4. Causal relationships hypotheses
5. Trading implications
6. Risk diversification insights"""

        correlation_analysis = await self.think(correlation_prompt)

        study = {
            "timestamp": datetime.utcnow().isoformat(),
            "variables": list(variables.keys()),
            "analysis": correlation_analysis
        }
        self.correlation_studies.append(study)

        return {
            "study": study,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def forecast_metric(
        self,
        metric_name: str,
        historical_data: List[float],
        horizon: int = 5
    ) -> Dict[str, Any]:
        """Forecast a metric."""
        forecast_prompt = f"""Forecast {metric_name} for {horizon} periods ahead:

Historical Data (last 50 periods):
{json.dumps(historical_data[-50:], indent=2)}

Provide:
1. Forecast values
2. Confidence intervals
3. Trend assessment
4. Volatility forecast
5. Key drivers
6. Risk factors"""

        forecast = await self.think(forecast_prompt)

        return {
            "metric": metric_name,
            "horizon": horizon,
            "forecast": forecast,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "analyze_patterns":
            result = await self.analyze_patterns(
                task.get("data"),
                task.get("pattern_type", "price_action")
            )
            return result

        elif task_type == "correlation":
            result = await self.build_correlation_model(task.get("variables", {}))
            return result

        elif task_type == "forecast":
            result = await self.forecast_metric(
                task.get("metric_name"),
                task.get("historical_data", []),
                task.get("horizon", 5)
            )
            return result

        return {"error": "Unknown task type"}


class TradesPsychologyAgent(BaseAgent):
    """Analyzes trading psychology and behavioral patterns."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize psychology agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_psychology_system_prompt()
        super().__init__(config, message_bus)
        self.behavioral_patterns: Dict[str, Dict[str, Any]] = {}
        self.bias_log: List[Dict[str, Any]] = []
        self.psychological_metrics: Dict[str, float] = {}

    def _get_psychology_system_prompt(self) -> str:
        """Get system prompt for psychology specialist."""
        return """You are a Trade Psychology Specialist in a multi-agent trading system.

Your expertise:
1. Behavioral biases in trading (anchoring, recency, overconfidence)
2. Emotion-driven decision analysis
3. Loss aversion and risk perception
4. Group psychology and herd behavior
5. Confidence cycles and market extremes
6. Decision-making under uncertainty

Your responsibilities:
- Monitor for psychological biases in trading decisions
- Assess market sentiment and extremes
- Identify overconfidence or panic signals
- Recommend discipline improvements
- Analyze decision quality independent of outcomes
- Provide context on behavioral market extremes

Key biases to track:
- Anchoring (past prices affecting decisions)
- Recency bias (overweighting recent events)
- Confirmation bias (seeking supporting evidence)
- Loss aversion (fear of losses > desire for gains)
- Overconfidence (excessive conviction)
- Hindsight bias (seeing outcomes as obvious)"""

    async def analyze_trader_psychology(
        self,
        trade_history: List[Dict[str, Any]],
        recent_performance: Dict[str, float]
    ) -> Dict[str, Any]:
        """Analyze psychological patterns in trading."""
        analysis_prompt = f"""Analyze trader psychology from trade history:

Number of Trades: {len(trade_history)}
Recent Performance:
{json.dumps(recent_performance, indent=2)}

Provide assessment of:
1. Risk taking behavior (changing with performance)
2. Entry/exit discipline (following system vs emotional)
3. Loss aversion signs (cutting winners, holding losers)
4. Overconfidence signals (size increases after wins)
5. Behavioral improvements needed
6. Psychological risk factors"""

        psychology_analysis = await self.think(analysis_prompt)

        self.behavioral_patterns[f"analysis_{datetime.utcnow().timestamp()}"] = {
            "trades_analyzed": len(trade_history),
            "analysis": psychology_analysis
        }

        return {
            "analysis": psychology_analysis,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def assess_market_psychology(
        self,
        market_metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """Assess market psychology and sentiment."""
        psychology_prompt = f"""Assess market psychology based on these metrics:

{json.dumps(market_metrics, indent=2)}

Provide:
1. Overall sentiment (bullish/bearish/extreme)
2. Risk appetite level
3. Fear gauge assessment
4. Greed signals
5. Potential reversal scenarios
6. Contrarian opportunities"""

        sentiment_analysis = await self.think(psychology_prompt)

        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],
            message_type="market_psychology_alert",
            content={
                "sentiment_analysis": sentiment_analysis,
                "metrics": market_metrics,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await self.send_message(message)

        return {
            "sentiment_analysis": sentiment_analysis,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "trader_psychology":
            result = await self.analyze_trader_psychology(
                task.get("trade_history", []),
                task.get("recent_performance", {})
            )
            return result

        elif task_type == "market_psychology":
            result = await self.assess_market_psychology(
                task.get("market_metrics", {})
            )
            return result

        elif task_type == "bias_check":
            analysis = await self.analyze({"task": "identify biases"})
            return analysis

        return {"error": "Unknown task type"}


class StrategyTesterAgent(BaseAgent):
    """Tests and validates trading strategies."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize strategy tester agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_strategy_test_system_prompt()
        super().__init__(config, message_bus)
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.validated_strategies: List[str] = []
        self.rejected_strategies: List[str] = []

    def _get_strategy_test_system_prompt(self) -> str:
        """Get system prompt for strategy tester."""
        return """You are a Strategy Testing Agent in a multi-agent trading system.

Your responsibilities:
1. Validate new trading strategies before deployment
2. Run backtests and walk-forward analysis
3. Assess strategy robustness across market regimes
4. Evaluate risk-adjusted returns
5. Test strategy combinations
6. Identify weaknesses and edge cases

Testing criteria:
- Minimum sample size (100+ trades)
- Positive expectancy (win rate × avg win > loss rate × avg loss)
- Acceptable drawdown (max drawdown < 20% of account)
- Profit factor > 1.5 (gross profit / gross loss)
- Sharpe ratio > 0.5 (risk-adjusted returns)
- Robustness across time periods

You also:
- Test strategy assumptions
- Identify curve-fitting
- Assess slippage impact
- Evaluate psychological feasibility
- Recommend parameter ranges"""

    async def test_strategy(
        self,
        strategy_name: str,
        rules: Dict[str, Any],
        backtest_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Test a strategy."""
        test_prompt = f"""Validate this strategy for trading:

Strategy: {strategy_name}
Rules: {json.dumps(rules, indent=2)}

Backtest Data: {len(backtest_data)} periods

Provide detailed evaluation:
1. Validity metrics (win rate, profit factor, etc.)
2. Risk assessment
3. Robustness analysis
4. Recommendation (ACCEPT/REJECT/MODIFY)
5. Implementation notes
6. Risk factors"""

        test_results = await self.think(test_prompt)

        self.test_results[strategy_name] = {
            "timestamp": datetime.utcnow().isoformat(),
            "rules": rules,
            "test_results": test_results,
            "data_points": len(backtest_data)
        }

        # Classify
        if "ACCEPT" in test_results.upper():
            self.validated_strategies.append(strategy_name)
            status = "VALIDATED"
        elif "REJECT" in test_results.upper():
            self.rejected_strategies.append(strategy_name)
            status = "REJECTED"
        else:
            status = "NEEDS_MODIFICATION"

        return {
            "strategy": strategy_name,
            "status": status,
            "test_results": test_results,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "test_strategy":
            result = await self.test_strategy(
                task.get("strategy_name"),
                task.get("rules", {}),
                task.get("backtest_data", [])
            )
            return result

        elif task_type == "validation_report":
            analysis = await self.analyze({
                "validated": len(self.validated_strategies),
                "rejected": len(self.rejected_strategies)
            })
            return analysis

        return {"error": "Unknown task type"}
