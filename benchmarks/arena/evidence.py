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
#   - Side effects: read local files; optional bounded host oracle subprocesses.
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
from hashlib import sha256
import os
from pathlib import Path
import stat
import sys
from typing import Any
from typing import Never
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import IO

from scripts.validate import experiment_manifest

from benchmarks.arena import analyze
from benchmarks.arena import budget_links
from benchmarks.arena import challenge_bundles
from benchmarks.arena import host_c_oracle
from benchmarks.arena import raw_samples
from benchmarks.arena import report_output
from benchmarks.arena import trial_runs

MAX_MANIFEST_BYTES = 1 * 1024 * 1024
BUNDLE_FILE_LIMITS = {
    "program.c": challenge_bundles.MAX_SOURCE_BYTES,
    "oracle.bin": challenge_bundles.ORACLE_BYTES,
    "manifest.json": challenge_bundles.MAX_MANIFEST_BYTES,
}
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
    if type(relative) is not str or not relative:
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


def _admit_byte_limit(limit: int) -> None:
    if type(limit) is not int or limit < 1:
        _fail("evidence byte limit must be an exact positive integer")


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
    if limit is not None:
        _admit_byte_limit(limit)
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


def _file_identity(details: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        details.st_dev,
        details.st_ino,
        details.st_size,
        details.st_mtime_ns,
        details.st_ctime_ns,
    )


def _open_evidence(path: Path) -> IO[bytes]:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        message = f"evidence file could not open safely: {path}"
        raise EvidenceError(message) from error
    try:
        # O_NOFOLLOW only protects the leaf. A parent directory may be
        # exchanged for a symlink after the component-by-component lstat,
        # then restored before the post-read pathname check. On Linux the
        # descriptor's actual pathname exposes that redirected open even when
        # the outside target is a hard link to the admitted inode.
        if sys.platform == "linux":
            actual_path = os.readlink(f"/proc/self/fd/{descriptor}")
            if actual_path != os.fspath(path):
                _fail(f"evidence opened path changed: {path}")
        return os.fdopen(descriptor, "rb")
    except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
        # Stream construction/path admission failed before stream ownership.
        # An unsuccessful close must not erase the original admission failure.
        try:
            os.close(descriptor)
        except (
            OSError,
            ValueError,
            RuntimeError,
            TypeError,
            AttributeError,
        ) as close_error:
            error.add_note(f"evidence descriptor cleanup also failed: {close_error}")
        if isinstance(error, EvidenceError):
            raise error  # ruff: ignore[TRY201]
        message = f"evidence stream could not open: {path}"
        raise EvidenceError(message) from error


def _read_complete(stream: IO[bytes], *, size: int, relative: str) -> bytes:
    """Consume the exact admitted inode length across bounded short reads.

    Returns:
        Complete admitted evidence bytes.

    Raises:
        EvidenceError: Incomplete or invalid read bytes or stream failure.

    """
    data = bytearray()
    while len(data) < size:
        requested = min(size - len(data), 1024 * 1024)
        try:
            chunk = stream.read(requested)
        except (
            OSError,
            ValueError,
            RuntimeError,
            TypeError,
            AttributeError,
        ) as error:
            message = f"evidence read failed: {relative}"
            raise EvidenceError(message) from error
        if type(chunk) is not bytes or len(chunk) > requested:
            _fail(f"evidence read returned invalid bytes: {relative}")
        if not chunk:
            _fail(f"evidence read ended before admitted size: {relative}")
        data.extend(chunk)
    return bytes(data)


