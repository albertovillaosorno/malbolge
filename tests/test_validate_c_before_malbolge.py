# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Regression evidence for the deterministic pre-Malbolge C validator.
# - Must-Not:
#   - Treat expensive-but-supported C constructs as compatibility failures.
# - Allows:
#   - Inputs: temporary explicit C translation units and repository-pinned
#     Clang.
#   - Outputs: accepted/rejected preflight process evidence.
#   - Side effects: temporary files and pinned Clang subprocess execution.
# - Split-When:
#   - Full lowerability fixtures gain a separate end-to-end compiler suite.
# - Merge-When:
#   - The tools/tidy lowerability suite owns these exact preflight cases.
# - Summary:
#   - Locks closed includes, reproducibility checks, and non-overrejection.
# - Description:
#   - Verifies deterministic hard failures without banning ABI-supported
#     features.
# - Usage:
#   - Executed by pytest.
# - Defaults:
#   - Missing pinned Clang skips executable preflight evidence.
#

"""Deterministic pre-Malbolge C validation regressions."""

from __future__ import annotations

from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "src/automation/repository/composition/scripts/validate"
    / "validate_c_before_malbolge.py"
)
PINNED_CLANG = ROOT / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
CLEAN_MESSAGE = "pre-Malbolge Clang preflight clean"
PRE_DIAGNOSTIC = "MALBOLGE-PRE-001"
DATE_DIAGNOSTIC = "date or time macro"
HOST_HEADER = "unistd.h"
NOT_FOUND = "file not found"


def _run(source: Path) -> sp.CompletedProcess[str]:
    if not PINNED_CLANG.is_file():
        pytest.skip("repository-pinned Clang is unavailable")
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, str(SCRIPT), "--preflight-only", str(source)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )


def test_preflight_accepts_supported_difficult_c(tmp_path: Path) -> None:
    """VLA, recursion, and function pointers are not rejected by difficulty."""
    source = tmp_path / "supported.c"
    _ = source.write_text(
        """
static int recursive(int value) {
    return value == 0 ? 0 : 1 + recursive(value - 1);
}
static int apply(int (*function)(int), int value) {
    int scratch[value > 0 ? value : 1];
    scratch[0] = function(value);
    return scratch[0];
}
int entry(int value) { return apply(recursive, value); }
""".lstrip(),
        encoding="utf-8",
    )
    completed = _run(source)
    assert completed.returncode == 0, completed.stderr
    assert CLEAN_MESSAGE in completed.stdout


def test_preflight_rejects_nondeterministic_date_macro(tmp_path: Path) -> None:
    """Compilation-time clock macros cannot enter deterministic guest source."""
    source = tmp_path / "date_macro.c"
    _ = source.write_text(
        "const char *build_date = __DATE__;\n",
        encoding="utf-8",
    )
    completed = _run(source)
    assert completed.returncode == 1
    assert PRE_DIAGNOSTIC in completed.stderr
    assert DATE_DIAGNOSTIC in completed.stderr


def test_preflight_rejects_ambient_host_header(tmp_path: Path) -> None:
    """The guest include universe cannot fall back to ambient host headers."""
    source = tmp_path / "host_header.c"
    _ = source.write_text(
        "#include <unistd.h>\nint entry(void) { return 0; }\n",
        encoding="utf-8",
    )
    completed = _run(source)
    assert completed.returncode == 1
    assert PRE_DIAGNOSTIC in completed.stderr
    assert HOST_HEADER in completed.stderr
    assert NOT_FOUND in completed.stderr
