"""
Volume & Seasonality Trading System Example

Demonstrates how the Volume & Seasonality group identifies trading opportunities
by correlating market volumes with seasonal patterns.

This system:
1. Monitors volumes across all major markets
2. Identifies seasonal patterns and expectations
3. Correlates high/low volume with seasonal periods
4. Generates trading signals when both align
5. Detects seasonal anomalies in volume behavior
"""

import asyncio
from datetime import datetime, timedelta
from src.framework.trading_command_center import TradingCommandCenter
from src.framework.group_coordinator import GroupCoordinator
from src.framework.base_agent import AgentRole
from src.agents import (
    MarketVolumeMonitorAgent,
    SeasonalPatternAgent,
    VolumeSeasonalSyncAgent,
)
from src.config.agent_configs import (
    MARKET_VOLUME_MONITOR_CONFIG,
    SEASONAL_PATTERN_CONFIG,
    VOLUME_SEASONAL_SYNC_CONFIG,
)


async def setup_volume_seasonality_system() -> TradingCommandCenter:
    """Set up the volume-seasonality trading system."""

    command_center = TradingCommandCenter()

    # ===== VOLUME & SEASONALITY GROUP =====
    volume_seasonal_group = GroupCoordinator(
        group_name="volume_seasonality",
        coordinator_id="volume_seasonal_coordinator",
        coordinator_role=AgentRole.ALERT_COORDINATOR,
        message_bus=command_center.message_bus
    )

    volume_monitor = MarketVolumeMonitorAgent(
        MARKET_VOLUME_MONITOR_CONFIG,
        command_center.message_bus
    )
    seasonal_specialist = SeasonalPatternAgent(
        SEASONAL_PATTERN_CONFIG,
        command_center.message_bus
    )
    volume_seasonal_sync = VolumeSeasonalSyncAgent(
        VOLUME_SEASONAL_SYNC_CONFIG,
        command_center.message_bus
    )

    await volume_seasonal_group.add_agent(volume_monitor)
    await volume_seasonal_group.add_agent(seasonal_specialist)
    await volume_seasonal_group.add_agent(volume_seasonal_sync)
    await command_center.register_group(volume_seasonal_group)

    return command_center


