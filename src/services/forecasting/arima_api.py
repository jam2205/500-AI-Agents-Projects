"""ARIMA FastAPI Server - Time Series Forecasting Endpoint.

Serves ARIMA/SARIMA predictions via HTTP API for agent consumption.
Handles OHLCV data with stationarity testing and ensemble forecasting.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import logging
import sys

# Add parent directory to path for imports
sys.path.insert(0, "/home/user/500-AI-Agents-Projects")

from src.services.forecasting.arima_service import (
    ARIMAService,
    ModelType,
    ARIMAParameters,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ARIMA Forecasting Service",
    description="ARIMA/SARIMA time series forecasting API",
    version="1.0.0",
)

# Initialize service
arima_service = ARIMAService()


class ModelTypeEnum(str, Enum):
    """Model type options."""
    ARIMA = "arima"
    SARIMA = "sarima"
    AUTO = "auto"


class ForecastInput(BaseModel):
    """Input for time series forecasting."""
    symbol: str = Field(..., description="Trading symbol")
    timeseries: List[float] = Field(..., description="Historical price/value series")
    steps: int = Field(default=10, description="Number of steps to forecast")
    model_type: ModelTypeEnum = Field(default="auto", description="Model type")
    confidence_level: float = Field(
        default=0.95, description="Confidence level (0.80 or 0.95)"
    )
    seasonal_period: int = Field(
        default=12, description="Seasonal period for SARIMA"
    )
    p: Optional[int] = Field(None, description="AR order")
    d: Optional[int] = Field(None, description="Integration order")
    q: Optional[int] = Field(None, description="MA order")
    P: Optional[int] = Field(None, description="Seasonal AR order")
    D: Optional[int] = Field(None, description="Seasonal integration order")
    Q: Optional[int] = Field(None, description="Seasonal MA order")


class EnsembleInput(BaseModel):
    """Input for ensemble forecasting."""
    symbol: str = Field(..., description="Trading symbol")
    timeseries: List[float] = Field(..., description="Historical series")
    steps: int = Field(default=10, description="Number of steps to forecast")
    models: List[str] = Field(
        default=["arima", "sarima_12"],
        description="Models to include in ensemble"
    )


class StationarityInput(BaseModel):
    """Input for stationarity testing."""
    timeseries: List[float] = Field(..., description="Time series to test")


class ForecastOutput(BaseModel):
    """Output from forecasting model."""
    symbol: str
    timestamp: str
    forecast: List[float]
    forecast_std: List[float]
    confidence_intervals_95: Dict[str, List[float]]
    confidence_intervals_80: Dict[str, List[float]]
    model_type: str
    parameters: Dict[str, Any]
    metrics: Dict[str, float]


class StationarityOutput(BaseModel):
    """Output from stationarity test."""
    adf_statistic: float
    adf_pvalue: float
    adf_critical_values: Dict[str, float]
    adf_result: str
    kpss_statistic: float
    kpss_pvalue: float
    kpss_critical_values: Dict[str, float]
    kpss_result: str
    differencing_needed: int
    recommendation: str


@app.on_event("startup")
async def startup_event():
    """Initialize at startup."""
    logger.info("ARIMA Forecasting Service initialized")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "arima-forecasting",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/forecast", response_model=ForecastOutput)
async def forecast(input_data: ForecastInput):
    """
    Generate ARIMA time series forecast.

    Args:
        input_data: ForecastInput with time series and parameters

    Returns:
        ForecastOutput with predictions and confidence intervals
    """
    try:
        # Validate input
        if not input_data.timeseries or len(input_data.timeseries) < 10:
            raise HTTPException(
                status_code=400,
                detail="Time series must have at least 10 data points"
            )

        # Build parameters if provided
        parameters = None
        if input_data.p is not None and input_data.d is not None and input_data.q is not None:
            parameters = ARIMAParameters(
                p=input_data.p,
                d=input_data.d,
                q=input_data.q,
                P=input_data.P,
                D=input_data.D,
                Q=input_data.Q,
                s=input_data.seasonal_period if input_data.P else None,
                is_seasonal=input_data.P is not None,
            )

        logger.info(
            f"Forecasting {input_data.symbol} with {input_data.model_type} "
            f"(steps={input_data.steps})"
        )

        # Convert model type
        model_type_map = {
            "arima": ModelType.ARIMA,
            "sarima": ModelType.SARIMA,
            "auto": ModelType.AUTO,
        }

        result = await arima_service.forecast(
            symbol=input_data.symbol,
            timeseries=input_data.timeseries,
            steps=input_data.steps,
            model_type=model_type_map.get(input_data.model_type, ModelType.AUTO),
            confidence_level=input_data.confidence_level,
            parameters=parameters,
            seasonal_period=input_data.seasonal_period,
        )

        return ForecastOutput(
            symbol=result.symbol,
            timestamp=result.timestamp,
            forecast=result.forecast,
            forecast_std=result.forecast_std,
            confidence_intervals_95={
                "lower": result.confidence_intervals_95[0],
                "upper": result.confidence_intervals_95[1],
            },
            confidence_intervals_80={
                "lower": result.confidence_intervals_80[0],
                "upper": result.confidence_intervals_80[1],
            },
            model_type=result.model_type,
            parameters=result.parameters,
            metrics=result.metrics,
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Forecast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ensemble-forecast")
async def ensemble_forecast(input_data: EnsembleInput):
    """
    Generate ensemble forecast combining multiple ARIMA variants.

    Args:
        input_data: EnsembleInput with time series and model selection

    Returns:
        Dictionary with ensemble forecast and individual results
    """
    try:
        if not input_data.timeseries or len(input_data.timeseries) < 20:
            raise HTTPException(
                status_code=400,
                detail="Time series must have at least 20 data points for ensemble"
            )

        logger.info(
            f"Ensemble forecast for {input_data.symbol} "
            f"with models: {input_data.models}"
        )

        result = await arima_service.ensemble_forecast(
            symbol=input_data.symbol,
            timeseries=input_data.timeseries,
            steps=input_data.steps,
            models_to_use=input_data.models,
        )

        return result

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Ensemble forecast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test-stationarity", response_model=StationarityOutput)
async def test_stationarity(input_data: StationarityInput):
    """
    Test time series for stationarity using ADF and KPSS tests.

    Args:
        input_data: StationarityInput with time series

    Returns:
        StationarityOutput with test results and recommendation
    """
    try:
        if not input_data.timeseries or len(input_data.timeseries) < 10:
            raise HTTPException(
                status_code=400,
                detail="Time series must have at least 10 data points"
            )

        logger.info("Testing stationarity...")

        result = await arima_service.test_stationarity(input_data.timeseries)

        # Generate recommendation
        if result.adf_pvalue < 0.05 and result.kpss_pvalue > 0.05:
            recommendation = "Series is stationary. Use d=0 for ARIMA."
        elif result.adf_pvalue >= 0.05 and result.kpss_pvalue <= 0.05:
            recommendation = "Series is non-stationary. Use d=1 or higher for ARIMA."
        else:
            recommendation = f"Unclear stationarity. Try d={result.differencing_needed} for ARIMA."

        return StationarityOutput(
            adf_statistic=result.adf_statistic,
            adf_pvalue=result.adf_pvalue,
            adf_critical_values=result.adf_critical_values,
            adf_result=result.adf_result.value,
            kpss_statistic=result.kpss_statistic,
            kpss_pvalue=result.kpss_pvalue,
            kpss_critical_values=result.kpss_critical_values,
            kpss_result=result.kpss_result.value,
            differencing_needed=result.differencing_needed,
            recommendation=recommendation,
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Stationarity test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/model-info")
async def model_info():
    """Get model information and capabilities."""
    return {
        "service": "ARIMA Forecasting",
        "version": "1.0.0",
        "models": ["ARIMA", "SARIMA", "AUTO"],
        "capabilities": [
            "Univariate time series forecasting",
            "Automatic parameter detection",
            "Ensemble forecasting",
            "Stationarity testing (ADF/KPSS)",
            "Confidence intervals",
            "OHLCV data support",
        ],
        "input_format": "List of float values",
        "output_format": "Forecast with confidence intervals and metrics",
        "min_data_points": 10,
        "recommended_data_points": 100,
        "endpoints": [
            "/forecast - Single ARIMA/SARIMA forecast",
            "/ensemble-forecast - Combine multiple models",
            "/test-stationarity - Test for stationarity",
            "/health - Health check",
            "/model-info - This endpoint",
        ],
    }


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "ARIMA Forecasting Service",
        "description": "Time series forecasting using ARIMA and SARIMA models",
        "endpoints": {
            "GET /health": "Health check",
            "GET /model-info": "Model information",
            "POST /forecast": "ARIMA/SARIMA forecast",
            "POST /ensemble-forecast": "Ensemble forecast",
            "POST /test-stationarity": "Test for stationarity",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8007)
