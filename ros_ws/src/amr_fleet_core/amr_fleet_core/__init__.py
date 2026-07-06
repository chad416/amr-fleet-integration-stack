"""Mission and fleet domain core.

This package intentionally has no ROS imports. ROS, HTTP, OPC UA, and MQTT
adapters call into this domain layer and translate its errors at the boundary.
"""

from .alarms import FleetAlarm, FleetAlarmEvaluator
from .dispatch import NearestEligibleDispatcher
from .errors import (
    DomainError,
    DuplicateMissionConflict,
    InvalidTransition,
    LeaseInvalid,
    NoEligibleRobot,
    NotFound,
    RecoveryLimitExceeded,
    StationBusy,
)
from .fault_campaign import FaultScenarioResult, campaign_summary, run_l0_fault_campaign
from .fleet import FleetService
from .grafana import build_grafana_dashboard, validate_grafana_dashboard
from .api import ApiResponse, FleetApi, create_fleet_api
from .http_api import FleetHttpApplication, create_server
from .mission import Mission
from .models import MissionState, MissionStop, Pose2D, RobotHealth, RobotSnapshot
from .observability import InfluxLineProtocolExporter
from .ot import PlcStationSimulator, StationBridge, StationBridgeDecision, StationPlcSnapshot
from .ot_transport import MqttStationCodec, OpcUaStationNodeSet, OpcUaWrite
from .station import StationAccessManager, StationLease
from .telemetry import (
    FleetTelemetrySnapshot,
    InMemoryTelemetrySink,
    MissionTelemetry,
    RobotTelemetry,
    TelemetryEvent,
    project_fleet_telemetry,
)
from .waypoints import Waypoint, WaypointCatalog

__all__ = [
    "ApiResponse",
    "DomainError",
    "DuplicateMissionConflict",
    "FleetApi",
    "FleetAlarm",
    "FleetAlarmEvaluator",
    "FleetService",
    "FaultScenarioResult",
    "FleetHttpApplication",
    "FleetTelemetrySnapshot",
    "InvalidTransition",
    "InMemoryTelemetrySink",
    "InfluxLineProtocolExporter",
    "LeaseInvalid",
    "Mission",
    "MissionState",
    "MissionStop",
    "MissionTelemetry",
    "MqttStationCodec",
    "NearestEligibleDispatcher",
    "NoEligibleRobot",
    "NotFound",
    "OpcUaStationNodeSet",
    "OpcUaWrite",
    "Pose2D",
    "RecoveryLimitExceeded",
    "RobotHealth",
    "RobotSnapshot",
    "RobotTelemetry",
    "PlcStationSimulator",
    "StationBridge",
    "StationBridgeDecision",
    "StationAccessManager",
    "StationBusy",
    "StationLease",
    "StationPlcSnapshot",
    "TelemetryEvent",
    "Waypoint",
    "WaypointCatalog",
    "build_grafana_dashboard",
    "campaign_summary",
    "create_fleet_api",
    "create_server",
    "project_fleet_telemetry",
    "run_l0_fault_campaign",
    "validate_grafana_dashboard",
]
