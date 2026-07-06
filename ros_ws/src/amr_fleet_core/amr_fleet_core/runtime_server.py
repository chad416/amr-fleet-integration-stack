"""Production-shaped HTTP, MQTT station, and InfluxDB runtime processes."""

from __future__ import annotations

import importlib
import os
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .api import FleetApi, create_fleet_api
from .http_api import create_server
from .influx_runtime import FleetTelemetryExportService, InfluxWriteClient, InfluxWriteConfig
from .station_runtime import MqttPlcStationSimulator, MqttStationCoordinator


@dataclass(frozen=True, slots=True)
class FleetRuntimeConfig:
    host: str
    port: int
    station_ids: tuple[str, ...]
    minimum_battery_percent: float
    telemetry_stale_after_seconds: float
    station_lease_seconds: float
    recovery_max_attempts: int
    mqtt_host: str | None
    mqtt_port: int
    influx: InfluxWriteConfig | None
    export_period_seconds: float

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> FleetRuntimeConfig:
        values = os.environ if environment is None else environment
        station_ids = tuple(
            station.strip()
            for station in values.get(
                "AMR_STATION_IDS",
                "station_infeed,station_outfeed,charger",
            ).split(",")
            if station.strip()
        )
        influx_url = values.get("INFLUX_URL", "").strip()
        influx = None
        if influx_url:
            influx = InfluxWriteConfig(
                influx_url,
                values.get("INFLUX_ORG", "amr"),
                values.get("INFLUX_BUCKET", "fleet"),
                _required(values, "INFLUX_TOKEN"),
                timeout_seconds=float(values.get("INFLUX_TIMEOUT_SECONDS", "5.0")),
            )
        mqtt_host = values.get("MQTT_HOST", "").strip() or None
        config = cls(
            host=values.get("AMR_HTTP_HOST", "0.0.0.0"),
            port=int(values.get("AMR_HTTP_PORT", "8080")),
            station_ids=station_ids,
            minimum_battery_percent=float(values.get("AMR_MINIMUM_BATTERY", "30.0")),
            telemetry_stale_after_seconds=float(
                values.get("AMR_TELEMETRY_STALE_SECONDS", "3.0")
            ),
            station_lease_seconds=float(values.get("AMR_STATION_LEASE_SECONDS", "30.0")),
            recovery_max_attempts=int(values.get("AMR_RECOVERY_MAX_ATTEMPTS", "3")),
            mqtt_host=mqtt_host,
            mqtt_port=int(values.get("MQTT_PORT", "1883")),
            influx=influx,
            export_period_seconds=float(values.get("AMR_EXPORT_PERIOD_SECONDS", "1.0")),
        )
        config._validate()
        return config

    def _validate(self) -> None:
        if not self.host.strip():
            raise ValueError("AMR_HTTP_HOST must be non-empty")
        if not 1 <= self.port <= 65535 or not 1 <= self.mqtt_port <= 65535:
            raise ValueError("runtime ports must be in [1, 65535]")
        if not self.station_ids or len(set(self.station_ids)) != len(self.station_ids):
            raise ValueError("AMR_STATION_IDS must contain unique station IDs")
        if self.export_period_seconds <= 0.0:
            raise ValueError("AMR_EXPORT_PERIOD_SECONDS must be positive")


