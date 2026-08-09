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
#   - Reproducible Windows build of the pinned normalized C frontend executable.
# - Must-Not:
#   - Download LLVM, edit extracted packages, or use ambient LLVM/C++ compilers.
# - Allows:
#   - Inputs: validated LLVM 22.1.8 roots and local Visual Studio build tools.
#   - Outputs: ignored native build state and one canonical frontend executable.
#   - Side effects: CMake/Ninja compilation under repository runtime roots only.
# - Split-When:
#   - Another frontend host platform requires an independent build protocol.
# - Merge-When:
#   - Repository bootstrap owns this exact native frontend lifecycle.
# - Summary:
#   - Build and verify the exact Clang C frontend adapter.
# - Description:
#   - Reuses reviewed LLVM and Visual Studio identity from native analysis.
# - Usage:
#   - Run as `python -m scripts.validate.c_frontend_build`.
# - Defaults:
#   - Missing prerequisites, build failure, or version drift fails closed.
#

"""Build and verify the native normalized C frontend executable."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import Final
from typing import Never

if __package__ in {None, ""}:
    composition_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(composition_root))

from scripts.repository_root import repository_root
from scripts.validate import tidy_build
from scripts.validate import tidy_toolchain

ROOT: Final = repository_root(Path(__file__))
SOURCE_ROOT: Final = ROOT / "src" / "compiler" / "c-frontend" / "composition"
BUILD_ROOT: Final = (
    ROOT / ".cache" / "compiler-c-frontend" / tidy_toolchain.LLVM_VERSION
)
OUTPUT_ROOT: Final = (
    ROOT / ".dependencies" / "compiler-c-frontend" / tidy_toolchain.LLVM_VERSION
)
EXECUTABLE: Final = OUTPUT_ROOT / "bin" / "malbolge-c-frontend.exe"


class FrontendBuildError(RuntimeError):
    """Pinned C frontend build prerequisites or outputs are invalid."""


def _fail(message: str) -> Never:
    raise FrontendBuildError(message)


def _batch_path(path: Path) -> str:
    return str(path.resolve()).replace("/", "\\")


def _run(
    command: list[str],
    *,
    capture: bool = False,
) -> sp.CompletedProcess[str]:
    try:
        return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            command,
            cwd=ROOT,
            check=False,
            capture_output=capture,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
    except OSError as error:
        _fail(f"failed to execute {command[0]}: {error}")


def _write_build_script(
    tools: tidy_build.VisualStudioTools,
    identity: tidy_toolchain.ToolchainIdentity,
) -> Path:
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    build_dir = BUILD_ROOT / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    script = BUILD_ROOT / "build.cmd"
    configure = (
        f'"{_batch_path(tools.cmake)}" '
        f'-S "{_batch_path(SOURCE_ROOT)}" '
        f'-B "{_batch_path(build_dir)}" -G Ninja '
        f'-DCMAKE_MAKE_PROGRAM="{_batch_path(tools.ninja)}" '
        f'-DCMAKE_CXX_COMPILER="{_batch_path(identity.clang_cl)}" '
        "-DCMAKE_BUILD_TYPE=Release "
        f'-DMALBOLGE_LLVM_ROOT="{_batch_path(identity.development_root)}" '
        f'-DMALBOLGE_DIA_GUIDS="{_batch_path(tools.dia_guids)}" '
        f'-DMALBOLGE_OUTPUT_DIR="{_batch_path(OUTPUT_ROOT)}"'
    )
    compile_command = (
        f'"{_batch_path(tools.cmake)}" '
        f'--build "{_batch_path(build_dir)}" --config Release'
    )
    lines = [
        "@echo off",
        "setlocal",
        (
            r'set "PATH=%SystemRoot%\System32;%SystemRoot%;'
            r'%SystemRoot%\System32\Wbem"'
        ),
        "set INCLUDE=",
        "set LIB=",
        "set LIBPATH=",
        f'call "{_batch_path(tools.vcvars64)}" >nul',
        "if errorlevel 1 exit /b %errorlevel%",
        configure,
        "if errorlevel 1 exit /b %errorlevel%",
        compile_command,
        "exit /b %errorlevel%",
    ]
    _ = script.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    return script


def build() -> None:
    """Build and verify the exact native frontend executable."""
    identity = tidy_toolchain.load_identity()
    tidy_toolchain.validate_installation(identity)
    tools = tidy_build.visual_studio_tools()
    script = _write_build_script(tools, identity)
    windows = Path(os.environ.get("SYSTEMROOT", "C:/Windows"))
    command_shell = windows / "System32" / "cmd.exe"
    completed = _run([str(command_shell), "/d", "/c", str(script.resolve())])
    if completed.returncode != 0:
        _fail(f"C frontend build failed with status {completed.returncode}")
    if not EXECUTABLE.is_file():
        _fail(f"C frontend executable missing: {EXECUTABLE}")
    version = _run([str(EXECUTABLE), "--version"], capture=True)
    expected = f"malbolge-c-frontend 1 LLVM {identity.llvm_version}"
    if version.returncode != 0 or version.stdout.strip() != expected:
        _fail("C frontend executable version identity is invalid")


def main() -> int:
    """Build the frontend and return a process status.

    Returns:
        Zero when the exact frontend output is ready, otherwise one.

    """
    try:
        build()
    except (
        FrontendBuildError,
        tidy_build.BuildError,
        tidy_toolchain.ToolchainError,
    ) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    _ = sys.stdout.write(f"C frontend ready: {EXECUTABLE}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
