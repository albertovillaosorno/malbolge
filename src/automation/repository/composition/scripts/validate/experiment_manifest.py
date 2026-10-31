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
#   - Validate version-one reproducible research experiment manifests.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Validate version-one reproducible research experiment manifests."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from stat import S_ISREG
from typing import Never, cast

import tomllib

from scripts.repository_root import repository_root
from scripts.research_layout import research_algorithm_directories
from scripts.validate import target_profile

ROOT = repository_root(Path(__file__))
SCHEMA_VERSION = 1
MAX_MANIFEST_BYTES = 1024 * 1024
PARENT_SEGMENT = ".."
PLAN_RECORD_KIND = "plan"
RUN_RECORD_KIND = "run"
METHOD_CLASSES = frozenset(
    {
        "benchmarking",
        "engineering",
        "exploratory",
        "mathematical",
        "optimization",
        "replication",
    }
)
RECORD_KINDS = frozenset({PLAN_RECORD_KIND, RUN_RECORD_KIND})
NONCANONICAL_TARGET_SCOPES = frozenset(
    {
        "malbolge-1998-classic-word-domain",
        "multi-profile",
        "profile-independent",
    }
)
NONCANONICAL_FINGERPRINT_ERROR = (
    "manifest.challenge.target_profile_fingerprint must be absent for "
    "noncanonical target scope"
)
CANONICAL_FINGERPRINT_REQUIRED_ERROR = (
    "manifest.challenge.target_profile_fingerprint is required for canonical "
    "target profile"
)
RUN_OUTCOMES = frozenset(
    {
        "candidate-invalid",
        "no-solution",
        "resource-exhausted",
        "success",
        "tool-failure",
    }
)
HEX_40 = re.compile(r"[0-9a-f]{40}\Z")
HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
CORE_TABLES = (
    "budget",
    "challenge",
    "experiment",
    "provenance",
    "verification",
)


class ExperimentManifestError(ValueError):
    """Malformed or insufficiently identified research experiment manifest."""


@dataclass(frozen=True, slots=True)
class RunIdentity:
    """Exact environment and retained-output identity for one recorded run."""

    accelerator: str
    commit: str
    host: str
    outcome: str
    raw_output: str
    toolchain: str
    workload_sha256: str


@dataclass(frozen=True, slots=True)
class ExperimentManifest:
    """Validated core identity shared by research plans and recorded runs."""

    challenge_family: str
    configuration: str
    difficulty: int
    identifier: str
    implementation: str
    method_class: str
    oracle: str
    output: str
    record_kind: str
    run: RunIdentity | None
    seed: int
    target_profile: str
    target_profile_fingerprint: str | None


@dataclass(frozen=True, slots=True)
class _ExperimentFields:
    identifier: str
    method_class: str
    record_kind: str
    seed: int


@dataclass(frozen=True, slots=True)
class _ChallengeFields:
    difficulty: int
    family: str
    target_profile: str
    target_profile_fingerprint: str | None


@dataclass(frozen=True, slots=True)
class _ProvenanceFields:
    configuration: str
    implementation: str
    output: str


def _fail(message: str) -> Never:
    raise ExperimentManifestError(message)