class PahoPublisher:
    def __init__(self, client: Any) -> None:
        self._client = client

    def publish(
        self,
        topic: str,
        payload: str,
        *,
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        info = self._client.publish(topic, payload, qos=qos, retain=retain)
        if int(info.rc) != 0:
            raise RuntimeError(f"MQTT publish failed with code {info.rc}")


class PahoFleetStationBridge:
    """Run station lease synchronization and status callbacks on an MQTT client."""

    def __init__(
        self,
        api: FleetApi,
        station_ids: tuple[str, ...],
        host: str,
        port: int,
        *,
        synchronize_period: float = 0.25,
    ) -> None:
        mqtt = importlib.import_module("paho.mqtt.client")
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id="amr-fleet-station-bridge",
        )
        self._coordinator = MqttStationCoordinator(
            api,
            PahoPublisher(self._client),
            station_ids,
        )
        self._host = host
        self._port = port
        self._period = synchronize_period
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._synchronize,
            name="station-lease-synchronizer",
            daemon=True,
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def start(self) -> None:
        self._client.connect(self._host, self._port, keepalive=30)
        self._client.loop_start()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5.0)
        self._client.disconnect()
        self._client.loop_stop()

    def _on_connect(
        self,
        client: Any,
        userdata: Any,
        flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        del userdata, flags, properties
        if reason_code.is_failure:
            raise RuntimeError(f"MQTT station bridge connection failed: {reason_code}")
        for topic in self._coordinator.status_topics:
            client.subscribe(topic, qos=1)

    def _on_message(self, client: Any, userdata: Any, message: Any) -> None:
        del client, userdata
        try:
            self._coordinator.handle_status(
                str(message.topic),
                bytes(message.payload).decode("utf-8"),
                received_at=time.monotonic(),
            )
        except (RuntimeError, ValueError) as error:
            print(f"station status rejected: {error}", flush=True)

    def _synchronize(self) -> None:
        while not self._stop.wait(self._period):
            try:
                self._coordinator.synchronize_leases(now=time.monotonic())
            except (RuntimeError, ValueError) as error:
                print(f"station lease synchronization failed: {error}", flush=True)


class TelemetryExportThread:
    def __init__(self, service: FleetTelemetryExportService, *, period: float) -> None:
        self._service = service
        self._period = period
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name="influx-telemetry-exporter",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5.0)

    def _run(self) -> None:
        while not self._stop.wait(self._period):
            try:
                self._service.export_once(now=time.monotonic())
            except (OSError, RuntimeError, ValueError) as error:
                print(f"telemetry export failed: {error}", flush=True)


def build_runtime_api(config: FleetRuntimeConfig) -> FleetApi:
    return create_fleet_api(
        station_ids=config.station_ids,
        minimum_battery=config.minimum_battery_percent,
        telemetry_stale_after=config.telemetry_stale_after_seconds,
        station_lease_seconds=config.station_lease_seconds,
        recovery_max_attempts=config.recovery_max_attempts,
    )


def main() -> None:
    config = FleetRuntimeConfig.from_environment()
    api = build_runtime_api(config)
    workers: list[Any] = []
    if config.influx is not None:
        exporter = FleetTelemetryExportService(api, InfluxWriteClient(config.influx))
        workers.append(TelemetryExportThread(exporter, period=config.export_period_seconds))
    if config.mqtt_host is not None:
        workers.append(
            PahoFleetStationBridge(
                api,
                config.station_ids,
                config.mqtt_host,
                config.mqtt_port,
            )
        )
    for worker in workers:
        worker.start()
    server = create_server(api, config.host, config.port)
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
        for worker in reversed(workers):
            worker.stop()


def station_simulator_main() -> None:
    mqtt = importlib.import_module("paho.mqtt.client")
    station_id = os.environ.get("AMR_STATION_ID", "station_infeed")
    host = os.environ.get("MQTT_HOST", "mqtt")
    port = int(os.environ.get("MQTT_PORT", "1883"))
    simulator = MqttPlcStationSimulator(station_id)
    lock = threading.Lock()
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"amr-plc-simulator-{station_id}",
    )

    def on_connect(
        connected_client: Any,
        userdata: Any,
        flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        del userdata, flags, properties
        if reason_code.is_failure:
            raise RuntimeError(f"MQTT PLC simulator connection failed: {reason_code}")
        connected_client.subscribe(simulator.command_topic, qos=1)

    def on_message(connected_client: Any, userdata: Any, message: Any) -> None:
        del userdata
        with lock:
            topic, payload = simulator.handle_command(
                str(message.topic),
                bytes(message.payload).decode("utf-8"),
                now=time.monotonic(),
            )
        connected_client.publish(topic, payload, qos=1, retain=True)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, keepalive=30)
    client.loop_start()
    try:
        while True:
            with lock:
                topic, payload = simulator.status_message(now=time.monotonic())
            client.publish(topic, payload, qos=1, retain=True)
            time.sleep(1.0)
    finally:
        client.disconnect()
        client.loop_stop()


def _required(environment: Mapping[str, str], name: str) -> str:
    value = environment.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required when its integration is enabled")
    return value


if __name__ == "__main__":
    main()
