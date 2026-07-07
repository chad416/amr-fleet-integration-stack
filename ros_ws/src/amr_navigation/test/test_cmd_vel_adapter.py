# Copyright 2026 AMR Fleet Integration Stack Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for the Jazzy Nav2-to-controller command boundary."""

import importlib.util
from math import inf, nan
from pathlib import Path
import sys  # noqa: I100 - Ruff owns repository import ordering.

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def load_adapter():
    """Load the installed-script source as a test module."""
    script = PACKAGE_ROOT / 'scripts' / 'cmd_vel_adapter.py'
    specification = importlib.util.spec_from_file_location('cmd_vel_adapter', script)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def test_command_is_clamped_to_model_limits() -> None:
    adapter = load_adapter()
    assert adapter.sanitize_command(2.0, 0.0, -3.0, -0.35, 0.8, 1.4) == (0.8, -1.4)
    assert adapter.sanitize_command(-2.0, 0.0, 3.0, -0.35, 0.8, 1.4) == (-0.35, 1.4)


def test_nonfinite_component_fails_to_zero_command() -> None:
    adapter = load_adapter()
    for command in ((nan, 0.0, 0.0), (0.2, inf, 0.0), (0.2, 0.0, -inf)):
        assert adapter.sanitize_command(*command, -0.35, 0.8, 1.4) == (0.0, 0.0)


def test_lateral_command_is_not_forwarded_to_differential_drive() -> None:
    adapter = load_adapter()
    assert adapter.sanitize_command(0.2, 0.5, 0.3, -0.35, 0.8, 1.4) == (0.2, 0.3)
