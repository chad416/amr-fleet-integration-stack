cmake_minimum_required(VERSION 3.8)
project(amr_interfaces)

find_package(ament_cmake REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(unique_identifier_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "action/ExecuteMission.action"
  "msg/MissionState.msg"
  "msg/RobotState.msg"
  "msg/StationLease.msg"
  "srv/RequestStationAccess.srv"
  DEPENDENCIES builtin_interfaces geometry_msgs unique_identifier_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()

