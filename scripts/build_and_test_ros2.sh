#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROS_WORKSPACE="${REPO_ROOT}/ros_ws"
ARTIFACT_ROOT="${AMR_ROS_ARTIFACT_ROOT:-${HOME}/.cache/amr_fleet_ros}"

if [[ ! -r /opt/ros/jazzy/setup.bash ]]; then
  echo "ROS 2 Jazzy is not installed; run scripts/bootstrap_ros2_jazzy.sh first." >&2
  exit 1
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u

cd "${ROS_WORKSPACE}"
mkdir -p "${ARTIFACT_ROOT}"
# ament_python is a colcon build type declared in Python package manifests,
# not an independently installable system dependency. ros-dev-tools above
# supplies the required colcon/setuptools integration.
rosdep install \
  --from-paths src \
  --ignore-src \
  --rosdistro jazzy \
  --skip-keys ament_python \
  -y
colcon --log-base "${ARTIFACT_ROOT}/log" build \
  --build-base "${ARTIFACT_ROOT}/build" \
  --install-base "${ARTIFACT_ROOT}/install" \
  --merge-install \
  --executor sequential \
  --event-handlers console_cohesion+ \
  --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo

set +u
# shellcheck disable=SC1091
source "${ARTIFACT_ROOT}/install/setup.bash"
set -u

colcon --log-base "${ARTIFACT_ROOT}/log-test" test \
  --build-base "${ARTIFACT_ROOT}/build" \
  --install-base "${ARTIFACT_ROOT}/install" \
  --merge-install \
  --executor sequential \
  --event-handlers console_cohesion+
colcon test-result --test-result-base "${ARTIFACT_ROOT}/build" --verbose
python3 -m unittest discover -s "${REPO_ROOT}/ros_ws/src/amr_fleet_core/test" -v
