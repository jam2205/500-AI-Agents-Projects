"""Analytics API - FastAPI endpoint for all analytics tools."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from services.analytics.volatility import VolatilityAnalyzer, VolatilityMetrics
from services.analytics.correlation import CorrelationAnalyzer, CorrelationAnalysis
from services.analytics.patterns import PatternAnalyzer, PatternAnalysis
from services.analytics.anomalies import AnomalyDetector, AnomalyAnalysis
from framework.service_registry import register_service, ServiceInfo, ServiceEndpoint

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Analytics Service",
    description="Advanced market analytics for volatility, correlation, patterns, and anomalies",
    version="1.0.0"
)


# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================

class VolatilityRequest(BaseModel):
    """Request for volatility analysis."""
    symbol: str
    returns: List[float]
    lookback: int = 50
    method: str = "realized"  # "realized", "parkinson", "garman_klass", "rogers_satchell", "garch"


class VolatilityResponse(BaseModel):
    """Response with volatility metrics."""
    symbol: str
    timestamp: str
    volatility: float
    method: str
    percentile: float
    trend: str
    forecast_1d: Optional[float]
    forecast_5d: Optional[float]
    signals: List[str]
    confidence: float


class CorrelationRequest(BaseModel):
    """Request for correlation analysis."""
    symbol1: str
    symbol2: str
    prices1: List[float]
    prices2: List[float]
    method: str = "pearson"


class CorrelationResponse(BaseModel):
    """Response with correlation metrics."""
    symbol_pair: str
    timestamp: str
    correlation: float
    regime: str
    lead_lag: Optional[str]
    lag_periods: int
    rolling_trend: str
    regime_change: bool
    signals: List[str]
    confidence: float


class PatternRequest(BaseModel):
    """Request for pattern analysis."""
    symbol: str
    highs: List[float]
    lows: List[float]
    closes: List[float]


class PatternResponse(BaseModel):
    """Response with pattern analysis."""
    symbol: str
    timestamp: str
    support_levels: List[Dict[str, Any]]
    resistance_levels: List[Dict[str, Any]]
    chart_patterns: List[Dict[str, Any]]
    pivot_points: Dict[str, float]
    signals: List[str]
    confidence: float


class AnomalyRequest(BaseModel):
    """Request for anomaly detection."""
    symbol: str
    opens: List[float]
    highs: List[float]
    lows: List[float]
    closes: List[float]
    volumes: List[float]


class AnomalyResponse(BaseModel):
    """Response with anomaly analysis."""
    symbol: str
    timestamp: str
    anomaly_score: float
    price_anomalies: int
    volume_anomalies: int
    volatility_anomalies: int
    behavioral_flags: int
    signals: List[str]
    confidence: float


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "analytics-api"
    }


# ============================================================================
# Volatility Endpoints
# ============================================================================

@app.post("/volatility/analyze", response_model=VolatilityResponse)
async def analyze_volatility(request: VolatilityRequest):
    """
    Analyze volatility using specified method.

    Methods:
    - realized: Historical standard deviation
    - parkinson: High-low based (more efficient)
    - garman_klass: OHLC based
    - rogers_satchell: Drift-independent
    - garch: GARCH(1,1) modeling with forecast
    """
    try:
        if request.method == "realized":
            vol_metrics = VolatilityAnalyzer.realized_volatility(
                request.returns,
                lookback=request.lookback
            )
        elif request.method == "parkinson":
            vol_metrics = VolatilityAnalyzer.parkinson_volatility(
                request.returns,
                lookback=request.lookback
            )
        elif request.method == "garman_klass":
            vol_metrics = VolatilityAnalyzer.garman_klass_volatility(
                request.returns,
                lookback=request.lookback
            )
        elif request.method == "rogers_satchell":
            vol_metrics = VolatilityAnalyzer.rogers_satchell_volatility(
                request.returns,
                lookback=request.lookback
            )
        elif request.method == "garch":
            vol_metrics = VolatilityAnalyzer.garch_volatility(
                request.returns
            )
        else:
            raise ValueError(f"Unknown volatility method: {request.method}")

        signal = VolatilityAnalyzer.volatility_signal(vol_metrics)

        return VolatilityResponse(
            symbol=request.symbol,
            timestamp=vol_metrics.timestamp.isoformat(),
            volatility=vol_metrics.volatility,
            method=request.method,
            percentile=vol_metrics.percentile,
            trend=vol_metrics.trend,
            forecast_1d=vol_metrics.forecast_1d,
            forecast_5d=vol_metrics.forecast_5d,
            signals=signal["signals"],
            confidence=signal["confidence"]
        )
    except Exception as e:
        logger.error(f"Error analyzing volatility: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Correlation Endpoints
# ============================================================================

@app.post("/correlation/analyze", response_model=CorrelationResponse)
async def analyze_correlation(request: CorrelationRequest):
    """Analyze correlation between two assets."""
    try:
        analysis = CorrelationAnalyzer.analyze_pair(
            request.symbol1,
            request.symbol2,
            request.prices1,
            request.prices2
        )

        signal = CorrelationAnalyzer.correlation_signal(analysis)

        return CorrelationResponse(
            symbol_pair=analysis.symbol_pair,
            timestamp=analysis.timestamp.isoformat(),
            correlation=analysis.correlation,
            regime=analysis.correlation_regime,
            lead_lag=analysis.lead_lag_relationship,
            lag_periods=analysis.lead_lag_lag_periods,
            rolling_trend=analysis.rolling_correlation_trend,
            regime_change=analysis.regime_change_detected,
            signals=signal["signals"],
            confidence=signal["confidence"]
        )
    except Exception as e:
        logger.error(f"Error analyzing correlation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/correlation/matrix")
async def correlation_matrix(symbols: List[str], price_data: Dict[str, List[float]]):
    """Calculate correlation matrix across multiple assets."""
    try:
        result = CorrelationAnalyzer.correlation_matrix(symbols, price_data)
        return {
            "symbols": result["symbols"],
            "matrix": result["matrix"],
            "strongest_positive": result["strongest_positive"],
            "strongest_negative": result["strongest_negative"],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error calculating correlation matrix: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Pattern Recognition Endpoints
# ============================================================================

@app.post("/patterns/analyze", response_model=PatternResponse)
async def analyze_patterns(request: PatternRequest):
    """Analyze chart patterns and support/resistance levels."""
    try:
        analysis = PatternAnalyzer.analyze_patterns(
            request.symbol,
            request.highs,
            request.lows,
            request.closes
        )

        return PatternResponse(
            symbol=analysis.symbol,
            timestamp=analysis.timestamp.isoformat(),
            support_levels=[
                {
                    "price": sl.price,
                    "strength": sl.strength,
                    "touches": sl.touches,
                    "confidence": sl.confidence
                }
                for sl in analysis.support_levels
            ],
            resistance_levels=[
                {
                    "price": rl.price,
                    "strength": rl.strength,
                    "touches": rl.touches,
                    "confidence": rl.confidence
                }
                for rl in analysis.resistance_levels
            ],
            chart_patterns=[
                {
                    "name": cp.pattern_name,
                    "type": cp.pattern_type,
                    "target_pct": cp.target_pct,
                    "confidence": cp.confidence
                }
                for cp in analysis.chart_patterns
            ],
            pivot_points=analysis.pivot_points,
            signals=analysis.signals,
            confidence=analysis.confidence
        )
    except Exception as e:
        logger.error(f"Error analyzing patterns: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Anomaly Detection Endpoints
# ============================================================================

@app.post("/anomalies/detect", response_model=AnomalyResponse)
async def detect_anomalies(request: AnomalyRequest):
    """Detect statistical and behavioral anomalies."""
    try:
        analysis = AnomalyDetector.analyze_anomalies(
            request.symbol,
            request.opens,
            request.highs,
            request.lows,
            request.closes,
            request.volumes
        )

        return AnomalyResponse(
            symbol=analysis.symbol,
            timestamp=analysis.timestamp.isoformat(),
            anomaly_score=analysis.overall_anomaly_score,
            price_anomalies=len(analysis.price_anomalies),
            volume_anomalies=len(analysis.volume_anomalies),
            volatility_anomalies=len(analysis.volatility_anomalies),
            behavioral_flags=len(analysis.behavioral_flags),
            signals=analysis.signals,
            confidence=analysis.confidence
        )
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Composite Analysis Endpoint
# ============================================================================

@app.post("/composite/analyze")
async def composite_analysis(
    symbol: str,
    highs: List[float],
    lows: List[float],
    opens: List[float],
    closes: List[float],
    volumes: List[float]
):
    """
    Run all analytics tools on a symbol and return comprehensive analysis.
    """
    try:
        # Calculate returns for volatility
        returns = []
        for i in range(1, len(closes)):
            ret = (closes[i] - closes[i-1]) / closes[i-1]
            returns.append(ret)

        # Run all analyses in parallel conceptually
        volatility_analysis = VolatilityAnalyzer.realized_volatility(returns)
        vol_signal = VolatilityAnalyzer.volatility_signal(volatility_analysis)

        patterns_analysis = PatternAnalyzer.analyze_patterns(symbol, highs, lows, closes)

        anomalies_analysis = AnomalyDetector.analyze_anomalies(
            symbol, opens, highs, lows, closes, volumes
        )

        return {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "volatility": {
                "current": volatility_analysis.volatility,
                "percentile": volatility_analysis.percentile,
                "trend": volatility_analysis.trend,
                "signals": vol_signal["signals"],
                "confidence": vol_signal["confidence"]
            },
            "patterns": {
                "support_levels": len(patterns_analysis.support_levels),
                "resistance_levels": len(patterns_analysis.resistance_levels),
                "chart_patterns": len(patterns_analysis.chart_patterns),
                "signals": patterns_analysis.signals,
                "confidence": patterns_analysis.confidence
            },
            "anomalies": {
                "anomaly_score": anomalies_analysis.overall_anomaly_score,
                "total_anomalies": sum([
                    len(anomalies_analysis.price_anomalies),
                    len(anomalies_analysis.volume_anomalies),
                    len(anomalies_analysis.volatility_anomalies),
                    len(anomalies_analysis.behavioral_flags),
                    len(anomalies_analysis.momentum_anomalies)
                ]),
                "signals": anomalies_analysis.signals,
                "confidence": anomalies_analysis.confidence
            },
            "overall_signal_count": (
                len(vol_signal["signals"]) +
                len(patterns_analysis.signals) +
                len(anomalies_analysis.signals)
            )
        }
    except Exception as e:
        logger.error(f"Error in composite analysis: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Service Registration
# ============================================================================

def register_analytics_service():
    """Register this service with the service registry."""
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
            ServiceEndpoint(
                path="/correlation/analyze",
                method="POST",
                description="Analyze correlation between assets",
                capabilities=["correlation_analysis"]
            ),
            ServiceEndpoint(
                path="/correlation/matrix",
                method="POST",
                description="Calculate correlation matrix",
                capabilities=["correlation_matrix"]
            ),
            ServiceEndpoint(
                path="/patterns/analyze",
                method="POST",
                description="Analyze chart patterns",
                capabilities=["pattern_recognition"]
            ),
            ServiceEndpoint(
                path="/anomalies/detect",
                method="POST",
                description="Detect anomalies",
                capabilities=["anomaly_detection"]
            ),
            ServiceEndpoint(
                path="/composite/analyze",
                method="POST",
                description="Comprehensive analysis",
                capabilities=["volatility_analysis", "correlation_analysis", "pattern_recognition", "anomaly_detection"]
            ),
        ],
        capabilities=[
            "volatility_analysis",
            "correlation_analysis",
            "pattern_recognition",
            "anomaly_detection",
            "composite_analysis"
        ],
        dependencies=[]
    )

    register_service(service_info)
    logger.info("Analytics service registered with service registry")


# ============================================================================
# Startup and Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Register service on startup."""
    logger.info("Analytics API starting up...")
    register_analytics_service()
    logger.info("Analytics API ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Analytics API shutting down...")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8002))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
