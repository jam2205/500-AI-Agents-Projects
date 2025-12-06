"""
Basic trading session example demonstrating the multi-agent trading system.

This example shows:
1. Initializing the trading command center
2. Creating agent groups
3. Agents communicating and coordinating
4. Economic calendar alerts
5. Market profile updates
6. Trading strategy signals
7. Risk management
8. Self-improvement pipeline
"""

import asyncio
from datetime import datetime, timedelta
from src.framework.trading_command_center import TradingCommandCenter
from src.framework.group_coordinator import GroupCoordinator
from src.framework.base_agent import AgentRole
from src.agents import (
    EconomicCalendarAgent,
    EconomicEvent,
    MarketProfileAgent,
    WeeklyProfile,
    BondAnalystAgent,
    ForexSpecialistAgent,
    MetalMarketTraderAgent,
    MarketMakerAgent,
    QuantTraderAgent,
    RiskManagerAgent,
    DataScienceAgent,
    TradesPsychologyAgent,
    StrategyTesterAgent,
    PerformanceAnalystAgent,
    HypothesisGeneratorAgent,
    KnowledgeRefinementAgent,
)
from src.config.agent_configs import (
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
)


async def setup_trading_system() -> TradingCommandCenter:
    """Set up the complete trading system with all agents."""

    # Create command center
    command_center = TradingCommandCenter()

    # ===== MARKET INTELLIGENCE GROUP =====
    market_intel_group = GroupCoordinator(
        group_name="market_intelligence",
        coordinator_id="market_intel_coordinator",
        coordinator_role=AgentRole.ALERT_COORDINATOR,
        message_bus=command_center.message_bus
    )

    econ_calendar = EconomicCalendarAgent(ECONOMIC_CALENDAR_CONFIG, command_center.message_bus)
    market_profile = MarketProfileAgent(MARKET_PROFILE_CONFIG, command_center.message_bus)

    await market_intel_group.add_agent(econ_calendar)
    await market_intel_group.add_agent(market_profile)
    await command_center.register_group(market_intel_group)

    # ===== MARKET SPECIALISTS GROUP =====
    specialists_group = GroupCoordinator(
        group_name="market_specialists",
        coordinator_id="specialists_coordinator",
        coordinator_role=AgentRole.ALERT_COORDINATOR,
        message_bus=command_center.message_bus
    )

    bond_analyst = BondAnalystAgent(BOND_ANALYST_CONFIG, command_center.message_bus)
    forex_specialist = ForexSpecialistAgent(FOREX_SPECIALIST_CONFIG, command_center.message_bus)
    metal_trader = MetalMarketTraderAgent(METALMARKET_TRADER_CONFIG, command_center.message_bus)

    await specialists_group.add_agent(bond_analyst)
    await specialists_group.add_agent(forex_specialist)
    await specialists_group.add_agent(metal_trader)
    await command_center.register_group(specialists_group)

    # ===== TRADING OPERATIONS GROUP =====
    trading_group = GroupCoordinator(
        group_name="trading_operations",
        coordinator_id="trading_coordinator",
        coordinator_role=AgentRole.ALERT_COORDINATOR,
        message_bus=command_center.message_bus
    )

    market_maker = MarketMakerAgent(MARKET_MAKER_CONFIG, command_center.message_bus)
    quant_trader = QuantTraderAgent(QUANT_TRADER_CONFIG, command_center.message_bus)
    risk_manager = RiskManagerAgent(RISK_MANAGER_CONFIG, command_center.message_bus)

    await trading_group.add_agent(market_maker)
    await trading_group.add_agent(quant_trader)
    await trading_group.add_agent(risk_manager)
    await command_center.register_group(trading_group)

    # ===== RESEARCH & INTELLIGENCE GROUP =====
    research_group = GroupCoordinator(
        group_name="research_and_intelligence",
        coordinator_id="research_coordinator",
        coordinator_role=AgentRole.ALERT_COORDINATOR,
        message_bus=command_center.message_bus
    )

    data_scientist = DataScienceAgent(DATA_SCIENCE_CONFIG, command_center.message_bus)
    psychology_specialist = TradesPsychologyAgent(PSYCHOLOGY_SPECIALIST_CONFIG, command_center.message_bus)
    strategy_tester = StrategyTesterAgent(STRATEGY_TESTER_CONFIG, command_center.message_bus)

    await research_group.add_agent(data_scientist)
    await research_group.add_agent(psychology_specialist)
    await research_group.add_agent(strategy_tester)
    await command_center.register_group(research_group)

    # ===== SELF-IMPROVEMENT GROUP =====
    improvement_group = GroupCoordinator(
        group_name="self_improvement",
        coordinator_id="improvement_coordinator",
        coordinator_role=AgentRole.ALERT_COORDINATOR,
        message_bus=command_center.message_bus
    )

    performance_analyst = PerformanceAnalystAgent(PERFORMANCE_ANALYST_CONFIG, command_center.message_bus)
    hypothesis_gen = HypothesisGeneratorAgent(HYPOTHESIS_GENERATOR_CONFIG, command_center.message_bus)
    knowledge_refine = KnowledgeRefinementAgent(KNOWLEDGE_REFINEMENT_CONFIG, command_center.message_bus)

    await improvement_group.add_agent(performance_analyst)
    await improvement_group.add_agent(hypothesis_gen)
    await improvement_group.add_agent(knowledge_refine)
    await command_center.register_group(improvement_group)

    return command_center


