"""Mission and fleet domain core.

This package intentionally has no ROS imports. ROS, HTTP, OPC UA, and MQTT
adapters call into this domain layer and translate its errors at the boundary.
"""

from .alarms import FleetAlarm, FleetAlarmEvaluator
from .api import ApiResponse, FleetApi, create_fleet_api
from .charging import ChargeMissionRequest, ChargePolicy
from .coordination import RouteCoordinator, RouteReservation
from .dispatch import NearestEligibleDispatcher
from .docking import DockingCommand, DockingPhase, PseudoDockingController
from .errors import (
    DomainError,
    DuplicateMissionConflict,
    InvalidTransition,
    LeaseInvalid,
    NoEligibleRobot,
    NotFound,
    RecoveryLimitExceeded,
    StationBusy,
    TrafficConflict,
)
from .fault_campaign import FaultScenarioResult, campaign_summary, run_l0_fault_campaign
from .fleet import FleetService
from .grafana import build_grafana_dashboard, validate_grafana_dashboard
from .http_api import FleetHttpApplication, create_server
from .mission import Mission
from .models import MissionState, MissionStop, Pose2D, RobotHealth, RobotSnapshot
from .observability import InfluxLineProtocolExporter
from .ot import PlcStationSimulator, StationBridge, StationBridgeDecision, StationPlcSnapshot
from .ot_transport import MqttStationCodec, OpcUaStationNodeSet, OpcUaWrite
from .station import StationAccessManager, StationLease
from .supervision import (
    AutonomyHealth,
    AutonomyMode,
    AutonomySupervisor,
    MotionEnableInterlock,
    SupervisionDecision,
)
from .telemetry import (
    FleetTelemetrySnapshot,
    InMemoryTelemetrySink,
    MissionTelemetry,
    RobotTelemetry,
    TelemetryEvent,
    project_fleet_telemetry,
)
from .traffic import TrafficManager, TrafficReservation
from .waypoints import Waypoint, WaypointCatalog

__all__ = [
    "ApiResponse",
    "AutonomyHealth",
    "AutonomyMode",
    "AutonomySupervisor",
    "ChargeMissionRequest",
    "ChargePolicy",
    "DomainError",
    "DuplicateMissionConflict",
    "DockingCommand",
    "DockingPhase",
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
    "MotionEnableInterlock",
    "MqttStationCodec",
    "NearestEligibleDispatcher",
    "NoEligibleRobot",
    "NotFound",
    "OpcUaStationNodeSet",
    "OpcUaWrite",
    "Pose2D",
    "PseudoDockingController",
    "RecoveryLimitExceeded",
    "RobotHealth",
    "RobotSnapshot",
    "RobotTelemetry",
    "RouteCoordinator",
    "RouteReservation",
    "PlcStationSimulator",
    "StationBridge",
    "StationBridgeDecision",
    "StationAccessManager",
    "StationBusy",
    "StationLease",
    "StationPlcSnapshot",
    "SupervisionDecision",
    "TelemetryEvent",
    "TrafficConflict",
    "TrafficManager",
    "TrafficReservation",
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
