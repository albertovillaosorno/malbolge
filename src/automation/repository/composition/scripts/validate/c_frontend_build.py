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
#   - Reproducible platform-native build of the normalized C frontend.
# - Must-Not:
#   - Download LLVM, edit extracted packages, or use ambient LLVM/C++ compilers.
# - Allows:
#   - Inputs: validated LLVM 22.1.8 roots and platform-native build tools.
#   - Outputs: ignored native build state and one canonical frontend executable.
#   - Side effects: CMake/Ninja compilation under repository runtime roots only.
# - Split-When:
#   - Another frontend host platform requires an independent build protocol.
# - Merge-When:
#   - Repository bootstrap owns this exact native frontend lifecycle.
# - Summary:
#   - Build and verify the exact Clang C frontend adapter.
# - Description:
#   - Reuses reviewed LLVM identity and platform-native build boundaries.
# - Usage:
#   - Run as `python -m scripts.validate.c_frontend_build`.
# - Defaults:
#   - Missing prerequisites, build failure, or version drift fails closed.
#

"""Build and verify the native normalized C frontend executable."""

from __future__ import annotations

import os
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path
from stat import S_ISREG
from typing import Final, Never, TextIO

if __package__ in {None, ""}:
    composition_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(composition_root))

from scripts.repository_root import repository_root
from scripts.validate import c_frontend_build_linux, tidy_build, tidy_toolchain

ROOT: Final = repository_root(Path(__file__))
SOURCE_ROOT: Final = ROOT / "src" / "compiler" / "c-frontend" / "composition"
BUILD_ROOT: Final = (
    ROOT / ".cache" / "compiler-c-frontend" / tidy_toolchain.LLVM_VERSION
)
OUTPUT_ROOT: Final = (
    ROOT / ".dependencies" / "compiler-c-frontend" / tidy_toolchain.LLVM_VERSION
)
HOST_PLATFORM_ID: Final = tidy_toolchain.host_platform_id()
EXECUTABLE_NAME: Final = (
    "malbolge-c-frontend.exe"
    if HOST_PLATFORM_ID == tidy_toolchain.WINDOWS_PLATFORM
    else "malbolge-c-frontend"
)
EXECUTABLE: Final = OUTPUT_ROOT / "bin" / EXECUTABLE_NAME


class FrontendBuildError(RuntimeError):
    """Pinned C frontend build prerequisites or outputs are invalid."""


def _fail(message: str) -> Never:
    raise FrontendBuildError(message)


def _native_path_status(receipt: object, context: str) -> bool:
    """Admit only exact native filesystem path decisions.

    Returns:
        The admitted boolean status.

    """
    if type(receipt) is not bool:
        _fail(f"{context} requires native path status")
    return receipt


def _batch_path(path: Path) -> str:
    return str(path.resolve()).replace("/", "\\")


def _run(
    command: list[str],
    *,
    capture: bool = False,
) -> sp.CompletedProcess[str]:
    try:
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            command.copy(),
            cwd=ROOT,
            check=False,
            capture_output=capture,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        native_types = {
            OSError,
            FileNotFoundError,
            PermissionError,
            ValueError,
            TypeError,
            RuntimeError,
        }
        detail = str(error) if type(error) in native_types else type(error).__name__
        raise FrontendBuildError(
            f"failed to execute {command[0]}: {detail}"
        ) from error
    if (
        type(completed) is not sp.CompletedProcess
        or type(completed.args) is not list
        or len(completed.args) != len(command)
        or any(type(argument) is not str for argument in completed.args)
        or completed.args != command
        or type(completed.returncode) is not int
        or (
            capture
            and (type(completed.stdout) is not str or type(completed.stderr) is not str)
        )
        or (not capture and (completed.stdout is not None or completed.stderr is not None))
    ):
        _fail("C frontend build returned malformed process receipt")
    return completed


def _require_physical_directory(path: Path, label: str) -> None:
    """Require unlinked directory ancestry for frontend build destinations."""
    for component in (path, *path.parents):
        if _native_path_status(
            component.is_symlink(), f"{label} redirect"
        ) or _native_path_status(component.is_junction(), f"{label} redirect"):
            _fail(f"{label} directory must not redirect: {component}")
        exists = _native_path_status(component.exists(), f"{label} existence")
        directory = _native_path_status(component.is_dir(), f"{label} directory")
        if exists and not directory:
            _fail(f"{label} path must be a directory: {component}")


def _require_private_build_script(path: Path) -> None:
    symbolic = _native_path_status(
        path.is_symlink(), "build cache script redirect"
    )
    junction = _native_path_status(
        path.is_junction(), "build cache script redirect"
    )
    if symbolic or junction:
        _fail(f"build cache script must not redirect: {path}")
    if _native_path_status(path.exists(), "build cache script existence"):
        status = path.lstat()
        if (
            type(status) is not os.stat_result
            or not S_ISREG(status.st_mode)
            or status.st_nlink != 1
        ):
            _fail(f"build cache script must be a private regular file: {path}")
        if not _native_path_status(
            path.is_file(), "build cache script regular file"
        ):
            _fail(f"build cache script must be a private regular file: {path}")


