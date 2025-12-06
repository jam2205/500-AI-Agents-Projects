"""Service Registry - Centralized service discovery for multi-service architecture.

Agents and services register themselves and discover other services.
Handles service metadata, health checks, and endpoint discovery.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import json


class ServiceStatus(Enum):
    """Service operational status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceEndpoint:
    """Endpoint information for a service."""
    name: str
    host: str
    port: int
    protocol: str = "http"  # http, grpc, websocket
    path: str = ""

    @property
    def url(self) -> str:
        """Get full URL for endpoint."""
        base = f"{self.protocol}://{self.host}:{self.port}"
        if self.path:
            return base + self.path
        return base


@dataclass
class ServiceInfo:
    """Complete service information for registry."""
    service_id: str
    service_name: str
    service_type: str  # "analytics", "ml", "data", "forecast", "backtest"
    version: str
    description: str
    endpoints: List[ServiceEndpoint]
    status: ServiceStatus = ServiceStatus.UNKNOWN
    capabilities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # Other service_ids
    health_check_url: Optional[str] = None
    registered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_heartbeat: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        data['endpoints'] = [{'name': e.name, 'url': e.url, 'protocol': e.protocol} for e in self.endpoints]
        return data


class ServiceRegistry:
    """Central registry for service discovery."""

    def __init__(self):
        """Initialize registry."""
        self.services: Dict[str, ServiceInfo] = {}
        self.service_index: Dict[str, List[str]] = {}  # Type -> [service_ids]
        self.dependency_graph: Dict[str, List[str]] = {}  # Service -> dependencies

    def register_service(self, service_info: ServiceInfo) -> bool:
        """
        Register a service in the registry.

        Args:
            service_info: Service information

        Returns:
            True if registered successfully
        """
        if service_info.service_id in self.services:
            print(f"⚠️  Service {service_info.service_id} already registered, updating...")

        # Register service
        self.services[service_info.service_id] = service_info

        # Index by type
        if service_info.service_type not in self.service_index:
            self.service_index[service_info.service_type] = []
        if service_info.service_id not in self.service_index[service_info.service_type]:
            self.service_index[service_info.service_type].append(service_info.service_id)

        # Track dependencies
        self.dependency_graph[service_info.service_id] = service_info.dependencies

        print(f"✅ Registered service: {service_info.service_name} ({service_info.service_id})")
        print(f"   Endpoints: {[e.name for e in service_info.endpoints]}")

        return True

    def deregister_service(self, service_id: str) -> bool:
        """Deregister a service."""
        if service_id not in self.services:
            return False

        service = self.services.pop(service_id)

        # Remove from type index
        if service.service_type in self.service_index:
            self.service_index[service.service_type].remove(service_id)

        # Remove from dependency graph
        if service_id in self.dependency_graph:
            del self.dependency_graph[service_id]

        print(f"🗑️  Deregistered service: {service_id}")
        return True

    def get_service(self, service_id: str) -> Optional[ServiceInfo]:
        """Get service information by ID."""
        return self.services.get(service_id)

    def get_services_by_type(self, service_type: str) -> List[ServiceInfo]:
        """Get all services of a given type."""
        service_ids = self.service_index.get(service_type, [])
        return [self.services[sid] for sid in service_ids if sid in self.services]

    def get_healthy_services(self, service_type: str) -> List[ServiceInfo]:
        """Get healthy services of a given type."""
        services = self.get_services_by_type(service_type)
        return [s for s in services if s.status == ServiceStatus.HEALTHY]

    def update_service_status(
        self,
        service_id: str,
        status: ServiceStatus,
        timestamp: Optional[str] = None
    ) -> bool:
        """Update service status."""
        if service_id not in self.services:
            return False

        service = self.services[service_id]
        service.status = status
        service.last_heartbeat = timestamp or datetime.utcnow().isoformat()

        return True

    def get_service_endpoint(
        self,
        service_id: str,
        endpoint_name: str = "default"
    ) -> Optional[ServiceEndpoint]:
        """Get specific endpoint of a service."""
        service = self.get_service(service_id)
        if not service:
            return None

        for endpoint in service.endpoints:
            if endpoint.name == endpoint_name:
                return endpoint

        # Return first endpoint if not found
        return service.endpoints[0] if service.endpoints else None

    def resolve_dependency(
        self,
        requester_id: str,
        capability_required: str
    ) -> Optional[ServiceInfo]:
        """
        Resolve a service dependency - find a service with a capability.

        Args:
            requester_id: ID of service requesting
            capability_required: Required capability

        Returns:
            ServiceInfo of a service with that capability
        """
        for service_id, service in self.services.items():
            if service.status != ServiceStatus.HEALTHY:
                continue
            if capability_required in service.capabilities:
                return service

        return None

    def get_service_topology(self) -> Dict[str, Any]:
        """Get the complete service topology."""
        return {
            "services": len(self.services),
            "types": list(self.service_index.keys()),
            "by_type": {
                stype: len(ids) for stype, ids in self.service_index.items()
            },
            "dependencies": self.dependency_graph,
            "status_summary": {
                ServiceStatus.HEALTHY.value: len([
                    s for s in self.services.values()
                    if s.status == ServiceStatus.HEALTHY
                ]),
                ServiceStatus.DEGRADED.value: len([
                    s for s in self.services.values()
                    if s.status == ServiceStatus.DEGRADED
                ]),
                ServiceStatus.UNHEALTHY.value: len([
                    s for s in self.services.values()
                    if s.status == ServiceStatus.UNHEALTHY
                ]),
            }
        }

    def list_services(self, service_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all services or services of a type."""
        if service_type:
            services = self.get_services_by_type(service_type)
        else:
            services = list(self.services.values())

        return [s.to_dict() for s in services]

    def export_registry(self) -> str:
        """Export registry as JSON."""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": self.list_services(),
            "topology": self.get_service_topology()
        }
        return json.dumps(data, indent=2)


# Global registry instance
_global_registry = ServiceRegistry()


def get_registry() -> ServiceRegistry:
    """Get the global service registry."""
    return _global_registry


def register_service(service_info: ServiceInfo) -> bool:
    """Register a service (convenience function)."""
    return _global_registry.register_service(service_info)


def get_service(service_id: str) -> Optional[ServiceInfo]:
    """Get service by ID (convenience function)."""
    return _global_registry.get_service(service_id)


def get_services_by_type(service_type: str) -> List[ServiceInfo]:
    """Get services by type (convenience function)."""
    return _global_registry.get_services_by_type(service_type)


def get_healthy_services(service_type: str) -> List[ServiceInfo]:
    """Get healthy services by type (convenience function)."""
    return _global_registry.get_healthy_services(service_type)
