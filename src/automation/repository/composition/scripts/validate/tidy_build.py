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
#   - Reproducible Windows construction of the pinned Malbolge clang-tidy host.
# - Must-Not:
#   - Download LLVM, mutate extracted packages, or use an ambient C++ compiler.
# - Allows:
#   - Inputs: reviewed LLVM roots and installed Visual Studio Build Tools.
#   - Outputs: ignored build files plus canonical ignored native binaries.
#   - Side effects: CMake/Ninja compilation inside repository runtime roots.
# - Split-When:
#   - Split when a second host platform needs a distinct native build protocol.
# - Merge-When:
#   - Merge when project bootstrap owns this pinned native build lifecycle.
# - Summary:
#   - Build and verify the Windows clang-tidy plugin host.
# - Description:
#   - Relinks LLVM 22.1.8 clang-tidy with one registry bridge for Windows DLLs.
# - Usage:
#   - Run as `python -m scripts.validate.tidy_build` from the repository.
# - Defaults:
#   - Missing build prerequisites or unverifiable outputs fail closed.
#

"""Build the Windows Malbolge clang-tidy host and plugin deterministically."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import Final
from typing import Never

if __package__ in {None, ""}:
    composition_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(composition_root))

from scripts.repository_root import repository_root
from scripts.validate import tidy_toolchain

ROOT: Final = repository_root(Path(__file__))
SOURCE_ROOT: Final = ROOT / "tools" / "tidy" / "composition"
BUILD_ROOT: Final = ROOT / ".cache" / "tools-tidy" / tidy_toolchain.LLVM_VERSION
VC_COMPONENT: Final = "Microsoft.VisualStudio.Component.VC.Tools.x86.x64"


class BuildError(RuntimeError):
    """Pinned clang-tidy build prerequisites or outputs are invalid."""


@dataclass(frozen=True, slots=True)
class VisualStudioTools:
    """Resolved Visual Studio native build tools used by the Windows build."""

    cmake: Path
    dia_guids: Path
    installation: Path
    ninja: Path
    vcvars64: Path


def _fail(message: str) -> Never:
    raise BuildError(message)


def _require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        _fail(f"{label} not found: {path}")
    return path


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


def _checked_output(command: list[str], label: str) -> str:
    completed = _run(command, capture=True)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        _fail(f"{label} failed with status {completed.returncode}: {detail}")
    return completed.stdout + chr(10) + completed.stderr


def _program_files_x86() -> Path:
    value = os.environ.get("PROGRAMFILES(X86)")
    return Path(value) if value else Path("C:/Program Files (x86)")


def visual_studio_tools() -> VisualStudioTools:
    """Resolve one VC-enabled Visual Studio installation using vswhere.

    Returns:
        Paths for the selected Visual Studio and CMake/Ninja tools.

    """
    vswhere = _require_file(
        _program_files_x86()
        / "Microsoft Visual Studio"
        / "Installer"
        / "vswhere.exe",
        "Visual Studio installer locator",
    )
    output = _checked_output(
        [
            str(vswhere),
            "-latest",
            "-products",
            "*",
            "-requires",
            VC_COMPONENT,
            "-property",
            "installationPath",
        ],
        "Visual Studio discovery",
    )
    installation_text = next(
        (line.strip() for line in output.splitlines() if line.strip()),
        "",
    )
    if not installation_text:
        _fail("no Visual Studio installation provides the x64 VC toolchain")
    installation = Path(installation_text)
    cmake_root = (
        installation
        / "Common7"
        / "IDE"
        / "CommonExtensions"
        / "Microsoft"
        / "CMake"
    )
    return VisualStudioTools(
        cmake=_require_file(
            cmake_root / "CMake" / "bin" / "cmake.exe",
            "CMake",
        ),
        dia_guids=_require_file(
            installation / "DIA SDK" / "lib" / "amd64" / "diaguids.lib",
            "x64 DIA GUID library",
        ),
        installation=installation,
        ninja=_require_file(cmake_root / "Ninja" / "ninja.exe", "Ninja"),
        vcvars64=_require_file(
            installation / "VC" / "Auxiliary" / "Build" / "vcvars64.bat",
            "vcvars64",
        ),
    )


def _batch_path(path: Path) -> str:
    return str(path.resolve()).replace("/", "\\")


def _write_build_script(
    tools: VisualStudioTools,
    identity: tidy_toolchain.ToolchainIdentity,
) -> Path:
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    build_dir = BUILD_ROOT / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    script = BUILD_ROOT / "build.cmd"
    configure = (
        f'"{_batch_path(tools.cmake)}" '
        f'-S "{_batch_path(SOURCE_ROOT)}" '
        f'-B "{_batch_path(build_dir)}" '
        "-G Ninja "
        f'-DCMAKE_MAKE_PROGRAM="{_batch_path(tools.ninja)}" '
        f'-DCMAKE_CXX_COMPILER="{_batch_path(identity.clang_cl)}" '
        "-DCMAKE_BUILD_TYPE=Release "
        f'-DMALBOLGE_LLVM_ROOT="{_batch_path(identity.development_root)}" '
        f'-DMALBOLGE_DIA_GUIDS="{_batch_path(tools.dia_guids)}" '
        f'-DMALBOLGE_OUTPUT_DIR="{_batch_path(identity.plugin_output_root)}"'
    )
    compile_command = (
        f'"{_batch_path(tools.cmake)}" '
        f'--build "{_batch_path(build_dir)}" --config Release'
    )
    path_line = r'set "PATH=%SystemRoot%\System32;%SystemRoot%;'
    path_line += r'%SystemRoot%\System32\Wbem"'
    lines = [
        "@echo off",
        "setlocal",
        path_line,
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


def build(identity: tidy_toolchain.ToolchainIdentity) -> None:
    """Build the canonical host/plugin outputs from pinned dependencies."""
    tidy_toolchain.validate_installation(identity)
    tools = visual_studio_tools()
    script = _write_build_script(tools, identity)
    windows = Path(os.environ.get("SYSTEMROOT", "C:/Windows"))
    command_shell = _require_file(windows / "System32" / "cmd.exe", "cmd.exe")
    completed = _run(
        [str(command_shell), "/d", "/c", str(script.resolve())]
    )
    if completed.returncode != 0:
        _fail(
            "clang-tidy native build failed with status "
            + str(completed.returncode)
        )


def provision_clang_resources(
    identity: tidy_toolchain.ToolchainIdentity,
) -> None:
    """Copy the pinned Clang builtin headers beside the generated host."""
    resource_version = identity.llvm_version.split(".", maxsplit=1)[0]
    relative = Path("lib") / "clang" / resource_version
    source = identity.runtime_root / relative
    destination = identity.plugin_output_root / relative
    _ = _require_file(source / "include" / "limits.h", "Clang limits header")
    if destination.exists():
        shutil.rmtree(destination)
    _ = shutil.copytree(source, destination)


def verify_outputs(identity: tidy_toolchain.ToolchainIdentity) -> None:
    """Require built host/plugin identity and reviewed plugin registration."""
    host = _require_file(identity.plugin_host, "Malbolge clang-tidy host")
    plugin = _require_file(
        identity.plugin_library,
        "Malbolge clang-tidy plugin",
    )
    version = _checked_output(
        [str(host), "--version"],
        "plugin host version query",
    )
    if f"LLVM version {identity.llvm_version}" not in version:
        _fail(f"plugin host must report LLVM version {identity.llvm_version}")

    exports = _checked_output(
        [str(identity.llvm_readobj), "--coff-exports", str(host)],
        "plugin host export inspection",
    )
    if f"Name: {identity.registry_bridge_export}" not in exports:
        _fail(
            "plugin host does not export the reviewed Windows registry bridge"
        )

    checks = _checked_output(
        [
            str(host),
            f"--load={plugin}",
            "--checks=-*,malbolge-*",
            "--list-checks",
        ],
        "plugin check registration query",
    )
    observed = tuple(
        line.strip()
        for line in checks.splitlines()
        if line.strip().startswith("malbolge-")
    )
    if set(observed) != set(identity.plugin_checks):
        expected = ", ".join(sorted(identity.plugin_checks))
        actual = ", ".join(sorted(observed)) if observed else "none"
        prefix = "plugin registration mismatch: expected "
        _fail(f"{prefix}{expected}; observed {actual}")


def main() -> int:
    """Build and verify canonical clang-tidy plugin outputs.

    Returns:
        Process status for the deterministic native build and verification.

    """
    try:
        identity = tidy_toolchain.load_identity()
        build(identity)
        provision_clang_resources(identity)
        verify_outputs(identity)
    except (BuildError, tidy_toolchain.ToolchainError) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    message = f"clang-tidy plugin ready: {identity.plugin_library}"
    _ = sys.stdout.write(message + chr(10))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
