"""
core/environment.py — Environment management for the multi-agent system.
Provides agent lifecycle management and system-wide coordination.
"""
from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional, Any
from agents.base_agent import BaseAgent


class Environment:
    """
    Environment class that manages multi-agent system lifecycle.
    Provides coordination, monitoring, and resource management.
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._running = False
        self._logger = logging.getLogger(__name__)
    
    async def add_agent(self, agent: BaseAgent) -> None:
        """Add an agent to environment."""
        if agent.agent_id in self._agents:
            raise ValueError(f"Agent {agent.agent_id} already exists")
        
        self._agents[agent.agent_id] = agent
        self._logger.info(f"Agent {agent.agent_id} added to environment")
    
    async def remove_agent(self, agent_id: str) -> None:
        """Remove an agent from environment."""
        if agent_id in self._agents:
            agent = self._agents[agent_id]
            agent.stop()
            del self._agents[agent_id]
            self._logger.info(f"Agent {agent_id} removed from environment")
    
    async def start_all(self) -> None:
        """Start all agents in environment."""
        if self._running:
            raise RuntimeError("Environment is already running")
        
        self._running = True
        self._logger.info("Starting multi-agent environment")
        
        # Start all agents concurrently
        start_tasks = []
        for agent in self._agents.values():
            start_tasks.append(self._start_agent(agent))
        
        await asyncio.gather(*start_tasks)
        self._logger.info(f"All {len(self._agents)} agents started")
    
    async def _start_agent(self, agent: BaseAgent) -> None:
        """Start a single agent with error handling."""
        try:
            await agent.run()
        except Exception as e:
            self._logger.error(f"Failed to start agent {agent.agent_id}: {e}")
            raise
    
    async def stop_all(self) -> None:
        """Stop all agents in environment."""
        if not self._running:
            return
        
        self._running = False
        self._logger.info("Stopping multi-agent environment")
        
        # Stop all agents
        for agent in self._agents.values():
            agent.stop()
        
        self._logger.info("All agents stopped")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)
    
    def get_all_agents(self) -> List[BaseAgent]:
        """Get all agents in environment."""
        return list(self._agents.values())
    
    def get_agent_ids(self) -> List[str]:
        """Get all agent IDs."""
        return list(self._agents.keys())
    
    def is_running(self) -> bool:
        """Check if environment is running."""
        return self._running
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        return {
            "running": self._running,
            "agent_count": len(self._agents),
            "agents": list(self._agents.keys())
        }


# Global environment instance for SPADE compatibility
_environment: Optional[Environment] = None


def get_environment() -> Environment:
    """Get the global environment instance."""
    global _environment
    if _environment is None:
        _environment = Environment()
    return _environment
