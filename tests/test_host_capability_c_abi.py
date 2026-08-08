# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Native execution of the independent C host-capability ABI harness.
# - Must-Not:
#   - Call the Rust implementation or perform a real host capability effect.
# - Allows:
#   - Inputs: tracked C codec, header, harness, and pinned repository Clang.
#   - Outputs: one passing or failing pytest result.
#   - Side effects: compilation and execution only inside pytest temporary
#     state.
# - Split-When:
#   - Split when C ABI harness families require independent toolchains.
# - Merge-When:
#   - Merge when another test owns this exact native conformance lifecycle.
# - Summary:
#   - Compiles and runs the independent C host-capability ABI vectors.
# - Description:
#   - Enforces strict warnings and cross-target syntax before native execution.
# - Usage:
#   - Collected by the repository Python test suite on Windows.
# - Defaults:
#   - Skips where the repository Windows Clang executable cannot run.
#

"""Compile and run independent C host-capability ABI conformance vectors."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang.exe"
CAPABILITY_ROOT = ROOT / "src/runtime/virtual-machine/adapter-outbound/c"
GENERIC_SOURCE = CAPABILITY_ROOT / "malbolge_host_capability.c"
MOUSE_SOURCE = CAPABILITY_ROOT / "malbolge_host_capability_mouse.c"
TELEMETRY_SOURCE = CAPABILITY_ROOT / "malbolge_host_capability_telemetry.c"
GENERIC_HARNESS = ROOT / "tests/vm/host_capability_conformance.c"
BUILTIN_HARNESS = ROOT / "tests/vm/host_capability_builtin_conformance.c"
INCLUDE = CAPABILITY_ROOT
NATIVE_HARNESSES = (
    ((GENERIC_SOURCE,), GENERIC_HARNESS, "host-capability-conformance.exe"),
    (
        (GENERIC_SOURCE, MOUSE_SOURCE, TELEMETRY_SOURCE),
        BUILTIN_HARNESS,
        "host-capability-builtins.exe",
    ),
)
WINDOWS_OS_NAME = "nt"
WINDOWS_ABI_TARGETS = (
    "i686-pc-windows-msvc",
    "x86_64-pc-windows-msvc",
    "aarch64-pc-windows-msvc",
)
STRICT_WARNINGS = (
    "-Wall",
    "-Wextra",
    "-Wpedantic",
    "-Wconversion",
    "-Wsign-conversion",
    "-Wshadow",
    "-Wformat=2",
    "-Wundef",
    "-Wcast-qual",
    "-Wcast-align",
    "-Wswitch-enum",
    "-Wswitch-default",
    "-Wvla",
    "-Wimplicit-fallthrough",
    "-Wstrict-prototypes",
    "-Wmissing-prototypes",
    "-Wmissing-variable-declarations",
    "-Wnull-dereference",
    "-Werror",
)


def run_command(
    command: tuple[str, ...],
    cwd: Path,
) -> sp.CompletedProcess[str]:
    """Run one fixed Clang or harness command without a shell.

    Returns:
        The completed process containing its status and captured diagnostics.

    """
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        shell=False,
        timeout=30,
    )


@pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="pinned native C harness uses Windows Clang",
)
def test_host_capability_c_abi(tmp_path: Path) -> None:
    """Compile cross-target syntax and execute all native C ABI vectors."""
    for sources, harness, executable_name in NATIVE_HARNESSES:
        _ = executable_name
        for target in WINDOWS_ABI_TARGETS:
            compiled = run_command(
                (
                    str(CLANG),
                    f"--target={target}",
                    "-std=c23",
                    *STRICT_WARNINGS,
                    f"-I{INCLUDE}",
                    "-fsyntax-only",
                    *(str(source) for source in sources),
                    str(harness),
                ),
                ROOT,
            )
            assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    for sources, harness, executable_name in NATIVE_HARNESSES:
        executable = tmp_path / executable_name
        compiled = run_command(
            (
                str(CLANG),
                "-std=c23",
                *STRICT_WARNINGS,
                f"-I{INCLUDE}",
                *(str(source) for source in sources),
                str(harness),
                "-o",
                str(executable),
            ),
            ROOT,
        )
        assert compiled.returncode == 0, compiled.stdout + compiled.stderr
        executed = run_command((str(executable),), tmp_path)
        assert executed.returncode == 0, executed.stdout + executed.stderr
