cmake_minimum_required(VERSION 3.8)
project(amr_simulation)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch worlds
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
  ament_add_pytest_test(
    simulation_contract
    test/test_simulation_contract.py
  )
  ament_add_pytest_test(
    multi_robot_contract
    test/test_multi_robot_contract.py
  )
endif()

ament_package()
