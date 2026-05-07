"""
Orchestrator Agent

Coordinates all domain agents to provide holistic business intelligence.
Synthesizes insights, prioritizes recommendations, and resolves conflicts.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from collections import defaultdict

from agents.base.base_agent import (
    BaseAgent,
    Recommendation,
    AnalysisResult,
    InsightType,
    ImpactLevel,
    UrgencyLevel,
    EffortLevel,
)
from agents.domain import SalesAgent, OperationsAgent, CustomerAgent, RevenueAgent
from config.agent_prompts import ORCHESTRATOR_SYSTEM


class OrchestratorAgent:
    """Meta-agent that coordinates domain agents"""

    def __init__(
        self,
        sales_agent: SalesAgent,
        operations_agent: OperationsAgent,
        customer_agent: CustomerAgent,
        revenue_agent: RevenueAgent,
        llm_adapter=None,
    ):
        self.agent_id = f"orchestrator_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        self.llm = llm_adapter

        # Domain agents
        self.agents = {
            "sales": sales_agent,
            "operations": operations_agent,
            "customer": customer_agent,
            "revenue": revenue_agent,
        }

        # Prioritization weights
        self.weights = {
            "confidence": 0.3,
            "impact": 0.3,
            "urgency": 0.25,
            "effort": 0.15,
        }

    async def analyze_all_domains(
        self,
        query: str,
        domains: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run analysis across all or specified domains"""

        domains = domains or list(self.agents.keys())
        context = context or {}

        # Run analyses in parallel
        import asyncio

        tasks = []
        for domain in domains:
            if domain in self.agents:
                task = self.agents[domain].analyze_data(
                    data=context.get(f"{domain}_data", {}),
                    query=query,
                    context=context,
                )
                tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful results
        domain_results = {}
        all_recommendations = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                continue

            domain = domains[i]
            domain_results[domain] = result
            all_recommendations.extend(result.recommendations)

        # Synthesize and prioritize
        synthesis = await self._synthesize_insights(
            domain_results=domain_results,
            query=query,
        )

        # Prioritize recommendations
        prioritized = self._prioritize_recommendations(all_recommendations)

        # Identify cross-domain opportunities
        cross_domain = self._identify_cross_domain_opportunities(domain_results)

        # Generate executive summary
        executive_summary = await self._generate_executive_summary(
            synthesis=synthesis,
            prioritized=prioritized,
            cross_domain=cross_domain,
        )

        return {
            "orchestrator_id": self.agent_id,
            "query": query,
            "domain_results": {
                domain: {
                    "summary": r.summary,
                    "confidence": r.confidence,
                    "recommendation_count": len(r.recommendations),
                    "key_findings": r.key_findings,
                }
                for domain, r in domain_results.items()
            },
            "synthesis": synthesis,
            "prioritized_recommendations": [
                r.to_dict() for r in prioritized[:20]
            ],
            "cross_domain_opportunities": cross_domain,
            "executive_summary": executive_summary,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _synthesize_insights(
        self,
        domain_results: Dict[str, AnalysisResult],
        query: str,
    ) -> Dict[str, Any]:
        """Synthesize insights from all domain analyses"""

        # Gather all insights
        all_insights = {
            "sales": [],
            "operations": [],
            "customer": [],
            "revenue": [],
        }

        for domain, result in domain_results.items():
            all_insights[domain] = result.key_findings

        # Build synthesis prompt
        prompt = f"""
## Query
{query}

## Domain Analysis Results

### Sales Agent
- Summary: {domain_results.get('sales', type('obj', (object,), {'summary': 'N/A'})()).summary}
- Key Findings: {all_insights['sales']}

### Operations Agent
- Summary: {domain_results.get('operations', type('obj', (object,), {'summary': 'N/A'})()).summary}
- Key Findings: {all_insights['operations']}

### Customer Agent
- Summary: {domain_results.get('customer', type('obj', (object,), {'summary': 'N/A'})()).summary}
- Key Findings: {all_insights['customer']}

### Revenue Agent
- Summary: {domain_results.get('revenue', type('obj', (object,), {'summary': 'N/A'})()).summary}
- Key Findings: {all_insights['revenue']}

## Task
Provide a synthesis that:
1. Identifies common themes across domains
2. Highlights the most critical issues
3. Notes any contradictions or trade-offs
4. Prioritizes areas needing immediate attention

Return JSON with:
- overall_assessment
- critical_issues (array)
- common_themes (array)
- contradictions (array)
- priority_focus_areas (array)
"""

        try:
            response = await self.llm.generate(
                prompt,
                system_prompt=ORCHESTRATOR_SYSTEM,
                temperature=0.7,
            )

            # Try to parse as JSON
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                # Fallback: extract structured data from text
                return {
                    "overall_assessment": response[:500],
                    "critical_issues": [],
                    "common_themes": [],
                    "contradictions": [],
                    "priority_focus_areas": [],
                }

        except Exception as e:
            return {
                "overall_assessment": f"Unable to synthesize: {str(e)}",
                "critical_issues": [],
                "common_themes": [],
                "contradictions": [],
                "priority_focus_areas": [],
            }

    def _prioritize_recommendations(
        self,
        recommendations: List[Recommendation]
    ) -> List[Recommendation]:
        """Prioritize recommendations using scoring framework"""

        # Group by urgency first
        urgency_order = {
            UrgencyLevel.CRITICAL: 0,
            UrgencyLevel.HIGH: 1,
            UrgencyLevel.MEDIUM: 2,
            UrgencyLevel.LOW: 3,
        }

        # Sort by urgency, then by composite score
        prioritized = sorted(
            recommendations,
            key=lambda r: (
                urgency_order.get(r.urgency, 4),
                -r.composite_score,
            )
        )

        # Add ranking
        for i, rec in enumerate(prioritized):
            rec.tags["orchestrator_rank"] = i + 1

        return prioritized

    def _identify_cross_domain_opportunities(
        self,
        domain_results: Dict[str, AnalysisResult]
    ) -> List[Dict[str, Any]]:
        """Identify opportunities that span multiple domains"""

        opportunities = []

        # Check for related metrics across domains
        metric_relations = [
            {
                "name": "Revenue Growth & Customer Retention",
                "domains": ["sales", "customer", "revenue"],
                "description": "Balancing revenue growth with customer retention",
                "related_metrics": ["revenue_growth_rate", "customer_retention_rate", "churn_rate"],
            },
            {
                "name": "Inventory Optimization & Customer Satisfaction",
                "domains": ["operations", "customer"],
                "description": "Stock availability impacts customer satisfaction",
                "related_metrics": ["stockout_rate", "nps_score", "on_time_delivery_rate"],
            },
            {
                "name": "Pricing & Volume Optimization",
                "domains": ["sales", "revenue", "operations"],
                "description": "Balancing pricing with volume and capacity",
                "related_metrics": ["average_order_value", "total_revenue", "capacity_utilization"],
            },
        ]

        # Check which opportunities are relevant based on domain results
        for opp in metric_relations:
            relevant_domains = [
                d for d in opp["domains"]
                if d in domain_results
            ]

            if len(relevant_domains) >= 2:
                opportunities.append({
                    **opp,
                    "relevant_domains": relevant_domains,
                    "action": "Analyze trade-offs and optimize jointly",
                })

        return opportunities

    async def _generate_executive_summary(
        self,
        synthesis: Dict[str, Any],
        prioritized: List[Recommendation],
        cross_domain: List[Dict[str, Any]],
    ) -> str:
        """Generate executive summary"""

        # Count by urgency
        urgency_counts = defaultdict(int)
        for rec in prioritized:
            urgency_counts[rec.urgency.value] += 1

        # Get top recommendations
        top_actions = []
        for rec in prioritized[:5]:
            top_actions.append(f"- [{rec.urgency.value.upper()}] {rec.summary}")

        prompt = f"""
## Analysis Results

### Overall Assessment
{synthesis.get('overall_assessment', 'N/A')}

### Critical Issues
{json.dumps(synthesis.get('critical_issues', []), indent=2)}

### Urgency Breakdown
- Critical: {urgency_counts.get('critical', 0)}
- High: {urgency_counts.get('high', 0)}
- Medium: {urgency_counts.get('medium', 0)}
- Low: {urgency_counts.get('low', 0)}

### Top 5 Priority Actions
{chr(10).join(top_actions)}

### Cross-Domain Opportunities
{len(cross_domain)} opportunities identified

## Task
Generate a concise executive summary (3-5 sentences) that:
1. States the overall business health
2. Highlights the most critical items needing attention
3. Notes the number of actionable recommendations
4. Indicates any cross-domain opportunities

Focus on what executives need to know.
"""

        try:
            response = await self.llm.generate(
                prompt,
                system_prompt=ORCHESTRATOR_SYSTEM,
                temperature=0.7,
                max_tokens=500,
            )

            return response.strip()

        except Exception as e:
            # Fallback summary
            return f"""
Analysis complete across {len(synthesis)} domains. Identified {len(prioritized)} recommendations
with {urgency_counts.get('critical', 0)} critical and {urgency_counts.get('high', 0)} high-priority items.
{len(cross_domain)} cross-domain opportunities identified for coordinated action.
            """.strip()

    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all domain agents"""

        status = {}

        for domain, agent in self.agents.items():
            status[domain] = {
                "agent_id": agent.agent_id,
                "agent_type": agent.agent_type,
                "max_recommendations": agent.max_recommendations,
                "confidence_threshold": agent.confidence_threshold,
                "available": True,
            }

        return {
            "orchestrator_id": self.agent_id,
            "domain_agents": status,
            "total_domains": len(self.agents),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def resolve_conflicts(
        self,
        recommendations: List[Recommendation]
    ) -> List[Dict[str, Any]]:
        """Identify and resolve conflicting recommendations"""

        conflicts = []

        # Look for recommendations with opposing goals
        # Example: reduce costs vs increase investment
        for i, rec1 in enumerate(recommendations):
            for rec2 in recommendations[i+1:]:
                if self._are_conflicting(rec1, rec2):
                    conflicts.append({
                        "recommendation_1": {
                            "agent": rec1.agent_type,
                            "summary": rec1.summary,
                            "impact": rec1.impact.value,
                        },
                        "recommendation_2": {
                            "agent": rec2.agent_type,
                            "summary": rec2.summary,
                            "impact": rec2.impact.value,
                        },
                        "conflict_type": self._classify_conflict(rec1, rec2),
                        "resolution": await self._suggest_resolution(rec1, rec2),
                    })

        return conflicts

    def _are_conflicting(
        self,
        rec1: Recommendation,
        rec2: Recommendation
    ) -> bool:
        """Check if two recommendations conflict"""

        # Simple conflict detection based on keywords
        conflicts = [
            ("reduce", "increase"),
            ("lower", "raise"),
            ("cut", "invest"),
            ("decrease", "grow"),
            ("minimize", "maximize"),
        ]

        summary1 = rec1.summary.lower()
        summary2 = rec2.summary.lower()

        for word1, word2 in conflicts:
            if word1 in summary1 and word2 in summary2:
                return True
            if word2 in summary1 and word1 in summary2:
                return True

        return False

    def _classify_conflict(
        self,
        rec1: Recommendation,
        rec2: Recommendation
    ) -> str:
        """Classify the type of conflict"""

        if "price" in rec1.summary.lower() or "price" in rec2.summary.lower():
            return "pricing_trade_off"
        elif "cost" in rec1.summary.lower() or "cost" in rec2.summary.lower():
            return "cost_benefit_trade_off"
        elif "inventory" in rec1.summary.lower() or "inventory" in rec2.summary.lower():
            return "inventory_optimization_trade_off"
        else:
            return "resource_allocation_conflict"

    async def _suggest_resolution(
        self,
        rec1: Recommendation,
        rec2: Recommendation
    ) -> str:
        """Suggest resolution for conflicting recommendations"""

        prompt = f"""
Two agents have made conflicting recommendations:

Recommendation 1 (from {rec1.agent_type} agent):
- Summary: {rec1.summary}
- Impact: {rec1.impact.value}
- Confidence: {rec1.confidence}
- Urgency: {rec1.urgency.value}

Recommendation 2 (from {rec2.agent_type} agent):
- Summary: {rec2.summary}
- Impact: {rec2.impact.value}
- Confidence: {rec2.confidence}
- Urgency: {rec2.urgency.value}

Suggest a resolution that:
1. Acknowledges both perspectives
2. Considers the relative confidence and urgency
3. Proposes a balanced approach
4. Recommends which to prioritize if both can't be done

Be specific and actionable.
"""

        try:
            response = await self.llm.generate(
                prompt,
                system_prompt=ORCHESTRATOR_SYSTEM,
                temperature=0.7,
                max_tokens=300,
            )

            return response.strip()

        except Exception:
            # Fallback: prioritize by composite score
            if rec1.composite_score > rec2.composite_score:
                return f"Prioritize {rec1.agent_type} recommendation due to higher priority score"
            else:
                return f"Prioritize {rec2.agent_type} recommendation due to higher priority score"

    async def get_unified_dashboard(
        self,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get unified dashboard data across all domains"""

        if not query:
            query = "Provide comprehensive business overview"

        # Run comprehensive analysis
        analysis = await self.analyze_all_domains(query)

        # Get agent status
        status = await self.get_agent_status()

        return {
            "analysis": analysis,
            "agent_status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
