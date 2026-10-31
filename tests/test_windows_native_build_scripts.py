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
#   - Windows native C frontend and clang-tidy build script admission tests.
# - Must-Not:
#   - Require Windows, build LLVM, or install native developer toolchains.
# - Allows:
#   - Inputs: pinned identities, temporary paths, and faulty file writers.
#   - Outputs: exact script-write rejection or complete script bytes.
#   - Side effects: temporary build scripts only.
# - Split-When:
#   - Another platform needs different executable build-script semantics.
# - Merge-When:
#   - The frontend or tidy build suites own identical script admission.
# - Summary:
#   - Fail closed on truncated Windows build scripts before command launch.
# - Description:
#   - Cross-platform tests for complete generated CMake/Ninja script writes.
# - Usage:
#   - Run with the repository Python validation suite.
# - Defaults:
#   - A malformed script write acknowledgement cannot be treated as success.
#

"""Regression tests for Windows native build-script publication."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from scripts.validate import c_frontend_build
from scripts.validate import tidy_build
from scripts.validate import tidy_toolchain

FRONTEND_KIND = "frontend"
TIDY_KIND = "tidy"
TRUNCATED_SCRIPT = "@"
NINJA_FLAG = "-G Ninja"
VCVARS_COMMAND = "vcvars64.bat"
CRLF = b"\r\n"
DOUBLE_CRLF = b"\r\r\n"
BARE_LF = b"\n"

type ScriptBuilder = Callable[
    [tidy_build.VisualStudioTools, tidy_toolchain.ToolchainIdentity], Path
]


def _windows_tools(tmp_path: Path) -> tidy_build.VisualStudioTools:
    """Provide named Windows build tools without executing any of them.

    Returns:
        Build tool paths suitable for deterministic script generation.

    """
    return tidy_build.VisualStudioTools(
        cmake=tmp_path / "cmake.exe",
        dia_guids=tmp_path / "diaguids.lib",
        installation=tmp_path / "vs",
        ninja=tmp_path / "ninja.exe",
        vcvars64=tmp_path / "vcvars64.bat",
    )


def _script_builder(
    kind: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[
    ScriptBuilder,
    type[Exception],
    Path,
]:
    """Select the guarded author and its dedicated exception type.

    Returns:
        Script creator, failure type, and generated script path.

    """
    module = c_frontend_build if kind == FRONTEND_KIND else tidy_build
    error_type = (
        c_frontend_build.FrontendBuildError
        if kind == FRONTEND_KIND
        else tidy_build.BuildError
    )
    directory = tmp_path / kind
    monkeypatch.setattr(module, "BUILD_ROOT", directory)
    builder = cast(
        "ScriptBuilder",
        vars(module)["_write_build_script"],
    )
    return builder, error_type, directory / "build.cmd"


@pytest.mark.parametrize("kind", [FRONTEND_KIND, TIDY_KIND])
@pytest.mark.parametrize("bad_count", [None, True, -1, 1, 1_000_000])
def test_windows_builder_rejects_incomplete_script_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    kind: str,
    bad_count: object,
) -> None:
    """Reject a script whose host writer did not acknowledge all characters."""
    builder, error_type, script = _script_builder(kind, monkeypatch, tmp_path)
    tools = _windows_tools(tmp_path)
    identity = tidy_toolchain.load_identity(
        platform_id=tidy_toolchain.WINDOWS_PLATFORM
    )
    original_write = Path.write_text

    def faulty_write(
        path: Path,
        text: str,
        encoding: str | None = None,
        *,
        newline: str | None = None,
    ) -> int:
        if path != script:
            return original_write(
                path, text, encoding=encoding, newline=newline
            )
        _ = original_write(path, text[:1], encoding=encoding, newline=newline)
        return cast("int", bad_count)

    monkeypatch.setattr(Path, "write_text", faulty_write)
    with pytest.raises(error_type, match="write count"):
        _ = builder(tools, identity)
    assert script.read_text(encoding="utf-8") == TRUNCATED_SCRIPT


@pytest.mark.parametrize("kind", [FRONTEND_KIND, TIDY_KIND])
def test_windows_builder_accepts_exact_complete_script(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    kind: str,
) -> None:
    """A complete native build script retains all expected batch commands."""
    builder, _, script = _script_builder(kind, monkeypatch, tmp_path)
    tools = _windows_tools(tmp_path)
    identity = tidy_toolchain.load_identity(
        platform_id=tidy_toolchain.WINDOWS_PLATFORM
    )
    assert builder(tools, identity) == script
    content = script.read_text(encoding="utf-8")
    assert content.startswith("@echo off\nsetlocal\n")
    assert NINJA_FLAG in content
    assert VCVARS_COMMAND in content
    assert content.endswith("exit /b %errorlevel%\n")
    raw = script.read_bytes()
    assert CRLF in raw
    assert DOUBLE_CRLF not in raw
    assert BARE_LF not in raw.replace(CRLF, b"")
