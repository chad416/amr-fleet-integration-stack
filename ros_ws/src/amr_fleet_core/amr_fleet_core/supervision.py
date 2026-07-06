"""Autonomy health supervision and explicit motion-enable interlocking."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AutonomyMode(str, Enum):
    NOMINAL = "nominal"
    RETURN_HOME = "return_home"
    HOLD = "hold"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class AutonomyHealth:
    localization_valid: bool
    primary_range_sensor_healthy: bool
    alternate_range_sensor_healthy: bool
    fleet_connected: bool
    home_route_available: bool
    emergency_stop_active: bool = False


@dataclass(frozen=True, slots=True)
class SupervisionDecision:
    mode: AutonomyMode
    accept_new_missions: bool
    motion_permitted: bool
    reason: str


class MotionEnableInterlock:
    """Require an explicit operator start after every emergency-stop cycle."""

    def __init__(self) -> None:
        self._emergency_stop_active = False
        self._operator_start_received = False

    @property
    def motion_permitted(self) -> bool:
        return not self._emergency_stop_active and self._operator_start_received

    def set_emergency_stop(self, active: bool) -> None:
        self._emergency_stop_active = active
        if active:
            self._operator_start_received = False

    def operator_start(self) -> None:
        if self._emergency_stop_active:
            raise RuntimeError("operator start rejected while emergency stop is active")
        self._operator_start_received = True


class AutonomySupervisor:
    """Choose a fail-safe autonomy mode from required subsystem health."""

    def evaluate(
        self,
        health: AutonomyHealth,
        *,
        motion_enable: bool,
    ) -> SupervisionDecision:
        if health.emergency_stop_active or not motion_enable:
            return SupervisionDecision(
                AutonomyMode.STOPPED,
                accept_new_missions=False,
                motion_permitted=False,
                reason="motion enable is not established",
            )
        if not health.localization_valid:
            return SupervisionDecision(
                AutonomyMode.HOLD,
                accept_new_missions=False,
                motion_permitted=False,
                reason="localization is invalid",
            )
        if not health.primary_range_sensor_healthy:
            if health.alternate_range_sensor_healthy and health.home_route_available:
                return SupervisionDecision(
                    AutonomyMode.RETURN_HOME,
                    accept_new_missions=False,
                    motion_permitted=True,
                    reason="primary range sensor unavailable; alternate return-home path active",
                )
            return SupervisionDecision(
                AutonomyMode.HOLD,
                accept_new_missions=False,
                motion_permitted=False,
                reason="no healthy perception path is available",
            )
        if not health.fleet_connected:
            if health.home_route_available:
                return SupervisionDecision(
                    AutonomyMode.RETURN_HOME,
                    accept_new_missions=False,
                    motion_permitted=True,
                    reason="fleet connection lost; returning to configured home",
                )
            return SupervisionDecision(
                AutonomyMode.HOLD,
                accept_new_missions=False,
                motion_permitted=False,
                reason="fleet connection lost and no home route is available",
            )
        return SupervisionDecision(
            AutonomyMode.NOMINAL,
            accept_new_missions=True,
            motion_permitted=True,
            reason="required autonomy paths are healthy",
        )
