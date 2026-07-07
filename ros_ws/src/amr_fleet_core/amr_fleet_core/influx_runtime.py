"""InfluxDB v2 writer and periodic fleet telemetry export service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .api import FleetApi
from .observability import InfluxLineProtocolExporter
from .telemetry import project_fleet_telemetry

HttpTransport = Callable[[Request, float], int]
Sleeper = Callable[[float], None]


@dataclass(frozen=True, slots=True)
class InfluxWriteConfig:
    base_url: str
    organization: str
    bucket: str
    token: str
    timeout_seconds: float = 5.0
    max_attempts: int = 3

    def __post_init__(self) -> None:
        text_values = (self.base_url, self.organization, self.bucket, self.token)
        if any(not value.strip() for value in text_values):
            raise ValueError("InfluxDB URL, organization, bucket and token are required")
        if self.timeout_seconds <= 0.0:
            raise ValueError("InfluxDB timeout must be positive")
        if self.max_attempts <= 0:
            raise ValueError("InfluxDB max_attempts must be positive")

    @property
    def write_url(self) -> str:
        query = urlencode(
            {
                "org": self.organization,
                "bucket": self.bucket,
                "precision": "ns",
            }
        )
        return f"{self.base_url.rstrip('/')}/api/v2/write?{query}"


class InfluxWriteClient:
    """Write line protocol with bounded retries and explicit failure reporting."""

    def __init__(
        self,
        config: InfluxWriteConfig,
        *,
        transport: HttpTransport | None = None,
        sleeper: Sleeper = time.sleep,
    ) -> None:
        self.config = config
        self._transport = transport or _default_transport
        self._sleeper = sleeper

    def write(self, line_protocol: str) -> None:
        if not line_protocol.strip():
            return
        request = Request(
            self.config.write_url,
            data=line_protocol.encode("utf-8"),
            headers={
                "Authorization": f"Token {self.config.token}",
                "Content-Type": "text/plain; charset=utf-8",
            },
            method="POST",
        )
        last_status = 0
        for attempt in range(1, self.config.max_attempts + 1):
            last_status = self._transport(request, self.config.timeout_seconds)
            if 200 <= last_status < 300:
                return
            if attempt < self.config.max_attempts:
                self._sleeper(min(2.0 ** (attempt - 1), 5.0))
        raise RuntimeError(
            f"InfluxDB write failed after {self.config.max_attempts} attempts "
            f"with HTTP {last_status}"
        )


class FleetTelemetryExportService:
    """Export current fleet state plus each audit event exactly once per process."""

    def __init__(self, api: FleetApi, writer: InfluxWriteClient) -> None:
        self._api = api
        self._writer = writer
        self._exporter = InfluxLineProtocolExporter()
        self._last_event_sequence = -1

    def export_once(self, *, now: float) -> int:
        snapshot = project_fleet_telemetry(
            self._api.service,
            now=now,
            telemetry_stale_after=self._api.telemetry_stale_after,
        )
        events = tuple(
            event
            for event in self._api.telemetry_sink.events
            if event.sequence > self._last_event_sequence
        )
        sections = [self._exporter.export_snapshot(snapshot)]
        if events:
            sections.append(self._exporter.export_events(events))
        line_protocol = "\n".join(section for section in sections if section)
        self._writer.write(line_protocol)
        if events:
            self._last_event_sequence = events[-1].sequence
        return len(line_protocol.splitlines()) if line_protocol else 0


def _default_transport(request: Request, timeout: float) -> int:
    with urlopen(request, timeout=timeout) as response:
        return int(response.status)
