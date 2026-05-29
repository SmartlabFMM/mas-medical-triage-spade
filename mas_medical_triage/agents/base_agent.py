"""
agents/base_agent.py — Classe abstraite commune à tous les agents.
Chaque agent hérite de BaseAgent et implémente process_message().
"""
from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from core.message import Message, MessageType
from core.message_bus import MessageBus
from utils.logger import log_agent_state, log_error


class BaseAgent(ABC):
    """
    Agent de base du système MAS.
    Fournit : connexion au bus, boucle d'écoute, envoi de messages.
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id: str          = agent_id
        self.bus: MessageBus | None = None
        self.queue: asyncio.Queue   = None
        self._running: bool         = False

    async def send(self, message: Message) -> None:
        """Envoie un message via le bus."""
        if self.bus:
            await self.bus.send(message)

    async def run(self) -> None:
        """Boucle principale de l'agent — écoute et traite les messages."""
        self._running = True
        log_agent_state(self.agent_id, "running")
        try:
            while self._running:
                msg = await self.bus.receive(self.agent_id)
                if msg:
                    await self.process_message(msg)
        except asyncio.CancelledError:
            log_agent_state(self.agent_id, "cancelled")
        except Exception as e:
            log_error(f"{self.agent_id} erreur: {e}")
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False

    @abstractmethod
    async def process_message(self, message: Message) -> None:
        """Traite un message reçu. À implémenter par chaque agent."""
        ...

    def _build_message(
        self,
        msg_type: MessageType,
        receiver: str,
        payload: dict,
        patient_id: str | None = None,
    ) -> Message:
        return Message(
            type=msg_type,
            sender=self.agent_id,
            receiver=receiver,
            patient_id=patient_id,
            payload=payload,
        )
