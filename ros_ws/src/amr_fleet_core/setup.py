from setuptools import find_packages, setup

PACKAGE_NAME = "amr_fleet_core"


setup(
    name=PACKAGE_NAME,
    version="0.1.0",
    packages=find_packages(exclude=("test", "test.*")),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{PACKAGE_NAME}"]),
        (f"share/{PACKAGE_NAME}", ["package.xml"]),
    ],
    install_requires=["paho-mqtt>=2.1,<3", "setuptools"],
    zip_safe=True,
    maintainer="AMR Fleet Integration Stack Contributors",
    maintainer_email="maintainers@example.com",
    description="Transport-independent mission and fleet domain core.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "fleet_server = amr_fleet_core.runtime_server:main",
            "mqtt_plc_simulator = amr_fleet_core.runtime_server:station_simulator_main",
        ],
    },
    test_suite="test",
)
