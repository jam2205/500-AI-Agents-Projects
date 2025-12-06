"""Agent configurations for all trading agents in the system."""

from src.framework.base_agent import AgentConfig, AgentRole

# Economic Calendar Agent
ECONOMIC_CALENDAR_CONFIG = AgentConfig(
    agent_id="economic_calendar_01",
    name="Economic Calendar Monitor",
    role=AgentRole.ECONOMIST,
    group="market_intelligence",
    model="claude-3-5-sonnet-20241022",
    temperature=0.6,
    max_tokens=2048,
    tools=["fetch_economic_calendar", "analyze_event_impact"]
)

# Market Profile Agent
MARKET_PROFILE_CONFIG = AgentConfig(
    agent_id="market_profile_01",
    name="Weekly Market Profile",
    role=AgentRole.MARKET_PROFILER,
    group="market_intelligence",
    model="claude-3-5-sonnet-20241022",
    temperature=0.6,
    max_tokens=2048,
    tools=["track_highs_lows", "identify_key_levels", "broadcast_direction"]
)

# Bond Analyst Agent
BOND_ANALYST_CONFIG = AgentConfig(
    agent_id="bond_analyst_01",
    name="Bond Market Specialist",
    role=AgentRole.BOND_ANALYST,
    group="market_specialists",
    model="claude-3-5-sonnet-20241022",
    temperature=0.7,
    max_tokens=2048,
    tools=["analyze_yield_curve", "assess_credit_spreads", "duration_analysis"]
)

# Forex Specialist Agent
FOREX_SPECIALIST_CONFIG = AgentConfig(
    agent_id="forex_specialist_01",
    name="Forex Trading Specialist",
    role=AgentRole.FOREX_SPECIALIST,
    group="market_specialists",
    model="claude-3-5-sonnet-20241022",
    temperature=0.7,
    max_tokens=2048,
    tools=["analyze_currency_pairs", "carry_trade_analysis", "correlation_analysis"]
)

# MetalMarket Trader Agent
METALMARKET_TRADER_CONFIG = AgentConfig(
    agent_id="metalmarket_trader_01",
    name="Metal Market Specialist",
    role=AgentRole.METALMARKET_TRADER,
    group="market_specialists",
    model="claude-3-5-sonnet-20241022",
    temperature=0.7,
    max_tokens=2048,
    tools=["track_metal_positions", "analyze_futures_curve", "supply_demand"]
)

# Market Maker Agent
MARKET_MAKER_CONFIG = AgentConfig(
    agent_id="market_maker_01",
    name="Market Maker",
    role=AgentRole.MARKET_MAKER,
    group="trading_operations",
    model="claude-3-5-sonnet-20241022",
    temperature=0.5,
    max_tokens=1024,
    tools=["update_quotes", "adjust_spreads", "manage_inventory"]
)

# Quant Trader Agent
QUANT_TRADER_CONFIG = AgentConfig(
    agent_id="quant_trader_01",
    name="Quantitative Trader",
    role=AgentRole.QUANT_TRADER,
    group="trading_operations",
    model="claude-3-5-sonnet-20241022",
    temperature=0.6,
    max_tokens=2048,
    tools=["generate_signals", "backtest_strategies", "optimize_parameters"]
)

# Risk Manager Agent
RISK_MANAGER_CONFIG = AgentConfig(
    agent_id="risk_manager_01",
    name="Risk Manager",
    role=AgentRole.RISK_MANAGER,
    group="trading_operations",
    model="claude-3-5-sonnet-20241022",
    temperature=0.5,
    max_tokens=1024,
    tools=["track_positions", "calculate_var", "enforce_limits"]
)

# Data Science Agent
DATA_SCIENCE_CONFIG = AgentConfig(
    agent_id="data_scientist_01",
    name="Data Science Analyst",
    role=AgentRole.DATA_SCIENTIST,
    group="research_and_intelligence",
    model="claude-3-5-sonnet-20241022",
    temperature=0.7,
    max_tokens=2048,
    tools=["analyze_patterns", "correlation_analysis", "forecast_models"]
)

