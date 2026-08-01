# File:
#   - experiment_manifest.py
# Path:
#   - scripts/validate/experiment_manifest.py
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
#   - Validate version-one reproducible research experiment manifests.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - malbolge.json
# - docs/research/methodology/experiment-identity.md
# - docs/technical/compatibility/custom-target-profile-identity.md
# - scripts/validate/target_profile.py
#
# Large file:
#   - false
#

"""Validate version-one reproducible research experiment manifests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
import tomllib
from typing import Never
from typing import cast

from scripts.validate import target_profile

ROOT = Path(__file__).resolve().parents[2]
ALGORITHMS_ROOT = ROOT / "algorithms"
SCHEMA_VERSION = 1
PARENT_SEGMENT = ".."
PLAN_RECORD_KIND = "plan"
RUN_RECORD_KIND = "run"
METHOD_CLASSES = frozenset({
    "benchmarking",
    "engineering",
    "exploratory",
    "mathematical",
    "optimization",
    "replication",
})
RECORD_KINDS = frozenset({PLAN_RECORD_KIND, RUN_RECORD_KIND})
NONCANONICAL_TARGET_SCOPES = frozenset({
    "malbolge-1998-classic-word-domain",
    "multi-profile",
    "profile-independent",
})
NONCANONICAL_FINGERPRINT_ERROR = (
    "manifest.challenge.target_profile_fingerprint must be absent for "
    "noncanonical target scope"
)
CANONICAL_FINGERPRINT_REQUIRED_ERROR = (
    "manifest.challenge.target_profile_fingerprint is required for canonical "
    "target profile"
)
RUN_OUTCOMES = frozenset({
    "candidate-invalid",
    "no-solution",
    "resource-exhausted",
    "success",
    "tool-failure",
})
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
    if not isinstance(value, dict):
        _fail(f"{context} must be a table")
    raw = cast("dict[object, object]", value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            _fail(f"{context} contains a non-string key")
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
    path = Path(value)
    if path.is_absolute() or PARENT_SEGMENT in path.parts:
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


def _parse_document(text: str) -> dict[str, object]:
    try:
        parsed = cast("object", tomllib.loads(text))
    except tomllib.TOMLDecodeError as error:
        _fail(f"invalid TOML: {error}")
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
    return " ".join((
        "MALBOLGE-PROFILE-ID-001",
        f"profile={profile_id}",
        f"expected={declared}",
        f"observed={observed}",
    ))


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
    try:
        return path.resolve().relative_to(ROOT)
    except ValueError:
        _fail(f"experiment manifest escapes repository: {path}")


def _validate_repository_identity(
    manifest: ExperimentManifest,
    algorithm_id: str,
) -> None:
    if manifest.identifier != algorithm_id:
        message = " ".join((
            "experiment ID does not match algorithm directory:",
            f"{manifest.identifier} != {algorithm_id}",
        ))
        _fail(message)
    expected_implementation = f"algorithms/{algorithm_id}"
    expected_configuration = f"{expected_implementation}/experiment.toml"
    expected_output = f"{expected_implementation}/out"
    if manifest.implementation != expected_implementation:
        message = (
            f"manifest provenance implementation mismatch: "
            f"{manifest.implementation}"
        )
        _fail(message)
    if manifest.configuration != expected_configuration:
        message = (
            f"manifest provenance configuration mismatch: "
            f"{manifest.configuration}"
        )
        _fail(message)
    if manifest.output != expected_output:
        _fail(f"manifest provenance output mismatch: {manifest.output}")


def validate_repository_manifest(path: Path) -> ExperimentManifest:
    """Validate one checked-in manifest against repository identity.

    Returns:
        Parsed manifest after directory/path identity checks succeed.

    """
    relative = _repository_relative(path)
    if not path.is_file():
        _fail(f"experiment manifest not found: {relative.as_posix()}")
    manifest = parse_manifest(path.read_text(encoding="utf-8"))
    _validate_repository_identity(manifest, path.parent.name)
    return manifest


def validate_repository() -> tuple[ExperimentManifest, ...]:
    """Validate every checked-in research algorithm experiment manifest.

    Returns:
        Manifests in stable algorithm-ID order.

    """
    manifests = tuple(
        validate_repository_manifest(directory / "experiment.toml")
        for directory in sorted(ALGORITHMS_ROOT.iterdir())
        if (directory / "experiment.toml").is_file()
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
