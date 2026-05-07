"""
Customer Agent

Analyzes customer behavior, sentiment, and engagement to drive retention,
satisfaction, and growth.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

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
from agents.tools import WarehouseTool, AnalyzerTool
from config.agent_prompts import CUSTOMER_AGENT_SYSTEM


class CustomerAgent(BaseAgent):
    """Customer Analytics Agent"""

    def __init__(
        self,
        llm_adapter=None,
        warehouse_tool: Optional[WarehouseTool] = None,
        analyzer: Optional[AnalyzerTool] = None,
        **kwargs
    ):
        super().__init__(
            agent_type="customer",
            llm_adapter=llm_adapter,
            **kwargs
        )

        self.warehouse = warehouse_tool
        self.analyzer = analyzer or AnalyzerTool()

        # Customer-specific metrics
        self.key_metrics = [
            "active_customers",
            "customer_retention_rate",
            "nps_score",
            "customer_satisfaction_score",
            "engagement_score",
            "feature_adoption_rate",
        ]

    def get_system_prompt(self) -> str:
        return CUSTOMER_AGENT_SYSTEM

    async def analyze_data(
        self,
        data: Dict[str, Any],
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """Analyze customer data and generate insights"""

        context = context or {}

        # Query warehouse for relevant data
        if self.warehouse:
            time_period = context.get("time_period", "last 30 days")

            # Get recent customer events
            customer_data = await self.warehouse.get_recent_events(
                domain="customer",
                hours=24 * 30,
                limit=1000,
            )

            # Get metrics
            metrics = await self.warehouse.get_metrics(
                domain="customer",
                metrics=self.key_metrics,
                time_period=time_period,
            )

            # Get trends
            trends = await self.warehouse.get_trends(
                domain="customer",
                metric="engagement_score",
                period="daily",
                days=30,
            )

            data["warehouse_data"] = {
                "customer_events": customer_data.to_summary() if customer_data else {},
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

    async def segment_customers(
        self,
        segmentation_type: str = "value"
    ) -> List[Dict[str, Any]]:
        """Segment customers based on specified criteria"""

        if not self.warehouse:
            return []

        if segmentation_type == "value":
            return await self._segment_by_value()
        elif segmentation_type == "behavior":
            return await self._segment_by_behavior()
        elif segmentation_type == "lifecycle":
            return await self._segment_by_lifecycle()
        else:
            return await self._segment_by_value()

    async def _segment_by_value(self) -> List[Dict[str, Any]]:
        """Segment customers by value (high, medium, low)"""

        query = """
        SELECT
            c.customer_id,
            COALESCE(SUM(s.revenue), 0) as total_revenue,
            COUNT(DISTINCT s.event_id) as purchase_count,
            COALESCE(AVG(s.revenue), 0) as avg_order_value,
            MAX(c.event_timestamp) as last_activity
        FROM `{{customer_table}}` c
        LEFT JOIN `{{sales_table}}` s ON c.customer_id = s.customer_id
            AND s.event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        WHERE c.event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        GROUP BY c.customer_id
        """

        result = await self.warehouse.query(query)

        if not result.data:
            return []

        # Calculate segment boundaries
        revenues = [r["total_revenue"] for r in result.data]
        revenues.sort(reverse=True)

        # Top 20% = high value
        high_value_threshold = revenues[int(len(revenues) * 0.2)] if revenues else 0
        # Bottom 40% = low value
        low_value_threshold = revenues[int(len(revenues) * 0.6)] if revenues else 0

        segments = {
            "high": [],
            "medium": [],
            "low": [],
        }

        for customer in result.data:
            revenue = customer["total_revenue"]

            if revenue >= high_value_threshold:
                segment = "high"
            elif revenue >= low_value_threshold:
                segment = "medium"
            else:
                segment = "low"

            segments[segment].append(customer)

        # Generate segment summaries
        return [
            {
                "segment": "high_value",
                "count": len(segments["high"]),
                "total_revenue": sum(c["total_revenue"] for c in segments["high"]),
                "avg_revenue": sum(c["total_revenue"] for c in segments["high"]) / len(segments["high"]) if segments["high"] else 0,
                "characteristics": "High revenue, frequent purchases",
                "recommended_actions": ["VIP support", "Early access to features", "Personal account manager"],
            },
            {
                "segment": "medium_value",
                "count": len(segments["medium"]),
                "total_revenue": sum(c["total_revenue"] for c in segments["medium"]),
                "avg_revenue": sum(c["total_revenue"] for c in segments["medium"]) / len(segments["medium"]) if segments["medium"] else 0,
                "characteristics": "Moderate revenue and purchase frequency",
                "recommended_actions": ["Targeted promotions", "Product recommendations", "Engagement campaigns"],
            },
            {
                "segment": "low_value",
                "count": len(segments["low"]),
                "total_revenue": sum(c["total_revenue"] for c in segments["low"]),
                "avg_revenue": sum(c["total_revenue"] for c in segments["low"]) / len(segments["low"]) if segments["low"] else 0,
                "characteristics": "Low revenue, infrequent purchases",
                "recommended_actions": ["Re-engagement campaigns", "Discount offers", "Onboarding support"],
            },
        ]

    async def _segment_by_behavior(self) -> List[Dict[str, Any]]:
        """Segment customers by behavior patterns"""

        query = """
        SELECT
            customer_id,
            COUNTIF(event_type = 'login') as login_count,
            COUNTIF(event_type = 'purchase') as purchase_count,
            COUNTIF(event_type = 'support') as support_count,
            COUNT(*) as total_events,
            AVG(satisfaction_score) as avg_satisfaction
        FROM `{{customer_table}}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
        GROUP BY customer_id
        HAVING total_events >= 5
        """

        result = await self.warehouse.query(query)

        if not result.data:
            return []

        segments = {
            "power_users": [],
            "regular_users": [],
            "at_risk": [],
            "dormant": [],
        }

        for customer in result.data:
            login_count = customer["login_count"] or 0
            purchase_count = customer["purchase_count"] or 0
            support_count = customer["support_count"] or 0
            satisfaction = customer["avg_satisfaction"] or 0

            # Classify based on behavior
            if purchase_count >= 5 and login_count >= 20:
                segment = "power_users"
            elif purchase_count >= 1 and login_count >= 5:
                segment = "regular_users"
            elif support_count > 3 or satisfaction < 3:
                segment = "at_risk"
            else:
                segment = "dormant"

            segments[segment].append(customer)

        return [
            {
                "segment": "power_users",
                "count": len(segments["power_users"]),
                "characteristics": "Frequent logins and purchases",
                "recommended_actions": ["Advocate program", "Beta testing invites", "Referral incentives"],
            },
            {
                "segment": "regular_users",
                "count": len(segments["regular_users"]),
                "characteristics": "Moderate engagement",
                "recommended_actions": ["Feature education", "Community engagement", "Progressive features"],
            },
            {
                "segment": "at_risk",
                "count": len(segments["at_risk"]),
                "characteristics": "High support tickets or low satisfaction",
                "recommended_actions": ["Proactive outreach", "Support quality review", "Retention offers"],
            },
            {
                "segment": "dormant",
                "count": len(segments["dormant"]),
                "characteristics": "Low engagement",
                "recommended_actions": ["Re-engagement campaigns", "Win-back offers", "Feature highlights"],
            },
        ]

    async def _segment_by_lifecycle(self) -> List[Dict[str, Any]]:
        """Segment customers by lifecycle stage"""

        # New (0-30 days), Active (31-90), Mature (91-180), At-risk (181+ with low activity)
        query = """
        SELECT
            customer_id,
            MIN(event_timestamp) as first_seen,
            MAX(event_timestamp) as last_seen,
            COUNT(*) as total_events,
            TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MIN(event_timestamp), DAY) as customer_age_days
        FROM `{{customer_table}}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 180 DAY)
        GROUP BY customer_id
        """

        result = await self.warehouse.query(query)

        if not result.data:
            return []

        segments = {
            "new": [],
            "active": [],
            "mature": [],
            "churned": [],
        }

        for customer in result.data:
            age = customer["customer_age_days"]
            last_activity = datetime.fromisoformat(customer["last_seen"])
            days_since_activity = (datetime.utcnow() - last_activity).days

            if age <= 30:
                segment = "new"
            elif days_since_activity > 30:
                segment = "churned"
            elif age <= 90:
                segment = "active"
            else:
                segment = "mature"

            segments[segment].append(customer)

        return [
            {
                "segment": "new",
                "count": len(segments["new"]),
                "characteristics": "Customers ≤ 30 days old",
                "recommended_actions": ["Onboarding flow", "Tutorial content", "Early success milestones"],
            },
            {
                "segment": "active",
                "count": len(segments["active"]),
                "characteristics": "Customers 31-90 days old, recent activity",
                "recommended_actions": ["Feature discovery", "Engagement encouragement", "Value reinforcement"],
            },
            {
                "segment": "mature",
                "count": len(segments["mature"]),
                "characteristics": "Customers > 90 days old",
                "recommended_actions": ["Advanced features", "Upsell opportunities", "Advocate programs"],
            },
            {
                "segment": "churned",
                "count": len(segments["churned"]),
                "characteristics": "No activity in 30+ days",
                "recommended_actions": ["Win-back campaigns", "Exit surveys", "Churn analysis"],
            },
        ]

    async def analyze_sentiment(
        self,
        time_period: str = "last 30 days"
    ) -> Dict[str, Any]:
        """Analyze customer sentiment trends"""

        if not self.warehouse:
            return {"error": "Warehouse not configured"}

        # Get satisfaction scores over time
        query = f"""
        SELECT
            DATE(event_timestamp) as date,
            AVG(satisfaction_score) as avg_satisfaction,
            AVG(nps_score) as avg_nps,
            COUNT(*) as response_count
        FROM `{{customer_table}}`
        WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
            AND satisfaction_score IS NOT NULL
        GROUP BY DATE(event_timestamp)
        ORDER BY date DESC
        """

        result = await self.warehouse.query(query)

        if not result.data:
            return {"error": "No sentiment data available"}

        # Calculate overall metrics
        all_satisfaction = [r["avg_satisfaction"] for r in result.data if r["avg_satisfaction"] is not None]
        all_nps = [r["avg_nps"] for r in result.data if r["avg_nps"] is not None]

        overall_satisfaction = sum(all_satisfaction) / len(all_satisfaction) if all_satisfaction else None
        overall_nps = sum(all_nps) / len(all_nps) if all_nps else None

        # Determine sentiment trend
        if len(all_satisfaction) >= 7:
            recent = all_satisfaction[:7]
            previous = all_satisfaction[7:14] if len(all_satisfaction) >= 14 else all_satisfaction[7:]

            if previous:
                recent_avg = sum(recent) / len(recent)
                previous_avg = sum(previous) / len(previous)

                if recent_avg > previous_avg + 0.2:
                    trend = "improving"
                elif recent_avg < previous_avg - 0.2:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"
        else:
            trend = "insufficient_data"

        # Classify sentiment
        if overall_satisfaction:
            if overall_satisfaction >= 4.5:
                sentiment_level = "excellent"
            elif overall_satisfaction >= 4.0:
                sentiment_level = "good"
            elif overall_satisfaction >= 3.5:
                sentiment_level = "satisfactory"
            elif overall_satisfaction >= 3.0:
                sentiment_level = "poor"
            else:
                sentiment_level = "critical"
        else:
            sentiment_level = "unknown"

        return {
            "overall_satisfaction": round(overall_satisfaction, 2) if overall_satisfaction else None,
            "overall_nps": round(overall_nps, 1) if overall_nps else None,
            "sentiment_level": sentiment_level,
            "trend": trend,
            "total_responses": sum(r["response_count"] for r in result.data),
            "daily_data": [
                {
                    "date": r["date"],
                    "satisfaction": round(r["avg_satisfaction"], 2) if r["avg_satisfaction"] else None,
                    "nps": round(r["avg_nps"], 1) if r["avg_nps"] else None,
                }
                for r in result.data[:30]
            ],
            "recommended_actions": self._get_sentiment_actions(sentiment_level, trend),
        }

    def _get_sentiment_actions(self, level: str, trend: str) -> List[str]:
        """Get recommended actions based on sentiment"""

        if level in ["poor", "critical"] or trend == "declining":
            return [
                "Conduct immediate customer feedback analysis",
                "Review recent product/service changes",
                "Increase support resources",
                "Create customer satisfaction improvement task force",
            ]
        elif level == "satisfactory":
            return [
                "Analyze detractors for common themes",
                "Implement targeted improvements",
                "Monitor satisfaction closely",
            ]
        elif trend == "improving":
            return [
                "Identify drivers of improvement",
                "Double down on successful initiatives",
                "Share learnings across teams",
            ]
        else:
            return [
                "Continue current engagement strategies",
                "Look for incremental improvements",
                "Monitor for changes",
            ]

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
Extract and structure the recommendations from this customer analysis:

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
                findings.append(f"Analyzed {wd['metrics']['row_count']} customer metric records")

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
