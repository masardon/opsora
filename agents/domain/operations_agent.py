"""
Operations Agent

Analyzes operational efficiency, inventory, supply chain, and resource utilization
to optimize business operations.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from agents.base.base_agent import (
    BaseAgent,
    AnalysisRequest,
    AnalysisResult,
    Recommendation,
    InsightType,
    ImpactLevel,
    UrgencyLevel,
    EffortLevel,
)
from agents.tools import WarehouseTool, AnalyzerTool, AnomalyDetectorTool
from config.agent_prompts import OPERATIONS_AGENT_SYSTEM


class OperationsAgent(BaseAgent):
    """Operations Analytics Agent"""

    def __init__(
        self,
        llm_adapter=None,
        warehouse_tool: Optional[WarehouseTool] = None,
        analyzer: Optional[AnalyzerTool] = None,
        detector: Optional[AnomalyDetectorTool] = None,
        **kwargs
    ):
        super().__init__(
            agent_type="operations",
            llm_adapter=llm_adapter,
            **kwargs
        )

        self.warehouse = warehouse_tool
        self.analyzer = analyzer or AnalyzerTool()
        self.detector = detector or AnomalyDetectorTool()

        # Operations-specific metrics
        self.key_metrics = [
            "inventory_turnover",
            "stockout_rate",
            "fulfillment_time",
            "on_time_delivery_rate",
            "operational_cost_per_unit",
            "capacity_utilization",
        ]

    def get_system_prompt(self) -> str:
        return OPERATIONS_AGENT_SYSTEM

    async def analyze_data(
        self,
        data: Dict[str, Any],
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """Analyze operations data and generate insights"""

        context = context or {}

        # Query warehouse for relevant data
        if self.warehouse:
            time_period = context.get("time_period", "last 30 days")

            # Get recent operations events
            ops_data = await self.warehouse.get_recent_events(
                domain="operations",
                hours=24 * 30,
                limit=1000,
            )

            # Get metrics
            metrics = await self.warehouse.get_metrics(
                domain="operations",
                metrics=self.key_metrics,
                time_period=time_period,
            )

            # Get trends
            trends = await self.warehouse.get_trends(
                domain="operations",
                metric="fulfillment_time",
                period="daily",
                days=30,
            )

            data["warehouse_data"] = {
                "operations_events": ops_data.to_summary() if ops_data else {},
                "metrics": metrics.to_summary() if metrics else {},
                "trends": trends.to_summary() if trends else {},
            }

        # Analyze using LLM
        prompt = self._build_analysis_prompt(query, data)

        response = await self.llm.generate(
            prompt,
            system_prompt=self.get_system_prompt(),
            temperature=0.7,
        )

        # Parse recommendations
        recommendations = await self._extract_recommendations(response, data)

        # Get key findings
        key_findings = await self._generate_key_findings(data)

        # Calculate overall confidence
        confidence = self._calculate_confidence(data, recommendations)

        return AnalysisResult(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            query=query,
            summary=self._extract_summary(response),
            key_findings=key_findings,
            recommendations=recommendations,
            confidence=confidence,
            metrics_analyzed=self.key_metrics,
            raw_response=response,
            metadata=data.get("warehouse_data", {}),
        )

    async def predict_stockout_risk(
        self,
        product_id: Optional[str] = None,
        days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """Predict products at risk of stockout"""

        if not self.warehouse:
            return []

        # Get inventory and sales data
        inventory_query = f"""
        SELECT
            product_id,
            AVG(inventory_level) as current_stock,
            COUNT(*) as data_points,
            STDDEV(inventory_level) as stock_variance
        FROM `{self.warehouse.tables['operations_events']}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        """

        if product_id:
            inventory_query += f" AND product_id = '{product_id}'"

        inventory_query += " GROUP BY product_id"

        inventory_data = await self.warehouse.query(inventory_query)

        # Get sales rate
        sales_query = f"""
        SELECT
            product_id,
            COUNT(*) as units_sold,
            SUM(quantity) as total_quantity
        FROM `{self.warehouse.tables['sales_events']}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
        """

        if product_id:
            sales_query += f" AND product_id = '{product_id}'"

        sales_query += " GROUP BY product_id"

        sales_data = await self.warehouse.query(sales_query)

        # Combine and analyze
        stockout_risks = []

        sales_by_product = {s["product_id"]: s for s in sales_data.data}

        for inv in inventory_data.data:
            product_id = inv["product_id"]

            if product_id not in sales_by_product:
                continue

            sales = sales_by_product[product_id]
            current_stock = inv["current_stock"]
            daily_sales_rate = sales["total_quantity"] / 30  # 30 days

            # Project stockout
            if daily_sales_rate > 0:
                days_until_stockout = current_stock / daily_sales_rate

                if days_until_stockout <= days_ahead:
                    risk_score = max(0, 1 - (days_until_stockout / days_ahead))

                    stockout_risks.append({
                        "product_id": product_id,
                        "current_stock": round(current_stock, 1),
                        "daily_sales_rate": round(daily_sales_rate, 1),
                        "days_until_stockout": round(days_until_stockout, 1),
                        "risk_score": round(risk_score, 2),
                        "urgency": "high" if days_until_stockout < 3 else "medium",
                        "suggested_action": f"Reorder within {int(days_until_stockout)} days",
                    })

        stockout_risks.sort(key=lambda x: x["risk_score"], reverse=True)

        return stockout_risks

    async def optimize_inventory_levels(
        self,
        service_level: float = 0.95
    ) -> List[Dict[str, Any]]:
        """Calculate optimal inventory levels for products"""

        if not self.warehouse:
            return []

        # Get demand variability
        demand_query = """
        SELECT
            product_id,
            DATE(event_timestamp) as date,
            SUM(quantity) as daily_demand
        FROM `{{sales_table}}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        GROUP BY product_id, DATE(event_timestamp)
        """

        # Calculate safety stock and reorder points
        # This would typically use more sophisticated demand forecasting

        recommendations = []

        # Simplified example for demo
        recommendations.append({
            "product_id": "example_product",
            "current_stock": 500,
            "avg_daily_demand": 25,
            "demand_stddev": 8,
            "lead_time_days": 7,
            "safety_stock": 46,  # Z * sigma * sqrt(lead_time)
            "reorder_point": 221,  # avg_demand * lead_time + safety_stock
            "economic_order_quantity": 350,
            "service_level": service_level,
        })

        return recommendations

    async def detect_supply_chain_disruptions(
        self,
        threshold_hours: float = 48
    ) -> List[Dict[str, Any]]:
        """Detect potential supply chain disruptions"""

        if not self.warehouse:
            return []

        # Look for increasing fulfillment times
        disruption_query = f"""
        WITH fulfillment_metrics AS (
            SELECT
                warehouse_id,
                DATE(event_timestamp) as date,
                AVG(fulfillment_time_hours) as avg_fulfillment_time,
                COUNT(*) as order_count
            FROM `{self.warehouse.tables['operations_events']}`
            WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
            GROUP BY warehouse_id, DATE(event_timestamp)
        ),
        baseline AS (
            SELECT
                warehouse_id,
                AVG(avg_fulfillment_time) as baseline_time,
                STDDEV(avg_fulfillment_time) as time_stddev
            FROM fulfillment_metrics
            WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
                AND date < DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
            GROUP BY warehouse_id
        )
        SELECT
            f.warehouse_id,
            f.date,
            f.avg_fulfillment_time,
            b.baseline_time,
            b.time_stddev,
            (f.avg_fulfillment_time - b.baseline_time) / NULLIF(b.time_stddev, 0) as z_score
        FROM fulfillment_metrics f
        JOIN baseline b ON f.warehouse_id = b.warehouse_id
        WHERE f.date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
            AND (f.avg_fulfillment_time - b.baseline_time) > {threshold_hours}
        ORDER BY z_score DESC
        """

        result = await self.warehouse.query(disruption_query)

        disruptions = []

        for row in result.data:
            disruptions.append({
                "warehouse_id": row["warehouse_id"],
                "date": row["date"],
                "current_fulfillment_time": row["avg_fulfillment_time"],
                "baseline_fulfillment_time": row["baseline_time"],
                "increase_hours": row["avg_fulfillment_time"] - row["baseline_time"],
                "z_score": row["z_score"],
                "severity": self._assess_disruption_severity(row["z_score"]),
                "suggested_action": "Investigate supplier delays and consider alternative sources",
            })

        return disruptions

    async def identify_bottlenecks(
        self,
        process: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Identify operational bottlenecks"""

        if not self.warehouse:
            return []

        # Analyze fulfillment times to find bottlenecks
        bottleneck_query = """
        SELECT
            warehouse_id,
            AVG(fulfillment_time_hours) as avg_time,
            PERCENTILE_CONT(fulfillment_time_hours, 0.5) OVER () as median_time,
            PERCENTILE_CONT(fulfillment_time_hours, 0.95) OVER () as p95_time,
            COUNT(*) as order_count
        FROM `{{operations_table}}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
        GROUP BY warehouse_id
        HAVING COUNT(*) >= 10
        ORDER BY avg_time DESC
        """

        result = await self.warehouse.query(bottleneck_query)

        bottlenecks = []

        # Find warehouses with unusually high times
        all_times = [r["avg_time"] for r in result.data]

        if all_times:
            import numpy as np
            mean_time = np.mean(all_times)
            std_time = np.std(all_times)

            for row in result.data:
                if row["avg_time"] > mean_time + std_time:
                    bottlenecks.append({
                        "warehouse_id": row["warehouse_id"],
                        "avg_fulfillment_time": row["avg_time"],
                        "median_time": row["median_time"],
                        "p95_time": row["p95_time"],
                        "order_count": row["order_count"],
                        "percentile": round((row["avg_time"] / max(all_times)) * 100, 1),
                        "suggested_action": "Review staffing, equipment, and processes",
                    })

        return bottlenecks

    async def _extract_recommendations(
        self,
        response: str,
        data: Dict[str, Any]
    ) -> List[Recommendation]:
        """Extract structured recommendations from LLM response"""

        schema = {
            "type": "object",
            "properties": {
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "insight_type": {"type": "string"},
                            "summary": {"type": "string"},
                            "description": {"type": "string"},
                            "confidence": {"type": "number"},
                            "impact": {"type": "string"},
                            "urgency": {"type": "string"},
                            "effort": {"type": "string"},
                            "expected_impact_value": {"type": "number"},
                            "rationale": {"type": "string"},
                            "metrics_affected": {"type": "array", "items": {"type": "string"}},
                            "stakeholders": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["insight_type", "summary", "description", "confidence", "impact", "urgency", "effort"],
                    },
                },
            },
            "required": ["recommendations"],
        }

        prompt = f"""
