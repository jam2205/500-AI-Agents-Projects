# Analytics Service Integration Guide

## Overview

The Analytics Service provides advanced market analytics capabilities (volatility, correlation, patterns, anomalies) to the multi-agent trading system. Agents discover and call these services dynamically using the **Service Registry**.

## Architecture

```
Trading Agents (30 across 10 groups)
    ↓
Service Registry (Central Discovery)
    ↓
Analytics Service (Port 8002)
├── Volatility Analysis
├── Correlation Analysis
├── Pattern Recognition
└── Anomaly Detection
```

## Service Registry

The Service Registry enables dynamic service discovery without hardcoded URLs.

### Registering a Service

Services register themselves on startup:

```python
from framework.service_registry import register_service, ServiceInfo, ServiceEndpoint

service_info = ServiceInfo(
    service_id="analytics-api-001",
    service_name="Analytics Service",
    service_type="analytics",
    endpoints=[
        ServiceEndpoint(
            path="/volatility/analyze",
            method="POST",
            description="Analyze volatility",
            capabilities=["volatility_analysis"]
        ),
        # ... more endpoints
    ],
    capabilities=["volatility_analysis", "correlation_analysis", ...],
    dependencies=[]
)

register_service(service_info)
```

### Discovering Services

Agents can discover services using:

```python
from framework.service_registry import (
    get_service_by_name,
    get_services_by_type,
    get_healthy_services,
    get_services_with_capability
)

# Get analytics service
analytics = get_service_by_name("Analytics Service")

# Get all healthy analytics services
services = get_healthy_services("analytics")

# Get services with volatility capability
vol_services = get_services_with_capability("volatility_analysis")

# Get all services by type
all_analytics = get_services_by_type("analytics")
```

## Integrating with Existing Agents

### Pattern 1: Quick Integration in Message Processor

Add analytics call to an existing agent:

```python
class MarketDataAgent(BaseAgent):
    async def process_message(self, message: Message):
        if message.type == "market_data":
            symbol = message.content.get("symbol")
            prices = message.content.get("prices")

            # Call analytics service
            analytics_url = "http://analytics-api:8002"
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{analytics_url}/patterns/analyze",
                    json={
                        "symbol": symbol,
                        "highs": prices["highs"],
                        "lows": prices["lows"],
                        "closes": prices["closes"]
                    }
                )

                patterns = response.json()

                # Enhance message with patterns
                enhanced = Message(
                    sender=self.agent_id,
                    type="market_data_with_patterns",
                    content={**message.content, "patterns": patterns}
                )

                await self.broadcast_message(enhanced)
```

### Pattern 2: Dedicated Analytics Agent

Create a specialized agent that enriches market data:

```python
from examples.analytics_integration import AnalyticsIntegrationAgent

# In your agent setup
analytics_agent = AnalyticsIntegrationAgent({
    "agent_id": "analytics-enricher",
    "agent_name": "Analytics Enricher",
    "role": "analytics"
})

await analytics_agent.initialize()

# It automatically enriches incoming market_data messages
# and broadcasts analytics_result messages
```

### Pattern 3: Multi-Service Querying

Query multiple analytics simultaneously:

```python
async def comprehensive_analysis(symbol, ohlcv_data):
    analytics_url = "http://analytics-api:8002"

    async with httpx.AsyncClient() as client:
        # Query all endpoints in parallel
        tasks = [
            client.post(
                f"{analytics_url}/volatility/analyze",
                json={
                    "symbol": symbol,
                    "returns": calculate_returns(ohlcv_data["closes"])
                }
            ),
            client.post(
                f"{analytics_url}/patterns/analyze",
                json={
                    "symbol": symbol,
                    "highs": ohlcv_data["highs"],
                    "lows": ohlcv_data["lows"],
                    "closes": ohlcv_data["closes"]
                }
            ),
            client.post(
                f"{analytics_url}/anomalies/detect",
                json={
                    "symbol": symbol,
                    "opens": ohlcv_data["opens"],
                    "highs": ohlcv_data["highs"],
                    "lows": ohlcv_data["lows"],
                    "closes": ohlcv_data["closes"],
                    "volumes": ohlcv_data["volumes"]
                }
            )
        ]

        vol_resp, pattern_resp, anomaly_resp = await asyncio.gather(*tasks)

        return {
            "volatility": vol_resp.json(),
            "patterns": pattern_resp.json(),
            "anomalies": anomaly_resp.json()
        }
```

