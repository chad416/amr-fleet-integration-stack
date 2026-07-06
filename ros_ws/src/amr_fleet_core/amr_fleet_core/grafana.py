"""Grafana dashboard artifact generation for AMR fleet observability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class GrafanaPanelSpec:
    title: str
    measurement: str
    field: str
    unit: str = "short"


DEFAULT_PANELS = (
    GrafanaPanelSpec("Robot Battery", "amr_robot", "battery_percent", "percent"),
    GrafanaPanelSpec("Robot Telemetry Age", "amr_robot", "telemetry_age_seconds", "s"),
    GrafanaPanelSpec("Mission Revisions", "amr_mission", "revision", "short"),
    GrafanaPanelSpec("Recovery Attempts", "amr_mission", "recovery_attempts", "short"),
    GrafanaPanelSpec("Station Lease Expiry", "amr_station_lease", "expires_at", "dateTimeAsIso"),
    GrafanaPanelSpec("Fleet Events", "amr_event", "sequence", "short"),
)


def build_grafana_dashboard(
    *,
    title: str = "AMR Fleet Integration Overview",
    datasource_uid: str = "influxdb",
) -> dict[str, Any]:
    panels = [
        _panel_from_spec(index, spec, datasource_uid=datasource_uid)
        for index, spec in enumerate(DEFAULT_PANELS)
    ]
    return {
        "annotations": {"list": []},
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 0,
        "links": [],
        "liveNow": False,
        "panels": panels,
        "schemaVersion": 39,
        "tags": ["amr", "fleet", "industrial-automation"],
        "templating": {"list": []},
        "time": {"from": "now-1h", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": title,
        "uid": "amr-fleet-overview",
        "version": 1,
        "weekStart": "",
    }


def validate_grafana_dashboard(dashboard: dict[str, Any]) -> None:
    if not dashboard.get("title"):
        raise ValueError("dashboard requires a title")
    panels = dashboard.get("panels")
    if not isinstance(panels, list) or not panels:
        raise ValueError("dashboard requires at least one panel")
    panel_titles = {panel.get("title") for panel in panels}
    required_titles = {panel.title for panel in DEFAULT_PANELS}
    missing = required_titles - panel_titles
    if missing:
        raise ValueError(f"dashboard is missing required panels: {sorted(missing)}")


def _panel_from_spec(
    index: int,
    spec: GrafanaPanelSpec,
    *,
    datasource_uid: str,
) -> dict[str, Any]:
    panel_id = index + 1
    return {
        "datasource": {"type": "influxdb", "uid": datasource_uid},
        "fieldConfig": {
            "defaults": {"unit": spec.unit},
            "overrides": [],
        },
        "gridPos": {
            "h": 8,
            "w": 8,
            "x": (index % 3) * 8,
            "y": (index // 3) * 8,
        },
        "id": panel_id,
        "options": {"legend": {"displayMode": "list", "placement": "bottom"}},
        "targets": [
            {
                "query": (
                    f'from(bucket: "amr_fleet") '
                    f'|> range(start: v.timeRangeStart, stop: v.timeRangeStop) '
                    f'|> filter(fn: (r) => r._measurement == "{spec.measurement}") '
                    f'|> filter(fn: (r) => r._field == "{spec.field}")'
                ),
                "refId": "A",
            }
        ],
        "title": spec.title,
        "type": "timeseries",
    }