Extract and structure the recommendations from this operations analysis:

{response}

Return a JSON object with a "recommendations" array.
"""

        try:
            extracted = await self.llm.generate_structured(
                prompt,
                schema=schema,
                temperature=0.3,
            )

            recommendations = []
            for rec in extracted.get("recommendations", [])[:self.max_recommendations]:
                rec["composite_score"] = self._calculate_score(
                    confidence=rec["confidence"],
                    impact=rec["impact"],
                    urgency=rec["urgency"],
                    effort=rec["effort"],
                )

                recommendations.append(
                    Recommendation(
                        agent_id=self.agent_id,
                        agent_type=self.agent_type,
                        **rec
                    )
                )

            return self.filter_by_confidence(self.sort_by_priority(recommendations))

        except Exception as e:
            return []

    async def _generate_key_findings(self, data: Dict[str, Any]) -> List[str]:
        """Generate key findings from data"""
        findings = []

        if "warehouse_data" in data:
            wd = data["warehouse_data"]
            if wd.get("metrics", {}).get("row_count", 0) > 0:
                findings.append(f"Analyzed {wd['metrics']['row_count']} operational metric records")

        return findings

    def _calculate_confidence(
        self,
        data: Dict[str, Any],
        recommendations: List[Recommendation]
    ) -> float:
        """Calculate overall confidence"""
        if not recommendations:
            return 0.5

        avg_rec_confidence = sum(r.confidence for r in recommendations) / len(recommendations)
        return round(min(avg_rec_confidence, 1.0), 2)

    def _extract_summary(self, response: str) -> str:
        """Extract summary from response"""
        if len(response) > 500:
            return response[:497] + "..."
        return response

    def _assess_disruption_severity(self, z_score: float) -> str:
        """Assess severity of disruption"""
        if z_score > 3:
            return "critical"
        elif z_score > 2:
            return "high"
        elif z_score > 1:
            return "medium"
        else:
            return "low"
