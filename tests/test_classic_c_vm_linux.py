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
#   - Linux runtime conformance execution for the independent classic C VM.
# - Must-Not:
#   - Use the Rust VM to validate or implement C transitions.
# - Allows:
#   - Inputs: tracked classic C VM implementation, header, and harness.
#   - Outputs: strict C23 and sanitizer conformance results.
#   - Side effects: pytest-owned temporary compiler outputs only.
# - Split-When:
#   - Native C VM conformance requires separate platform runners.
# - Merge-When:
#   - A shared native test harness guarantees the same independent execution.
# - Summary:
#   - Make standalone classic C VM conformance run under Linux pytest.
# - Description:
#   - Builds and executes the full C VM semantic harness using pinned Clang.
# - Usage:
#   - Collected by the repository's Python tests on Linux.
# - Defaults:
#   - Other hosts skip this pinned Linux compiler execution fixture.
#

"""Run the independent classic C VM conformance harness on Linux."""

from __future__ import annotations

from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys

import pytest

LINUX_PLATFORM = "linux"
ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
VM = ROOT / "src/runtime/virtual-machine/adapter-outbound/c"
HARNESS = ROOT / "tests/vm/c_conformance.c"
WARNINGS = (
    "-std=c23",
    "-Wall",
    "-Wextra",
    "-Wconversion",
    "-Werror",
    "-pedantic",
    f"-I{VM}",
)
SANITIZERS = ("-fsanitize=address,undefined", "-fno-omit-frame-pointer")
CROSS_TARGETS = (
    "i686-pc-windows-msvc",
    "x86_64-pc-windows-msvc",
    "aarch64-pc-windows-msvc",
    "wasm32-unknown-unknown",
)


def run_command(command: tuple[str, ...]) -> sp.CompletedProcess[str]:
    """Invoke pinned Clang or the compiled fixture without a shell.

    Returns:
        Completed process with status, output, and diagnostics.

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
def test_classic_c_vm_conformance_on_linux(
    tmp_path: Path,
    sanitizer_flags: tuple[str, ...],
) -> None:
    """Execute C state, binary-stream, EOF, and wrap conformance fixtures."""
    executable = tmp_path / "classic-c-vm"
    compiled = run_command((
        str(CLANG),
        *WARNINGS,
        *sanitizer_flags,
        str(VM / "malbolge_vm.c"),
        str(HARNESS),
        "-o",
        str(executable),
    ))
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    executed = run_command((str(executable),))
    assert executed.returncode == 0, executed.stdout + executed.stderr


@pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM,
    reason="cross-target compiler asset is pinned to the Linux runner",
)
@pytest.mark.parametrize("target", CROSS_TARGETS)
def test_classic_c_vm_cross_target_syntax_on_linux(target: str) -> None:
    """Check the independent C VM on three Windows ABIs and wasm32."""
    compiled = run_command((
        str(CLANG),
        f"--target={target}",
        *WARNINGS,
        "-ffreestanding",
        "-fno-builtin",
        "-fsyntax-only",
        str(VM / "malbolge_vm.c"),
        str(HARNESS),
    ))
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
