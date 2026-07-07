"""Minimal JSON/HTTP adapter for the fleet API."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any
from urllib.parse import parse_qs, urlparse

from .api import ApiResponse, FleetApi


class FleetHttpApplication:
    """Small deterministic HTTP router around :class:`FleetApi`."""

    def __init__(self, api: FleetApi) -> None:
        self.api = api

    def handle(
        self,
        method: str,
        raw_path: str,
        body: dict[str, Any] | None = None,
    ) -> ApiResponse:
        parsed = urlparse(raw_path)
        path = parsed.path.rstrip("/") or "/"
        parts = [part for part in path.split("/") if part]
        payload = body or {}

        if method == "GET" and parts == ["healthz"]:
            return ApiResponse(True, HTTPStatus.OK, {"status": "ok"})

        if method == "GET" and parts == ["telemetry"]:
            query = parse_qs(parsed.query)
            now = _query_float(query, "now")
            return self.api.telemetry(now=now)

        if method == "POST" and parts == ["missions"]:
            return self.api.submit_mission(payload)

        if method == "POST" and parts == ["dispatch"]:
            return self.api.dispatch_all(payload)

        if method == "GET" and len(parts) == 2 and parts[0] == "missions":
            return self.api.mission(parts[1])

        if method == "POST" and len(parts) >= 3 and parts[0] == "missions":
            mission_id = parts[1]
            command = "/".join(parts[2:])
            if command == "dispatch":
                return self.api.dispatch(mission_id, payload)
            if command == "start":
                return self.api.start(mission_id)
            if command == "arrive":
                return self.api.arrive_at_station_approach(mission_id)
            if command == "station-access":
                return self.api.request_station_access(mission_id, payload)
            if command == "dock/start":
                return self.api.start_docking(mission_id, payload)
            if command == "dock/confirm":
                return self.api.confirm_docked(mission_id, payload)
            if command == "transfer/complete":
                return self.api.complete_transfer(mission_id, payload)
            if command == "pause":
                return self.api.pause(mission_id)
            if command == "resume":
                return self.api.resume(mission_id)
            if command == "cancel":
                return self.api.cancel(mission_id, payload)
            if command == "recovery/start":
                return self.api.begin_recovery(mission_id, payload)
            if command == "recovery/complete":
                return self.api.complete_recovery(mission_id)

        if (
            method == "POST"
            and len(parts) == 3
            and parts[0] == "robots"
            and parts[2] == "telemetry"
        ):
            payload = dict(payload)
            payload.setdefault("robot_id", parts[1])
            return self.api.update_robot(payload)

        return ApiResponse(
            False,
            HTTPStatus.NOT_FOUND,
            {"error": {"code": "RouteNotFound", "message": f"{method} {path}"}},
        )


def make_handler(app: FleetHttpApplication) -> type[BaseHTTPRequestHandler]:
    class FleetHttpHandler(BaseHTTPRequestHandler):
        server_version = "AMRFleetHTTP/0.1"

        def do_GET(self) -> None:
            self._handle("GET")

        def do_POST(self) -> None:
            self._handle("POST")

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _handle(self, method: str) -> None:
            try:
                payload = self._read_payload()
                response = app.handle(method, self.path, payload)
            except json.JSONDecodeError as error:
                response = ApiResponse(
                    False,
                    HTTPStatus.BAD_REQUEST,
                    {"error": {"code": "InvalidJson", "message": str(error)}},
                )
            encoded = json.dumps(response.body, sort_keys=True).encode("utf-8")
            self.send_response(int(response.status))
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _read_payload(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length == 0:
                return {}
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise json.JSONDecodeError("top-level JSON value must be an object", "", 0)
            return payload

    return FleetHttpHandler


def create_server(
    api: FleetApi,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> ThreadingHTTPServer:
    app = FleetHttpApplication(api)
    return ThreadingHTTPServer((host, port), make_handler(app))


def _query_float(query: dict[str, list[str]], key: str) -> float | None:
    values = query.get(key)
    if not values:
        return None
    return float(values[0])
