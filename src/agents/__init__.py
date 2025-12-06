"""Trading agents - specialized AI agents for different market roles."""

from .economic_calendar_agent import EconomicCalendarAgent, EconomicEvent
from .market_profile_agent import MarketProfileAgent, WeeklyProfile
from .market_specialists import (
    BondAnalystAgent,
    ForexSpecialistAgent,
    MetalMarketTraderAgent,
)
from .trading_agents import (
    MarketMakerAgent,
    QuantTraderAgent,
    RiskManagerAgent,
)
from .research_agents import (
    DataScienceAgent,
    TradesPsychologyAgent,
    StrategyTesterAgent,
)
from .improvement_agents import (
    PerformanceAnalystAgent,
    HypothesisGeneratorAgent,
    KnowledgeRefinementAgent,
)
from .bond_dynamics_agents import (
    ShortTermBondMonitorAgent,
    BondFXCorrelationAgent,
    LagTimeDetectorAgent,
    AssetRotationAlertAgent,
)

__all__ = [
    "EconomicCalendarAgent",
    "EconomicEvent",
    "MarketProfileAgent",
    "WeeklyProfile",
    "BondAnalystAgent",
    "ForexSpecialistAgent",
    "MetalMarketTraderAgent",
    "MarketMakerAgent",
    "QuantTraderAgent",
    "RiskManagerAgent",
    "DataScienceAgent",
    "TradesPsychologyAgent",
    "StrategyTesterAgent",
    "PerformanceAnalystAgent",
    "HypothesisGeneratorAgent",
    "KnowledgeRefinementAgent",
    "ShortTermBondMonitorAgent",
    "BondFXCorrelationAgent",
    "LagTimeDetectorAgent",
    "AssetRotationAlertAgent",
]
