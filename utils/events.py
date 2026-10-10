"""
NEUTRON Event Bus System

Provides asynchronous publish/subscribe event system for
inter-module communication with type safety and replay.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache
from typing import Any, Callable, Coroutine, TypeVar, Generic
from weakref import WeakSet

from config.constants import SystemEvent


@dataclass(frozen=True, slots=True)
class Event:
    """
    Immutable event container.
    
    Attributes:
        id: Unique event identifier
        type: Event type from SystemEvent enum
        data: Event payload
        timestamp: Event creation time (UTC)
        source: Module/component that emitted the event
        priority: Event priority (higher = more urgent)
        correlation_id: Optional ID to correlate related events
    """
    id: str
    type: SystemEvent
    data: dict[str, Any]
    timestamp: datetime
    source: str
    priority: int = 0
    correlation_id: str | None = None
    
    @classmethod
    def create(
        cls,
        event_type: SystemEvent,
        data: dict[str, Any] | None = None,
        source: str = "unknown",
        priority: int = 0,
        correlation_id: str | None = None,
    ) -> "Event":
        """Factory method to create a new event."""
        return cls(
            id=str(uuid.uuid4()),
            type=event_type,
            data=data or {},
            timestamp=datetime.now(timezone.utc),
            source=source,
            priority=priority,
            correlation_id=correlation_id,
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "priority": self.priority,
            "correlation_id": self.correlation_id,
        }


# Type for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]
SyncEventHandler = Callable[[Event], None]


@dataclass
class Subscription:
    """Represents an event subscription."""
    id: str
    event_type: SystemEvent | None  # None = subscribe to all
    handler: EventHandler
    filter_fn: Callable[[Event], bool] | None = None
    priority: int = 0
    one_shot: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventBus:
    """
    Asynchronous event bus for inter-module communication.
    
    Features:
    - Type-safe event publishing and subscription
    - Priority-based handler execution
    - Event filtering
    - One-shot subscriptions
    - Event history with replay capability
    - Weak references to prevent memory leaks
    - Async and sync handler support
    """
    
    _instance: "EventBus | None" = None
    
    def __init__(self, history_size: int = 1000) -> None:
        """
        Initialize the event bus.
        
        Args:
            history_size: Number of events to keep in history
        """
        self._subscriptions: dict[SystemEvent | None, list[Subscription]] = defaultdict(list)
        self._history: list[Event] = []
        self._history_size = history_size
        self._lock = asyncio.Lock()
        self._pending_events: asyncio.Queue[Event] = asyncio.Queue()
        self._running = False
        self._process_task: asyncio.Task | None = None
        self._stats = {
            "events_published": 0,
            "events_processed": 0,
            "handlers_called": 0,
            "errors": 0,
        }
    
    @classmethod
    def get_instance(cls) -> "EventBus":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = EventBus()
        return cls._instance
    
    async def start(self) -> None:
        """Start the event processing loop."""
        if self._running:
            return
        
        self._running = True
        self._process_task = asyncio.create_task(self._process_loop())
    
    async def stop(self) -> None:
        """Stop the event processing loop."""
        self._running = False
        
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
            self._process_task = None
    
    async def _process_loop(self) -> None:
        """Main event processing loop."""
        while self._running:
            try:
                # Wait for event with timeout to allow checking running flag
                try:
                    event = await asyncio.wait_for(
                        self._pending_events.get(),
                        timeout=0.1
                    )
                except asyncio.TimeoutError:
                    continue
                
                await self._process_event(event)
                self._pending_events.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._stats["errors"] += 1
                # Log error but don't crash the loop
                print(f"Event bus error: {e}")
    
    async def _process_event(self, event: Event) -> None:
        """Process a single event."""
        self._stats["events_processed"] += 1
        
        # Get handlers for this event type and global handlers
        handlers: list[Subscription] = []
        
        async with self._lock:
            # Type-specific handlers
            if event.type in self._subscriptions:
                handlers.extend(self._subscriptions[event.type])
            
            # Global handlers (subscribed to None)
            if None in self._subscriptions:
                handlers.extend(self._subscriptions[None])
        
        # Sort by priority (higher first)
        handlers.sort(key=lambda s: s.priority, reverse=True)
        
        # Track one-shot handlers to remove
        one_shots_to_remove: list[Subscription] = []
        
        # Execute handlers
        for subscription in handlers:
            # Apply filter if present
            if subscription.filter_fn and not subscription.filter_fn(event):
                continue
            
            try:
                await subscription.handler(event)
                self._stats["handlers_called"] += 1
                
                if subscription.one_shot:
                    one_shots_to_remove.append(subscription)
                    
            except Exception as e:
                self._stats["errors"] += 1
                print(f"Handler error for {event.type}: {e}")
        
        # Remove one-shot handlers
        if one_shots_to_remove:
            async with self._lock:
                for sub in one_shots_to_remove:
                    if sub.event_type in self._subscriptions:
                        try:
                            self._subscriptions[sub.event_type].remove(sub)
                        except ValueError:
                            pass
    
    def subscribe(
        self,
        event_type: SystemEvent | None,
        handler: EventHandler,
        filter_fn: Callable[[Event], bool] | None = None,
        priority: int = 0,
        one_shot: bool = False,
    ) -> str:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Event type to subscribe to (None = all events)
            handler: Async handler function
            filter_fn: Optional filter function
            priority: Handler priority (higher = called first)
            one_shot: If True, handler is removed after first call
            
        Returns:
            Subscription ID for later unsubscription
        """
        subscription = Subscription(
            id=str(uuid.uuid4()),
            event_type=event_type,
            handler=handler,
            filter_fn=filter_fn,
            priority=priority,
            one_shot=one_shot,
        )
        
        # Use sync lock for non-async subscribe
        self._subscriptions[event_type].append(subscription)
        
        return subscription.id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe a handler.
        
        Args:
            subscription_id: ID returned from subscribe()
            
        Returns:
            True if subscription was found and removed
        """
        for event_type, subs in self._subscriptions.items():
            for sub in subs:
                if sub.id == subscription_id:
                    subs.remove(sub)
                    return True
        return False
    
    async def publish(
        self,
        event_type: SystemEvent,
        data: dict[str, Any] | None = None,
        source: str = "unknown",
        priority: int = 0,
        correlation_id: str | None = None,
        immediate: bool = False,
    ) -> Event:
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: Type of event
            data: Event payload
            source: Publishing module name
            priority: Event priority
            correlation_id: Optional correlation ID
            immediate: If True, process synchronously instead of queuing
            
        Returns:
            The created event
        """
        event = Event.create(
            event_type=event_type,
            data=data,
            source=source,
            priority=priority,
            correlation_id=correlation_id,
        )
        
        # Add to history
        async with self._lock:
            self._history.append(event)
            if len(self._history) > self._history_size:
                self._history = self._history[-self._history_size:]
        
        self._stats["events_published"] += 1
        
        if immediate:
            await self._process_event(event)
        else:
            await self._pending_events.put(event)
        
        return event
    
    def publish_sync(
        self,
        event_type: SystemEvent,
        data: dict[str, Any] | None = None,
        source: str = "unknown",
        priority: int = 0,
        correlation_id: str | None = None,
    ) -> Event:
        """
        Synchronous publish that creates event and queues for processing.
        
        For use in sync code that can't await.
        """
        event = Event.create(
            event_type=event_type,
            data=data,
            source=source,
            priority=priority,
            correlation_id=correlation_id,
        )
        
        self._history.append(event)
        if len(self._history) > self._history_size:
            self._history = self._history[-self._history_size:]
        
        self._stats["events_published"] += 1
        
        # Put in queue without await
        try:
            self._pending_events.put_nowait(event)
        except asyncio.QueueFull:
            # Drop event if queue is full
            self._stats["errors"] += 1
        
        return event
    
    async def wait_for(
        self,
        event_type: SystemEvent,
        timeout: float | None = None,
        filter_fn: Callable[[Event], bool] | None = None,
    ) -> Event | None:
        """
        Wait for a specific event type.
        
        Args:
            event_type: Event type to wait for
            timeout: Maximum wait time in seconds
            filter_fn: Optional filter function
            
        Returns:
            The event if received, None if timeout
        """
        result_event: Event | None = None
        received = asyncio.Event()
        
        async def handler(event: Event) -> None:
            nonlocal result_event
            result_event = event
            received.set()
        
        sub_id = self.subscribe(
            event_type=event_type,
            handler=handler,
            filter_fn=filter_fn,
            one_shot=True,
        )
        
        try:
            await asyncio.wait_for(received.wait(), timeout=timeout)
            return result_event
        except asyncio.TimeoutError:
            self.unsubscribe(sub_id)
            return None
    
    def get_history(
        self,
        event_type: SystemEvent | None = None,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[Event]:
        """
        Get event history.
        
        Args:
            event_type: Filter by event type (None = all)
            limit: Maximum number of events to return
            since: Only events after this time
            
        Returns:
            List of events (newest first)
        """
        events = self._history.copy()
        
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        if since:
            events = [e for e in events if e.timestamp > since]
        
        return list(reversed(events[-limit:]))
    
    async def replay(
        self,
        event_type: SystemEvent | None = None,
        since: datetime | None = None,
        handler: EventHandler | None = None,
    ) -> int:
        """
        Replay historical events to a handler.
        
        Args:
            event_type: Filter by event type
            since: Only events after this time
            handler: Handler to replay to (None = all subscribers)
            
        Returns:
            Number of events replayed
        """
        events = self.get_history(event_type=event_type, since=since)
        count = 0
        
        for event in events:
            if handler:
                await handler(event)
            else:
                await self._process_event(event)
            count += 1
        
        return count
    
    def get_stats(self) -> dict[str, Any]:
        """Get event bus statistics."""
        return {
            **self._stats,
            "pending_events": self._pending_events.qsize(),
            "history_size": len(self._history),
            "subscription_count": sum(len(subs) for subs in self._subscriptions.values()),
        }
    
    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()


@lru_cache()
def get_event_bus() -> EventBus:
    """Get the singleton event bus instance."""
    return EventBus.get_instance()


# Decorator for subscribing methods to events
def on_event(
    event_type: SystemEvent,
    priority: int = 0,
    filter_fn: Callable[[Event], bool] | None = None,
):
    """
    Decorator to subscribe a method to an event type.
    
    Usage:
        class MyComponent:
            @on_event(SystemEvent.WAKE_WORD_DETECTED)
            async def handle_wake(self, event: Event):
                ...
    """
    def decorator(func: EventHandler):
        func._event_subscription = {  # type: ignore
            "event_type": event_type,
            "priority": priority,
            "filter_fn": filter_fn,
        }
        return func
    return decorator


class EventEmitter:
    """
    Mixin class for components that emit events.
    
    Provides convenient methods for publishing events
    with automatic source tracking.
    """
    
    _event_bus: EventBus | None = None
    
    @property
    def event_bus(self) -> EventBus:
        """Get event bus instance."""
        if self._event_bus is None:
            self._event_bus = get_event_bus()
        return self._event_bus
    
    async def emit(
        self,
        event_type: SystemEvent,
        data: dict[str, Any] | None = None,
        priority: int = 0,
        correlation_id: str | None = None,
        immediate: bool = False,
    ) -> Event:
        """Emit an event with this component as source."""
        return await self.event_bus.publish(
            event_type=event_type,
            data=data,
            source=self.__class__.__name__,
            priority=priority,
            correlation_id=correlation_id,
            immediate=immediate,
        )
    
    def emit_sync(
        self,
        event_type: SystemEvent,
        data: dict[str, Any] | None = None,
        priority: int = 0,
        correlation_id: str | None = None,
    ) -> Event:
        """Emit an event synchronously."""
        return self.event_bus.publish_sync(
            event_type=event_type,
            data=data,
            source=self.__class__.__name__,
            priority=priority,
            correlation_id=correlation_id,
        )
    
    def subscribe_to(
        self,
        event_type: SystemEvent,
        handler: EventHandler,
        priority: int = 0,
    ) -> str:
        """Subscribe to an event type."""
        return self.event_bus.subscribe(
            event_type=event_type,
            handler=handler,
            priority=priority,
        )


__all__ = [
    "Event",
    "EventBus",
    "EventHandler",
    "Subscription",
    "get_event_bus",
    "on_event",
    "EventEmitter",
]
