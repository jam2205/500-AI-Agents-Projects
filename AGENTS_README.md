# Multi-Agent Trading System

A sophisticated, self-improving multi-agent trading system inspired by military command structures (Auftragstaktik). This system orchestrates specialized AI agents across five coordinated groups to manage trading, market analysis, risk, and continuous improvement.

## 🎯 Vision

Build a **self-sufficient, robust trading ecosystem** with:
- **Specialized Agents**: Each agent has specific expertise (bonds, forex, options, psychology, etc.)
- **Autonomous Groups**: Teams operate independently but coordinate through messaging
- **Self-Improvement Pipeline**: Continuous testing, learning, and refinement of strategies
- **Resilient Architecture**: Graceful degradation and redundancy built-in
- **LLM-Powered Reasoning**: Claude API provides intelligent analysis across all agents

## 🏗️ System Architecture

### Five Core Groups

```
┌─────────────────────────────────────────────────────────┐
│               TRADING COMMAND CENTER                    │
│           (Central Orchestration & Monitoring)          │
└─────────────────────────────────────────────────────────┘
                            │
                    ┌───────┼───────┐
                    │       │       │
        ┌───────────┴───┐  │   ┌────┴─────────┐
        │               │  │   │              │
    ┌─────────┐    ┌────┴──┴──┴──┐    ┌──────────┐
    │ Market  │    │  Trading    │    │Research &│
    │Intell.  │    │ Operations  │    │Intelligence
    └─────────┘    └─────────────┘    └──────────┘
        │               │                  │
    ┌─────────┐        │                  │
    │Specialists◄──────┤              ┌────────┐
    └─────────┘        │              │Self-   │
                       │              │Improve │
                       │              └────────┘
                       │                  │
```

### 1. **Market Intelligence Group** (2 agents)
Monitors markets and provides directional guidance
- 📅 **Economic Calendar Agent**: Tracks economic events, analyzes impact
- 📊 **Market Profile Agent**: Tracks weekly highs/lows, provides direction alerts

### 2. **Market Specialists Group** (3 agents)
Deep expertise in specific market segments
- 💳 **Bond Analyst**: Yield curve, credit spreads, duration
- 💱 **Forex Specialist**: Currency pairs, carry trades, central banks
- ⚒️ **Metal Market Trader**: Precious metals, futures curves, supply/demand

### 3. **Trading Operations Group** (3 agents)
Executes trades and manages risk
- 🔄 **Market Maker**: Provides liquidity, manages spreads
- 📈 **Quant Trader**: Algorithm-based signals, backtesting
- 🛡️ **Risk Manager**: Position tracking, VaR, limits enforcement

### 4. **Research & Intelligence Group** (3 agents)
Analyzes patterns and generates insights
- 🔬 **Data Scientist**: Pattern recognition, correlations, forecasting
- 🧠 **Psychology Specialist**: Sentiment, behavioral biases, extremes
- ✅ **Strategy Tester**: Validates strategies, robustness testing

### 5. **Self-Improvement Group** (3 agents)
Continuous learning and system enhancement
- 📊 **Performance Analyst**: Reviews results, identifies improvements
- 💡 **Hypothesis Generator**: Creates new trading ideas
- 📚 **Knowledge Refinement**: Consolidates learning, updates rules

## 🚀 Quick Start

### Installation

```bash
# Clone and navigate to the project
cd /home/user/500-AI-Agents-Projects

# Install dependencies
pip install anthropic

# Set your API key
export ANTHROPIC_API_KEY="your-api-key-here"
```

### Run Basic Example

```bash
# Run the basic trading session example
python -m src.examples.basic_trading_session
```

This will:
1. Initialize all 14 agents across 5 groups
2. Simulate economic calendar events
3. Update market profiles
4. Generate trading signals
5. Analyze performance
6. Generate system report

### Expected Output

```
================================================================================
TRADING SESSION STARTED
================================================================================

✓ Trading Command Center initialized
✓ Added 2 high-importance economic events to calendar
✓ Weekly market profile updated (BULLISH direction)
✓ Bond analyst updated yield curve (slightly inverted 5-10)
✓ Forex specialist tracking EUR/USD at 1.0950
...

================================================================================
SYSTEM STATUS REPORT
================================================================================

Timestamp: 2025-12-06T...
System Running: True
Active Groups: 5

Group Status:
  • market_intelligence: 2 agents - Status: active
  • market_specialists: 3 agents - Status: active
  • trading_operations: 3 agents - Status: active
  • research_and_intelligence: 3 agents - Status: active
  • self_improvement: 3 agents - Status: active
...
```

