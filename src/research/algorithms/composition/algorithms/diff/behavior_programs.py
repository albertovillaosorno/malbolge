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

import builtins
import os
import shutil
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar, cast

from algorithms.diff.behavior import (
    BehaviorObservations,
    BehaviorProfile,
    BugObservation,
    BugProbe,
    BugState,
    CompatibilityObservation,
    CompatibilityProbe,
    IdentityObservation,
    IdentityProbe,
    evaluate_behavior,
)
from algorithms.diff.exact import ExactTreeError, snapshot_tree
from algorithms.diff.probe_exec import (
    ProbeExecutionError,
    ProbeProgram,
    ProbeRunContext,
    ProbeTranscript,
    run_probe_program,
    run_probe_programs,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import MemberDescriptorType

    from algorithms.diff.behavior import BehaviorEvidence
    from algorithms.diff.model import TreeSnapshot


# Bind native path operations before domain hooks can replace them.
_NATIVE_PATH_STR = Path.__str__
_NATIVE_OS_REALPATH = os.path.realpath
_NATIVE_ANY = builtins.any
_NATIVE_TYPE = builtins.type
_NATIVE_TUPLE = builtins.tuple
_NATIVE_LEN = builtins.len
_NATIVE_STR = builtins.str
_NATIVE_BYTES = builtins.bytes
_NATIVE_SORTED = builtins.sorted
_NATIVE_SET = builtins.set
_NATIVE_OBJECT_NEW = object.__new__
_NATIVE_COPYTREE = shutil.copytree
_NATIVE_TEMPORARY_DIRECTORY = tempfile.TemporaryDirectory
_NUL = "\x00"
_NATIVE_WINDOWS_HOST = os.name == "nt"


def _native_path_resolve(path: Path, *, strict: bool = False) -> Path:
    """Resolve trusted native paths without late process-global path hooks."""
    return Path(_NATIVE_OS_REALPATH(_NATIVE_PATH_STR(path), strict=strict))


_NATIVE_PATH_RESOLVE = _native_path_resolve


# Probe identities and transcript receipts remain authoritative after a
# consumer replaces late class properties or __getattribute__ methods.
_PROGRAM_ID_SLOT = cast(
    "MemberDescriptorType", ProbeProgram.__dict__["probe_id"]
)
_TRANSCRIPT_ID_SLOT = cast(
    "MemberDescriptorType", ProbeTranscript.__dict__["probe_id"]
)
_TRANSCRIPT_DIGEST_SLOT = cast(
    "MemberDescriptorType", ProbeTranscript.__dict__["digest"]
)
_TRANSCRIPT_COUNT_SLOT = cast(
    "MemberDescriptorType", ProbeTranscript.__dict__["digested_commands"]
)


def _program_id(program: ProbeProgram) -> str:
    return cast("str", _PROGRAM_ID_SLOT.__get__(program, ProbeProgram))


def _transcript_fields(transcript: ProbeTranscript) -> tuple[str, bytes, int]:
    return (
        cast("str", _TRANSCRIPT_ID_SLOT.__get__(transcript, ProbeTranscript)),
        cast("bytes", _TRANSCRIPT_DIGEST_SLOT.__get__(transcript, ProbeTranscript)),
        cast("int", _TRANSCRIPT_COUNT_SLOT.__get__(transcript, ProbeTranscript)),
    )


class BehaviorProgramError(ValueError):
    """Raised when behavior programs cannot form an unambiguous profile."""


def _behavior_error_detail(error: BaseException) -> str:
    """Keep host and delegated error display hooks outside probe admission."""
    if _NATIVE_TYPE(error) in (
        OSError,
        PermissionError,
        ValueError,
        RuntimeError,
        ExactTreeError,
        ProbeExecutionError,
        BehaviorProgramError,
    ):
        arguments = cast("tuple[object, ...]", error.args)
        if _NATIVE_LEN(arguments) == 1 and _NATIVE_TYPE(arguments[0]) is _NATIVE_STR:
            return arguments[0]
    return _NATIVE_TYPE(error).__name__


def _require_selected_program(program: ProbeProgram, context: str) -> None:
    """Require at least one observation in an identity or bug program.

    Raises:
        BehaviorProgramError: No command selects stdout or exit status.

    """
    if not _NATIVE_ANY(
        command.digest_stdout or command.digest_exit_code
        for command in program.commands
    ):
        message = f"{context} program requires a selected observation"
        raise BehaviorProgramError(message)


@dataclass(frozen=True, slots=True, init=False)
class BugProgram:
    """Portable probe program plus the correction it conditionally controls."""

    program: ProbeProgram
    correction_id: str

    def __init__(self, program: ProbeProgram, correction_id: str) -> None:
        """Bind original fields and validate the bug program."""
        _BUG_PROGRAM_SLOT.__set__(self, program)
        _BUG_CORRECTION_SLOT.__set__(self, correction_id)
        _BUG_PROGRAM_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require a named correction for the bug probe.

        Raises:
            BehaviorProgramError: The correction identifier is empty.

        """
        program, correction = read_bug_program(self)
        if _NATIVE_TYPE(program) is not ProbeProgram:
            message = "bug behavior program requires an exact ProbeProgram"
            raise BehaviorProgramError(message)
        _require_selected_program(program, "bug")
        _ = _require_correction_identifier(correction, "bug behavior program")


_BUG_PROGRAM_VALIDATOR = BugProgram.__dict__["__post_init__"]
_BUG_PROGRAM_SLOT = cast("MemberDescriptorType", BugProgram.__dict__["program"])
_BUG_CORRECTION_SLOT = cast(
    "MemberDescriptorType", BugProgram.__dict__["correction_id"]
)


def read_bug_program(program: BugProgram) -> tuple[ProbeProgram, str]:
    """Read the native bug program fields, unaffected by later class hooks."""
    return (
        cast("ProbeProgram", _BUG_PROGRAM_SLOT.__get__(program, BugProgram)),
        cast("str", _BUG_CORRECTION_SLOT.__get__(program, BugProgram)),
    )


def _require_program_tuple(value: object, context: str) -> None:
    if _NATIVE_TYPE(value) is not _NATIVE_TUPLE:
        message = f"{context} must use the exact immutable tuple type"
        raise BehaviorProgramError(message)
    items = cast("tuple[object, ...]", value)
    if _NATIVE_ANY(_NATIVE_TYPE(item) is not ProbeProgram for item in items):
        message = f"{context} contains a foreign probe program"
        raise BehaviorProgramError(message)


def _require_identity_program_tuple(value: object, context: str) -> None:
    _require_program_tuple(value, context)
    programs = cast("tuple[ProbeProgram, ...]", value)
    for program in programs:
        _require_selected_program(program, "identity")


def _require_bug_program_tuple(value: object) -> None:
    if _NATIVE_TYPE(value) is not _NATIVE_TUPLE:
        message = "bug behavior programs must use the exact immutable tuple type"
        raise BehaviorProgramError(message)
    items = cast("tuple[object, ...]", value)
    if _NATIVE_ANY(_NATIVE_TYPE(item) is not BugProgram for item in items):
        message = "bug behavior programs contain a foreign bug record"
        raise BehaviorProgramError(message)


@dataclass(frozen=True, slots=True, init=False)
class BehaviorPrograms:
    """Consumer-supplied portable programs for all behavior probe classes."""

    identity: tuple[ProbeProgram, ...]
    compatibility: tuple[ProbeProgram, ...]
    bugs: tuple[BugProgram, ...]

    def __init__(
        self,
        identity: tuple[ProbeProgram, ...],
        compatibility: tuple[ProbeProgram, ...],
        bugs: tuple[BugProgram, ...],
    ) -> None:
        """Bind original groups before validating program topology."""
        _BEHAVIOR_IDENTITY_SLOT.__set__(self, identity)
        _BEHAVIOR_COMPATIBILITY_SLOT.__set__(self, compatibility)
        _BEHAVIOR_BUGS_SLOT.__set__(self, bugs)
        _BEHAVIOR_PROGRAMS_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require sorted unique identifiers and at least one identity program.

        Raises:
            BehaviorProgramError: Program identifiers violate profile policy.

        """
        identity, compatibility, bugs = read_behavior_programs(self)
        _require_identity_program_tuple(identity, "identity behavior programs")
        _require_program_tuple(compatibility, "compatibility behavior programs")
        _require_bug_program_tuple(bugs)
        if not identity:
            message = "behavior programs require at least one identity program"
            raise BehaviorProgramError(message)
        groups = (
            _program_ids(identity),
            _bug_program_ids(bugs),
            _program_ids(compatibility),
        )
        identifiers = _NATIVE_TUPLE(item for group in groups for item in group)
        if _NATIVE_LEN(identifiers) != _NATIVE_LEN(_NATIVE_SET(identifiers)):
            message = "behavior program identifiers must be globally unique"
            raise BehaviorProgramError(message)
        correction_ids = _NATIVE_TUPLE(read_bug_program(item)[1] for item in bugs)
        if _NATIVE_LEN(correction_ids) != _NATIVE_LEN(
            _NATIVE_SET(correction_ids)
        ):
            message = "bug behavior correction identifiers must be unique"
            raise BehaviorProgramError(message)


_BEHAVIOR_PROGRAMS_VALIDATOR = BehaviorPrograms.__dict__["__post_init__"]
_BEHAVIOR_IDENTITY_SLOT = cast(
    "MemberDescriptorType", BehaviorPrograms.__dict__["identity"]
)
_BEHAVIOR_COMPATIBILITY_SLOT = cast(
    "MemberDescriptorType", BehaviorPrograms.__dict__["compatibility"]
)
_BEHAVIOR_BUGS_SLOT = cast(
    "MemberDescriptorType", BehaviorPrograms.__dict__["bugs"]
)


def read_behavior_programs(
    programs: BehaviorPrograms,
) -> tuple[tuple[ProbeProgram, ...], tuple[ProbeProgram, ...], tuple[BugProgram, ...]]:
    """Read native identity, compatibility and bug program groups."""
    return (
        cast(
            "tuple[ProbeProgram, ...]",
            _BEHAVIOR_IDENTITY_SLOT.__get__(programs, BehaviorPrograms),
        ),
        cast(
            "tuple[ProbeProgram, ...]",
            _BEHAVIOR_COMPATIBILITY_SLOT.__get__(programs, BehaviorPrograms),
        ),
        cast(
            "tuple[BugProgram, ...]",
            _BEHAVIOR_BUGS_SLOT.__get__(programs, BehaviorPrograms),
        ),
    )


def _require_exact_probe_program(value: object, context: str) -> ProbeProgram:
    if _NATIVE_TYPE(value) is not ProbeProgram:
        message = f"{context} requires an exact ProbeProgram"
        raise BehaviorProgramError(message)
    return value


def _require_correction_identifier(value: object, context: str) -> str:
    if _NATIVE_TYPE(value) is not _NATIVE_STR or not value:
        message = f"{context} requires a correction identifier"
        raise BehaviorProgramError(message)
    if _NUL in value:
        message = f"{context} correction identifier must not contain NUL"
        raise BehaviorProgramError(message)
    try:
        _ = value.encode("utf-8")
    except UnicodeEncodeError as error:
        message = f"{context} correction identifier must use UTF-8 text"
        raise BehaviorProgramError(message) from error
    return value


def _require_authored_digest(value: object, context: str) -> bytes:
    if _NATIVE_TYPE(value) is not _NATIVE_BYTES or not value:
        message = f"{context} must use non-empty exact bytes"
        raise BehaviorProgramError(message)
    return value


@dataclass(frozen=True, slots=True, init=False)
class AuthoredBugProgram:
    """Bug program with source-present and oracle-fixed transcript baselines."""

    program: ProbeProgram
    correction_id: str
    present_digest: bytes
    fixed_digest: bytes

    def __init__(
        self,
        program: ProbeProgram,
        correction_id: str,
        present_digest: bytes,
        fixed_digest: bytes,
    ) -> None:
        """Bind original fields before checking authored bug evidence."""
        _AUTHORED_BUG_PROGRAM_SLOT.__set__(self, program)
        _AUTHORED_BUG_CORRECTION_SLOT.__set__(self, correction_id)
        _AUTHORED_BUG_PRESENT_SLOT.__set__(self, present_digest)
        _AUTHORED_BUG_FIXED_SLOT.__set__(self, fixed_digest)
        _AUTHORED_BUG_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require exact unambiguous authored bug evidence.

        Raises:
            BehaviorProgramError: Present and fixed digests are identical.

        """
        program, correction, present_digest, fixed_digest = read_authored_bug(self)
        _ = _require_exact_probe_program(program, "authored bug")
        _require_selected_program(program, "authored bug")
        _ = _require_correction_identifier(correction, "authored bug")
        present = _require_authored_digest(
            present_digest, "authored bug present digest"
        )
        fixed = _require_authored_digest(
            fixed_digest, "authored bug fixed digest"
        )
        if present == fixed:
            message = "authored bug digests must distinguish present from fixed"
            raise BehaviorProgramError(message)


_AUTHORED_BUG_VALIDATOR = AuthoredBugProgram.__dict__["__post_init__"]
_AUTHORED_BUG_PROGRAM_SLOT = cast(
    "MemberDescriptorType", AuthoredBugProgram.__dict__["program"]
)
_AUTHORED_BUG_CORRECTION_SLOT = cast(
    "MemberDescriptorType", AuthoredBugProgram.__dict__["correction_id"]
)
_AUTHORED_BUG_PRESENT_SLOT = cast(
    "MemberDescriptorType", AuthoredBugProgram.__dict__["present_digest"]
)
_AUTHORED_BUG_FIXED_SLOT = cast(
    "MemberDescriptorType", AuthoredBugProgram.__dict__["fixed_digest"]
)


def read_authored_bug(
    bug: AuthoredBugProgram,
) -> tuple[ProbeProgram, str, bytes, bytes]:
    """Read original authored bug program and digest evidence."""
    return (
        cast(
            "ProbeProgram",
            _AUTHORED_BUG_PROGRAM_SLOT.__get__(bug, AuthoredBugProgram),
        ),
        cast("str", _AUTHORED_BUG_CORRECTION_SLOT.__get__(bug, AuthoredBugProgram)),
        cast("bytes", _AUTHORED_BUG_PRESENT_SLOT.__get__(bug, AuthoredBugProgram)),
        cast("bytes", _AUTHORED_BUG_FIXED_SLOT.__get__(bug, AuthoredBugProgram)),
    )


@dataclass(frozen=True, slots=True, init=False)
class AuthoredBehaviorPrograms:
    """Distributable probe programs plus locally authored behavior baselines."""

    profile: BehaviorProfile
    identity: tuple[ProbeProgram, ...]
    compatibility: tuple[ProbeProgram, ...]
    bugs: tuple[AuthoredBugProgram, ...]

    def __init__(
        self,
        profile: BehaviorProfile,
        identity: tuple[ProbeProgram, ...],
        compatibility: tuple[ProbeProgram, ...],
        bugs: tuple[AuthoredBugProgram, ...],
    ) -> None:
        """Bind original fields before validating the authored profile."""
        _AUTHORED_PROFILE_SLOT.__set__(self, profile)
        _AUTHORED_IDENTITY_SLOT.__set__(self, identity)
        _AUTHORED_COMPATIBILITY_SLOT.__set__(self, compatibility)
        _AUTHORED_BUGS_SLOT.__set__(self, bugs)
        _AUTHORED_BEHAVIOR_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require exact programs aligned with the behavior profile.

        Raises:
            BehaviorProgramError: Authored programs are invalid or misaligned.

        """
        profile, identity, compatibility, bugs = read_authored_behavior(self)
        if _NATIVE_TYPE(profile) is not BehaviorProfile:
            message = "authored behavior requires an exact BehaviorProfile"
            raise BehaviorProgramError(message)
        _require_identity_program_tuple(identity, "authored identity programs")
        _require_program_tuple(compatibility, "authored compatibility programs")
        _require_authored_bug_tuple(bugs)
        _require_authored_profile_alignment(self)


_AUTHORED_BEHAVIOR_VALIDATOR = AuthoredBehaviorPrograms.__dict__["__post_init__"]
_AUTHORED_PROFILE_SLOT = cast(
    "MemberDescriptorType", AuthoredBehaviorPrograms.__dict__["profile"]
)
_AUTHORED_IDENTITY_SLOT = cast(
    "MemberDescriptorType", AuthoredBehaviorPrograms.__dict__["identity"]
)
_AUTHORED_COMPATIBILITY_SLOT = cast(
    "MemberDescriptorType", AuthoredBehaviorPrograms.__dict__["compatibility"]
)
_AUTHORED_BUGS_SLOT = cast(
    "MemberDescriptorType", AuthoredBehaviorPrograms.__dict__["bugs"]
)


def read_authored_behavior(
    authored: AuthoredBehaviorPrograms,
) -> tuple[
    BehaviorProfile,
    tuple[ProbeProgram, ...],
    tuple[ProbeProgram, ...],
    tuple[AuthoredBugProgram, ...],
]:
    """Read stored profile, identity, compatibility, and correction programs."""
    return (
        cast(
            "BehaviorProfile",
            _AUTHORED_PROFILE_SLOT.__get__(authored, AuthoredBehaviorPrograms),
        ),
        cast(
            "tuple[ProbeProgram, ...]",
            _AUTHORED_IDENTITY_SLOT.__get__(authored, AuthoredBehaviorPrograms),
        ),
        cast(
            "tuple[ProbeProgram, ...]",
            _AUTHORED_COMPATIBILITY_SLOT.__get__(authored, AuthoredBehaviorPrograms),
        ),
        cast(
            "tuple[AuthoredBugProgram, ...]",
            _AUTHORED_BUGS_SLOT.__get__(authored, AuthoredBehaviorPrograms),
        ),
    )


# A probe runner can replace process-global class hooks before its transcript
# is consumed. Pin the original record initializers, not just their validators,
# and allocate native instances without dispatching through late __new__.
_RecordT = TypeVar("_RecordT")
_IDENTITY_PROBE_INIT = cast("Callable[..., None]", IdentityProbe.__dict__["__init__"])
_COMPATIBILITY_PROBE_INIT = cast(
    "Callable[..., None]", CompatibilityProbe.__dict__["__init__"]
)
_BUG_PROBE_INIT = cast("Callable[..., None]", BugProbe.__dict__["__init__"])
_BEHAVIOR_PROFILE_INIT = cast(
    "Callable[..., None]", BehaviorProfile.__dict__["__init__"]
)
_AUTHORED_BUG_INIT = cast(
    "Callable[..., None]", AuthoredBugProgram.__dict__["__init__"]
)
_AUTHORED_BEHAVIOR_INIT = cast(
    "Callable[..., None]", AuthoredBehaviorPrograms.__dict__["__init__"]
)
_IDENTITY_OBSERVATION_INIT = cast(
    "Callable[..., None]", IdentityObservation.__dict__["__init__"]
)
_COMPATIBILITY_OBSERVATION_INIT = cast(
    "Callable[..., None]", CompatibilityObservation.__dict__["__init__"]
)
_BUG_OBSERVATION_INIT = cast("Callable[..., None]", BugObservation.__dict__["__init__"])
_BEHAVIOR_OBSERVATIONS_INIT = cast(
    "Callable[..., None]", BehaviorObservations.__dict__["__init__"]
)


def _new_receipt(
    record_type: type[_RecordT], initializer: Callable[..., None], /, **fields: object
) -> _RecordT:
    result = _NATIVE_OBJECT_NEW(record_type)
    initializer(result, **fields)
    return result


def _require_authored_bug_tuple(value: object) -> None:
    if _NATIVE_TYPE(value) is not _NATIVE_TUPLE:
        message = "authored bugs must use the exact immutable tuple type"
        raise BehaviorProgramError(message)
    items = cast("tuple[object, ...]", value)
    if _NATIVE_ANY(
        _NATIVE_TYPE(item) is not AuthoredBugProgram for item in items
    ):
        message = "authored bugs contain a foreign authored bug record"
        raise BehaviorProgramError(message)


def _require_authored_profile_alignment(
    authored: AuthoredBehaviorPrograms,
) -> None:
    profile, identity, compatibility, authored_bugs = read_authored_behavior(
        authored
    )
    identity_ids = _NATIVE_TUPLE(_program_id(item) for item in identity)
    profile_identity_ids = _NATIVE_TUPLE(item.probe_id for item in profile.identity)
    compatibility_ids = _NATIVE_TUPLE(_program_id(item) for item in compatibility)
    profile_compatibility_ids = _NATIVE_TUPLE(
        item.probe_id for item in profile.compatibility
    )
    bugs = _NATIVE_TUPLE(
        (_program_id(read_authored_bug(item)[0]), read_authored_bug(item)[1])
        for item in authored_bugs
    )
    profile_bugs = _NATIVE_TUPLE(
        (item.probe_id, item.correction_id) for item in profile.bugs
    )
    if identity_ids != profile_identity_ids:
        message = "authored identity programs do not match behavior profile"
        raise BehaviorProgramError(message)
    if compatibility_ids != profile_compatibility_ids:
        message = "authored compatibility programs do not match behavior profile"
        raise BehaviorProgramError(message)
    if bugs != profile_bugs:
        message = "authored bug programs do not match behavior profile"
        raise BehaviorProgramError(message)


def _require_run_context(value: object, context: str) -> ProbeRunContext:
    if _NATIVE_TYPE(value) is not ProbeRunContext:
        message = f"{context} must use the exact ProbeRunContext type"
        raise BehaviorProgramError(message)
    return value


def _sorted_unique(identifiers: tuple[str, ...], kind: str) -> tuple[str, ...]:
    if identifiers != _NATIVE_TUPLE(_NATIVE_SORTED(_NATIVE_SET(identifiers))):
        message = f"{kind} behavior programs must have unique sorted identifiers"
        raise BehaviorProgramError(message)
    return identifiers


def _program_ids(programs: tuple[ProbeProgram, ...]) -> tuple[str, ...]:
    identifiers = _NATIVE_TUPLE(_program_id(program) for program in programs)
    return _sorted_unique(identifiers, "probe")


def _bug_program_ids(programs: tuple[BugProgram, ...]) -> tuple[str, ...]:
    identifiers = _NATIVE_TUPLE(
        _program_id(read_bug_program(program)[0]) for program in programs
    )
    return _sorted_unique(identifiers, "bug")


def _all_programs(programs: BehaviorPrograms) -> tuple[ProbeProgram, ...]:
    identity, compatibility, bugs = read_behavior_programs(programs)
    flattened = (
        *identity,
        *compatibility,
        *(read_bug_program(item)[0] for item in bugs),
    )
    return _NATIVE_TUPLE(
        _NATIVE_SORTED(flattened, key=_program_id)
    )


def _transcript_map(
    transcripts: tuple[ProbeTranscript, ...],
    programs: tuple[ProbeProgram, ...],
) -> dict[str, ProbeTranscript]:
    """Require exactly one native receipt for every requested probe."""
    if _NATIVE_TYPE(transcripts) is not _NATIVE_TUPLE or _NATIVE_ANY(
        _NATIVE_TYPE(item) is not ProbeTranscript for item in transcripts
    ):
        message = "behavior transcript batch must use exact immutable records"
        raise BehaviorProgramError(message)
    observed = _NATIVE_TUPLE(
        _transcript_fields(transcript)[0] for transcript in transcripts
    )
    expected = _NATIVE_TUPLE(_program_id(program) for program in programs)
    if observed != expected:
        message = "behavior transcript batch differs from requested programs"
        raise BehaviorProgramError(message)
    return {_transcript_fields(transcript)[0]: transcript for transcript in transcripts}


def _require_digest(transcript: ProbeTranscript) -> bytes:
    probe_id, digest, selected = _transcript_fields(transcript)
    if selected < 1:
        message = f"behavior probe {probe_id!r} selects no stdout for identity"
        raise BehaviorProgramError(message)
    return digest


def _resolved_context_path(path: Path, description: str) -> Path:
    try:
        resolved = _NATIVE_PATH_RESOLVE(path)
    except (OSError, ValueError, RuntimeError) as error:
        detail = _behavior_error_detail(error)
        native_path = _NATIVE_PATH_STR(path)
        message = f"behavior {description} resolution failed: {native_path}: {detail}"
        raise BehaviorProgramError(message) from error
    if _NATIVE_TYPE(resolved) is not _NATIVE_TYPE(Path()):
        message = f"behavior {description} resolution requires native resolved Path"
        raise BehaviorProgramError(message)
    return resolved


def _native_context_path_key(path: Path) -> str:
    """Compare canonical paths without mutable Path equality hooks."""
    spelling = _NATIVE_PATH_STR(path)
    return spelling.lower() if _NATIVE_WINDOWS_HOST else spelling


def _context_signature(
    context: ProbeRunContext,
) -> tuple[str, tuple[tuple[str, str], ...]]:
    tools = _NATIVE_TUPLE(
        (
            tool_id,
            _native_context_path_key(_resolved_context_path(path, "tool")),
        )
        for tool_id, path in context.tools
    )
    repository = _native_context_path_key(
        _resolved_context_path(context.repository_root, "repository")
    )
    return repository, tools


def _require_matching_contexts(
    source_context: ProbeRunContext,
    oracle_context: ProbeRunContext,
) -> None:
    # Comparing path objects would delegate to mutable Path.__eq__ and str.
    # Canonical host spellings retain Windows's case-insensitive comparison.
    if _context_signature(source_context) != _context_signature(oracle_context):
        message = "source and oracle behavior runs must use the same tool bindings"
        raise BehaviorProgramError(message)


def _author_bug_programs(
    programs: tuple[BugProgram, ...],
    source_transcripts: dict[str, ProbeTranscript],
    oracle_transcripts: dict[str, ProbeTranscript],
) -> tuple[AuthoredBugProgram, ...]:
    authored: list[AuthoredBugProgram] = []
    for item in programs:
        program, correction = read_bug_program(item)
        probe_id = _program_id(program)
        present_digest = _require_digest(source_transcripts[probe_id])
        fixed_digest = _require_digest(oracle_transcripts[probe_id])
        if present_digest == fixed_digest:
            message = f"bug probe {probe_id!r} cannot distinguish present from fixed"
            raise BehaviorProgramError(message)
        authored.append(
            _new_receipt(
                AuthoredBugProgram,
                _AUTHORED_BUG_INIT,
                program=program,
                correction_id=correction,
                present_digest=present_digest,
                fixed_digest=fixed_digest,
            )
        )
    return _NATIVE_TUPLE(authored)


def _require_authoring_trees_unchanged(
    admitted: tuple[tuple[Path, TreeSnapshot], ...],
) -> None:
    """Verify cross-stage source and oracle byte trees stay admitted.

    Raises:
        ProbeExecutionError: An authored input tree was changed or invalidated.

    """
    for root, expected in admitted:
        try:
            current = _snapshot_observed_source(root)
        except ProbeExecutionError as error:
            detail = _behavior_error_detail(error)
            message = f"behavior tree changed during authoring: {detail}"
            raise ProbeExecutionError(message) from error
        if current != expected:
            message = "behavior source/oracle tree changed during authoring"
            raise ProbeExecutionError(message)


def _run_authored_baselines(
    programs: BehaviorPrograms,
    source_context: ProbeRunContext,
    oracle_context: ProbeRunContext,
) -> tuple[dict[str, ProbeTranscript], dict[str, ProbeTranscript]]:
    """Run source/oracle probes while preserving their admitted input trees.

    Returns:
        Source and oracle transcript maps by probe identifier.

    """
    _, _, bugs = read_behavior_programs(programs)
    roots = (source_context.source_root,)
    if bugs:
        roots = (*roots, oracle_context.source_root)
    admitted = _NATIVE_TUPLE(
        (root, _snapshot_observed_source(root)) for root in roots
    )
    try:
        source_programs = _all_programs(programs)
        source_transcripts = _transcript_map(
            run_probe_programs(source_programs, source_context), source_programs
        )
        _require_authoring_trees_unchanged(admitted)
        bug_programs = _NATIVE_TUPLE(read_bug_program(item)[0] for item in bugs)
        oracle_transcripts = _transcript_map(
            run_probe_programs(bug_programs, oracle_context) if bug_programs else (),
            bug_programs,
        )
    finally:
        _require_authoring_trees_unchanged(admitted)
    return source_transcripts, oracle_transcripts


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

    Raises:
        BehaviorProgramError: Program metadata or contexts are invalid.

    """
    if _NATIVE_TYPE(programs) is not BehaviorPrograms:
        message = "behavior authoring requires exact BehaviorPrograms"
        raise BehaviorProgramError(message)
    source_context = _require_run_context(source_context, "source behavior context")
    oracle_context = _require_run_context(oracle_context, "oracle behavior context")
    _require_matching_contexts(source_context, oracle_context)
    identity_programs, compatibility_programs, bug_programs = read_behavior_programs(
        programs
    )
    source_transcripts, oracle_transcripts = _run_authored_baselines(
        programs, source_context, oracle_context
    )
    identity = _NATIVE_TUPLE(
        _new_receipt(
            IdentityProbe,
            _IDENTITY_PROBE_INIT,
            probe_id=_program_id(program),
            expected_digest=_require_digest(source_transcripts[_program_id(program)]),
        )
        for program in identity_programs
    )
    compatibility = _NATIVE_TUPLE(
        _new_receipt(
            CompatibilityProbe, _COMPATIBILITY_PROBE_INIT, probe_id=_program_id(program)
        )
        for program in compatibility_programs
    )
    authored_bugs = _author_bug_programs(
        bug_programs,
        source_transcripts,
        oracle_transcripts,
    )
    bug_profile = _NATIVE_TUPLE(
        _new_receipt(
            BugProbe,
            _BUG_PROBE_INIT,
            probe_id=_program_id(read_authored_bug(item)[0]),
            correction_id=read_authored_bug(item)[1],
        )
        for item in authored_bugs
    )
    return _new_receipt(
        AuthoredBehaviorPrograms,
        _AUTHORED_BEHAVIOR_INIT,
        profile=_new_receipt(
            BehaviorProfile,
            _BEHAVIOR_PROFILE_INIT,
            identity=identity,
            compatibility=compatibility,
            bugs=bug_profile,
        ),
        identity=identity_programs,
        compatibility=compatibility_programs,
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
        digest = _transcript_fields(transcript)[1] if transcript is not None else None
        observations.append(
            _new_receipt(
                IdentityObservation,
                _IDENTITY_OBSERVATION_INIT,
                probe_id=_program_id(program),
                digest=digest,
            )
        )
    return _NATIVE_TUPLE(observations)


def _observe_compatibility(
    programs: tuple[ProbeProgram, ...],
    context: ProbeRunContext,
) -> tuple[CompatibilityObservation, ...]:
    return _NATIVE_TUPLE(
        _new_receipt(
            CompatibilityObservation,
            _COMPATIBILITY_OBSERVATION_INIT,
            probe_id=_program_id(program),
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
        _, _, present, fixed = read_authored_bug(program)
        digest = _transcript_fields(transcript)[1]
        if digest == present:
            state = BugState.PRESENT
        elif digest == fixed:
            state = BugState.FIXED
    return state


def _observe_bugs(
    programs: tuple[AuthoredBugProgram, ...],
    context: ProbeRunContext,
) -> tuple[BugObservation, ...]:
    return _NATIVE_TUPLE(
        _new_receipt(
            BugObservation,
            _BUG_OBSERVATION_INIT,
            probe_id=_program_id(read_authored_bug(item)[0]),
            state=_bug_state(
                item, _try_transcript(read_authored_bug(item)[0], context)
            ),
        )
        for item in programs
    )


def _snapshot_observed_source(root: Path) -> TreeSnapshot:
    """Normalize tree snapshot failures to the behavior execution boundary.

    Returns:
        The full candidate byte-tree snapshot.

    Raises:
        ProbeExecutionError: The candidate tree is malformed or unreadable.

    """
    try:
        return snapshot_tree(root)
    except ExactTreeError as error:
        detail = _behavior_error_detail(error)
        message = f"behavior candidate tree changed between probes: {detail}"
        raise ProbeExecutionError(message) from error


def _require_observed_source_unchanged(root: Path, admitted: TreeSnapshot) -> None:
    """Require the entire candidate tree to retain its admitted bytes.

    Raises:
        ProbeExecutionError: Candidate bytes changed between probe groups.

    """
    if _snapshot_observed_source(root) != admitted:
        message = "behavior candidate tree changed between probes"
        raise ProbeExecutionError(message)


def _admit_observation_mirror(
    context: ProbeRunContext, mirror: Path, admitted: TreeSnapshot
) -> ProbeRunContext:
    """Freeze the observed source for all identity and bug probes.

    Returns:
        An immutable admitted mirror context for the entire probe observation.

    Raises:
        ProbeExecutionError: The mirror cannot be copied or matched to source.

    """
    try:
        completion = _NATIVE_COPYTREE(
            context.source_root, mirror, symlinks=True
        )
    except Exception as error:
        detail = _behavior_error_detail(error)
        message = f"behavior candidate mirror failed: {detail}"
        raise ProbeExecutionError(message) from error
    if _NATIVE_TYPE(completion) is not _NATIVE_TYPE(Path()) or _NATIVE_PATH_STR(
        completion
    ) != _NATIVE_PATH_STR(mirror):
        message = "behavior candidate mirror copy reported non-native completion"
        raise ProbeExecutionError(message)
    if _snapshot_observed_source(mirror) != admitted:
        message = "behavior candidate tree changed while creating mirror"
        raise ProbeExecutionError(message)
    _require_observed_source_unchanged(context.source_root, admitted)
    return replace(context, source_root=mirror, enforce_source_immutable=True)


def _require_observation_sources_unchanged(
    source: Path, mirror: Path, admitted: TreeSnapshot
) -> None:
    """Verify both original and observation mirror after one probe class."""
    _require_observed_source_unchanged(source, admitted)
    _require_observed_source_unchanged(mirror, admitted)


def _temporary_observation_root() -> tempfile.TemporaryDirectory[str]:
    try:
        return _NATIVE_TEMPORARY_DIRECTORY(prefix="diff-behavior-source-")
    except (OSError, ValueError, RuntimeError) as error:
        detail = _behavior_error_detail(error)
        message = f"behavior observation temporary root failed: {detail}"
        raise ProbeExecutionError(message) from error


def observe_behavior_programs(
    authored: AuthoredBehaviorPrograms,
    context: ProbeRunContext,
) -> BehaviorObservations:
    """Execute authored portable programs against one candidate source tree.

    Returns:
        Normalized observations consumable by the generic behavior evaluator.

    Raises:
        BehaviorProgramError: Authored metadata or execution context is invalid.

    """
    if _NATIVE_TYPE(authored) is not AuthoredBehaviorPrograms:
        message = "behavior observation requires exact AuthoredBehaviorPrograms"
        raise BehaviorProgramError(message)
    context = _require_run_context(context, "behavior observation context")
    _, identity_programs, compatibility_programs, bug_programs = read_authored_behavior(
        authored
    )
    admitted = _snapshot_observed_source(context.source_root)
    with _temporary_observation_root() as temporary:
        mirror = Path(temporary) / "source"
        mirrored = _admit_observation_mirror(context, mirror, admitted)
        identity = _observe_identity(identity_programs, mirrored)
        _require_observation_sources_unchanged(context.source_root, mirror, admitted)
        compatibility = _observe_compatibility(compatibility_programs, mirrored)
        _require_observation_sources_unchanged(context.source_root, mirror, admitted)
        bugs = _observe_bugs(bug_programs, mirrored)
        _require_observation_sources_unchanged(context.source_root, mirror, admitted)
        return _new_receipt(
            BehaviorObservations,
            _BEHAVIOR_OBSERVATIONS_INIT,
            identity=identity,
            compatibility=compatibility,
            bugs=bugs,
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
    profile = read_authored_behavior(authored)[0]
    return evaluate_behavior(profile, observations, minimum_similarity)
