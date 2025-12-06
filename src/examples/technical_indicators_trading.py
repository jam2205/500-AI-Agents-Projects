"""Technical Indicators Trading System Example

Demonstrates how the Technical Analysis Agent calculates and uses:
- VWAP (Volume Weighted Average Price)
- TWAP (Time Weighted Average Price)
- OBV (On-Balance Volume)
- ATR (Average True Range)
- ADR (Average Daily Range)

This system:
1. Monitors OHLCV data for major trading symbols
2. Calculates all technical indicators automatically
3. Generates combined signals from multiple indicators
4. Detects price-volume divergences (reversal signals)
5. Assesses volume quality and conviction
"""

import asyncio
from datetime import datetime, timedelta
from src.framework.trading_command_center import TradingCommandCenter
from src.framework.group_coordinator import GroupCoordinator
from src.framework.base_agent import AgentRole
from src.agents import TechnicalAnalysisAgent
from src.config.agent_configs import TECHNICAL_ANALYSIS_CONFIG


async def setup_technical_indicators_system() -> TradingCommandCenter:
    """Set up the technical indicators system."""

    command_center = TradingCommandCenter()

    # ===== VOLUME & SEASONALITY GROUP WITH TECHNICAL ANALYSIS =====
    volume_seasonal_group = GroupCoordinator(
        group_name="volume_seasonality",
        coordinator_id="volume_seasonal_coordinator",
        coordinator_role=AgentRole.ALERT_COORDINATOR,
        message_bus=command_center.message_bus
    )

    technical_analysis = TechnicalAnalysisAgent(
        TECHNICAL_ANALYSIS_CONFIG,
        command_center.message_bus
    )

    await volume_seasonal_group.add_agent(technical_analysis)
    await command_center.register_group(volume_seasonal_group)

    return command_center


def generate_sample_ohlcv_data(
    symbol: str,
    num_bars: int = 20,
    trend: str = "up"
) -> list:
    """Generate sample OHLCV data for demonstration."""

    data = []
    base_price = 4800.0 if symbol == "ES" else 1.0950 if symbol == "EUR/USD" else 2050.0

    for i in range(num_bars):
        # Add trend
        if trend == "up":
            price_change = i * 5.0
        elif trend == "down":
            price_change = -i * 5.0
        else:
            price_change = (i % 2) * 3.0

        close = base_price + price_change
        open_price = close - (2.0 if i % 2 == 0 else -2.0)
        high = max(close, open_price) + 5.0
        low = min(close, open_price) - 5.0

        # Volume increases with uptrend
        base_volume = 1_000_000
        if trend == "up":
            volume = base_volume * (1.0 + i * 0.05)
        else:
            volume = base_volume * (1.0 - i * 0.02) if i < 10 else base_volume

        timestamp = (datetime.utcnow() - timedelta(bars=num_bars - i - 1)).isoformat()

        data.append({
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "timestamp": timestamp
        })

    return data


