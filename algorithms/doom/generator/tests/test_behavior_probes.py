# File:
#   - test_behavior_probes.py
# Path:
#   - algorithms/doom/generator/tests/test_behavior_probes.py
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
#   - Synthetic tests for DOOM behavior probe programs.
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

"""Synthetic tests for DOOM behavior probe programs."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from algorithms.diff.probe_exec import run_probe_program
from algorithms.doom.generator.behavior_probes import (
    fixed_point_identity_program,
)
from algorithms.doom.generator.behavior_probes import pinned_probe_context
from algorithms.doom.generator.doom import build_behavior_programs

_WINDOWS_OS_NAME = "nt"
_EXPECTED_COMMANDS = 4


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _require_pinned_windows_llvm(repository_root: Path) -> None:
    context = pinned_probe_context(repository_root, repository_root)
    tools = tuple(path for _, path in context.tools)
    if os.name != _WINDOWS_OS_NAME or not all(path.is_file() for path in tools):
        pytest.skip("pinned Windows LLVM probe toolchain is unavailable")


def _write_fixed_tree(root: Path, *, alternate: bool) -> None:
    code = root / "linuxdoom-1.10"
    code.mkdir(parents=True)
    header_parts = (
        "typedef int fixed_t;\n",
        "fixed_t FixedMul(fixed_t a, fixed_t b);\n",
        "fixed_t FixedDiv(fixed_t a, fixed_t b);\n",
    )
    _ = (code / "m_fixed.h").write_text(
        "".join(header_parts),
        encoding="utf-8",
    )
    if alternate:
        implementation_parts = (
            '#include "m_fixed.h"\n',
            "fixed_t FixedMul(fixed_t a, fixed_t b) {\n",
            "    long long product = (long long)a * (long long)b;\n",
            "    return (fixed_t)(product >> 16);\n",
            "}\n",
            "fixed_t FixedDiv(fixed_t a, fixed_t b) {\n",
            "    long long numerator = (long long)a << 16;\n",
            "    return (fixed_t)(numerator / b);\n",
            "}\n",
        )
        implementation = "".join(implementation_parts)
    else:
        implementation = (
            '#include "m_fixed.h"\n'
            "fixed_t FixedMul(fixed_t a, fixed_t b) {\n"
            "    return (fixed_t)(((long long)a * b) >> 16);\n"
            "}\n"
            "fixed_t FixedDiv(fixed_t a, fixed_t b) {\n"
            "    return (fixed_t)(((long long)a << 16) / b);\n"
            "}\n"
        )
    _ = (code / "m_fixed.c").write_text(implementation, encoding="utf-8")


def test_domain_module_exposes_behavior_programs() -> None:
    """Keep the thin recipe pointed at one DOOM domain facade."""
    programs = build_behavior_programs()
    _expect(
        len(programs.identity) == 1, "domain facade lost its identity probe"
    )
    _expect(
        not programs.compatibility, "unexpected compatibility probe appeared"
    )
    _expect(not programs.bugs, "unvalidated bug probe appeared")


def test_fixed_point_probe_is_portable_program_shape() -> None:
    """Keep DOOM probe construction declarative and source-path structured."""
    program = fixed_point_identity_program()
    _expect(
        len(program.commands) == _EXPECTED_COMMANDS,
        "fixed-point probe command count changed",
    )
    run = program.commands[-1]
    _expect(
        run.expected_exit_code is None, "runtime result is not observational"
    )
    _expect(run.digest_exit_code, "runtime exit code is not behavior evidence")
    _expect(not run.digest_stdout, "fixed-point probe unexpectedly uses stdout")


def test_fixed_point_probe_matches_semantically_equivalent_variants(
    tmp_path: Path,
) -> None:
    """Observe equal behavior across different fixed-point implementations."""
    repository_root = _repository_root()
    _require_pinned_windows_llvm(repository_root)
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_fixed_tree(first, alternate=False)
    _write_fixed_tree(second, alternate=True)
    program = fixed_point_identity_program()

    first_transcript = run_probe_program(
        program,
        pinned_probe_context(first, repository_root),
    )
    second_transcript = run_probe_program(
        program,
        pinned_probe_context(second, repository_root),
    )

    _expect(
        first_transcript.digest == second_transcript.digest,
        "equivalent fixed-point behavior produced different transcripts",
    )
