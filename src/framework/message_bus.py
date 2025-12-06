"""Async message bus for inter-agent communication."""

import asyncio
import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from .base_agent import Message, AgentRole


@dataclass
class MessageLog:
    """Log entry for message tracking."""
    message: Message
    delivered_to: List[str]
    timestamp: str


class MessageBus:
    """Central message bus for agent communication."""

    def __init__(self, max_history: int = 1000):
        """Initialize the message bus."""
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.broadcast_subscribers: List[Callable] = []
        self.message_history: List[MessageLog] = []
        self.max_history = max_history
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self._processing = False

    async def subscribe(self, agent_id: str, handler: Callable):
        """Subscribe an agent to receive specific messages."""
        self.subscribers[agent_id].append(handler)

    async def subscribe_broadcast(self, handler: Callable):
        """Subscribe to all broadcast messages."""
        self.broadcast_subscribers.append(handler)

    async def publish(self, message: Message):
        """Publish a message to the bus."""
        await self.message_queue.put(message)

    async def process_messages(self):
        """Process messages from the queue."""
        self._processing = True
        while self._processing:
            try:
                message = await asyncio.wait_for(
                    self.message_queue.get(), timeout=0.1
                )
                await self._route_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error processing message: {e}")

    async def _route_message(self, message: Message):
        """Route a message to appropriate recipients."""
        delivered_to = []

        # If no specific recipients, broadcast
        if not message.recipient_ids:
            for handler in self.broadcast_subscribers:
                try:
                    await self._execute_handler(handler, message)
                    delivered_to.append("broadcast")
                except Exception as e:
                    print(f"Error in broadcast handler: {e}")
        else:
            # Send to specific recipients
            for recipient_id in message.recipient_ids:
                if recipient_id in self.subscribers:
                    for handler in self.subscribers[recipient_id]:
                        try:
                            await self._execute_handler(handler, message)
                            delivered_to.append(recipient_id)
                        except Exception as e:
                            print(f"Error delivering to {recipient_id}: {e}")

        # Log the message
        await self._log_message(message, delivered_to)

    async def _execute_handler(self, handler: Callable, message: Message):
        """Execute a handler, handling both sync and async functions."""
        if asyncio.iscoroutinefunction(handler):
            await handler(message)
        else:
            handler(message)

    async def _log_message(self, message: Message, delivered_to: List[str]):
        """Log message delivery."""
        log_entry = MessageLog(
            message=message,
            delivered_to=delivered_to,
            timestamp=datetime.utcnow().isoformat()
        )
        self.message_history.append(log_entry)

        # Keep history size manageable
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)

    def get_message_history(
        self,
        sender_id: Optional[str] = None,
        message_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve message history with optional filters."""
        filtered = self.message_history

        if sender_id:
            filtered = [m for m in filtered if m.message.sender_id == sender_id]

        if message_type:
            filtered = [m for m in filtered if m.message.message_type == message_type]

        # Return most recent messages
        return [
            {
                "message": asdict(m.message),
                "delivered_to": m.delivered_to,
                "logged_at": m.timestamp
            }
            for m in filtered[-limit:]
        ]

    def get_bus_stats(self) -> Dict[str, Any]:
        """Get message bus statistics."""
        return {
            "total_subscribers": len(self.subscribers),
            "broadcast_subscribers": len(self.broadcast_subscribers),
            "message_history_size": len(self.message_history),
            "queue_size": self.message_queue.qsize(),
            "is_processing": self._processing
        }

    async def stop(self):
        """Stop message processing."""
        self._processing = False
