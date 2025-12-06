"""Session Opening Analysis Example

Demonstrates session opening tracking and analysis aligned with market cycles:
1. Tracks five key session opens per day (Midnight, London, NYSE, PM, Close)
2. Analyzes price reaction at each opening (expansion vs lingering)
3. Detects session progression (escalating, declining, static)
4. Aligns session behavior with market cycle quarters
5. Generates trading signals from session patterns

This provides the framework for understanding how markets open and where
institutions are accumulating or distributing at session begins.
"""

import asyncio
from datetime import datetime, timedelta
from src.framework.trading_command_center import TradingCommandCenter
from src.framework.group_coordinator import GroupCoordinator
from src.framework.base_agent import AgentRole
from src.agents import SessionOpeningAgent
from src.config.agent_configs import SESSION_OPENING_CONFIG


async def setup_session_opens_system() -> TradingCommandCenter:
    """Set up the session opening analysis system."""

    command_center = TradingCommandCenter()

    # ===== SESSION OPENS ANALYSIS GROUP =====
    session_opens_group = GroupCoordinator(
        group_name="session_opens",
        coordinator_id="session_opens_coordinator",
        coordinator_role=AgentRole.MARKET_INTELLIGENCE,
        message_bus=command_center.message_bus
    )

    session_opens = SessionOpeningAgent(
        SESSION_OPENING_CONFIG,
        command_center.message_bus
    )

    await session_opens_group.add_agent(session_opens)
    await command_center.register_group(session_opens_group)

    return command_center


def generate_session_data(
    base_price: float = 4800.0,
    scenario: str = "bullish"
) -> dict:
    """Generate realistic session opening data."""

    if scenario == "bullish":
        # Escalating opens = institutional buying
        opens = {
            "midnight_open": {"open": base_price, "price": base_price, "volume": 100_000},
            "london_open": {"open": base_price + 5, "price": base_price + 5, "volume": 500_000},
            "nyse_open": {"open": base_price + 10, "price": base_price + 12, "volume": 2_000_000},
            "us_pm_session": {"open": base_price + 15, "price": base_price + 18, "volume": 1_500_000},
            "london_close": {"open": base_price + 20, "price": base_price + 22, "volume": 800_000},
        }
        current_price = base_price + 22

    elif scenario == "bearish":
        # Declining opens = institutional distribution
        opens = {
            "midnight_open": {"open": base_price, "price": base_price, "volume": 150_000},
            "london_open": {"open": base_price - 3, "price": base_price - 5, "volume": 600_000},
            "nyse_open": {"open": base_price - 8, "price": base_price - 10, "volume": 2_200_000},
            "us_pm_session": {"open": base_price - 15, "price": base_price - 18, "volume": 1_800_000},
            "london_close": {"open": base_price - 20, "price": base_price - 22, "volume": 1_000_000},
        }
        current_price = base_price - 22

    else:  # neutral
        # Static opens = consolidation
        opens = {
            "midnight_open": {"open": base_price, "price": base_price, "volume": 120_000},
            "london_open": {"open": base_price + 1, "price": base_price - 1, "volume": 550_000},
            "nyse_open": {"open": base_price + 2, "price": base_price + 3, "volume": 1_800_000},
            "us_pm_session": {"open": base_price - 1, "price": base_price, "volume": 1_200_000},
            "london_close": {"open": base_price + 1, "price": base_price + 1, "volume": 900_000},
        }
        current_price = base_price + 1

    # Add timestamps
    now = datetime.utcnow()
    for i, (session_name, data) in enumerate(opens.items()):
        data["session"] = session_name
        data["timestamp"] = (now - timedelta(hours=len(opens) - i - 1)).isoformat()

    return {
        "opens": opens,
        "current_price": current_price,
        "scenario": scenario
    }


