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
#   - Optional run-manifest and retained-path identity preflight for arena.
# - Must-Not:
#   - Treat checked paths as certified measurements or independent verification.
# - Allows:
#   - Inputs: admitted arena JSON and repository-local manifest/raw paths.
#   - Outputs: identity cross-check summary and offline capacity analysis.
#   - Side effects: read declared repository-local regular files.
# - Split-When:
#   - Verifier replay or content-digest admission gains an owned lifecycle.
# - Merge-When:
#   - The experiment manifest validator owns these cross-record obligations.
# - Summary:
#   - Binds reported trial metadata to existing manifest parser authority.
# - Description:
#   - Checks linked run identity without certifying the reported trial outcome.
# - Usage:
#   - `python -B -m benchmarks.arena.evidence study.json --root .`.
# - Defaults:
#   - Missing, inconsistent, external, or linked files fail closed.
#

"""Cross-check arena observations against repository experiment run records."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import stat
import sys
from typing import Any
from typing import Never

from scripts.validate import experiment_manifest

from benchmarks.arena import analyze
from benchmarks.arena import budget_links
from benchmarks.arena import challenge_bundles
from benchmarks.arena import raw_samples
from benchmarks.arena import trial_runs

MAX_MANIFEST_BYTES = 1 * 1024 * 1024
RUN_RECORD_KIND = experiment_manifest.RUN_RECORD_KIND
RUN_OUTCOMES = {
    "verified": "success",
    "verifier_rejected": "candidate-invalid",
    "no_solution": "no-solution",
    "resource_exhausted": "resource-exhausted",
    "tool_failed": "tool-failure",
}


class EvidenceError(ValueError):
    """Missing or inconsistent reported research evidence link."""


def _fail(message: str) -> Never:
    raise EvidenceError(message)


def _segments(relative: str) -> list[str]:
    if not isinstance(relative, str) or not relative:
        _fail("evidence requires a canonical relative path")
    if relative.startswith(("/", analyze.BACKSLASH)):
        _fail("evidence requires a canonical relative path")
    if (
        analyze.BACKSLASH in relative
        or analyze.COLON in relative
        or analyze.NUL in relative
    ):
        _fail("evidence requires a canonical relative path")
    parts = relative.split("/")
    if any(
        part in {"", analyze.CURRENT_DIR, analyze.PARENT_DIR} for part in parts
    ):
        _fail("evidence requires a canonical relative path")
    return parts


def regular_path(
    root: Path,
    relative: str,
    *,
    limit: int | None = None,
) -> Path:
    """Admit only an existing nonempty ordinary file without symlink hops.

    Returns:
        A canonical file path entirely inside the caller-supplied root.

    """
    current = root.resolve(strict=True)
    for segment in _segments(relative):
        current /= segment
        mode = current.lstat().st_mode
        if stat.S_ISLNK(mode):
            _fail(f"evidence symlink is not admitted: {relative}")
    details = current.lstat()
    if not stat.S_ISREG(details.st_mode) or details.st_size == 0:
        _fail(f"evidence must be a nonempty ordinary file: {relative}")
    if limit is not None and details.st_size > limit:
        _fail(f"evidence exceeds byte limit: {relative}")
    return current


def _manifest(
    root: Path,
    relative: str,
    *,
    require_trial: bool,
    require_budgets: bool,
) -> _ManifestLink:
    path = regular_path(root, relative, limit=MAX_MANIFEST_BYTES)
    with path.open("rb") as stream:
        data = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(data) > MAX_MANIFEST_BYTES:
        _fail(f"evidence exceeds byte limit: {relative}")
    text = data.decode("utf-8")
    return _ManifestLink(
        manifest=experiment_manifest.parse_manifest(text),
        trial=(trial_runs.parse_trial_run(text) if require_trial else None),
        budgets=(
            budget_links.parse_run_budgets(text) if require_budgets else None
        ),
    )


def _compare_identity(
    row: dict[str, Any],
    study: dict[str, Any],
    manifest: experiment_manifest.ExperimentManifest,
) -> None:
    case = row["case"]
    run = manifest.run
    if manifest.record_kind != RUN_RECORD_KIND or run is None:
        _fail("arena evidence requires an experiment run, not a plan")
    if manifest.identifier != row["algorithm"]:
        _fail("experiment ID does not match arena algorithm")
    _compare_case(case, manifest)
    if manifest.target_profile != study["target_profile"]:
        _fail("experiment target profile does not match arena study")
    if manifest.oracle != row["verifier"]:
        _fail("experiment oracle identity does not match reported verifier")
    _compare_run(row, study, run)


def _compare_case(
    case: dict[str, Any],
    manifest: experiment_manifest.ExperimentManifest,
) -> None:
    if manifest.challenge_family != case["family"]:
        _fail("experiment challenge family does not match arena case")
    if (
        manifest.difficulty != case["difficulty"]
        or manifest.seed != case["seed"]
    ):
        _fail("experiment challenge seed/difficulty does not match arena case")


def _compare_run(
    row: dict[str, Any],
    study: dict[str, Any],
    run: experiment_manifest.RunIdentity,
) -> None:
    if run.workload_sha256 != row["case"]["workload_sha256"]:
        _fail("experiment workload digest does not match arena case")
    if run.raw_output != row["raw_sample"]:
        _fail("experiment raw output does not match arena reference")
    if run.host != study["host"] or run.toolchain != study["toolchain"]:
        _fail("experiment host/toolchain does not match arena study")
    if run.outcome != RUN_OUTCOMES[row["outcome"]]:
        _fail("experiment run outcome does not match arena trial")


@dataclass(frozen=True, slots=True)
class _ManifestLink:
    manifest: experiment_manifest.ExperimentManifest
    trial: trial_runs.TrialRun | None
    budgets: budget_links.RunBudgets | None


@dataclass(frozen=True, slots=True)
class EvidencePolicy:
    """Optional source-reported evidence checks, defaulting to identity only."""

    require_raw_rows: bool = False
    require_trial_run_identity: bool = False
    require_budget_agreement: bool = False
    challenge_root: str | None = None


DEFAULT_EVIDENCE_POLICY = EvidencePolicy()


@dataclass(slots=True)
class _EvidenceContext:
    root: Path
    study: dict[str, Any]
    manifests: dict[str, _ManifestLink]
    samples: set[str]
    claimed_trial_manifests: set[str]
    policy: EvidencePolicy


def _admit_observation(row: dict[str, Any], context: _EvidenceContext) -> None:
    manifest_path = row["experiment_manifest"]
    if manifest_path not in context.manifests:
        context.manifests[manifest_path] = _manifest(
            context.root,
            manifest_path,
            require_trial=context.policy.require_trial_run_identity,
            require_budgets=context.policy.require_budget_agreement,
        )
    link = context.manifests[manifest_path]
    _compare_identity(row, context.study, link.manifest)
    if context.policy.require_trial_run_identity:
        _compare_trial(row, manifest_path, link, context=context)
    if context.policy.require_budget_agreement:
        _compare_budgets(link, context.study)
    sample = row["raw_sample"]
    _ = regular_path(context.root, sample)
    context.samples.add(sample)


def _compare_trial(
    row: dict[str, Any],
    path: str,
    link: _ManifestLink,
    *,
    context: _EvidenceContext,
) -> None:
    if path in context.claimed_trial_manifests:
        _fail(f"arena_trial manifest cited for multiple trials: {path}")
    if link.trial is None or link.trial.trial != row["trial"]:
        _fail(f"arena_trial repetition differs from reported trial: {path}")
    context.claimed_trial_manifests.add(path)


def _compare_budgets(
    link: _ManifestLink,
    study: dict[str, Any],
) -> None:
    if link.budgets is None:
        _fail("experiment run budget agreement was not loaded")
    if (
        link.budgets.time_ns != study["budget"]["time_ns"]
        or link.budgets.memory_bytes != study["budget"]["memory_bytes"]
    ):
        _fail("experiment run declared budget differs from arena study")


def _trial_digests(
    context: _EvidenceContext,
    contents: dict[str, str],
    document: dict[str, Any],
) -> None:
    for row in document["observations"]:
        trial = context.manifests[row["experiment_manifest"]].trial
        if trial is None or trial.raw_sha256 != contents[row["raw_sample"]]:
            _fail("arena_trial retained raw SHA-256 differs from run manifest")


def _raw_contents(
    document: dict[str, Any],
    root: Path,
) -> dict[str, str]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in document["observations"]:
        groups.setdefault(row["raw_sample"], []).append(row)
    contents = {}
    for relative, rows in sorted(groups.items()):
        path = regular_path(root, relative, limit=raw_samples.MAX_RAW_BYTES)
        with path.open("rb") as stream:
            raw = stream.read(raw_samples.MAX_RAW_BYTES + 1)
        contents[relative] = raw_samples.check_rows(raw, rows, relative)
    return contents


def _checked_contents(
    document: dict[str, Any],
    context: _EvidenceContext,
) -> dict[str, str] | None:
    if not (
        context.policy.require_raw_rows
        or context.policy.require_trial_run_identity
    ):
        return None
    contents = _raw_contents(document, context.root)
    if context.policy.require_trial_run_identity:
        _trial_digests(context, contents, document)
    return contents


def _bundle_source(
    root: Path,
    relative: str,
    *,
    limit: int,
) -> bytes:
    path = regular_path(root, relative, limit=limit)
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        _fail(f"challenge bundle exceeds byte limit: {relative}")
    return data


def _bundle_directory(case: dict[str, Any], relative_root: str) -> str:
    if case["difficulty"] > challenge_bundles.MAX_BUNDLE_NODES:
        _fail("challenge replay exceeds 4096-node preflight limit")
    return (
        f"{relative_root}/{case["family"]}/v{case["version"]}/"
        f"seed-{case["seed"]}/nodes-{case["difficulty"]}"
    )


def _bundle_inspection(
    document: dict[str, Any],
    root: Path,
    relative_root: str,
) -> dict[str, str]:
    _ = _segments(relative_root)
    results: dict[str, str] = {}
    cases: set[tuple[str, int, int, int]] = set()
    for row in document["observations"]:
        case = row["case"]
        key = (
            case["family"],
            case["version"],
            case["seed"],
            case["difficulty"],
        )
        directory = _bundle_directory(case, relative_root)
        if key in cases:
            if results[directory] != case["workload_sha256"]:
                _fail("repeated challenge case has different workload digest")
            continue
        cases.add(key)
        if len(cases) > challenge_bundles.MAX_BUNDLE_CASES:
            _fail("too many distinct challenge bundles for replay")
        limits = {
            "program.c": challenge_bundles.MAX_SOURCE_BYTES,
            "oracle.bin": challenge_bundles.ORACLE_BYTES,
            "manifest.json": challenge_bundles.MAX_MANIFEST_BYTES,
        }
        files = {
            name: _bundle_source(
                root, f"{directory}/{name}", limit=limits[name]
            )
            for name in challenge_bundles.BUNDLE_FILES
        }
        results[directory] = challenge_bundles.verify_bundle(
            case,
            document["study"]["target_profile"],
            files,
        )
    return results


def _report_links(
    context: _EvidenceContext,
    document: dict[str, Any],
    contents: dict[str, str] | None,
    *,
    bundle_sources: dict[str, str] | None,
) -> dict[str, Any]:
    report = {
        "manifest_links_checked": len(context.manifests),
        "raw_sample_paths_checked": len(context.samples),
        "reported_trials_checked": len(document["observations"]),
        "scope": (
            "Linked run identity and nonempty raw-file presence only; "
            "no content digest verification or semantic oracle replay."
        ),
    }
    if contents is not None:
        report["raw_file_sha256"] = contents
        report["raw_rows_matched"] = len(document["observations"])
        report["scope"] = (
            "Reported raw CSV identity and metrics match; no provenance "
            "authentication or independent semantic oracle replay."
        )
    if context.policy.require_trial_run_identity:
        report["trial_run_links_checked"] = len(context.claimed_trial_manifests)
        report["scope"] = (
            "Versioned per-trial run identity, matching retained CSV rows, "
            "and source-reported raw-byte hashes; no verifier replay or "
            "independent measurement authentication."
        )
    if context.policy.require_budget_agreement:
        report["run_budget_links_checked"] = len(context.manifests)
        report["scope"] += (
            " Exact declared run time/memory budgets agree with study; "
            "no physical budget enforcement."
        )
    if bundle_sources is not None:
        report["regenerated_challenge_bundles"] = len(bundle_sources)
        report["challenge_source_sha256"] = bundle_sources
        report["scope"] += (
            " Deterministic challenge bundle replay succeeded; "
            "no compiler execution or verifier replay."
        )
    return report


def validate_links(
    document: dict[str, Any],
    root: Path,
    *,
    policy: EvidencePolicy = DEFAULT_EVIDENCE_POLICY,
) -> dict[str, Any]:
    """Cross-check reported trials with bounded canonical run files.

    Returns:
        Counts of checked links without claiming semantic certification.

    Raises:
        EvidenceError: A linked identity or retained file is inadmissible.

    """
    context = _EvidenceContext(
        root,
        document["study"],
        {},
        set(),
        set(),
        policy,
    )
    try:
        for row in document["observations"]:
            _admit_observation(row, context)
        contents = _checked_contents(document, context)
        bundle_sources = (
            _bundle_inspection(document, root, policy.challenge_root)
            if policy.challenge_root is not None
            else None
        )
    except (
        OSError,
        UnicodeError,
        RuntimeError,
        experiment_manifest.ExperimentManifestError,
        raw_samples.RawSampleError,
        trial_runs.TrialRunError,
        budget_links.BudgetLinkError,
        challenge_bundles.ChallengeBundleError,
    ) as error:
        message = f"linked arena evidence invalid: {error}"
        raise EvidenceError(message) from error
    return _report_links(
        context,
        document,
        contents,
        bundle_sources=bundle_sources,
    )


def main() -> int:
    """Analyze a study only after its local evidence identity preflight.

    Returns:
        Zero after cross-checking all links; two on invalid input.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).parents[2])
    parser.add_argument("--require-raw-rows", action="store_true")
    parser.add_argument("--require-trial-run-identity", action="store_true")
    parser.add_argument("--require-budget-agreement", action="store_true")
    parser.add_argument("--challenge-root")
    args = parser.parse_args()
    try:
        document = analyze.parse_document(analyze.read_input(args.study))
        checked = validate_links(
            document,
            args.root,
            policy=EvidencePolicy(
                require_raw_rows=args.require_raw_rows,
                require_trial_run_identity=args.require_trial_run_identity,
                require_budget_agreement=args.require_budget_agreement,
                challenge_root=args.challenge_root,
            ),
        )
        report = analyze.analyze(document)
    except (analyze.ArenaError, EvidenceError, OSError, UnicodeError) as error:
        parser.exit(2, f"arena evidence: {error}\n")
    report["evidence_preflight"] = checked
    _ = sys.stdout.write(json.dumps(report, sort_keys=True, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
