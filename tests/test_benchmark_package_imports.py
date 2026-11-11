# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Cross-root benchmark package import regressions.
# - Must-Not:
#   - Run benchmark measurements during test collection.
# - Allows:
#   - Inputs: the repository's benchmark import roots.
#   - Outputs: independent import admission assertions.
#   - Side effects: isolated Python subprocesses only.
# - Split-When:
#   - Import boundaries have independent package contracts.
# - Merge-When:
#   - Another test suite covers the same import roots.
# - Summary:
#   - Verify arena and accelerator benchmarks coexist on sys.path.
# - Description:
#   - Exercise both repository Python import path orders in fresh interpreters.
# - Usage:
#   - Run with the repository-pinned pytest environment.
# - Defaults:
#   - Missing either benchmark package fails collection evidence.
#

"""Both benchmark roots must be importable under repository Python paths."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NESTED = ROOT / "src/performance/benchmarking/composition"
PROBE = """
from pathlib import Path
from benchmarks import accelerator, arena
assert Path(accelerator.__file__).resolve() == Path(ARG_ACCELERATOR)
assert Path(arena.__file__).resolve() == Path(ARG_ARENA)
"""


@pytest.mark.parametrize("nested_first", [True, False])
def test_arena_and_accelerator_benchmark_packages_coexist(
    nested_first: bool, tmp_path: Path
) -> None:
    """A regular benchmarking package must not mask the arena namespace."""
    paths = (NESTED, ROOT) if nested_first else (ROOT, NESTED)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(str(path) for path in paths)
    probe = "\n".join(
        (
            f"ARG_ACCELERATOR = {str(NESTED / 'benchmarks/accelerator/__init__.py')!r}",
            f"ARG_ARENA = {str(ROOT / 'benchmarks/arena/__init__.py')!r}",
            PROBE,
        )
    )
    result = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
