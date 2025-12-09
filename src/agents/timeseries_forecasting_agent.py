"""Time Series Forecasting Agent - Coordinates ARIMA and SARIMA model calls.

Orchestrates forecasting across multiple models and timeframes:
- ARIMA: AutoRegressive Integrated Moving Average for non-seasonal data
- SARIMA: Seasonal ARIMA for seasonal patterns
- Ensemble forecasts from multiple model variants
- Confidence-weighted ensemble predictions with stationarity awareness
"""

import json
import aiohttp
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.framework.base_agent import BaseAgent, AgentConfig, AgentRole, Message
from src.utils.timeseries_prep import (
    TimeSeriesPreprocessor,
    TimeSeriesDataPipeline,
)


class TimeSeriesForecastingAgent(BaseAgent):
    """Orchestrates time series forecasting across ARIMA and SARIMA models.

    Responsibilities:
    - Prepare market data for models
    - Test stationarity of time series
    - Call ARIMA for non-seasonal forecasts
    - Call SARIMA for seasonal pattern detection
    - Ensemble predictions with confidence weighting
    - Generate buy/sell signals from forecasts
    - Track forecast accuracy
    """

    def __init__(self, config: AgentConfig, message_bus=None):
        """Initialize time series forecasting agent."""
        if config.system_prompt is None:
            config.system_prompt = self._get_forecasting_system_prompt()
        super().__init__(config, message_bus)
        self.preprocessor = TimeSeriesPreprocessor(
            normalization="minmax",
            window_length=512
        )
        self.pipeline = TimeSeriesDataPipeline(
            window_length=512,
            normalization="minmax"
        )
        self.arima_url = "http://arima-forecasting:8007"
        self.forecast_history: Dict[str, List[Dict[str, Any]]] = {}
        self.accuracy_metrics: Dict[str, Dict[str, float]] = {}

    def _get_forecasting_system_prompt(self) -> str:
        """Get system prompt for forecasting agent."""
        return """You are a Time Series Forecasting Specialist in a multi-agent trading system.

Your expertise:
1. ARIMA: AutoRegressive Integrated Moving Average
   - Non-seasonal time series forecasting
   - Auto-parameter detection (p, d, q)
   - Good for trending markets and mean reversion
   - Fast, lightweight, statistically sound

2. SARIMA: Seasonal ARIMA
   - Seasonal pattern detection (monthly, quarterly, annual)
   - Captures repeating cycles and seasonal breaks
   - Better for commodities, bonds, FX with seasonal components
   - Multi-scale analysis (daily/weekly/monthly)

3. Stationarity Testing
   - ADF test (Augmented Dickey-Fuller)
   - KPSS test (Kwiatkowski-Phillips-Schmidt-Shin)
   - Automatic differencing level detection
   - Confidence intervals and uncertainty quantification

4. Ensemble Methods
   - Multi-model confidence weighting
   - ARIMA + SARIMA combination
   - Consensus scoring
   - Divergence detection and risk warnings

Your responsibilities:
- Prepare price series for ARIMA analysis
- Test stationarity to guide differencing
- Call ARIMA for non-seasonal analysis
- Call SARIMA for seasonal pattern detection
- Ensemble predictions for better coverage
- Detect forecast divergence (warning signal)
- Generate trading signals with risk assessment
- Track forecast accuracy for model weighting

Key insights:
- Stationary series = d=0 (no differencing needed)
- Non-stationary = d=1 or d=2 (differencing required)
- Seasonal patterns = use SARIMA
- Large model disagreement = uncertainty = reduce position
- Both models bullish = high confidence buy signal
- Both models bearish = high confidence sell signal

Framework integration:
- Work with Volume agents for confirmation
- Work with Bond agents for FX moves
- Work with Cycle agents for phase alignment
- Work with Session agents for entry timing"""

    async def prepare_forecast_request(
        self,
        symbol: str,
        timeframe: str,
        ohlcv_data: List[Dict[str, Any]],
        atr_values: List[float],
        adr_values: List[float],
        session_codes: List[int],
        normalize: bool = True
    ) -> Dict[str, Any]:
        """
        Prepare data for forecasting models.

        Args:
            symbol: Trading symbol
            timeframe: "daily", "weekly", or "monthly"
            ohlcv_data: List of OHLCV bars
            atr_values: ATR values
            adr_values: ADR values
            session_codes: Session encoding (0-4)
            normalize: Whether to normalize

        Returns:
            Request payload for model APIs
        """
        try:
            # Prepare window
            window = self.preprocessor.prepare_ohlcv_window(
                symbol, ohlcv_data, atr_values, adr_values, session_codes,
                normalize=normalize, fit_scalers=True
            )

            # Build request payload
            payload = {
                "input_sequence": window.sequence.tolist(),
                "features": window.features,
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": datetime.utcnow().isoformat(),
            }

            return {
                "success": True,
                "payload": payload,
                "metadata": window.metadata
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def call_arima(
        self,
        symbol: str,
        timeseries: List[float],
        steps: int = 96,
        model_type: str = "auto"
    ) -> Dict[str, Any]:
        """
        Call ARIMA model for forecasting.

        Args:
            symbol: Trading symbol
            timeseries: Price/close series
            steps: Steps to forecast
            model_type: "arima", "sarima", or "auto"

        Returns:
            Forecast result from ARIMA
        """
        try:
            payload = {
                "symbol": symbol,
                "timeseries": timeseries,
                "steps": steps,
                "model_type": model_type,
                "confidence_level": 0.95
            }

            # Call API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.arima_url}/forecast",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        result["model"] = "arima"
                        result["call_timestamp"] = datetime.utcnow().isoformat()
                        return result
                    else:
                        error = await response.text()
                        return {
                            "error": f"ARIMA API error {response.status}: {error}",
                            "model": "arima"
                        }

        except asyncio.TimeoutError:
            return {"error": "ARIMA request timeout", "model": "arima"}
        except Exception as e:
            return {"error": f"ARIMA call failed: {str(e)}", "model": "arima"}

    async def call_sarima(
        self,
        symbol: str,
        timeseries: List[float],
        steps: int = 96,
        seasonal_period: int = 12
    ) -> Dict[str, Any]:
        """
        Call SARIMA model for seasonal forecasting.

        Args:
            symbol: Trading symbol
            timeseries: Price/close series
            steps: Steps to forecast
            seasonal_period: Seasonal period (12 for monthly, 252 for trading days)

        Returns:
            Forecast result from SARIMA
        """
        try:
            payload = {
                "symbol": symbol,
                "timeseries": timeseries,
                "steps": steps,
                "model_type": "sarima",
                "seasonal_period": seasonal_period,
                "confidence_level": 0.95
            }

            # Call API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.arima_url}/forecast",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        result["model"] = "sarima"
                        result["call_timestamp"] = datetime.utcnow().isoformat()
                        return result
                    else:
                        error = await response.text()
                        return {
                            "error": f"SARIMA API error {response.status}: {error}",
                            "model": "sarima"
                        }

        except asyncio.TimeoutError:
            return {"error": "SARIMA request timeout", "model": "sarima"}
        except Exception as e:
            return {"error": f"SARIMA call failed: {str(e)}", "model": "sarima"}

    async def ensemble_forecasts(
        self,
        arima_result: Dict[str, Any],
        sarima_result: Dict[str, Any],
        symbol: str,
        current_price: float
    ) -> Dict[str, Any]:
        """
        Create ensemble forecast from ARIMA and SARIMA models.

        Args:
            arima_result: ARIMA forecast
            sarima_result: SARIMA forecast
            symbol: Trading symbol
            current_price: Current price

        Returns:
            Ensemble forecast with confidence weighting
        """
        try:
            arima_forecast = arima_result.get("forecast", [])
            sarima_forecast = sarima_result.get("forecast", [])

            if not arima_forecast or not sarima_forecast:
                return {"error": "One or both models failed to generate forecasts"}

            # Get confidence scores
            arima_conf = arima_result.get("confidence", 50) / 100
            sarima_conf = sarima_result.get("confidence", 50) / 100

            # Normalize confidence scores
            total_conf = arima_conf + sarima_conf
            arima_weight = arima_conf / total_conf if total_conf > 0 else 0.5
            sarima_weight = sarima_conf / total_conf if total_conf > 0 else 0.5

            # Align forecasts to same length (use shorter)
            min_len = min(len(arima_forecast), len(sarima_forecast))
            arima_f = arima_forecast[:min_len]
            sarima_f = sarima_forecast[:min_len]

            # Weighted ensemble
            ensemble = [
                af * arima_weight + sf * sarima_weight
                for af, sf in zip(arima_f, sarima_f)
            ]

            # Calculate disagreement (divergence warning)
            disagreement = [
                abs(af - sf) for af, sf in zip(arima_f, sarima_f)
            ]
            avg_disagreement = sum(disagreement) / len(disagreement) if disagreement else 0
            max_disagreement = max(disagreement) if disagreement else 0

            # Generate signal
            ensemble_direction = "bullish" if ensemble[-1] > current_price else "bearish"
            arima_direction = "bullish" if arima_f[-1] > current_price else "bearish"
            sarima_direction = "bullish" if sarima_f[-1] > current_price else "bearish"

            # Consensus level
            if ensemble_direction == arima_direction == sarima_direction:
                consensus = "strong"
                consensus_confidence = 0.9
            elif (ensemble_direction == arima_direction or
                  ensemble_direction == sarima_direction):
                consensus = "moderate"
                consensus_confidence = 0.7
            else:
                consensus = "weak"
                consensus_confidence = 0.4

            result = {
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat(),
                "current_price": current_price,
                "ensemble_forecast": ensemble,
                "ensemble_direction": ensemble_direction,
                "ensemble_target": ensemble[-1] if ensemble else current_price,
                "arima_forecast": arima_f,
                "arima_direction": arima_direction,
                "arima_target": arima_f[-1] if arima_f else current_price,
                "sarima_forecast": sarima_f,
                "sarima_direction": sarima_direction,
                "sarima_target": sarima_f[-1] if sarima_f else current_price,
                "weights": {
                    "arima": float(arima_weight),
                    "sarima": float(sarima_weight),
                },
                "consensus": consensus,
                "consensus_confidence": consensus_confidence,
                "disagreement": {
                    "average": float(avg_disagreement),
                    "maximum": float(max_disagreement),
                    "warning": "HIGH_DIVERGENCE" if avg_disagreement > (current_price * 0.02) else "NORMAL"
                },
                "trading_signal": self._generate_signal(
                    ensemble_direction,
                    consensus_confidence,
                    avg_disagreement / current_price if current_price > 0 else 0
                )
            }

            return result

        except Exception as e:
            return {"error": f"Ensemble failed: {str(e)}"}

    def _generate_signal(
        self,
        direction: str,
        confidence: float,
        uncertainty: float
    ) -> Dict[str, Any]:
        """Generate trading signal from ensemble."""
        if uncertainty > 0.05:  # >5% divergence
            return {
                "type": "CAUTION",
                "action": "REDUCE_SIZE",
                "description": f"Models diverging significantly - reduce position to {int((1-uncertainty)*100)}%"
            }

        if direction == "bullish":
            if confidence > 0.85:
                return {
                    "type": "STRONG_BUY",
                    "action": "SCALE_IN",
                    "position_size": "FULL",
                    "description": "High confidence bullish ensemble"
                }
            elif confidence > 0.70:
                return {
                    "type": "BUY",
                    "action": "ENTER",
                    "position_size": "3/4",
                    "description": "Moderate confidence bullish ensemble"
                }
            else:
                return {
                    "type": "WEAK_BUY",
                    "action": "SMALL_POSITION",
                    "position_size": "1/2",
                    "description": "Weak bullish signal - wait for confirmation"
                }
        else:
            if confidence > 0.85:
                return {
                    "type": "STRONG_SELL",
                    "action": "SCALE_OUT",
                    "position_size": "EXIT",
                    "description": "High confidence bearish ensemble"
                }
            elif confidence > 0.70:
                return {
                    "type": "SELL",
                    "action": "EXIT",
                    "position_size": "3/4",
                    "description": "Moderate confidence bearish ensemble"
                }
            else:
                return {
                    "type": "WEAK_SELL",
                    "action": "PROTECT",
                    "position_size": "1/2",
                    "description": "Weak bearish signal - tighten stops"
                }

    async def forecast_symbol(
        self,
        symbol: str,
        timeframe: str,
        ohlcv_data: List[Dict[str, Any]],
        atr_values: List[float],
        adr_values: List[float],
        session_codes: List[int],
        current_price: float,
        closes_only: bool = True
    ) -> Dict[str, Any]:
        """
        Generate ensemble forecast for a symbol.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe for analysis
            ohlcv_data: OHLCV data
            atr_values: ATR values (optional for ARIMA)
            adr_values: ADR values (optional for ARIMA)
            session_codes: Session codes (optional for ARIMA)
            current_price: Current market price
            closes_only: Use only closing prices for ARIMA

        Returns:
            Complete ensemble forecast with signals
        """
        try:
            # Extract closing prices for ARIMA
            if closes_only:
                timeseries = [bar.get("close", bar.get("c", 0)) if isinstance(bar, dict) else bar
                             for bar in ohlcv_data]
            else:
                timeseries = [bar.get("close", bar.get("c", 0)) if isinstance(bar, dict) else bar
                             for bar in ohlcv_data]

            # Call both models in parallel
            arima_task = self.call_arima(
                symbol, timeseries, steps=96, model_type="auto"
            )
            sarima_task = self.call_sarima(
                symbol, timeseries, steps=96, seasonal_period=12
            )

            import asyncio
            arima_result, sarima_result = await asyncio.gather(
                arima_task, sarima_task
            )

            # Check for errors
            if "error" in arima_result and "error" in sarima_result:
                return {
                    "error": "Both models failed",
                    "symbol": symbol,
                    "arima_error": arima_result["error"],
                    "sarima_error": sarima_result["error"]
                }

            # Ensemble the forecasts
            ensemble = await self.ensemble_forecasts(
                arima_result, sarima_result, symbol, current_price
            )

            # Broadcast forecast
            message = Message(
                sender_id=self.config.agent_id,
                message_type="timeseries_forecast",
                content=ensemble
            )
            await self.message_bus.publish(message)

            # Store in history
            if symbol not in self.forecast_history:
                self.forecast_history[symbol] = []
            self.forecast_history[symbol].append(ensemble)

            return ensemble

        except Exception as e:
            return {"error": f"Forecast failed: {str(e)}", "symbol": symbol}

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute forecasting tasks."""
        task_type = task.get("type")

        if task_type == "forecast_symbol":
            result = await self.forecast_symbol(
                task.get("symbol"),
                task.get("timeframe", "daily"),
                task.get("ohlcv_data", []),
                task.get("atr_values", []),
                task.get("adr_values", []),
                task.get("session_codes", []),
                task.get("current_price", 0)
            )
            return result

        elif task_type == "get_history":
            symbol = task.get("symbol")
            if symbol in self.forecast_history:
                return {
                    "success": True,
                    "symbol": symbol,
                    "forecasts": self.forecast_history[symbol],
                    "count": len(self.forecast_history[symbol])
                }
            return {"error": f"No history for {symbol}"}

        elif task_type == "get_stats":
            total_forecasts = sum(len(f) for f in self.forecast_history.values())
            return {
                "total_forecasts": total_forecasts,
                "symbols_tracked": len(self.forecast_history),
                "symbols": list(self.forecast_history.keys())
            }

        return {"error": "Unknown task type"}