async def simulate_volume_seasonality_scenario(command_center: TradingCommandCenter):
    """Simulate volume and seasonality trading scenario."""

    print("\n" + "="*80)
    print("VOLUME & SEASONALITY TRADING SYSTEM")
    print("="*80)

    await command_center.initialize()
    print("\n✓ System initialized")

    # Get agents
    volume_group = await command_center.get_group("volume_seasonality")
    volume_monitor = volume_group.get_agent("market_volume_monitor_01")
    seasonal_specialist = volume_group.get_agent("seasonal_pattern_01")
    volume_sync = volume_group.get_agent("volume_seasonal_sync_01")

    print("\n" + "-"*80)
    print("SCENARIO 1: QUARTER-END VOLUME SURGE")
    print("-"*80)

    print("\nQuarter-end period typically sees:")
    print("  • Portfolio rebalancing (higher volumes)")
    print("  • Window dressing by fund managers")
    print("  • Position squaring before quarter close")
    print("  • Strong close into quarter-end (seasonal bias)")

    # Simulate volume updates leading to quarter-end
    print("\nUpdating volumes as we approach quarter-end...")

    normal_volume_eur = 1_500_000
    normal_volume_gbp = 800_000
    normal_volume_jpy = 2_000_000

    # Simulate increasing volumes as quarter-end approaches
    volumes = [
        ("EUR/USD", normal_volume_eur * 1.1, "Normal pre-quarter activity"),
        ("EUR/USD", normal_volume_eur * 1.3, "Volume picking up"),
        ("EUR/USD", normal_volume_eur * 1.8, "Strong volume into quarter-end"),
        ("EUR/USD", normal_volume_eur * 2.2, "SPIKE: Quarter-end rebalancing"),
        ("GBP/USD", normal_volume_gbp * 1.6, "Following EUR strength"),
        ("JPY/USD", normal_volume_jpy * 1.4, "Volume rise across majors"),
    ]

    for pair, volume, description in volumes:
        await volume_monitor.update_volume(
            symbol=pair,
            volume=volume,
            timestamp=datetime.utcnow().isoformat(),
            market_type="forex"
        )
        print(f"  ✓ {pair}: {volume/1_000_000:.2f}M ({description})")
        await asyncio.sleep(0.2)

    print("\n✓ Quarter-end volume surge detected")

    # Get volume stats
    volume_stats = await volume_monitor.execute_task({"type": "get_stats"})
    print("\nVolume Statistics (all pairs):")
    for pair, stats in volume_stats["stats"].items():
        if stats:
            print(f"  {pair}:")
            print(f"    Current: {stats.get('current_volume', 0)/1_000_000:.2f}M")
            print(f"    Average: {stats.get('average_volume', 0)/1_000_000:.2f}M")
            print(f"    Trend: {stats.get('volume_trend', 'unknown')}")

    await asyncio.sleep(1)

    print("\n" + "-"*80)
    print("SCENARIO 2: IDENTIFYING SEASONAL PATTERNS")
    print("-"*80)

    print("\nRecording historical seasonal data...")
    print("This allows the system to learn seasonal patterns")

    # Record some historical data for seasonal analysis
    historical_dates = [
        ("EUR/USD", "2024-03-29", 1.080, 1_200_000),  # Quarter-end
        ("EUR/USD", "2024-06-28", 1.085, 1_300_000),  # Quarter-end
        ("EUR/USD", "2024-09-30", 1.090, 1_400_000),  # Quarter-end
        ("EUR/USD", "2024-12-27", 1.095, 900_000),    # Year-end holiday
    ]

    for symbol, date, value, volume in historical_dates:
        await seasonal_specialist.record_seasonal_data(symbol, date, value, volume)

    print("✓ Historical seasonal data recorded")

    # Identify seasonal patterns
    print("\nAnalyzing seasonal patterns...")
    seasonal_analysis = await seasonal_specialist.execute_task({
        "type": "identify_patterns",
        "symbol": "EUR/USD"
    })

    print("✓ Seasonal patterns identified")

    # Forecast seasonal behavior
    print("\nForecasting seasonal behavior for current period...")
    seasonal_forecast = await seasonal_specialist.execute_task({
        "type": "forecast",
        "symbol": "EUR/USD"
    })

    print("✓ Seasonal forecast generated")

    await asyncio.sleep(1)

    print("\n" + "-"*80)
    print("SCENARIO 3: VOLUME-SEASONAL SYNCHRONIZATION")
    print("-"*80)

    print("\nAnalyzing volume-seasonal alignment...")
    print("When volume AND seasonality both point in the same direction,")
    print("the signal becomes much stronger and more reliable.")

    # Analyze volume-seasonal sync
    sync_analysis = await volume_sync.analyze_volume_seasonal_sync(
        symbol="EUR/USD",
        current_volume=normal_volume_eur * 2.2,
        volume_average=normal_volume_eur,
        seasonal_forecast="Strong quarter-end close expected (historical bias)",
        current_season="Q4 ending"
    )

    print("\n✓ Volume-Seasonal Sync Analysis Complete:")
    print(f"  Symbol: {sync_analysis.get('symbol')}")
    print(f"  Current Season: {sync_analysis.get('season')}")
    print(f"  Volume Multiple: {sync_analysis.get('volume_multiple', 0):.2f}x average")

    await asyncio.sleep(1)

    print("\n" + "-"*80)
    print("SCENARIO 4: IDENTIFYING SEASONAL VOLUME ANOMALIES")
    print("-"*80)

    print("\nDetecting unusual volume patterns for the season...")

    # Define what normal volumes look like by season
    historical_seasonal_volumes = {
        "spring": 1_000_000,      # Lower volume in spring
        "summer": 800_000,         # Summer doldrums
        "autumn": 1_200_000,       # Picking up in autumn
        "winter": 1_800_000,       # Higher volume in Q4
    }

    print("\nHistorical Seasonal Volume Averages:")
    for season, avg_vol in historical_seasonal_volumes.items():
        print(f"  {season.upper()}: {avg_vol/1_000_000:.2f}M")

    # Current volume in Q4 (winter season)
    current_vol = normal_volume_eur * 2.2  # 3.3M

    print(f"\nCurrent Volume (Q4): {current_vol/1_000_000:.2f}M")
    print(f"Seasonal Average for Q4: {historical_seasonal_volumes.get('winter', 0)/1_000_000:.2f}M")
    print(f"Ratio: {current_vol / historical_seasonal_volumes.get('winter', 1):.2f}x")

    anomaly_analysis = await volume_sync.identify_seasonal_volume_anomalies(
        symbol="EUR/USD",
        historical_seasonal_volumes=historical_seasonal_volumes,
        current_volume=current_vol,
        current_season="winter"
    )

    print("✓ Seasonal volume anomaly analysis complete")

    await asyncio.sleep(1)

    print("\n" + "-"*80)
    print("SCENARIO 5: TRADING RECOMMENDATIONS")
    print("-"*80)

    print("\nGenerating volume-seasonal trading recommendations...")

    recommendations = await volume_sync.recommend_seasonal_trades(
        symbol="EUR/USD",
        volume_condition="ELEVATED (2.2x seasonal average) - Strong conviction",
        seasonal_outlook="Quarter-end rebalancing + Strong seasonal close bias"
    )

    print("\n✓ Trading Recommendations Generated:")
    print("  Recommendation Type: Volume-Seasonal Confluence")
    print("  Signal Strength: STRONG (both factors aligned)")
    print("  Confidence: HIGH")

    await asyncio.sleep(1)

    print("\n" + "="*80)
    print("KEY INSIGHTS FROM VOLUME-SEASONALITY ANALYSIS")
    print("="*80)

    print("""
1. VOLUME AS CONVICTION INDICATOR
   ✓ Rising volume into seasonal event = strong acceptance
   ✓ Declining volume into seasonal event = weak/fake move
   ✓ Normal volume during seasonal event = noise/mean reversion

2. SEASONAL PATTERNS
   ✓ Quarter-end: Strong close into month-end and quarter-end
   ✓ Year-end: Santa Claus rally (Dec 25 - Jan 6), holiday liquidity drop
   ✓ Summer: "Sell in May and go away" - lower participation
   ✓ Tax season: December tax-loss harvesting, January rebound

3. VOLUME-SEASONAL CONFLUENCE
   ✓ High volume + favorable seasonal = STRONG TRADE
   ✓ High volume + unfavorable seasonal = CAUTION (potential reversal)
   ✓ Low volume + favorable seasonal = WEAK (not enough conviction)
   ✓ Low volume + unfavorable seasonal = AVOID

4. ACTIONABLE SIGNALS
   ✓ When volume AND seasonality both point same direction = HIGH conviction
   ✓ When they diverge = Warning sign, trade with caution
   ✓ Seasonal anomalies in volume = Unusual event/flow
   ✓ Volume spike at seasonal turning point = Strong reversal signal

5. TRADING APPLICATIONS
   ✓ Position sizing based on volume-seasonal alignment score
   ✓ Entry timing around seasonal inflection points
   ✓ Exit strategies when volume starts declining into seasonals
   ✓ Hedging during weak seasonal periods with low volume
   ✓ Aggressive positioning when both factors align
    """)

    print("\n" + "="*80)
    print("SYSTEM REPORT")
    print("="*80)

    system_report = await command_center.generate_system_report()

    print(f"\nVolume-Seasonality Group Status:")
    vol_season_info = system_report["groups"].get("volume_seasonality", {})
    print(f"  Agents: {vol_season_info.get('num_agents', 0)}")
    print(f"  Status: {vol_season_info.get('status', 'unknown')}")

    print(f"\nMessage Bus Activity:")
    bus_stats = system_report["message_bus_stats"]
    print(f"  Total Subscribers: {bus_stats['total_subscribers']}")
    print(f"  Queue Size: {bus_stats['queue_size']}")

    # Shutdown
    await command_center.shutdown()
    print("\n✓ System shutdown complete\n")


async def main():
    """Main entry point."""
    try:
        command_center = await setup_volume_seasonality_system()
        await simulate_volume_seasonality_scenario(command_center)
    except KeyboardInterrupt:
        print("\n\nScenario interrupted by user")
    except Exception as e:
        print(f"\nError during scenario: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
