"""ARIMA/SARIMA Forecasting Service - Univariate Time Series Models.

Provides ARIMA and SARIMA forecasting with auto-parameter detection,
stationarity testing, and ensemble forecasting capabilities.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
import logging
from datetime import datetime

# Try to import statsmodels, fall back gracefully
try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    from statsmodels.tsa.stattools import adfuller, kpss
    from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelType(Enum):
    """ARIMA model variants."""
    ARIMA = "arima"
    SARIMA = "sarima"
    AUTO = "auto"


class StationarityResult(Enum):
    """Stationarity test results."""
    STATIONARY = "stationary"
    NON_STATIONARY = "non_stationary"
    UNCLEAR = "unclear"


@dataclass
class StationarityTest:
    """Stationarity test result."""
    adf_statistic: float
    adf_pvalue: float
    adf_critical_values: Dict[str, float]
    adf_result: StationarityResult
    kpss_statistic: float
    kpss_pvalue: float
    kpss_critical_values: Dict[str, float]
    kpss_result: StationarityResult
    differencing_needed: int


@dataclass
class ARIMAParameters:
    """ARIMA/SARIMA parameters (p, d, q) and (P, D, Q, s) for seasonal."""
    p: int
    d: int
    q: int
    P: Optional[int] = None
    D: Optional[int] = None
    Q: Optional[int] = None
    s: Optional[int] = None
    is_seasonal: bool = False


@dataclass
class ForecastResult:
    """Result from ARIMA forecast."""
    symbol: str
    timestamp: str
    forecast: List[float]
    forecast_std: List[float]
    confidence_intervals_95: Tuple[List[float], List[float]]
    confidence_intervals_80: Tuple[List[float], List[float]]
    model_type: str
    parameters: Dict[str, Any]
    metrics: Dict[str, float]
    stationarity_info: Optional[StationarityTest] = None


class ARIMAService:
    """ARIMA/SARIMA forecasting service."""

    def __init__(self):
        """Initialize ARIMA service."""
        if not STATSMODELS_AVAILABLE:
            logger.warning(
                "statsmodels not installed. Install with: "
                "pip install statsmodels"
            )
        self.models_cache = {}

    async def forecast(
        self,
        symbol: str,
        timeseries: List[float],
        steps: int = 10,
        model_type: ModelType = ModelType.AUTO,
        confidence_level: float = 0.95,
        parameters: Optional[ARIMAParameters] = None,
        seasonal_period: int = 12,
    ) -> ForecastResult:
        """
        Forecast time series using ARIMA/SARIMA.

        Args:
            symbol: Trading symbol
            timeseries: Historical price/value series
            steps: Number of steps to forecast
            model_type: ARIMA, SARIMA, or AUTO
            confidence_level: Confidence level for intervals (0.80 or 0.95)
            parameters: Explicit ARIMA(P,D,Q) parameters if available
            seasonal_period: Seasonal period (default 12 for monthly in annual data)

        Returns:
            ForecastResult with predictions and confidence intervals
        """
        if not STATSMODELS_AVAILABLE:
            return self._mock_forecast(symbol, timeseries, steps)

        try:
            ts_array = np.array(timeseries, dtype=np.float64)

            # Auto-detect parameters if not provided
            if parameters is None:
                parameters = await self._auto_detect_parameters(
                    ts_array, model_type, seasonal_period
                )

            # Build and fit model
            if parameters.is_seasonal and model_type != ModelType.ARIMA:
                # Use SARIMA for seasonal data
                model = SARIMAX(
                    ts_array,
                    order=(parameters.p, parameters.d, parameters.q),
                    seasonal_order=(
                        parameters.P,
                        parameters.D,
                        parameters.Q,
                        parameters.s,
                    ),
                )
            else:
                # Use ARIMA
                model = ARIMA(ts_array, order=(parameters.p, parameters.d, parameters.q))

            # Fit model
            results = model.fit()

            # Generate forecast
            forecast_result = results.get_forecast(steps=steps)
            forecast_mean = forecast_result.predicted_mean.values
            forecast_std = forecast_result.se_mean.values

            # Calculate confidence intervals
            ci_95 = forecast_result.conf_int(alpha=1 - confidence_level if confidence_level == 0.95 else 0.05)
            ci_80 = forecast_result.conf_int(alpha=0.20)

            return ForecastResult(
                symbol=symbol,
                timestamp=datetime.utcnow().isoformat(),
                forecast=forecast_mean.tolist(),
                forecast_std=forecast_std.tolist(),
                confidence_intervals_95=(
                    ci_95.iloc[:, 0].tolist(),
                    ci_95.iloc[:, 1].tolist(),
                ),
                confidence_intervals_80=(
                    ci_80.iloc[:, 0].tolist(),
                    ci_80.iloc[:, 1].tolist(),
                ),
                model_type=parameters.is_seasonal and "SARIMA" or "ARIMA",
                parameters={
                    "p": parameters.p,
                    "d": parameters.d,
                    "q": parameters.q,
                    "P": parameters.P,
                    "D": parameters.D,
                    "Q": parameters.Q,
                    "s": parameters.s,
                    "is_seasonal": parameters.is_seasonal,
                },
                metrics={
                    "aic": float(results.aic),
                    "bic": float(results.bic),
                    "rmse": float(np.sqrt(np.mean((results.resid) ** 2))),
                },
            )

        except Exception as e:
            logger.error(f"ARIMA forecast failed for {symbol}: {e}")
            raise

    async def ensemble_forecast(
        self,
        symbol: str,
        timeseries: List[float],
        steps: int = 10,
        models_to_use: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Ensemble forecast combining multiple ARIMA variants.

        Args:
            symbol: Trading symbol
            timeseries: Historical series
            steps: Forecast steps
            models_to_use: List of model types ("arima", "sarima_12", "sarima_4")

        Returns:
            Dictionary with ensemble forecast and individual model results
        """
        if models_to_use is None:
            models_to_use = ["arima", "sarima_12"]

        ensemble_results = {}
        forecasts = []

        # Run multiple models
        for model_name in models_to_use:
            try:
                if model_name == "arima":
                    result = await self.forecast(
                        symbol, timeseries, steps, ModelType.ARIMA
                    )
                elif model_name.startswith("sarima"):
                    # Extract seasonal period from name (e.g., "sarima_12")
                    seasonal = int(model_name.split("_")[1]) if "_" in model_name else 12
                    result = await self.forecast(
                        symbol, timeseries, steps, ModelType.SARIMA,
                        seasonal_period=seasonal
                    )
                else:
                    continue

                ensemble_results[model_name] = result
                forecasts.append(result.forecast)

            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}")

        # Calculate ensemble average
        if forecasts:
            ensemble_forecast = np.mean(forecasts, axis=0).tolist()
            ensemble_std = np.std(forecasts, axis=0).tolist()
        else:
            raise ValueError("No models produced valid forecasts")

        return {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "ensemble_forecast": ensemble_forecast,
            "ensemble_std": ensemble_std,
            "individual_models": ensemble_results,
            "num_models": len(ensemble_results),
            "summary": f"Ensemble of {len(ensemble_results)} models",
        }

    async def test_stationarity(
        self, timeseries: List[float]
    ) -> StationarityTest:
        """
        Test time series for stationarity using ADF and KPSS tests.

        Args:
            timeseries: Time series to test

        Returns:
            StationarityTest with results from both tests
        """
        if not STATSMODELS_AVAILABLE:
            return self._mock_stationarity_test(timeseries)

        try:
            ts_array = np.array(timeseries, dtype=np.float64)

            # ADF test (null: non-stationary)
            adf_result = adfuller(ts_array, autolag="AIC")
            adf_stat = adf_result[0]
            adf_pval = adf_result[1]
            adf_crit = {key: adf_result[4][key] for key in adf_result[4].keys()}
            adf_is_stationary = adf_pval < 0.05

            # KPSS test (null: stationary)
            kpss_result = kpss(ts_array, regression="c", nlags="auto")
            kpss_stat = kpss_result[0]
            kpss_pval = kpss_result[1]
            kpss_crit = {key: kpss_result[3][key] for key in kpss_result[3].keys()}
            kpss_is_stationary = kpss_pval > 0.05

            # Determine overall stationarity and differencing needed
            if adf_is_stationary and kpss_is_stationary:
                overall_stationarity = StationarityResult.STATIONARY
                differencing_needed = 0
            elif not adf_is_stationary and not kpss_is_stationary:
                overall_stationarity = StationarityResult.NON_STATIONARY
                differencing_needed = 1
            else:
                overall_stationarity = StationarityResult.UNCLEAR
                differencing_needed = 1

            return StationarityTest(
                adf_statistic=float(adf_stat),
                adf_pvalue=float(adf_pval),
                adf_critical_values={str(k): float(v) for k, v in adf_crit.items()},
                adf_result=StationarityResult.STATIONARY if adf_is_stationary else StationarityResult.NON_STATIONARY,
                kpss_statistic=float(kpss_stat),
                kpss_pvalue=float(kpss_pval),
                kpss_critical_values={str(k): float(v) for k, v in kpss_crit.items()},
                kpss_result=StationarityResult.STATIONARY if kpss_is_stationary else StationarityResult.NON_STATIONARY,
                differencing_needed=differencing_needed,
            )

        except Exception as e:
            logger.error(f"Stationarity test failed: {e}")
            raise

    async def _auto_detect_parameters(
        self,
        timeseries: np.ndarray,
        model_type: ModelType,
        seasonal_period: int = 12,
    ) -> ARIMAParameters:
        """
        Auto-detect ARIMA/SARIMA parameters using grid search.

        Args:
            timeseries: Time series data
            model_type: Model type to use
            seasonal_period: Seasonal period

        Returns:
            ARIMAParameters with optimal p, d, q values
        """
        # Test stationarity to determine d
        stationarity = await self.test_stationarity(timeseries.tolist())
        d = stationarity.differencing_needed

        if model_type == ModelType.AUTO:
            # Determine if seasonal
            is_seasonal = len(timeseries) >= seasonal_period * 2
            model_type = ModelType.SARIMA if is_seasonal else ModelType.ARIMA

        # Simple grid search (simplified for demo - production would be more thorough)
        best_score = float("inf")
        best_params = ARIMAParameters(p=1, d=d, q=1)

        # Search p and q values
        for p in range(0, 3):
            for q in range(0, 3):
                try:
                    if model_type == ModelType.SARIMA:
                        # For SARIMA, also search seasonal parameters
                        model = SARIMAX(
                            timeseries,
                            order=(p, d, q),
                            seasonal_order=(1, 0, 1, seasonal_period),
                        )
                        results = model.fit(disp=False, maxiter=200)
                        score = results.aic

                        if score < best_score:
                            best_score = score
                            best_params = ARIMAParameters(
                                p=p,
                                d=d,
                                q=q,
                                P=1,
                                D=0,
                                Q=1,
                                s=seasonal_period,
                                is_seasonal=True,
                            )
                    else:
                        # ARIMA
                        model = ARIMA(timeseries, order=(p, d, q))
                        results = model.fit()
                        score = results.aic

                        if score < best_score:
                            best_score = score
                            best_params = ARIMAParameters(
                                p=p, d=d, q=q, is_seasonal=False
                            )

                except Exception:
                    continue

        logger.info(
            f"Auto-detected ARIMA parameters: {best_params} (AIC: {best_score:.2f})"
        )
        return best_params

    def _mock_forecast(
        self, symbol: str, timeseries: List[float], steps: int
    ) -> ForecastResult:
        """Mock forecast when statsmodels not available."""
        ts_array = np.array(timeseries)
        last_val = ts_array[-1]
        trend = (ts_array[-1] - ts_array[-20]) / 20 if len(ts_array) > 20 else 0

        forecast = [last_val + trend * (i + 1) for i in range(steps)]
        forecast_std = [abs(trend) * 0.1 for _ in range(steps)]

        ci_95_upper = [f + 1.96 * s for f, s in zip(forecast, forecast_std)]
        ci_95_lower = [f - 1.96 * s for f, s in zip(forecast, forecast_std)]
        ci_80_upper = [f + 1.28 * s for f, s in zip(forecast, forecast_std)]
        ci_80_lower = [f - 1.28 * s for f, s in zip(forecast, forecast_std)]

        return ForecastResult(
            symbol=symbol,
            timestamp=datetime.utcnow().isoformat(),
            forecast=forecast,
            forecast_std=forecast_std,
            confidence_intervals_95=(ci_95_lower, ci_95_upper),
            confidence_intervals_80=(ci_80_lower, ci_80_upper),
            model_type="ARIMA_MOCK",
            parameters={"p": 1, "d": 1, "q": 1},
            metrics={"aic": 0, "bic": 0, "rmse": 0},
        )

    def _mock_stationarity_test(
        self, timeseries: List[float]
    ) -> StationarityTest:
        """Mock stationarity test when statsmodels not available."""
        return StationarityTest(
            adf_statistic=-2.5,
            adf_pvalue=0.10,
            adf_critical_values={"1%": -3.43, "5%": -2.86, "10%": -2.57},
            adf_result=StationarityResult.UNCLEAR,
            kpss_statistic=0.35,
            kpss_pvalue=0.10,
            kpss_critical_values={"1%": 0.739, "5%": 0.463, "10%": 0.347},
            kpss_result=StationarityResult.UNCLEAR,
            differencing_needed=1,
        )
