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

"""Synthetic tests for authoring and observing portable behavior programs."""

from __future__ import annotations

import math
from pathlib import Path
import sys
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff.behavior import BugState
from algorithms.diff.behavior_programs import AuthoredBehaviorPrograms
from algorithms.diff.behavior_programs import AuthoredBugProgram
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
import pytest

if TYPE_CHECKING:
    from algorithms.diff.behavior import BehaviorProfile

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


def test_context_repository_resolution_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep repository resolution failures inside behavior authoring."""
    source, oracle = _trees(tmp_path)
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == tmp_path:
            message = "blocked behavior repository"
            raise PermissionError(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    with pytest.raises(
        BehaviorProgramError, match="repository resolution failed"
    ):
        _ = author_behavior_programs(
            _programs(),
            _context(source, tmp_path),
            _context(oracle, tmp_path),
        )


def test_context_tool_resolution_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep tool resolution failures inside behavior authoring."""
    source, oracle = _trees(tmp_path)
    tool = Path(sys.executable)
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == tool:
            message = "blocked behavior tool"
            raise PermissionError(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    with pytest.raises(BehaviorProgramError, match="tool resolution failed"):
        _ = author_behavior_programs(
            _programs(),
            _context(source, tmp_path),
            _context(oracle, tmp_path),
        )


def test_behavior_program_records_reject_foreign_mutable_inputs() -> None:
    """Validate metadata before dereferencing program records."""
    program = _read_program("identity", "identity.txt")
    with pytest.raises(BehaviorProgramError, match="exact ProbeProgram"):
        _ = BugProgram(cast("ProbeProgram", object()), "fix")
    with pytest.raises(BehaviorProgramError, match="correction identifier"):
        _ = BugProgram(program, cast("str", object()))
    with pytest.raises(BehaviorProgramError, match="immutable tuple"):
        _ = BehaviorPrograms(
            identity=cast(
                "tuple[ProbeProgram, ...]",
                cast("object", [program]),
            ),
            compatibility=(),
            bugs=(),
        )
    with pytest.raises(BehaviorProgramError, match="foreign probe program"):
        _ = BehaviorPrograms(
            identity=(cast("ProbeProgram", object()),),
            compatibility=(),
            bugs=(),
        )
    with pytest.raises(BehaviorProgramError, match="foreign bug record"):
        _ = BehaviorPrograms(
            identity=(program,),
            compatibility=(),
            bugs=(cast("BugProgram", object()),),
        )


def test_authored_behavior_records_reject_foreign_incoherent_inputs(
    tmp_path: Path,
) -> None:
    """Reject direct authored records that bypass profile coherence."""
    program = _read_program("identity-stable", "identity.txt")
    with pytest.raises(BehaviorProgramError, match="exact ProbeProgram"):
        _ = AuthoredBugProgram(
            cast("ProbeProgram", object()),
            "fix",
            b"present",
            b"fixed",
        )
    with pytest.raises(BehaviorProgramError, match="non-empty exact bytes"):
        _ = AuthoredBugProgram(
            program,
            "fix",
            cast("bytes", cast("object", bytearray(b"present"))),
            b"fixed",
        )
    with pytest.raises(BehaviorProgramError, match="distinguish"):
        _ = AuthoredBugProgram(program, "fix", b"same", b"same")

    authored, _, _ = _authored(tmp_path)
    with pytest.raises(BehaviorProgramError, match="exact BehaviorProfile"):
        _ = AuthoredBehaviorPrograms(
            profile=cast("BehaviorProfile", object()),
            identity=authored.identity,
            compatibility=authored.compatibility,
            bugs=authored.bugs,
        )
    with pytest.raises(BehaviorProgramError, match="immutable tuple"):
        _ = AuthoredBehaviorPrograms(
            profile=authored.profile,
            identity=cast(
                "tuple[ProbeProgram, ...]",
                cast("object", list(authored.identity)),
            ),
            compatibility=authored.compatibility,
            bugs=authored.bugs,
        )
    with pytest.raises(
        BehaviorProgramError,
        match="do not match behavior profile",
    ):
        _ = AuthoredBehaviorPrograms(
            profile=authored.profile,
            identity=(_read_program("other", "identity.txt"),),
            compatibility=authored.compatibility,
            bugs=authored.bugs,
        )


def test_behavior_program_apis_reject_foreign_records_before_execution(
    tmp_path: Path,
) -> None:
    """Validate public records before authoring or observation dereference."""
    source, oracle = _trees(tmp_path)
    source_context = _context(source, tmp_path)
    oracle_context = _context(oracle, tmp_path)
    with pytest.raises(BehaviorProgramError, match="exact BehaviorPrograms"):
        _ = author_behavior_programs(
            cast("BehaviorPrograms", object()),
            source_context,
            oracle_context,
        )
    with pytest.raises(BehaviorProgramError, match="exact ProbeRunContext"):
        _ = author_behavior_programs(
            _programs(),
            cast("ProbeRunContext", object()),
            oracle_context,
        )

    authored = author_behavior_programs(
        _programs(), source_context, oracle_context
    )
    with pytest.raises(
        BehaviorProgramError,
        match="exact AuthoredBehaviorPrograms",
    ):
        _ = observe_behavior_programs(
            cast("AuthoredBehaviorPrograms", object()),
            source_context,
        )
    with pytest.raises(BehaviorProgramError, match="exact ProbeRunContext"):
        _ = observe_behavior_programs(
            authored,
            cast("ProbeRunContext", object()),
        )


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
