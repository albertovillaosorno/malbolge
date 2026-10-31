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
#   - Independent read-only admission of retained host-C arena studies.
# - Must-Not:
#   - Measure host performance, execute candidate binaries or certify Malbolge.
# - Allows:
#   - Inputs: bounded ignored local host-C study and optional source replay.
#   - Outputs: checked report over source, raw, run, and binary identities.
#   - Side effects: none by default; optional temporary host-C oracle replay.
# - Split-When:
#   - Target compiler results need an independently attested trust boundary.
# - Merge-When:
#   - All arena studies acquire a governed generic offline audit contract.
# - Summary:
#   - Reopen retained studies without trusting their producer's own checks.
# - Description:
#   - Revalidates trial links, canonical source and binary hashes/byte lengths.
# - Usage:
#   - `python -B -m benchmarks.arena.reference_audit .temp/RUN/study.json`.
# - Defaults:
#   - No native child process or claimed performance verification by default.
#

"""Read-only offline audit of retained real host-C reference studies."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from dataclasses import dataclass
from hashlib import sha256
from itertools import starmap
from pathlib import Path
from typing import Any, Never

from benchmarks.arena import (
    analyze,
    evidence,
    host_c_oracle,
    reference_study,
    report_output,
)
from benchmarks.challenges import generate
from scripts.validate import experiment_manifest

_ROOT = Path(__file__).resolve().parents[2]
MAX_ARTIFACT_INDEX_BYTES = 1024 * 1024
PART_COUNT = 3
ROOT_PART = ".temp"
GIT_COMMIT_TYPE = b"commit"
UNDERSCORE = "_"
STUDY_LEAF = "study.json"
ARTIFACT_LEAF = "artifacts.json"
FAILURES_LEAF = "failures.json"
RESOURCE_CONTROLS_LEAF = "resource-controls.json"
MAX_RESOURCE_CONTROLS_BYTES = 4096
MAX_FAILURES_BYTES = 64 * 1024
RUN_PREFIX = "arena-host-c-study-"
STAGE = "host-c-reference-not-malbolge"
TOOLCHAIN = "repo-pinned-clang-22.1.8"
PRODUCER_IMPLEMENTATION = "benchmarks/arena/reference_study.py"
PRODUCER_CONFIGURATION = "benchmarks/arena/README.md"
PRODUCER_METHOD_CLASS = "benchmarking"
PRODUCER_ACCELERATOR = "none"
PRODUCER_RESEARCH_CLAIMS = {
    "question": "Does Clang O2 reduce time or code size vs O0?",
    "hypothesis": "O2 improves verified time/size frontier on C.",
    "rejection_observation": "O2 is dominated by O0 at all difficulties.",
}
REQUIRED_OBJECTIVES = ["elapsed_ns", "artifact_bytes"]
CURRENT_OBJECTIVES = [*REQUIRED_OBJECTIVES, "peak_rss_bytes"]
RSS_RESOURCE_POLICY_VERSION = 2
REQUIRED_ALGORITHMS = frozenset(
    {
        reference_study.BASELINE,
        reference_study.CANDIDATE,
    }
)


@dataclass(frozen=True, slots=True)
class AuditOptions:
    """Optional admission and replay gates for retained host-C evidence."""

    replay_oracles: bool = False
    rebuild_binaries: bool = False
    require_source_commit_object: bool = False
    require_resource_controls_record: bool = False


@dataclass(frozen=True, slots=True)
class _AuditData:
    document: dict[str, Any]
    checked: dict[str, Any]
    artifacts: dict[str, dict[str, str]]
    verified_binaries: int
    failed_diagnostics: int
    commit: str
    resource_record_version: int
    manifest_fingerprints: dict[str, bytes]
    sidecar_fingerprints: dict[str, bytes | None]
    evidence_snapshot: evidence.EvidenceSnapshot
    study_fingerprint: bytes


DEFAULT_AUDIT_OPTIONS = AuditOptions()


class ReferenceAuditError(ValueError):
    """Retained host-C research evidence is not independently consistent."""


def _fail(message: str) -> Never:
    raise ReferenceAuditError(message)


def _safe_error_detail(error: Exception) -> str:
    """Keep exact project/native errors readable without foreign formatter hooks.

    Returns:
        Trusted diagnostic text, otherwise the foreign exception type name.

    """
    if type(error) in (
        ReferenceAuditError,
        report_output.ReportOutputError,
        analyze.ArenaError,
        evidence.EvidenceError,
        reference_study.ReferenceStudyError,
        host_c_oracle.HostOracleError,
        experiment_manifest.ExperimentManifestError,
        OSError,
        PermissionError,
        FileNotFoundError,
        ValueError,
        TypeError,
        UnicodeError,
        UnicodeDecodeError,
    ):
        # Exact native exception types can still carry caller-owned arguments.
        # Never let their default __str__ format a foreign object.
        arguments = error.args
        if len(arguments) == 1 and type(arguments[0]) is str:
            return arguments[0]
        if (
            type(error) in (OSError, PermissionError, FileNotFoundError)
            and len(arguments) == 2
            and type(arguments[0]) is int
            and type(arguments[1]) is str
        ):
            return f"{type(error).__name__}: [Errno {arguments[0]}] {arguments[1]}"
    return type(error).__name__


def _admit_options(options: AuditOptions) -> None:
    """Require precise opt-ins before any input reads or native child work."""
    if type(options) is not AuditOptions or any(
        type(value) is not bool
        for value in (
            options.replay_oracles,
            options.rebuild_binaries,
            options.require_source_commit_object,
            options.require_resource_controls_record,
        )
    ):
        _fail("host-C audit options require exact booleans")


def _prefix(relative: str) -> str:
    if type(relative) is not str:
        _fail("host-C audit requires a canonical ignored study path")
    parts = relative.split("/")
    if len(parts) != PART_COUNT or parts[0] != ROOT_PART or parts[2] != STUDY_LEAF:
        _fail("host-C audit requires .temp/arena-host-c-study-*/study.json")
    directory = parts[1]
    suffix = directory.removeprefix(RUN_PREFIX)
    if not directory.startswith(RUN_PREFIX) or not suffix:
        _fail("host-C audit requires a generated host-C study directory")
    if not suffix.isascii() or not all(
        char.isalnum() or char == UNDERSCORE for char in suffix
    ):
        _fail("host-C audit requires a canonical local study directory")
    return "/".join(parts[:2])


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            _fail(f"host-C retained JSON has duplicate field: {name}")
        result[name] = value
    return result


def _reject_nonfinite(value: str) -> Never:
    _fail(f"host-C retained JSON has nonfinite number: {value}")


def _read_bounded_evidence(relative: str, *, limit: int) -> bytes:
    """Admit exact bounded native reader bytes before hashing or interpretation."""
    raw = evidence.read_bounded_regular(_ROOT, relative, limit=limit)
    if type(raw) is not bytes or len(raw) > limit:
        _fail(f"host-C retained evidence requires exact bounded bytes: {relative}")
    return raw


def _read_json(
    relative: str, *, limit: int, fingerprints: dict[str, bytes | None]
) -> object:
    raw = _read_bounded_evidence(relative, limit=limit)
    try:
        parsed = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_nonfinite,
        )
    except ReferenceAuditError:
        raise
    except Exception as error:
        # Any ordinary JSON dependency fault remains a typed admission failure.
        message = f"host-C retained JSON is not valid: {relative}"
        raise ReferenceAuditError(message) from error
    fingerprints[relative] = sha256(raw).digest()
    return parsed


def _load_study(relative: str) -> tuple[dict[str, Any], bytes]:
    raw = _read_bounded_evidence(
        relative,
        limit=analyze.MAX_INPUT_BYTES,
    )
    return analyze.parse_document(raw.decode("utf-8")), sha256(raw).digest()


def _check_trials(
    document: dict[str, Any],
    prefix: str,
) -> None:
    observations = document["observations"]
    if {row["algorithm"] for row in observations} != REQUIRED_ALGORITHMS:
        _fail("host-C reference audit requires both recorded Clang arms")
    for row in observations:
        if row["verifier"] != reference_study.VERIFIER:
            _fail("host-C reference audit requires native C entry oracle")
        case = row["case"]
        name = f"{row['algorithm']}-nodes-{case['difficulty']}-trial-{row['trial']}"
        if (
            row["experiment_manifest"] != f"{prefix}/runs/{name}.toml"
            or row["raw_sample"] != f"{prefix}/raw/{name}.csv"
        ):
            _fail("host-C reference audit trial paths differ from native producer")


def _check_plan_trials(rows: list[dict[str, Any]]) -> None:
    trials = {row["trial"] for row in rows}
    if not 1 <= len(trials) <= reference_study.MAX_TRIALS:
        _fail("host-C audit contains too many trial repetitions")
    if trials != set(range(len(trials))):
        _fail("host-C audit requires consecutive trial repetition indices")
    # The native producer applies one repetition count to every difficulty.
    # Per-difficulty paired cohorts alone do not establish that invariant.
    by_difficulty: dict[int, set[int]] = {}
    for row in rows:
        difficulty = row["case"]["difficulty"]
        by_difficulty.setdefault(difficulty, set()).add(row["trial"])
    if any(level_trials != trials for level_trials in by_difficulty.values()):
        _fail("host-C audit requires the same trials at every difficulty")


def _check_case_plan(document: dict[str, Any]) -> None:
    rows = document["observations"]
    families = {row["case"]["family"] for row in rows}
    seeds = {row["case"]["seed"] for row in rows}
    difficulties = {row["case"]["difficulty"] for row in rows}
    if len(families) != 1 or len(seeds) != 1:
        _fail("host-C audit requires one generated family and seed")
    if not 1 <= len(difficulties) <= reference_study.MAX_DIFFICULTIES:
        _fail("host-C audit contains too many challenge difficulty levels")
    if max(difficulties) > reference_study.host_c_oracle.MAX_REPLAY_NODES:
        _fail("host-C audit exceeds the source runner challenge limit")
    family = next(iter(families))
    seed = next(iter(seeds))
    if document["study"]["id"] != f"host-C-reference-{family}-seed-{seed}":
        _fail("host-C reference audit study identity differs from source")
    _check_plan_trials(rows)


def _check_stage(document: dict[str, Any], prefix: str) -> None:
    study = document["study"]
    if study["stage"] != STAGE or study["target_profile"] != reference_study.PROFILE:
        _fail("host-C reference audit stage or target profile differs")
    if any(
        study[field] != expected for field, expected in PRODUCER_RESEARCH_CLAIMS.items()
    ):
        _fail("host-C reference producer research claims differ")
    if (
        study["baseline"] != reference_study.BASELINE
        or study["toolchain"] != TOOLCHAIN
        or study["objectives"] not in (REQUIRED_OBJECTIVES, CURRENT_OBJECTIVES)
    ):
        _fail("host-C reference audit configured arms or objectives differ")
    expected_budget = {
        "time_ns": reference_study.BUDGET_SECONDS * 1_000_000_000,
        "memory_bytes": reference_study.BUDGET_MEMORY_MIB * 1_048_576,
    }
    if study["budget"] != expected_budget:
        _fail("host-C reference audit budgets differ from source runner")
    _check_trials(document, prefix)
    _check_case_plan(document)


def _index_entry(name: object, item: object) -> tuple[str, dict[str, str]]:
    if (
        type(name) is not str
        or type(item) is not dict
        or any(type(key) is not str for key in item)
    ):
        _fail("host-C artifact index has invalid trial entries")
    if set(item) != {"path", "sha256"}:
        _fail("host-C artifact index requires exact identity fields")
    path, digest = item["path"], item["sha256"]
    if type(path) is not str or type(digest) is not str:
        _fail("host-C artifact index requires string identity fields")
    return name, {"path": path, "sha256": digest}


def _check_artifact_index(
    source: object,
    document: dict[str, Any],
) -> dict[str, dict[str, str]]:
    if type(source) is not dict or any(type(key) is not str for key in source):
        _fail("host-C artifact index must be a native JSON map")
    if len(source) > len(document["observations"]):
        _fail("host-C artifact index contains extra entries")
    return dict(starmap(_index_entry, source.items()))


def _check_trial_file_inventory(
    document: dict[str, Any],
    artifacts: dict[str, dict[str, str]],
    prefix: str,
) -> None:
    """Reject undeclared trial files rather than ignoring foreign local data."""
    expected: dict[str, set[str]] = {
        "runs": {
            row["experiment_manifest"].rsplit("/", maxsplit=1)[1]
            for row in document["observations"]
        },
        "raw": {
            row["raw_sample"].rsplit("/", maxsplit=1)[1]
            for row in document["observations"]
        },
        "candidates": {
            value["path"].rsplit("/", maxsplit=1)[1] for value in artifacts.values()
        },
    }
    for folder, names in expected.items():
        directory = _ROOT / prefix / folder
        if directory.is_symlink() or not directory.is_dir():
            _fail(f"host-C trial file inventory directory invalid: {folder}")
        observed: set[str] = set()
        for entry in directory.iterdir():
            if entry.name not in names:
                _fail(f"unregistered host-C trial file in {folder}: {entry.name}")
            observed.add(entry.name)
        if observed != names:
            _fail(f"host-C trial file inventory missing entries in {folder}")


def _recorded_source_commit(
    document: dict[str, Any],
    *,
    require_git_object: bool,
) -> tuple[str, dict[str, bytes]]:
    commits: set[str] = set()
    fingerprints: dict[str, bytes] = {}
    paths = {row["experiment_manifest"] for row in document["observations"]}
    for relative in sorted(paths):
        data = _read_bounded_evidence(
            relative,
            limit=evidence.MAX_MANIFEST_BYTES,
        )
        fingerprints[relative] = sha256(data).digest()
        manifest = experiment_manifest.parse_manifest(data.decode("utf-8"))
        if manifest.run is None:
            _fail("host-C audit source commit requires a recorded run")
        if (
            manifest.implementation != PRODUCER_IMPLEMENTATION
            or manifest.configuration != PRODUCER_CONFIGURATION
            or manifest.method_class != PRODUCER_METHOD_CLASS
            or manifest.output != relative.rsplit("/runs/", maxsplit=1)[0]
            or manifest.run.accelerator != PRODUCER_ACCELERATOR
        ):
            _fail("host-C run manifest producer provenance differs")
        commits.add(manifest.run.commit)
    if len(commits) != 1:
        _fail("host-C study run manifests disagree on source commit")
    commit = next(iter(commits))
    if require_git_object:
        _require_git_commit(commit)
    return commit, fingerprints


def _require_unchanged_manifests(fingerprints: dict[str, bytes]) -> None:
    """Reject retained run-manifest drift across a host-C audit pass."""
    for relative, fingerprint in sorted(fingerprints.items()):
        data = _read_bounded_evidence(relative, limit=evidence.MAX_MANIFEST_BYTES)
        if sha256(data).digest() != fingerprint:
            _fail("host-C run manifest changed during audit")


def _require_unchanged_sidecars(
    prefix: str, fingerprints: dict[str, bytes | None]
) -> None:
    """Bind optional and required receipts to their originally parsed bytes."""
    for leaf, limit in (
        (ARTIFACT_LEAF, MAX_ARTIFACT_INDEX_BYTES),
        (FAILURES_LEAF, MAX_FAILURES_BYTES),
        (RESOURCE_CONTROLS_LEAF, MAX_RESOURCE_CONTROLS_BYTES),
    ):
        relative = f"{prefix}/{leaf}"
        if relative not in fingerprints:
            _fail("host-C audit missing admitted sidecar identity")
        original = fingerprints[relative]
        if original is None:
            try:
                (_ROOT / relative).lstat()
            except FileNotFoundError:
                continue
            except Exception as error:
                message = f"host-C retained sidecar changed during audit: {relative}"
                raise ReferenceAuditError(message) from error
            _fail(f"host-C retained sidecar changed during audit: {relative}")
        try:
            current = _read_bounded_evidence(relative, limit=limit)
        except Exception as error:
            # An unanticipated bounded-reader fault must not leak as a raw
            # exception or invoke foreign exception diagnostic hooks.
            message = f"host-C retained sidecar changed during audit: {relative}"
            raise ReferenceAuditError(message) from error
        if sha256(current).digest() != original:
            _fail(f"host-C retained sidecar changed during audit: {relative}")


def _require_git_commit(commit: str) -> None:
    try:
        executable = shutil.which("git", path=os.defpath)
    except Exception as error:
        # Unexpected ordinary resolver faults remain typed provenance errors.
        message = "host-C source commit Git lookup failed"
        raise ReferenceAuditError(message) from error
    if executable is None:
        _fail("host-C source commit admission requires local Git")
    if (
        type(executable) is not str
        or not executable
        or "\0" in executable
        or not Path(executable).is_absolute()
    ):
        _fail("host-C source commit admission requires absolute Git executable")
    try:
        _ = os.fsencode(executable)
    except UnicodeError as error:
        message = "host-C source commit admission requires encodable Git executable"
        raise ReferenceAuditError(message) from error
    try:
        mode = Path(executable).lstat().st_mode
        is_executable = os.access(executable, os.X_OK)
    except Exception as error:
        # Do not allow a substituted host inspector to escape this boundary.
        message = "host-C source commit Git path inspection failed"
        raise ReferenceAuditError(message) from error
    if not stat.S_ISREG(mode) or not is_executable:
        _fail("host-C source commit requires physical executable Git")
    # Foreign GIT_DIR and object alternates cannot satisfy local admission.
    try:
        clean_env = {
            name: value for name, value in os.environ.items() if not name.startswith("GIT_")
        }
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [executable, "cat-file", "-t", commit],
            cwd=_ROOT,
            stdin=sp.DEVNULL,
            env=clean_env,
            check=False,
            shell=False,
            capture_output=True,
            timeout=5,
        )
        returncode = getattr(completed, "returncode", None)
        stdout = getattr(completed, "stdout", None)
    except Exception as error:
        # Include clean environment capture and foreign receipt accessors.
        message = "host-C source commit object lookup failed"
        raise ReferenceAuditError(message) from error
    if (
        type(returncode) is not int
        or returncode != 0
        or type(stdout) is not bytes
        or stdout.strip() != GIT_COMMIT_TYPE
    ):
        _fail("host-C recorded source commit is not a local Git commit object")


def _valid_failure_version(version: object) -> bool:
    return type(version) is int and version == 1


def _check_retained_failures(
    document: dict[str, Any],
    prefix: str,
    fingerprints: dict[str, bytes | None],
) -> int:
    relative = f"{prefix}/{FAILURES_LEAF}"
    path = _ROOT / relative
    has_failure = any(
        row["outcome"] == reference_study.FAILED_OUTCOME
        for row in document["observations"]
    )
    if not path.exists() and not path.is_symlink():
        if has_failure:
            _fail("host-C reference failure details file is missing")
        fingerprints[relative] = None
        return 0  # Pre-extension all-success pilot is still admissible.
    source = _read_json(relative, limit=MAX_FAILURES_BYTES, fingerprints=fingerprints)
    if (
        not isinstance(source, dict)
        or set(source) != {"schema_version", "failures"}
        or not _valid_failure_version(source["schema_version"])
    ):
        _fail("host-C reference failure file has invalid schema")
    failures = source["failures"]
    if not isinstance(failures, dict) or any(
        type(key) is not str or type(value) is not str
        for key, value in failures.items()
    ):
        _fail("host-C reference failure index has invalid data")
    return reference_study.check_retained_failures(document, failures)


def _expected_resource_policy(version: int) -> dict[str, str | int]:
    expected = host_c_oracle.resource_controls_record()
    if version == 1:
        expected = {
            key: value
            for key, value in expected.items()
            if key not in {"rss_measurement", "rss_tool"}
        }
        expected["schema_version"] = 1
    return expected


def _validate_resource_policy_fields(
    recorded: dict[str, Any],
    version: int,
) -> None:
    expected = _expected_resource_policy(version)
    if set(recorded) != set(expected):
        _fail("host-C reference child resource-control policy differs")
    if any(
        type(recorded[name]) is not type(value) or recorded[name] != value
        for name, value in expected.items()
    ):
        _fail("host-C reference child resource-control policy differs")


def _check_resource_controls(
    prefix: str,
    *,
    required: bool,
    fingerprints: dict[str, bytes | None],
) -> int:
    relative = f"{prefix}/{RESOURCE_CONTROLS_LEAF}"
    path = _ROOT / relative
    if not path.exists() and not path.is_symlink():
        if required:
            _fail("host-C reference resource-control record is missing")
        fingerprints[relative] = None
        return 0  # Legacy measurements predate controlled child launches.
    recorded = _read_json(
        relative, limit=MAX_RESOURCE_CONTROLS_BYTES, fingerprints=fingerprints
    )
    if not isinstance(recorded, dict):
        _fail("host-C reference child resource-control policy differs")
    version = recorded.get("schema_version")
    if type(version) is not int or version not in {1, 2}:
        _fail("host-C reference child resource-control version invalid")
    _validate_resource_policy_fields(recorded, version)
    return version


def _admit_data(
    relative_study: str,
    prefix: str,
    options: AuditOptions,
) -> _AuditData:
    document, study_fingerprint = _load_study(relative_study)
    _check_stage(document, prefix)
    # Bind the reported source revision to the same retained manifest bytes
    # admitted by the subsequent independent link preflight.
    commit, manifest_fingerprints = _recorded_source_commit(
        document,
        require_git_object=options.require_source_commit_object,
    )
    snapshots: list[evidence.EvidenceSnapshot] = []
    checked = evidence.validate_links(
        document,
        _ROOT,
        policy=evidence.EvidencePolicy(
            require_trial_run_identity=True,
            require_budget_agreement=True,
            challenge_root=f"{prefix}/bundles",
            require_host_c_challenge_oracle=options.replay_oracles,
        ),
        _snapshot_out=snapshots,
    )
    if len(snapshots) != 1:
        _fail("host-C audit did not retain its linked evidence snapshot")
    sidecar_fingerprints: dict[str, bytes | None] = {}
    artifacts = _check_artifact_index(
        _read_json(
            f"{prefix}/{ARTIFACT_LEAF}",
            limit=MAX_ARTIFACT_INDEX_BYTES,
            fingerprints=sidecar_fingerprints,
        ),
        document,
    )
    verified_binaries = reference_study.check_retained_artifacts(
        document,
        artifacts,
    )
    _check_trial_file_inventory(document, artifacts, prefix)
    failed_diagnostics = _check_retained_failures(
        document, prefix, sidecar_fingerprints
    )
    resource_record = _check_resource_controls(
        prefix,
        required=options.require_resource_controls_record,
        fingerprints=sidecar_fingerprints,
    )
    if (
        document["study"]["objectives"] == CURRENT_OBJECTIVES
        and resource_record != RSS_RESOURCE_POLICY_VERSION
    ):
        _fail("host-C peak-RSS study requires v2 resource-control record")
    return _AuditData(
        document,
        checked,
        artifacts,
        verified_binaries,
        failed_diagnostics,
        commit,
        resource_record,
        manifest_fingerprints,
        sidecar_fingerprints,
        snapshots[0],
        study_fingerprint,
    )


def _rebuild_reference_binaries(
    document: dict[str, Any],
    artifacts: dict[str, dict[str, str]],
) -> int:
    built: dict[tuple[str, int, int, int, str], bytes] = {}
    for row in document["observations"]:
        if row["outcome"] != analyze.VERIFIED:
            continue
        case = row["case"]
        mode = "-O0" if row["algorithm"] == reference_study.BASELINE else "-O2"
        key = (
            case["family"],
            case["version"],
            case["seed"],
            case["difficulty"],
            mode,
        )
        if key not in built:
            identity = generate.ChallengeIdentity(
                family=case["family"],
                version=case["version"],
                seed=case["seed"],
                nodes=case["difficulty"],
                profile=reference_study.PROFILE,
            )
            built[key] = host_c_oracle.rebuild_reference(identity, mode)
        retained = _read_bounded_evidence(
            artifacts[row["experiment_manifest"]]["path"],
            limit=reference_study.MAX_ARTIFACT_BYTES,
        )
        if built[key] != retained:
            _fail("host-C retained binary differs from canonical rebuilt C")
    return len(built)


def audit(
    relative_study: str,
    *,
    options: AuditOptions = DEFAULT_AUDIT_OPTIONS,
) -> dict[str, Any]:
    """Reopen and validate all retained host-C reference evidence.

    The optional independent source oracle check only compiles regenerated
    canonical C; rebuild mode compiles a new reference without executing the
    retained trial binary or pretending to reproduce its recorded elapsed time.

    Returns:
        Audited source counts, checked artifact count, and offline arena report.

    Raises:
        ReferenceAuditError: Evidence is absent, malformed, or inconsistent.

    """
    _admit_options(options)
    prefix = _prefix(relative_study)
    try:
        data = _admit_data(relative_study, prefix, options)
        rebuilt = (
            _rebuild_reference_binaries(data.document, data.artifacts)
            if options.rebuild_binaries
            else 0
        )
        report = analyze.analyze(data.document)
        # Unlike a fresh preflight, this compares the originally admitted
        # raw and bundle bytes without repeating optional native replay.
        evidence.recheck_evidence_snapshot(data.evidence_snapshot)
        _require_unchanged_manifests(data.manifest_fingerprints)
        _require_unchanged_sidecars(prefix, data.sidecar_fingerprints)
        current = _read_bounded_evidence(relative_study, limit=analyze.MAX_INPUT_BYTES)
        if sha256(current).digest() != data.study_fingerprint:
            _fail("host-C retained study JSON changed during audit")
        # Recheck original native binary claims after any optional rebuild or
        # oracle replay. The preflight may have admitted bytes that are no
        # longer present when this report is returned.
        if (
            reference_study.check_retained_artifacts(data.document, data.artifacts)
            != data.verified_binaries
        ):
            _fail("host-C retained artifact count changed during audit")
        _check_trial_file_inventory(data.document, data.artifacts, prefix)
    except ReferenceAuditError:
        # Local typed evidence rejections already contain the right diagnostic.
        raise
    except Exception as error:
        # Dependency faults must remain typed and safe to render at the CLI.
        message = f"host-C reference evidence audit failed: {_safe_error_detail(error)}"
        raise ReferenceAuditError(message) from error
    return {
        "schema_version": 1,
        "scope": (
            "Retained source-reported host-C reference evidence consistent; "
            "no Malbolge candidate execution, measurement replay, "
            "or physical budget attestation."
        ),
        "study": relative_study,
        "host_c_binaries_checked": data.verified_binaries,
        "host_c_failure_diagnostics_checked": data.failed_diagnostics,
        "recorded_source_commit": data.commit,
        "source_commit_object_verified": options.require_source_commit_object,
        "resource_controls_record_checked": data.resource_record_version > 0,
        "resource_controls_record_version": data.resource_record_version,
        "host_c_oracle_replayed": options.replay_oracles,
        "host_c_reference_builds_reproduced": rebuilt,
        "evidence_preflight": data.checked,
        "capacity_curve": report["capacity_curve"],
        "pareto_frontiers": report["pareto_frontiers"],
    }


def main() -> int:
    """Audit a retained local host-C study without modifying its files.

    Returns:
        Zero with a checked JSON audit report or two on admission failure.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", help=".temp/arena-host-c-study-*/study.json")
    parser.add_argument("--replay-oracles", action="store_true")
    parser.add_argument("--rebuild-binaries", action="store_true")
    parser.add_argument("--require-source-commit-object", action="store_true")
    parser.add_argument("--require-resource-controls-record", action="store_true")
    args = parser.parse_args()
    try:
        report = audit(
            args.study,
            options=AuditOptions(
                replay_oracles=args.replay_oracles,
                rebuild_binaries=args.rebuild_binaries,
                require_source_commit_object=args.require_source_commit_object,
                require_resource_controls_record=args.require_resource_controls_record,
            ),
        )
        report_output.publish(report, sys.stdout)
    except (ReferenceAuditError, report_output.ReportOutputError) as error:
        parser.exit(2, f"host-C reference audit: {_safe_error_detail(error)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
