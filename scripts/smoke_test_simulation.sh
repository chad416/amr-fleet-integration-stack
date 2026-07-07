#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_ROOT="${AMR_ROS_ARTIFACT_ROOT:-${HOME}/.cache/amr_fleet_ros}"
INSTALL_SETUP="${ARTIFACT_ROOT}/install/setup.bash"
LOG_DIR="${ARTIFACT_ROOT}/smoke-logs/$(date -u +%Y%m%dT%H%M%SZ)"
LAUNCH_PID=""
GZ_WORLD_PROCESS_PATTERN="gz sim .*amr_simulation/worlds/factory.sdf"
export ROS_DOMAIN_ID="${AMR_TEST_DOMAIN_ID:-42}"

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
    echo "Simulation smoke test failed. Launch log: ${LOG_DIR}/simulation.log" >&2
    tail -120 "${LOG_DIR}/simulation.log" >&2 || true
  fi
  exit "${exit_code}"
}
trap cleanup EXIT INT TERM

if [[ ! -r /opt/ros/jazzy/setup.bash ]]; then
  echo "ROS 2 Jazzy is not installed." >&2
  exit 1
fi
if [[ ! -r "${INSTALL_SETUP}" ]]; then
  echo "Built workspace not found; run scripts/build_and_test_ros2.sh first." >&2
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
  local deadline=$((SECONDS + 60))
  until "$@" >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
      echo "Timed out waiting for ${description}." >&2
      return 1
    fi
    sleep 1
  done
}

stop_factory_gazebo_processes

setsid ros2 launch amr_simulation simulation.launch.py headless:=true \
  >"${LOG_DIR}/simulation.log" 2>&1 &
LAUNCH_PID=$!

wait_for "simulation clock" timeout 3 ros2 topic echo /clock --once \
  --qos-reliability best_effort
wait_for "laser scan" timeout 3 ros2 topic echo /scan --once \
  --qos-reliability best_effort
wait_for "IMU data" timeout 3 ros2 topic echo /imu/data --once \
  --qos-reliability best_effort
wait_for "controller manager" timeout 3 ros2 service type /controller_manager/list_controllers

CONTROLLERS="$(timeout 15 ros2 control list_controllers --controller-manager /controller_manager)"
grep -Eq '^joint_state_broadcaster[[:space:]]+joint_state_broadcaster/JointStateBroadcaster[[:space:]]+active' <<<"${CONTROLLERS}"
grep -Eq '^base_controller[[:space:]]+diff_drive_controller/DiffDriveController[[:space:]]+active' <<<"${CONTROLLERS}"

wait_for "wheel odometry" timeout 3 ros2 topic echo /base_controller/odom --once \
  --qos-reliability best_effort
BEFORE_X="$(timeout 10 ros2 topic echo /base_controller/odom --field pose.pose.position.x \
  --once --qos-reliability best_effort | head -1)"

ros2 topic pub --rate 10 --times 20 \
  /base_controller/cmd_vel geometry_msgs/msg/TwistStamped \
  "{header: {frame_id: base_link}, twist: {linear: {x: 0.25}, angular: {z: 0.0}}}" \
  >"${LOG_DIR}/motion-command.log"

AFTER_X="$(timeout 10 ros2 topic echo /base_controller/odom --field pose.pose.position.x \
  --once --qos-reliability best_effort | head -1)"
python3 - "${BEFORE_X}" "${AFTER_X}" <<'PY'
import sys

before = float(sys.argv[1])
after = float(sys.argv[2])
distance = abs(after - before)
if distance < 0.05:
    raise SystemExit(f'AMR motion check failed: odometry changed only {distance:.4f} m')
print(f'AMR motion verified: odometry changed {distance:.3f} m')
PY

echo "Simulation smoke test passed."
echo "Evidence: ${LOG_DIR}"
