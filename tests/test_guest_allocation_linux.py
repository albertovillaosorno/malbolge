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
#   - Native Linux execution of public guest C allocation wrappers.
# - Must-Not:
#   - Substitute host allocation for guest-bound heap semantics.
# - Allows:
#   - Inputs: tracked allocator, startup, wrappers, and C harness.
#   - Outputs: native strict C23 and sanitizer conformance verdicts.
#   - Side effects: pytest-owned native object/executable creation.
# - Split-When:
#   - Linux allocation wrapper coverage gains independent platform policy.
# - Merge-When:
#   - A shared native runner executes these exact wrapper vectors on Linux.
# - Summary:
#   - Execute Windows-only guest libc allocator vectors on Linux too.
# - Description:
#   - Uses pinned Clang and test-renamed C allocation entry points.
# - Usage:
#   - Collected by Python tests on Linux without host allocator fallback.
# - Defaults:
#   - Non-Linux hosts skip this native executable check.
#

"""Run public guest C allocation wrapper conformance on Linux."""

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
HARNESS = ROOT / "tests/runtime/guest_allocation_wrapper_conformance.c"
WARNINGS = (
    "-std=c23",
    "-fno-builtin",
    "-Wall",
    "-Wextra",
    "-Wconversion",
    "-Werror",
    "-pedantic",
    f"-I{RUNTIME / "contract"}",
)
SANITIZERS = ("-fsanitize=address,undefined", "-fno-omit-frame-pointer")
RENAMED_ALLOCATIONS = (
    "-Dmalloc=malbolge_test_malloc",
    "-Dcalloc=malbolge_test_calloc",
    "-Drealloc=malbolge_test_realloc",
    "-Dfree=malbolge_test_free",
)


def run_command(command: tuple[str, ...]) -> sp.CompletedProcess[str]:
    """Run pinned compiler or one deterministic native wrapper fixture.

    Returns:
        Completed process containing exact status and diagnostics.

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
def test_guest_allocation_wrappers_on_linux(
    tmp_path: Path,
    sanitizer_flags: tuple[str, ...],
) -> None:
    """Verify guest malloc/calloc/realloc/free and startup gate behavior."""
    wrapper_object = tmp_path / "guest-allocator-wrapper.o"
    compiled = run_command((
        str(CLANG),
        *WARNINGS,
        *sanitizer_flags,
        "-ffreestanding",
        *RENAMED_ALLOCATIONS,
        f"-I{LIBC / "contract/include"}",
        "-c",
        str(LIBC / "domain/allocation.c"),
        "-o",
        str(wrapper_object),
    ))
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    executable = tmp_path / "guest-allocation"
    linked = run_command((
        str(CLANG),
        *WARNINGS,
        *sanitizer_flags,
        str(RUNTIME / "domain/heap.c"),
        str(RUNTIME / "domain/startup.c"),
        str(wrapper_object),
        str(HARNESS),
        "-o",
        str(executable),
    ))
    assert linked.returncode == 0, linked.stdout + linked.stderr

    executed = run_command((str(executable),))
    assert executed.returncode == 0, executed.stdout + executed.stderr
