"""Alarm evaluation for fleet dashboards and remote monitoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import MissionState
from .telemetry import FleetTelemetrySnapshot


@dataclass(frozen=True, slots=True)
class FleetAlarm:
    alarm_id: str
    severity: str
    source: str
    message: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "alarm_id": self.alarm_id,
            "severity": self.severity,
            "source": self.source,
            "message": self.message,
            "metadata": dict(self.metadata),
        }


class FleetAlarmEvaluator:
    """Evaluate dashboard alarms from a read-only fleet telemetry snapshot."""

    def __init__(
        self,
        *,
        critical_battery_percent: float = 15.0,
        lease_expiry_warning_seconds: float = 5.0,
    ) -> None:
        if not 0.0 <= critical_battery_percent <= 100.0:
            raise ValueError("critical_battery_percent must be in [0, 100]")
        if lease_expiry_warning_seconds < 0.0:
            raise ValueError("lease_expiry_warning_seconds cannot be negative")
        self.critical_battery_percent = critical_battery_percent
        self.lease_expiry_warning_seconds = lease_expiry_warning_seconds

    def evaluate(self, snapshot: FleetTelemetrySnapshot) -> tuple[FleetAlarm, ...]:
        alarms: list[FleetAlarm] = []
        for robot in snapshot.robots:
            if robot.stale:
                alarms.append(
                    FleetAlarm(
                        alarm_id=f"robot:{robot.robot_id}:telemetry_stale",
                        severity="warning",
                        source=robot.robot_id,
                        message="Robot telemetry is stale",
                        metadata={"telemetry_age_seconds": robot.telemetry_age_seconds},
                    )
                )
            if robot.battery_percent <= self.critical_battery_percent:
                alarms.append(
                    FleetAlarm(
                        alarm_id=f"robot:{robot.robot_id}:battery_critical",
                        severity="critical",
                        source=robot.robot_id,
                        message="Robot battery is below the critical threshold",
                        metadata={
                            "battery_percent": robot.battery_percent,
                            "threshold_percent": self.critical_battery_percent,
                        },
                    )
                )
        for mission in snapshot.missions:
            if mission.state is MissionState.FAILED:
                alarms.append(
                    FleetAlarm(
                        alarm_id=f"mission:{mission.mission_id}:failed",
                        severity="critical",
                        source=mission.mission_id,
                        message="Mission failed",
                        metadata={"failure_reason": mission.failure_reason},
                    )
                )
        for lease in snapshot.station_leases:
            remaining = lease.expires_at - snapshot.generated_at
            if remaining <= self.lease_expiry_warning_seconds:
                alarms.append(
                    FleetAlarm(
                        alarm_id=f"station:{lease.station_id}:lease_expiring",
                        severity="warning",
                        source=lease.station_id,
                        message="Station lease is close to expiry",
                        metadata={
                            "lease_id": lease.lease_id,
                            "remaining_seconds": remaining,
                        },
                    )
                )
        return tuple(alarms)
