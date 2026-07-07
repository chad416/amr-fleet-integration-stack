#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_ROOT="${AMR_ROS_ARTIFACT_ROOT:-${HOME}/.cache/amr_fleet_ros}"
INSTALL_SETUP="${ARTIFACT_ROOT}/install/setup.bash"
LOG_DIR="${ARTIFACT_ROOT}/navigation-logs/$(date -u +%Y%m%dT%H%M%SZ)"
LAUNCH_PID=""
GZ_WORLD_PROCESS_PATTERN="gz sim .*amr_simulation/worlds/factory.sdf"
GOAL_X="${AMR_NAV_GOAL_X:--2.4}"
GOAL_Y="${AMR_NAV_GOAL_Y:--1.5}"
GOAL_YAW="${AMR_NAV_GOAL_YAW:-0.0}"
export ROS_DOMAIN_ID="${AMR_TEST_DOMAIN_ID:-43}"

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
    echo "Navigation smoke test failed. Launch log: ${LOG_DIR}/navigation.log" >&2
    tail -160 "${LOG_DIR}/navigation.log" >&2 || true
    if [[ -r "${LOG_DIR}/acceptance.log" ]]; then
      echo "Acceptance client log:" >&2
      tail -80 "${LOG_DIR}/acceptance.log" >&2 || true
    fi
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

wait_for_lifecycle_active() {
  local node_name=$1
  local deadline=$((SECONDS + 120))
  until timeout 3 ros2 lifecycle get "${node_name}" 2>/dev/null | grep -q '^active '; do
    if ! kill -0 "${LAUNCH_PID}" 2>/dev/null; then
      echo "Navigation launch exited while waiting for ${node_name}." >&2
      return 1
    fi
    if (( SECONDS >= deadline )); then
      echo "Timed out waiting for ${node_name} to become active." >&2
      return 1
    fi
    sleep 1
  done
}

wait_for_action_server() {
  local action_name=$1
  local deadline=$((SECONDS + 60))
  until timeout 5 ros2 action info "${action_name}" 2>/dev/null | grep -q 'Action servers: 1'; do
    if ! kill -0 "${LAUNCH_PID}" 2>/dev/null; then
      echo "Navigation launch exited while waiting for ${action_name}." >&2
      return 1
    fi
    if (( SECONDS >= deadline )); then
      echo "Timed out waiting for ${action_name} action server." >&2
      return 1
    fi
    sleep 1
  done
}

stop_factory_gazebo_processes

setsid ros2 launch amr_navigation navigation.launch.py headless:=true \
  >"${LOG_DIR}/navigation.log" 2>&1 &
LAUNCH_PID=$!

wait_for_lifecycle_active /map_server
wait_for_lifecycle_active /amcl
wait_for_lifecycle_active /planner_server
wait_for_lifecycle_active /controller_server
wait_for_lifecycle_active /bt_navigator
wait_for_lifecycle_active /collision_monitor
wait_for_action_server /compute_path_to_pose
wait_for_action_server /follow_path
wait_for_action_server /navigate_to_pose

timeout 240 ros2 run amr_navigation navigation_acceptance.py \
  --x "${GOAL_X}" --y "${GOAL_Y}" --yaw "${GOAL_YAW}" \
  >"${LOG_DIR}/acceptance.log" 2>&1

echo "Navigation smoke test passed."
echo "Evidence: ${LOG_DIR}"