async def simulate_technical_analysis_scenario(command_center: TradingCommandCenter):
    """Simulate technical analysis scenarios."""

    print("\n" + "="*80)
    print("TECHNICAL INDICATORS ANALYSIS SYSTEM")
    print("="*80)

    await command_center.initialize()
    print("\n✓ System initialized")

    # Get technical analysis agent
    volume_group = await command_center.get_group("volume_seasonality")
    tech_agent = volume_group.get_agent("technical_analysis_01")

    print("\n" + "-"*80)
    print("SCENARIO 1: STRONG UPTREND - ES (S&P 500 E-mini)")
    print("-"*80)

    print("\nGenerating 20 bars of OHLCV data with STRONG UPTREND...")
    es_data = generate_sample_ohlcv_data("ES", num_bars=20, trend="up")

    print(f"First bar: Close={es_data[0]['close']:.2f}, Volume={es_data[0]['volume']:,.0f}")
    print(f"Last bar:  Close={es_data[-1]['close']:.2f}, Volume={es_data[-1]['volume']:,.0f}")
    print(f"\nPrice moved UP {es_data[-1]['close'] - es_data[0]['close']:.2f} points")
    print(f"Volume increased {(es_data[-1]['volume'] / es_data[0]['volume']):.2f}x")

    print("\n✓ Calculating all technical indicators...")
    es_result = await tech_agent.execute_task({
        "type": "calculate_indicators",
        "symbol": "ES",
        "ohlcv_data": es_data
    })

    if es_result.get("success"):
        print("\n✓ ES Technical Analysis Complete:")
        print(f"  VWAP:  ${es_result['vwap']:.2f}")
        print(f"  TWAP:  ${es_result['twap']:.2f}")
        print(f"  OBV:   {es_result['obv']:,.0f}")
        print(f"  ATR:   ${es_result['atr']:.2f} ({es_result['volume_profile'].get('price_trend')} trend)")
        print(f"  ADR:   ${es_result['adr']:.2f}")
        print(f"\n  Signal:     {es_result['combined_signal']}")
        print(f"  Confidence: {es_result['confidence']:.1f}%")
        print(f"\n  Volume Assessment: {es_result['volume_profile']['vol_price_agreement']}")
    else:
        print(f"✗ Error: {es_result.get('error')}")

    await asyncio.sleep(1)

    print("\n" + "-"*80)
    print("SCENARIO 2: DOWNTREND WITH LOW VOLUME - EUR/USD")
    print("-"*80)

    print("\nGenerating 20 bars of OHLCV data with DOWNTREND...")
    eurusd_data = generate_sample_ohlcv_data("EUR/USD", num_bars=20, trend="down")

    print(f"First bar: Close={eurusd_data[0]['close']:.4f}, Volume={eurusd_data[0]['volume']:,.0f}")
    print(f"Last bar:  Close={eurusd_data[-1]['close']:.4f}, Volume={eurusd_data[-1]['volume']:,.0f}")
    print(f"\nPrice moved DOWN {eurusd_data[0]['close'] - eurusd_data[-1]['close']:.4f}")
    print(f"Volume decreased {(eurusd_data[-1]['volume'] / eurusd_data[0]['volume']):.2f}x")

    print("\n✓ Calculating all technical indicators...")
    eurusd_result = await tech_agent.execute_task({
        "type": "calculate_indicators",
        "symbol": "EUR/USD",
        "ohlcv_data": eurusd_data
    })

    if eurusd_result.get("success"):
        print("\n✓ EUR/USD Technical Analysis Complete:")
        print(f"  VWAP:  {eurusd_result['vwap']:.4f}")
        print(f"  TWAP:  {eurusd_result['twap']:.4f}")
        print(f"  OBV:   {eurusd_result['obv']:,.0f}")
        print(f"  ATR:   {eurusd_result['atr']:.4f}")
        print(f"  ADR:   {eurusd_result['adr']:.4f}")
        print(f"\n  Signal:     {eurusd_result['combined_signal']}")
        print(f"  Confidence: {eurusd_result['confidence']:.1f}%")
        print(f"\n  Alert: Downtrend with declining volume - weak conviction!")
    else:
        print(f"✗ Error: {eurusd_result.get('error')}")

    await asyncio.sleep(1)

    print("\n" + "-"*80)
    print("SCENARIO 3: SIDEWAYS MARKET - GOLD")
    print("-"*80)

    print("\nGenerating 20 bars of OHLCV data with SIDEWAYS movement...")
    gold_data = generate_sample_ohlcv_data("GC", num_bars=20, trend="sideways")

    print(f"First bar: Close={gold_data[0]['close']:.2f}, Volume={gold_data[0]['volume']:,.0f}")
    print(f"Last bar:  Close={gold_data[-1]['close']:.2f}, Volume={gold_data[-1]['volume']:,.0f}")
    print(f"\nPrice ranged sideways (small net change)")

    print("\n✓ Calculating all technical indicators...")
    gold_result = await tech_agent.execute_task({
        "type": "calculate_indicators",
        "symbol": "GC",
        "ohlcv_data": gold_data
    })

    if gold_result.get("success"):
        print("\n✓ Gold Technical Analysis Complete:")
        print(f"  VWAP:  ${gold_result['vwap']:.2f}")
        print(f"  TWAP:  ${gold_result['twap']:.2f}")
        print(f"  OBV:   {gold_result['obv']:,.0f}")
        print(f"  ATR:   ${gold_result['atr']:.2f}")
        print(f"  ADR:   ${gold_result['adr']:.2f}")
        print(f"\n  Signal:     {gold_result['combined_signal']}")
        print(f"  Confidence: {gold_result['confidence']:.1f}%")
        print(f"\n  Range Condition: {gold_result['volume_profile'].get('vol_price_agreement')}")
    else:
        print(f"✗ Error: {gold_result.get('error')}")

    await asyncio.sleep(1)

    print("\n" + "="*80)
    print("KEY TECHNICAL INDICATOR INTERPRETATIONS")
    print("="*80)

    print("""
1. VWAP (Volume Weighted Average Price)
   ✓ Use: Mean reversion levels, entry/exit points
   ✓ Bullish: Price > VWAP with increasing volume
   ✓ Bearish: Price < VWAP with decreasing volume

2. TWAP (Time Weighted Average Price)
   ✓ Use: Execution benchmarks, algorithmic order placement
   ✓ Trend confirmation: Compare current price to TWAP trend
   ✓ Useful: Identifying accumulation zones

3. OBV (On-Balance Volume)
   ✓ Use: Volume-based trend confirmation
   ✓ Bullish: OBV rising with price above MA
   ✓ Bearish: OBV falling with price below MA
   ✓ Divergence: Price high but OBV low = warning sign

4. ATR (Average True Range)
   ✓ Use: Volatility measurement, stop loss placement
   ✓ Expanding ATR: Volatility increasing (breakout likely)
   ✓ Contracting ATR: Consolidation phase (breakout imminent)
   ✓ Normal range: ±ATR from current price

5. ADR (Average Daily Range)
   ✓ Use: Range expectations, profit targets
   ✓ Wide range: Above 1.2x ADR (expansion)
   ✓ Narrow range: Below 0.8x ADR (consolidation)
   ✓ Stop placement: Typically 0.5x ADR from entry

SIGNAL INTERPRETATION:
  • STRONG_BUY: Multiple indicators aligned bullish (>70%)
  • BUY: Majority bullish signals (60-70%)
  • NEUTRAL: Mixed signals or no clear direction (40-60%)
  • SELL: Majority bearish signals (30-40%)
  • STRONG_SELL: Multiple indicators aligned bearish (<30%)

VOLUME QUALITY:
  • Excellent: OBV + Volume + Price all agree (70+)
  • Good: Most indicators agree (50-70)
  • Moderate: Mixed signals (30-50)
  • Weak: Poor agreement (<30)
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
        command_center = await setup_technical_indicators_system()
        await simulate_technical_analysis_scenario(command_center)
    except KeyboardInterrupt:
        print("\n\nScenario interrupted by user")
    except Exception as e:
        print(f"\nError during scenario: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
