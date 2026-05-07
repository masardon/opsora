"""
Anomaly Detector Tool

Provides anomaly detection capabilities using various statistical and ML methods.
"""

import numpy as np
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum


class AnomalyMethod(str, Enum):
    """Anomaly detection methods"""
    Z_SCORE = "z_score"
    IQR = "iqr"
    ISOLATION_FOREST = "isolation_forest"
    DBSCAN = "dbscan"
    MOVING_WINDOW = "moving_window"


@dataclass
class Anomaly:
    """Detected anomaly"""
    index: int
    timestamp: Optional[datetime]
    value: float
    expected_value: float
    deviation: float
    score: float
    severity: str  # low, medium, high, critical
    method: str
    context: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "value": self.value,
            "expected_value": self.expected_value,
            "deviation": self.deviation,
            "score": self.score,
            "severity": self.severity,
            "method": self.method,
            "context": self.context or {},
        }


class AnomalyDetectorTool:
    """Tool for detecting anomalies in time series and metrics"""

    def __init__(self):
        self.default_threshold = 2.5
        self.default_window = 7
        self.severity_thresholds = {
            "low": 2.0,
            "medium": 3.0,
            "high": 4.0,
            "critical": 5.0,
        }

    def detect(
        self,
        values: List[float],
        timestamps: Optional[List[datetime]] = None,
        method: AnomalyMethod = AnomalyMethod.Z_SCORE,
        threshold: Optional[float] = None,
        window: Optional[int] = None,
    ) -> List[Anomaly]:
        """Detect anomalies using specified method"""

        threshold = threshold or self.default_threshold
        window = window or self.default_window

        if len(values) < 4:
            return []

        if method == AnomalyMethod.Z_SCORE:
            return self._detect_z_score(values, timestamps, threshold)
        elif method == AnomalyMethod.IQR:
            return self._detect_iqr(values, timestamps, threshold)
        elif method == AnomalyMethod.MOVING_WINDOW:
            return self._detect_moving_window(values, timestamps, window, threshold)
        elif method == AnomalyMethod.ISOLATION_FOREST:
            return self._detect_isolation_forest(values, timestamps)
        elif method == AnomalyMethod.DBSCAN:
            return self._detect_dbscan(values, timestamps)
        else:
            return self._detect_z_score(values, timestamps, threshold)

    def _detect_z_score(
        self,
        values: List[float],
        timestamps: Optional[List[datetime]],
        threshold: float
    ) -> List[Anomaly]:
        """Detect anomalies using z-score method"""
        arr = np.array(values)
        mean = np.mean(arr)
        std = np.std(arr)

        if std == 0:
            return []

        anomalies = []

        for i, value in enumerate(values):
            z_score = abs((value - mean) / std)

            if z_score > threshold:
                anomalies.append(Anomaly(
                    index=i,
                    timestamp=timestamps[i] if timestamps and i < len(timestamps) else None,
                    value=value,
                    expected_value=mean,
                    deviation=value - mean,
                    score=z_score,
                    severity=self._classify_severity(z_score),
                    method="z_score",
                ))

        return anomalies

    def _detect_iqr(
        self,
        values: List[float],
        timestamps: Optional[List[datetime]],
        threshold: float
    ) -> List[Anomaly]:
        """Detect anomalies using interquartile range"""
        arr = np.array(values)
        q1 = np.percentile(arr, 25)
        q3 = np.percentile(arr, 75)
        iqr = q3 - q1

        if iqr == 0:
            return []

        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr

        anomalies = []

        for i, value in enumerate(values):
            if value < lower_bound or value > upper_bound:
                deviation = value - q1 if value < lower_bound else value - q3
                score = abs(deviation) / iqr

                anomalies.append(Anomaly(
                    index=i,
                    timestamp=timestamps[i] if timestamps and i < len(timestamps) else None,
                    value=value,
                    expected_value=q1 if value < lower_bound else q3,
                    deviation=deviation,
                    score=score,
                    severity=self._classify_severity(score),
                    method="iqr",
                    context={"bounds": (lower_bound, upper_bound)},
                ))

        return anomalies

    def _detect_moving_window(
        self,
        values: List[float],
        timestamps: Optional[List[datetime]],
        window: int,
        threshold: float
    ) -> List[Anomaly]:
        """Detect anomalies using moving window statistics"""
        anomalies = []

        for i in range(window, len(values)):
            window_values = values[i - window:i]
            window_mean = np.mean(window_values)
            window_std = np.std(window_values)

            if window_std == 0:
                continue

            value = values[i]
            z_score = abs((value - window_mean) / window_std)

            if z_score > threshold:
                anomalies.append(Anomaly(
                    index=i,
                    timestamp=timestamps[i] if timestamps and i < len(timestamps) else None,
                    value=value,
                    expected_value=window_mean,
                    deviation=value - window_mean,
                    score=z_score,
                    severity=self._classify_severity(z_score),
                    method="moving_window",
                    context={"window_size": window, "window_mean": window_mean},
                ))

        return anomalies

    def _detect_isolation_forest(
        self,
        values: List[float],
        timestamps: Optional[List[datetime]]
    ) -> List[Anomaly]:
        """Detect anomalies using Isolation Forest"""
        try:
            from sklearn.ensemble import IsolationForest
        except ImportError:
            return self._detect_z_score(values, timestamps, self.default_threshold)

        # Reshape data
        arr = np.array(values).reshape(-1, 1)

        # Fit model
        model = IsolationForest(contamination=0.1, random_state=42)
        predictions = model.fit_predict(arr)
        scores = model.score_samples(arr)

        anomalies = []

        for i, (pred, score) in enumerate(zip(predictions, scores)):
            if pred == -1:  # Anomaly
                anomalies.append(Anomaly(
                    index=i,
                    timestamp=timestamps[i] if timestamps and i < len(timestamps) else None,
                    value=values[i],
                    expected_value=0,  # Isolation forest doesn't provide expected value
                    deviation=abs(score),
                    score=abs(score),
                    severity=self._classify_severity(abs(score) * 10),  # Scale score
                    method="isolation_forest",
                ))

        return anomalies

    def _detect_dbscan(
        self,
        values: List[float],
        timestamps: Optional[List[datetime]]
    ) -> List[Anomaly]:
        """Detect anomalies using DBSCAN clustering"""
        try:
            from sklearn.cluster import DBSCAN
        except ImportError:
            return self._detect_z_score(values, timestamps, self.default_threshold)

        # Reshape data
        arr = np.array(values).reshape(-1, 1)

        # Fit DBSCAN
        clustering = DBSCAN(eps=0.5, min_samples=3).fit(arr)

        # Points labeled as -1 are outliers
        anomalies = []

        for i, label in enumerate(clustering.labels_):
            if label == -1:
                anomalies.append(Anomaly(
                    index=i,
                    timestamp=timestamps[i] if timestamps and i < len(timestamps) else None,
                    value=values[i],
                    expected_value=0,
                    deviation=0,
                    score=1.0,
                    severity="medium",
                    method="dbscan",
                ))

        return anomalies

    def detect_pattern_anomalies(
        self,
        values: List[float],
        timestamps: List[datetime],
        expected_pattern: str = "daily"
    ) -> List[Anomaly]:
        """Detect deviations from expected patterns (seasonality)"""
        if len(values) < 14:
            return []

        # Group by pattern period
        pattern_groups = {}

        for i, ts in enumerate(timestamps):
            if expected_pattern == "daily":
                key = ts.hour
            elif expected_pattern == "weekly":
                key = ts.weekday()
            elif expected_pattern == "monthly":
                key = ts.day
            else:
                continue

            if key not in pattern_groups:
                pattern_groups[key] = []
            pattern_groups[key].append(values[i])

        # Calculate expected ranges for each pattern
        pattern_stats = {}
        for key, group_values in pattern_groups.items():
            if len(group_values) >= 3:
                pattern_stats[key] = {
                    "mean": np.mean(group_values),
                    "std": np.std(group_values),
                }

        # Detect anomalies
        anomalies = []

        for i, (ts, value) in enumerate(zip(timestamps, values)):
            if expected_pattern == "daily":
                key = ts.hour
            elif expected_pattern == "weekly":
                key = ts.weekday()
            elif expected_pattern == "monthly":
                key = ts.day
            else:
                continue

            if key in pattern_stats:
                stats = pattern_stats[key]
                if stats["std"] > 0:
                    z_score = abs((value - stats["mean"]) / stats["std"])

                    if z_score > self.default_threshold:
                        anomalies.append(Anomaly(
                            index=i,
                            timestamp=ts,
                            value=value,
                            expected_value=stats["mean"],
                            deviation=value - stats["mean"],
                            score=z_score,
                            severity=self._classify_severity(z_score),
                            method=f"pattern_{expected_pattern}",
                            context={"pattern_key": key},
                        ))

        return anomalies

    def detect_change_points(
        self,
        values: List[float],
        timestamps: Optional[List[datetime]] = None,
        window: int = 10
    ) -> List[Dict[str, Any]]:
        """Detect significant change points in the data"""
        if len(values) < window * 2:
            return []

        change_points = []

        for i in range(window, len(values) - window):
            before = values[i - window:i]
            after = values[i:i + window]

            # Simple t-test approximation
            mean_before = np.mean(before)
            mean_after = np.mean(after)
            std_before = np.std(before)
            std_after = np.std(after)

            # Calculate normalized difference
            if std_before > 0 and std_after > 0:
                diff_score = abs(mean_after - mean_before) / max(std_before, std_after)

                if diff_score > self.default_threshold:
                    change_points.append({
                        "index": i,
                        "timestamp": timestamps[i].isoformat() if timestamps and i < len(timestamps) else None,
                        "before_mean": float(mean_before),
                        "after_mean": float(mean_after),
                        "change_magnitude": float(mean_after - mean_before),
                        "score": float(diff_score),
                        "severity": self._classify_severity(diff_score),
                    })

        return change_points

    def _classify_severity(self, score: float) -> str:
        """Classify anomaly severity based on score"""
        if score < self.severity_thresholds["low"]:
            return "low"
        elif score < self.severity_thresholds["medium"]:
            return "medium"
        elif score < self.severity_thresholds["high"]:
            return "high"
        else:
            return "critical"

    def get_anomaly_summary(self, anomalies: List[Anomaly]) -> Dict[str, Any]:
        """Get summary statistics for detected anomalies"""
        if not anomalies:
            return {
                "total_anomalies": 0,
                "by_severity": {},
                "by_method": {},
            }

        severity_counts = {}
        method_counts = {}

        for anomaly in anomalies:
            severity_counts[anomaly.severity] = severity_counts.get(anomaly.severity, 0) + 1
            method_counts[anomaly.method] = method_counts.get(anomaly.method, 0) + 1

        return {
            "total_anomalies": len(anomalies),
            "by_severity": severity_counts,
            "by_method": method_counts,
            "average_score": float(np.mean([a.score for a in anomalies])),
            "max_score": float(max([a.score for a in anomalies])),
        }
