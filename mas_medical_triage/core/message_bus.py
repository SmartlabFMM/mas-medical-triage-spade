"""
core/message_bus.py — Message bus implementation for SPADE-based communication.
This module provides compatibility with the original architecture while using SPADE XMPP.
"""
from __future__ import annotations
import asyncio
from typing import Dict, Optional
from core.message import Message


class MessageBus:
    """
    Message bus for inter-agent communication using SPADE XMPP backend.
    Provides compatibility layer for the original architecture.
    """
    
    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._running = False
    
    async def register_agent(self, agent_id: str) -> None:
        """Register an agent with the message bus."""
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue()
    
    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the message bus."""
        if agent_id in self._queues:
            del self._queues[agent_id]
    
    async def send(self, message: Message) -> None:
        """
        Send a message to the specified receiver.
        Note: In SPADE implementation, this delegates to XMPP messaging.
        """
        if message.receiver not in self._queues:
            raise ValueError(f"Agent {message.receiver} not registered")
        
        await self._queues[message.receiver].put(message)
    
    async def receive(self, agent_id: str, timeout: float = 10.0) -> Optional[Message]:
        """
        Receive a message for the specified agent.
        Returns None if timeout occurs.
        """
        if agent_id not in self._queues:
            raise ValueError(f"Agent {agent_id} not registered")
        
        try:
            return await asyncio.wait_for(
                self._queues[agent_id].get(), 
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None
    
    def get_registered_agents(self) -> list[str]:
        """Get list of registered agent IDs."""
        return list(self._queues.keys())
    
    async def start(self) -> None:
        """Start the message bus."""
        self._running = True
    
    async def stop(self) -> None:
        """Stop the message bus and clean up resources."""
        self._running = False
        self._queues.clear()


# Global message bus instance for compatibility
_message_bus: Optional[MessageBus] = None


def get_message_bus() -> MessageBus:
    """Get the global message bus instance."""
    global _message_bus
    if _message_bus is None:
        _message_bus = MessageBus()
    return _message_bus
