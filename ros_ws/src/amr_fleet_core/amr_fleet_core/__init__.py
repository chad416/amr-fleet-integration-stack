"""Mission and fleet domain core.

This package intentionally has no ROS imports. ROS, HTTP, OPC UA, and MQTT
adapters call into this domain layer and translate its errors at the boundary.
"""

from .dispatch import NearestEligibleDispatcher
from .errors import (
    DomainError,
    DuplicateMissionConflict,
    InvalidTransition,
    LeaseInvalid,
    NoEligibleRobot,
    NotFound,
    StationBusy,
)
from .fleet import FleetService
from .mission import Mission
from .models import MissionState, MissionStop, Pose2D, RobotHealth, RobotSnapshot
from .station import StationAccessManager, StationLease

__all__ = [
    "DomainError",
    "DuplicateMissionConflict",
    "FleetService",
    "InvalidTransition",
    "LeaseInvalid",
    "Mission",
    "MissionState",
    "MissionStop",
    "NearestEligibleDispatcher",
    "NoEligibleRobot",
    "NotFound",
    "Pose2D",
    "RobotHealth",
    "RobotSnapshot",
    "StationAccessManager",
    "StationBusy",
    "StationLease",
]
