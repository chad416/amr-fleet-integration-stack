"""ROS 2 node that exposes the fleet domain core through AMR interfaces."""

from __future__ import annotations

from typing import Any

from amr_fleet_core import create_fleet_api

from .adapter_contracts import (
    MissionGoalRequest,
    mission_payload_from_goal,
    progress_percent,
    terminal_result_from_api_response,
    waypoint_catalog_from_json,
)

try:
    from amr_interfaces.action import ExecuteMission
    from amr_interfaces.msg import MissionState, RobotState
    from amr_interfaces.srv import RequestStationAccess
    import rclpy
    from rclpy.action import ActionServer
    from rclpy.node import Node
except ImportError:  # pragma: no cover - exercised only on non-ROS developer hosts
    rclpy = None
    ActionServer = object
    Node = object
    ExecuteMission = None
    MissionState = None
    RobotState = None
    RequestStationAccess = None


class FleetAdapterNode(Node):
    """Adapter boundary between ROS transport and the transport-independent core."""

    def __init__(self) -> None:
        super().__init__("amr_fleet_adapter")
        self.declare_parameter("station_ids", ["station_infeed", "station_outfeed"])
        self.declare_parameter("minimum_battery_percent", 30.0)
        self.declare_parameter("telemetry_stale_after_seconds", 3.0)
        self.declare_parameter("station_lease_seconds", 30.0)
        self.declare_parameter("recovery_max_attempts", 3)
        self.declare_parameter("telemetry_publish_period_seconds", 1.0)
        self.declare_parameter("waypoint_records_json", "[]")

        self._catalog = waypoint_catalog_from_json(
            self.get_parameter("waypoint_records_json").value
        )
        self._api = create_fleet_api(
            station_ids=set(self.get_parameter("station_ids").value),
            minimum_battery=float(self.get_parameter("minimum_battery_percent").value),
            telemetry_stale_after=float(
                self.get_parameter("telemetry_stale_after_seconds").value
            ),
            station_lease_seconds=float(self.get_parameter("station_lease_seconds").value),
            recovery_max_attempts=int(self.get_parameter("recovery_max_attempts").value),
            waypoint_catalog=self._catalog,
            clock=lambda: self.get_clock().now().nanoseconds * 1e-9,
        )

        self._mission_pub = self.create_publisher(MissionState, "fleet/mission_states", 10)
        self._robot_pub = self.create_publisher(RobotState, "fleet/robot_states", 10)
        self.create_subscription(RobotState, "fleet/robot_updates", self._on_robot_state, 10)
        self.create_service(
            RequestStationAccess,
            "fleet/request_station_access",
            self._on_station_access,
        )
        self._action_server = ActionServer(
            self,
            ExecuteMission,
            "fleet/execute_mission",
            self._execute_mission,
        )
        period = float(self.get_parameter("telemetry_publish_period_seconds").value)
        self.create_timer(period, self._publish_telemetry)

    def _execute_mission(self, goal_handle: Any) -> Any:
        goal = goal_handle.request
        request = MissionGoalRequest(
            mission_id=goal.mission_id,
            station_ids=tuple(goal.station_ids),
            waypoint_names=tuple(goal.waypoint_names),
        )
        submit = self._api.submit_mission(mission_payload_from_goal(request, self._catalog))
        if not submit.ok:
            return self._action_result(False, "failed", submit.body["error"]["code"], submit.body)

        dispatch = self._api.dispatch(goal.mission_id, {})
        if not dispatch.ok:
            return self._action_result(
                False,
                "failed",
                dispatch.body["error"]["code"],
                dispatch.body,
            )

        start = self._api.start(goal.mission_id)
        if not start.ok:
            return self._action_result(False, "failed", start.body["error"]["code"], start.body)

        feedback = ExecuteMission.Feedback()
        mission = start.body["mission"]
        feedback.state = mission["state"]
        feedback.current_stop_index = mission["current_stop_index"]
        feedback.current_station_id = mission["current_stop"]["station_id"]
        feedback.progress_percent = progress_percent(
            mission["state"],
            mission["current_stop_index"],
            len(goal.station_ids),
        )
        feedback.detail = "mission dispatched and started by fleet adapter"
        goal_handle.publish_feedback(feedback)
        goal_handle.succeed()
        result_data = terminal_result_from_api_response(start.body)
        return self._action_result(
            True,
            result_data["terminal_state"],
            "",
            {"detail": "mission accepted by fleet adapter"},
        )

    def _on_station_access(self, request: Any, response: Any) -> Any:
        result = self._api.request_station_access(
            request.mission_id,
            {"now": self.get_clock().now().nanoseconds * 1e-9},
        )
        response.granted = result.ok
        response.error_code = "" if result.ok else result.body["error"]["code"]
        response.detail = (
            "station access granted" if result.ok else result.body["error"]["message"]
        )
        if result.ok:
            lease = result.body["lease"]
            response.lease.lease_id = lease["lease_id"]
            response.lease.station_id = lease["station_id"]
            response.lease.robot_id = lease["robot_id"]
            response.lease.mission_id = lease["mission_id"]
            _assign_time(response.lease.granted_at, lease["granted_at"])
            _assign_time(response.lease.expires_at, lease["expires_at"])
        return response

    def _on_robot_state(self, message: Any) -> None:
        self._api.update_robot(
            {
                "robot_id": message.robot_id,
                "pose": {
                    "x": message.pose.x,
                    "y": message.pose.y,
                    "yaw": message.pose.theta,
                    "frame_id": "map",
                },
                "battery_percent": message.battery_percent,
                "health": message.health,
                "available": message.available,
                "telemetry_at": self.get_clock().now().nanoseconds * 1e-9,
            }
        )

    def _publish_telemetry(self) -> None:
        telemetry = self._api.telemetry()
        fleet = telemetry.body["fleet"]
        active_missions = fleet["active_mission_by_robot"]
        now_msg = self.get_clock().now().to_msg()
        for robot in fleet["robots"]:
            msg = RobotState()
            msg.stamp = now_msg
            msg.robot_id = robot["robot_id"]
            msg.pose.x = robot["pose"]["x"]
            msg.pose.y = robot["pose"]["y"]
            msg.pose.theta = robot["pose"]["yaw"]
            msg.battery_percent = robot["battery_percent"]
            msg.health = robot["health"]
            msg.available = robot["available"]
            msg.active_mission_id = active_missions.get(robot["robot_id"], "")
            faults = []
            if robot["stale"]:
                faults.append("TELEMETRY_STALE")
            if robot["health"] not in {"healthy", "degraded"}:
                faults.append(robot["health"].upper())
            msg.active_fault_codes = faults
            self._robot_pub.publish(msg)

        for mission in fleet["missions"]:
            msg = MissionState()
            msg.stamp = now_msg
            msg.mission_id = mission["mission_id"]
            msg.robot_id = mission["robot_id"] or ""
            msg.state = mission["state"]
            msg.current_stop_index = mission["current_stop_index"]
            msg.current_station_id = mission["current_station_id"]
            msg.station_lease_id = mission["station_lease_id"] or ""
            msg.revision = mission["revision"]
            msg.detail = mission["failure_reason"] or ""
            self._mission_pub.publish(msg)

    def _action_result(
        self,
        success: bool,
        terminal_state: str,
        error_code: str,
        detail: Any,
    ) -> Any:
        result = ExecuteMission.Result()
        result.success = success
        result.terminal_state = terminal_state
        result.error_code = error_code
        result.detail = str(detail)
        return result


def _assign_time(message: Any, seconds: float) -> None:
    whole_seconds = int(seconds)
    message.sec = whole_seconds
    message.nanosec = int((seconds - whole_seconds) * 1_000_000_000)


def main() -> None:
    if rclpy is None:
        raise RuntimeError("rclpy is required to run fleet_adapter_node")
    rclpy.init()
    node = FleetAdapterNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
