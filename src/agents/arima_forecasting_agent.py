"""ARIMA Forecasting Agent - Time Series Prediction Coordinator.

Coordinates with ARIMA forecasting service for time series predictions.
Supports ensemble forecasting and stationarity testing.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesData:
    """Time series data point."""
    symbol: str
    values: List[float]
    timestamps: Optional[List[str]] = None
    frequency: str = "1h"


class ARIMAForecastingAgent:
    """Agent for ARIMA time series forecasting."""

    def __init__(self, config: Dict[str, Any], message_bus=None):
        """
        Initialize ARIMA forecasting agent.

        Args:
            config: Configuration dictionary
            message_bus: Message bus for inter-agent communication
        """
        self.config = config
        self.message_bus = message_bus
        self.name = "ARIMAForecastingAgent"
        self.capabilities = [
            "arima_forecast",
            "sarima_forecast",
            "ensemble_forecast",
            "stationarity_test",
        ]
        self.service_url = config.get("arima_service_url", "http://arima-forecasting:8007")
        self.request_timeout = config.get("request_timeout", 30)

    async def forecast_arima(
        self,
        symbol: str,
        timeseries: List[float],
        steps: int = 10,
        model_type: str = "auto",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate ARIMA forecast.

        Args:
            symbol: Trading symbol
            timeseries: Historical values
            steps: Number of steps to forecast
            model_type: "auto", "arima", or "sarima"
            parameters: Optional explicit ARIMA parameters

        Returns:
            Forecast result dictionary
        """
        try:
            payload = {
                "symbol": symbol,
                "timeseries": timeseries,
                "steps": steps,
                "model_type": model_type,
            }

            if parameters:
                payload.update(parameters)

            logger.info(
                f"Requesting ARIMA forecast for {symbol} "
                f"({len(timeseries)} points, {steps} steps)"
            )

            # Call ARIMA service
            result = await self._call_service(
                f"{self.service_url}/forecast",
                payload
            )

            # Broadcast result if message bus available
            if self.message_bus:
                await self.message_bus.publish(
                    "forecast.arima",
                    {
                        "agent": self.name,
                        "symbol": symbol,
                        "result": result,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

            return result

        except Exception as e:
            logger.error(f"ARIMA forecast failed for {symbol}: {e}")
            raise

    async def ensemble_forecast(
        self,
        symbol: str,
        timeseries: List[float],
        steps: int = 10,
        models: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate ensemble forecast using multiple ARIMA variants.

        Args:
            symbol: Trading symbol
            timeseries: Historical values
            steps: Number of steps to forecast
            models: List of models to include (e.g., ["arima", "sarima_12"])

        Returns:
            Ensemble forecast result
        """
        try:
            if models is None:
                models = ["arima", "sarima_12"]

            payload = {
                "symbol": symbol,
                "timeseries": timeseries,
                "steps": steps,
                "models": models,
            }

            logger.info(
                f"Requesting ensemble forecast for {symbol} "
                f"with models: {models}"
            )

            result = await self._call_service(
                f"{self.service_url}/ensemble-forecast",
                payload
            )

            if self.message_bus:
                await self.message_bus.publish(
                    "forecast.ensemble",
                    {
                        "agent": self.name,
                        "symbol": symbol,
                        "models": models,
                        "result": result,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Ensemble forecast failed for {symbol}: {e}")
            raise

    async def test_stationarity(
        self,
        timeseries: List[float],
    ) -> Dict[str, Any]:
        """
        Test time series for stationarity.

        Args:
            timeseries: Time series to test

        Returns:
            Stationarity test results with recommendation
        """
        try:
            payload = {"timeseries": timeseries}

            logger.info(f"Testing stationarity for {len(timeseries)} points")

            result = await self._call_service(
                f"{self.service_url}/test-stationarity",
                payload
            )

            if self.message_bus:
                await self.message_bus.publish(
                    "analysis.stationarity",
                    {
                        "agent": self.name,
                        "result": result,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

            return result

        except Exception as e:
            logger.error(f"Stationarity test failed: {e}")
            raise

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming message from message bus.

        Args:
            message: Message with forecast request

        Returns:
            Forecast result
        """
        try:
            message_type = message.get("type", "").lower()

            if "forecast" in message_type:
                return await self.forecast_arima(
                    symbol=message.get("symbol", "UNKNOWN"),
                    timeseries=message.get("timeseries", []),
                    steps=message.get("steps", 10),
                    model_type=message.get("model_type", "auto"),
                    parameters=message.get("parameters"),
                )

            elif "ensemble" in message_type:
                return await self.ensemble_forecast(
                    symbol=message.get("symbol", "UNKNOWN"),
                    timeseries=message.get("timeseries", []),
                    steps=message.get("steps", 10),
                    models=message.get("models"),
                )

            elif "stationarity" in message_type:
                return await self.test_stationarity(
                    timeseries=message.get("timeseries", [])
                )

            else:
                logger.warning(f"Unknown message type: {message_type}")
                return {"error": f"Unknown message type: {message_type}"}

        except Exception as e:
            logger.error(f"Message processing failed: {e}")
            return {"error": str(e)}

    async def _call_service(
        self,
        url: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call ARIMA service via HTTP.

        Args:
            url: Service endpoint URL
            payload: Request payload

        Returns:
            Service response
        """
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.request_timeout)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise Exception(
                            f"Service returned {response.status}: {error_text}"
                        )

        except ImportError:
            logger.warning("aiohttp not installed, falling back to mock response")
            return self._mock_response(payload)

    def _mock_response(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate mock response when service unavailable.

        Args:
            payload: Request payload

        Returns:
            Mock forecast result
        """
        symbol = payload.get("symbol", "UNKNOWN")
        steps = payload.get("steps", 10)
        timeseries = payload.get("timeseries", [])

        if not timeseries:
            return {"error": "No timeseries provided"}

        # Simple trend continuation mock
        last_val = timeseries[-1]
        trend = (timeseries[-1] - timeseries[-20]) / 20 if len(timeseries) > 20 else 0

        forecast = [last_val + trend * (i + 1) for i in range(steps)]
        forecast_std = [abs(trend) * 0.1 for _ in range(steps)]

        return {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "forecast": forecast,
            "forecast_std": forecast_std,
            "confidence_intervals_95": {
                "lower": [f - 1.96 * s for f, s in zip(forecast, forecast_std)],
                "upper": [f + 1.96 * s for f, s in zip(forecast, forecast_std)],
            },
            "confidence_intervals_80": {
                "lower": [f - 1.28 * s for f, s in zip(forecast, forecast_std)],
                "upper": [f + 1.28 * s for f, s in zip(forecast, forecast_std)],
            },
            "model_type": "ARIMA_MOCK",
            "parameters": {"p": 1, "d": 1, "q": 1},
            "metrics": {"aic": 0, "bic": 0, "rmse": 0},
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if ARIMA service is healthy.

        Returns:
            Health status
        """
        try:
            result = await self._call_service(
                f"{self.service_url}/health",
                {}
            )
            return {
                "agent": self.name,
                "status": "healthy",
                "service_status": result.get("status", "unknown"),
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "agent": self.name,
                "status": "unhealthy",
                "error": str(e),
            }
