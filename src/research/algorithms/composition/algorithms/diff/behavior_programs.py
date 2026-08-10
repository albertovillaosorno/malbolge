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
#   - Author and observe behavior profiles from portable probe programs.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Author and observe behavior profiles from portable probe programs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from algorithms.diff.behavior import BehaviorObservations
from algorithms.diff.behavior import BehaviorProfile
from algorithms.diff.behavior import BugObservation
from algorithms.diff.behavior import BugProbe
from algorithms.diff.behavior import BugState
from algorithms.diff.behavior import CompatibilityObservation
from algorithms.diff.behavior import CompatibilityProbe
from algorithms.diff.behavior import IdentityObservation
from algorithms.diff.behavior import IdentityProbe
from algorithms.diff.behavior import evaluate_behavior
from algorithms.diff.probe_exec import ProbeExecutionError
from algorithms.diff.probe_exec import run_probe_program
from algorithms.diff.probe_exec import run_probe_programs

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from algorithms.diff.behavior import BehaviorEvidence
    from algorithms.diff.probe_exec import ProbeProgram
    from algorithms.diff.probe_exec import ProbeRunContext
    from algorithms.diff.probe_exec import ProbeTranscript


class BehaviorProgramError(ValueError):
    """Raised when behavior programs cannot form an unambiguous profile."""


@dataclass(frozen=True, slots=True)
class BugProgram:
    """Portable probe program plus the correction it conditionally controls."""

    program: ProbeProgram
    correction_id: str

    def __post_init__(self) -> None:
        """Require a named correction for the bug probe.

        Raises:
            BehaviorProgramError: The correction identifier is empty.

        """
        if not self.correction_id:
            message = "bug behavior program requires a correction identifier"
            raise BehaviorProgramError(message)


@dataclass(frozen=True, slots=True)
class BehaviorPrograms:
    """Consumer-supplied portable programs for all behavior probe classes."""

    identity: tuple[ProbeProgram, ...]
    compatibility: tuple[ProbeProgram, ...]
    bugs: tuple[BugProgram, ...]

    def __post_init__(self) -> None:
        """Require sorted unique identifiers and at least one identity program.

        Raises:
            BehaviorProgramError: Program identifiers violate profile policy.

        """
        if not self.identity:
            message = "behavior programs require at least one identity program"
            raise BehaviorProgramError(message)
        groups = (
            _program_ids(self.identity),
            _bug_program_ids(self.bugs),
            _program_ids(self.compatibility),
        )
        identifiers = tuple(item for group in groups for item in group)
        if len(identifiers) != len(set(identifiers)):
            message = "behavior program identifiers must be globally unique"
            raise BehaviorProgramError(message)
        correction_ids = tuple(item.correction_id for item in self.bugs)
        if len(correction_ids) != len(set(correction_ids)):
            message = "bug behavior correction identifiers must be unique"
            raise BehaviorProgramError(message)


@dataclass(frozen=True, slots=True)
class AuthoredBugProgram:
    """Bug program with source-present and oracle-fixed transcript baselines."""

    program: ProbeProgram
    correction_id: str
    present_digest: bytes
    fixed_digest: bytes


@dataclass(frozen=True, slots=True)
class AuthoredBehaviorPrograms:
    """Distributable probe programs plus locally authored behavior baselines."""

    profile: BehaviorProfile
    identity: tuple[ProbeProgram, ...]
    compatibility: tuple[ProbeProgram, ...]
    bugs: tuple[AuthoredBugProgram, ...]


def _sorted_unique(identifiers: tuple[str, ...], kind: str) -> tuple[str, ...]:
    if identifiers != tuple(sorted(set(identifiers))):
        message = (
            f"{kind} behavior programs must have unique sorted identifiers"
        )
        raise BehaviorProgramError(message)
    return identifiers


def _program_ids(programs: tuple[ProbeProgram, ...]) -> tuple[str, ...]:
    identifiers = tuple(program.probe_id for program in programs)
    return _sorted_unique(identifiers, "probe")


def _bug_program_ids(programs: tuple[BugProgram, ...]) -> tuple[str, ...]:
    identifiers = tuple(program.program.probe_id for program in programs)
    return _sorted_unique(identifiers, "bug")


def _all_programs(programs: BehaviorPrograms) -> tuple[ProbeProgram, ...]:
    flattened = (
        *programs.identity,
        *programs.compatibility,
        *(item.program for item in programs.bugs),
    )
    return tuple(sorted(flattened, key=lambda item: item.probe_id))


def _transcript_map(
    transcripts: Iterable[ProbeTranscript],
) -> dict[str, ProbeTranscript]:
    return {transcript.probe_id: transcript for transcript in transcripts}


def _require_digest(transcript: ProbeTranscript) -> bytes:
    if transcript.digested_commands < 1:
        message = (
            f"behavior probe {transcript.probe_id!r} selects no stdout "
            "for identity"
        )
        raise BehaviorProgramError(message)
    return transcript.digest


def _resolved_context_path(path: Path, description: str) -> Path:
    try:
        return path.resolve()
    except OSError as error:
        message = f"behavior {description} resolution failed: {path}: {error}"
        raise BehaviorProgramError(message) from error


def _context_signature(
    context: ProbeRunContext,
) -> tuple[Path, tuple[tuple[str, Path], ...]]:
    tools = tuple(
        (tool_id, _resolved_context_path(path, "tool"))
        for tool_id, path in context.tools
    )
    repository = _resolved_context_path(context.repository_root, "repository")
    return repository, tools


