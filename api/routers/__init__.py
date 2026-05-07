"""API Routers Package"""

# Explicitly import each router module to avoid circular imports
from api.routers import events
from api.routers import recommendations
from api.routers import analytics
from api.routers import agents

__all__ = [
    "events",
    "recommendations",
    "analytics",
    "agents",
]
