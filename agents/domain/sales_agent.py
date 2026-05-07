"""
Sales Agent

Analyzes sales performance, revenue trends, and customer purchasing behavior
to identify opportunities and risks.
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
from agents.tools import WarehouseTool, AnalyzerTool, ForecasterTool, AnomalyDetectorTool
from config.agent_prompts import SALES_AGENT_SYSTEM


class SalesAgent(BaseAgent):
    """Sales Analytics Agent"""

    def __init__(
        self,
        llm_adapter=None,
        warehouse_tool: Optional[WarehouseTool] = None,
        analyzer: Optional[AnalyzerTool] = None,
        forecaster: Optional[ForecasterTool] = None,
        detector: Optional[AnomalyDetectorTool] = None,
        **kwargs
    ):
        super().__init__(
            agent_type="sales",
            llm_adapter=llm_adapter,
            **kwargs
        )

        self.warehouse = warehouse_tool
        self.analyzer = analyzer or AnalyzerTool()
        self.forecaster = forecaster or ForecasterTool()
        self.detector = detector or AnomalyDetectorTool()

        # Sales-specific metrics
        self.key_metrics = [
            "revenue",
            "average_order_value",
            "purchase_frequency",
            "customer_lifetime_value",
            "conversion_rate",
            "cart_abandonment_rate",
        ]

    def get_system_prompt(self) -> str:
        return SALES_AGENT_SYSTEM

    async def analyze_data(
        self,
        data: Dict[str, Any],
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """Analyze sales data and generate insights"""

        context = context or {}

        # Query warehouse for relevant data
        if self.warehouse:
            time_period = context.get("time_period", "last 30 days")

            # Get recent sales events
            sales_data = await self.warehouse.get_recent_events(
                domain="sales",
                hours=24 * 30,  # 30 days
                limit=1000,
            )

            # Get metrics
            metrics = await self.warehouse.get_metrics(
                domain="sales",
                metrics=self.key_metrics,
                time_period=time_period,
            )

            # Get trends
            trends = await self.warehouse.get_trends(
                domain="sales",
                metric="revenue",
                period="daily",
                days=30,
            )

            data["warehouse_data"] = {
                "sales_events": sales_data.to_summary() if sales_data else {},
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

        # Parse recommendations from response
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

    async def forecast_revenue(
        self,
        periods: int = 7,
        domain: str = "sales"
    ) -> Dict[str, Any]:
        """Forecast future revenue"""

        if not self.warehouse:
            return {"error": "Warehouse tool not configured"}

        # Get historical data
        trends = await self.warehouse.get_trends(
            domain=domain,
            metric="revenue",
            period="daily",
            days=90,
        )

        if not trends.data or len(trends.data) < 10:
            return {"error": "Insufficient historical data"}

        # Extract values and timestamps
        values = [row.get("avg_value", 0) for row in trends.data]
        timestamps = [
            datetime.fromisoformat(row["period"].replace("Z", "+00:00"))
            if isinstance(row["period"], str) else row["period"]
            for row in trends.data
        ]

        # Generate forecast
        forecast = self.forecaster.forecast(
            values=values[::-1],  # Reverse to chronological
            timestamps=timestamps[::-1],
            periods=periods,
        )

        return {
            "forecast_values": forecast.forecast_values,
            "forecast_dates": [d.isoformat() for d in forecast.forecast_dates],
            "lower_bound": forecast.lower_bound,
            "upper_bound": forecast.upper_bound,
            "method": forecast.method,
            "confidence": forecast.confidence,
            "metrics": forecast.metrics,
        }

    async def detect_churn_risk(
        self,
        customer_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Detect customers at risk of churning"""

        if not self.warehouse:
            return []

        # Get customer purchase patterns
        customer_data = await self.warehouse.query(f"""
        SELECT
            customer_id,
            COUNT(*) as purchase_count,
            MAX(event_timestamp) as last_purchase,
            AVG(revenue) as avg_order_value,
            SUM(revenue) as total_revenue,
            MIN(event_timestamp) as first_purchase
        FROM `{self.warehouse.tables['sales_events']}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        GROUP BY customer_id
        HAVING purchase_count >= 2
        """)

        churn_risks = []

        for customer in customer_data.data:
            # Calculate days since last purchase
            last_purchase = datetime.fromisoformat(customer["last_purchase"])
            days_since_purchase = (datetime.utcnow() - last_purchase).days

            # Calculate average purchase interval
            first_purchase = datetime.fromisoformat(customer["first_purchase"])
            total_days = (last_purchase - first_purchase).days
            avg_interval = total_days / (customer["purchase_count"] - 1) if customer["purchase_count"] > 1 else 30

            # Churn risk factors
            risk_score = 0

            if days_since_purchase > avg_interval * 2:
                risk_score += 0.4
            elif days_since_purchase > avg_interval * 1.5:
                risk_score += 0.2

            if customer["purchase_count"] < 3:
                risk_score += 0.2

            if customer["avg_order_value"] < 100:
                risk_score += 0.1

            if customer_id and customer["customer_id"] != customer_id:
                continue

            if risk_score >= 0.5:
                churn_risks.append({
                    "customer_id": customer["customer_id"],
                    "risk_score": round(risk_score, 2),
                    "days_since_purchase": days_since_purchase,
                    "avg_interval_days": round(avg_interval, 1),
                    "total_revenue": customer["total_revenue"],
                    "purchase_count": customer["purchase_count"],
                    "last_purchase": customer["last_purchase"],
                })

        # Sort by risk score
        churn_risks.sort(key=lambda x: x["risk_score"], reverse=True)

        return churn_risks[:10]

    async def identify_upsell_opportunities(
        self,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Identify customers with upsell potential"""

        if not self.warehouse:
            return []

        # Find customers with high purchase frequency but low order value
        opportunities = await self.warehouse.query(f"""
        SELECT
            customer_id,
            COUNT(*) as purchase_count,
            AVG(revenue) as avg_order_value,
            SUM(revenue) as total_revenue,
            ARRAY_AGG(DISTINCT product_id) as products_purchased
        FROM `{self.warehouse.tables['sales_events']}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        GROUP BY customer_id
        HAVING purchase_count >= 3 AND avg_order_value < 500
        ORDER BY purchase_count DESC, total_revenue DESC
        LIMIT {limit * 2}
        """)

        results = []

        for opp in opportunities.data:
            # Score the opportunity
            frequency_score = min(opp["purchase_count"] / 10, 1.0)  # Normalize to 0-1
            value_score = 1 - min(opp["avg_order_value"] / 500, 1.0)  # Lower value = higher potential
            opportunity_score = (frequency_score + value_score) / 2

            results.append({
                "customer_id": opp["customer_id"],
                "opportunity_score": round(opportunity_score, 2),
                "purchase_count": opp["purchase_count"],
                "avg_order_value": opp["avg_order_value"],
                "total_revenue": opp["total_revenue"],
                "products_purchased": len(opp.get("products_purchased", [])),
                "suggested_action": "Offer bundle discount or premium product",
            })

        results.sort(key=lambda x: x["opportunity_score"], reverse=True)

        return results[:limit]

    async def _extract_recommendations(
        self,
        response: str,
        data: Dict[str, Any]
    ) -> List[Recommendation]:
        """Extract structured recommendations from LLM response"""

        # Use LLM to extract structured recommendations
        schema = {
            "type": "object",
            "properties": {
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "insight_type": {"type": "string", "enum": ["alert", "suggestion", "automation", "insight"]},
                            "summary": {"type": "string"},
                            "description": {"type": "string"},
                            "confidence": {"type": "number"},
                            "impact": {"type": "string", "enum": ["low", "medium", "high"]},
                            "urgency": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                            "effort": {"type": "string", "enum": ["easy", "moderate", "complex"]},
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
Extract and structure the recommendations from this analysis response:

{response}

Return a JSON object with a "recommendations" array containing the structured recommendations.
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
            # Fallback: create generic recommendations
            return []

    async def _generate_key_findings(self, data: Dict[str, Any]) -> List[str]:
        """Generate key findings from data"""

        findings = []

        # Analyze warehouse data if available
        if "warehouse_data" in data:
            wd = data["warehouse_data"]

            if wd.get("metrics", {}).get("row_count", 0) > 0:
                findings.append(f"Analyzed {wd['metrics']['row_count']} metric records")

            # Check for anomalies
            if self.warehouse:
                anomalies = await self.detector.detect(
                    values=[r.get("avg_value", 0) for r in wd.get("trends", {}).get("data", [])],
                    method="z_score",
                )

                if anomalies:
                    findings.append(f"Detected {len(anomalies)} anomalous data points")

        return findings

    def _calculate_confidence(
        self,
        data: Dict[str, Any],
        recommendations: List[Recommendation]
    ) -> float:
        """Calculate overall confidence in the analysis"""

        if not recommendations:
            return 0.5

        # Average recommendation confidence
        avg_rec_confidence = sum(r.confidence for r in recommendations) / len(recommendations)

        # Data quality factor
        data_quality = 1.0

        if "warehouse_data" in data:
            wd = data["warehouse_data"]
            if wd.get("metrics", {}).get("row_count", 0) < 10:
                data_quality = 0.7
            elif wd.get("metrics", {}).get("row_count", 0) < 50:
                data_quality = 0.85

        return round(min(avg_rec_confidence * data_quality, 1.0), 2)

    def _extract_summary(self, response: str) -> str:
        """Extract summary from response"""

        # Take first 500 characters as summary
        if len(response) > 500:
            return response[:497] + "..."
        return response
