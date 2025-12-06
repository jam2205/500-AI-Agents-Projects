"""
Example: Integration of Analytics Service with Trading Agents

This example demonstrates how trading agents can:
1. Discover the analytics service using the service registry
2. Call analytics endpoints for volatility, correlation, patterns, and anomalies
3. Use the results to enhance trading signals
"""

import asyncio
import sys
import os
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from framework.service_registry import get_healthy_services, get_service_by_name
from framework.base_agent import BaseAgent, Message
import httpx


class AnalyticsIntegrationAgent(BaseAgent):
    """
    Example agent that uses the analytics service to enhance trading decisions.

    This agent demonstrates:
    - Service discovery using the service registry
    - Making HTTP requests to remote analytics endpoints
    - Processing analytics results into trading signals
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.analytics_url = None
        self.http_client = None

    async def initialize(self):
        """Initialize by discovering the analytics service."""
        await super().initialize()

        # Discover analytics service using service registry
        analytics_service = get_service_by_name("Analytics Service")

        if analytics_service:
            self.logger.info(f"Found analytics service: {analytics_service.service_id}")
            self.analytics_url = f"http://analytics-api:8002"  # Internal service URL
            self.logger.info(f"Analytics service URL: {self.analytics_url}")
        else:
            self.logger.warning("Analytics service not found in registry")
            # Fallback to direct URL
            self.analytics_url = "http://analytics-api:8002"

        # Create HTTP client
        self.http_client = httpx.AsyncClient()

    async def shutdown(self):
        """Cleanup on shutdown."""
        if self.http_client:
            await self.http_client.aclose()
        await super().shutdown()

    async def analyze_with_analytics(
        self,
        symbol: str,
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float]
    ) -> Dict[str, Any]:
        """
        Call the analytics service for comprehensive analysis.

        Args:
            symbol: Trading symbol
            opens, highs, lows, closes, volumes: OHLCV data

        Returns:
            Dictionary with analytics results
        """
        if not self.analytics_url:
            self.logger.error("Analytics service not available")
            return {}

        try:
            payload = {
                "symbol": symbol,
                "highs": highs,
                "lows": lows,
                "opens": opens,
                "closes": closes,
                "volumes": volumes
            }

            response = await self.http_client.post(
                f"{self.analytics_url}/composite/analyze",
                json=payload,
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Analytics error: {response.status_code}")
                return {}

        except Exception as e:
            self.logger.error(f"Error calling analytics service: {e}")
            return {}

    async def analyze_volatility(
        self,
        symbol: str,
        returns: List[float],
        method: str = "realized"
    ) -> Dict[str, Any]:
        """
        Call volatility analysis endpoint.

        Args:
            symbol: Trading symbol
            returns: List of returns
            method: Volatility method (realized, parkinson, garman_klass, etc.)

        Returns:
            Volatility analysis results
        """
        try:
            payload = {
                "symbol": symbol,
                "returns": returns,
                "method": method
            }

            response = await self.http_client.post(
                f"{self.analytics_url}/volatility/analyze",
                json=payload,
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Volatility analysis error: {response.status_code}")
                return {}

        except Exception as e:
            self.logger.error(f"Error analyzing volatility: {e}")
            return {}

    async def analyze_patterns(
        self,
        symbol: str,
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> Dict[str, Any]:
        """
        Call pattern analysis endpoint.

        Args:
            symbol: Trading symbol
            highs, lows, closes: OHLC data

        Returns:
            Pattern analysis results
        """
        try:
            payload = {
                "symbol": symbol,
                "highs": highs,
                "lows": lows,
                "closes": closes
            }

            response = await self.http_client.post(
                f"{self.analytics_url}/patterns/analyze",
                json=payload,
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Pattern analysis error: {response.status_code}")
                return {}

        except Exception as e:
            self.logger.error(f"Error analyzing patterns: {e}")
            return {}

    async def detect_anomalies(
        self,
        symbol: str,
        opens: List[float],
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volumes: List[float]
    ) -> Dict[str, Any]:
        """
        Call anomaly detection endpoint.

        Args:
            symbol: Trading symbol
            opens, highs, lows, closes, volumes: OHLCV data

        Returns:
            Anomaly detection results
        """
        try:
            payload = {
                "symbol": symbol,
                "opens": opens,
                "highs": highs,
                "lows": lows,
                "closes": closes,
                "volumes": volumes
            }

            response = await self.http_client.post(
                f"{self.analytics_url}/anomalies/detect",
                json=payload,
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Anomaly detection error: {response.status_code}")
                return {}

        except Exception as e:
            self.logger.error(f"Error detecting anomalies: {e}")
            return {}

    async def process_message(self, message: Message):
        """
        Process incoming messages with analytics.

        Example: A market data update arrives, and we enrich it with analytics.
        """
        if message.type == "market_data":
            symbol = message.content.get("symbol")
            data = message.content.get("data", {})

            # Extract OHLCV
            opens = data.get("opens", [])
            highs = data.get("highs", [])
            lows = data.get("lows", [])
            closes = data.get("closes", [])
            volumes = data.get("volumes", [])

            if not all([opens, highs, lows, closes, volumes]):
                self.logger.warning("Incomplete market data")
                return

            # Run comprehensive analytics
            analytics_results = await self.analyze_with_analytics(
                symbol, opens, highs, lows, closes, volumes
            )

            if analytics_results:
                # Create enhanced message with analytics
                enhanced_message = Message(
                    sender=self.agent_id,
                    type="analytics_result",
                    content={
                        "symbol": symbol,
                        "timestamp": analytics_results.get("timestamp"),
                        "volatility": analytics_results.get("volatility"),
                        "patterns": analytics_results.get("patterns"),
                        "anomalies": analytics_results.get("anomalies"),
                        "overall_signal_count": analytics_results.get("overall_signal_count")
                    },
                    priority=message.priority + 1  # Slightly higher priority
                )

                # Broadcast to other agents
                await self.broadcast_message(enhanced_message)

                self.logger.info(
                    f"Enhanced {symbol} with analytics: "
                    f"{analytics_results.get('overall_signal_count')} signals found"
                )


# ============================================================================
# Example Usage
# ============================================================================

async def example_discover_analytics_service():
    """Example: Discover analytics service from registry."""
    print("\n=== Example 1: Service Discovery ===")

    # Get all healthy analytics services
    analytics_services = get_healthy_services("analytics")

    if analytics_services:
        print(f"Found {len(analytics_services)} healthy analytics service(s):")
        for service in analytics_services:
            print(f"  - {service.service_name} ({service.service_id})")
            print(f"    Capabilities: {service.capabilities}")
            print(f"    Endpoints: {len(service.endpoints)}")
    else:
        print("No analytics services found")


async def example_check_service_capabilities():
    """Example: Check service capabilities."""
    print("\n=== Example 2: Service Capabilities ===")

    analytics_service = get_service_by_name("Analytics Service")

    if analytics_service:
        print(f"Analytics Service Capabilities:")
        for capability in analytics_service.capabilities:
            print(f"  - {capability}")

        print(f"\nAvailable Endpoints:")
        for endpoint in analytics_service.endpoints:
            print(f"  - {endpoint.method} {endpoint.path}")
            print(f"    Description: {endpoint.description}")
            print(f"    Capabilities: {endpoint.capabilities}")
    else:
        print("Analytics service not found")


async def example_agent_with_analytics():
    """Example: Agent using analytics service."""
    print("\n=== Example 3: Agent Using Analytics ===")

    # Create sample agent
    config = {
        "agent_id": "demo-analytics-agent",
        "agent_name": "Demo Analytics Agent",
        "role": "analytics"
    }

    agent = AnalyticsIntegrationAgent(config)
    await agent.initialize()

    # Sample market data
    symbol = "EURUSD"
    closes = [1.0850, 1.0851, 1.0853, 1.0852, 1.0854] * 10  # 50 bars
    highs = [c + 0.0005 for c in closes]
    lows = [c - 0.0005 for c in closes]
    opens = [c - 0.0002 for c in closes]
    volumes = [1000000] * len(closes)

    # Calculate returns
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]

    # Analyze volatility
    print(f"\nAnalyzing volatility for {symbol}...")
    vol_result = await agent.analyze_volatility(symbol, returns)
    if vol_result:
        print(f"  Volatility: {vol_result.get('volatility', 'N/A'):.6f}")
        print(f"  Trend: {vol_result.get('trend', 'N/A')}")
        print(f"  Signals: {vol_result.get('signals', [])}")

    # Analyze patterns
    print(f"\nAnalyzing patterns for {symbol}...")
    pattern_result = await agent.analyze_patterns(symbol, highs, lows, closes)
    if pattern_result:
        print(f"  Support levels: {pattern_result.get('support_levels', [])}")
        print(f"  Signals: {pattern_result.get('signals', [])}")

    # Detect anomalies
    print(f"\nDetecting anomalies for {symbol}...")
    anomaly_result = await agent.detect_anomalies(symbol, opens, highs, lows, closes, volumes)
    if anomaly_result:
        print(f"  Anomaly score: {anomaly_result.get('anomaly_score', 'N/A'):.2f}")
        print(f"  Signals: {anomaly_result.get('signals', [])}")

    # Run comprehensive analysis
    print(f"\nRunning comprehensive analysis for {symbol}...")
    composite_result = await agent.analyze_with_analytics(
        symbol, opens, highs, lows, closes, volumes
    )
    if composite_result:
        print(f"  Total signals: {composite_result.get('overall_signal_count', 0)}")
        print(f"  Volatility signals: {len(composite_result.get('volatility', {}).get('signals', []))}")
        print(f"  Pattern signals: {len(composite_result.get('patterns', {}).get('signals', []))}")
        print(f"  Anomaly signals: {len(composite_result.get('anomalies', {}).get('signals', []))}")

    await agent.shutdown()


async def main():
    """Run all examples."""
    print("=" * 70)
    print("Analytics Service Integration Examples")
    print("=" * 70)

    await example_discover_analytics_service()
    await example_check_service_capabilities()
    await example_agent_with_analytics()

    print("\n" + "=" * 70)
    print("Examples complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
