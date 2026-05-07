"""
Event Validator

Validates incoming events before processing.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class EventType(str, Enum):
    """Types of business events"""
    SALE = "sale"
    OPERATION = "operation"
    CUSTOMER = "customer"
    REVENUE = "revenue"
    SYSTEM = "system"


class SaleEvent(BaseModel):
    """Sale event schema"""
    customer_id: str
    product_id: str
    revenue: float = Field(gt=0)
    quantity: int = Field(gt=0)
    channel: str
    timestamp: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class OperationEvent(BaseModel):
    """Operations event schema"""
    inventory_level: int = Field(ge=0)
    product_id: str
    warehouse_id: str
    fulfillment_time_hours: float = Field(ge=0)
    timestamp: datetime


class CustomerEvent(BaseModel):
    """Customer event schema"""
    customer_id: str
    event_type: str  # login, purchase, support, review
    satisfaction_score: Optional[int] = Field(None, ge=1, le=5)
    nps_score: Optional[int] = Field(None, ge=0, le=10)
    timestamp: datetime


class RevenueEvent(BaseModel):
    """Revenue event schema"""
    revenue_type: str  # recurring, one_time, expansion, churn
    amount: float
    arr: Optional[float] = Field(None, ge=0)
    timestamp: datetime


class EventValidator:
    """Validates incoming events"""

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.validation_stats = {
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "errors": {},
        }

    def validate_event(
        self,
        event_data: Dict[str, Any],
        event_type: EventType
    ) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Validate an event

        Returns:
            (is_valid, error_message, cleaned_data)
        """

        self.validation_stats["total"] += 1

        try:
            # Normalize event type
            event_data = self._normalize_event(event_data)

            # Validate based on type
            if event_type == EventType.SALE:
                validated = SaleEvent(**event_data)
            elif event_type == EventType.OPERATION:
                validated = OperationEvent(**event_data)
            elif event_type == EventType.CUSTOMER:
                validated = CustomerEvent(**event_data)
            elif event_type == EventType.REVENUE:
                validated = RevenueEvent(**event_data)
            else:
                # Generic event - basic validation only
                self._validate_generic(event_data)
                validated = event_data

            self.validation_stats["valid"] += 1
            return True, None, validated.dict() if hasattr(validated, "dict") else validated

        except Exception as e:
            self.validation_stats["invalid"] += 1
            error_type = type(e).__name__
            self.validation_stats["errors"][error_type] = \
                self.validation_stats["errors"].get(error_type, 0) + 1

            if self.strict_mode:
                raise

            return False, str(e), None

    def _normalize_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize event data"""

        normalized = event_data.copy()

        # Ensure timestamp is datetime
        if "timestamp" in normalized:
            if isinstance(normalized["timestamp"], str):
                normalized["timestamp"] = datetime.fromisoformat(
                    normalized["timestamp"].replace("Z", "+00:00")
                )
            elif isinstance(normalized["timestamp"], (int, float)):
                # Unix timestamp
                normalized["timestamp"] = datetime.fromtimestamp(normalized["timestamp"])

        # Ensure event_timestamp exists
        if "event_timestamp" not in normalized and "timestamp" in normalized:
            normalized["event_timestamp"] = normalized["timestamp"]

        # Add event_timestamp if missing
        if "event_timestamp" not in normalized:
            normalized["event_timestamp"] = datetime.utcnow()

        return normalized

    def _validate_generic(self, event_data: Dict[str, Any]):
        """Basic validation for generic events"""

        if not event_data:
            raise ValueError("Event data is empty")

        if "event_timestamp" not in event_data and "timestamp" not in event_data:
            raise ValueError("Event must have a timestamp")

        if "event_type" not in event_data and "type" not in event_data:
            raise ValueError("Event must have an event_type")

    def validate_batch(
        self,
        events: List[Dict[str, Any]],
        event_type: EventType
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Validate a batch of events

        Returns:
            (valid_events, invalid_events_with_errors)
        """

        valid = []
        invalid = []

        for event_data in events:
            is_valid, error, cleaned = self.validate_event(event_data, event_type)

            if is_valid:
                valid.append(cleaned)
            else:
                invalid.append({
                    "event": event_data,
                    "error": error,
                })

        return valid, invalid

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""

        total = self.validation_stats["total"]
        valid = self.validation_stats["valid"]

        return {
            **self.validation_stats,
            "valid_rate": round(valid / total * 100, 2) if total > 0 else 0,
        }

    def reset_stats(self):
        """Reset validation statistics"""
        self.validation_stats = {
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "errors": {},
        }


class EventEnricher:
    """Enriches events with additional context"""

    def __init__(self, warehouse_client=None):
        self.warehouse = warehouse_client

    async def enrich_event(
        self,
        event: Dict[str, Any],
        event_type: EventType
    ) -> Dict[str, Any]:
        """Enrich an event with additional context"""

        enriched = event.copy()

        # Add metadata
        enriched["ingested_at"] = datetime.utcnow().isoformat()
        enriched["event_id"] = self._generate_event_id(event, event_type)

        # Add domain
        enriched["domain"] = self._get_domain(event_type)

        # Add enrichment based on type
        if event_type == EventType.SALE:
            enriched = await self._enrich_sale(enriched)
        elif event_type == EventType.CUSTOMER:
            enriched = await self._enrich_customer(enriched)

        return enriched

    def _generate_event_id(self, event: Dict[str, Any], event_type: EventType) -> str:
        """Generate unique event ID"""
        import hashlib

        content = f"{event_type.value}_{event.get('timestamp', '')}_{str(event)}"
        hash_obj = hashlib.md5(content.encode())
        return f"evt_{hash_obj.hexdigest()[:16]}"

    def _get_domain(self, event_type: EventType) -> str:
        """Get domain for event type"""
        return event_type.value

    async def _enrich_sale(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich sale event"""

        # Calculate total value
        if "total_value" not in event:
            event["total_value"] = event.get("revenue", 0) * event.get("quantity", 1)

        # Add time fields
        if event.get("timestamp"):
            ts = event["timestamp"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            event["hour"] = ts.hour
            event["day_of_week"] = ts.weekday()
            event["is_weekend"] = ts.weekday() >= 5

        return event

    async def _enrich_customer(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich customer event"""

        # Calculate sentiment
        satisfaction = event.get("satisfaction_score")
        nps = event.get("nps_score")

        if satisfaction:
            if satisfaction >= 4:
                event["sentiment"] = "positive"
            elif satisfaction == 3:
                event["sentiment"] = "neutral"
            else:
                event["sentiment"] = "negative"

        if nps is not None:
            if nps >= 9:
                event["nps_category"] = "promoter"
            elif nps >= 7:
                event["nps_category"] = "passive"
            else:
                event["nps_category"] = "detractor"

        return event
