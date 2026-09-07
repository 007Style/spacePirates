"""core/events.py — simple publish/subscribe event bus."""
from collections import defaultdict
from typing import Callable, Any


class EventBus:
    def __init__(self):
        self._listeners: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event: str, callback: Callable) -> None:
        self._listeners[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable) -> None:
        self._listeners[event] = [
            cb for cb in self._listeners[event] if cb is not callback
        ]

    def publish(self, event: str, **kwargs: Any) -> None:
        for cb in list(self._listeners[event]):
            cb(**kwargs)


# Global singleton
bus = EventBus()