async def analyze_scenario(
    command_center: TradingCommandCenter,
    scenario_name: str,
    scenario_type: str,
    base_price: float
):
    """Run a session opening analysis scenario."""

    print(f"\n{'-'*80}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'-'*80}")

    # Get session opening agent
    opens_group = await command_center.get_group("session_opens")
    session_agent = opens_group.get_agent("session_opening_01")

    # Generate data
    session_data = generate_session_data(base_price, scenario_type)
    opens = session_data["opens"]
    current_price = session_data["current_price"]

    print(f"\nSession Progression:")
    for session_name in ["midnight_open", "london_open", "nyse_open", "us_pm_session", "london_close"]:
        data = opens[session_name]
        change = data["price"] - base_price
        pct = (change / base_price) * 100
        print(f"  {session_name:20} → Open: {data['open']:8.2f}  Current: {data['price']:8.2f}  ({pct:+.2f}%)")

    print(f"\nCurrent Price: {current_price:.2f}")

    # Analyze
    print("\n✓ Analyzing session opening behavior...")
    result = await session_agent.execute_task({
        "type": "track_opens",
        "symbol": "ES",
        "session_data": opens,
        "current_price": current_price,
        "timeframe": "daily"
    })

    if result.get("success"):
        print(f"\n✓ Analysis Complete:")
        print(f"  Session Character: {result['session_character']}")
        print(f"  Strongest Open:    {result['strongest_open']}")

        seq = result.get("sequence_analysis", {})
        print(f"\nSequence Analysis:")
        print(f"  Progression:       {seq.get('progression', 'unknown')}")
        print(f"  Net Change:        {seq.get('net_change_pct', 0):+.2f}%")
        print(f"  High Open:         {seq.get('high_open', 0):.2f}")
        print(f"  Low Open:          {seq.get('low_open', 0):.2f}")
        print(f"  Open Range:        {seq.get('open_range', 0):.2f}")

        print(f"\nPrice vs Session Opens:")
        for session, relation in result.get("price_vs_opens", {}).items():
            print(f"  {session:20} {relation}")

        print(f"\nKey Insights:")
        for insight in result.get("insights", []):
            print(f"  {insight}")

        # Test signals
        signal_result = await session_agent.execute_task({
            "type": "detect_signals",
            "symbol": "ES",
            "sessions": list(opens.values()),
            "current_price": current_price
        })

        if signal_result.get("signals"):
            print(f"\nTrading Signals:")
            print(f"  Overall Bias: {signal_result.get('overall_bias')}")
            print(f"  Signal Count: {signal_result.get('signal_count')}")
            print(f"  Confidence:   {signal_result.get('average_confidence', 0):.1f}%")

            for signal in signal_result.get("signals", []):
                print(f"    • {signal['type']:25} {signal['direction']:8} (str: {signal['strength']:.0f}%)")
                print(f"      {signal['description']}")
    else:
        print(f"✗ Error: {result.get('error')}")


