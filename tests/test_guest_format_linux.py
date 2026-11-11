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
#   - Linux native execution for independent guest C formatting kernels.
# - Must-Not:
#   - Use host printf or floating arithmetic as formatting authority.
# - Allows:
#   - Inputs: tracked guest C formatting sources and reviewed native harnesses.
#   - Outputs: pinned C23 and sanitizer semantic conformance results.
#   - Side effects: pytest-owned temporary native executable creation.
# - Split-When:
#   - A formatting family acquires an independent platform test lifecycle.
# - Merge-When:
#   - Another Linux native runner owns these exact nine semantic families.
# - Summary:
#   - Execute the Windows-only guest formatting vectors on Linux too.
# - Description:
#   - Builds all nine formatter/parser/decimal harnesses with pinned Clang.
# - Usage:
#   - Collected by Python tests on Linux independently of the Windows ABI run.
# - Defaults:
#   - Other platforms skip the native Linux executable probes.
#

"""Run the nine freestanding guest C formatting harnesses on Linux."""

from __future__ import annotations

from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys

import pytest

LINUX_PLATFORM = "linux"
ROOT = Path(__file__).resolve().parents[1]
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang"
RUNTIME = ROOT / "src/runtime/guest-runtime"
HARNESS_DIR = ROOT / "tests/runtime"
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
FORMAT_SUITES: dict[str, tuple[tuple[str, ...], str]] = {
    "format": (("format",), "guest_format_conformance"),
    "parser": (("format_parse",), "guest_format_parse_conformance"),
    "varargs": (("varargs",), "guest_varargs_conformance"),
    "arguments": (
        ("format_parse", "varargs", "format_args"),
        "guest_format_args_conformance",
    ),
    "scalar": (
        ("format", "format_parse", "format_scalar"),
        "guest_format_scalar_conformance",
    ),
    "memory": (
        ("format", "format_parse", "format_memory"),
        "guest_format_memory_conformance",
    ),
    "hex-float": (
        ("format", "format_parse", "format_float"),
        "guest_format_float_conformance",
    ),
    "exact-decimal": (
        ("format_decimal_exact",),
        "guest_decimal_exact_conformance",
    ),
    "decimal": (
        (
            "format",
            "format_parse",
            "format_decimal_exact",
            "format_float_decimal",
        ),
        "guest_format_decimal_conformance",
    ),
}


def run_command(command: tuple[str, ...]) -> sp.CompletedProcess[str]:
    """Run pinned Clang or one deterministic native formatting harness.

    Returns:
        Completed process with exit code and captured diagnostics.

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
@pytest.mark.parametrize("suite_name", tuple(FORMAT_SUITES))
@pytest.mark.parametrize(
    "sanitizer_flags",
    [(), SANITIZERS],
    ids=["strict", "asan-ubsan"],
)
def test_guest_format_conformance_on_linux(
    tmp_path: Path,
    suite_name: str,
    sanitizer_flags: tuple[str, ...],
) -> None:
    """Verify every freestanding formatting family and its error cases."""
    sources, harness = FORMAT_SUITES[suite_name]
    executable = tmp_path / f"guest-format-{suite_name}"
    compiled = run_command((
        str(CLANG),
        *WARNINGS,
        *sanitizer_flags,
        *(str(RUNTIME / f"domain/{name}.c") for name in sources),
        str(HARNESS_DIR / f"{harness}.c"),
        "-o",
        str(executable),
    ))
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    executed = run_command((str(executable),))
    assert executed.returncode == 0, executed.stdout + executed.stderr