# Psychology Specialist Agent
PSYCHOLOGY_SPECIALIST_CONFIG = AgentConfig(
    agent_id="psychology_specialist_01",
    name="Trade Psychology Specialist",
    role=AgentRole.PSYCHOLOGY_SPECIALIST,
    group="research_and_intelligence",
    model="claude-3-5-sonnet-20241022",
    temperature=0.6,
    max_tokens=2048,
    tools=["analyze_trader_psychology", "assess_market_sentiment", "bias_detection"]
)

# Strategy Tester Agent
STRATEGY_TESTER_CONFIG = AgentConfig(
    agent_id="strategy_tester_01",
    name="Strategy Tester",
    role=AgentRole.STRATEGY_TESTER,
    group="research_and_intelligence",
    model="claude-3-5-sonnet-20241022",
    temperature=0.6,
    max_tokens=2048,
    tools=["backtest_strategy", "validate_rules", "robustness_testing"]
)

# Performance Analyst Agent
PERFORMANCE_ANALYST_CONFIG = AgentConfig(
    agent_id="performance_analyst_01",
    name="Performance Analyst",
    role=AgentRole.PERFORMANCE_ANALYST,
    group="self_improvement",
    model="claude-3-5-sonnet-20241022",
    temperature=0.6,
    max_tokens=2048,
    tools=["analyze_performance", "identify_improvements", "attribution_analysis"]
)

# Hypothesis Generator Agent
HYPOTHESIS_GENERATOR_CONFIG = AgentConfig(
    agent_id="hypothesis_generator_01",
    name="Hypothesis Generator",
    role=AgentRole.ALERT_COORDINATOR,  # Using similar role
    group="self_improvement",
    model="claude-3-5-sonnet-20241022",
    temperature=0.8,  # Higher creativity
    max_tokens=2048,
    tools=["generate_ideas", "test_hypotheses", "refine_hypotheses"]
)

# Knowledge Refinement Agent
KNOWLEDGE_REFINEMENT_CONFIG = AgentConfig(
    agent_id="knowledge_refinement_01",
    name="Knowledge Refinement",
    role=AgentRole.ALERT_COORDINATOR,  # Using similar role
    group="self_improvement",
    model="claude-3-5-sonnet-20241022",
    temperature=0.6,
    max_tokens=2048,
    tools=["consolidate_learning", "update_knowledge_base", "generate_rules"]
)

# ===== SHORT-TERM BOND DYNAMICS GROUP =====

# Short-Term Bond Monitor Agent
SHORT_TERM_BOND_MONITOR_CONFIG = AgentConfig(
    agent_id="short_term_bond_monitor_01",
    name="Short-Term Bond Monitor",
    role=AgentRole.BOND_ANALYST,
    group="bond_dynamics",
    model="claude-3-5-sonnet-20241022",
    temperature=0.6,
    max_tokens=2048,
    tools=["track_2y_3y_yields", "detect_momentum", "identify_significant_moves"]
)

# Bond-FX Correlation Agent
BOND_FX_CORRELATION_CONFIG = AgentConfig(
    agent_id="bond_fx_correlation_01",
    name="Bond-FX Correlation Monitor",
    role=AgentRole.FOREX_SPECIALIST,
    group="bond_dynamics",
    model="claude-3-5-sonnet-20241022",
    temperature=0.6,
    max_tokens=2048,
    tools=["monitor_correlations", "detect_breaks", "correlation_analysis"]
)

# Lag Time Detector Agent
LAG_TIME_DETECTOR_CONFIG = AgentConfig(
    agent_id="lag_time_detector_01",
    name="Lag Time Detector",
    role=AgentRole.FOREX_SPECIALIST,
    group="bond_dynamics",
    model="claude-3-5-sonnet-20241022",
    temperature=0.6,
    max_tokens=2048,
    tools=["measure_lag_times", "detect_lag_changes", "predict_timing"]
)

# Asset Rotation Alert Agent
ASSET_ROTATION_ALERT_CONFIG = AgentConfig(
    agent_id="asset_rotation_alert_01",
    name="Asset Rotation Specialist",
    role=AgentRole.QUANT_TRADER,
    group="bond_dynamics",
    model="claude-3-5-sonnet-20241022",
    temperature=0.7,
    max_tokens=2048,
    tools=["analyze_rotation", "rate_assets", "detect_state_change", "recommend_trades"]
)