## Analytics Endpoints

### Volatility Analysis

**Endpoint:** `POST /volatility/analyze`

**Request:**
```json
{
    "symbol": "EURUSD",
    "returns": [0.0001, -0.0002, 0.0003, ...],
    "method": "realized"
}
```

**Methods:**
- `realized` - Historical standard deviation
- `parkinson` - High-low based (more efficient)
- `garman_klass` - OHLC based
- `rogers_satchell` - Drift-independent
- `garch` - GARCH(1,1) modeling with forecast

**Response:**
```json
{
    "symbol": "EURUSD",
    "volatility": 0.0045,
    "percentile": 65,
    "trend": "increasing",
    "signals": ["HIGH_VOLATILITY_REGIME", "BREAKOUT_POTENTIAL"],
    "confidence": 85
}
```

### Correlation Analysis

**Endpoint:** `POST /correlation/analyze`

**Request:**
```json
{
    "symbol1": "EURUSD",
    "symbol2": "ES",
    "prices1": [1.0850, 1.0851, ...],
    "prices2": [4500, 4505, ...],
    "method": "pearson"
}
```

**Response:**
```json
{
    "symbol_pair": "EURUSD vs ES",
    "correlation": 0.65,
    "regime": "moderate_positive",
    "lead_lag": "EURUSD leads ES",
    "lag_periods": 3,
    "signals": ["CORRELATION_REGIME_CHANGE"],
    "confidence": 72
}
```

### Pattern Recognition

**Endpoint:** `POST /patterns/analyze`

**Request:**
```json
{
    "symbol": "EURUSD",
    "highs": [1.0855, 1.0856, ...],
    "lows": [1.0845, 1.0844, ...],
    "closes": [1.0850, 1.0851, ...]
}
```

**Response:**
```json
{
    "symbol": "EURUSD",
    "support_levels": [
        {
            "price": 1.0840,
            "strength": 0.85,
            "touches": 3,
            "confidence": 0.92
        }
    ],
    "resistance_levels": [...],
    "chart_patterns": [
        {
            "name": "ascending_triangle",
            "type": "bullish",
            "target_pct": 2.5,
            "confidence": 0.68
        }
    ],
    "pivot_points": {
        "S2": 1.0820,
        "S1": 1.0835,
        "P": 1.0850,
        "R1": 1.0865,
        "R2": 1.0880
    },
    "signals": ["STRONG_SUPPORT_NEARBY", "BULLISH_ASCENDING_TRIANGLE"],
    "confidence": 78
}
```

### Anomaly Detection

**Endpoint:** `POST /anomalies/detect`

**Request:**
```json
{
    "symbol": "EURUSD",
    "opens": [1.0848, 1.0850, ...],
    "highs": [1.0855, 1.0856, ...],
    "lows": [1.0845, 1.0844, ...],
    "closes": [1.0850, 1.0851, ...],
    "volumes": [1000000, 1100000, ...]
}
```

**Response:**
```json
{
    "symbol": "EURUSD",
    "anomaly_score": 0.45,
    "price_anomalies": 1,
    "volume_anomalies": 1,
    "volatility_anomalies": 0,
    "behavioral_flags": 2,
    "signals": ["VOLUME_ANOMALY_DETECTED", "BREAKAWAY_MOVE"],
    "confidence": 68
}
```

### Composite Analysis

**Endpoint:** `POST /composite/analyze`

Runs all analytics tools at once:

```json
{
    "symbol": "EURUSD",
    "opens": [...],
    "highs": [...],
    "lows": [...],
    "closes": [...],
    "volumes": [...]
}
```

**Response:**
```json
{
    "symbol": "EURUSD",
    "volatility": {
        "current": 0.0045,
        "percentile": 65,
        "trend": "increasing",
        "signals": ["HIGH_VOLATILITY_REGIME"],
        "confidence": 85
    },
    "patterns": {
        "support_levels": 1,
        "resistance_levels": 2,
        "chart_patterns": 1,
        "signals": ["STRONG_SUPPORT_NEARBY"],
        "confidence": 78
    },
    "anomalies": {
        "anomaly_score": 0.45,
        "total_anomalies": 3,
        "signals": ["VOLUME_ANOMALY_DETECTED"],
        "confidence": 68
    },
    "overall_signal_count": 5
}
```