## 📁 Project Structure

```
src/
├── framework/                    # Core framework
│   ├── base_agent.py            # BaseAgent class
│   ├── message_bus.py           # Message routing
│   ├── group_coordinator.py     # Group management
│   └── trading_command_center.py # System orchestration
│
├── agents/                       # All trading agents
│   ├── economic_calendar_agent.py      # Economic events
│   ├── market_profile_agent.py         # Weekly highs/lows
│   ├── market_specialists.py           # Bond, Forex, Metal traders
│   ├── trading_agents.py               # MM, Quant, Risk Mgmt
│   ├── research_agents.py              # Data Sci, Psychology, Tester
│   └── improvement_agents.py           # Performance, Hypothesis, Knowledge
│
├── config/
│   └── agent_configs.py         # Configuration for all agents
│
├── examples/
│   └── basic_trading_session.py  # Example trading session
│
└── __init__.py                   # Package init

AGENT_ARCHITECTURE.md             # Detailed architecture docs
AGENTS_README.md                  # This file
```

## 🔧 Agent Responsibilities

### Economic Calendar Agent
```python
# Monitor economic events
event = EconomicEvent(
    event_id="nfp_01",
    name="Non-Farm Payroll",
    country="USA",
    importance="high",
    scheduled_time="2025-12-06T13:30:00",
    forecast_value="250000",
    previous_value="227000"
)

await econ_agent.add_event(event)
await econ_agent.update_event("nfp_01", {"actual_value": "272000", "impact": "beats"})
```

### Market Profile Agent
```python
# Track weekly structure
profile = WeeklyProfile(
    week_start="2025-12-01",
    week_end="2025-12-05",
    high=4850.50,
    low=4720.25,
    direction="up",
    profile_type="bull"
)

await profile_agent.set_weekly_profile(profile)
await profile_agent.broadcast_market_direction()
```

### Bond Analyst
```python
# Analyze yield curve
await bond_agent.update_yield_curve({
    "2Y": 4.25,
    "5Y": 4.15,
    "10Y": 4.20,
    "30Y": 4.35
})
```

### Quant Trader
```python
# Generate trading signals
signal = await quant_agent.generate_signal("ES", {
    "price": 4840.00,
    "rsi": 65,
    "macd": "positive",
    "volume": "above_average"
})
```

### Risk Manager
```python
# Track positions and calculate risk
await risk_agent.update_position("ES", position_size=100, price=4840.00)
var_result = await risk_agent.calculate_portfolio_var(confidence_level=0.95)
```

### Performance Analyst
```python
# Review trading results
await perf_agent.analyze_performance(
    period="2025-12-01_to_2025-12-05",
    trades=[...],
    returns={"total_return": 0.045, "sharpe_ratio": 1.2}
)
```

## 📨 Message Types

Agents communicate through typed messages:

```
economic_alert         → High-impact economic events
weekly_profile_update  → Market direction changes
market_level_alert     → Key support/resistance breaks
trading_signal         → Entry/exit recommendations
bond_analysis_update   → Fixed income insights
forex_technical_alert  → Currency pair alerts
position_risk_analysis → Risk assessments
performance_analysis   → Trading results review
new_hypotheses         → Novel trading ideas
knowledge_update       → Learning consolidation
market_psychology_alert → Sentiment analysis
market_direction_alert  → Directional guidance
```

## 🔄 Self-Improvement Pipeline

The system continuously improves through:

```
1. Performance Analysis
   ↓
2. Identify Improvements
   ↓
3. Generate Hypotheses
   ↓
4. Test Strategies
   ↓
5. Consolidate Learning
   ↓
6. Update Knowledge Base
   ↓
7. Implement Improvements
   ↓ (repeat)
```

## 💡 Key Features

### ✅ Async Message Bus
- Non-blocking agent communication
- Pub/Sub architecture
- Message history tracking
- Type-specific subscriptions

### ✅ Group Coordination
- Hierarchical organization
- Coordinated workflows
- Group status reporting
- Cross-group communication