# ===== VOLUME & SEASONALITY GROUP =====

# Market Volume Monitor Agent
MARKET_VOLUME_MONITOR_CONFIG = AgentConfig(
    agent_id="market_volume_monitor_01",
    name="Market Volume Monitor",
    role=AgentRole.DATA_SCIENTIST,
    group="volume_seasonality",
    model="claude-3-5-sonnet-20241022",
    temperature=0.6,
    max_tokens=2048,
    tools=["track_volumes", "detect_anomalies", "analyze_participation"]
)

# Seasonal Pattern Agent
SEASONAL_PATTERN_CONFIG = AgentConfig(
    agent_id="seasonal_pattern_01",
    name="Seasonal Pattern Specialist",
    role=AgentRole.DATA_SCIENTIST,
    group="volume_seasonality",
    model="claude-3-5-sonnet-20241022",
    temperature=0.6,
    max_tokens=2048,
    tools=["identify_patterns", "forecast_seasonality", "calendar_analysis"]
)

# Volume-Seasonal Sync Agent
VOLUME_SEASONAL_SYNC_CONFIG = AgentConfig(
    agent_id="volume_seasonal_sync_01",
    name="Volume-Seasonal Sync",
    role=AgentRole.ALERT_COORDINATOR,
    group="volume_seasonality",
    model="claude-3-5-sonnet-20241022",
    temperature=0.6,
    max_tokens=2048,
    tools=["analyze_sync", "identify_anomalies", "recommend_seasonal_trades"]
)

# Group of all agent configs
ALL_AGENT_CONFIGS = [
    ECONOMIC_CALENDAR_CONFIG,
    MARKET_PROFILE_CONFIG,
    BOND_ANALYST_CONFIG,
    FOREX_SPECIALIST_CONFIG,
    METALMARKET_TRADER_CONFIG,
    MARKET_MAKER_CONFIG,
    QUANT_TRADER_CONFIG,
    RISK_MANAGER_CONFIG,
    DATA_SCIENCE_CONFIG,
    PSYCHOLOGY_SPECIALIST_CONFIG,
    STRATEGY_TESTER_CONFIG,
    PERFORMANCE_ANALYST_CONFIG,
    HYPOTHESIS_GENERATOR_CONFIG,
    KNOWLEDGE_REFINEMENT_CONFIG,
    SHORT_TERM_BOND_MONITOR_CONFIG,
    BOND_FX_CORRELATION_CONFIG,
    LAG_TIME_DETECTOR_CONFIG,
    ASSET_ROTATION_ALERT_CONFIG,
    MARKET_VOLUME_MONITOR_CONFIG,
    SEASONAL_PATTERN_CONFIG,
    VOLUME_SEASONAL_SYNC_CONFIG,
]

# Group organization
AGENT_GROUPS = {
    "market_intelligence": [
        ECONOMIC_CALENDAR_CONFIG,
        MARKET_PROFILE_CONFIG,
    ],
    "market_specialists": [
        BOND_ANALYST_CONFIG,
        FOREX_SPECIALIST_CONFIG,
        METALMARKET_TRADER_CONFIG,
    ],
    "trading_operations": [
        MARKET_MAKER_CONFIG,
        QUANT_TRADER_CONFIG,
        RISK_MANAGER_CONFIG,
    ],
    "research_and_intelligence": [
        DATA_SCIENCE_CONFIG,
        PSYCHOLOGY_SPECIALIST_CONFIG,
        STRATEGY_TESTER_CONFIG,
    ],
    "self_improvement": [
        PERFORMANCE_ANALYST_CONFIG,
        HYPOTHESIS_GENERATOR_CONFIG,
        KNOWLEDGE_REFINEMENT_CONFIG,
    ],
    "bond_dynamics": [
        SHORT_TERM_BOND_MONITOR_CONFIG,
        BOND_FX_CORRELATION_CONFIG,
        LAG_TIME_DETECTOR_CONFIG,
        ASSET_ROTATION_ALERT_CONFIG,
    ],
    "volume_seasonality": [
        MARKET_VOLUME_MONITOR_CONFIG,
        SEASONAL_PATTERN_CONFIG,
        VOLUME_SEASONAL_SYNC_CONFIG,
    ],
}
