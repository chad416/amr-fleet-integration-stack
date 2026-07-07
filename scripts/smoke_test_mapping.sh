#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_ROOT="${AMR_ROS_ARTIFACT_ROOT:-${HOME}/.cache/amr_fleet_ros}"
INSTALL_SETUP="${ARTIFACT_ROOT}/install/setup.bash"
LOG_DIR="${ARTIFACT_ROOT}/mapping-logs/$(date -u +%Y%m%dT%H%M%SZ)"
LAUNCH_PID=""
GZ_WORLD_PROCESS_PATTERN="gz sim .*amr_simulation/worlds/factory.sdf"
export ROS_DOMAIN_ID="${AMR_TEST_DOMAIN_ID:-44}"

mkdir -p "${LOG_DIR}"

stop_factory_gazebo_processes() {
  pgrep -f "${GZ_WORLD_PROCESS_PATTERN}" >/dev/null 2>&1 || return 0
  pkill -INT -f "${GZ_WORLD_PROCESS_PATTERN}" 2>/dev/null || true
  sleep 2
  pgrep -f "${GZ_WORLD_PROCESS_PATTERN}" >/dev/null 2>&1 || return 0
  pkill -TERM -f "${GZ_WORLD_PROCESS_PATTERN}" 2>/dev/null || true
  sleep 1
  pgrep -f "${GZ_WORLD_PROCESS_PATTERN}" >/dev/null 2>&1 || return 0
  pkill -KILL -f "${GZ_WORLD_PROCESS_PATTERN}" 2>/dev/null || true
}

cleanup() {
  local exit_code=$?
  if [[ -n "${LAUNCH_PID}" ]]; then
    kill -INT -- "-${LAUNCH_PID}" 2>/dev/null || true
    sleep 3
    kill -TERM -- "-${LAUNCH_PID}" 2>/dev/null || true
    sleep 1
    kill -KILL -- "-${LAUNCH_PID}" 2>/dev/null || true
  fi
  stop_factory_gazebo_processes
  if [[ ${exit_code} -ne 0 ]]; then
    echo "Mapping smoke test failed. Launch log: ${LOG_DIR}/mapping.log" >&2
    tail -160 "${LOG_DIR}/mapping.log" >&2 || true
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
      echo "Mapping launch exited while waiting for ${description}." >&2
      return 1
    fi
    if (( SECONDS >= deadline )); then
      echo "Timed out waiting for ${description}." >&2
      return 1
    fi
    sleep 1
  done
}

wait_for_lifecycle_active() {
  local node_name=$1
  local deadline=$((SECONDS + 90))
  until timeout 5 ros2 service call \
    "${node_name}/get_state" lifecycle_msgs/srv/GetState "{}" 2>/dev/null \
    | grep -Eq "label[=:][^[:alnum:]]*active"; do
    if ! kill -0 "${LAUNCH_PID}" 2>/dev/null; then
      echo "Mapping launch exited while waiting for ${node_name}." >&2
      return 1
    fi
    if (( SECONDS >= deadline )); then
      echo "Timed out waiting for ${node_name} to become active." >&2
      return 1
    fi
    sleep 1
  done
}

stop_factory_gazebo_processes

setsid ros2 launch amr_navigation mapping.launch.py headless:=true \
  >"${LOG_DIR}/mapping.log" 2>&1 &
LAUNCH_PID=$!

wait_for "simulation clock" timeout 3 ros2 topic echo /clock --once \
  --qos-reliability best_effort
wait_for "laser scan" timeout 3 ros2 topic echo /scan --once \
  --qos-reliability best_effort
wait_for "controller manager" timeout 3 ros2 service type /controller_manager/list_controllers

CONTROLLERS="$(timeout 15 ros2 control list_controllers --controller-manager /controller_manager)"
grep -Eq '^joint_state_broadcaster[[:space:]]+joint_state_broadcaster/JointStateBroadcaster[[:space:]]+active' <<<"${CONTROLLERS}"
grep -Eq '^base_controller[[:space:]]+diff_drive_controller/DiffDriveController[[:space:]]+active' <<<"${CONTROLLERS}"

wait_for_lifecycle_active /map_saver
wait_for "SLAM map before motion" timeout 5 ros2 topic echo /map --once \
  --qos-durability transient_local

ros2 topic pub --rate 10 --times 20 \
  /base_controller/cmd_vel geometry_msgs/msg/TwistStamped \
  "{header: {frame_id: base_link}, twist: {linear: {x: 0.20}, angular: {z: 0.15}}}" \
  >"${LOG_DIR}/mapping-motion-command.log"

wait_for "SLAM map after motion" timeout 5 ros2 topic echo /map --once \
  --qos-durability transient_local

echo "Mapping smoke test passed."
echo "Evidence: ${LOG_DIR}"
