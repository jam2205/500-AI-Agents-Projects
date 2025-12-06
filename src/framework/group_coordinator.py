"""Coordinator for agent groups (Market Ops, Trading Ops, Research, etc.)."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from .base_agent import BaseAgent, Message, AgentRole


@dataclass
class GroupReport:
    """Report from a group coordinator."""
    group_name: str
    timestamp: str
    status: str  # "active", "alert", "issue"
    agent_statuses: Dict[str, Dict[str, Any]]
    key_insights: List[str]
    alerts: List[str]


class GroupCoordinator:
    """Coordinates a group of agents working on related tasks."""

    def __init__(
        self,
        group_name: str,
        coordinator_id: str,
        coordinator_role: AgentRole,
        message_bus=None
    ):
        """Initialize group coordinator."""
        self.group_name = group_name
        self.coordinator_id = coordinator_id
        self.coordinator_role = coordinator_role
        self.message_bus = message_bus
        self.agents: Dict[str, BaseAgent] = {}
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.group_state: Dict[str, Any] = {}
        self.alerts: List[str] = []

    async def add_agent(self, agent: BaseAgent):
        """Add an agent to the group."""
        self.agents[agent.config.agent_id] = agent

        # Subscribe agent to messages
        if self.message_bus:
            await self.message_bus.subscribe(
                agent.config.agent_id,
                agent.receive_message
            )

    async def remove_agent(self, agent_id: str):
        """Remove an agent from the group."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            # Cancel any active tasks
            if agent_id in self.active_tasks:
                self.active_tasks[agent_id].cancel()

    async def broadcast_to_group(self, message: Message):
        """Broadcast a message to all agents in the group."""
        if self.message_bus:
            await self.message_bus.publish(message)

    async def request_agent_analysis(
        self,
        agent_id: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Request analysis from a specific agent."""
        if agent_id not in self.agents:
            return None

        agent = self.agents[agent_id]
        return await agent.analyze(data)

    async def coordinate_workflow(
        self,
        workflow_name: str,
        agents_sequence: List[str],
        initial_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a coordinated workflow across multiple agents."""
        results = {}
        current_data = initial_data

        for agent_id in agents_sequence:
            if agent_id not in self.agents:
                continue

            try:
                agent = self.agents[agent_id]
                # Pass output of previous agent as input
                result = await agent.analyze(current_data)
                results[agent_id] = result
                current_data = result  # Chain results
            except Exception as e:
                results[agent_id] = {"error": str(e)}

        return {
            "workflow": workflow_name,
            "timestamp": datetime.utcnow().isoformat(),
            "results": results
        }

    async def start_continuous_task(
        self,
        agent_id: str,
        task_name: str,
        interval: float,
        task_func: Any
    ):
        """Start a continuous task for an agent."""
        async def run_continuously():
            while True:
                try:
                    await task_func()
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.alerts.append(f"Error in {task_name}: {str(e)}")
                    await asyncio.sleep(interval)

        task = asyncio.create_task(run_continuously())
        self.active_tasks[f"{agent_id}:{task_name}"] = task

    async def generate_group_report(self) -> GroupReport:
        """Generate a status report for the group."""
        agent_statuses = {}
        alerts = []

        for agent_id, agent in self.agents.items():
            state = agent.get_state()
            agent_statuses[agent_id] = state

        # Identify alerts
        for agent_id, agent in self.agents.items():
            if agent.state.get("alert"):
                alerts.append(
                    f"Alert from {agent_id}: {agent.state.get('alert_reason')}"
                )

        status = "active"
        if alerts:
            status = "alert"
        if self.group_state.get("issue"):
            status = "issue"

        return GroupReport(
            group_name=self.group_name,
            timestamp=datetime.utcnow().isoformat(),
            status=status,
            agent_statuses=agent_statuses,
            key_insights=self.group_state.get("insights", []),
            alerts=alerts
        )

    async def initialize_group(self):
        """Initialize all agents in the group."""
        tasks = [agent.initialize() for agent in self.agents.values()]
        await asyncio.gather(*tasks)

    async def shutdown_group(self):
        """Shutdown all agents in the group."""
        # Cancel all active tasks
        for task in self.active_tasks.values():
            task.cancel()

        # Shutdown agents
        tasks = [agent.shutdown() for agent in self.agents.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

    def get_agent_ids(self) -> List[str]:
        """Get all agent IDs in the group."""
        return list(self.agents.keys())

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get a specific agent."""
        return self.agents.get(agent_id)