def read_bounded_regular(root: Path, relative: str, *, limit: int) -> bytes:
    """Read bounded ordinary evidence with before/after file identity checks.

    Returns:
        Source bytes from one matching opened descriptor and retained path.

    """
    _admit_byte_limit(limit)
    path = regular_path(root, relative, limit=limit)
    original = path.lstat()
    primary: Exception | None = None
    try:
        with _open_evidence(path) as stream:
            try:
                opened = os.fstat(stream.fileno())
                if not stat.S_ISREG(opened.st_mode) or (
                    _file_identity(original) != _file_identity(opened)
                ):
                    _fail(
                        f"evidence opened file changed after path admission: {relative}"
                    )
                data = _read_complete(stream, size=opened.st_size, relative=relative)
                completed = os.fstat(stream.fileno())
                if _file_identity(completed) != _file_identity(opened):
                    _fail(f"evidence file changed during read: {relative}")
            except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
                primary = error
                raise
    except (OSError, ValueError, RuntimeError, TypeError, AttributeError) as error:
        if primary is not None and error is not primary:
            # The stream's close error must not replace a rejected read.
            primary.add_note(f"evidence stream cleanup also failed: {error}")
            error = primary
        if isinstance(error, EvidenceError):
            # It may be the earlier body exception, not the active close error.
            raise error  # ruff: ignore[TRY201]
        message = f"evidence stream access failed: {relative}"
        raise EvidenceError(message) from error
    final_path = regular_path(root, relative, limit=limit)
    if _file_identity(final_path.lstat()) != _file_identity(opened):
        _fail(f"evidence path changed during read: {relative}")
    if len(data) > limit:
        _fail(f"evidence exceeds byte limit: {relative}")
    return data


