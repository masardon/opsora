"""
Notifier Tool

Provides notification capabilities for agents to send alerts and recommendations.
"""

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio


class NotificationChannel(str, Enum):
    """Available notification channels"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    CONSOLE = "console"
    PUBSUB = "pubsub"


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Notification:
    """A notification to be sent"""
    channel: NotificationChannel
    priority: NotificationPriority
    title: str
    message: str
    recipients: List[str]
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    sent: bool = False
    sent_at: Optional[datetime] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "recipients": self.recipients,
            "metadata": self.metadata or {},
            "timestamp": self.timestamp.isoformat(),
            "sent": self.sent,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "error": self.error,
        }


@dataclass
class WebhookPayload:
    """Standard webhook payload format"""
    event_type: str
    priority: str
    timestamp: str
    source: str
    data: Dict[str, Any]


class NotifierTool:
    """Tool for sending notifications and alerts"""

    def __init__(
        self,
        default_channels: List[NotificationChannel] = None,
        webhook_urls: Dict[str, str] = None,
        slack_webhook_url: str = None,
        email_config: Dict[str, Any] = None,
    ):
        self.default_channels = default_channels or [NotificationChannel.CONSOLE]
        self.webhook_urls = webhook_urls or {}
        self.slack_webhook_url = slack_webhook_url
        self.email_config = email_config or {}
        self.notification_history: List[Notification] = []

        # Queue for async sending
        self._notification_queue: asyncio.Queue = None

    async def send(
        self,
        notification: Notification,
        channels: Optional[List[NotificationChannel]] = None
    ) -> Notification:
        """Send notification through specified channels"""

        channels = channels or self.default_channels
        notification.sent = False
        notification.error = None

        for channel in channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    await self._send_email(notification)
                elif channel == NotificationChannel.WEBHOOK:
                    await self._send_webhook(notification)
                elif channel == NotificationChannel.SLACK:
                    await self._send_slack(notification)
                elif channel == NotificationChannel.CONSOLE:
                    self._send_console(notification)
                elif channel == NotificationChannel.PUBSUB:
                    await self._send_pubsub(notification)

                notification.sent = True
                notification.sent_at = datetime.utcnow()
                break  # Success, don't try other channels

            except Exception as e:
                notification.error = str(e)
                continue

        self.notification_history.append(notification)
        return notification

    async def send_alert(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        recipients: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        channels: Optional[List[NotificationChannel]] = None,
    ) -> Notification:
        """Send an alert notification"""

        notification = Notification(
            channel=channels[0] if channels else self.default_channels[0],
            priority=priority,
            title=title,
            message=message,
            recipients=recipients or [],
            metadata=metadata,
        )

        return await self.send(notification, channels)

    async def send_recommendation(
        self,
        recommendation: Dict[str, Any],
        recipients: List[str],
        priority: NotificationPriority = NotificationPriority.MEDIUM,
    ) -> Notification:
        """Send a recommendation notification"""

        title = f"Recommendation: {recommendation.get('summary', 'New insight')}"
        message = self._format_recommendation_message(recommendation)

        notification = Notification(
            channel=NotificationChannel.EMAIL,
            priority=priority,
            title=title,
            message=message,
            recipients=recipients,
            metadata={"recommendation": recommendation},
        )

        return await self.send(notification)

    async def send_anomaly_alert(
        self,
        anomaly: Dict[str, Any],
        metric_name: str,
        recipients: List[str],
    ) -> Notification:
        """Send an anomaly alert"""

        severity = anomaly.get("severity", "medium")

        title = f"🚨 Anomaly Detected: {metric_name}"
        message = f"""
Anomaly detected in {metric_name}

Value: {anomaly.get('value', 'N/A')}
Expected: {anomaly.get('expected_value', 'N/A')}
Deviation: {anomaly.get('deviation', 'N/A')}
Severity: {severity.upper()}
Time: {anomaly.get('timestamp', 'N/A')}

