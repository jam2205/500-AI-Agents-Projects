"""Time Series Forecasting Agent - Coordinates TimesFM and PatchTST model calls.

Orchestrates forecasting across multiple models and timeframes:
- TimesFM: Google's foundation model for short-medium horizon
- PatchTST: Patch-based transformer for long-horizon forecasting
- Consensus forecasts from multiple models
- Confidence-weighted ensemble predictions
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
    """Orchestrates time series forecasting across TimesFM and PatchTST.

    Responsibilities:
    - Prepare market data for models
    - Call TimesFM for baseline/short-horizon forecasts
    - Call PatchTST for long-horizon forecasts
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
        self.timesfm_url = "http://timesfm-api-service:8000"
        self.patchtst_url = "http://patchtst-api-service:8001"
        self.forecast_history: Dict[str, List[Dict[str, Any]]] = {}
        self.accuracy_metrics: Dict[str, Dict[str, float]] = {}

    def _get_forecasting_system_prompt(self) -> str:
        """Get system prompt for forecasting agent."""
        return """You are a Time Series Forecasting Specialist in a multi-agent trading system.

Your expertise:
1. TimesFM: Google foundation model for time series
   - Short to medium-term forecasting (24-96 hours)
   - Excellent at capturing market regimes
   - Fast inference, good for real-time updates

2. PatchTST: Patch-based Transformer
   - Long-horizon forecasting (96+ hours)
   - Captures complex temporal patterns
   - Better for structural breaks and transitions
   - Handles multivariate data well

3. Ensemble Methods
   - Confidence-weighted averaging
   - Consensus scoring
   - Model disagreement analysis
   - Risk assessment from forecast spread

Your responsibilities:
- Prepare OHLCV + technical indicator data for models
- Call both TimesFM and PatchTST with appropriate horizons
- Compare and ensemble predictions
- Detect forecast divergence (warning signal)
- Generate trading signals from ensemble
- Track forecast accuracy for model weighting
- Alert when models disagree significantly

Key insights:
- TimesFM good for immediate structure (next 24h)
- PatchTST good for medium-term trajectory (next week)
- Large disagreement = uncertainty = reduce position size
- Both models bullish = high confidence buy
- Both models bearish = high confidence sell
- Model flip = potential reversal coming

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

    async def call_timesfm(
        self,
        symbol: str,
        timeframe: str,
        ohlcv_data: List[Dict[str, Any]],
        atr_values: List[float],
        adr_values: List[float],
        session_codes: List[int],
        prediction_length: int = 96
    ) -> Dict[str, Any]:
        """
        Call TimesFM model for forecasting.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe for analysis
            ohlcv_data: OHLCV data
            atr_values: ATR values
            adr_values: ADR values
            session_codes: Session codes
            prediction_length: Steps to forecast

        Returns:
            Forecast result from TimesFM
        """
        try:
            # Prepare request
            prep = await self.prepare_forecast_request(
                symbol, timeframe, ohlcv_data, atr_values, adr_values,
                session_codes, normalize=True
            )

            if not prep.get("success"):
                return {"error": f"Data prep failed: {prep.get('error')}"}

            payload = prep["payload"]
            payload["prediction_length"] = prediction_length
            payload["freq"] = "1h"

            # Call API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.timesfm_url}/predict",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        result["model"] = "timesfm"
                        result["call_timestamp"] = datetime.utcnow().isoformat()
                        return result
                    else:
                        error = await response.text()
                        return {
                            "error": f"TimesFM API error {response.status}: {error}",
                            "model": "timesfm"
                        }

        except asyncio.TimeoutError:
            return {"error": "TimesFM request timeout", "model": "timesfm"}
        except Exception as e:
            return {"error": f"TimesFM call failed: {str(e)}", "model": "timesfm"}

    async def call_patchtst(
        self,
        symbol: str,
        timeframe: str,
        ohlcv_data: List[Dict[str, Any]],
        atr_values: List[float],
        adr_values: List[float],
        session_codes: List[int],
        pred_len: int = 96,
        patch_len: int = 16,
        stride: int = 8
    ) -> Dict[str, Any]:
        """
        Call PatchTST model for long-horizon forecasting.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe for analysis
            ohlcv_data: OHLCV data
            atr_values: ATR values
            adr_values: ADR values
            session_codes: Session codes
            pred_len: Prediction length
            patch_len: Patch length
            stride: Stride for patches

        Returns:
            Forecast result from PatchTST
        """
        try:
            # Prepare request
            prep = await self.prepare_forecast_request(
                symbol, timeframe, ohlcv_data, atr_values, adr_values,
                session_codes, normalize=True
            )

            if not prep.get("success"):
                return {"error": f"Data prep failed: {prep.get('error')}"}

            payload = prep["payload"]
            payload["pred_len"] = pred_len
            payload["patch_len"] = patch_len
            payload["stride"] = stride

            # Call API
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.patchtst_url}/predict",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)  # Longer timeout
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        result["model"] = "patchtst"
                        result["call_timestamp"] = datetime.utcnow().isoformat()
                        return result
                    else:
                        error = await response.text()
                        return {
                            "error": f"PatchTST API error {response.status}: {error}",
                            "model": "patchtst"
                        }

        except asyncio.TimeoutError:
            return {"error": "PatchTST request timeout", "model": "patchtst"}
        except Exception as e:
            return {"error": f"PatchTST call failed: {str(e)}", "model": "patchtst"}

    async def ensemble_forecasts(
        self,
        timesfm_result: Dict[str, Any],
        patchtst_result: Dict[str, Any],
        symbol: str,
        current_price: float
    ) -> Dict[str, Any]:
        """
        Create ensemble forecast from both models.

        Args:
            timesfm_result: TimesFM forecast
            patchtst_result: PatchTST forecast
            symbol: Trading symbol
            current_price: Current price

        Returns:
            Ensemble forecast with confidence weighting
        """
        try:
            timesfm_forecast = timesfm_result.get("forecast", [])
            patchtst_forecast = patchtst_result.get("forecast", [])

            if not timesfm_forecast or not patchtst_forecast:
                return {"error": "One or both models failed to generate forecasts"}

            # Get confidence scores
            timesfm_conf = timesfm_result.get("confidence", 50) / 100
            patchtst_conf = patchtst_result.get("confidence", 50) / 100

            # Normalize confidence scores
            total_conf = timesfm_conf + patchtst_conf
            timesfm_weight = timesfm_conf / total_conf if total_conf > 0 else 0.5
            patchtst_weight = patchtst_conf / total_conf if total_conf > 0 else 0.5

            # Align forecasts to same length (use shorter)
            min_len = min(len(timesfm_forecast), len(patchtst_forecast))
            timesfm_f = timesfm_forecast[:min_len]
            patchtst_f = patchtst_forecast[:min_len]

            # Weighted ensemble
            ensemble = [
                tf * timesfm_weight + pf * patchtst_weight
                for tf, pf in zip(timesfm_f, patchtst_f)
            ]

            # Calculate disagreement (divergence warning)
            disagreement = [
                abs(tf - pf) for tf, pf in zip(timesfm_f, patchtst_f)
            ]
            avg_disagreement = sum(disagreement) / len(disagreement) if disagreement else 0
            max_disagreement = max(disagreement) if disagreement else 0

            # Generate signal
            ensemble_direction = "bullish" if ensemble[-1] > current_price else "bearish"
            timesfm_direction = "bullish" if timesfm_f[-1] > current_price else "bearish"
            patchtst_direction = "bullish" if patchtst_f[-1] > current_price else "bearish"

            # Consensus level
            if ensemble_direction == timesfm_direction == patchtst_direction:
                consensus = "strong"
                consensus_confidence = 0.9
            elif (ensemble_direction == timesfm_direction or
                  ensemble_direction == patchtst_direction):
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
                "timesfm_forecast": timesfm_f,
                "timesfm_direction": timesfm_direction,
                "timesfm_target": timesfm_f[-1] if timesfm_f else current_price,
                "patchtst_forecast": patchtst_f,
                "patchtst_direction": patchtst_direction,
                "patchtst_target": patchtst_f[-1] if patchtst_f else current_price,
                "weights": {
                    "timesfm": float(timesfm_weight),
                    "patchtst": float(patchtst_weight),
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
        current_price: float
    ) -> Dict[str, Any]:
        """
        Generate ensemble forecast for a symbol.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe for analysis
            ohlcv_data: OHLCV data
            atr_values: ATR values
            adr_values: ADR values
            session_codes: Session codes
            current_price: Current market price

        Returns:
            Complete ensemble forecast with signals
        """
        try:
            # Call both models in parallel
            timesfm_task = self.call_timesfm(
                symbol, timeframe, ohlcv_data, atr_values, adr_values,
                session_codes, prediction_length=96
            )
            patchtst_task = self.call_patchtst(
                symbol, timeframe, ohlcv_data, atr_values, adr_values,
                session_codes, pred_len=96
            )

            import asyncio
            timesfm_result, patchtst_result = await asyncio.gather(
                timesfm_task, patchtst_task
            )

            # Check for errors
            if "error" in timesfm_result and "error" in patchtst_result:
                return {
                    "error": "Both models failed",
                    "symbol": symbol,
                    "timesfm_error": timesfm_result["error"],
                    "patchtst_error": patchtst_result["error"]
                }

            # Ensemble the forecasts
            ensemble = await self.ensemble_forecasts(
                timesfm_result, patchtst_result, symbol, current_price
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