def _manifest(
    root: Path,
    relative: str,
    *,
    require_trial: bool,
    require_budgets: bool,
) -> _ManifestLink:
    data = read_bounded_regular(root, relative, limit=MAX_MANIFEST_BYTES)
    text = data.decode("utf-8")
    return _ManifestLink(
        source_sha256=sha256(data).hexdigest(),
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
    source_sha256: str
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
    require_matched_accelerator: bool = False
    require_host_c_challenge_oracle: bool = False


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
        raw = read_bounded_regular(
            root,
            relative,
            limit=raw_samples.MAX_RAW_BYTES,
        )
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


def _recheck_retained_links(
    context: _EvidenceContext,
    contents: dict[str, str] | None,
) -> None:
    # The parsed run manifest remains authoritative only while its retained
    # bytes agree with admission, including after optional host-C execution.
    for relative, link in sorted(context.manifests.items()):
        now = read_bounded_regular(context.root, relative, limit=MAX_MANIFEST_BYTES)
        if sha256(now).hexdigest() != link.source_sha256:
            _fail(f"run manifest changed after admission: {relative}")

    if contents is None:
        # Default mode claims presence, not raw content, so preserve that
        # weaker contract while rejecting late disappearance or symlinks.
        for relative in sorted(context.samples):
            _ = regular_path(context.root, relative)
        return

    # Strict mode reports and optionally links these exact source-byte hashes.
    for relative, expected in sorted(contents.items()):
        now = read_bounded_regular(
            context.root, relative, limit=raw_samples.MAX_RAW_BYTES
        )
        if sha256(now).hexdigest() != expected:
            _fail(f"raw CSV changed after row admission: {relative}")


def _bundle_source(
    root: Path,
    relative: str,
    *,
    limit: int,
) -> bytes:
    return read_bounded_regular(root, relative, limit=limit)


def _bundle_directory(case: dict[str, Any], relative_root: str) -> str:
    if case["difficulty"] > challenge_bundles.MAX_BUNDLE_NODES:
        _fail("challenge replay exceeds 4096-node preflight limit")
    return (
        f"{relative_root}/{case["family"]}/v{case["version"]}/"
        f"seed-{case["seed"]}/nodes-{case["difficulty"]}"
    )


@dataclass(frozen=True, slots=True)
class _BundleInspection:
    sources: dict[str, str]
    retained_sha256: dict[str, str]


def _bundle_inspection(
    document: dict[str, Any],
    root: Path,
    relative_root: str,
) -> _BundleInspection:
    _ = _segments(relative_root)
    results: dict[str, str] = {}
    retained_sha256: dict[str, str] = {}
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
        files = {
            name: _bundle_source(
                root, f"{directory}/{name}", limit=BUNDLE_FILE_LIMITS[name]
            )
            for name in challenge_bundles.BUNDLE_FILES
        }
        results[directory] = challenge_bundles.verify_bundle(
            case,
            document["study"]["target_profile"],
            files,
        )
        for name, contents in files.items():
            retained_sha256[f"{directory}/{name}"] = sha256(contents).hexdigest()
    return _BundleInspection(results, retained_sha256)


def _recheck_bundle_files(root: Path, inspection: _BundleInspection) -> None:
    # Reopen all three original names after subsequent oracle/report work.
    # Metadata consistency during an individual read cannot rule out a later
    # same-length replacement or a rewrite between distinct pipeline stages.
    for relative, expected in inspection.retained_sha256.items():
        name = relative.rsplit("/", 1)[1]
        current = _bundle_source(root, relative, limit=BUNDLE_FILE_LIMITS[name])
        if sha256(current).hexdigest() != expected:
            _fail(f"challenge bundle changed after replay: {relative}")


def _replay_host_c_challenges(
    document: dict[str, Any],
    bundle_hashes: dict[str, str],
    relative_root: str,
) -> dict[str, str]:
    cases = {
        _bundle_directory(row["case"], relative_root): row["case"]
        for row in document["observations"]
    }
    if len(cases) > host_c_oracle.MAX_REPLAY_CASES:
        _fail("host-C challenge replay exceeds 16 distinct cases")
    if any(
        case["difficulty"] > host_c_oracle.MAX_REPLAY_NODES
        for case in cases.values()
    ):
        _fail("host-C challenge replay exceeds 512 nodes")
    return {
        key: host_c_oracle.replay_one(
            case,
            document["study"]["target_profile"],
            bundle_hashes[key],
        )
        for key, case in sorted(cases.items())
    }


def _matched_accelerators(
    context: _EvidenceContext,
) -> dict[str, str] | None:
    if not context.policy.require_matched_accelerator:
        return None
    declared = {}
    for path, link in sorted(context.manifests.items()):
        run = link.manifest.run
        if run is None:
            _fail("accelerator comparison requires a recorded experiment run")
        declared[path] = run.accelerator
    if len(set(declared.values())) != 1:
        _fail("comparison runs declare different accelerator identities")
    return declared


def _report_accelerators(
    report: dict[str, Any],
    accelerators: dict[str, str] | None,
) -> None:
    if accelerators is not None:
        report["declared_run_accelerators"] = accelerators
        report["scope"] += (
            " Reported accelerator identities agree across run manifests; "
            "no physical device attestation."
        )


@dataclass(frozen=True, slots=True)
class _BundleReports:
    source_hashes: dict[str, str] | None
    host_c_hashes: dict[str, str] | None


def _report_bundle_sources(
    report: dict[str, Any],
    bundle: _BundleReports,
) -> None:
    if bundle.source_hashes is not None:
        report["regenerated_challenge_bundles"] = len(bundle.source_hashes)
        report["challenge_source_sha256"] = bundle.source_hashes
        if bundle.host_c_hashes is None:
            report["scope"] += (
                " Deterministic challenge bundle replay succeeded; "
                "no compiler execution or verifier replay."
            )
        else:
            report["scope"] += (
                " Deterministic challenge bundle replay succeeded before "
                "optional host-C source execution."
            )
    if bundle.host_c_hashes is not None:
        report["host_c_challenge_oracles_replayed"] = len(bundle.host_c_hashes)
        report["host_c_replay_modes"] = ["O0", "O2"]
        report["host_c_replay_source_sha256"] = bundle.host_c_hashes
        report["scope"] += (
            " Pinned host C compiler executed canonical generator C at O0/O2 "
            "and matched the generated oracle; no candidate compiler output "
            "was executed or independently certified."
        )


def _report_links(
    context: _EvidenceContext,
    document: dict[str, Any],
    contents: dict[str, str] | None,
    *,
    bundle: _BundleReports,
) -> dict[str, Any]:
    accelerators = _matched_accelerators(context)
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
    _report_accelerators(report, accelerators)
    _report_bundle_sources(report, bundle)
    return report


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    """Snapshot of exact linked input bytes for a final read-only recheck."""

    context: _EvidenceContext
    contents: dict[str, str] | None
    bundle: _BundleInspection | None


def recheck_evidence_snapshot(snapshot: EvidenceSnapshot) -> None:
    """Reject observed retained-input drift without rerunning native tools."""
    if snapshot.bundle is not None:
        _recheck_bundle_files(snapshot.context.root, snapshot.bundle)
    _recheck_retained_links(snapshot.context, snapshot.contents)


def validate_links(
    document: dict[str, Any],
    root: Path,
    *,
    policy: EvidencePolicy = DEFAULT_EVIDENCE_POLICY,
    _snapshot_out: list[EvidenceSnapshot] | None = None,
) -> dict[str, Any]:
    """Cross-check reported trials with bounded canonical run files.

    Returns:
        Counts of checked links without claiming semantic certification.

    Raises:
        EvidenceError: A linked identity or retained file is inadmissible.

    """
    if policy.require_host_c_challenge_oracle and policy.challenge_root is None:
        _fail("host-C oracle replay requires --challenge-root")
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
        bundle_inspection = (
            _bundle_inspection(document, root, policy.challenge_root)
            if policy.challenge_root is not None
            else None
        )
        bundle_sources = (
            bundle_inspection.sources if bundle_inspection is not None else None
        )
        host_c_sources = (
            _replay_host_c_challenges(
                document, bundle_sources, policy.challenge_root
            )
            if policy.require_host_c_challenge_oracle
            and bundle_sources is not None
            and policy.challenge_root is not None
            else None
        )
        report = _report_links(
            context,
            document,
            contents,
            bundle=_BundleReports(bundle_sources, host_c_sources),
        )
        snapshot = EvidenceSnapshot(context, contents, bundle_inspection)
        recheck_evidence_snapshot(snapshot)
    except (
        OSError,
        UnicodeError,
        RuntimeError,
        experiment_manifest.ExperimentManifestError,
        raw_samples.RawSampleError,
        trial_runs.TrialRunError,
        budget_links.BudgetLinkError,
        challenge_bundles.ChallengeBundleError,
        host_c_oracle.HostOracleError,
    ) as error:
        message = f"linked arena evidence invalid: {error}"
        raise EvidenceError(message) from error
    if _snapshot_out is not None:
        _snapshot_out.append(snapshot)
    return report


def _publish_cli_report(
    report: dict[str, Any],
    parser: argparse.ArgumentParser,
) -> None:
    try:
        report_output.publish(report, sys.stdout)
    except report_output.ReportOutputError as error:
        parser.exit(2, f"arena evidence: {error}\n")


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
    parser.add_argument("--require-matched-accelerator", action="store_true")
    parser.add_argument(
        "--require-host-c-challenge-oracle", action="store_true"
    )
    parser.add_argument("--median-intervals-95", action="store_true")
    parser.add_argument("--paired-exact-tests", action="store_true")
    parser.add_argument("--adjust-paired-tests", action="store_true")
    parser.add_argument("--success-intervals-95", action="store_true")
    args = parser.parse_args()
    try:
        source = analyze.read_input(args.study)
        document = analyze.parse_document(source)
        snapshots: list[EvidenceSnapshot] = []
        checked = validate_links(
            document,
            args.root,
            policy=EvidencePolicy(
                require_raw_rows=args.require_raw_rows,
                require_trial_run_identity=args.require_trial_run_identity,
                require_budget_agreement=args.require_budget_agreement,
                challenge_root=args.challenge_root,
                require_matched_accelerator=args.require_matched_accelerator,
                require_host_c_challenge_oracle=(
                    args.require_host_c_challenge_oracle
                ),
            ),
            _snapshot_out=snapshots,
        )
        report = analyze.analyze(
            document,
            median_intervals_95=args.median_intervals_95,
            paired_exact_tests_enabled=args.paired_exact_tests,
            adjust_paired_tests=args.adjust_paired_tests,
        )
        if args.success_intervals_95:
            analyze.annotate_success_intervals(report)
        analyze.require_unchanged_study_input(args.study, source)
        if len(snapshots) != 1:
            _fail("evidence preflight did not retain an input snapshot")
        recheck_evidence_snapshot(snapshots[0])
    except (analyze.ArenaError, EvidenceError, OSError, UnicodeError) as error:
        parser.exit(2, f"arena evidence: {error}\n")
    report["evidence_preflight"] = checked
    _publish_cli_report(report, parser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
