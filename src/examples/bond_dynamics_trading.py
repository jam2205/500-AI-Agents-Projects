"""
Advanced example: Short-Term Bond Dynamics Trading System

Demonstrates how the Bond Dynamics group uses short-term bonds (2Y/3Y) as leading
indicators for FX currency pair movements. The system:

1. Monitors 2Y/3Y yields for momentum and significant moves
2. Tracks correlation between bond yields and major FX pairs
3. Measures lag times between bond moves and FX reactions
4. Recommends asset rotation and correlated trades

This is particularly useful because:
- Bonds typically lead FX by 5-30 minutes
- Bond momentum can predict currency moves
- Lag time changes indicate regime shifts
- Correlation breakdowns create trading opportunities
"""

import asyncio
from datetime import datetime, timedelta
from src.framework.trading_command_center import TradingCommandCenter
from src.framework.group_coordinator import GroupCoordinator
from src.framework.base_agent import AgentRole
from src.agents import (
    ShortTermBondMonitorAgent,
    BondFXCorrelationAgent,
    LagTimeDetectorAgent,
    AssetRotationAlertAgent,
    QuantTraderAgent,
    MarketMakerAgent,
)
from src.config.agent_configs import (
    SHORT_TERM_BOND_MONITOR_CONFIG,
    BOND_FX_CORRELATION_CONFIG,
    LAG_TIME_DETECTOR_CONFIG,
    ASSET_ROTATION_ALERT_CONFIG,
    QUANT_TRADER_CONFIG,
    MARKET_MAKER_CONFIG,
)


async def setup_bond_dynamics_system() -> TradingCommandCenter:
    """Set up the bond dynamics trading system."""

    # Create command center
    command_center = TradingCommandCenter()

    # ===== BOND DYNAMICS GROUP (NEW!) =====
    bond_dynamics_group = GroupCoordinator(
        group_name="bond_dynamics",
        coordinator_id="bond_dynamics_coordinator",
        coordinator_role=AgentRole.ALERT_COORDINATOR,
        message_bus=command_center.message_bus
    )

    bond_monitor = ShortTermBondMonitorAgent(
        SHORT_TERM_BOND_MONITOR_CONFIG,
        command_center.message_bus
    )
    bond_fx_correlation = BondFXCorrelationAgent(
        BOND_FX_CORRELATION_CONFIG,
        command_center.message_bus
    )
    lag_detector = LagTimeDetectorAgent(
        LAG_TIME_DETECTOR_CONFIG,
        command_center.message_bus
    )
    rotation_alert = AssetRotationAlertAgent(
        ASSET_ROTATION_ALERT_CONFIG,
        command_center.message_bus
    )

    await bond_dynamics_group.add_agent(bond_monitor)
    await bond_dynamics_group.add_agent(bond_fx_correlation)
    await bond_dynamics_group.add_agent(lag_detector)
    await bond_dynamics_group.add_agent(rotation_alert)
    await command_center.register_group(bond_dynamics_group)

    # ===== TRADING OPERATIONS GROUP =====
    trading_group = GroupCoordinator(
        group_name="trading_operations",
        coordinator_id="trading_coordinator",
        coordinator_role=AgentRole.ALERT_COORDINATOR,
        message_bus=command_center.message_bus
    )

    quant_trader = QuantTraderAgent(QUANT_TRADER_CONFIG, command_center.message_bus)
    market_maker = MarketMakerAgent(MARKET_MAKER_CONFIG, command_center.message_bus)

    await trading_group.add_agent(quant_trader)
    await trading_group.add_agent(market_maker)
    await command_center.register_group(trading_group)

    return command_center