def _mapping(value: object, context: str) -> dict[str, object]:
    if type(value) is not dict:
        _fail(f"{context} must be an exact native table")
    raw = cast("dict[object, object]", value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if type(key) is not str:
            _fail(f"{context} contains a non-native string key")
        result[key] = item
    return result


def _table(document: dict[str, object], name: str) -> dict[str, object]:
    if name not in document:
        _fail(f"manifest.{name} table is required")
    return _mapping(document[name], f"manifest.{name}")


def _string(table: dict[str, object], name: str, context: str) -> str:
    value = table.get(name)
    if type(value) is not str or not value:
        _fail(f"{context}.{name} must be a non-empty string")
    return value


def _integer(table: dict[str, object], name: str, context: str) -> int:
    value = table.get(name)
    if type(value) is not int:
        _fail(f"{context}.{name} must be an integer")
    return value


def _boolean(table: dict[str, object], name: str, context: str) -> bool:
    value = table.get(name)
    if type(value) is not bool:
        _fail(f"{context}.{name} must be a boolean")
    return value


def _relative_path(value: str, context: str) -> str:
    if "\x00" in value:
        _fail(f"{context} must not contain NUL")
    path = Path(value)
    windows_path = PureWindowsPath(value)
    native_relative = not path.is_absolute() and PARENT_SEGMENT not in path.parts
    windows_relative = (
        not windows_path.drive
        and not windows_path.root
        and PARENT_SEGMENT not in windows_path.parts
    )
    if not native_relative or not windows_relative:
        _fail(f"{context} must be repository-relative: {value}")
    return path.as_posix()


def _positive_budget(table: dict[str, object]) -> None:
    positive = any(type(value) is int and value > 0 for value in table.values())
    if not positive:
        _fail("manifest.budget must contain a positive integer stopping bound")


def _enum(value: str, allowed: frozenset[str], context: str) -> str:
    if value not in allowed:
        _fail(f"unsupported {context}: {value}")
    return value


def _admit_source_text(text: str, *, byte_limit: int) -> None:
    """Require bounded exact UTF-8 text before the host TOML parser.

    Raises:
        ExperimentManifestError: Source admission failed.

    """
    if type(text) is not str:
        _fail("TOML source requires exact str text")
    if len(text) > byte_limit:
        _fail("TOML source exceeds byte limit")
    try:
        encoded_size = len(text.encode("utf-8"))
    except UnicodeEncodeError as error:
        message = "TOML source requires strict UTF-8 text"
        raise ExperimentManifestError(message) from error
    if encoded_size > byte_limit:
        _fail("TOML source exceeds byte limit")


def _parse_document(text: str) -> dict[str, object]:
    _admit_source_text(text, byte_limit=MAX_MANIFEST_BYTES)
    try:
        parsed = cast("object", tomllib.loads(text))
    except tomllib.TOMLDecodeError as error:
        # Only the native parser error has a trusted diagnostic formatter.
        detail = (
            str(error)
            if type(error) is tomllib.TOMLDecodeError
            else type(error).__name__
        )
        raise ExperimentManifestError(f"invalid TOML: {detail}") from error
    except (ValueError, RecursionError) as error:
        message = "invalid TOML exceeds host parser capacity"
        raise ExperimentManifestError(message) from error
    except (TypeError, RuntimeError) as error:
        message = "invalid TOML host parser failure"
        raise ExperimentManifestError(message) from error
    document = _mapping(parsed, "manifest")
    version = document.get("schema_version")
    if type(version) is not int or version != SCHEMA_VERSION:
        _fail(f"unsupported experiment schema: {version}")
    for table_name in CORE_TABLES:
        _ = _table(document, table_name)
    return document


def _experiment_fields(document: dict[str, object]) -> _ExperimentFields:
    table = _table(document, "experiment")
    record_kind = _enum(
        _string(table, "record_kind", "manifest.experiment"),
        RECORD_KINDS,
        "record kind",
    )
    method_class = _enum(
        _string(table, "method_class", "manifest.experiment"),
        METHOD_CLASSES,
        "method class",
    )
    seed = _integer(table, "seed", "manifest.experiment")
    if seed < 0:
        _fail("manifest.experiment.seed must be non-negative")
    return _ExperimentFields(
        identifier=_string(table, "id", "manifest.experiment"),
        method_class=method_class,
        record_kind=record_kind,
        seed=seed,
    )


def _challenge_fields(document: dict[str, object]) -> _ChallengeFields:
    table = _table(document, "challenge")
    difficulty = _integer(table, "difficulty", "manifest.challenge")
    if difficulty <= 0:
        _fail("manifest.challenge.difficulty must be positive")
    profile_id = _string(table, "target_profile", "manifest.challenge")
    return _ChallengeFields(
        difficulty=difficulty,
        family=_string(table, "family", "manifest.challenge"),
        target_profile=profile_id,
        target_profile_fingerprint=_target_profile_fingerprint(
            table,
            profile_id,
        ),
    )


def _target_profile_fingerprint(
    challenge: dict[str, object],
    profile_id: str,
) -> str | None:
    declared = challenge.get("target_profile_fingerprint")
    if profile_id in NONCANONICAL_TARGET_SCOPES:
        return _noncanonical_target_fingerprint(declared)
    return _canonical_target_fingerprint(profile_id, declared)


def _noncanonical_target_fingerprint(declared: object) -> None:
    if declared is not None:
        _fail(NONCANONICAL_FINGERPRINT_ERROR)


def _canonical_target_fingerprint(profile_id: str, declared: object) -> str:
    canonical = target_profile.load_document(target_profile.DEFAULT_PROFILE)
    try:
        observed = target_profile.profile_fingerprint(canonical, profile_id)
    except target_profile.ProfileValidationError:
        _fail(f"unsupported manifest challenge target profile: {profile_id}")
    if type(declared) is not str or not declared:
        _fail(CANONICAL_FINGERPRINT_REQUIRED_ERROR)
    if declared != observed:
        _fail(_profile_fingerprint_mismatch(profile_id, declared, observed))
    return declared


def _profile_fingerprint_mismatch(
    profile_id: str,
    declared: str,
    observed: str,
) -> str:
    return " ".join(
        (
            "MALBOLGE-PROFILE-ID-001",
            f"profile={profile_id}",
            f"expected={declared}",
            f"observed={observed}",
        )
    )


def _provenance_fields(document: dict[str, object]) -> _ProvenanceFields:
    table = _table(document, "provenance")
    return _ProvenanceFields(
        configuration=_relative_path(
            _string(table, "configuration", "manifest.provenance"),
            "manifest.provenance.configuration",
        ),
        implementation=_relative_path(
            _string(table, "implementation", "manifest.provenance"),
            "manifest.provenance.implementation",
        ),
        output=_relative_path(
            _string(table, "output", "manifest.provenance"),
            "manifest.provenance.output",
        ),
    )


def _verification_oracle(document: dict[str, object]) -> str:
    table = _table(document, "verification")
    if not _boolean(table, "required", "manifest.verification"):
        _fail("manifest.verification.required must be true")
    return _string(table, "oracle", "manifest.verification")


def _run_identity(document: dict[str, object]) -> RunIdentity:
    run = _table(document, "run")
    commit = _string(run, "commit", "manifest.run")
    workload_sha256 = _string(run, "workload_sha256", "manifest.run")
    if HEX_40.fullmatch(commit) is None:
        _fail("manifest.run.commit must be a lowercase 40-hex Git commit")
    if HEX_64.fullmatch(workload_sha256) is None:
        _fail("manifest.run.workload_sha256 must be lowercase SHA-256 hex")
    outcome = _enum(
        _string(run, "outcome", "manifest.run"),
        RUN_OUTCOMES,
        "run outcome",
    )
    return RunIdentity(
        accelerator=_string(run, "accelerator", "manifest.run"),
        commit=commit,
        host=_string(run, "host", "manifest.run"),
        outcome=outcome,
        raw_output=_relative_path(
            _string(run, "raw_output", "manifest.run"),
            "manifest.run.raw_output",
        ),
        toolchain=_string(run, "toolchain", "manifest.run"),
        workload_sha256=workload_sha256,
    )


def _optional_run(
    document: dict[str, object],
    record_kind: str,
) -> RunIdentity | None:
    if record_kind == RUN_RECORD_KIND:
        return _run_identity(document)
    if RUN_RECORD_KIND in document:
        _fail("plan experiment manifest must not contain a run table")
    return None


def parse_manifest(text: str) -> ExperimentManifest:
    """Parse and validate the version-one experiment manifest core.

    Returns:
        Immutable validated plan or recorded-run identity.

    """
    document = _parse_document(text)
    experiment = _experiment_fields(document)
    challenge = _challenge_fields(document)
    provenance = _provenance_fields(document)
    budget = _table(document, "budget")
    _positive_budget(budget)
    return ExperimentManifest(
        challenge_family=challenge.family,
        configuration=provenance.configuration,
        difficulty=challenge.difficulty,
        identifier=experiment.identifier,
        implementation=provenance.implementation,
        method_class=experiment.method_class,
        oracle=_verification_oracle(document),
        output=provenance.output,
        record_kind=experiment.record_kind,
        run=_optional_run(document, experiment.record_kind),
        seed=experiment.seed,
        target_profile=challenge.target_profile,
        target_profile_fingerprint=challenge.target_profile_fingerprint,
    )


def _repository_relative(path: Path) -> Path:
    """Preserve physical path components when admitting an in-root manifest.

    Returns:
        Repository-relative path without resolving a symlink alias.

    """
    if PARENT_SEGMENT in path.parts:
        _fail(f"experiment manifest path must not traverse parents: {path}")
    supplied = path if path.is_absolute() else Path.cwd() / path
    try:
        return supplied.relative_to(ROOT)
    except ValueError:
        _fail(f"experiment manifest escapes repository: {path}")


def _validate_repository_identity(
    manifest: ExperimentManifest,
    path: Path,
) -> None:
    directory_ids = {
        directory: identifier
        for identifier, directory in research_algorithm_directories(ROOT)
    }
    algorithm_id = directory_ids.get(path.parent, path.parent.name)
    if manifest.identifier != algorithm_id:
        message = " ".join(
            (
                "experiment ID does not match canonical directory:",
                f"{manifest.identifier} != {algorithm_id}",
            )
        )
        _fail(message)
    expected_implementation = f"algorithms/{algorithm_id}"
    expected_configuration = path.relative_to(ROOT).as_posix()
    expected_output = f"{expected_implementation}/out"
    if manifest.implementation != expected_implementation:
        message = (
            f"manifest provenance implementation mismatch: {manifest.implementation}"
        )
        _fail(message)
    if manifest.configuration != expected_configuration:
        message = (
            f"manifest provenance configuration mismatch: {manifest.configuration}"
        )
        _fail(message)
    if manifest.output != expected_output:
        _fail(f"manifest provenance output mismatch: {manifest.output}")


def _manifest_identity(
    status: os.stat_result,
) -> tuple[int, int, int, int, int]:
    """Require a bounded regular manifest and retain its source identity.

    Returns:
        Device, inode, size, mtime and ctime of the admitted manifest.

    """
    if not S_ISREG(status.st_mode):
        _fail("experiment manifest must be a regular file")
    if status.st_size > MAX_MANIFEST_BYTES:
        _fail("experiment manifest exceeds byte limit")
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _check_manifest_parents(path: Path) -> None:
    """Reject directory aliases before and after manifest admission."""
    for parent in path.parents:
        if parent.is_symlink() or parent.is_junction():
            _fail("experiment manifest path must not redirect")


def _read_manifest_bytes(path: Path) -> bytes:
    """Admit exact regular manifest bytes through one stable descriptor.

    Returns:
        Bounded complete bytes of the unchanged named file.

    """
    _check_manifest_parents(path)
    admitted = path.lstat()
    expected = _manifest_identity(admitted)
    if path.is_symlink() or path.is_junction():
        _fail("experiment manifest path must not redirect")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    descriptor = os.open(path, flags)
    try:
        stream = os.fdopen(descriptor, "rb")
    except BaseException:
        # Ownership transfers only after fdopen succeeds. Preserve the cause.
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
    with stream:
        if _manifest_identity(os.fstat(stream.fileno())) != expected:
            _fail("experiment manifest changed before read")
        raw = stream.read(MAX_MANIFEST_BYTES + 1)
        if (
            len(raw) != admitted.st_size
            or _manifest_identity(os.fstat(stream.fileno())) != expected
            or _manifest_identity(path.lstat()) != expected
        ):
            _fail("experiment manifest changed during read")
    _check_manifest_parents(path)
    return raw


def _read_utf8(path: Path) -> str:
    try:
        raw = _read_manifest_bytes(path)
    except ExperimentManifestError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        # Do not dispatch an untrusted host exception's __str__ method.
        detail = (
            str(error)
            if type(error) in (OSError, ValueError, TypeError, RuntimeError)
            else type(error).__name__
        )
        raise ExperimentManifestError(
            f"experiment manifest cannot be read: {detail}"
        ) from error
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as error:
        _fail(f"invalid experiment manifest UTF-8: {error}")


def validate_repository_manifest(path: Path) -> ExperimentManifest:
    """Validate one checked-in manifest against repository identity.

    Returns:
        Parsed manifest after directory/path identity checks succeed.

    """
    relative = _repository_relative(path)
    canonical_path = ROOT / relative
    try:
        exists = canonical_path.is_file()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        # Exact built-in failures retain detail; subclasses cannot run hooks.
        detail = (
            str(error)
            if type(error) in (OSError, ValueError, TypeError, RuntimeError)
            else type(error).__name__
        )
        raise ExperimentManifestError(
            f"experiment manifest cannot be inspected: {detail}"
        ) from error
    if not exists:
        _fail(f"experiment manifest not found: {relative.as_posix()}")
    manifest = parse_manifest(_read_utf8(canonical_path))
    _validate_repository_identity(manifest, canonical_path)
    return manifest


def validate_repository() -> tuple[ExperimentManifest, ...]:
    """Validate every checked-in research algorithm experiment manifest.

    Returns:
        Manifests in stable algorithm-ID order.

    """
    manifests = tuple(
        validate_repository_manifest(directory / "experiment.toml")
        for _identifier, directory in research_algorithm_directories(ROOT)
    )
    if not manifests:
        _fail("repository contains no experiment manifests")
    return manifests


def main() -> int:
    """Validate checked-in experiment manifests and return process status.

    Returns:
        Zero for valid manifests and one for deterministic policy failure.

    """
    try:
        manifests = validate_repository()
    except (ExperimentManifestError, OSError) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    _ = sys.stdout.write(f"experiment manifests valid: {len(manifests)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
