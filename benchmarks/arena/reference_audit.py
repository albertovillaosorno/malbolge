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
from dataclasses import dataclass
from itertools import starmap
import json
from pathlib import Path
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import Any
from typing import Never

from scripts.validate import experiment_manifest

from benchmarks.arena import analyze
from benchmarks.arena import evidence
from benchmarks.arena import host_c_oracle
from benchmarks.arena import reference_study
from benchmarks.arena import report_output
from benchmarks.challenges import generate

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
REQUIRED_OBJECTIVES = ["elapsed_ns", "artifact_bytes"]
REQUIRED_ALGORITHMS = frozenset({
    reference_study.BASELINE,
    reference_study.CANDIDATE,
})


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
    resource_record: bool


DEFAULT_AUDIT_OPTIONS = AuditOptions()


class ReferenceAuditError(ValueError):
    """Retained host-C research evidence is not independently consistent."""


def _fail(message: str) -> Never:
    raise ReferenceAuditError(message)


def _prefix(relative: str) -> str:
    if type(relative) is not str:
        _fail("host-C audit requires a canonical ignored study path")
    parts = relative.split("/")
    if (
        len(parts) != PART_COUNT
        or parts[0] != ROOT_PART
        or parts[2] != STUDY_LEAF
    ):
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


def _read_json(relative: str, *, limit: int) -> object:
    raw = evidence.read_bounded_regular(_ROOT, relative, limit=limit)
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        message = f"host-C retained JSON is not valid: {relative}"
        raise ReferenceAuditError(message) from error


def _load_study(relative: str) -> dict[str, Any]:
    raw = evidence.read_bounded_regular(
        _ROOT,
        relative,
        limit=analyze.MAX_INPUT_BYTES,
    )
    return analyze.parse_document(raw.decode("utf-8"))


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
        if not (
            row["experiment_manifest"].startswith(f"{prefix}/runs/")
            and row["raw_sample"].startswith(f"{prefix}/raw/")
        ):
            _fail("host-C reference audit trial identity escapes its study")


def _check_plan_trials(rows: list[dict[str, Any]]) -> None:
    trials = {row["trial"] for row in rows}
    if not 1 <= len(trials) <= reference_study.MAX_TRIALS:
        _fail("host-C audit contains too many trial repetitions")
    if trials != set(range(len(trials))):
        _fail("host-C audit requires consecutive trial repetition indices")


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
    if (
        study["stage"] != STAGE
        or study["target_profile"] != reference_study.PROFILE
    ):
        _fail("host-C reference audit stage or target profile differs")
    if (
        study["baseline"] != reference_study.BASELINE
        or study["toolchain"] != TOOLCHAIN
        or study["objectives"] != REQUIRED_OBJECTIVES
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
    if type(name) is not str or not isinstance(item, dict):
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
    if not isinstance(source, dict):
        _fail("host-C artifact index must be a map")
    if len(source) > len(document["observations"]):
        _fail("host-C artifact index contains extra entries")
    return dict(starmap(_index_entry, source.items()))


def _recorded_source_commit(
    document: dict[str, Any],
    *,
    require_git_object: bool,
) -> str:
    commits: set[str] = set()
    paths = {row["experiment_manifest"] for row in document["observations"]}
    for relative in sorted(paths):
        data = evidence.read_bounded_regular(
            _ROOT,
            relative,
            limit=evidence.MAX_MANIFEST_BYTES,
        )
        manifest = experiment_manifest.parse_manifest(data.decode("utf-8"))
        if manifest.run is None:
            _fail("host-C audit source commit requires a recorded run")
        commits.add(manifest.run.commit)
    if len(commits) != 1:
        _fail("host-C study run manifests disagree on source commit")
    commit = next(iter(commits))
    if require_git_object:
        _require_git_commit(commit)
    return commit


def _require_git_commit(commit: str) -> None:
    executable = shutil.which("git")
    if executable is None:
        _fail("host-C source commit admission requires local Git")
    try:
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [executable, "cat-file", "-t", commit],
            cwd=_ROOT,
            check=False,
            shell=False,
            capture_output=True,
            timeout=5,
        )
    except (OSError, sp.TimeoutExpired) as error:
        message = "host-C source commit object lookup failed"
        raise ReferenceAuditError(message) from error
    if completed.returncode != 0 or completed.stdout.strip() != GIT_COMMIT_TYPE:
        _fail("host-C recorded source commit is not a local Git commit object")


def _valid_failure_version(version: object) -> bool:
    return type(version) is int and version == 1


def _check_retained_failures(
    document: dict[str, Any],
    prefix: str,
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
        return 0  # Pre-extension all-success pilot is still admissible.
    source = _read_json(relative, limit=MAX_FAILURES_BYTES)
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


def _check_resource_controls(
    prefix: str,
    *,
    required: bool,
) -> bool:
    relative = f"{prefix}/{RESOURCE_CONTROLS_LEAF}"
    path = _ROOT / relative
    if not path.exists() and not path.is_symlink():
        if required:
            _fail("host-C reference resource-control record is missing")
        return False  # Legacy measurements predate controlled child launches.
    recorded = _read_json(relative, limit=MAX_RESOURCE_CONTROLS_BYTES)
    expected = host_c_oracle.resource_controls_record()
    if not isinstance(recorded, dict) or set(recorded) != set(expected):
        _fail("host-C reference child resource-control policy differs")
    if any(
        type(recorded[name]) is not type(value) or recorded[name] != value
        for name, value in expected.items()
    ):
        _fail("host-C reference child resource-control policy differs")
    return True


def _admit_data(
    relative_study: str,
    prefix: str,
    options: AuditOptions,
) -> _AuditData:
    document = _load_study(relative_study)
    _check_stage(document, prefix)
    checked = evidence.validate_links(
        document,
        _ROOT,
        policy=evidence.EvidencePolicy(
            require_trial_run_identity=True,
            require_budget_agreement=True,
            challenge_root=f"{prefix}/bundles",
            require_host_c_challenge_oracle=options.replay_oracles,
        ),
    )
    commit = _recorded_source_commit(
        document,
        require_git_object=options.require_source_commit_object,
    )
    artifacts = _check_artifact_index(
        _read_json(
            f"{prefix}/{ARTIFACT_LEAF}",
            limit=MAX_ARTIFACT_INDEX_BYTES,
        ),
        document,
    )
    verified_binaries = reference_study.check_retained_artifacts(
        document,
        artifacts,
    )
    failed_diagnostics = _check_retained_failures(document, prefix)
    resource_record = _check_resource_controls(
        prefix,
        required=options.require_resource_controls_record,
    )
    return _AuditData(
        document,
        checked,
        artifacts,
        verified_binaries,
        failed_diagnostics,
        commit,
        resource_record,
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
        retained = evidence.read_bounded_regular(
            _ROOT,
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
    prefix = _prefix(relative_study)
    try:
        data = _admit_data(relative_study, prefix, options)
        rebuilt = (
            _rebuild_reference_binaries(data.document, data.artifacts)
            if options.rebuild_binaries
            else 0
        )
        report = analyze.analyze(data.document)
    except (
        analyze.ArenaError,
        evidence.EvidenceError,
        reference_study.ReferenceStudyError,
        host_c_oracle.HostOracleError,
        experiment_manifest.ExperimentManifestError,
        OSError,
        UnicodeError,
    ) as error:
        message = f"host-C reference evidence audit failed: {error}"
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
        "resource_controls_record_checked": data.resource_record,
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
    parser.add_argument(
        "--require-resource-controls-record", action="store_true"
    )
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
        parser.exit(2, f"host-C reference audit: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
