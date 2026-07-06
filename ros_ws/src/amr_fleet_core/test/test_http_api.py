"""Verification of the JSON/HTTP adapter."""

import http.client
import json
import threading
import unittest

from amr_fleet_core import create_fleet_api, create_server
from test_api import mission_payload, robot_payload


class HttpApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api = create_fleet_api(
            station_ids={"infeed"},
            station_lease_seconds=10.0,
            telemetry_stale_after=3.0,
            clock=lambda: 100.0,
        )
        self.server = create_server(self.api, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host, self.port = self.server.server_address

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2.0)

    def test_http_boundary_accepts_remote_mission_commands(self) -> None:
        self.assertEqual(
            self._post("/robots/amr-01/telemetry", robot_payload(100.0))[0],
            200,
        )
        self.assertEqual(self._post("/missions", mission_payload("http-1"))[0], 201)
        status, body = self._post("/missions/http-1/dispatch", {"now": 101.0})

        self.assertEqual(status, 200)
        self.assertEqual(body["robot_id"], "amr-01")
        status, body = self._get("/missions/http-1")
        self.assertEqual(status, 200)
        self.assertEqual(body["mission"]["state"], "dispatched")

    def test_http_boundary_accepts_batch_dispatch(self) -> None:
        self.assertEqual(
            self._post("/robots/amr-01/telemetry", robot_payload(100.0))[0],
            200,
        )
        self.assertEqual(self._post("/missions", mission_payload("http-batch"))[0], 201)
        status, body = self._post("/dispatch", {"now": 101.0})

        self.assertEqual(status, 200)
        self.assertEqual(
            body["assignments"],
            [{"mission_id": "http-batch", "robot_id": "amr-01"}],
        )

    def _post(self, path: str, payload: dict) -> tuple[int, dict]:
        encoded = json.dumps(payload).encode("utf-8")
        connection = http.client.HTTPConnection(self.host, self.port, timeout=5.0)
        try:
            connection.request(
                "POST",
                path,
                encoded,
                {"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            return response.status, json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()

    def _get(self, path: str) -> tuple[int, dict]:
        connection = http.client.HTTPConnection(self.host, self.port, timeout=5.0)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            return response.status, json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
