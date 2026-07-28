# File:
#   - test_behavior_programs.py
# Path:
#   - algorithms/diff/tests/test_behavior_programs.py
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
#   - Synthetic tests for authoring and observing portable behavior programs.
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

"""Synthetic tests for authoring and observing portable behavior programs."""

from __future__ import annotations

import math
from pathlib import Path
import sys
from typing import TYPE_CHECKING

import pytest

from algorithms.diff.behavior import BugState
from algorithms.diff.behavior_programs import BehaviorProgramError
from algorithms.diff.behavior_programs import BehaviorPrograms
from algorithms.diff.behavior_programs import BugProgram
from algorithms.diff.behavior_programs import author_behavior_programs
from algorithms.diff.behavior_programs import evaluate_behavior_programs
from algorithms.diff.behavior_programs import observe_behavior_programs
from algorithms.diff.probe_exec import PathArgument
from algorithms.diff.probe_exec import ProbeCommand
from algorithms.diff.probe_exec import ProbeProgram
from algorithms.diff.probe_exec import ProbeRoot
from algorithms.diff.probe_exec import ProbeRunContext
from algorithms.diff.probe_exec import ToolExecutable

if TYPE_CHECKING:
    from algorithms.diff.behavior_programs import AuthoredBehaviorPrograms

_PYTHON_TOOL = "python"
_READ_BYTES = (
    "import pathlib,sys;"
    "sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes())"
)
_REQUIRE_FILE = (
    "import pathlib,sys;"
    "raise SystemExit(0 if pathlib.Path(sys.argv[1]).is_file() else 9)"
)


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _write(root: Path, name: str, data: bytes) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _ = (root / name).write_bytes(data)


def _context(root: Path, repository_root: Path) -> ProbeRunContext:
    return ProbeRunContext(
        source_root=root,
        repository_root=repository_root,
        tools=((_PYTHON_TOOL, Path(sys.executable)),),
    )


def _read_program(probe_id: str, relative_path: str) -> ProbeProgram:
    return ProbeProgram(
        probe_id=probe_id,
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _READ_BYTES,
                    PathArgument(ProbeRoot.SOURCE, relative_path),
                ),
                digest_stdout=True,
            ),
        ),
    )


def _compatibility_program() -> ProbeProgram:
    return ProbeProgram(
        probe_id="runtime-capability",
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _REQUIRE_FILE,
                    PathArgument(ProbeRoot.SOURCE, "runtime.flag"),
                ),
            ),
        ),
    )


def _programs() -> BehaviorPrograms:
    return BehaviorPrograms(
        identity=(_read_program("identity-stable", "identity.txt"),),
        compatibility=(_compatibility_program(),),
        bugs=(
            BugProgram(
                program=_read_program("historical-bug", "bug-state.txt"),
                correction_id="fix-historical-bug",
            ),
        ),
    )


def _trees(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    for root in (source, oracle):
        _write(root, "identity.txt", b"stable")
        _write(root, "runtime.flag", b"available")
    _write(source, "bug-state.txt", b"present")
    _write(oracle, "bug-state.txt", b"fixed")
    return source, oracle


def _authored(
    tmp_path: Path,
) -> tuple[AuthoredBehaviorPrograms, Path, Path]:
    source, oracle = _trees(tmp_path)
    authored = author_behavior_programs(
        _programs(),
        _context(source, tmp_path),
        _context(oracle, tmp_path),
    )
    return authored, source, oracle


def test_authoring_derives_identity_and_distinct_bug_baselines(
    tmp_path: Path,
) -> None:
    """Generate source identity plus present/fixed bug transcript baselines."""
    authored, _, _ = _authored(tmp_path)
    bug = authored.bugs[0]

    _expect(
        bool(authored.profile.identity[0].expected_digest), "identity is empty"
    )
    _expect(
        bug.present_digest != bug.fixed_digest, "bug baselines are ambiguous"
    )


def test_original_bug_state_routes_correction_to_apply(tmp_path: Path) -> None:
    """Classify a source-like candidate as defect present."""
    authored, source, _ = _authored(tmp_path)
    evidence = evaluate_behavior_programs(
        authored,
        _context(source, tmp_path),
        minimum_similarity=0.80,
    )

    _expect(evidence.admitted, "source behavior was rejected")
    _expect(
        evidence.corrections_to_apply == ("fix-historical-bug",),
        "present bug did not route correction",
    )


def test_oracle_bug_state_routes_correction_to_skip(tmp_path: Path) -> None:
    """Classify an already-corrected candidate as fixed without rejection."""
    authored, _, oracle = _authored(tmp_path)
    evidence = evaluate_behavior_programs(
        authored,
        _context(oracle, tmp_path),
        minimum_similarity=0.80,
    )

    _expect(evidence.admitted, "fixed behavior was rejected")
    _expect(
        evidence.corrections_to_skip == ("fix-historical-bug",),
        "fixed bug did not skip correction",
    )


def test_unknown_bug_transcript_fails_closed(tmp_path: Path) -> None:
    """Classify behavior matching neither source nor oracle as unknown."""
    authored, source, _ = _authored(tmp_path)
    candidate = tmp_path / "candidate-unknown"
    for name in ("identity.txt", "runtime.flag"):
        _write(candidate, name, (source / name).read_bytes())
    _write(candidate, "bug-state.txt", b"third-state")

    observations = observe_behavior_programs(
        authored,
        _context(candidate, tmp_path),
    )
    _expect(observations.bugs[0].state is BugState.UNKNOWN, "bug was guessed")
    evidence = evaluate_behavior_programs(
        authored,
        _context(candidate, tmp_path),
        minimum_similarity=0.80,
    )
    _expect(not evidence.admitted, "unknown bug state was admitted")


def test_failed_compatibility_program_rejects_candidate(tmp_path: Path) -> None:
    """Turn a failed portable precondition program into behavior rejection."""
    authored, source, _ = _authored(tmp_path)
    candidate = tmp_path / "candidate-incompatible"
    _write(candidate, "identity.txt", (source / "identity.txt").read_bytes())
    _write(candidate, "bug-state.txt", (source / "bug-state.txt").read_bytes())

    evidence = evaluate_behavior_programs(
        authored,
        _context(candidate, tmp_path),
        minimum_similarity=0.80,
    )
    _expect(
        not evidence.admitted, "missing compatibility capability was admitted"
    )


def test_changed_identity_program_output_reduces_similarity(
    tmp_path: Path,
) -> None:
    """Derive identity mismatch from executable probe output."""
    authored, source, _ = _authored(tmp_path)
    candidate = tmp_path / "candidate-different"
    _write(candidate, "identity.txt", b"different")
    _write(candidate, "runtime.flag", b"available")
    _write(candidate, "bug-state.txt", (source / "bug-state.txt").read_bytes())

    evidence = evaluate_behavior_programs(
        authored,
        _context(candidate, tmp_path),
        minimum_similarity=0.80,
    )
    _expect(not evidence.admitted, "changed identity behavior was admitted")
    _expect(
        math.isclose(evidence.similarity, 0.0),
        "identity mismatch score changed",
    )


def test_bug_probe_must_distinguish_source_from_oracle(tmp_path: Path) -> None:
    """Reject a bug program that cannot tell defect presence from correction."""
    source, oracle = _trees(tmp_path)
    _write(oracle, "bug-state.txt", b"present")

    with pytest.raises(BehaviorProgramError, match="cannot distinguish"):
        _ = author_behavior_programs(
            _programs(),
            _context(source, tmp_path),
            _context(oracle, tmp_path),
        )
