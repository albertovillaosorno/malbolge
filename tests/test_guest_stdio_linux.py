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
#   - Linux execution evidence for guest C stdio byte wrappers.
# - Must-Not:
#   - Substitute host stdio for guest intrinsic semantics.
# - Allows:
#   - Inputs: tracked guest runtime, wrapper, and conformance C sources.
#   - Outputs: successful pinned-Clang compile and byte-exact test execution.
#   - Side effects: pytest-owned temporary object and executable creation.
# - Split-When:
#   - Linux native guest wrapper evidence gains independent implementations.
# - Merge-When:
#   - The cross-target runtime test suite runs this native fixture on Linux.
# - Summary:
#   - Prevents the Windows-only wrapper test from leaving Linux untested.
# - Description:
#   - Builds and executes the same exhaustive guest C byte wrapper vectors.
# - Usage:
#   - Collected by the repository Python test suite on Linux.
# - Defaults:
#   - Other platforms skip this pinned Linux compiler execution fixture.
#

"""Execute the exhaustive guest stdio intrinsic fixture on Linux."""

from __future__ import annotations

from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys

import pytest

LINUX_PLATFORM = "linux"
ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
RUNTIME = ROOT / "src/runtime/guest-runtime"
LIBC = ROOT / "src/runtime/guest-c-library"
HARNESS = ROOT / "tests/runtime/guest_stdio_wrapper_conformance.c"
WARNING_FLAGS = (
    "-std=c23",
    "-fno-builtin",
    "-Wall",
    "-Wextra",
    "-Wconversion",
    "-Werror",
    "-pedantic",
    f"-I{LIBC / "contract/include"}",
    f"-I{RUNTIME / "contract"}",
)


def run_command(command: tuple[str, ...]) -> sp.CompletedProcess[str]:
    """Run a fixed local compiler or fixture with captured diagnostics.

    Returns:
        Completed process carrying the exit code and compiler output.

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
def test_guest_stdio_wrapper_executes_on_linux(tmp_path: Path) -> None:
    """Verify raw bytes and EOF through the actual guest C wrappers."""
    object_file = tmp_path / "guest-stdio.o"
    compiled = run_command((
        str(CLANG),
        *WARNING_FLAGS,
        "-ffreestanding",
        "-Dgetchar=malbolge_test_getchar",
        "-Dputchar=malbolge_test_putchar",
        "-c",
        str(LIBC / "domain/stdio.c"),
        "-o",
        str(object_file),
    ))
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    executable = tmp_path / "guest-stdio"
    linked = run_command((
        str(CLANG),
        *WARNING_FLAGS,
        str(RUNTIME / "domain/byte_stream.c"),
        str(object_file),
        str(HARNESS),
        "-o",
        str(executable),
    ))
    assert linked.returncode == 0, linked.stdout + linked.stderr

    executed = run_command((str(executable),))
    assert executed.returncode == 0, executed.stdout + executed.stderr