def _require_matching_contexts(
    source_context: ProbeRunContext,
    oracle_context: ProbeRunContext,
) -> None:
    if _context_signature(source_context) != _context_signature(oracle_context):
        message = (
            "source and oracle behavior runs must use the same tool bindings"
        )
        raise BehaviorProgramError(message)


def _author_bug_programs(
    programs: tuple[BugProgram, ...],
    source_transcripts: dict[str, ProbeTranscript],
    oracle_transcripts: dict[str, ProbeTranscript],
) -> tuple[AuthoredBugProgram, ...]:
    authored: list[AuthoredBugProgram] = []
    for item in programs:
        probe_id = item.program.probe_id
        present_digest = _require_digest(source_transcripts[probe_id])
        fixed_digest = _require_digest(oracle_transcripts[probe_id])
        if present_digest == fixed_digest:
            message = (
                f"bug probe {probe_id!r} cannot distinguish present from fixed"
            )
            raise BehaviorProgramError(message)
        authored.append(
            AuthoredBugProgram(
                program=item.program,
                correction_id=item.correction_id,
                present_digest=present_digest,
                fixed_digest=fixed_digest,
            )
        )
    return tuple(authored)


def author_behavior_programs(
    programs: BehaviorPrograms,
    source_context: ProbeRunContext,
    oracle_context: ProbeRunContext,
) -> AuthoredBehaviorPrograms:
    """Generate behavior baselines from source and local corrected oracle.

    Identity baselines come from the source. Compatibility programs must execute
    successfully on the source but do not contribute an output digest. Every bug
    program runs against both source and oracle, which must yield distinct
    selected-stdout digests for unambiguous `present` versus `fixed` routing.

    Returns:
        Portable authored programs plus the evaluator profile.

    """
    _require_matching_contexts(source_context, oracle_context)
    source_transcripts = _transcript_map(
        run_probe_programs(_all_programs(programs), source_context)
    )
    bug_programs = tuple(item.program for item in programs.bugs)
    oracle_transcripts = _transcript_map(
        run_probe_programs(bug_programs, oracle_context) if bug_programs else ()
    )
    identity = tuple(
        IdentityProbe(
            probe_id=program.probe_id,
            expected_digest=_require_digest(
                source_transcripts[program.probe_id]
            ),
        )
        for program in programs.identity
    )
    compatibility = tuple(
        CompatibilityProbe(probe_id=program.probe_id)
        for program in programs.compatibility
    )
    authored_bugs = _author_bug_programs(
        programs.bugs,
        source_transcripts,
        oracle_transcripts,
    )
    bug_profile = tuple(
        BugProbe(
            probe_id=item.program.probe_id, correction_id=item.correction_id
        )
        for item in authored_bugs
    )
    return AuthoredBehaviorPrograms(
        profile=BehaviorProfile(
            identity=identity,
            compatibility=compatibility,
            bugs=bug_profile,
        ),
        identity=programs.identity,
        compatibility=programs.compatibility,
        bugs=authored_bugs,
    )


def _try_transcript(
    program: ProbeProgram,
    context: ProbeRunContext,
) -> ProbeTranscript | None:
    try:
        return run_probe_program(program, context)
    except ProbeExecutionError:
        return None


def _observe_identity(
    programs: tuple[ProbeProgram, ...],
    context: ProbeRunContext,
) -> tuple[IdentityObservation, ...]:
    observations: list[IdentityObservation] = []
    for program in programs:
        transcript = _try_transcript(program, context)
        digest = transcript.digest if transcript is not None else None
        observations.append(IdentityObservation(program.probe_id, digest))
    return tuple(observations)


def _observe_compatibility(
    programs: tuple[ProbeProgram, ...],
    context: ProbeRunContext,
) -> tuple[CompatibilityObservation, ...]:
    return tuple(
        CompatibilityObservation(
            probe_id=program.probe_id,
            compatible=_try_transcript(program, context) is not None,
        )
        for program in programs
    )


def _bug_state(
    program: AuthoredBugProgram,
    transcript: ProbeTranscript | None,
) -> BugState:
    state = BugState.UNKNOWN
    if transcript is not None:
        if transcript.digest == program.present_digest:
            state = BugState.PRESENT
        elif transcript.digest == program.fixed_digest:
            state = BugState.FIXED
    return state


def _observe_bugs(
    programs: tuple[AuthoredBugProgram, ...],
    context: ProbeRunContext,
) -> tuple[BugObservation, ...]:
    return tuple(
        BugObservation(
            probe_id=item.program.probe_id,
            state=_bug_state(item, _try_transcript(item.program, context)),
        )
        for item in programs
    )


def observe_behavior_programs(
    authored: AuthoredBehaviorPrograms,
    context: ProbeRunContext,
) -> BehaviorObservations:
    """Execute authored portable programs against one candidate source tree.

    Returns:
        Normalized observations consumable by the generic behavior evaluator.

    """
    return BehaviorObservations(
        identity=_observe_identity(authored.identity, context),
        compatibility=_observe_compatibility(authored.compatibility, context),
        bugs=_observe_bugs(authored.bugs, context),
    )


def evaluate_behavior_programs(
    authored: AuthoredBehaviorPrograms,
    context: ProbeRunContext,
    minimum_similarity: float,
) -> BehaviorEvidence:
    """Execute authored programs and evaluate their normalized observations.

    Returns:
        Generic behavior evidence including bug-correction routing.

    """
    observations = observe_behavior_programs(authored, context)
    return evaluate_behavior(authored.profile, observations, minimum_similarity)
