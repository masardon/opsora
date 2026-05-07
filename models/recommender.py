"""
Recommendation Engine

Core engine for scoring, ranking, and managing recommendations.
"""

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from collections import defaultdict
import asyncio

from models.schemas import (
    Recommendation,
    RecommendationFilter,
    RecommendationStatus,
    RecommendationSource,
    Action,
    ActionStatus,
)


class ScoringStrategy(str, Enum):
    """Scoring strategies"""
    WEIGHTED = "weighted"           # Standard weighted scoring
    ML_BASED = "ml_based"           # Machine learning based
    BANDIT = "bandit"               # Multi-armed bandit
    RANKING = "ranking"             # Learning to rank


class PrioritizationStrategy(str, Enum):
    """Prioritization strategies"""
    SCORE_BASED = "score_based"     # By composite score
    URGENCY_FIRST = "urgency_first"  # By urgency then score
    IMPACT_FIRST = "impact_first"    # By impact then score
    EFFORT_AWARE = "effort_aware"    # Consider effort heavily
    STAKEHOLDER = "stakeholder"      # By stakeholder


class RecommendationEngine:
    """Engine for generating, scoring, and managing recommendations"""

    def __init__(
        self,
        scoring_weights: Optional[Dict[str, float]] = None,
        default_confidence_threshold: float = 0.7,
        auto_expire_hours: int = 168,  # 7 days
    ):
        self.scoring_weights = scoring_weights or {
            "confidence": 0.3,
            "impact": 0.3,
            "urgency": 0.25,
            "effort": 0.15,
        }

        self.confidence_threshold = default_confidence_threshold
        self.auto_expire_hours = auto_expire_hours

        # Storage (in production, use database)
        self._recommendations: Dict[str, Recommendation] = {}
        self._actions: Dict[str, Action] = {}

        # Bandit state for learning
        self._bandit_state: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"success": 0, "failure": 0}
        )

    def generate_id(self, content: str) -> str:
        """Generate deterministic ID from content"""
        hash_obj = hashlib.md5(content.encode())
        return f"rec_{hash_obj.hexdigest()[:12]}"

    def calculate_score(
        self,
        confidence: float,
        impact: str,
        urgency: str,
        effort: str,
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """Calculate composite score from components"""

        weights = weights or self.scoring_weights

        # Normalize impact (low=1, medium=2, high=3)
        impact_score = {"low": 1, "medium": 2, "high": 3}.get(impact.lower(), 2) / 3

        # Normalize urgency (low=1, medium=2, high=3, critical=4)
        urgency_score = {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(
            urgency.lower(), 2
        ) / 4

        # Normalize effort (easy=3, moderate=2, complex=1) - inverted
        effort_score = {"easy": 3, "moderate": 2, "complex": 1}.get(
            effort.lower(), 2
        ) / 3

        # Calculate weighted composite
        composite = (
            confidence * weights["confidence"] +
            impact_score * weights["impact"] +
            urgency_score * weights["urgency"] +
            effort_score * weights["effort"]
        )

        return round(composite, 3)

    async def create_recommendation(
        self,
        title: str,
        description: str,
        insight_type: str,
        domain: str,
        source: RecommendationSource,
        confidence: float,
        impact: str,
        urgency: str,
        effort: str,
        rationale: str,
        expected_outcome: Optional[str] = None,
        expected_impact_value: Optional[float] = None,
        stakeholders: Optional[List[str]] = None,
        metrics_affected: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None,
        category: Optional[str] = None,
    ) -> Recommendation:
        """Create a new recommendation"""

        # Calculate composite score
        composite_score = self.calculate_score(
            confidence=confidence,
            impact=impact,
            urgency=urgency,
            effort=effort,
        )

        # Create recommendation
        recommendation = Recommendation(
            recommendation_id=self.generate_id(f"{title}_{description}"),
            title=title,
            description=description,
            insight_type=insight_type,
            domain=domain,
            category=category,
            confidence=confidence,
            impact=impact,
            urgency=urgency,
            effort=effort,
            composite_score=composite_score,
            rationale=rationale,
            expected_outcome=expected_outcome,
            expected_impact_value=expected_impact_value,
            stakeholders=stakeholders or [],
            metrics_affected=metrics_affected or [],
            tags=tags or {},
            source=source,
            status=RecommendationStatus.PENDING,
        )

        # Store
        self._recommendations[recommendation.recommendation_id] = recommendation

        return recommendation

    async def batch_create_recommendations(
        self,
        recommendations_data: List[Dict[str, Any]]
    ) -> List[Recommendation]:
        """Create multiple recommendations in batch"""

        tasks = [
            self.create_recommendation(**data)
            for data in recommendations_data
        ]

        return await asyncio.gather(*tasks)

    def get_recommendation(
        self,
        recommendation_id: str
    ) -> Optional[Recommendation]:
        """Get a recommendation by ID"""
        return self._recommendations.get(recommendation_id)

    def query_recommendations(
        self,
        filter: RecommendationFilter
    ) -> Tuple[List[Recommendation], int]:
        """Query recommendations with filters"""

        # Start with all recommendations
        results = list(self._recommendations.values())

        # Apply filters
        if filter.domains:
            results = [r for r in results if r.domain in filter.domains]

        if filter.insight_types:
            results = [r for r in results if r.insight_type in filter.insight_types]

        if filter.status:
            results = [r for r in results if r.status in filter.status]

        if filter.min_confidence:
            results = [r for r in results if r.confidence >= filter.min_confidence]

        if filter.min_score:
            results = [r for r in results if r.composite_score >= filter.min_score]

        if filter.urgency:
            results = [r for r in results if r.urgency in filter.urgency]

        if filter.impact:
            results = [r for r in results if r.impact in filter.impact]

        if filter.agent_types:
            results = [
                r for r in results
                if r.source.agent_type in filter.agent_types
            ]

        if filter.stakeholders:
            results = [
                r for r in results
                if any(s in r.stakeholders for s in filter.stakeholders)
            ]

        if filter.tags:
            results = [
                r for r in results
                if all(r.tags.get(k) == v for k, v in filter.tags.items())
            ]

        if filter.date_from:
            results = [r for r in results if r.created_at >= filter.date_from]

        if filter.date_to:
            results = [r for r in results if r.created_at <= filter.date_to]

        # Sort by score descending
        results.sort(key=lambda r: r.composite_score, reverse=True)

        # Pagination
        total = len(results)
        start = filter.offset
        end = start + filter.limit
        paginated = results[start:end]

        return paginated, total

    def prioritize_recommendations(
        self,
        recommendations: List[Recommendation],
        strategy: PrioritizationStrategy = PrioritizationStrategy.SCORE_BASED,
        limit: int = 20
    ) -> List[Recommendation]:
        """Prioritize recommendations using specified strategy"""

        if strategy == PrioritizationStrategy.SCORE_BASED:
            prioritized = sorted(
                recommendations,
                key=lambda r: (r.composite_score, r.confidence),
                reverse=True
            )

        elif strategy == PrioritizationStrategy.URGENCY_FIRST:
            urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            prioritized = sorted(
                recommendations,
                key=lambda r: (
                    urgency_order.get(r.urgency, 4),
                    -r.composite_score
                )
            )

        elif strategy == PrioritizationStrategy.IMPACT_FIRST:
            impact_order = {"high": 0, "medium": 1, "low": 2}
            prioritized = sorted(
                recommendations,
                key=lambda r: (
                    impact_order.get(r.impact, 3),
                    -r.composite_score
                )
            )

        elif strategy == PrioritizationStrategy.EFFORT_AWARE:
            # Weight effort more heavily
            effort_order = {"easy": 0, "moderate": 1, "complex": 2}
            prioritized = sorted(
                recommendations,
                key=lambda r: (
                    effort_order.get(r.effort, 3),
                    -r.composite_score
                )
            )

        elif strategy == PrioritizationStrategy.STAKEHOLDER:
            # Prioritize by stakeholder (executive > manager > individual)
            def stakeholder_priority(r: Recommendation) -> int:
                if any("executive" in s.lower() or "ceo" in s.lower()
                       for s in r.stakeholders):
                    return 0
                elif any("manager" in s.lower() or "director" in s.lower()
                         for s in r.stakeholders):
                    return 1
                else:
                    return 2

            prioritized = sorted(
                recommendations,
                key=lambda r: (stakeholder_priority(r), -r.composite_score)
            )

        else:
            prioritized = recommendations

        return prioritized[:limit]

    async def update_recommendation_status(
        self,
        recommendation_id: str,
        status: RecommendationStatus,
        feedback: Optional[str] = None,
        actual_impact: Optional[float] = None,
    ) -> Optional[Recommendation]:
        """Update recommendation status"""

        rec = self._recommendations.get(recommendation_id)
        if not rec:
            return None

        rec.status = status
        rec.updated_at = datetime.utcnow()

        if feedback:
            rec.feedback = feedback

        if actual_impact is not None:
            rec.actual_impact = actual_impact

            # Update bandit state
            if actual_impact > 0:
                self._bandit_state[rec.domain]["success"] += 1
            else:
                self._bandit_state[rec.domain]["failure"] += 1

        return rec

    async def expire_old_recommendations(self) -> int:
        """Expire recommendations older than threshold"""

        cutoff = datetime.utcnow() - timedelta(hours=self.auto_expire_hours)
        expired_count = 0

        for rec in self._recommendations.values():
            if rec.status == RecommendationStatus.PENDING and rec.created_at < cutoff:
                rec.status = RecommendationStatus.ARCHIVED
                rec.updated_at = datetime.utcnow()
                expired_count += 1

        return expired_count

    async def create_action(
        self,
        recommendation_id: str,
        action_type: str,
        description: str,
        executor: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> Action:
        """Create an action based on a recommendation"""

        rec = self._recommendations.get(recommendation_id)
        if not rec:
            raise ValueError(f"Recommendation {recommendation_id} not found")

        action = Action(
            action_id=f"act_{uuid.uuid4().hex[:12]}",
            recommendation_id=recommendation_id,
            action_type=action_type,
            description=description,
            executor=executor,
            scheduled_at=scheduled_at,
            expected_impact=rec.expected_impact_value,
        )

        self._actions[action.action_id] = action

        # Update recommendation
        rec.action_taken = description
        rec.updated_at = datetime.utcnow()

        return action

    async def update_action_status(
        self,
        action_id: str,
        status: ActionStatus,
        progress: Optional[float] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Action]:
        """Update action status"""

        action = self._actions.get(action_id)
        if not action:
            return None

        action.status = status
        action.updated_at = datetime.utcnow()

        if progress is not None:
            action.progress = progress

        if result is not None:
            action.result = result

        if error_message is not None:
            action.error_message = error_message

        # Handle status transitions
        if status == ActionStatus.RUNNING and not action.started_at:
            action.started_at = datetime.utcnow()

        elif status == ActionStatus.COMPLETED:
            action.completed_at = datetime.utcnow()
            action.progress = 100

        return action

    def get_statistics(self) -> Dict[str, Any]:
        """Get recommendation and action statistics"""

        recs = list(self._recommendations.values())
        actions = list(self._actions.values())

        # Count by status
        rec_by_status = defaultdict(int)
        for rec in recs:
            rec_by_status[rec.status.value] += 1

        action_by_status = defaultdict(int)
        for act in actions:
            action_by_status[act.status.value] += 1

        # Count by domain
        rec_by_domain = defaultdict(int)
        for rec in recs:
            rec_by_domain[rec.domain] += 1

        # Count by urgency
        rec_by_urgency = defaultdict(int)
        for rec in recs:
            rec_by_urgency[rec.urgency] += 1

        # Average scores
        avg_confidence = sum(r.confidence for r in recs) / len(recs) if recs else 0
        avg_score = sum(r.composite_score for r in recs) / len(recs) if recs else 0

        # Bandit stats
        bandit_stats = dict(self._bandit_state)

        return {
            "recommendations": {
                "total": len(recs),
                "by_status": dict(rec_by_status),
                "by_domain": dict(rec_by_domain),
                "by_urgency": dict(rec_by_urgency),
                "avg_confidence": round(avg_confidence, 3),
                "avg_score": round(avg_score, 3),
            },
            "actions": {
                "total": len(actions),
                "by_status": dict(action_by_status),
            },
            "bandit_state": bandit_stats,
        }

    def get_recommendations_for_dashboard(
        self,
        limit: int = 50
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get recommendations organized for dashboard display"""

        filter_obj = RecommendationFilter(
            status=[RecommendationStatus.PENDING],
            limit=limit * 2,
        )

        results, _ = self.query_recommendations(filter_obj)

        # Organize by urgency
        by_urgency = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
        }

        for rec in results:
            by_urgency[rec.urgency].append(rec.to_dict())

        # Get recent actions
        recent_actions = sorted(
            self._actions.values(),
            key=lambda a: a.created_at,
            reverse=True
        )[:10]

        return {
            "by_urgency": by_urgency,
            "recent_actions": [a.dict() for a in recent_actions],
        }
