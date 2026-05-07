"""
Forecaster Tool

Provides forecasting capabilities for agents using various time series methods.
"""

import numpy as np
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class ForecastResult:
    """Result from forecasting"""
    forecast_values: List[float]
    forecast_dates: List[datetime]
    lower_bound: List[float]
    upper_bound: List[float]
    method: str
    confidence: float
    metrics: Dict[str, float]


class ForecasterTool:
    """Tool for time series forecasting"""

    def __init__(self):
        self.default_confidence = 0.95
        self.min_data_points = 10

    def forecast(
        self,
        values: List[float],
        timestamps: List[datetime],
        periods: int = 7,
        method: str = "auto"
    ) -> ForecastResult:
        """Generate forecast using best available method"""

        if len(values) < self.min_data_points:
            raise ValueError(f"Need at least {self.min_data_points} data points for forecasting")

        if len(values) != len(timestamps):
            raise ValueError("Values and timestamps must have same length")

        # Select method
        if method == "auto":
            method = self._select_method(values)

        # Generate forecast
        if method == "prophet":
            return self._forecast_prophet(values, timestamps, periods)
        elif method == "linear":
            return self._forecast_linear(values, timestamps, periods)
        elif method == "exponential_smoothing":
            return self._forecast_exponential_smoothing(values, timestamps, periods)
        elif method == "moving_average":
            return self._forecast_moving_average(values, timestamps, periods)
        else:
            return self._forecast_linear(values, timestamps, periods)

    def _select_method(self, values: List[float]) -> str:
        """Select best forecasting method based on data characteristics"""
        # Check for seasonality
        if len(values) >= 50:
            return "prophet"
        elif self._has_trend(values):
            return "linear"
        else:
            return "exponential_smoothing"

    def _has_trend(self, values: List[float]) -> bool:
        """Check if data has a significant trend"""
        x = np.arange(len(values))
        y = np.array(values)

        # Simple linear regression
        slope = np.polyfit(x, y, 1)[0]

        # Check if slope is significant relative to data scale
        data_range = np.max(y) - np.min(y)
        return abs(slope * len(values)) > 0.1 * data_range if data_range > 0 else False

    def _forecast_prophet(
        self,
        values: List[float],
        timestamps: List[datetime],
        periods: int
    ) -> ForecastResult:
        """Forecast using Facebook Prophet"""
        try:
            from prophet import Prophet
        except ImportError:
            # Fall back to linear if Prophet not available
            return self._forecast_linear(values, timestamps, periods)

        # Prepare data
        df_data = {
            "ds": timestamps,
            "y": values,
        }

        # Fit model
        model = Prophet(
            interval_width=0.95,
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=len(values) > 365,
        )
        model.fit(df_data)

        # Make future dataframe
        future = model.make_future_dataframe(periods=periods)
        forecast = model.predict(future)

        # Extract forecast values
        forecast_values = forecast["yhat"][-periods:].tolist()
        lower_bound = forecast["yhat_lower"][-periods:].tolist()
        upper_bound = forecast["yhat_upper"][-periods:].tolist()
        forecast_dates = forecast["ds"][-periods:].dt.to_pydatetime().tolist()

        # Calculate metrics
        residuals = np.array(values) - np.array(forecast["yhat"][:len(values)].tolist())
        mae = np.mean(np.abs(residuals))
        rmse = np.sqrt(np.mean(residuals ** 2))

        return ForecastResult(
            forecast_values=forecast_values,
            forecast_dates=forecast_dates,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            method="prophet",
            confidence=0.95,
            metrics={
                "mae": float(mae),
                "rmse": float(rmse),
                "mape": float(np.mean(np.abs(residuals / np.array(values))) * 100),
            }
        )

    def _forecast_linear(
        self,
        values: List[float],
        timestamps: List[datetime],
        periods: int
    ) -> ForecastResult:
        """Forecast using linear regression"""
        x = np.arange(len(values))
        y = np.array(values)

        # Fit polynomial (degree 1 for linear)
        coefficients = np.polyfit(x, y, 1)
        trend_line = np.poly1d(coefficients)

        # Generate forecast
        forecast_x = np.arange(len(values), len(values) + periods)
        forecast_values = trend_line(forecast_x).tolist()

        # Calculate confidence intervals
        residuals = y - trend_line(x)
        std_error = np.std(residuals)

        # 95% confidence interval
        z_score = 1.96
        upper_bound = (forecast_values + z_score * std_error).tolist()
        lower_bound = (forecast_values - z_score * std_error).tolist()

        # Generate forecast dates
        last_date = timestamps[-1]
        interval = (timestamps[-1] - timestamps[-2]) if len(timestamps) > 1 else timedelta(days=1)
        forecast_dates = [last_date + interval * (i + 1) for i in range(periods)]

        # Calculate metrics
        mae = float(np.mean(np.abs(residuals)))
        rmse = float(np.sqrt(np.mean(residuals ** 2)))

        return ForecastResult(
            forecast_values=forecast_values,
            forecast_dates=forecast_dates,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            method="linear_regression",
            confidence=0.95,
            metrics={"mae": mae, "rmse": rmse}
        )

    def _forecast_exponential_smoothing(
        self,
        values: List[float],
        timestamps: List[datetime],
        periods: int
    ) -> ForecastResult:
        """Forecast using exponential smoothing"""
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
        except ImportError:
            return self._forecast_linear(values, timestamps, periods)

        y = np.array(values)

        # Fit model
        model = ExponentialSmoothing(
            y,
            trend="add",
            seasonal=None,
            damped_trend=True,
        ).fit()

        # Forecast
        forecast_result = model.forecast(steps=periods)
        forecast_values = forecast_result.tolist()

        # Simple confidence intervals (based on residuals)
        residuals = model.resid
        std_error = np.std(residuals)
        z_score = 1.96

        upper_bound = (np.array(forecast_values) + z_score * std_error).tolist()
        lower_bound = (np.array(forecast_values) - z_score * std_error).tolist()

        # Generate forecast dates
        last_date = timestamps[-1]
        interval = (timestamps[-1] - timestamps[-2]) if len(timestamps) > 1 else timedelta(days=1)
        forecast_dates = [last_date + interval * (i + 1) for i in range(periods)]

        # Calculate metrics
        mae = float(np.mean(np.abs(residuals)))
        rmse = float(np.sqrt(np.mean(residuals ** 2)))

        return ForecastResult(
            forecast_values=forecast_values,
            forecast_dates=forecast_dates,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            method="exponential_smoothing",
            confidence=0.95,
            metrics={"mae": mae, "rmse": rmse}
        )

    def _forecast_moving_average(
        self,
        values: List[float],
        timestamps: List[datetime],
        periods: int
    ) -> ForecastResult:
        """Forecast using moving average"""
        window = min(7, len(values) // 2)

        # Calculate moving average
        ma = np.convolve(values, np.ones(window) / window, mode='valid')

        # Forecast is the last moving average value
        last_ma = ma[-1]
        forecast_values = [last_ma] * periods

        # Calculate residuals for confidence intervals
        aligned_values = values[window - 1:]
        residuals = np.array(aligned_values) - ma
        std_error = np.std(residuals)

        z_score = 1.96
        upper_bound = [last_ma + z_score * std_error] * periods
        lower_bound = [last_ma - z_score * std_error] * periods

        # Generate forecast dates
        last_date = timestamps[-1]
        interval = (timestamps[-1] - timestamps[-2]) if len(timestamps) > 1 else timedelta(days=1)
        forecast_dates = [last_date + interval * (i + 1) for i in range(periods)]

        return ForecastResult(
            forecast_values=forecast_values,
            forecast_dates=forecast_dates,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            method=f"moving_average_{window}",
            confidence=0.95,
            metrics={"mae": float(np.mean(np.abs(residuals))), "rmse": float(np.sqrt(np.mean(residuals ** 2)))}
        )

    def detect_anomalies_in_forecast(
        self,
        actual: List[float],
        forecast: List[float],
        threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Detect anomalies where actual values deviate significantly from forecast"""
        if len(actual) != len(forecast):
            raise ValueError("Actual and forecast must have same length")

        anomalies = []

        for i, (act, fc) in enumerate(zip(actual, forecast)):
            if fc != 0:
                percent_error = abs((act - fc) / fc) * 100
            else:
                percent_error = 0

            # Simple threshold-based detection
            if abs(act - fc) > threshold * np.std([abs(a - f) for a, f in zip(actual, forecast)]):
                anomalies.append({
                    "index": i,
                    "actual": act,
                    "forecast": fc,
                    "deviation": act - fc,
                    "percent_error": round(percent_error, 2),
                    "severity": self._classify_anomaly_severity(percent_error),
                })

        return anomalies

    def _classify_anomaly_severity(self, percent_error: float) -> str:
        """Classify anomaly severity"""
        if percent_error < 10:
            return "low"
        elif percent_error < 25:
            return "medium"
        elif percent_error < 50:
            return "high"
        else:
            return "critical"
