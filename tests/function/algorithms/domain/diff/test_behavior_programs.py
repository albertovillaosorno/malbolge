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
import shutil
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
from algorithms.diff.probe_exec import ProbeExecutionError
from algorithms.diff.probe_exec import ProbeProgram
from algorithms.diff.probe_exec import ProbeRoot
from algorithms.diff.probe_exec import ProbeRunContext
from algorithms.diff.probe_exec import ToolExecutable
from algorithms.diff.probe_exec import run_probe_program
from algorithms.diff.probe_exec import run_probe_programs
import pytest

if TYPE_CHECKING:
    from algorithms.diff.behavior import BehaviorProfile
    from algorithms.diff.probe_exec import ProbeTranscript

_PYTHON_TOOL = "python"
_IDENTITY_A = "identity-a"
_IDENTITY_B = "identity-b"
_CHANGED_SECOND_BYTES = b"different"
_STABLE_IDENTITY_BYTES = b"stable"
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


def test_identity_and_bug_programs_require_selected_transcripts(
    tmp_path: Path,
) -> None:
    """Admit transcript selectors before any authoring process executes."""
    unselected = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "print('unselected output')"),
    )
    identity = ProbeProgram("identity-stable", (unselected,))
    with pytest.raises(BehaviorProgramError, match="selected observation"):
        _ = BehaviorPrograms(identity=(identity,), compatibility=(), bugs=())

    bug = ProbeProgram("historical-bug", (unselected,))
    with pytest.raises(BehaviorProgramError, match="selected observation"):
        _ = BehaviorPrograms(
            identity=(_read_program("identity-stable", "identity.txt"),),
            compatibility=(),
            bugs=(BugProgram(bug, "fix-historical-bug"),),
        )
    with pytest.raises(BehaviorProgramError, match="selected observation"):
        _ = AuthoredBugProgram(bug, "fix-historical-bug", b"present", b"fixed")

    authored, _, _ = _authored(tmp_path)
    with pytest.raises(BehaviorProgramError, match="selected observation"):
        _ = AuthoredBehaviorPrograms(
            profile=authored.profile,
            identity=(identity,),
            compatibility=authored.compatibility,
            bugs=authored.bugs,
        )

    _ = BehaviorPrograms(
        identity=(_read_program("identity-stable", "identity.txt"),),
        compatibility=(ProbeProgram("runtime-capability", (unselected,)),),
        bugs=(),
    )
    exit_only = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", "raise SystemExit(7)"),
        digest_exit_code=True,
        expected_exit_code=None,
    )
    _ = BehaviorPrograms(
        identity=(ProbeProgram("exit-identity", (exit_only,)),),
        compatibility=(),
        bugs=(
            BugProgram(
                ProbeProgram("exit-bug", (exit_only,)),
                "fix-exit-bug",
            ),
        ),
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


@pytest.mark.parametrize("mutate_after_source", [False, True])
@pytest.mark.parametrize("mutate_source", [False, True])
def test_authoring_rejects_cross_tree_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    mutate_after_source: bool,
    mutate_source: bool,
) -> None:
    """Neither source nor oracle can drift between authoring probe batches."""
    source, oracle = _trees(tmp_path)
    changed = source if mutate_source else oracle
    phase_root = source if mutate_after_source else oracle

    def modifying_batch(
        programs: tuple[ProbeProgram, ...], context: ProbeRunContext
    ) -> tuple[ProbeTranscript, ...]:
        transcripts = run_probe_programs(programs, context)
        if context.source_root == phase_root:
            _write(changed, "identity.txt", b"changed after probe")
        return transcripts

    monkeypatch.setattr(
        "algorithms.diff.behavior_programs.run_probe_programs", modifying_batch
    )
    with pytest.raises(ProbeExecutionError, match="changed during authoring"):
        _ = author_behavior_programs(
            _programs(),
            _context(source, tmp_path),
            _context(oracle, tmp_path),
        )


