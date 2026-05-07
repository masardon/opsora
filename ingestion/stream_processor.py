"""
Stream Processor

Real-time event processing using Google PubSub.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict

from ingestion.event_validator import EventValidator, EventEnricher, EventType


@dataclass
class StreamConfig:
    """Configuration for stream processing"""
    project_id: str
    subscription_name: str
    max_messages: int = 100
    ack_deadline_seconds: int = 60
    enable_aggregation: bool = True
    aggregation_window_seconds: int = 10


class StreamProcessor:
    """Processes streaming events from PubSub"""

    def __init__(
        self,
        config: StreamConfig,
        validator: Optional[EventValidator] = None,
        enricher: Optional[EventEnricher] = None,
    ):
        self.config = config
        self.validator = validator or EventValidator()
        self.enricher = enricher or EventEnricher()

        # Processing state
        self._running = False
        self._subscribers = {}
        self._aggregated_events = defaultdict(list)

        # Metrics
        self._metrics = {
            "messages_received": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "events_created": 0,
        }

        # Callbacks
        self._on_event: Optional[Callable] = None
        self._on_error: Optional[Callable] = None
        self._on_batch: Optional[Callable] = None

    def on_event(self, callback: Callable):
        """Register callback for individual events"""
        self._on_event = callback

    def on_error(self, callback: Callable):
        """Register callback for errors"""
        self._on_error = callback

    def on_batch(self, callback: Callable):
        """Register callback for batched events"""
        self._on_batch = callback

    async def start(self):
        """Start streaming processor"""

        if self._running:
            return

        self._running = True

        try:
            subscriber = self._get_subscriber()
            self._subscribers["main"] = subscriber

            # Start processing loop
            await self._processing_loop()

        except Exception as e:
            if self._on_error:
                await self._on_error(e)
            raise

    async def stop(self):
        """Stop streaming processor"""

        self._running = False

        # Flush aggregated events
        if self._aggregated_events:
            await self._flush_aggregated_events()

        # Close subscribers
        for subscriber in self._subscribers.values():
            if hasattr(subscriber, "close"):
                await subscriber.close()

        self._subscribers.clear()

    def _get_subscriber(self):
        """Get PubSub subscriber"""

        try:
            from google.cloud import pubsub_v1

            subscriber = pubsub_v1.SubscriberClient()
            subscription_path = subscriber.subscription_path(
                self.config.project_id,
                self.config.subscription_name
            )

            # Create streaming pull helper
            stream = pubsub_v1.streaming.PushHelper(
                subscriber,
                subscription_path,
            )

            return stream

        except ImportError:
            # For demo/testing, return mock subscriber
            return MockSubscriber()

    async def _processing_loop(self):
        """Main processing loop"""

        subscriber = self._subscribers.get("main")

        while self._running:
            try:
                # Pull messages
                messages = await self._pull_messages(subscriber)

                if messages:
                    await self._process_messages(messages)

                # Process aggregation window
                if self.config.enable_aggregation:
                    await asyncio.sleep(self.config.aggregation_window_seconds)
                    await self._flush_aggregated_events()

                else:
                    await asyncio.sleep(0.1)

            except Exception as e:
                self._metrics["messages_failed"] += 1

                if self._on_error:
                    await self._on_error(e)

                if not self.config.enable_aggregation:
                    # Continue processing in aggregation mode
                    await asyncio.sleep(1)

    async def _pull_messages(self, subscriber) -> List[Any]:
        """Pull messages from subscriber"""

        if hasattr(subscriber, "pull"):
            # Real PubSub
            response = subscriber.pull(
                request={
                    "subscription": self.config.subscription_name,
                    "max_messages": self.config.max_messages,
                },
                timeout=1.0,
            )

            return list(response.received_messages)

        elif isinstance(subscriber, MockSubscriber):
            # Mock subscriber for testing
            messages = subscriber.get_messages(self.config.max_messages)
            self._metrics["messages_received"] += len(messages)
            return messages

        return []

    async def _process_messages(self, messages: List[Any]):
        """Process batch of messages"""

        for message in messages:
            try:
                # Parse message
                data = self._parse_message(message)

                # Validate
                event_type = EventType(data.get("event_type", "system"))
                is_valid, error, cleaned = self.validator.validate_event(data, event_type)

                if is_valid and cleaned:
                    # Enrich
                    enriched = await self.enricher.enrich_event(cleaned, event_type)

                    # Track metric
                    self._metrics["events_created"] += 1

                    # Handle event
                    if self._on_event:
                        await self._on_event(enriched)

                    # Aggregate if enabled
                    if self.config.enable_aggregation:
                        self._aggregated_events[event_type].append(enriched)

                    # Acknowledge message
                    if hasattr(message, "ack_id"):
                        self._acknowledge(message)

                    self._metrics["messages_processed"] += 1

                else:
                    # Invalid event
                    if self._on_error:
                        await self._on_error(f"Validation error: {error}")

                    # Acknowledge to move on
                    if hasattr(message, "ack_id"):
                        self._acknowledge(message)

            except Exception as e:
                self._metrics["messages_failed"] += 1

                if self._on_error:
                    await self._on_error(e)

    def _parse_message(self, message) -> Dict[str, Any]:
        """Parse message data"""

        if hasattr(message, "data"):
            # PubSub message
            data = message.data.decode("utf-8")
        elif isinstance(message, dict):
            data = message.get("data", "{}")
        elif isinstance(message, str):
            data = message
        else:
            return {}

        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {"raw_data": data}

    def _acknowledge(self, message):
        """Acknowledge a message"""

        # In real implementation, this would call subscriber.acknowledge()
        pass

    async def _flush_aggregated_events(self):
        """Flush aggregated events"""

        if not self._aggregated_events:
            return

        if self._on_batch:
            # Convert to list
            all_events = []
            for events in self._aggregated_events.values():
                all_events.extend(events)

            await self._on_batch(all_events)

        # Clear aggregation
        self._aggregated_events.clear()

    async def ingest_event(
        self,
        event_data: Dict[str, Any],
        event_type: EventType
    ) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Ingest a single event (for non-streaming use)"""

        self._metrics["messages_received"] += 1

        # Validate
        is_valid, error, cleaned = self.validator.validate_event(event_data, event_type)

        if not is_valid:
            self._metrics["messages_failed"] += 1
            return False, error, None

        # Enrich
        enriched = await self.enricher.enrich_event(cleaned, event_type)

        self._metrics["events_created"] += 1
        self._metrics["messages_processed"] += 1

        return True, None, enriched

    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics"""

        return {
            **self._metrics,
            "aggregation_queue_size": sum(len(v) for v in self._aggregated_events.values()),
            "validation_stats": self.validator.get_validation_stats(),
        }


class MockSubscriber:
    """Mock subscriber for testing"""

    def __init__(self):
        self._messages: List[Dict[str, Any]] = []
        self._counter = 0

    def add_test_message(self, message: Dict[str, Any]):
        """Add a test message"""
        self._messages.append({
            "ack_id": f"ack_{self._counter}",
            "data": json.dumps(message).encode("utf-8"),
            "message_id": f"msg_{self._counter}",
        })
        self._counter += 1

    def get_messages(self, max_count: int) -> List[Dict[str, Any]]:
        """Get messages (for testing)"""
        messages = self._messages[:max_count]
        self._messages = self._messages[max_count:]
        return messages