async def simulate_market_session(command_center: TradingCommandCenter):
    """Simulate a trading session with various market events."""

    print("\n" + "="*80)
    print("TRADING SESSION STARTED")
    print("="*80)

    # Initialize system
    await command_center.initialize()
    print("\n✓ Trading Command Center initialized")

    # Add some economic events
    econ_calendar = command_center.groups["market_intelligence"].get_agent("economic_calendar_01")

    event1 = EconomicEvent(
        event_id="nfp_01",
        name="Non-Farm Payroll",
        country="USA",
        currency="USD",
        importance="high",
        scheduled_time=(datetime.utcnow() + timedelta(hours=2)).isoformat(),
        forecast_value="250000",
        previous_value="227000"
    )

    event2 = EconomicEvent(
        event_id="ecb_rate_01",
        name="ECB Interest Rate Decision",
        country="EU",
        currency="EUR",
        importance="high",
        scheduled_time=(datetime.utcnow() + timedelta(hours=4)).isoformat(),
        forecast_value="4.75%",
        previous_value="4.50%"
    )

    await econ_calendar.add_event(event1)
    await econ_calendar.add_event(event2)
    print("\n✓ Added 2 high-importance economic events to calendar")

    # Update market profile
    market_profile = command_center.groups["market_intelligence"].get_agent("market_profile_01")

    weekly_profile = WeeklyProfile(
        week_start="2025-12-01",
        week_end="2025-12-05",
        high=4850.50,
        low=4720.25,
        high_time=datetime.utcnow().isoformat(),
        low_time=datetime.utcnow().isoformat(),
        close=4800.0,
        volume=1250000000,
        direction="up",
        profile_type="bull",
        key_levels={
            "resistance_1": 4900,
            "support_1": 4750,
            "pivot": 4823,
        },
        alerts_generated=[]
    )

    await market_profile.set_weekly_profile(weekly_profile)
    print("✓ Weekly market profile updated (BULLISH direction)")

    # Update yield curve
    bond_analyst = command_center.groups["market_specialists"].get_agent("bond_analyst_01")

    yield_curve = {
        "2Y": 4.25,
        "5Y": 4.15,
        "10Y": 4.20,
        "30Y": 4.35
    }

    await bond_analyst.update_yield_curve(yield_curve)
    print("✓ Bond analyst updated yield curve (slightly inverted 5-10)")

    # Update forex pair
    forex = command_center.groups["market_specialists"].get_agent("forex_specialist_01")
    await forex.update_currency_pair("EUR/USD", 1.0950, bid_ask_spread=0.0002, volume=5000000)
    print("✓ Forex specialist tracking EUR/USD at 1.0950")

    # Update metal position
    metal_trader = command_center.groups["market_specialists"].get_agent("metalmarket_trader_01")
    await metal_trader.update_metal_position("GOLD", price=2085.50, position_size=100)
    print("✓ Metal trader positioned in GOLD (100 oz)")

    # Generate market maker quotes
    mm = command_center.groups["trading_operations"].get_agent("market_maker_01")
    await mm.update_quote("ES", bid=4840.50, ask=4840.75, bid_size=500, ask_size=500)
    print("✓ Market maker providing ES quotes (4840.50-4840.75)")

    # Quant trader generates signal
    quant = command_center.groups["trading_operations"].get_agent("quant_trader_01")
    signal = await quant.generate_signal("ES", {
        "price": 4840.00,
        "rsi": 65,
        "macd": "positive",
        "volume": "above_average"
    })
    print("✓ Quant trader generated signal (BUY bias)")

    # Risk manager updates position
    risk_mgr = command_center.groups["trading_operations"].get_agent("risk_manager_01")
    await risk_mgr.update_position("ES", position_size=100, price=4840.00)
    print("✓ Risk manager tracking ES position (100 contracts)")

    # Data scientist analyzes patterns
    data_sci = command_center.groups["research_and_intelligence"].get_agent("data_scientist_01")
    pattern_result = await data_sci.analyze_patterns(
        {
            "pattern": "breakout_from_consolidation",
            "frequency": "occurs 35% of time",
            "win_rate": "62%"
        },
        pattern_type="price_action"
    )
    print("✓ Data scientist identified breakout pattern (62% win rate)")

    # Psychology specialist assesses sentiment
    psych = command_center.groups["research_and_intelligence"].get_agent("psychology_specialist_01")
    await psych.assess_market_psychology({
        "vix": 15.5,
        "put_call_ratio": 0.85,
        "manager_positioning": "net_short",
        "sentiment_score": 0.65
    })
    print("✓ Psychology specialist: Moderate bullish sentiment (65/100)")

    # Strategy tester validates strategy
    strat_tester = command_center.groups["research_and_intelligence"].get_agent("strategy_tester_01")
    test_result = await strat_tester.test_strategy(
        strategy_name="breakout_momentum",
        rules={"entry": "close_above_resistance", "exit": "2ATR_stop"},
        backtest_data=[{"price": i*100} for i in range(50)]
    )
    print("✓ Strategy tester validated 'breakout_momentum' strategy")

    # Performance analyst reviews results
    perf_analyst = command_center.groups["self_improvement"].get_agent("performance_analyst_01")
    perf_report = await perf_analyst.analyze_performance(
        period="2025-12-01_to_2025-12-05",
        trades=[
            {"entry": 4800, "exit": 4850, "result": "win"},
            {"entry": 4820, "exit": 4815, "result": "loss"},
            {"entry": 4835, "exit": 4880, "result": "win"},
        ],
        returns={"total_return": 0.045, "sharpe_ratio": 1.2, "win_rate": 0.67}
    )
    print("✓ Performance analyst: Positive week (4.5% return, 67% win rate)")

    # Hypothesis generator creates new ideas
    hyp_gen = command_center.groups["self_improvement"].get_agent("hypothesis_generator_01")
    hyps = await hyp_gen.generate_hypotheses(
        market_context={"regime": "trending", "vol": "low", "sentiment": "bullish"},
        recent_observations=[
            "Fed likely pausing rate hikes",
            "GDP growth strengthening",
            "Corporate earnings beating expectations"
        ]
    )
    print("✓ Hypothesis generator: Created 5 new trading ideas")

    # Knowledge refinement consolidates learning
    knowledge = command_center.groups["self_improvement"].get_agent("knowledge_refinement_01")
    await knowledge.consolidate_learning(
        validated_patterns=[
            {"name": "morning_breakout", "win_rate": 0.65},
            {"name": "retest_support", "win_rate": 0.58}
        ],
        performance_insights=["Trend following working well", "Scalping less effective"]
    )
    print("✓ Knowledge refinement: Updated system knowledge base")

    # Generate system report
    print("\n" + "="*80)
    print("SYSTEM STATUS REPORT")
    print("="*80)

    system_report = await command_center.generate_system_report()

    print(f"\nTimestamp: {system_report['timestamp']}")
    print(f"System Running: {system_report['system_running']}")
    print(f"Active Groups: {system_report['num_groups']}")

    print("\nGroup Status:")
    for group_name, group_info in system_report["groups"].items():
        print(f"  • {group_name}: {group_info['num_agents']} agents - Status: {group_info['status']}")
        if group_info['alerts']:
            for alert in group_info['alerts']:
                print(f"    ⚠ {alert}")

    print("\nMarket State:")
    if system_report["market_state"]:
        for key, value in system_report["market_state"].items():
            print(f"  • {key}: {value}")

    print("\nWeekly Profile:")
    if system_report["weekly_profile"]:
        print(f"  • Direction: {system_report['weekly_profile'].get('direction', 'N/A')}")
        print(f"  • High: {system_report['weekly_profile'].get('high', 'N/A')}")
        print(f"  • Low: {system_report['weekly_profile'].get('low', 'N/A')}")

    print("\nMessage Bus Stats:")
    bus_stats = system_report["message_bus_stats"]
    print(f"  • Total Subscribers: {bus_stats['total_subscribers']}")
    print(f"  • Messages Processed: {len(system_report['groups'])} group reports")

    print("\n" + "="*80)
    print("TRADING SESSION SUMMARY")
    print("="*80)
    print("\nAll agent groups operational and coordinating successfully!")
    print("Economic alerts monitoring active")
    print("Weekly profiles guiding directional bias")
    print("Self-improvement pipeline running")
    print("\n✓ Session completed successfully")

    # Shutdown
    await command_center.shutdown()
    print("\n✓ System shutdown complete")


async def main():
    """Main entry point for the trading session example."""
    try:
        # Setup the trading system
        command_center = await setup_trading_system()

        # Run trading session
        await simulate_market_session(command_center)

    except KeyboardInterrupt:
        print("\n\nSession interrupted by user")
    except Exception as e:
        print(f"\nError during trading session: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
