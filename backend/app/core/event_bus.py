import asyncio
import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger("EventBus")

class EventBus:
    """
    A lightweight, asynchronous publish-subscribe event bus.
    Topics can be subscribed to with callback functions.
    Callbacks must be async functions.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self.main_loop = None

    def set_main_loop(self, loop):
        self.main_loop = loop

    def subscribe(self, topic: str, callback: Callable):
        """
        Subscribe an async callback to a topic.
        """
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)

    def publish(self, topic: str, message: Any):
        """
        Publish a message to a topic.
        Schedules the async callbacks in the asyncio event loop without blocking.
        """
        if topic not in self._subscribers:
            return
            
        for callback in self._subscribers[topic]:
            # Schedule the callback safely
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._safe_execute(callback, message))
            except RuntimeError:
                # If there's no running event loop (e.g. running from a background thread),
                # schedule it on the main loop if available.
                if self.main_loop:
                    asyncio.run_coroutine_threadsafe(self._safe_execute(callback, message), self.main_loop)
                else:
                    try:
                        asyncio.run(self._safe_execute(callback, message))
                    except Exception as e:
                        logger.error(f"Error publishing synchronously to {topic}: {e}")

    async def _safe_execute(self, callback: Callable, message: Any):
        """Execute the callback safely, catching any exceptions to prevent crashing the event bus."""
        try:
            await callback(message)
        except Exception as e:
            logger.error(f"Exception in event bus subscriber for callback {callback.__name__}: {e}")

# Global singleton event bus
event_bus = EventBus()
