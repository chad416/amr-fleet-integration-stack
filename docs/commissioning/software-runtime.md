# Software Runtime Commissioning

This procedure starts the complete non-ROS OT/IT runtime: fleet HTTP API,
correlated MQTT station bridge, three PLC station simulators, InfluxDB and a
provisioned Grafana dashboard.

## Start

1. Copy `deployment/.env.example` to `.env` and replace every credential.
2. Run `docker compose config` and review the resolved configuration.
3. Run `docker compose up --build --wait`.
4. Verify `http://127.0.0.1:8080/healthz` returns `{"status":"ok"}`.
5. Open Grafana at `http://127.0.0.1:3000` and confirm the `AMR Fleet` folder
   contains the provisioned overview dashboard.

The demo MQTT listener binds only to localhost. Anonymous MQTT is used solely
inside this simulation deployment; production commissioning must enable broker
authentication, TLS, unique client credentials and network segmentation.

## Stop and reset

- Preserve time-series and Grafana state: `docker compose down`.
- Remove only the named demonstration volumes after evidence has been exported:
  `docker compose down --volumes`.

## Acceptance

- All six services report healthy/running.
- Fleet API telemetry writes reach the `amr_fleet` bucket.
- Station entry requests and retained status messages carry the same lease ID.
- A mismatched, stale or faulted station status never advances docking.
- Grafana loads the committed dashboard without manual edits.
