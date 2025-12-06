"""Base Agent class for all trading agents in the system."""

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from anthropic import Anthropic

class AgentRole(Enum):
    """Enumeration of agent roles in the trading system."""
    MARKET_MAKER = "market_maker"
    QUANT_TRADER = "quant_trader"
    METALMARKET_TRADER = "metalmarket_trader"
    BOND_ANALYST = "bond_analyst"
    FOREX_SPECIALIST = "forex_specialist"
    DATA_SCIENTIST = "data_scientist"
    ECONOMIST = "economist"
    PSYCHOLOGY_SPECIALIST = "psychology_specialist"
    MARKET_PROFILER = "market_profiler"
    STRATEGY_TESTER = "strategy_tester"
    RISK_MANAGER = "risk_manager"
    PERFORMANCE_ANALYST = "performance_analyst"
    ALERT_COORDINATOR = "alert_coordinator"


@dataclass
class Message:
    """Message structure for inter-agent communication."""
    sender_id: str
    sender_role: AgentRole
    recipient_ids: List[str]  # Can be broadcast to all if empty
    message_type: str  # e.g., "alert", "data_request", "analysis", "status"
    content: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    message_id: str = field(default_factory=lambda: str(datetime.utcnow().timestamp()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        data = asdict(self)
        data['sender_role'] = self.sender_role.value
        return data


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    agent_id: str
    name: str
    role: AgentRole
    group: str  # e.g., "market_ops", "trading_ops", "research"
    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    max_tokens: int = 2048
    system_prompt: Optional[str] = None
    tools: List[str] = field(default_factory=list)
    knowledge_base: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Base class for all trading agents."""

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize agent with configuration."""
        self.config = config
        self.message_bus = message_bus
        self.client = Anthropic()
        self.conversation_history: List[Dict[str, str]] = []
        self.state: Dict[str, Any] = {}
        self.performance_metrics: Dict[str, Any] = {}

    async def initialize(self):
        """Initialize agent - override in subclasses for custom setup."""
        pass

    async def send_message(self, message: Message):
        """Send a message to other agents via the message bus."""
        if self.message_bus:
            await self.message_bus.publish(message)

    async def receive_message(self, message: Message):
        """Receive and process a message from another agent."""
        # Store in conversation history for context
        self.conversation_history.append({
            "role": "user",
            "content": f"[{message.sender_role.value}]: {json.dumps(message.content)}"
        })

    async def think(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Use LLM to think through a problem."""
        # Build context-aware prompt
        if context:
            prompt = f"{prompt}\n\nContext: {json.dumps(context, indent=2)}"

        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": prompt
        })

        # Call Claude
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=self.config.system_prompt or self._get_default_system_prompt(),
            messages=self.conversation_history
        )

        thought = response.content[0].text

        # Add to history for continuity
        self.conversation_history.append({
            "role": "assistant",
            "content": thought
        })

        return thought

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for the agent."""
        return f"""You are a {self.config.role.value} agent in a multi-agent trading system.
Your agent ID: {self.config.agent_id}
Agent group: {self.config.group}

You operate as part of a larger trading ecosystem where:
- Multiple specialized agents collaborate on trading decisions
- You have specific expertise in {self.config.role.value}
- You receive alerts and data from other agents
- You make recommendations based on your analysis
- You report performance metrics and insights

Be concise, analytical, and actionable in your responses."""

    @abstractmethod
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task - must be implemented by subclasses."""
        pass

    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data and return insights."""
        analysis_prompt = f"""Analyze the following data and provide key insights:

{json.dumps(data, indent=2)}

Provide structured analysis with:
1. Key findings
2. Relevant patterns
3. Recommendations or actions"""

        analysis = await self.think(analysis_prompt)
        return {
            "analysis": analysis,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": self.config.agent_id
        }

    def update_metrics(self, metrics: Dict[str, Any]):
        """Update agent performance metrics."""
        self.performance_metrics.update(metrics)

    def get_state(self) -> Dict[str, Any]:
        """Get current agent state."""
        return {
            "agent_id": self.config.agent_id,
            "role": self.config.role.value,
            "state": self.state,
            "metrics": self.performance_metrics,
            "conversation_history_length": len(self.conversation_history)
        }

    async def shutdown(self):
        """Clean shutdown - override in subclasses for cleanup."""
        pass
