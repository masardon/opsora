"""
Revenue Agent

Analyzes revenue streams, pricing, and financial performance to maximize
revenue growth and profitability.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import numpy as np

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
from agents.tools import WarehouseTool, AnalyzerTool, ForecasterTool
from config.agent_prompts import REVENUE_AGENT_SYSTEM


class RevenueAgent(BaseAgent):
    """Revenue Analytics Agent"""

    def __init__(
        self,
        llm_adapter=None,
        warehouse_tool: Optional[WarehouseTool] = None,
        analyzer: Optional[AnalyzerTool] = None,
        forecaster: Optional[ForecasterTool] = None,
        **kwargs
    ):
        super().__init__(
            agent_type="revenue",
            llm_adapter=llm_adapter,
            **kwargs
        )

        self.warehouse = warehouse_tool
        self.analyzer = analyzer or AnalyzerTool()
        self.forecaster = forecaster or ForecasterTool()

        # Revenue-specific metrics
        self.key_metrics = [
            "total_revenue",
            "mrr",
            "arr",
            "arpu",
            "revenue_growth_rate",
            "net_revenue_retention",
            "gross_margin",
        ]

    def get_system_prompt(self) -> str:
        return REVENUE_AGENT_SYSTEM

    async def analyze_data(
        self,
        data: Dict[str, Any],
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """Analyze revenue data and generate insights"""

        context = context or {}

        # Query warehouse for relevant data
        if self.warehouse:
            time_period = context.get("time_period", "last 30 days")

            # Get recent revenue events
            revenue_data = await self.warehouse.get_recent_events(
                domain="revenue",
                hours=24 * 30,
                limit=1000,
            )

            # Get metrics
            metrics = await self.warehouse.get_metrics(
                domain="revenue",
                metrics=self.key_metrics,
                time_period=time_period,
            )

            # Get trends
            trends = await self.warehouse.get_trends(
                domain="revenue",
                metric="total_revenue",
                period="daily",
                days=30,
            )

            data["warehouse_data"] = {
                "revenue_events": revenue_data.to_summary() if revenue_data else {},
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

    async def forecast_revenue(
        self,
        periods: int = 30,
        confidence_interval: float = 0.95
    ) -> Dict[str, Any]:
        """Forecast future revenue"""

        if not self.warehouse:
            return {"error": "Warehouse not configured"}

        # Get historical revenue data
        trends = await self.warehouse.get_trends(
            domain="revenue",
            metric="total_revenue",
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
            values=values[::-1],
            timestamps=timestamps[::-1],
            periods=periods,
        )

        # Calculate projected totals
        projected_total = sum(forecast.forecast_values)
        projected_lower = sum(forecast.lower_bound)
        projected_upper = sum(forecast.upper_bound)

        return {
            "periods": periods,
            "forecast_values": forecast.forecast_values,
            "forecast_dates": [d.isoformat() for d in forecast.forecast_dates],
            "lower_bound": forecast.lower_bound,
            "upper_bound": forecast.upper_bound,
            "projected_total": round(projected_total, 2),
            "projected_lower": round(projected_lower, 2),
            "projected_upper": round(projected_upper, 2),
            "method": forecast.method,
            "confidence": forecast.confidence,
            "metrics": forecast.metrics,
        }

    async def analyze_revenue_streams(
        self,
        time_period: str = "last 30 days"
    ) -> List[Dict[str, Any]]:
        """Analyze revenue by stream/type"""

        if not self.warehouse:
            return []

        query = f"""
        SELECT
            revenue_type,
            SUM(amount) as total_revenue,
            COUNT(*) as transaction_count,
            AVG(amount) as avg_transaction_value,
            MIN(amount) as min_transaction,
            MAX(amount) as max_transaction,
            STDDEV(amount) as stddev_transaction
        FROM `{self.warehouse.tables['revenue_events']}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
        GROUP BY revenue_type
        ORDER BY total_revenue DESC
        """

        result = await self.warehouse.query(query)

        if not result.data:
            return []

        # Calculate total for percentages
        total_revenue = sum(r["total_revenue"] for r in result.data)

        streams = []
        for row in result.data:
            revenue = row["total_revenue"]
            percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0

            streams.append({
                "revenue_type": row["revenue_type"],
                "total_revenue": round(revenue, 2),
                "percentage": round(percentage, 1),
                "transaction_count": row["transaction_count"],
                "avg_transaction_value": round(row["avg_transaction_value"], 2),
                "min_transaction": round(row["min_transaction"], 2),
                "max_transaction": round(row["max_transaction"], 2),
                "stddev_transaction": round(row["stddev_transaction"], 2) if row["stddev_transaction"] else 0,
                "concentration_risk": "high" if percentage > 40 else ("medium" if percentage > 20 else "low"),
            })

        # Add concentration analysis
        if len(streams) > 0:
            # Herfindahl-Hirschman Index (HHI) for concentration
            hhi = sum((s["percentage"] ** 2) for s in streams)
            concentration_level = "high" if hhi > 2500 else ("medium" if hhi > 1500 else "low")

            return {
                "streams": streams,
                "total_revenue": round(total_revenue, 2),
                "stream_count": len(streams),
                "hhi": round(hhi, 1),
                "concentration_level": concentration_level,
                "diversification_score": round(max(0, 100 - hhi / 30), 1),
            }

        return streams

    async def detect_revenue_anomalies(
        self,
        threshold_std: float = 2.5
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in revenue"""

        if not self.warehouse:
            return []

        anomalies = await self.warehouse.get_anomalies(
            domain="revenue",
            metric="total_revenue",
            threshold_std=threshold_std,
            days=30,
        )

        results = []
        for anomaly in anomalies.data:
            results.append({
                "date": anomaly.get("period"),
                "value": round(anomaly.get("avg_value", 0), 2),
                "z_score": round(anomaly.get("z_score", 0), 2),
                "deviation": round(anomaly.get("avg_value", 0) - anomaly.get("mean", 0), 2),
                "severity": self._classify_anomaly_severity(abs(anomaly.get("z_score", 0))),
                "investigate": True,
            })

        return results

    async def analyze_pricing_opportunities(
        self,
        product_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Analyze pricing optimization opportunities"""

        if not self.warehouse:
            return []

        # Get revenue by price points
        query = f"""
        SELECT
            product_id,
            revenue / NULLIF(quantity, 0) as effective_price,
            SUM(quantity) as total_quantity,
            SUM(revenue) as total_revenue,
            COUNT(DISTINCT customer_id) as unique_customers
        FROM `{self.warehouse.tables['sales_events']}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
            AND quantity > 0
        """

        if product_id:
            query += f" AND product_id = '{product_id}'"

        query += " GROUP BY product_id, effective_price, revenue, quantity"

        result = await self.warehouse.query(query)

        if not result.data:
            return []

        # Analyze price elasticity
        opportunities = []

        # Group by product
        from collections import defaultdict
        products = defaultdict(list)

        for row in result.data:
            products[row["product_id"]].append(row)

        for product_id, data_points in products.items():
            if len(data_points) < 2:
                continue

            # Sort by effective price
            data_points.sort(key=lambda x: x["effective_price"])

            # Simple elasticity check
            prices = [d["effective_price"] for d in data_points]
            quantities = [d["total_quantity"] for d in data_points]

            # If higher prices have similar quantities, may have pricing power
            if len(prices) >= 2:
                price_range = max(prices) - min(prices)
                avg_price = sum(prices) / len(prices)

                if price_range > 0:
                    # Check if quantity varies less than price
                    qty_cv = np.std(quantities) / (np.mean(quantities) if np.mean(quantities) > 0 else 1)
                    price_cv = price_range / avg_price

                    # Low quantity variation with high price variation = pricing power
                    if qty_cv < price_cv * 0.5:
                        opportunities.append({
                            "product_id": product_id,
                            "opportunity": "pricing_increase",
                            "current_avg_price": round(avg_price, 2),
                            "potential_increase_percent": 10,
                            "reason": "Low quantity sensitivity to price changes",
                            "confidence": round(1 - qty_cv, 2),
                        })

        return opportunities

    async def calculate_net_revenue_retention(
        self,
        cohort_months: int = 12
    ) -> Dict[str, Any]:
        """Calculate Net Revenue Retention (NRR)"""

        if not self.warehouse:
            return {"error": "Warehouse not configured"}

        # Simplified NRR calculation
        # In production, this would be more sophisticated with cohort analysis

        query = f"""
        WITH customer_revenue AS (
            SELECT
                customer_id,
                SUM(CASE
                    WHEN revenue_type = 'recurring' THEN revenue
                    ELSE 0
                END) as recurring_revenue,
                SUM(CASE
                    WHEN revenue_type = 'expansion' THEN revenue
                    ELSE 0
                END) as expansion_revenue,
                SUM(CASE
                    WHEN revenue_type = 'churn' THEN ABS(revenue)
                    ELSE 0
                END) as churn_revenue
            FROM `{self.warehouse.tables['revenue_events']}`
            WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {cohort_months} MONTH)
            GROUP BY customer_id
        )
        SELECT
            SUM(recurring_revenue) as starting_revenue,
            SUM(expansion_revenue) as expansion_revenue,
            SUM(churn_revenue) as churn_revenue,
            COUNT(*) as customer_count
        FROM customer_revenue
        WHERE recurring_revenue > 0
        """

        result = await self.warehouse.query(query)

        if not result.data or not result.data[0]["starting_revenue"]:
            return {"error": "Insufficient revenue data"}

        row = result.data[0]
        starting = row["starting_revenue"]
        expansion = row["expansion_revenue"]
        churn = row["churn_revenue"]

        # NRR = (Starting + Expansion - Churn) / Starting
        ending = starting + expansion - churn
        nrr = (ending / starting * 100) if starting > 0 else 0

        # Classify NRR
        if nrr >= 125:
            nrr_level = "excellent"
        elif nrr >= 110:
            nrr_level = "good"
        elif nrr >= 100:
            nrr_level = "healthy"
        elif nrr >= 90:
            nrr_level = "concerning"
        else:
            nrr_level = "critical"

        return {
            "net_revenue_retention": round(nrr, 1),
            "nrr_level": nrr_level,
            "starting_revenue": round(starting, 2),
            "expansion_revenue": round(expansion, 2),
            "churn_revenue": round(churn, 2),
            "ending_revenue": round(ending, 2),
            "customer_count": row["customer_count"],
            "recommended_actions": self._get_nrr_actions(nrr_level),
        }

    def _get_nrr_actions(self, level: str) -> List[str]:
        """Get recommended actions based on NRR level"""

        actions = {
            "excellent": [
                "Document and share best practices",
                "Invest in customer success team",
                "Expand into new markets",
            ],
            "good": [
                "Identify drivers of expansion",
                "Focus on upsell opportunities",
                "Reduce churn risks",
            ],
            "healthy": [
                "Maintain current strategies",
                "Monitor for changes",
                "Incremental improvements",
            ],
            "concerning": [
                "Analyze churn reasons",
                "Improve product/service fit",
                "Strengthen customer success",
            ],
            "critical": [
                "Urgent: Review churned customers",
                "Implement retention playbook",
                "Consider pricing/offer changes",
            ],
        }

        return actions.get(level, [])

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
Extract and structure the recommendations from this revenue analysis:

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
                findings.append(f"Analyzed {wd['metrics']['row_count']} revenue metric records")

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

    def _classify_anomaly_severity(self, z_score: float) -> str:
        """Classify anomaly severity"""
        if z_score > 4:
            return "critical"
        elif z_score > 3:
            return "high"
        elif z_score > 2:
            return "medium"
        else:
            return "low"