def _write_build_script(
    tools: tidy_build.VisualStudioTools,
    identity: tidy_toolchain.ToolchainIdentity,
) -> Path:
    _require_physical_directory(BUILD_ROOT, "build cache")
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    build_dir = BUILD_ROOT / "build"
    _require_physical_directory(build_dir, "build cache")
    build_dir.mkdir(parents=True, exist_ok=True)
    _require_physical_directory(build_dir, "build cache")
    script = BUILD_ROOT / "build.cmd"
    _require_private_build_script(script)
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
    content = "\r\n".join(lines) + "\r\n"
    _require_physical_directory(BUILD_ROOT, "build cache")
    _require_private_build_script(script)
    written = script.write_text(content, encoding="utf-8", newline="")
    if type(written) is not int or written != len(content):
        _fail("C frontend build script has invalid write count")
    return script


def _build_windows(identity: tidy_toolchain.ToolchainIdentity) -> None:
    output = OUTPUT_ROOT
    _require_physical_directory(output, "frontend output")
    output.mkdir(parents=True, exist_ok=True)
    _require_physical_directory(output, "frontend output")
    tools = tidy_build.visual_studio_tools()
    script = _write_build_script(tools, identity)
    windows = Path(os.environ.get("SYSTEMROOT", "C:/Windows"))
    command_shell = windows / "System32" / "cmd.exe"
    _require_physical_directory(BUILD_ROOT, "build cache")
    _require_physical_directory(output, "frontend output")
    completed = _run([str(command_shell), "/d", "/c", str(script.resolve())])
    if completed.returncode != 0:
        _fail(f"C frontend build failed with status {completed.returncode}")


def _require_private_executable(path: Path) -> None:
    """Admit an unlinked, native regular executable before version checking."""
    if not _native_path_status(path.is_file(), "frontend executable file"):
        _fail(f"C frontend executable missing: {path}")
    symbolic = _native_path_status(
        path.is_symlink(), "frontend executable redirect"
    )
    junction = _native_path_status(
        path.is_junction(), "frontend executable redirect"
    )
    if symbolic or junction:
        _fail(f"C frontend executable must be a private regular file: {path}")
    status = path.lstat()
    if (
        type(status) is not os.stat_result
        or not S_ISREG(status.st_mode)
        or status.st_nlink != 1
    ):
        _fail(f"C frontend executable must be a private regular file: {path}")


def build() -> None:
    """Build and verify the exact native frontend executable."""
    identity = tidy_toolchain.load_identity(platform_id=HOST_PLATFORM_ID)
    tidy_toolchain.validate_installation(identity)
    if identity.platform_id == tidy_toolchain.LINUX_PLATFORM:
        c_frontend_build_linux.build(identity, output_root=OUTPUT_ROOT)
    elif identity.platform_id == tidy_toolchain.WINDOWS_PLATFORM:
        _build_windows(identity)
    else:
        _fail(f"unsupported C frontend build platform: {identity.platform_id}")
    _require_physical_directory(EXECUTABLE.parent, "frontend output")
    _require_private_executable(EXECUTABLE)
    version = _run([str(EXECUTABLE), "--version"], capture=True)
    expected = f"malbolge-c-frontend 1 LLVM {identity.llvm_version}"
    if version.returncode != 0 or version.stdout.strip() != expected:
        _fail("C frontend executable version identity is invalid")


def _write_cli_record(stream: TextIO, message: str) -> bool:
    """Return whether exact native CLI text write and flush both completed."""
    try:
        written = stream.write(message)
        if type(written) is not int or written != len(message):
            return False
        return stream.flush() is None
    except (
        AttributeError,
        IndexError,
        OSError,
        OverflowError,
        RuntimeError,
        TypeError,
        ValueError,
    ):
        return False


def main() -> int:
    """Build the frontend and return a process status.

    Returns:
        Zero when the exact frontend output is ready and CLI output delivered.

    """
    try:
        build()
        if not _write_cli_record(sys.stdout, f"C frontend ready: {EXECUTABLE}\n"):
            _fail("C frontend CLI output write or flush failed")
    except (
        FrontendBuildError,
        c_frontend_build_linux.LinuxFrontendBuildError,
        tidy_build.BuildError,
        tidy_toolchain.ToolchainError,
    ) as error:
        detail = (
            str(error)
            if type(error)
            in {
                FrontendBuildError,
                c_frontend_build_linux.LinuxFrontendBuildError,
                tidy_build.BuildError,
                tidy_toolchain.ToolchainError,
            }
            else type(error).__name__
        )
        _ = _write_cli_record(sys.stderr, f"error: {detail}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
