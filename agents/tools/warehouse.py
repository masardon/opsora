"""
Warehouse Tool

Provides agents with the ability to query BigQuery and retrieve data.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

import pandas as pd
import polars as pl


@dataclass
class QueryResult:
    """Result from a warehouse query"""
    query: str
    data: List[Dict[str, Any]]
    rows: int
    columns: List[str]
    execution_time_ms: int
    error: Optional[str] = None

    def to_dataframe(self, library: str = "polars") -> Union[pd.DataFrame, pl.DataFrame]:
        """Convert to pandas or polars DataFrame"""
        if library == "pandas":
            return pd.DataFrame(self.data)
        return pl.DataFrame(self.data)

    def to_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        if not self.data:
            return {"count": 0, "message": "No data returned"}

        df = self.to_dataframe("polars")

        summary = {
            "row_count": len(df),
            "columns": self.columns,
            "numeric_summary": {},
            "categorical_summary": {},
        }

        # Numeric columns
        for col in df.columns:
            if df[col].dtype in [pl.Float32, pl.Float64, pl.Int32, pl.Int64]:
                col_data = df[col].drop_nulls()
                if len(col_data) > 0:
                    summary["numeric_summary"][col] = {
                        "min": float(col_data.min()),
                        "max": float(col_data.max()),
                        "mean": float(col_data.mean()),
                        "median": float(col_data.median()),
                        "std": float(col_data.std()) if len(col_data) > 1 else 0,
                    }

        return summary


class WarehouseTool:
    """Tool for querying BigQuery data warehouse"""

    def __init__(
        self,
        project_id: str,
        dataset: str = "opsora",
        location: str = "us-central1",
    ):
        self.project_id = project_id
        self.dataset = dataset
        self.location = location
        self._client = None
        self._query_cache = {}

        # Common table references
        self.tables = {
            "raw_events": f"{project_id}.{dataset}.bronze_raw_events",
            "sales_events": f"{project_id}.{dataset}.silver_sales_events",
            "operations_events": f"{project_id}.{dataset}.silver_operations_events",
            "customer_events": f"{project_id}.{dataset}.silver_customer_events",
            "revenue_events": f"{project_id}.{dataset}.silver_revenue_events",
            "metrics_sales": f"{project_id}.{dataset}.gold_metrics_sales",
            "metrics_operations": f"{project_id}.{dataset}.gold_metrics_operations",
            "metrics_customers": f"{project_id}.{dataset}.gold_metrics_customers",
            "metrics_revenue": f"{project_id}.{dataset}.gold_metrics_revenue",
            "recommendations": f"{project_id}.{dataset}.gold_recommendations",
        }

    def _get_client(self):
        """Lazy load BigQuery client"""
        if self._client is None:
            try:
                from google.cloud import bigquery
                self._client = bigquery.Client(project=self.project_id, location=self.location)
            except ImportError:
                raise ImportError("google-cloud-bigquery is required. Install with: pip install google-cloud-bigquery")
            except Exception as e:
                # For demo/local development, return mock client
                if not self.project_id or self.project_id == "your-project-id":
                    return MockWarehouseClient(self.tables)
                raise
        return self._client

    async def query(
        self,
        sql: str,
        use_cache: bool = True,
        timeout_ms: int = 30000,
    ) -> QueryResult:
        """Execute a SQL query and return results"""
        import time

        cache_key = hash(sql) if use_cache else None
        if use_cache and cache_key in self._query_cache:
            return self._query_cache[cache_key]

        start_time = time.time()

        try:
            client = self._get_client()

            if isinstance(client, MockWarehouseClient):
                # Use mock client for demo
                result = await client.query(sql)
            else:
                # Use real BigQuery
                job = client.query(sql)
                result = job.result(timeout_ms=timeout_ms)

                data = [dict(row) for row in result]
                rows = len(data)
                columns = list(data[0].keys()) if data else []

                result = QueryResult(
                    query=sql,
                    data=data,
                    rows=rows,
                    columns=columns,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            if use_cache and cache_key:
                self._query_cache[cache_key] = result

            return result

        except Exception as e:
            return QueryResult(
                query=sql,
                data=[],
                rows=0,
                columns=[],
                execution_time_ms=int((time.time() - start_time) * 1000),
                error=str(e),
            )

    async def get_recent_events(
        self,
        domain: str,
        hours: int = 24,
        limit: int = 1000,
    ) -> QueryResult:
        """Get recent events for a domain"""

        table = self.tables.get(f"{domain}_events", self.tables["raw_events"])

        sql = f"""
        SELECT *
        FROM `{table}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        ORDER BY event_timestamp DESC
        LIMIT {limit}
        """

        return await self.query(sql)

    async def get_metrics(
        self,
        domain: str,
        metrics: List[str],
        time_period: str = "last 30 days",
        group_by: Optional[List[str]] = None,
    ) -> QueryResult:
        """Get aggregated metrics for a domain"""

        # Parse time period
        days = self._parse_time_period(time_period)

        table = self.tables.get(f"metrics_{domain}", self.tables.get(f"{domain}_events"))

        # Build SELECT clause
        select_clauses = []
        for metric in metrics:
            if "avg" in metric.lower():
                select_clauses.append(f"AVG({metric}) as {metric}")
            elif "sum" in metric.lower():
                select_clauses.append(f"SUM({metric}) as {metric}")
            elif "count" in metric.lower():
                select_clauses.append(f"COUNT({metric}) as {metric}")
            else:
                select_clauses.append(metric)

        # Build GROUP BY clause
        group_by_clause = ""
        if group_by:
            group_by_clause = f"GROUP BY {', '.join(group_by)}"

        sql = f"""
        SELECT
            DATE(event_timestamp) as date,
            {', '.join(select_clauses)}
        FROM `{table}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        {group_by_clause}
        ORDER BY date DESC
        """

        return await self.query(sql)

    async def get_trends(
        self,
        domain: str,
        metric: str,
        period: str = "daily",
        days: int = 30,
    ) -> QueryResult:
        """Get trend data for a metric"""

        table = self.tables.get(f"metrics_{domain}", self.tables.get(f"{domain}_events"))

        # Determine truncation based on period
        if period == "hourly":
            date_trunc = "TIMESTAMP_TRUNC(event_timestamp, HOUR)"
        elif period == "daily":
            date_trunc = "DATE(event_timestamp)"
        elif period == "weekly":
            date_trunc = "TIMESTAMP_TRUNC(event_timestamp, WEEK)"
        elif period == "monthly":
            date_trunc = "TIMESTAMP_TRUNC(event_timestamp, MONTH)"
        else:
            date_trunc = "DATE(event_timestamp)"

        sql = f"""
        SELECT
            {date_trunc} as period,
            AVG({metric}) as avg_value,
            MIN({metric}) as min_value,
            MAX({metric}) as max_value,
            COUNT(*) as count,
            STDDEV({metric}) as std_dev
        FROM `{table}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
        GROUP BY period
        ORDER BY period DESC
        """

        return await self.query(sql)

    async def get_anomalies(
        self,
        domain: str,
        metric: str,
        threshold_std: float = 2.5,
        days: int = 7,
    ) -> QueryResult:
        """Find anomalous values using z-score"""

        # First get statistics
        stats_sql = f"""
        SELECT
            AVG({metric}) as mean,
            STDDEV({metric}) as stddev
        FROM `{self.tables.get(f'metrics_{domain}')}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        """

        stats = await self.query(stats_sql)

        if not stats.data or stats.data[0].get("stddev") is None:
            return QueryResult(
                query="",
                data=[],
                rows=0,
                columns=[],
                execution_time_ms=0,
                error="Insufficient data for anomaly detection",
            )

        mean = stats.data[0]["mean"]
        stddev = stats.data[0]["stddev"]

        # Find anomalies
        anomaly_sql = f"""
        SELECT
            *,
            ({metric} - {mean}) / {stddev} as z_score,
            ABS(({metric} - {mean}) / {stddev}) as abs_z_score
        FROM `{self.tables.get(f'metrics_{domain}')}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
            AND ABS(({metric} - {mean}) / {stddev}) > {threshold_std}
        ORDER BY abs_z_score DESC
        """

        return await self.query(anomaly_sql)

    async def compare_periods(
        self,
        domain: str,
        metrics: List[str],
        current_days: int = 7,
        previous_days: int = 7,
    ) -> QueryResult:
        """Compare metrics between two time periods"""

        table = self.tables.get(f"metrics_{domain}", self.tables.get(f"{domain}_events"))

        metric_selects = ", ".join([f"AVG({m}) as {m}" for m in metrics])

        sql = f"""
        WITH current_period AS (
            SELECT
                {metric_selects},
                'current' as period
            FROM `{table}`
            WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {current_days} DAY)
        ),
        previous_period AS (
            SELECT
                {metric_selects},
                'previous' as period
            FROM `{table}`
            WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {current_days + previous_days} DAY)
                AND event_timestamp < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {current_days} DAY)
        )
        SELECT * FROM current_period
        UNION ALL
        SELECT * FROM previous_period
        """

        return await self.query(sql)

    def _parse_time_period(self, period: str) -> int:
        """Parse time period string to days"""
        period_lower = period.lower()

        if "hour" in period_lower:
            hours = int(period_lower.split()[0]) if period_lower.split()[0].isdigit() else 1
            return hours / 24
        elif "day" in period_lower:
            return int(period_lower.split()[0]) if period_lower.split()[0].isdigit() else 1
        elif "week" in period_lower:
            weeks = int(period_lower.split()[0]) if period_lower.split()[0].isdigit() else 1
            return weeks * 7
        elif "month" in period_lower:
            months = int(period_lower.split()[0]) if period_lower.split()[0].isdigit() else 1
            return months * 30
        else:
            return 30  # Default to 30 days

    def clear_cache(self):
        """Clear query cache"""
        self._query_cache.clear()


class MockWarehouseClient:
    """Mock warehouse client for demo/testing without real GCP setup"""

    def __init__(self, tables: Dict[str, str]):
        self.tables = tables
        self._mock_data = self._generate_mock_data()

    def _generate_mock_data(self) -> Dict[str, List[Dict]]:
        """Generate mock data for demo"""
        import random
        from datetime import datetime, timedelta

        base_time = datetime.utcnow()

        def generate_sales_events(n=100):
            events = []
            for i in range(n):
                events.append({
                    "event_id": f"sale_{i}",
                    "event_timestamp": (base_time - timedelta(hours=random.randint(0, 720))).isoformat(),
                    "customer_id": f"cust_{random.randint(1, 50)}",
                    "product_id": f"prod_{random.randint(1, 20)}",
                    "revenue": round(random.uniform(50, 5000), 2),
                    "quantity": random.randint(1, 10),
                    "channel": random.choice(["online", "store", "phone"]),
                })
            return events

        def generate_operations_events(n=100):
            events = []
            for i in range(n):
                events.append({
                    "event_id": f"ops_{i}",
                    "event_timestamp": (base_time - timedelta(hours=random.randint(0, 720))).isoformat(),
                    "inventory_level": random.randint(100, 5000),
                    "product_id": f"prod_{random.randint(1, 20)}",
                    "warehouse_id": f"wh_{random.randint(1, 5)}",
                    "fulfillment_time_hours": round(random.uniform(1, 72), 2),
                })
            return events

        def generate_customer_events(n=100):
            events = []
            for i in range(n):
                events.append({
                    "event_id": f"cust_event_{i}",
                    "event_timestamp": (base_time - timedelta(hours=random.randint(0, 720))).isoformat(),
                    "customer_id": f"cust_{random.randint(1, 50)}",
                    "event_type": random.choice(["login", "purchase", "support", "review"]),
                    "satisfaction_score": random.randint(1, 5) if random.random() > 0.3 else None,
                    "nps_score": random.randint(0, 10) if random.random() > 0.5 else None,
                })
            return events

        def generate_revenue_events(n=100):
            events = []
            for i in range(n):
                events.append({
                    "event_id": f"rev_{i}",
                    "event_timestamp": (base_time - timedelta(hours=random.randint(0, 720))).isoformat(),
                    "revenue_type": random.choice(["recurring", "one_time", "expansion", "churn"]),
                    "amount": round(random.uniform(100, 10000), 2),
                    "arr": round(random.uniform(1000, 50000), 2),
                })
            return events

        return {
            "sales": generate_sales_events(),
            "operations": generate_operations_events(),
            "customers": generate_customer_events(),
            "revenue": generate_revenue_events(),
        }

    async def query(self, sql: str) -> QueryResult:
        """Mock query execution"""
        import time
        import re

        start_time = time.time()

        # Simple parsing to determine what data to return
        sql_lower = sql.lower()

        if "sales" in sql_lower:
            data = self._mock_data["sales"][:50]  # Limit for demo
        elif "operations" in sql_lower or "ops" in sql_lower:
            data = self._mock_data["operations"][:50]
        elif "customer" in sql_lower:
            data = self._mock_data["customers"][:50]
        elif "revenue" in sql_lower or "rev" in sql_lower:
            data = self._mock_data["revenue"][:50]
        else:
            data = []

        columns = list(data[0].keys()) if data else []

        # Simulate network delay
        await asyncio.sleep(0.1)

        return QueryResult(
            query=sql,
            data=data,
            rows=len(data),
            columns=columns,
            execution_time_ms=int((time.time() - start_time) * 1000),
        )


# Import asyncio for mock client
import asyncio