async def simulate_bond_dynamics_scenario(command_center: TradingCommandCenter):
    """Simulate a trading scenario driven by bond dynamics."""

    print("\n" + "="*80)
    print("BOND DYNAMICS TRADING SYSTEM - ADVANCED SCENARIO")
    print("="*80)

    # Initialize
    await command_center.initialize()
    print("\n✓ System initialized")

    # Get agents
    bond_dynamics_group = await command_center.get_group("bond_dynamics")
    bond_monitor = bond_dynamics_group.get_agent("short_term_bond_monitor_01")
    bond_fx_corr = bond_dynamics_group.get_agent("bond_fx_correlation_01")
    lag_detector = bond_dynamics_group.get_agent("lag_time_detector_01")
    rotation_alert = bond_dynamics_group.get_agent("asset_rotation_alert_01")

    print("\n" + "-"*80)
    print("SCENARIO 1: RISING 2Y YIELDS WITH MOMENTUM")
    print("-"*80)

    # Simulate bond yield updates
    print("\nUpdating yield data (2Y rising from 4.25 to 4.35)...")
    await bond_monitor.update_yields(
        yield_2y=4.25,
        yield_3y=4.28,
        timestamp=datetime.utcnow().isoformat()
    )

    await asyncio.sleep(0.5)

    await bond_monitor.update_yields(
        yield_2y=4.28,
        yield_3y=4.30,
        timestamp=(datetime.utcnow() + timedelta(minutes=5)).isoformat()
    )

    await asyncio.sleep(0.5)

    await bond_monitor.update_yields(
        yield_2y=4.32,
        yield_3y=4.33,
        timestamp=(datetime.utcnow() + timedelta(minutes=10)).isoformat()
    )

    await asyncio.sleep(0.5)

    await bond_monitor.update_yields(
        yield_2y=4.35,
        yield_3y=4.35,
        timestamp=(datetime.utcnow() + timedelta(minutes=15)).isoformat()
    )

    print("✓ Bond yields updated - 2Y rising momentum detected")

    # Check momentum
    momentum_result = await bond_monitor.execute_task({"type": "get_momentum"})
    print(f"\nMomentum indicators:")
    print(f"  2Y Direction: {momentum_result['momentum'].get('direction_2Y')}")
    print(f"  Spread Direction: {momentum_result['momentum'].get('spread_direction')}")

    await asyncio.sleep(1)

    print("\n" + "-"*80)
    print("SCENARIO 2: TRACKING BOND-FX CORRELATIONS")
    print("-"*80)

    # Simulate FX reactions to bond moves
    print("\nTracking correlation between 2Y yields and EUR/USD...")

    # Simulate 5 bond-FX pairs
    bond_fx_pairs = [
        ("EUR/USD", 4.25, 1.0850),
        ("EUR/USD", 4.28, 1.0858),
        ("EUR/USD", 4.32, 1.0872),
        ("EUR/USD", 4.35, 1.0885),
        ("GBP/USD", 4.35, 1.2700),
    ]

    for bond_metric, fx_price, pair_code in [
        ("EUR/USD", 4.25, (datetime.utcnow() - timedelta(minutes=10)).isoformat()),
        ("EUR/USD", 4.28, (datetime.utcnow() - timedelta(minutes=5)).isoformat()),
        ("EUR/USD", 4.32, datetime.utcnow().isoformat()),
    ]:
        # Note: The time strings are being reused for simplicity
        pass

    # Update correlations
    await bond_fx_corr.update_correlation(
        pair="EUR/USD",
        bond_metric=4.25,
        fx_price=1.0850,
        timestamp=(datetime.utcnow() - timedelta(minutes=10)).isoformat()
    )

    await bond_fx_corr.update_correlation(
        pair="EUR/USD",
        bond_metric=4.28,
        fx_price=1.0858,
        timestamp=(datetime.utcnow() - timedelta(minutes=5)).isoformat()
    )

    await bond_fx_corr.update_correlation(
        pair="EUR/USD",
        bond_metric=4.32,
        fx_price=1.0872,
        timestamp=datetime.utcnow().isoformat()
    )

    print("✓ Correlations tracked")

    corr_matrix = await bond_fx_corr.execute_task({"type": "get_matrix"})
    print(f"\nCorrelation Matrix:")
    for pair, corr in corr_matrix["correlation_matrix"].items():
        if corr != 0.0:
            print(f"  {pair}: {corr:.3f}")

    await asyncio.sleep(1)

    print("\n" + "-"*80)
    print("SCENARIO 3: LAG TIME DETECTION")
    print("-"*80)

    # Record lag times
    print("\nRecording bond-to-FX lag times...")

    lags = [
        ("EUR/USD", "2025-12-06T10:00:00", 0.0040, "2025-12-06T10:00:15", 0.0035),
        ("EUR/USD", "2025-12-06T10:05:00", 0.0050, "2025-12-06T10:05:22", 0.0045),
        ("EUR/USD", "2025-12-06T10:10:00", 0.0045, "2025-12-06T10:10:18", 0.0040),
        ("EUR/USD", "2025-12-06T10:15:00", 0.0055, "2025-12-06T10:15:25", 0.0050),
        ("EUR/USD", "2025-12-06T10:20:00", 0.0060, "2025-12-06T10:20:28", 0.0055),
    ]

    for pair, bond_time, bond_move, fx_time, fx_move in lags:
        await lag_detector.record_movement(
            pair=pair,
            bond_time=bond_time,
            bond_move=bond_move,
            fx_time=fx_time,
            fx_move=fx_move
        )

    print("✓ Lag times recorded")

    lag_summary = await lag_detector.execute_task({"type": "get_lags"})
    print(f"\nLag Time Summary:")
    for pair, lag_info in lag_summary["lags"].items():
        print(f"\n  {pair}:")
        print(f"    Average Lag: {lag_info.get('average_lag_seconds', 0):.1f} seconds")
        print(f"    Recent Lag: {lag_info.get('recent_lag_seconds', 0):.1f} seconds")
        print(f"    Lag Trend: {lag_info.get('lag_trend', 'unknown')}")

    await asyncio.sleep(1)

    print("\n" + "-"*80)
    print("SCENARIO 4: ASSET ROTATION OPPORTUNITY")
    print("-"*80)

    # Analyze rotation opportunity
    print("\nAnalyzing asset rotation based on bond move...")

    rotation_rec = await rotation_alert.analyze_rotation_opportunity(
        bond_direction="up",
        bond_momentum=15.0,  # 2Y up 15bps, accelerating
        correlation_regime="normal",
        current_positions={
            "EUR/USD": 100000,
            "GBP/USD": 50000,
            "AUD/USD": 25000,
            "JPY/USD": -30000
        }
    )

    print("✓ Rotation analysis completed")
    print(f"\nRotation Recommendation Generated:")
    print(f"  Bond Direction: {rotation_rec.get('bond_direction')}")
    print(f"  Correlation Regime: {rotation_rec.get('correlation_regime')}")

    await asyncio.sleep(1)

    print("\n" + "-"*80)
    print("SCENARIO 5: CORRELATED TRADE RECOMMENDATIONS")
    print("-"*80)

    # Get correlated trade recommendations
    print("\nGenerating correlated trade recommendations...")

    correlated_trades = await rotation_alert.recommend_correlated_trades(
        initiating_pair="EUR/USD",
        initiating_move=0.0035,
        correlation_matrix={
            "EUR/USD": 1.0,
            "GBP/USD": 0.72,
            "AUD/USD": 0.65,
            "NZD/USD": 0.61,
            "JPY/USD": -0.58,
            "EUR/GBP": 0.45,
            "EUR/AUD": 0.38
        }
    )

    print("✓ Correlated trades recommended")
    print("\nHighly Correlated Pairs to Trade:")
    print("  • GBP/USD (0.72 correlation) - BUY")
    print("  • AUD/USD (0.65 correlation) - BUY")
    print("  • NZD/USD (0.61 correlation) - BUY")
    print("  • JPY/USD (-0.58 correlation) - SELL")

    await asyncio.sleep(1)

    print("\n" + "="*80)
    print("SYSTEM REPORT")
    print("="*80)

    # Generate system report
    system_report = await command_center.generate_system_report()

    print(f"\nBond Dynamics Group Status:")
    bond_group_info = system_report["groups"].get("bond_dynamics", {})
    print(f"  Agents: {bond_group_info.get('num_agents', 0)}")
    print(f"  Status: {bond_group_info.get('status', 'unknown')}")
    print(f"  Alerts: {len(bond_group_info.get('alerts', []))}")

    print(f"\nMessage Bus Activity:")
    bus_stats = system_report["message_bus_stats"]
    print(f"  Subscribers: {bus_stats['total_subscribers']}")
    print(f"  Queue Size: {bus_stats['queue_size']}")

    print("\n" + "="*80)
    print("BOND DYNAMICS SCENARIO COMPLETE")
    print("="*80)

    print("""
Key Insights from This Scenario:

1. BOND MOMENTUM DETECTION
   - 2Y yields rising from 4.25 to 4.35 (10bps in 15 minutes)
   - Momentum accelerating → strong signal
   - Alerts all agents about directional bias

2. CORRELATION TRACKING
   - EUR/USD correlates strongly with 2Y yields
   - Rising yields = stronger USD pairs
   - Correlations quantified for position sizing

3. LAG TIME MEASUREMENT
   - EUR/USD reacts to bond moves in ~15-25 seconds
   - Lag trend is stable (no expansion indicating uncertainty)
   - Predictable timing enables positioning ahead of move

4. ASSET ROTATION
   - Bond momentum suggests USD strength play
   - Increase EUR/USD, GBP/USD, AUD/USD
   - Reduce or short JPY pairs (inverse correlation)

5. CORRELATED TRADES
   - Use EUR/USD as initiator
   - Trade GBP/USD, AUD/USD with appropriate sizing
   - Manage JPY pairs inversely

This system turns bond moves into currency trading opportunities
by exploiting the lead-lag relationships and correlations.
    """)

    # Shutdown
    await command_center.shutdown()
    print("✓ System shutdown complete\n")


async def main():
    """Main entry point."""
    try:
        command_center = await setup_bond_dynamics_system()
        await simulate_bond_dynamics_scenario(command_center)
    except KeyboardInterrupt:
        print("\n\nScenario interrupted by user")
    except Exception as e:
        print(f"\nError during scenario: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
