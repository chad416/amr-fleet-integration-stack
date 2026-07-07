#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_ROOT="${AMR_ROS_ARTIFACT_ROOT:-${HOME}/.cache/amr_fleet_ros}"
INSTALL_SETUP="${ARTIFACT_ROOT}/install/setup.bash"
LOG_DIR="${ARTIFACT_ROOT}/multi-robot-logs/$(date -u +%Y%m%dT%H%M%SZ)"
LAUNCH_PID=""
GZ_WORLD_PROCESS_PATTERN="gz sim .*amr_simulation/worlds/factory.sdf"
export ROS_DOMAIN_ID="${AMR_TEST_DOMAIN_ID:-45}"

mkdir -p "${LOG_DIR}"

cleanup() {
  local exit_code=$?
  if [[ -n "${LAUNCH_PID}" ]]; then
    kill -INT -- "-${LAUNCH_PID}" 2>/dev/null || true
    sleep 3
    kill -TERM -- "-${LAUNCH_PID}" 2>/dev/null || true
    kill -KILL -- "-${LAUNCH_PID}" 2>/dev/null || true
  fi
  pkill -TERM -f "${GZ_WORLD_PROCESS_PATTERN}" 2>/dev/null || true
  if [[ ${exit_code} -ne 0 ]]; then
    echo "Multi-robot smoke test failed. Log: ${LOG_DIR}/multi-robot.log" >&2
    tail -180 "${LOG_DIR}/multi-robot.log" >&2 || true
  fi
  exit "${exit_code}"
}
trap cleanup EXIT INT TERM

if [[ ! -r /opt/ros/jazzy/setup.bash || ! -r "${INSTALL_SETUP}" ]]; then
  echo "ROS 2 Jazzy and a built workspace are required." >&2
  exit 1
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
# shellcheck disable=SC1090
source "${INSTALL_SETUP}"
set -u

# The ros2 CLI daemon captures ROS_DOMAIN_ID when it starts. Reset it so a
# previous acceptance process cannot leak discovery state into this domain.
ros2 daemon stop >/dev/null 2>&1 || true

wait_for() {
  local description=$1
  shift
  local deadline=$((SECONDS + 90))
  until "$@" >/dev/null 2>&1; do
    if ! kill -0 "${LAUNCH_PID}" 2>/dev/null; then
      echo "Launch exited while waiting for ${description}." >&2
      return 1
    fi
    if (( SECONDS >= deadline )); then
      echo "Timed out waiting for ${description}." >&2
      return 1
    fi
    sleep 1
  done
}

setsid ros2 launch amr_simulation multi_robot_simulation.launch.py headless:=true \
  >"${LOG_DIR}/multi-robot.log" 2>&1 &
LAUNCH_PID=$!

wait_for "simulation clock" timeout 3 ros2 topic echo /clock --once

for robot in amr_01 amr_02; do
  wait_for "${robot} lidar" timeout 3 ros2 topic echo "/${robot}/scan" --once \
    --qos-reliability best_effort
  wait_for "${robot} IMU" timeout 3 ros2 topic echo "/${robot}/imu/data" --once \
    --qos-reliability best_effort
  wait_for "${robot} controller manager" timeout 3 ros2 service type \
    "/${robot}/controller_manager/list_controllers"
  controllers="$(timeout 15 ros2 control list_controllers \
    --controller-manager "/${robot}/controller_manager")"
  grep -Eq '^joint_state_broadcaster.*active' <<<"${controllers}"
  grep -Eq '^base_controller.*active' <<<"${controllers}"
  wait_for "${robot} odometry" timeout 3 ros2 topic echo \
    "/${robot}/base_controller/odom" --once --qos-reliability best_effort
done

for robot in amr_01 amr_02; do
  before="$(timeout 10 ros2 topic echo "/${robot}/base_controller/odom" \
    --field pose.pose.position.x --once --qos-reliability best_effort | head -1)"
  ros2 topic pub --rate 10 --times 15 \
    "/${robot}/base_controller/cmd_vel" geometry_msgs/msg/TwistStamped \
    "{header: {frame_id: ${robot}/base_link}, twist: {linear: {x: 0.20}}}" \
    >"${LOG_DIR}/${robot}-motion.log"
  after="$(timeout 10 ros2 topic echo "/${robot}/base_controller/odom" \
    --field pose.pose.position.x --once --qos-reliability best_effort | head -1)"
  python3 - "${robot}" "${before}" "${after}" <<'PY'
import sys

robot, before, after = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
distance = abs(after - before)
if distance < 0.03:
    raise SystemExit(f'{robot} motion check failed: {distance:.4f} m')
print(f'{robot} motion verified: {distance:.3f} m')
PY
done

echo "Multi-robot simulation smoke test passed."
echo "Evidence: ${LOG_DIR}"