def test_failed_oracle_authoring_still_detects_source_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed oracle probe cannot suppress source-drift diagnostics."""
    source, oracle = _trees(tmp_path)

    def failing_oracle(
        programs: tuple[ProbeProgram, ...], context: ProbeRunContext
    ) -> tuple[ProbeTranscript, ...]:
        if context.source_root == oracle:
            _write(source, "identity.txt", b"changed before failed oracle")
            message = "synthetic oracle execution error"
            raise ProbeExecutionError(message)
        return run_probe_programs(programs, context)

    monkeypatch.setattr(
        "algorithms.diff.behavior_programs.run_probe_programs", failing_oracle
    )
    with pytest.raises(ProbeExecutionError, match="changed during authoring"):
        _ = author_behavior_programs(
            _programs(), _context(source, tmp_path), _context(oracle, tmp_path)
        )


def test_identity_only_authoring_does_not_require_oracle_tree(
    tmp_path: Path,
) -> None:
    """Without a bug baseline, oracle files are not required."""
    source, _ = _trees(tmp_path)
    missing_oracle = tmp_path / "missing-oracle"
    identity = _read_program("identity-stable", "identity.txt")
    programs = BehaviorPrograms(identity=(identity,), compatibility=(), bugs=())
    authored = author_behavior_programs(
        programs,
        _context(source, tmp_path),
        _context(missing_oracle, tmp_path),
    )
    _expect(
        authored.profile.identity[0].probe_id == identity.probe_id, "ID drift"
    )
    _expect(not authored.bugs, "identity-only authoring gained a bug baseline")


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


@pytest.mark.parametrize(
    "changed_after",
    ["identity-stable", "runtime-capability", "historical-bug"],
)
def test_observation_rejects_source_changed_between_probes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changed_after: str,
) -> None:
    """Identity from one source must not combine with a later bug state."""
    authored, source, _ = _authored(tmp_path)
    candidate = tmp_path / "switching-source"
    for name in ("identity.txt", "runtime.flag", "bug-state.txt"):
        _write(candidate, name, (source / name).read_bytes())

    def switching_run(
        program: ProbeProgram, run_context: ProbeRunContext
    ) -> ProbeTranscript:
        transcript = run_probe_program(program, run_context)
        if program.probe_id == changed_after:
            _write(candidate, "bug-state.txt", b"fixed")
        return transcript

    monkeypatch.setattr(
        "algorithms.diff.behavior_programs.run_probe_program", switching_run
    )
    with pytest.raises(ProbeExecutionError, match="changed between probes"):
        _ = evaluate_behavior_programs(
            authored,
            _context(candidate, tmp_path),
            minimum_similarity=0.80,
        )


def test_observation_keeps_one_source_view_across_identity_probes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A flip-and-restore candidate cannot blend separate identity snapshots."""
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    candidate = tmp_path / "candidate"
    for root in (source, oracle):
        _write(root, "first.txt", b"first")
        _write(root, "second.txt", b"second")
    _write(candidate, "first.txt", b"first")
    _write(candidate, "second.txt", _CHANGED_SECOND_BYTES)
    programs = BehaviorPrograms(
        identity=(
            _read_program(_IDENTITY_A, "first.txt"),
            _read_program(_IDENTITY_B, "second.txt"),
        ),
        compatibility=(),
        bugs=(),
    )
    authored = author_behavior_programs(
        programs, _context(source, tmp_path), _context(oracle, tmp_path)
    )

    def flip_during_identity(
        program: ProbeProgram, run_context: ProbeRunContext
    ) -> ProbeTranscript:
        transcript = run_probe_program(program, run_context)
        if program.probe_id == _IDENTITY_A:
            _write(candidate, "second.txt", b"second")
        elif program.probe_id == _IDENTITY_B:
            _write(candidate, "second.txt", _CHANGED_SECOND_BYTES)
        return transcript

    monkeypatch.setattr(
        "algorithms.diff.behavior_programs.run_probe_program",
        flip_during_identity,
    )
    evidence = evaluate_behavior_programs(
        authored, _context(candidate, tmp_path), minimum_similarity=1.0
    )
    _expect(not evidence.admitted, "interleaved source versions were admitted")
    _expect(
        (candidate / "second.txt").read_bytes() == _CHANGED_SECOND_BYTES,
        "candidate was not restored by interleaving fixture",
    )


def test_observation_rejects_copy_time_mirror_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A changed copied byte tree is rejected before any probe executes."""
    authored, source, _ = _authored(tmp_path)
    copied_tree = shutil.copytree

    def changed_copy(
        source_root: Path, destination: Path, *, symlinks: bool = False
    ) -> Path:
        copied = copied_tree(source_root, destination, symlinks=symlinks)
        _write(copied, "identity.txt", b"drift during copy")
        return copied

    monkeypatch.setattr(shutil, "copytree", changed_copy)
    with pytest.raises(
        ProbeExecutionError, match="changed while creating mirror"
    ):
        _ = observe_behavior_programs(authored, _context(source, tmp_path))
    _expect(
        (source / "identity.txt").read_bytes() == _STABLE_IDENTITY_BYTES,
        "authoring source changed during mirror rejection",
    )


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
