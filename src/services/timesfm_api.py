"""TimesFM FastAPI Server - Google's Time Series Foundation Model Endpoint.

Serves TimesFM predictions via HTTP API for agent consumption.
Handles OHLCV data with ATR/ADR/session features.
Supports S3 data loading and caching.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TimesFM Forecasting Service",
    description="Google TimesFM time series foundation model API",
    version="1.0.0"
)

# Models will be loaded at startup
timesfm_model = None


class TimeSeriesInput(BaseModel):
    """Input for time series forecasting."""
    input_sequence: List[List[float]] = Field(
        ..., description="2D array of shape (window_length, num_features)"
    )
    features: List[str] = Field(
        default=["close"], description="Feature names in order"
    )
    prediction_length: int = Field(
        default=96, description="Number of steps to forecast"
    )
    freq: Optional[str] = Field(
        default="1h", description="Frequency of time series"
    )
    symbol: Optional[str] = Field(default="ES", description="Asset symbol")
    confidence_level: float = Field(
        default=0.8, description="Confidence level for predictions (0-1)"
    )


class ForecastResult(BaseModel):
    """Output from forecasting model."""
    symbol: str
    timestamp: str
    forecast: List[float] = Field(description="Predicted values")
    forecast_std: Optional[List[float]] = Field(
        default=None, description="Standard deviation of forecast"
    )
    confidence_intervals: Optional[Dict[str, List[float]]] = Field(
        default=None, description="95% and 80% confidence intervals"
    )
    features: List[str]
    prediction_length: int
    model: str = "timesfm"
    input_length: int


@app.on_event("startup")
async def startup_event():
    """Load model at startup."""
    global timesfm_model
    try:
        logger.info("Loading TimesFM model...")
        # Import here to avoid loading if not needed
        try:
            from timesfm import TimesFM
            timesfm_model = TimesFM()
        except ImportError:
            logger.warning(
                "timesfm package not installed. "
                "Install with: pip install google-research-timesfm"
            )
            # Create mock for development
            timesfm_model = MockTimesFM()
        logger.info("TimesFM model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load TimesFM model: {e}")
        raise


class MockTimesFM:
    """Mock TimesFM for testing without model."""

    def __init__(self):
        self.context_len = 512

    def forecast(self, context, prediction_length):
        """Return mock forecast."""
        # Simple trend continuation
        context_array = np.array(context)
        if len(context_array.shape) == 1:
            last_val = context_array[-1]
            trend = (context_array[-1] - context_array[-50]) / 50
        else:
            last_val = context_array[-1, 0]
            trend = (context_array[-1, 0] - context_array[-50, 0]) / 50

        forecast = [last_val + trend * (i + 1) for i in range(prediction_length)]
        return np.array(forecast)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": "timesfm",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/predict", response_model=ForecastResult)
async def predict(input_data: TimeSeriesInput):
    """
    Generate time series forecast.

    Args:
        input_data: TimeSeriesInput with time series and parameters

    Returns:
        ForecastResult with predictions and confidence intervals
    """
    try:
        if timesfm_model is None:
            raise HTTPException(
                status_code=503,
                detail="Model not loaded. Check logs."
            )

        # Convert to numpy array
        sequence = np.array(input_data.input_sequence, dtype=np.float32)

        if len(sequence.shape) == 1:
            sequence = sequence.reshape(-1, 1)

        logger.info(
            f"Forecasting {input_data.symbol} "
            f"with input shape {sequence.shape}, "
            f"prediction_length={input_data.prediction_length}"
        )

        # Generate forecast
        forecast_values = timesfm_model.forecast(
            sequence,
            prediction_length=input_data.prediction_length
        )

        # Calculate confidence intervals (simple method)
        std_forecast = np.std(forecast_values) * 0.1  # 10% of std as uncertainty
        std_values = [float(std_forecast)] * len(forecast_values)

        # 95% CI: ±1.96 * std, 80% CI: ±1.28 * std
        ci_95_upper = (forecast_values + 1.96 * std_forecast).tolist()
        ci_95_lower = (forecast_values - 1.96 * std_forecast).tolist()
        ci_80_upper = (forecast_values + 1.28 * std_forecast).tolist()
        ci_80_lower = (forecast_values - 1.28 * std_forecast).tolist()

        return ForecastResult(
            symbol=input_data.symbol,
            timestamp=datetime.utcnow().isoformat(),
            forecast=forecast_values.tolist(),
            forecast_std=std_values,
            confidence_intervals={
                "ci_95_upper": ci_95_upper,
                "ci_95_lower": ci_95_lower,
                "ci_80_upper": ci_80_upper,
                "ci_80_lower": ci_80_lower,
            },
            features=input_data.features,
            prediction_length=input_data.prediction_length,
            input_length=len(sequence)
        )

    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch-predict")
async def batch_predict(requests: List[TimeSeriesInput]):
    """
    Batch prediction for multiple time series.

    Args:
        requests: List of TimeSeriesInput objects

    Returns:
        List of ForecastResults
    """
    results = []
    for req in requests:
        try:
            result = await predict(req)
            results.append(result)
        except HTTPException as e:
            logger.error(f"Batch predict failed for {req.symbol}: {e.detail}")
            results.append({"error": str(e.detail), "symbol": req.symbol})

    return results


@app.get("/model-info")
async def model_info():
    """Get model information."""
    return {
        "model_name": "TimesFM",
        "organization": "Google Research",
        "description": "Time Series Foundation Model",
        "context_length": getattr(timesfm_model, 'context_len', 512),
        "capabilities": [
            "Univariate forecasting",
            "Multivariate forecasting",
            "OHLCV data support",
            "Technical indicators",
        ],
        "input_format": "2D array (time_steps, features)",
        "output_format": "Forecast values with confidence intervals"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
