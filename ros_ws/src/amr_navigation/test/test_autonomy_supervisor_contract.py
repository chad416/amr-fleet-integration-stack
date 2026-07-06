"""Static contract checks for the ROS autonomy supervisor adapter."""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_supervisor_exposes_required_health_and_operator_topics() -> None:
    source = (PACKAGE_ROOT / "scripts" / "autonomy_supervisor.py").read_text()
    required = {
        "localization/valid",
        "sensors/primary_range_healthy",
        "sensors/alternate_range_healthy",
        "fleet/connected",
        "navigation/home_route_available",
        "safety/emergency_stop",
        "operator/start",
        "autonomy/mode",
        "autonomy/motion_permitted",
    }
    assert all(topic in source for topic in required)
    assert "MotionEnableInterlock" in source


def test_navigation_launch_starts_autonomy_supervisor() -> None:
    launch = (PACKAGE_ROOT / "launch" / "navigation.launch.py").read_text()
    assert "autonomy_supervisor.py" in launch
