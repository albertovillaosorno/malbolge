# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Linux native execution of guest C heap, frame, startup, and byte vectors.
# - Must-Not:
#   - Use host allocator or streams as the guest semantic authority.
# - Allows:
#   - Inputs: standalone guest core C sources and deterministic test harness.
#   - Outputs: exact pass/fail from pinned-Clang C23 and sanitizer runs.
#   - Side effects: pytest-owned temporary native executable creation.
# - Split-When:
#   - Guest core platform runners require independent platform contracts.
# - Merge-When:
#   - One native runner owns exactly the same platform coverage.
# - Summary:
#   - Execute the Windows-tested guest runtime core on Linux CI.
# - Description:
#   - Pins 4,000-operation allocator and frame/byte/startup conformance.
# - Usage:
#   - Collected with repository Python tests on Linux.
# - Defaults:
#   - Non-Linux hosts skip this pinned native binary fixture.
#

"""Execute the guest runtime C core conformance suite on Linux."""

from __future__ import annotations

from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys

import pytest

LINUX_PLATFORM = "linux"
ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
RUNTIME = ROOT / "src/runtime/guest-runtime"
HARNESS = ROOT / "tests/runtime/guest_runtime_conformance.c"
CORE_SOURCES = tuple(
    RUNTIME / f"domain/{name}.c"
    for name in ("heap", "byte_stream", "frame", "startup")
)
WARNINGS = (
    "-std=c23",
    "-ffreestanding",
    "-fno-builtin",
    "-Wall",
    "-Wextra",
    "-Wconversion",
    "-Werror",
    "-pedantic",
    f"-I{RUNTIME / "contract"}",
)
SANITIZERS = ("-fsanitize=address,undefined", "-fno-omit-frame-pointer")


def run_command(command: tuple[str, ...]) -> sp.CompletedProcess[str]:
    """Execute a deterministic compiler or conformance command.

    Returns:
        Completed process with status and captured diagnostics.

    """
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        shell=False,
        timeout=30,
    )


@pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM,
    reason="the pinned native executable is built with Linux Clang",
)
@pytest.mark.parametrize(
    "sanitizer_flags",
    [(), SANITIZERS],
    ids=["strict", "asan-ubsan"],
)
def test_guest_runtime_core_conformance_on_linux(
    tmp_path: Path,
    sanitizer_flags: tuple[str, ...],
) -> None:
    """Check C heap, frame, byte, and startup behavior with both tool modes."""
    executable = tmp_path / "guest-runtime-core"
    compiled = run_command((
        str(CLANG),
        *WARNINGS,
        *sanitizer_flags,
        *(str(source) for source in CORE_SOURCES),
        str(HARNESS),
        "-o",
        str(executable),
    ))
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    executed = run_command((str(executable),))
    assert executed.returncode == 0, executed.stdout + executed.stderr
