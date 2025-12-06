"""Central command center for the entire trading agent system."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from .base_agent import AgentRole, Message
from .message_bus import MessageBus
from .group_coordinator import GroupCoordinator


class TradingCommandCenter:
    """Central orchestrator for all trading agent groups."""

    def __init__(self):
        """Initialize the trading command center."""
        self.message_bus = MessageBus()
        self.groups: Dict[str, GroupCoordinator] = {}
        self.system_alerts: List[Dict[str, Any]] = []
        self.market_state: Dict[str, Any] = {}
        self.weekly_profile: Dict[str, Any] = {}
        self.is_running = False

    async def register_group(self, group: GroupCoordinator):
        """Register an agent group with the command center."""
        self.groups[group.group_name] = group
        group.message_bus = self.message_bus

    async def initialize(self):
        """Initialize the entire system."""
        self.is_running = True

        # Start message processing
        asyncio.create_task(self.message_bus.process_messages())

        # Initialize all groups
        tasks = [group.initialize_group() for group in self.groups.values()]
        await asyncio.gather(*tasks)

        # Start system monitoring
        asyncio.create_task(self._monitor_system())

    async def broadcast_alert(
        self,
        alert_type: str,
        content: Dict[str, Any],
        priority: str = "normal"
    ):
        """Broadcast an alert to all agents."""
        message = Message(
            sender_id="command_center",
            sender_role=AgentRole.ALERT_COORDINATOR,
            recipient_ids=[],  # Broadcast
            message_type="alert",
            content={
                "alert_type": alert_type,
                "priority": priority,
                "details": content
            }
        )
        await self.message_bus.publish(message)
        self.system_alerts.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": alert_type,
            "priority": priority,
            "content": content
        })

    async def update_market_state(self, state_update: Dict[str, Any]):
        """Update market state and broadcast to relevant agents."""
        self.market_state.update(state_update)

        # Alert all agents about market state change
        await self.broadcast_alert(
            "market_state_update",
            state_update,
            priority="high"
        )

    async def update_weekly_profile(self, profile: Dict[str, Any]):
        """Update weekly market profile."""
        self.weekly_profile = profile

        # Alert all agents about weekly profile
        await self.broadcast_alert(
            "weekly_profile_update",
            profile,
            priority="high"
        )

    async def get_group(self, group_name: str) -> Optional[GroupCoordinator]:
        """Get a group coordinator by name."""
        return self.groups.get(group_name)

    async def generate_system_report(self) -> Dict[str, Any]:
        """Generate comprehensive system report."""
        group_reports = {}

        for group_name, group in self.groups.items():
            report = await group.generate_group_report()
            group_reports[group_name] = {
                "group_name": report.group_name,
                "timestamp": report.timestamp,
                "status": report.status,
                "num_agents": len(report.agent_statuses),
                "alerts": report.alerts,
                "insights": report.key_insights
            }

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system_running": self.is_running,
            "num_groups": len(self.groups),
            "groups": group_reports,
            "market_state": self.market_state,
            "weekly_profile": self.weekly_profile,
            "recent_system_alerts": self.system_alerts[-10:],
            "message_bus_stats": self.message_bus.get_bus_stats()
        }

    async def _monitor_system(self):
        """Continuously monitor system health."""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every 60 seconds
                report = await self.generate_system_report()

                # Check for issues
                for group_info in report["groups"].values():
                    if group_info["status"] == "issue":
                        await self.broadcast_alert(
                            "group_issue",
                            {"group": group_info["group_name"]},
                            priority="critical"
                        )

            except Exception as e:
                print(f"Error in system monitoring: {e}")

    async def shutdown(self):
        """Shutdown the entire system."""
        self.is_running = False

        # Shutdown all groups
        tasks = [group.shutdown_group() for group in self.groups.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Stop message bus
        await self.message_bus.stop()
