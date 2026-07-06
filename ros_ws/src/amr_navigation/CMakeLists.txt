cmake_minimum_required(VERSION 3.8)
project(amr_navigation)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch maps
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/cmd_vel_adapter.py
    scripts/generate_factory_map.py
    scripts/navigation_acceptance.py
    scripts/autonomy_supervisor.py
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
  ament_add_pytest_test(
    navigation_contract
    test/test_navigation_contract.py
  )
  ament_add_pytest_test(
    cmd_vel_adapter
    test/test_cmd_vel_adapter.py
  )
  ament_add_pytest_test(
    autonomy_supervisor_contract
    test/test_autonomy_supervisor_contract.py
  )
endif()

ament_package()
