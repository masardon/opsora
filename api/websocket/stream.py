"""
WebSocket Manager

Manages WebSocket connections for real-time updates.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Set, Optional
from dataclasses import dataclass
from enum import Enum

from fastapi import WebSocket


class MessageType(str, Enum):
    """WebSocket message types"""
    RECOMMENDATION = "recommendation"
    ALERT = "alert"
    METRIC_UPDATE = "metric_update"
    AGENT_STATUS = "agent_status"
    ANALYSIS_COMPLETE = "analysis_complete"
    ERROR = "error"
    PONG = "pong"


@dataclass
class WebSocketMessage:
    """Structured WebSocket message"""
    type: MessageType
    data: Dict[str, Any]
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps({
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
        })


class WebSocketManager:
    """Manages WebSocket connections and broadcasts"""

    def __init__(self):
        # Active connections
        self._connections: Set[WebSocket] = set()

        # Channel subscriptions
        self._subscriptions: Dict[WebSocket, Set[str]] = {}

        # Channel to connections mapping
        self._channel_subscribers: Dict[str, Set[WebSocket]] = {}

        # Message queue for broadcasting
        self._message_queue: asyncio.Queue = None
        self._broadcast_task: Optional[asyncio.Task] = None

        # Metrics
        self._metrics = {
            "connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
        }

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""

        await websocket.accept()
        self._connections.add(websocket)
        self._subscriptions[websocket] = set()

        self._metrics["connections"] = len(self._connections)

        # Send welcome message
        await self._send_to_connection(websocket, WebSocketMessage(
            type=MessageType.METRIC_UPDATE,
            data={
                "event": "connected",
                "connection_id": id(websocket),
                "server_time": datetime.utcnow().isoformat(),
            }
        ))

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""

        # Remove from all channels
        if websocket in self._subscriptions:
            for channel in self._subscriptions[websocket]:
                if channel in self._channel_subscribers:
                    self._channel_subscribers[channel].discard(websocket)

            del self._subscriptions[websocket]

        self._connections.discard(websocket)
        self._metrics["connections"] = len(self._connections)

    async def subscribe(self, websocket: WebSocket, channel: str):
        """Subscribe a connection to a channel"""

        if websocket not in self._connections:
            return

        # Add to connection's subscriptions
        self._subscriptions[websocket].add(channel)

        # Add to channel's subscribers
        if channel not in self._channel_subscribers:
            self._channel_subscribers[channel] = set()
        self._channel_subscribers[channel].add(websocket)

        # Confirm subscription
        await self._send_to_connection(websocket, WebSocketMessage(
            type=MessageType.METRIC_UPDATE,
            data={
                "event": "subscribed",
                "channel": channel,
            }
        ))

    async def unsubscribe(self, websocket: WebSocket, channel: str):
        """Unsubscribe a connection from a channel"""

        if websocket in self._subscriptions:
            self._subscriptions[websocket].discard(channel)

        if channel in self._channel_subscribers:
            self._channel_subscribers[channel].discard(websocket)

        await self._send_to_connection(websocket, WebSocketMessage(
            type=MessageType.METRIC_UPDATE,
            data={
                "event": "unsubscribed",
                "channel": channel,
            }
        ))

    async def broadcast(self, message: WebSocketMessage, channel: Optional[str] = None):
        """Broadcast a message to all or specific channel subscribers"""

        if channel:
            # Send to channel subscribers
            subscribers = self._channel_subscribers.get(channel, set())
            for websocket in subscribers:
                await self._send_to_connection(websocket, message)
        else:
            # Send to all connections
            for websocket in self._connections:
                await self._send_to_connection(websocket, message)

    async def broadcast_recommendation(self, recommendation: Dict[str, Any]):
        """Broadcast a new recommendation"""

        await self.broadcast(
            WebSocketMessage(
                type=MessageType.RECOMMENDATION,
                data=recommendation
            ),
            channel="recommendations"
        )

    async def broadcast_alert(self, alert: Dict[str, Any]):
        """Broadcast an alert"""

        await self.broadcast(
            WebSocketMessage(
                type=MessageType.ALERT,
                data=alert
            ),
            channel="alerts"
        )

    async def broadcast_metric_update(self, metric: str, value: float, domain: str):
        """Broadcast a metric update"""

        await self.broadcast(
            WebSocketMessage(
                type=MessageType.METRIC_UPDATE,
                data={
                    "metric": metric,
                    "value": value,
                    "domain": domain,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            channel=f"metrics:{domain}"
        )

    async def broadcast_agent_status(self, agent_type: str, status: Dict[str, Any]):
        """Broadcast agent status update"""

        await self.broadcast(
            WebSocketMessage(
                type=MessageType.AGENT_STATUS,
                data={
                    "agent_type": agent_type,
                    **status
                }
            ),
            channel="agents"
        )

    async def broadcast_analysis_complete(self, analysis: Dict[str, Any]):
        """Broadcast analysis completion"""

        await self.broadcast(
            WebSocketMessage(
                type=MessageType.ANALYSIS_COMPLETE,
                data=analysis
            ),
            channel="analysis"
        )

    async def _send_to_connection(self, websocket: WebSocket, message: WebSocketMessage):
        """Send a message to a specific connection"""

        try:
            await websocket.send_text(message.to_json())
            self._metrics["messages_sent"] += 1
        except Exception as e:
            self._metrics["errors"] += 1
            # Connection might be closed, remove it
            self.disconnect(websocket)

    def get_subscribers(self, channel: str) -> int:
        """Get number of subscribers for a channel"""

        return len(self._channel_subscribers.get(channel, set()))

    def get_connection_info(self, websocket: WebSocket) -> Dict[str, Any]:
        """Get info about a connection"""

        return {
            "connection_id": id(websocket),
            "subscriptions": list(self._subscriptions.get(websocket, set())),
            "connected": True,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get WebSocket manager metrics"""

        return {
            **self._metrics,
            "active_connections": len(self._connections),
            "channels": {
                channel: len(subscribers)
                for channel, subscribers in self._channel_subscribers.items()
            },
        }

    def get_all_channels(self) -> List[str]:
        """Get all active channels"""

        return list(self._channel_subscribers.keys())
