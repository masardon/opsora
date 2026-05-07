"""
Analyzer Tool

Provides statistical analysis capabilities for agents.
"""

import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import polars as pl


@dataclass
class AnalysisResult:
    """Result from statistical analysis"""
    metric: str
    statistic: str
    value: float
    interpretation: str
    confidence: float
    metadata: Dict[str, Any]


class AnalyzerTool:
    """Tool for performing statistical analyses"""

    def __init__(self):
        self.confidence_level = 0.95

    def calculate_growth_rate(
        self,
        values: List[float],
        periods: int = 1
    ) -> Dict[str, float]:
        """Calculate growth rate over periods"""
        if len(values) < 2:
            return {"growth_rate": 0.0, "method": "insufficient_data"}

        # Simple period-over-period growth
        if len(values) >= periods + 1:
            current = values[-1]
            previous = values[-(periods + 1)]
            if previous != 0:
                growth_rate = ((current - previous) / previous) * 100
            else:
                growth_rate = 0.0
            method = "period_over_period"
        else:
            # Use all available data
            first = values[0]
            last = values[-1]
            if first != 0:
                growth_rate = ((last - first) / first) * 100
            else:
                growth_rate = 0.0
            method = "full_period"

        return {
            "growth_rate": round(growth_rate, 2),
            "method": method,
        }

    def detect_trend(
        self,
        values: List[float],
        timestamps: Optional[List[datetime]] = None
    ) -> Dict[str, Any]:
        """Detect trend direction and strength"""
        if len(values) < 3:
            return {
                "trend": "unknown",
                "strength": 0.0,
                "confidence": 0.0,
            }

        # Linear regression to detect trend
        x = np.arange(len(values))
        y = np.array(values)

        # Calculate slope
        slope = np.polyfit(x, y, 1)[0]

        # Calculate R-squared
        y_mean = np.mean(y)
        ss_tot = np.sum((y - y_mean) ** 2)
        y_pred = np.polyval(np.polyfit(x, y, 1), x)
        ss_res = np.sum((y - y_pred) ** 2)

        if ss_tot > 0:
            r_squared = 1 - (ss_res / ss_tot)
        else:
            r_squared = 0.0

        # Determine trend
        if abs(slope) < 0.01 * np.mean(np.abs(y)):
            trend = "stable"
        elif slope > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        # Strength based on R-squared and slope magnitude
        strength = min(abs(r_squared) * 100, 100)

        return {
            "trend": trend,
            "slope": float(slope),
            "r_squared": float(r_squared),
            "strength": round(strength, 2),
            "confidence": round(min(abs(r_squared) + 0.5, 1.0), 2),
        }

    def calculate_moving_average(
        self,
        values: List[float],
        window: int = 7
    ) -> List[float]:
        """Calculate moving average"""
        if len(values) < window:
            return [sum(values) / len(values)] if values else []

        ma = []
        for i in range(len(values) - window + 1):
            ma.append(sum(values[i:i + window]) / window)

        return ma

    def detect_outliers(
        self,
        values: List[float],
        method: str = "iqr",
        threshold: float = 1.5
    ) -> Dict[str, Any]:
        """Detect outliers in data"""
        if len(values) < 4:
            return {"outliers": [], "count": 0, "indices": []}

        values_array = np.array(values)

        if method == "iqr":
            # Interquartile range method
            q1 = np.percentile(values_array, 25)
            q3 = np.percentile(values_array, 75)
            iqr = q3 - q1

            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr

            outlier_indices = np.where((values_array < lower_bound) | (values_array > upper_bound))[0].tolist()
            outlier_values = [values[i] for i in outlier_indices]

        elif method == "zscore":
            # Z-score method
            mean = np.mean(values_array)
            std = np.std(values_array)

            if std == 0:
                return {"outliers": [], "count": 0, "indices": []}

            z_scores = np.abs((values_array - mean) / std)
            outlier_indices = np.where(z_scores > threshold)[0].tolist()
            outlier_values = [values[i] for i in outlier_indices]

        else:
            return {"outliers": [], "count": 0, "indices": []}

        return {
            "outliers": outlier_values,
            "count": len(outlier_values),
            "indices": outlier_indices,
            "percentage": round(len(outlier_values) / len(values) * 100, 2),
        }

    def compare_to_baseline(
        self,
        current_values: List[float],
        baseline_values: List[float]
    ) -> Dict[str, Any]:
        """Compare current values to baseline"""
        if not current_values or not baseline_values:
            return {"error": "Insufficient data"}

        current_avg = np.mean(current_values)
        baseline_avg = np.mean(baseline_values)

        if baseline_avg != 0:
            percent_change = ((current_avg - baseline_avg) / baseline_avg) * 100
        else:
            percent_change = 0.0

        # Statistical significance (t-test approximation)
        from scipy import stats
        t_stat, p_value = stats.ttest_ind(current_values, baseline_values)

        return {
            "current_average": float(current_avg),
            "baseline_average": float(baseline_avg),
            "absolute_change": float(current_avg - baseline_avg),
            "percent_change": round(percent_change, 2),
            "is_significant": p_value < 0.05,
            "p_value": float(p_value),
            "t_statistic": float(t_stat),
            "interpretation": self._interpret_change(percent_change, p_value),
        }

    def calculate_seasonality(
        self,
        values: List[float],
        timestamps: List[datetime],
        period: str = "weekly"
    ) -> Dict[str, Any]:
        """Analyze seasonal patterns"""
        if len(values) != len(timestamps) or len(values) < 14:
            return {"error": "Insufficient data for seasonality analysis"}

        df = pl.DataFrame({
            "timestamp": timestamps,
            "value": values,
        })

        if period == "daily":
            df = df.with_columns(
                pl.col("timestamp").dt.day().alias("period")
            )
        elif period == "weekly":
            df = df.with_columns(
                pl.col("timestamp").dt.weekday().alias("period")
            )
        elif period == "monthly":
            df = df.with_columns(
                pl.col("timestamp").dt.month().alias("period")
            )
        else:
            return {"error": f"Unknown period: {period}"}

        # Calculate average by period
        period_stats = df.group_by("period").agg(
            pl.col("value").mean().alias("avg_value"),
            pl.col("value").count().alias("count"),
        ).sort("period")

        overall_avg = df["value"].mean()

        # Calculate seasonal index
        result = []
        for row in period_stats.iter_rows(named=True):
            seasonal_index = (row["avg_value"] / overall_avg - 1) * 100
            result.append({
                "period": int(row["period"]),
                "average_value": float(row["avg_value"]),
                "sample_count": int(row["count"]),
                "seasonal_index": round(seasonal_index, 2),
            })

        return {
            "period_type": period,
            "overall_average": float(overall_avg),
            "seasonal_patterns": result,
        }

    def calculate_correlation(
        self,
        x_values: List[float],
        y_values: List[float]
    ) -> Dict[str, Any]:
        """Calculate correlation between two variables"""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return {"error": "Invalid input data"}

        from scipy import stats

        correlation, p_value = stats.pearsonr(x_values, y_values)

        return {
            "correlation_coefficient": float(correlation),
            "p_value": float(p_value),
            "is_significant": p_value < 0.05,
            "strength": self._interpret_correlation(abs(correlation)),
            "direction": "positive" if correlation > 0 else "negative",
        }

    def forecast_simple(
        self,
        values: List[float],
        periods: int = 7
    ) -> Dict[str, Any]:
        """Simple linear forecast"""
        if len(values) < 2:
            return {"error": "Insufficient data"}

        x = np.arange(len(values))
        y = np.array(values)

        # Fit linear regression
        coefficients = np.polyfit(x, y, 1)
        trend_line = np.poly1d(coefficients)

        # Generate forecast
        forecast_x = np.arange(len(values), len(values) + periods)
        forecast_values = trend_line(forecast_x)

        # Calculate confidence intervals (simplified)
        residuals = y - trend_line(x)
        std_error = np.std(residuals)

        upper_bound = forecast_values + 1.96 * std_error
        lower_bound = forecast_values - 1.96 * std_error

        return {
            "forecast": [float(v) for v in forecast_values],
            "upper_bound": [float(v) for v in upper_bound],
            "lower_bound": [float(v) for v in lower_bound],
            "trend_slope": float(coefficients[0]),
            "method": "linear_regression",
        }

    def _interpret_change(
        self,
        percent_change: float,
        p_value: float
    ) -> str:
        """Interpret the magnitude and significance of change"""
        if p_value >= 0.05:
            return "not statistically significant"

        abs_change = abs(percent_change)

        if abs_change < 5:
            magnitude = "minimal"
        elif abs_change < 15:
            magnitude = "moderate"
        elif abs_change < 30:
            magnitude = "significant"
        else:
            magnitude = "substantial"

        direction = "increase" if percent_change > 0 else "decrease"

        return f"{magnitude} {direction}"

    def _interpret_correlation(self, r: float) -> str:
        """Interpret correlation strength"""
        if r < 0.1:
            return "negligible"
        elif r < 0.3:
            return "weak"
        elif r < 0.5:
            return "moderate"
        elif r < 0.7:
            return "strong"
        else:
            return "very strong"

    def generate_summary_stats(
        self,
        data: List[float]
    ) -> Dict[str, float]:
        """Generate comprehensive summary statistics"""
        if not data:
            return {}

        arr = np.array(data)

        return {
            "count": len(data),
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "mode": float(np.argmax(np.bincount(arr.astype(int)))) if arr.dtype.kind in 'iu' else None,
            "std": float(np.std(arr)),
            "variance": float(np.var(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "range": float(np.max(arr) - np.min(arr)),
            "q1": float(np.percentile(arr, 25)),
            "q3": float(np.percentile(arr, 75)),
            "iqr": float(np.percentile(arr, 75) - np.percentile(arr, 25)),
            "skewness": float(self._calculate_skewness(arr)),
            "coefficient_of_variation": float(np.std(arr) / np.mean(arr)) if np.mean(arr) != 0 else 0,
        }

    def _calculate_skewness(self, arr: np.ndarray) -> float:
        """Calculate skewness"""
        from scipy import stats
        return stats.skew(arr)