async def simulate_session_opens_framework(command_center: TradingCommandCenter):
    """Simulate the session opens framework."""

    print("\n" + "="*80)
    print("SESSION OPENING ANALYSIS - DAILY FRAMEWORK")
    print("="*80)
    print("""
This system tracks and analyzes five key market session opens:

1. MIDNIGHT OPEN (00:00 ET)
   • Algorithmic and international overnight activity
   • Sets tone for entire day
   • Lower volume, wider spreads

2. LONDON OPEN (08:00 ET)
   • European institutional participation
   • Confirms or rejects overnight direction
   • Increasing volume and volatility

3. NYSE OPEN (09:30 ET)
   • Most important session
   • Full US institutional participation
   • Peak volatility and volume
   • Sets daily character

4. US PM SESSION (13:30 ET)
   • Afternoon European closes + afternoon US activity
   • Confirms morning direction or reverses
   • Critical for end-of-day positioning

5. LONDON CLOSE (16:00 ET)
   • European close, final US establishment
   • Volume declining as Europe closes
   • Sets tone for overnight trading

Framework Analysis:
✓ Escalating Opens:     Institutions buying (bullish)
✓ Declining Opens:      Institutions distributing (bearish)
✓ Static Opens:         Consolidation/Accumulation
✓ Price Above All:      Strong uptrend bias
✓ Price Below All:      Strong downtrend bias
✓ Mixed:                Uncertain, watch for breakout
    """)

    await command_center.initialize()
    print("✓ System initialized\n")

    # Scenario 1: Bullish Escalating Opens
    await analyze_scenario(
        command_center,
        "BULLISH ESCALATING OPENS",
        "bullish",
        4800.0
    )

    print("\n📊 INTERPRETATION:")
    print("""
Opens rising from midnight through close (4800 → 4820):
• Midnight: Algorithmic confirmation
• London: European buyers stepping in
• NYSE: Institutional money entering
• PM: Continuation of buying pressure
• Close: Buyers control session

Signal: STRONG INSTITUTIONAL BUYING
• Price above all opens → Accumulation phase
• Escalating opens → Momentum building
• High volume NYSE → Conviction confirmed
• Forecast: Gap up at next session likely
    """)

    await asyncio.sleep(1)

    # Scenario 2: Bearish Declining Opens
    await analyze_scenario(
        command_center,
        "BEARISH DECLINING OPENS",
        "bearish",
        4800.0
    )

    print("\n📊 INTERPRETATION:")
    print("""
Opens declining from midnight through close (4800 → 4778):
• Midnight: Overnight support breaks
• London: Weakness continues, sellers dominant
• NYSE: No bounce at open, distribution begins
• PM: Afternoon selling pressure
• Close: Sellers maintain control

Signal: INSTITUTIONAL DISTRIBUTION
• Price below all opens → Capitulation phase
• Declining opens → Momentum deteriorating
• Volume persists → Conviction of selling
• Forecast: Next session opens lower (breakdown continues)
    """)

    await asyncio.sleep(1)

    # Scenario 3: Neutral/Consolidation
    await analyze_scenario(
        command_center,
        "NEUTRAL - CONSOLIDATION",
        "neutral",
        4800.0
    )

    print("\n📊 INTERPRETATION:")
    print("""
Opens mostly flat with slight variation (4800 → 4801):
• Midnight: Direction unclear
• London: Small bounce then rejection
• NYSE: Support holding, no conviction
• PM: Oscillation near morning open
• Close: Day closes near where it opened

Signal: ACCUMULATION/CONSOLIDATION BASE
• Static opens → No institutional directionality yet
• Mixed price vs opens → Both buyers and sellers
• Lower volume → Waiting for catalyst
• Forecast: Breakout expected when opens start escalating/declining
    """)

    await asyncio.sleep(1)

    print("\n" + "="*80)
    print("SESSION OPENS ALIGNED WITH MARKET CYCLE QUARTERS")
    print("="*80)

    print("""
Daily Quarter Alignment:

Q1 (First ~5 sessions):
├─ Midnight, London, Early NYSE
├─ Sets daily tone
└─ Watch: Do early opens establish direction?

Q2 (Mid-day ~5 sessions):
├─ Mid-NYSE through Afternoon
├─ Confirms or rejects Q1 direction
└─ Critical: Price breaking new opens or rejecting?

Q3 (Late ~5 sessions):
├─ Afternoon through PM Session
├─ Trend continuation or divergence?
└─ Watch: Volume participation maintaining?

Q4 (Final Close):
├─ London Close and final pricing
├─ Establishes overnight direction
└─ Critical: Where does close break?


ALIGNMENT SCORING:

Accumulation Phase:
✓ Static opens through quarters
✓ Choppy price action, not breaking opens far
✓ Volume building gradually
→ Expected: Escalation to break out of range

Markup Phase:
✓ Escalating opens Q1 → Q2 → Q3 → Q4
✓ Price consistently above newest opens
✓ Volume expanding with each session
→ Expected: Momentum continues

Distribution Phase:
✓ Escalating opens then rolling over Q2-Q3
✓ Price showing inability to hold new highs
✓ Volume declining into resistance
→ Expected: Reversal coming, prepare for decline

Markdown Phase:
✓ Declining opens Q1 → Q2 → Q3 → Q4
✓ Price breaking below session opens
✓ Participation declining
→ Expected: Downtrend continues
    """)

    # Shutdown
    await command_center.shutdown()
    print("\n✓ System shutdown complete\n")


async def main():
    """Main entry point."""
    try:
        command_center = await setup_session_opens_system()
        await simulate_session_opens_framework(command_center)
    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted by user")
    except Exception as e:
        print(f"\nError during analysis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
