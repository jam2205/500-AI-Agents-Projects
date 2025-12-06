"""Market Cycle Analysis Example

Demonstrates the top-down market structure framework:
1. Market Cycle Analysis (monthly, weekly, daily breakdown by quarters)
2. Volume & Seasonality Confirmation
3. Technical Indicator Alignment
4. Trading Framework & Position Sizing

This shows how accumulation/distribution cycles work across timeframes
and how to normalize market cycles for consistent trading signals.
"""

import asyncio
from datetime import datetime, timedelta
from src.framework.trading_command_center import TradingCommandCenter
from src.framework.group_coordinator import GroupCoordinator
from src.framework.base_agent import AgentRole
from src.agents import MarketCycleAgent
from src.config.agent_configs import MARKET_CYCLE_CONFIG


async def setup_market_cycle_system() -> TradingCommandCenter:
    """Set up the market cycle analysis system."""

    command_center = TradingCommandCenter()

    # ===== MARKET CYCLE ANALYSIS GROUP =====
    market_cycle_group = GroupCoordinator(
        group_name="market_cycles",
        coordinator_id="market_cycle_coordinator",
        coordinator_role=AgentRole.ALERT_COORDINATOR,
        message_bus=command_center.message_bus
    )

    market_cycle = MarketCycleAgent(
        MARKET_CYCLE_CONFIG,
        command_center.message_bus
    )

    await market_cycle_group.add_agent(market_cycle)
    await command_center.register_group(market_cycle_group)

    return command_center


def generate_daily_data(num_days: int = 20, trend: str = "up") -> list:
    """Generate sample daily OHLCV data."""
    data = []
    base_price = 4800.0

    for i in range(num_days):
        if trend == "up":
            price_offset = i * 10  # Steady uptrend
        elif trend == "accumulation":
            price_offset = 0 if i % 4 == 0 else (i % 4) * 3  # Choppy, building
        else:
            price_offset = -i * 8  # Downtrend

        close = base_price + price_offset
        open_price = close - 5
        high = close + 12
        low = close - 12

        volume = 1_000_000 if trend == "up" else 800_000 if trend == "accumulation" else 600_000

        data.append({
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "timestamp": (datetime.utcnow() - timedelta(days=num_days - i - 1)).isoformat()
        })

    return data


def generate_weekly_data(num_weeks: int = 8, phase: str = "markup") -> list:
    """Generate sample weekly OHLCV data."""
    data = []
    base_price = 4700.0

    for i in range(num_weeks):
        if phase == "markup":
            price_offset = i * 30  # Strong uptrend
            volume = 2_000_000 + i * 200_000  # Expanding volume
        elif phase == "distribution":
            price_offset = 100 if i < 4 else 100 - (i - 4) * 25  # Up then down
            volume = 2_500_000  # High but declining conviction
        else:  # accumulation
            price_offset = (i % 3) * 20  # Choppy
            volume = 1_500_000  # Building

        close = base_price + price_offset
        open_price = close - 15
        high = close + 40
        low = close - 40

        data.append({
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "timestamp": (datetime.utcnow() - timedelta(weeks=num_weeks - i - 1)).isoformat()
        })

    return data


async def analyze_scenario(
    command_center: TradingCommandCenter,
    scenario_name: str,
    daily_trend: str,
    weekly_phase: str
):
    """Run a market cycle analysis scenario."""

    print(f"\n{'-'*80}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'-'*80}")

    # Get market cycle agent
    cycle_group = await command_center.get_group("market_cycles")
    market_cycle = cycle_group.get_agent("market_cycle_01")

    # Generate data
    print(f"\nDaily Phase: {daily_trend}")
    print(f"Weekly Phase: {weekly_phase}")

    daily_data = generate_daily_data(20, daily_trend)
    weekly_data = generate_weekly_data(8, weekly_phase)

    print(f"\nDaily bars: {len(daily_data)} | Weekly bars: {len(weekly_data)}")
    print(f"Daily range: {daily_data[0]['close']:.2f} → {daily_data[-1]['close']:.2f}")
    print(f"Weekly range: {weekly_data[0]['close']:.2f} → {weekly_data[-1]['close']:.2f}")

    # Analyze
    print("\n✓ Analyzing market cycles with quarterly breakdown...")
    result = await market_cycle.execute_task({
        "type": "analyze_symbol",
        "symbol": "ES",
        "daily_data": daily_data,
        "weekly_data": weekly_data
    })

    if result.get("success"):
        print(f"\n✓ Analysis Complete:")
        print(f"  Daily Phase:  {result['daily_phase']}")
        print(f"  Weekly Phase: {result['weekly_phase']}")
        print(f"  Alignment:    {result['alignment_score']:.1f}%")
        print(f"\nTrading Framework:")
        framework = result['trading_framework']
        print(f"  Direction:    {framework['primary_direction']}")
        print(f"  Strength:     {framework['strength']}")
        print(f"  Risk Factors:")
        print(f"    - Pullback opportunity: {framework['pullback_opportunity']}")
        print(f"    - Reversal risk:       {framework['reversal_risk']}")

        print(f"\nManipulation Risk:")
        print(f"  Daily:  {result['manipulation_risk']['daily']}")
        print(f"  Weekly: {result['manipulation_risk']['weekly']}")
    else:
        print(f"✗ Error: {result.get('error')}")


