#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root (for example: sudo bash scripts/bootstrap_ros2_jazzy.sh)." >&2
  exit 1
fi

if [[ ! -r /etc/os-release ]]; then
  echo "Cannot identify the operating system." >&2
  exit 1
fi

# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID}" != "ubuntu" || "${VERSION_CODENAME:-}" != "noble" ]]; then
  echo "This baseline requires Ubuntu 24.04 (Noble); found ${PRETTY_NAME:-unknown}." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  locales \
  software-properties-common

locale-gen en_US en_US.UTF-8
update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
add-apt-repository -y universe

# Pin the repository bootstrap package so the build is reproducible. Override
# ROS_APT_SOURCE_VERSION explicitly only after reviewing the upstream release.
ROS_APT_SOURCE_VERSION="${ROS_APT_SOURCE_VERSION:-1.2.0}"
ROS_APT_SOURCE_DEB="ros2-apt-source_${ROS_APT_SOURCE_VERSION}.noble_all.deb"
curl --fail --location --retry 3 \
  --output "/tmp/${ROS_APT_SOURCE_DEB}" \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/${ROS_APT_SOURCE_DEB}"
dpkg -i "/tmp/${ROS_APT_SOURCE_DEB}"

apt-get update
apt-get upgrade -y
apt-get install -y --no-install-recommends \
  ros-dev-tools \
  ros-jazzy-desktop \
  ros-jazzy-gz-ros2-control \
  ros-jazzy-nav2-bringup \
  ros-jazzy-navigation2 \
  ros-jazzy-ros-gz \
  ros-jazzy-ros2-control \
  ros-jazzy-ros2-controllers \
  ros-jazzy-slam-toolbox \
  ros-jazzy-xacro

if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  rosdep init
fi
rosdep update

echo "ROS 2 Jazzy development environment installed successfully."
echo "Source it with: source /opt/ros/jazzy/setup.bash"

