"""Metrics exporters for fleet telemetry."""

from __future__ import annotations

from typing import Any

from .telemetry import FleetTelemetrySnapshot, TelemetryEvent


class InfluxLineProtocolExporter:
    """Convert fleet snapshots and events into InfluxDB line protocol."""

    def export_snapshot(self, snapshot: FleetTelemetrySnapshot) -> str:
        lines: list[str] = []
        timestamp_ns = _seconds_to_nanoseconds(snapshot.generated_at)
        for robot in snapshot.robots:
            lines.append(
                "amr_robot,"
                f"robot_id={_escape_tag(robot.robot_id)} "
                f"battery_percent={robot.battery_percent},"
                f"available={_bool_field(robot.available)},"
                f"stale={_bool_field(robot.stale)},"
                f"telemetry_age_seconds={robot.telemetry_age_seconds} "
                f"{timestamp_ns}"
            )
        for mission in snapshot.missions:
            robot_id = mission.robot_id or "unassigned"
            lines.append(
                "amr_mission,"
                f"mission_id={_escape_tag(mission.mission_id)},"
                f"state={_escape_tag(mission.state.value)},"
                f"robot_id={_escape_tag(robot_id)} "
                f"current_stop_index={mission.current_stop_index}i,"
                f"revision={mission.revision}i,"
                f"recovery_attempts={mission.recovery_attempts}i "
                f"{timestamp_ns}"
            )
        for lease in snapshot.station_leases:
            lines.append(
                "amr_station_lease,"
                f"station_id={_escape_tag(lease.station_id)},"
                f"robot_id={_escape_tag(lease.robot_id)},"
                f"mission_id={_escape_tag(lease.mission_id)} "
                f"active=1i,expires_at={lease.expires_at} "
                f"{timestamp_ns}"
            )
        return "\n".join(lines)

    def export_events(self, events: tuple[TelemetryEvent, ...]) -> str:
        return "\n".join(self._event_line(event) for event in events)

    def _event_line(self, event: TelemetryEvent) -> str:
        timestamp_ns = _seconds_to_nanoseconds(event.timestamp)
        payload_size = len(event.payload)
        return (
            "amr_event,"
            f"event_type={_escape_tag(event.event_type)},"
            f"source={_escape_tag(event.source)},"
            f"severity={_escape_tag(event.severity)} "
            f"sequence={event.sequence}i,payload_size={payload_size}i "
            f"{timestamp_ns}"
        )


def _seconds_to_nanoseconds(value: float) -> int:
    return int(value * 1_000_000_000)


def _bool_field(value: bool) -> str:
    return "true" if value else "false"


def _escape_tag(value: Any) -> str:
    text = str(value)
    return (
        text.replace("\\", "\\\\")
        .replace(" ", "\\ ")
        .replace(",", "\\,")
        .replace("=", "\\=")
    )