async def simulate_market_cycle_framework(command_center: TradingCommandCenter):
    """Simulate the market cycle analysis framework."""

    print("\n" + "="*80)
    print("MARKET CYCLE ANALYSIS - TOP-DOWN FRAMEWORK")
    print("="*80)
    print("""
This system provides:
1. QUARTERLY BREAKDOWN: Each timeframe divided into 4 quarters for phase detection
2. CYCLE PHASES: Wyckoff methodology (Accumulation → Markup → Distribution → Markdown)
3. MULTI-TIMEFRAME ALIGNMENT: Normalized framework across daily, weekly, monthly
4. MANIPULATION DETECTION: Volume traps, false breakouts, price extremes
5. POSITION SIZING: Framework strength determines position size and risk
    """)

    await command_center.initialize()
    print("✓ System initialized\n")

    # Scenario 1: Perfect Alignment - Strong Uptrend
    await analyze_scenario(
        command_center,
        "PERFECT ALIGNMENT - Strong Uptrend",
        daily_trend="up",
        weekly_phase="markup"
    )

    print("\n📊 INTERPRETATION:")
    print("""
Both timeframes in MARKUP phase (highest conviction)
• Daily breakdown into 4 quarters: All showing higher highs/lows
• Weekly breakdown: Consistent expansion, volume increasing
• Alignment Score: 100% (perfect)
• Trading Framework: STRONG BUY, full position size
• Risk: Low - all timeframes aligned
• Strategy: Trend-following, buy dips (Q2 weakness), hold into Q3-Q4
    """)

    await asyncio.sleep(1)

    # Scenario 2: Partial Alignment - Distribution Phase
    await analyze_scenario(
        command_center,
        "PARTIAL ALIGNMENT - Distribution Phase",
        daily_trend="up",
        weekly_phase="distribution"
    )

    print("\n📊 INTERPRETATION:")
    print("""
Daily still in MARKUP but Weekly showing DISTRIBUTION (divergence warning!)
• Daily quarters: Q1-Q2 strong, Q3-Q4 weakening
• Weekly quarters: High volatility, volume declining into strength
• Alignment Score: 60% (partial - conflicting signals)
• Trading Framework: WEAK BUY, reduce position size to 50-75%
• Risk: ELEVATED - reversal possible
• Strategy: Tighten stops, look for reversal signals, stay defensive
• This is the most important phase change to detect - transition period
    """)

    await asyncio.sleep(1)

    # Scenario 3: Consolidation Building Base
    await analyze_scenario(
        command_center,
        "CONSOLIDATION - Accumulation Base Building",
        daily_trend="accumulation",
        weekly_phase="accumulation"
    )

    print("\n📊 INTERPRETATION:")
    print("""
Both timeframes in ACCUMULATION phase (base building)
• Daily quarters: Q1-Q2-Q3 choppy/sideways, Q4 breakout attempt
• Weekly quarters: Low volatility, price consolidating, volume steady
• Alignment Score: 100% (both in accumulation)
• Trading Framework: HOLD/ACCUMULATE, look for breakout opportunity
• Risk: Low while in consolidation, increases post-breakout
• Strategy: Don't force trades, wait for quarterly breakout confirmation
• Institutional accumulation period - prepare for next leg up
    """)

    await asyncio.sleep(1)

    print("\n" + "="*80)
    print("QUARTERLY FRAMEWORK - HOW IT WORKS")
    print("="*80)

    print("""
Each timeframe is divided into 4 equal quarters:

DAILY (20 bars) → 5 bars per quarter
├─ Q1: Initial price action and volume
├─ Q2: Continuation or reversal from Q1
├─ Q3: Trend development or consolidation
└─ Q4: Final confirmation before weekly close

WEEKLY (8 weeks) → 2 weeks per quarter
├─ Q1: Week 1-2: Early period, establishing trend
├─ Q2: Week 3-4: Mid-period confirmation or rejection
├─ Q3: Week 5-6: Late development, phase maturity
└─ Q4: Week 7-8: Final period, looking ahead to next phase

MONTHLY (available in full system)
├─ Q1: Weeks 1-2: Month setup
├─ Q2: Weeks 3-4: Month development
├─ Q3: Weeks 5-8: Month mid-point
└─ Q4: Weeks 9-13: Month conclusion

Benefits:
✓ Early detection of phase changes (see Q2-Q3 shifts)
✓ Identifies weakness within trend (expansion in Q2-Q3 fading by Q4)
✓ Normalizes different timeframe bars into comparable framework
✓ Manipulations become obvious (volume/price disagreement by quarter)
✓ Position sizing: stronger alignment = larger positions
    """)

    print("\n" + "="*80)
    print("CYCLE PHASES - TRADING IMPLICATIONS")
    print("="*80)

    print("""
ACCUMULATION (Institutional Buying, Low Volatility Base)
├─ Characteristics: Sideways/choppy, volume steady, low volatility
├─ Q1-Q2: Initial accumulation, buying interest evident
├─ Q3-Q4: Distribution phase weakness, but held above support
├─ Trading: Accumulate on dips, wait for breakout
├─ Risk: Low during base, increases at breakout
└─ Position: Build core position gradually

MARKUP (Strong Uptrend, Expanding Participation)
├─ Characteristics: Higher highs/lows, increasing volume, expanding range
├─ Q1-Q2: Initial thrust, new participants entering
├─ Q3-Q4: Momentum continues, possible parabolic phase
├─ Trading: Trend-following, buy weakness, protect long stops
├─ Risk: Low until weakness signals distribution coming
└─ Position: Full size, scale in on dips

DISTRIBUTION (Transition Phase, Profit-Taking)
├─ Characteristics: High volatility, sideways/declining, volume declining into strength
├─ Q1-Q2: Sellers active, resistance forms
├─ Q3-Q4: Breakout attempts fail, lower closes on volume
├─ Trading: Reduce longs, look for short opportunities
├─ Risk: HIGH - reversal coming, transition uncertain
└─ Position: Reduce to 25-50%, prepare for markdown

MARKDOWN (Downtrend, Declining Participation)
├─ Characteristics: Lower lows, increasing selling, declining volume
├─ Q1-Q2: Initial break of support, new shorts entering
├─ Q3-Q4: Momentum deteriorates, potential bounce-backs fail
├─ Trading: Short-biased, sell rallies, let losses run
├─ Risk: Low during trend, increases near support
└─ Position: Short full size, scale in on rallies
    """)

    print("\n" + "="*80)
    print("FRAMEWORK STRENGTH & POSITION SIZING")
    print("="*80)

    # Test framework assessment
    print("\nTesting framework strength scoring...")

    assessment = await command_center.get_group("market_cycles").get_agent("market_cycle_01").execute_task({
        "type": "assess_framework",
        "alignment_score": 100.0,
        "daily_confidence": 85.0,
        "weekly_confidence": 90.0
    })

    print(f"\n✓ Perfect Alignment Case:")
    print(f"  Framework Strength: {assessment['framework_strength']:.1f}%")
    print(f"  Quality:           {assessment['quality']}")
    print(f"  Position Sizing:   {assessment['position_sizing']}")
    print(f"  Risk Level:        {assessment['risk_level']}")

    assessment = await command_center.get_group("market_cycles").get_agent("market_cycle_01").execute_task({
        "type": "assess_framework",
        "alignment_score": 60.0,
        "daily_confidence": 75.0,
        "weekly_confidence": 70.0
    })

    print(f"\n✓ Partial Alignment Case:")
    print(f"  Framework Strength: {assessment['framework_strength']:.1f}%")
    print(f"  Quality:           {assessment['quality']}")
    print(f"  Position Sizing:   {assessment['position_sizing']}")
    print(f"  Risk Level:        {assessment['risk_level']}")

    # Shutdown
    await command_center.shutdown()
    print("\n✓ System shutdown complete\n")


async def main():
    """Main entry point."""
    try:
        command_center = await setup_market_cycle_system()
        await simulate_market_cycle_framework(command_center)
    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted by user")
    except Exception as e:
        print(f"\nError during analysis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