## Integration Examples

See `examples/analytics_integration.py` for:

1. **Service Discovery** - Finding analytics service in registry
2. **Capability Checking** - Verifying available endpoints
3. **Agent Integration** - Using analytics in agent workflow
4. **Parallel Queries** - Calling multiple endpoints simultaneously

## Deployment

### Local Development

```bash
docker-compose up analytics-api
```

Accessible at `http://localhost:8002`

### Kubernetes

```bash
kubectl apply -f k8s/analytics-deployment.yaml
```

### Health Checks

Each service exposes `/health` endpoint:

```bash
curl http://analytics-api:8002/health
# {"status": "healthy", "timestamp": "...", "service": "analytics-api"}
```

## Signal Interpretation

### Volatility Signals
- `HIGH_VOLATILITY_REGIME` - Consider reducing position size
- `BREAKOUT_POTENTIAL` - Price may accelerate
- `STABLE_VOLATILITY` - Consolidation phase

### Correlation Signals
- `CORRELATION_REGIME_CHANGE` - Diversification changes
- `DIVERGENCE_LIKELY` - Assets moving apart
- `CORRELATION_FORMING` - Assets becoming related

### Pattern Signals
- `STRONG_SUPPORT_NEARBY` - Support level within 2%
- `STRONG_RESISTANCE_NEARBY` - Resistance level within 2%
- `BULLISH_*_PATTERN` - Bullish pattern detected
- `BEARISH_*_PATTERN` - Bearish pattern detected

### Anomaly Signals
- `PRICE_ANOMALY_DETECTED` - Unusual price movement (Z-score > 2)
- `VOLUME_ANOMALY_DETECTED` - Volume spike > 1.5x normal
- `VOLATILITY_ANOMALY_DETECTED` - Vol change > 1.5x normal
- `REVERSAL_CANDLE_DETECTED` - Large candle opposite to trend
- `PRICE_GAP_DETECTED` - Gap > 1% from previous close
- `BREAKAWAY_MOVE` - High volume with price away from range
- `REJECTION_DETECTED` - Large wicks (rejection of extremes)

## Performance Considerations

### Scaling
- Analytics service auto-scales 1-4 replicas based on CPU/memory
- Stateless design allows horizontal scaling
- Each request is independent

### Latency
- Typical response time: 50-200ms per endpoint
- Composite endpoint: 200-500ms (parallel queries)
- Health check: < 10ms

### Data Requirements
- Minimum 50 bars for reliable analysis
- 250+ bars recommended for patterns and anomalies
- Longer lookback = higher confidence

## Troubleshooting

### Service Not Found

```python
service = get_service_by_name("Analytics Service")
if not service:
    # Fallback to direct URL
    analytics_url = "http://analytics-api:8002"
```

### Connection Timeout

```python
# Increase timeout
response = await client.post(
    url,
    json=payload,
    timeout=30.0  # 30 seconds
)
```

### Invalid Request

Ensure:
- All required fields are present
- Lists have consistent length (OHLCV all same length)
- Numeric values are valid (no NaN or Inf)
- Symbol is a string

## Future Enhancements

1. **ML-based Anomaly Detection** - Isolation Forest, VAE
2. **Inter-market Analysis** - Cross-market correlations
3. **Sentiment Integration** - NLP for news/social signals
4. **Risk Metrics** - VaR, Sharpe ratio, Sortino
5. **Backtesting** - Historical signal performance
6. **Real-time Streaming** - WebSocket support

## References

- Service Registry: `src/framework/service_registry.py`
- Analytics API: `src/services/analytics/api.py`
- Volatility: `src/services/analytics/volatility.py`
- Correlation: `src/services/analytics/correlation.py`
- Patterns: `src/services/analytics/patterns.py`
- Anomalies: `src/services/analytics/anomalies.py`
- Integration Example: `examples/analytics_integration.py`
