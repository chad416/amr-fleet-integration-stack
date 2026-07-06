"""Verification of environment-driven runtime configuration."""

import unittest

from amr_fleet_core.runtime_server import FleetRuntimeConfig, build_runtime_api


class RuntimeServerTests(unittest.TestCase):
    def test_minimal_environment_builds_deployable_api(self) -> None:
        config = FleetRuntimeConfig.from_environment(
            {
                "AMR_HTTP_HOST": "127.0.0.1",
                "AMR_HTTP_PORT": "8090",
                "AMR_STATION_IDS": "infeed,outfeed,charger",
                "MQTT_HOST": "mqtt",
            }
        )
        api = build_runtime_api(config)
        self.assertEqual(("infeed", "outfeed", "charger"), config.station_ids)
        self.assertEqual("mqtt", config.mqtt_host)
        self.assertEqual(200, api.telemetry(now=1.0).status)

    def test_influx_configuration_requires_token(self) -> None:
        with self.assertRaisesRegex(ValueError, "INFLUX_TOKEN"):
            FleetRuntimeConfig.from_environment({"INFLUX_URL": "http://influxdb:8086"})

    def test_invalid_duplicate_station_and_port_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unique station"):
            FleetRuntimeConfig.from_environment({"AMR_STATION_IDS": "infeed,infeed"})
        with self.assertRaisesRegex(ValueError, "ports"):
            FleetRuntimeConfig.from_environment({"AMR_HTTP_PORT": "70000"})


if __name__ == "__main__":
    unittest.main()
