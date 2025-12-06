"""Self-Improvement Agents - Performance Analysis, Hypothesis Generation, Knowledge Refinement."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.framework.base_agent import BaseAgent, AgentConfig, AgentRole, Message


class PerformanceAnalystAgent(BaseAgent):
    """Analyzes trading performance and identifies improvement opportunities."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize performance analyst agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_performance_system_prompt()
        super().__init__(config, message_bus)
        self.performance_records: List[Dict[str, Any]] = []
        self.performance_trends: Dict[str, List[float]] = {}
        self.improvement_opportunities: List[Dict[str, Any]] = []

    def _get_performance_system_prompt(self) -> str:
        """Get system prompt for performance analyst."""
        return """You are a Performance Analysis Agent in a multi-agent trading system.

Your responsibilities:
1. Track trading performance metrics (PnL, returns, Sharpe ratio)
2. Analyze performance by strategy, instrument, time period
3. Identify what's working and what's failing
4. Benchmark performance against objectives
5. Detect performance degradation
6. Recommend improvements

Key metrics:
- Total return and CAGR (compound annual growth rate)
- Sharpe ratio (risk-adjusted returns)
- Sortino ratio (downside risk only)
- Maximum drawdown and recovery time
- Win rate and profit factor
- Average win vs average loss
- Consecutive wins/losses (streak analysis)

You provide:
- Monthly/quarterly performance reviews
- Attribution analysis (what drove returns)
- Risk-adjusted performance evaluation
- Peer benchmarking
- Early warning signs of trouble
- Specific improvement recommendations"""

    async def analyze_performance(
        self,
        period: str,
        trades: List[Dict[str, Any]],
        returns: Dict[str, float]
    ) -> Dict[str, Any]:
        """Analyze trading performance for a period."""
        analysis_prompt = f"""Analyze trading performance:

Period: {period}
Number of Trades: {len(trades)}
Returns:
{json.dumps(returns, indent=2)}

Provide analysis with:
1. Performance rating (excellent/good/acceptable/poor)
2. Key metrics (Sharpe, win rate, profit factor)
3. What went well
4. What needs improvement
5. Specific action items
6. Risk factors to address"""

        performance_analysis = await self.think(analysis_prompt)

        record = {
            "period": period,
            "timestamp": datetime.utcnow().isoformat(),
            "trades": len(trades),
            "returns": returns,
            "analysis": performance_analysis
        }
        self.performance_records.append(record)

        # Broadcast performance update
        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],
            message_type="performance_analysis",
            content={
                "period": period,
                "analysis": performance_analysis,
                "returns": returns
            }
        )
        await self.send_message(message)

        return record

    async def identify_improvement_opportunities(
        self,
        performance_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify specific areas for improvement."""
        improvement_prompt = f"""Identify improvement opportunities from this performance data:

{json.dumps(performance_data, indent=2)}

Provide top 5 improvement opportunities with:
1. Opportunity name
2. Current state vs target
3. Expected impact (return improvement)
4. Implementation difficulty (easy/medium/hard)
5. Dependencies (what else needs to change)
6. Success metrics"""

        opportunities = await self.think(improvement_prompt)

        self.improvement_opportunities.append({
            "timestamp": datetime.utcnow().isoformat(),
            "opportunities": opportunities
        })

        return [{
            "opportunities": opportunities,
            "timestamp": datetime.utcnow().isoformat()
        }]

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "analyze_performance":
            result = await self.analyze_performance(
                task.get("period", "unknown"),
                task.get("trades", []),
                task.get("returns", {})
            )
            return result

        elif task_type == "identify_improvements":
            result = await self.identify_improvement_opportunities(
                task.get("performance_data", {})
            )
            return result

        elif task_type == "performance_report":
            analysis = await self.analyze({
                "records": len(self.performance_records),
                "opportunities": len(self.improvement_opportunities)
            })
            return analysis

        return {"error": "Unknown task type"}


class HypothesisGeneratorAgent(BaseAgent):
    """Generates new trading hypotheses and ideas for testing."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize hypothesis generator agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_hypothesis_system_prompt()
        super().__init__(config, message_bus)
        self.hypothesis_library: List[Dict[str, Any]] = []
        self.tested_hypotheses: Dict[str, str] = {}  # name -> result
        self.rejected_ideas: List[str] = []

    def _get_hypothesis_system_prompt(self) -> str:
        """Get system prompt for hypothesis generator."""
        return """You are a Hypothesis Generator Agent in a multi-agent trading system.

Your responsibilities:
1. Generate novel trading ideas and hypotheses
2. Base ideas on market observations and patterns
3. Combine insights from multiple data sources
4. Refine hypotheses based on test results
5. Suggest experiments to validate ideas
6. Learn from failures and adapt

Hypothesis generation approaches:
- Pattern continuation (momentum, mean reversion)
- Factor relationships (correlation changes, causality)
- Seasonal effects (time-of-day, day-of-week, calendar)
- Market microstructure (order flow, spreads, inventory)
- Behavioral factors (sentiment, positioning, flows)
- Economic data combinations (leading indicators)

For each hypothesis provide:
- Specific, testable trading rule
- Economic/statistical rationale
- Expected edge (win rate, profit factor)
- Risk factors
- Testing requirements"""

    async def generate_hypotheses(
        self,
        market_context: Dict[str, Any],
        recent_observations: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate new trading hypotheses."""
        hypothesis_prompt = f"""Generate 5 novel trading hypotheses based on:

Market Context:
{json.dumps(market_context, indent=2)}

Recent Observations:
{json.dumps(recent_observations, indent=2)}

For each hypothesis provide:
1. Hypothesis name
2. Trading rule (specific entry/exit)
3. Rationale (why it might work)
4. Expected statistical edge
5. Testing parameters
6. Risk factors"""

        new_hypotheses = await self.think(hypothesis_prompt)

        hypotheses = {
            "timestamp": datetime.utcnow().isoformat(),
            "market_context": market_context,
            "hypotheses": new_hypotheses
        }
        self.hypothesis_library.append(hypotheses)

        # Alert strategy testing team
        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],
            message_type="new_hypotheses",
            content=hypotheses
        )
        await self.send_message(message)

        return [hypotheses]

    async def refine_hypothesis(
        self,
        hypothesis_name: str,
        test_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Refine a hypothesis based on test results."""
        refinement_prompt = f"""Refine this hypothesis based on test results:

Hypothesis: {hypothesis_name}

Test Results:
{json.dumps(test_results, indent=2)}

Provide:
1. Results interpretation
2. Hypothesis was right/wrong and why
3. Adjustments to improve performance
4. New testing direction
5. Confidence in refined hypothesis
6. Next steps"""

        refinement = await self.think(refinement_prompt)

        self.tested_hypotheses[hypothesis_name] = test_results

        return {
            "hypothesis": hypothesis_name,
            "refinement": refinement,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "generate":
            result = await self.generate_hypotheses(
                task.get("market_context", {}),
                task.get("observations", [])
            )
            return {"hypotheses": result}

        elif task_type == "refine":
            result = await self.refine_hypothesis(
                task.get("hypothesis_name"),
                task.get("test_results", {})
            )
            return result

        return {"error": "Unknown task type"}


class KnowledgeRefinementAgent(BaseAgent):
    """Consolidates learning and refines system knowledge."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize knowledge refinement agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_knowledge_system_prompt()
        super().__init__(config, message_bus)
        self.knowledge_base: Dict[str, Dict[str, Any]] = {}
        self.learned_patterns: List[Dict[str, Any]] = []
        self.system_updates: List[Dict[str, Any]] = []

    def _get_knowledge_system_prompt(self) -> str:
        """Get system prompt for knowledge refinement."""
        return """You are a Knowledge Refinement Agent in a multi-agent trading system.

Your responsibilities:
1. Consolidate learning across the system
2. Update system knowledge base
3. Identify generalizable patterns
4. Document lessons learned
5. Create trading rules from validated patterns
6. Maintain hypothesis validity log

You synthesize information from:
- Performance analysis (what worked)
- Strategy testing results (validated rules)
- Economic analysis (macroeconomic relationships)
- Technical analysis (price patterns)
- Behavioral insights (psychology factors)

You create:
- Trading rule documents
- Pattern library entries
- Economic factor relationships
- Risk management guidelines
- Strategy parameter ranges
- Behavioral guidelines"""

    async def consolidate_learning(
        self,
        validated_patterns: List[Dict[str, Any]],
        performance_insights: List[str]
    ) -> Dict[str, Any]:
        """Consolidate learning into knowledge base."""
        consolidation_prompt = f"""Consolidate these insights into trading knowledge:

Validated Patterns ({len(validated_patterns)}):
{json.dumps(validated_patterns[:3], indent=2)}

Performance Insights:
{json.dumps(performance_insights, indent=2)}

Provide:
1. Core principles extracted
2. New rules to add to knowledge base
3. Pattern relationships and interactions
4. Confidence levels
5. Scope of applicability
6. Integration with existing knowledge"""

        consolidation = await self.think(consolidation_prompt)

        update = {
            "timestamp": datetime.utcnow().isoformat(),
            "patterns": len(validated_patterns),
            "consolidation": consolidation
        }
        self.system_updates.append(update)

        # Broadcast knowledge update
        message = Message(
            sender_id=self.config.agent_id,
            sender_role=self.config.role,
            recipient_ids=[],
            message_type="knowledge_update",
            content=update
        )
        await self.send_message(message)

        return update

    async def update_knowledge_base(
        self,
        category: str,
        knowledge_item: Dict[str, Any]
    ):
        """Update knowledge base with new knowledge."""
        if category not in self.knowledge_base:
            self.knowledge_base[category] = {}

        self.knowledge_base[category][
            knowledge_item.get("name", str(datetime.utcnow().timestamp()))
        ] = knowledge_item

        learned = {
            "timestamp": datetime.utcnow().isoformat(),
            "category": category,
            "knowledge_item": knowledge_item
        }
        self.learned_patterns.append(learned)

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task."""
        task_type = task.get("type")

        if task_type == "consolidate":
            result = await self.consolidate_learning(
                task.get("validated_patterns", []),
                task.get("performance_insights", [])
            )
            return result

        elif task_type == "update_knowledge":
            await self.update_knowledge_base(
                task.get("category"),
                task.get("knowledge_item", {})
            )
            return {"status": "knowledge_updated"}

        elif task_type == "knowledge_report":
            analysis = await self.analyze({
                "knowledge_categories": len(self.knowledge_base),
                "learned_patterns": len(self.learned_patterns)
            })
            return analysis

        return {"error": "Unknown task type"}
