"""
FastAPI Application

Main API application for Opsora.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import settings
from api.routers import events as events_router
from api.routers import recommendations as recommendations_router
from api.routers import analytics as analytics_router
from api.routers import agents as agents_router
from api.websocket.stream import WebSocketManager


# Global state
agents = None
orchestrator = None
websocket_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""

    # Startup
    global agents, orchestrator, websocket_manager

    # Initialize agents
    from agents import (
        SalesAgent,
        OperationsAgent,
        CustomerAgent,
        RevenueAgent,
        OrchestratorAgent,
        create_llm_adapter,
        WarehouseTool,
    )

    # Create LLM adapter
    try:
        llm_adapter = create_llm_adapter(
            provider=settings.llm.provider,
            anthropic_api_key=settings.llm.anthropic_api_key,
            anthropic_model=settings.llm.anthropic_model,
            openai_api_key=settings.llm.openai_api_key,
            openai_model=settings.llm.openai_model,
            glm_api_key=settings.llm.glm_api_key if hasattr(settings.llm, 'glm_api_key') else "",
            glm_model=settings.llm.glm_model if hasattr(settings.llm, 'glm_model') else "glm-4-flash",
            glm_base_url=settings.llm.glm_base_url if hasattr(settings.llm, 'glm_base_url') else "https://open.bigmodel.cn/api/paas/v4/",
            local_base_url=settings.llm.local_base_url,
            local_model=settings.llm.local_model,
        )
    except Exception as e:
        print(f"Warning: Could not create LLM adapter: {e}")
        llm_adapter = None

    # Create warehouse tool
    warehouse = WarehouseTool(
        project_id=settings.gcp.project_id,
        dataset=settings.gcp.bigquery_dataset,
        location=settings.gcp.region,
    )

    # Initialize domain agents
    agents = {
        "sales": SalesAgent(llm_adapter=llm_adapter, warehouse_tool=warehouse),
        "operations": OperationsAgent(llm_adapter=llm_adapter, warehouse_tool=warehouse),
        "customer": CustomerAgent(llm_adapter=llm_adapter, warehouse_tool=warehouse),
        "revenue": RevenueAgent(llm_adapter=llm_adapter, warehouse_tool=warehouse),
    }

    # Initialize orchestrator
    orchestrator = OrchestratorAgent(
        sales_agent=agents["sales"],
        operations_agent=agents["operations"],
        customer_agent=agents["customer"],
        revenue_agent=agents["revenue"],
        llm_adapter=llm_adapter,
    )

    # Initialize WebSocket manager
    websocket_manager = WebSocketManager()

    print("Opsora API started successfully")

    yield

    # Shutdown
    print("Opsora API shutting down")


# Create FastAPI app
app = FastAPI(
    title="Opsora API",
    description="Agentic AI Business Analytics & Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# DEPENDENCIES
# =============================================================================

def get_settings():
    """Get settings instance"""
    return settings


def get_agents():
    """Get agents instance"""
    if agents is None:
        raise HTTPException(status_code=503, detail="Agents not initialized")
    return agents


def get_orchestrator():
    """Get orchestrator instance"""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return orchestrator


def get_websocket_manager():
    """Get WebSocket manager"""
    if websocket_manager is None:
        raise HTTPException(status_code=503, detail="WebSocket manager not initialized")
    return websocket_manager


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "agents_initialized": agents is not None,
        "orchestrator_initialized": orchestrator is not None,
    }


# =============================================================================
# INCLUDE ROUTERS
# =============================================================================

app.include_router(events_router.router, prefix="/v1/events", tags=["Events"])
app.include_router(recommendations_router.router, prefix="/v1/recommendations", tags=["Recommendations"])
app.include_router(analytics_router.router, prefix="/v1/analytics", tags=["Analytics"])
app.include_router(agents_router.router, prefix="/v1/agents", tags=["Agents"])


# =============================================================================
# WEBSOCKET ENDPOINT
# =============================================================================

@app.websocket("/v1/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""

    manager = get_websocket_manager()
    await manager.connect(websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            # Handle different message types
            message_type = data.get("type")

            if message_type == "subscribe":
                # Subscribe to updates
                channels = data.get("channels", [])
                for channel in channels:
                    await manager.subscribe(websocket, channel)

                await websocket.send_json({
                    "type": "subscribed",
                    "channels": channels,
                })

            elif message_type == "unsubscribe":
                # Unsubscribe from updates
                channels = data.get("channels", [])
                for channel in channels:
                    await manager.unsubscribe(websocket, channel)

                await websocket.send_json({
                    "type": "unsubscribed",
                    "channels": channels,
                })

            elif message_type == "ping":
                # Ping/pong for connection health
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e),
        })
        manager.disconnect(websocket)


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "type": "http_error",
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": str(exc),
                "type": "internal_error",
            }
        },
    )


# =============================================================================
# DASHBOARD ENDPOINTS
# =============================================================================

@app.get("/v1/dashboard/overview")
async def get_dashboard_overview(
    orchestrator: Any = Depends(get_orchestrator),
):
    """Get dashboard overview data"""

    try:
        overview = await orchestrator.get_unified_dashboard(
            query="Provide comprehensive business overview"
        )

        return overview

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/dashboard/metrics")
async def get_dashboard_metrics(
    period: str = "last_7d",
    agents_dict: Dict = Depends(get_agents),
):
    """Get metrics for dashboard"""

    try:
        # In production, this would query actual metrics from warehouse
        # For now, return mock data structure

        return {
            "period": period,
            "generated_at": datetime.utcnow().isoformat(),
            "metrics": {
                "sales": {
                    "revenue": 125000,
                    "growth_rate": 15.3,
                    "trend": "up",
                },
                "operations": {
                    "inventory_turnover": 4.2,
                    "fulfillment_time": 24.5,
                    "trend": "stable",
                },
                "customers": {
                    "active": 2340,
                    "nps": 42,
                    "trend": "up",
                },
                "revenue": {
                    "mrr": 85000,
                    "arr": 1020000,
                    "nrr": 112,
                },
            },
            "recommendations": {
                "total": 23,
                "critical": 2,
                "high": 5,
                "medium": 12,
                "low": 4,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ROOT ENDPOINT
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Opsora API",
        "version": "1.0.0",
        "description": "Agentic AI Business Analytics & Intelligence",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
    )
