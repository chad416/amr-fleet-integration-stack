"""Verification of bounded InfluxDB writes and telemetry export deduplication."""

import unittest
from urllib.request import Request

from amr_fleet_core import create_fleet_api
from amr_fleet_core.influx_runtime import (
    FleetTelemetryExportService,
    InfluxWriteClient,
    InfluxWriteConfig,
)
from test_api import robot_payload


class RecordingTransport:
    def __init__(self, statuses: list[int] | None = None) -> None:
        self.statuses = list(statuses or [204])
        self.requests: list[Request] = []

    def __call__(self, request: Request, timeout: float) -> int:
        self.requests.append(request)
        self.last_timeout = timeout
        return self.statuses.pop(0)


class InfluxRuntimeTests(unittest.TestCase):
    def config(self, *, max_attempts: int = 3) -> InfluxWriteConfig:
        return InfluxWriteConfig(
            "http://influxdb:8086",
            "amr",
            "fleet",
            "secret-token",
            max_attempts=max_attempts,
        )

    def test_writer_uses_v2_endpoint_authentication_and_bounded_retry(self) -> None:
        transport = RecordingTransport([503, 204])
        delays: list[float] = []
        writer = InfluxWriteClient(
            self.config(),
            transport=transport,
            sleeper=delays.append,
        )
        writer.write("amr_robot,robot_id=amr-01 battery_percent=80.0 1")

        self.assertEqual(2, len(transport.requests))
        request = transport.requests[-1]
        self.assertIn("/api/v2/write?", request.full_url)
        self.assertIn("org=amr", request.full_url)
        self.assertEqual("Token secret-token", request.get_header("Authorization"))
        self.assertEqual([1.0], delays)

    def test_export_service_does_not_repeat_audit_events(self) -> None:
        transport = RecordingTransport([204, 204])
        writer = InfluxWriteClient(self.config(), transport=transport)
        api = create_fleet_api(station_ids={"infeed"}, clock=lambda: 100.0)
        api.update_robot(robot_payload())
        service = FleetTelemetryExportService(api, writer)

        first_lines = service.export_once(now=100.0)
        second_lines = service.export_once(now=101.0)

        first_payload = transport.requests[0].data.decode("utf-8")
        second_payload = transport.requests[1].data.decode("utf-8")
        self.assertGreater(first_lines, second_lines)
        self.assertIn("amr_event", first_payload)
        self.assertNotIn("amr_event", second_payload)

    def test_writer_raises_after_configured_attempt_budget(self) -> None:
        transport = RecordingTransport([500, 500])
        writer = InfluxWriteClient(
            self.config(max_attempts=2),
            transport=transport,
            sleeper=lambda _: None,
        )
        with self.assertRaisesRegex(RuntimeError, "after 2 attempts"):
            writer.write("amr_event sequence=1i 1")


if __name__ == "__main__":
    unittest.main()
