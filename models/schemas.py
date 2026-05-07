"""
Data Schemas

Core data models for the Opsora platform.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


# =============================================================================
# EVENT SCHEMAS
# =============================================================================

class EventType(str, Enum):
    """Types of business events"""
    SALE = "sale"
    OPERATION = "operation"
    CUSTOMER = "customer"
    REVENUE = "revenue"
    SYSTEM = "system"


class Event(BaseModel):
    """Business event data"""
    event_id: str
    event_type: EventType
    event_timestamp: datetime
    domain: str
    data: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None
    processed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


# =============================================================================
# RECOMMENDATION SCHEMAS
# =============================================================================

class RecommendationStatus(str, Enum):
    """Status of a recommendation"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class RecommendationSource(BaseModel):
    """Source of a recommendation"""
    agent_id: str
    agent_type: str
    model_version: Optional[str] = None
    confidence: float = Field(ge=0, le=1)
    reasoning: Optional[str] = None


class Recommendation(BaseModel):
    """AI-generated recommendation"""
    recommendation_id: str
    title: str
    description: str

    # Classification
    insight_type: str  # alert, suggestion, automation, insight
    domain: str  # sales, operations, customer, revenue
    category: Optional[str] = None

    # Scoring
    confidence: float = Field(ge=0, le=1)
    impact: str  # low, medium, high
    urgency: str  # low, medium, high, critical
    effort: str  # easy, moderate, complex
    composite_score: float = Field(ge=0, le=1)

    # Details
    expected_outcome: Optional[str] = None
    expected_impact_value: Optional[float] = None  # Quantified impact
    rationale: str

    # Targeting
    stakeholders: List[str] = Field(default_factory=list)
    metrics_affected: List[str] = Field(default_factory=list)
    tags: Dict[str, str] = Field(default_factory=dict)

    # Source
    source: RecommendationSource

    # Lifecycle
    status: RecommendationStatus = RecommendationStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    # Execution
    action_taken: Optional[str] = None
    action_result: Optional[Dict[str, Any]] = None
    feedback: Optional[str] = None
    actual_impact: Optional[float] = None

    class Config:
        use_enum_values = True


class RecommendationFilter(BaseModel):
    """Filter for querying recommendations"""
    domains: Optional[List[str]] = None
    insight_types: Optional[List[str]] = None
    status: Optional[List[RecommendationStatus]] = None
    min_confidence: Optional[float] = None
    min_score: Optional[float] = None
    urgency: Optional[List[str]] = None
    impact: Optional[List[str]] = None
    agent_types: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    stakeholders: Optional[List[str]] = None
    tags: Optional[Dict[str, str]] = None
    limit: int = 50
    offset: int = 0


# =============================================================================
# ACTION SCHEMAS
# =============================================================================

class ActionStatus(str, Enum):
    """Status of an action"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Action(BaseModel):
    """Action taken based on a recommendation"""
    action_id: str
    recommendation_id: str
    action_type: str  # manual, automated, workflow
    description: str

    # Execution details
    executor: Optional[str] = None  # User or system
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Status
    status: ActionStatus = ActionStatus.PENDING
    progress: float = Field(default=0, ge=0, le=100)

    # Results
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    logs: List[str] = Field(default_factory=list)

    # Impact tracking
    expected_impact: Optional[float] = None
    actual_impact: Optional[float] = None
    impact_measured_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


# =============================================================================
# DASHBOARD METRICS
# =============================================================================

class MetricDataPoint(BaseModel):
    """Single metric data point"""
    timestamp: datetime
    value: float
    metadata: Optional[Dict[str, Any]] = None


class DomainMetrics(BaseModel):
    """Metrics for a specific domain"""
    domain: str
    metric_name: str
    current_value: float
    previous_value: Optional[float] = None
    change_percent: Optional[float] = None
    trend: Optional[str] = None  # up, down, stable
    data_points: List[MetricDataPoint] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class DashboardMetrics(BaseModel):
    """Aggregated dashboard metrics"""
    period: str  # last_24h, last_7d, last_30d
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Domain metrics
    sales_metrics: List[DomainMetrics] = Field(default_factory=list)
    operations_metrics: List[DomainMetrics] = Field(default_factory=list)
    customer_metrics: List[DomainMetrics] = Field(default_factory=list)
    revenue_metrics: List[DomainMetrics] = Field(default_factory=list)

    # Summary stats
    total_recommendations: int = 0
    active_alerts: int = 0
    pending_actions: int = 0
    completed_actions: int = 0

    # Agent status
    agents_active: int = 0
    agents_total: int = 0


# =============================================================================
# ANALYTICS QUERY
# =============================================================================

class AnalyticsQuery(BaseModel):
    """Query for analytics data"""
    metric: str
    domain: str
    time_period: str = "last_30_days"
    group_by: Optional[str] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    aggregations: List[str] = Field(default_factory=lambda: ["avg", "min", "max", "count"])
    limit: int = 100


class AnalyticsResult(BaseModel):
    """Result of analytics query"""
    query: AnalyticsQuery
    data: List[Dict[str, Any]]
    total_rows: int
    execution_time_ms: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