### ✅ LLM Integration
- Claude API for intelligent analysis
- Context-aware prompting
- Multi-turn reasoning
- Continuous learning

### ✅ State Management
- Agent-level state
- Group-level insights
- System metrics
- Performance records

## 🎓 Example: Adding a New Agent

```python
from src.framework.base_agent import BaseAgent, AgentConfig, AgentRole

class MyCustomAgent(BaseAgent):
    """Custom agent for my specific domain."""

    def __init__(self, config: AgentConfig, message_bus=None):
        super().__init__(config, message_bus)

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type")

        if task_type == "analyze":
            data = task.get("data")
            result = await self.analyze(data)
            return result

        return {"error": "Unknown task type"}

# Create config
config = AgentConfig(
    agent_id="my_agent_01",
    name="My Custom Agent",
    role=AgentRole.QUANT_TRADER,
    group="trading_operations"
)

# Create and use agent
agent = MyCustomAgent(config, message_bus)
result = await agent.execute_task({"type": "analyze", "data": {...}})
```

## 📊 System Monitoring

Get complete system status:

```python
report = await command_center.generate_system_report()

# Access group statuses
for group_name, group_info in report["groups"].items():
    print(f"{group_name}: {group_info['status']}")

# Check message bus stats
stats = report["message_bus_stats"]
print(f"Subscribers: {stats['total_subscribers']}")
print(f"Queue size: {stats['queue_size']}")
```

## 🔐 Configuration

All agents are configured in `src/config/agent_configs.py`:

```python
QUANT_TRADER_CONFIG = AgentConfig(
    agent_id="quant_trader_01",
    name="Quantitative Trader",
    role=AgentRole.QUANT_TRADER,
    group="trading_operations",
    model="claude-3-5-sonnet-20241022",
    temperature=0.6,
    max_tokens=2048,
    tools=["generate_signals", "backtest_strategies"]
)
```

Customize agent behavior by modifying:
- `temperature`: 0.0-1.0 (lower = more deterministic)
- `max_tokens`: Response length limit
- `system_prompt`: Custom instructions
- `tools`: Available functions

## 🚀 Advanced Usage

### Running Specific Group

```python
group = await command_center.get_group("trading_operations")
result = await group.coordinate_workflow(
    workflow_name="risk_assessment",
    agents_sequence=["risk_manager_01", "data_scientist_01"],
    initial_data={...}
)
```

### Broadcasting to All Agents

```python
await command_center.broadcast_alert(
    alert_type="market_shock",
    content={"volatility": "spiked", "action": "reduce_exposure"},
    priority="critical"
)
```

### Continuous Task

```python
await market_intel_group.start_continuous_task(
    agent_id="economic_calendar_01",
    task_name="monitor_upcoming_events",
    interval=3600,  # Every hour
    task_func=econ_agent._monitor_events_task
)
```

## 📈 Performance Metrics

System tracks:
- **Trading Metrics**: PnL, Sharpe ratio, win rate, profit factor
- **System Health**: Message latency, queue size, subscriber count
- **Agent Performance**: Task execution time, error rate
- **Group Status**: Active agents, alerts, insights

## 🔮 Future Enhancements

- [ ] Reinforcement learning for signal improvement
- [ ] Multi-asset class support
- [ ] Real-time data feed integration
- [ ] Advanced risk models (VaR, stress testing)
- [ ] Distributed deployment
- [ ] API exposure for external systems
- [ ] Backtesting engine
- [ ] Compliance and regulatory reporting
- [ ] Web dashboard for monitoring

## 📝 Contributing

To add new agents or features:

1. Create agent class inheriting from `BaseAgent`
2. Implement `execute_task()` method
3. Add configuration to `agent_configs.py`
4. Create integration example
5. Document in architecture guide

## 📄 License

Part of the 500-AI-Agents-Projects collection

## 📚 Documentation

- **AGENT_ARCHITECTURE.md**: Detailed architecture and design
- **src/framework/base_agent.py**: Core agent class documentation
- **src/agents/**: Individual agent implementation details
- **src/examples/**: Working examples and patterns

## 🙋 Support

For questions or issues:
1. Check existing documentation
2. Review example implementations
3. Examine agent system prompts
4. Test with basic_trading_session.py

---

**Version**: 1.0.0
**Last Updated**: December 2025
**Status**: Production Ready
