# File:
#   - behavior_probes.py
# Path:
#   - algorithms/doom/generator/behavior_probes.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
#
# Boundary-Contract:
# - Owns:
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - DOOM-specific portable behavior probe programs.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""DOOM-specific portable behavior probe programs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from algorithms.diff.behavior_programs import BehaviorPrograms
from algorithms.diff.probe_exec import PathArgument
from algorithms.diff.probe_exec import ProbeCommand
from algorithms.diff.probe_exec import ProbeProgram
from algorithms.diff.probe_exec import ProbeRoot
from algorithms.diff.probe_exec import ProbeRunContext
from algorithms.diff.probe_exec import RootedExecutable
from algorithms.diff.probe_exec import ToolExecutable

if TYPE_CHECKING:
    from pathlib import Path

    from algorithms.diff.probe_exec import ProbeArgument

LLVM_VERSION = "22.1.8"
PROBE_PROFILE_ID = "windows-x86_64-clang22-v1"

_CLANG_TOOL = "clang"
_LINK_TOOL = "lld-link"
_CODE_ROOT = "linuxdoom-1.10"
_ASSET_ROOT = "algorithms/doom/generator/probe_assets/fixed_point"
_SHIM_ROOT = f"{_ASSET_ROOT}/shim"
_PROBE_SOURCE = f"{_ASSET_ROOT}/probe.c"
_FIXED_SOURCE = f"{_CODE_ROOT}/m_fixed.c"
_FIXED_INCLUDE = _CODE_ROOT
_PROBE_OBJECT = "fixed-probe.obj"
_FIXED_OBJECT = "m_fixed.obj"
_PROBE_EXECUTABLE = "fixed-probe.exe"
_TARGET = "x86_64-pc-windows-msvc"
_COMPILE_TIMEOUT_MS = 30_000
_LINK_TIMEOUT_MS = 10_000
_RUN_TIMEOUT_MS = 2_000


def _compile_arguments(
    source: PathArgument,
    output: str,
) -> tuple[ProbeArgument, ...]:
    return (
        f"--target={_TARGET}",
        "-std=gnu11",
        "-ffreestanding",
        "-nostdinc",
        "-fms-extensions",
        "-O2",
        "-I",
        PathArgument(ProbeRoot.REPOSITORY, _SHIM_ROOT),
        "-I",
        PathArgument(ProbeRoot.SOURCE, _FIXED_INCLUDE),
        "-c",
        source,
        "-o",
        PathArgument(ProbeRoot.SCRATCH, output),
    )


def fixed_point_identity_program() -> ProbeProgram:
    """Build the first executable Linux DOOM lineage behavior probe.

    The probe compiles the candidate's real `m_fixed.c` with a repository-owned
    freestanding harness, links a no-CRT PE with a private entry point, executes
    it, and digests only the process exit code. The user source remains
    read-only
    because generic probe execution supplies an isolated source mirror.

    Returns:
        Windows x86-64 LLVM 22 behavior program for fixed-point arithmetic.

    """
    compile_harness = ProbeCommand(
        executable=ToolExecutable(_CLANG_TOOL),
        arguments=_compile_arguments(
            PathArgument(ProbeRoot.REPOSITORY, _PROBE_SOURCE),
            _PROBE_OBJECT,
        ),
        timeout_ms=_COMPILE_TIMEOUT_MS,
    )
    compile_fixed = ProbeCommand(
        executable=ToolExecutable(_CLANG_TOOL),
        arguments=_compile_arguments(
            PathArgument(ProbeRoot.SOURCE, _FIXED_SOURCE),
            _FIXED_OBJECT,
        ),
        timeout_ms=_COMPILE_TIMEOUT_MS,
    )
    link = ProbeCommand(
        executable=ToolExecutable(_LINK_TOOL),
        arguments=(
            "/nodefaultlib",
            "/subsystem:console",
            "/entry:probe_entry",
            "/machine:x64",
            "/opt:ref",
            PathArgument(ProbeRoot.SCRATCH, _PROBE_OBJECT),
            PathArgument(ProbeRoot.SCRATCH, _FIXED_OBJECT),
            f"/out:{_PROBE_EXECUTABLE}",
        ),
        timeout_ms=_LINK_TIMEOUT_MS,
    )
    run = ProbeCommand(
        executable=RootedExecutable(ProbeRoot.SCRATCH, _PROBE_EXECUTABLE),
        expected_exit_code=None,
        timeout_ms=_RUN_TIMEOUT_MS,
        max_stdout_bytes=0,
        max_stderr_bytes=0,
        digest_exit_code=True,
    )
    return ProbeProgram(
        probe_id=f"{PROBE_PROFILE_ID}:fixed-point-arithmetic",
        commands=(compile_harness, compile_fixed, link, run),
    )


def behavior_programs() -> BehaviorPrograms:
    """Return the currently implemented DOOM behavior program set.

    Returns:
        One stable fixed-point identity probe. Bug/compatibility probes are
        added only when their executable harnesses are independently validated.

    """
    return BehaviorPrograms(
        identity=(fixed_point_identity_program(),),
        compatibility=(),
        bugs=(),
    )


def pinned_probe_context(
    source_root: Path, repository_root: Path
) -> ProbeRunContext:
    """Resolve the repository-pinned Windows LLVM tools for DOOM probes.

    Returns:
        Generic probe context with Clang and lld-link logical tool bindings.

    """
    llvm_bin = repository_root / ".dependencies" / "llvm" / LLVM_VERSION / "bin"
    return ProbeRunContext(
        source_root=source_root,
        repository_root=repository_root,
        tools=(
            (_CLANG_TOOL, llvm_bin / "clang.exe"),
            (_LINK_TOOL, llvm_bin / "lld-link.exe"),
        ),
    )