Context: {anomaly.get('context', {})}
        """.strip()

        priority = {
            "low": NotificationPriority.LOW,
            "medium": NotificationPriority.MEDIUM,
            "high": NotificationPriority.HIGH,
            "critical": NotificationPriority.CRITICAL,
        }.get(severity, NotificationPriority.MEDIUM)

        notification = Notification(
            channel=NotificationChannel.SLACK if self.slack_webhook_url else NotificationChannel.EMAIL,
            priority=priority,
            title=title,
            message=message,
            recipients=recipients,
            metadata={"anomaly": anomaly, "metric": metric_name},
        )

        return await self.send(notification)

    def _send_console(self, notification: Notification):
        """Send notification to console"""
        priority_symbols = {
            NotificationPriority.LOW: "ℹ️",
            NotificationPriority.MEDIUM: "⚠️",
            NotificationPriority.HIGH: "🔶",
            NotificationPriority.CRITICAL: "🚨",
        }

        symbol = priority_symbols.get(notification.priority, "📢")

        print(f"\n{symbol} [{notification.priority.value.upper()}] {notification.title}")
        print(f"{'─' * 60}")
        print(notification.message)
        if notification.metadata:
            print(f"\nMetadata: {json.dumps(notification.metadata, indent=2, default=str)}")
        print(f"{'─' * 60}\n")

    async def _send_email(self, notification: Notification):
        """Send email notification"""
        # Placeholder for email implementation
        # In production, use SendGrid, AWS SES, or GCP Mailjet
        print(f"[EMAIL] To: {notification.recipients}")
        print(f"[EMAIL] Subject: {notification.title}")
        print(f"[EMAIL] Body: {notification.message[:100]}...")

    async def _send_webhook(self, notification: Notification):
        """Send webhook notification"""
        import httpx

        url = self.webhook_urls.get(notification.priority.value, self.webhook_urls.get("default"))

        if not url:
            raise ValueError("No webhook URL configured for this priority")

        payload = WebhookPayload(
            event_type="agent_notification",
            priority=notification.priority.value,
            timestamp=notification.timestamp.isoformat(),
            source="opsora_agent",
            data={
                "title": notification.title,
                "message": notification.message,
                "metadata": notification.metadata,
            }
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload.__dict__,
                headers={"Content-Type": "application/json"},
                timeout=10.0,
            )
            response.raise_for_status()

    async def _send_slack(self, notification: Notification):
        """Send Slack notification via webhook"""
        if not self.slack_webhook_url:
            raise ValueError("Slack webhook URL not configured")

        import httpx

        # Color based on priority
        colors = {
            NotificationPriority.LOW: "#36a64f",  # green
            NotificationPriority.MEDIUM: "#ff9900",  # orange
            NotificationPriority.HIGH: "#ff0000",  # red
            NotificationPriority.CRITICAL: "#990000",  # dark red
        }

        color = colors.get(notification.priority, "#36a64f")

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": notification.title,
                    "text": notification.message,
                    "footer": "Opsora Agent",
                    "ts": int(notification.timestamp.timestamp()),
                }
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.slack_webhook_url,
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()

    async def _send_pubsub(self, notification: Notification):
        """Send notification via Google PubSub"""
        # Placeholder for PubSub implementation
        # In production, publish to PubSub topic
        print(f"[PUBSUB] Publishing to topic: notifications-{notification.priority.value}")

    def _format_recommendation_message(self, recommendation: Dict[str, Any]) -> str:
        """Format a recommendation into a readable message"""
        return f"""
Summary: {recommendation.get('summary', 'N/A')}

Description:
{recommendation.get('description', 'N/A')}

Details:
- Impact: {recommendation.get('impact', 'N/A')}
- Urgency: {recommendation.get('urgency', 'N/A')}
- Effort: {recommendation.get('effort', 'N/A')}
- Confidence: {recommendation.get('confidence', 0):.0%}

Rationale:
{recommendation.get('rationale', 'N/A')}

Affected Metrics:
{', '.join(recommendation.get('metrics_affected', []))}
        """.strip()

    def get_notification_stats(self) -> Dict[str, Any]:
        """Get statistics about sent notifications"""
        if not self.notification_history:
            return {"total": 0}

        total = len(self.notification_history)
        sent = sum(1 for n in self.notification_history if n.sent)
        failed = total - sent

        by_priority = {}
        for notification in self.notification_history:
            priority = notification.priority.value
            by_priority[priority] = by_priority.get(priority, 0) + 1

        return {
            "total": total,
            "sent": sent,
            "failed": failed,
            "success_rate": round(sent / total * 100, 2) if total > 0 else 0,
            "by_priority": by_priority,
        }
