"""
Events Router

API endpoints for event ingestion and management.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ingestion.event_validator import EventType
from ingestion.stream_processor import StreamProcessor

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class IngestEventRequest(BaseModel):
    """Request to ingest a single event"""
    event_type: str = Field(..., description="Type of event")
    data: Dict[str, Any] = Field(..., description="Event data")
    source: Optional[str] = Field(None, description="Event source")


class IngestBatchRequest(BaseModel):
    """Request to ingest multiple events"""
    events: List[Dict[str, Any]] = Field(..., description="List of events")
    event_type: str = Field(..., description="Type of all events")


class IngestEventResponse(BaseModel):
    """Response from event ingestion"""
    success: bool
    event_id: Optional[str] = None
    error: Optional[str] = None


class IngestBatchResponse(BaseModel):
    """Response from batch event ingestion"""
    processed: int
    invalid: int
    events: List[Dict[str, Any]]
    invalid_events: List[Dict[str, Any]]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/", response_model=IngestEventResponse)
async def ingest_event(request: IngestEventRequest):
    """Ingest a single event"""

    try:
        # This would use the actual stream processor
        # For now, return mock response

        event_id = f"evt_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

        return IngestEventResponse(
            success=True,
            event_id=event_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/batch", response_model=IngestBatchResponse)
async def ingest_batch(request: IngestBatchRequest):
    """Ingest multiple events in batch"""

    try:
        # Validate events
        # In production, this would use EventValidator

        processed = len(request.events)
        invalid = 0

        return IngestBatchResponse(
            processed=processed,
            invalid=invalid,
            events=request.events,
            invalid_events=[],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/types")
async def get_event_types():
    """Get available event types"""

    return {
        "event_types": [
            {
                "type": "sale",
                "description": "Sales and transaction events",
                "fields": ["customer_id", "product_id", "revenue", "quantity", "channel"],
            },
            {
                "type": "operation",
                "description": "Operations and inventory events",
                "fields": ["inventory_level", "product_id", "warehouse_id", "fulfillment_time"],
            },
            {
                "type": "customer",
                "description": "Customer behavior and feedback events",
                "fields": ["customer_id", "event_type", "satisfaction_score", "nps_score"],
            },
            {
                "type": "revenue",
                "description": "Revenue and financial events",
                "fields": ["revenue_type", "amount", "arr"],
            },
        ]
    }


@router.get("/stats")
async def get_ingestion_stats():
    """Get ingestion statistics"""

    return {
        "total_events": 15234,
        "events_today": 842,
        "events_by_type": {
            "sale": 5234,
            "operation": 4123,
            "customer": 3512,
            "revenue": 2365,
        },
        "validation_rate": 98.5,
        "last_event": datetime.utcnow().isoformat(),
    }
