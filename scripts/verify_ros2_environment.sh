#!/usr/bin/env bash
set -euo pipefail

if [[ ! -r /opt/ros/jazzy/setup.bash ]]; then
  echo "ROS 2 Jazzy is not installed." >&2
  exit 1
fi

# ROS-generated setup hooks legitimately inspect optional variables. Suspend
# nounset only while importing the trusted environment, then restore it.
set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u

required_packages=(
  ament_cmake
  controller_manager
  gz_ros2_control
  nav2_bringup
  nav2_amcl
  ros_gz_sim
  slam_toolbox
  xacro
)

missing=0
for package in "${required_packages[@]}"; do
  if ! ros2 pkg prefix "${package}" >/dev/null 2>&1; then
    echo "MISSING ${package}" >&2
    missing=1
  else
    echo "OK ${package}"
  fi
done

if [[ "${missing}" -ne 0 ]]; then
  exit 1
fi

echo "ROS_DISTRO=${ROS_DISTRO}"
echo "RMW_IMPLEMENTATION=${RMW_IMPLEMENTATION:-default}"
echo "Environment verification passed."
