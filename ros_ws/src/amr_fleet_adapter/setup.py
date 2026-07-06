from glob import glob

from setuptools import find_packages, setup

PACKAGE_NAME = "amr_fleet_adapter"


setup(
    name=PACKAGE_NAME,
    version="0.1.0",
    packages=find_packages(exclude=("test", "test.*")),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{PACKAGE_NAME}"]),
        (f"share/{PACKAGE_NAME}", ["package.xml"]),
        (f"share/{PACKAGE_NAME}/config", glob("config/*.yaml")),
        (f"share/{PACKAGE_NAME}/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="AMR Fleet Integration Stack Contributors",
    maintainer_email="maintainers@example.com",
    description="ROS 2 adapter exposing the AMR fleet domain core.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "fleet_adapter_node = amr_fleet_adapter.fleet_adapter_node:main",
        ],
    },
    test_suite="test",
)
