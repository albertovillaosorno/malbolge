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
#   - Real host-C reference measurements for bounded parametric C challenges.
# - Must-Not:
#   - Misrepresent reference C binaries as Malbolge compiler output.
# - Allows:
#   - Inputs: explicit canonical family, node levels, seed and trial count.
#   - Outputs: governed arena JSON, run TOML, raw CSV and exact artifacts.
#   - Side effects: ignored local data and bounded Clang subprocesses.
# - Split-When:
#   - A target compiler runner gains its own executable and verifier contract.
# - Merge-When:
#   - One governed measurement harness owns all host reference comparisons.
# - Summary:
#   - Retains actual stage times, output sizes, failures and source identities.
# - Description:
#   - Runs pinned Clang O0/O2 on matching challenge cases and seed/trial pairs.
# - Usage:
#   - `python -B -m benchmarks.arena.reference_study arithmetic-dag`.
# - Defaults:
#   - Only bounded canonical host C; outputs are ignored, never published.
#

"""Retain real host-C reference measurements in ignored local files."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import shutil
import stat
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
import time
from dataclasses import dataclass, field
from hashlib import sha256
from io import StringIO
from pathlib import Path
from typing import Any, Never

from benchmarks.arena import (
    analyze,
    evidence,
    host_c_oracle,
    raw_samples,
    report_output,
)
from benchmarks.challenges import generate
from scripts.validate import experiment_manifest

_ROOT = Path(__file__).resolve().parents[2]
_LOCAL = _ROOT / ".temp"
PROFILE = "malbolge-2026.3"
BASELINE = "host-clang-O0"
CANDIDATE = "host-clang-O2"
ALGORITHMS = ((BASELINE, "-O0"), (CANDIDATE, "-O2"))
VERIFIER = "generated-challenge-native-C-entry-oracle-v1"
BUDGET_SECONDS = 60
BUDGET_MEMORY_MIB = 1024
MAX_DIFFICULTIES = 4
MAX_TRIALS = 5
FAILED_OUTCOME = "tool_failed"
ASCII_LOW = " "
ASCII_HIGH = "~"
GIT_HASH_WIDTH = 40


class ReferenceStudyError(ValueError):
    """Host-C reference measurements cannot be published as valid evidence."""


def _fail(message: str) -> Never:
    raise ReferenceStudyError(message)


def _quote(text: str) -> str:
    return json.dumps(text, ensure_ascii=True)


def _commit() -> str:
    executable = shutil.which("git", path=os.defpath)
    if executable is None:
        _fail("host-C reference study requires Git")
    # Caller Git selectors cannot redirect a source provenance lookup.
    clean_env = {
        name: value for name, value in os.environ.items() if not name.startswith("GIT_")
    }
    try:
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [executable, "rev-parse", "HEAD"],
            cwd=_ROOT,
            stdin=sp.DEVNULL,
            env=clean_env,
            shell=False,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, sp.CalledProcessError, sp.TimeoutExpired) as error:
        message = "host reference study cannot identify source commit"
        raise ReferenceStudyError(message) from error
    commit = completed.stdout.strip()
    if (
        len(commit) != GIT_HASH_WIDTH
        or not set(commit) <= analyze.SHA256_ALPHABET
    ):
        _fail("host reference study has invalid source commit")
    return commit


def _raw_csv(observation: dict[str, Any]) -> bytes:
    row = observation
    case = row["case"]
    values: dict[str, str] = {
        "schema_version": "1",
        "algorithm": row["algorithm"],
        "family": case["family"],
        "version": str(case["version"]),
        "difficulty": str(case["difficulty"]),
        "seed": str(case["seed"]),
        "workload_sha256": case["workload_sha256"],
        "trial": str(row["trial"]),
        "outcome": row["outcome"],
        "verifier": row["verifier"],
        "verifier_verdict": row["verifier_verdict"],
    }
    values.update({key: str(value) for key, value in row["metrics"].items()})
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    _ = writer.writerow(raw_samples.HEADER)
    _ = writer.writerow([values.get(key, "") for key in raw_samples.HEADER])
    raw = output.getvalue().encode("utf-8")
    _ = raw_samples.check_rows(raw, [observation], "new host-C raw sample")
    return raw


@dataclass(frozen=True, slots=True)
class StudyPlan:
    """Bounded host reference study inputs."""

    family: str
    difficulties: tuple[int, ...]
    seed: int
    trials: int


@dataclass(frozen=True, slots=True)
class _Env:
    root: Path
    plan: StudyPlan
    commit: str
    host: str
    toolchain: str
    prefix: str
    failures: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _ManifestMeta:
    env: _Env
    fingerprint: str
    raw_sha256: str


def _manifest(row: dict[str, Any], meta: _ManifestMeta) -> str:
    commit = meta.env.commit
    host = meta.env.host
    profile_fingerprint = meta.fingerprint
    raw_sha256 = meta.raw_sha256
    output_root = meta.env.prefix
    case = row["case"]
    outcome = evidence.RUN_OUTCOMES[row["outcome"]]
    lines = [
        "schema_version = 1",
        "",
        "[experiment]",
        f"id = {_quote(row["algorithm"])}",
        'record_kind = "run"',
        'method_class = "benchmarking"',
        f"seed = {case["seed"]}",
        "",
        "[challenge]",
        f"family = {_quote(case["family"])}",
        f"difficulty = {case["difficulty"]}",
        f"target_profile = {_quote(PROFILE)}",
        f"target_profile_fingerprint = {_quote(profile_fingerprint)}",
        "",
        "[budget]",
        f"seconds = {BUDGET_SECONDS}",
        f"memory_mib = {BUDGET_MEMORY_MIB}",
        "",
        "[verification]",
        "required = true",
        f"oracle = {_quote(VERIFIER)}",
        "",
        "[provenance]",
        'implementation = "benchmarks/arena/reference_study.py"',
        'configuration = "benchmarks/arena/README.md"',
        f"output = {_quote(output_root)}",
        "",
        "[run]",
        f"commit = {_quote(commit)}",
        f"workload_sha256 = {_quote(case["workload_sha256"])}",
        f"host = {_quote(host)}",
        'accelerator = "none"',
        f"toolchain = {_quote(meta.env.toolchain)}",
        f"outcome = {_quote(outcome)}",
        f"raw_output = {_quote(row["raw_sample"])}",
        "",
        "[arena_trial]",
        "schema_version = 1",
        f"trial = {row["trial"]}",
        f"raw_sha256 = {_quote(raw_sha256)}",
        "",
    ]
    text = "\n".join(lines)
    _ = experiment_manifest.parse_manifest(text)
    return text


def _generate_bundle(
    root: Path,
    family: str,
    nodes: int,
    *,
    seed: int,
) -> tuple[dict[str, Any], str]:
    identity = generate.ChallengeIdentity(
        family=family,
        version=1,
        seed=seed,
        profile=PROFILE,
        nodes=nodes,
    )
    generated = generate.generate(identity)
    directory = f"bundles/{family}/v1/seed-{seed}/nodes-{nodes}"
    output = root / directory
    output.mkdir(parents=True)
    _write_retained_bytes(output / "program.c", generated.source)
    _write_retained_bytes(output / "oracle.bin", generated.oracle)
    _write_retained_bytes(output / "manifest.json", generated.manifest)
    case = {
        "family": family,
        "version": 1,
        "difficulty": nodes,
        "seed": seed,
        "workload_sha256": sha256(generated.source).hexdigest(),
    }
    fingerprint = json.loads(generated.manifest)["identity"][
        "target_profile_fingerprint"
    ]
    return case, fingerprint


def _successful(
    root: Path,
    identity: generate.ChallengeIdentity,
    name: str,
    *,
    mode: str,
) -> tuple[dict[str, int], dict[str, str]]:
    measured = host_c_oracle.measure_reference(identity, mode)
    if measured.elapsed_ns > BUDGET_SECONDS * 1_000_000_000:
        _fail("host-C successful measurement exceeds declared budget")
    path = f"candidates/{name}"
    _write_retained_bytes(root / path, measured.executable)
    return (
        {
            "elapsed_ns": measured.elapsed_ns,
            "artifact_bytes": len(measured.executable),
            "peak_rss_bytes": measured.peak_rss_bytes,
        },
        {
            "path": f"{root.relative_to(_ROOT).as_posix()}/{path}",
            "sha256": sha256(measured.executable).hexdigest(),
        },
    )


def _failure_diagnostic(error: host_c_oracle.HostOracleError) -> str:
    raw = str(error)
    ascii_message = "".join(
        character if ASCII_LOW <= character <= ASCII_HIGH else "?"
        for character in raw
    )[:256]
    return ascii_message or "host-C reference failed without diagnostic"


def _measure(
    root: Path,
    case: dict[str, Any],
    *,
    trial: int,
    arm: tuple[str, str],
) -> tuple[dict[str, Any], dict[str, str], str | None]:
    algorithm, mode = arm
    name = f"{algorithm}-nodes-{case["difficulty"]}-trial-{trial}"
    identity = generate.ChallengeIdentity(
        case["family"],
        case["version"],
        case["seed"],
        PROFILE,
        case["difficulty"],
    )
    started = time.perf_counter_ns()
    diagnostic: str | None = None
    try:
        metrics, artifact = _successful(root, identity, name, mode=mode)
    except host_c_oracle.HostOracleError as error:
        diagnostic = _failure_diagnostic(error)
        outcome = FAILED_OUTCOME
        metrics, artifact = (
            {"elapsed_ns": time.perf_counter_ns() - started},
            {},
        )
    else:
        outcome = analyze.VERIFIED
    prefix = root.relative_to(_ROOT).as_posix()
    return (
        {
            "algorithm": algorithm,
            "case": case.copy(),
            "trial": trial,
            "outcome": outcome,
            "verifier": VERIFIER,
            "verifier_verdict": (
                analyze.ACCEPTED
                if outcome == analyze.VERIFIED
                else analyze.NOT_RUN
            ),
            "experiment_manifest": f"{prefix}/runs/{name}.toml",
            "raw_sample": f"{prefix}/raw/{name}.csv",
            "metrics": metrics,
        },
        artifact,
        diagnostic,
    )


def _write_attempt(
    environment: _Env,
    bundle: tuple[dict[str, Any], str],
    *,
    trial: int,
    arm: tuple[str, str],
) -> tuple[dict[str, Any], dict[str, str]]:
    case, fingerprint = bundle
    row, artifact, diagnostic = _measure(
        environment.root,
        case,
        trial=trial,
        arm=arm,
    )
    if diagnostic is not None:
        environment.failures[row["experiment_manifest"]] = diagnostic
    raw = _raw_csv(row)
    _write_retained_bytes(_ROOT / row["raw_sample"], raw)
    metadata = _ManifestMeta(environment, fingerprint, sha256(raw).hexdigest())
    _write_retained_text(
        _ROOT / row["experiment_manifest"], _manifest(row, metadata)
    )
    return row, artifact


def _write_case(
    environment: _Env,
    nodes: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    case, fingerprint = _generate_bundle(
        environment.root,
        environment.plan.family,
        nodes,
        seed=environment.plan.seed,
    )
    rows: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, str]] = {}
    for trial in range(environment.plan.trials):
        for arm in ALGORITHMS:
            row, artifact = _write_attempt(
                environment,
                (case, fingerprint),
                trial=trial,
                arm=arm,
            )
            rows.append(row)
            if artifact:
                artifacts[row["experiment_manifest"]] = artifact
    return rows, artifacts


def _document(
    environment: _Env,
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    plan = environment.plan
    return {
        "schema_version": 1,
        "study": {
            "id": f"host-C-reference-{plan.family}-seed-{plan.seed}",
            "question": "Does Clang O2 reduce time or code size vs O0?",
            "hypothesis": "O2 improves verified time/size frontier on C.",
            "baseline": BASELINE,
            "rejection_observation": (
                "O2 is dominated by O0 at all difficulties."
            ),
            "stage": "host-c-reference-not-malbolge",
            "target_profile": PROFILE,
            "host": environment.host,
            "toolchain": environment.toolchain,
            "budget": {
                "time_ns": BUDGET_SECONDS * 1_000_000_000,
                "memory_bytes": BUDGET_MEMORY_MIB * 1_048_576,
            },
            "objectives": ["elapsed_ns", "artifact_bytes", "peak_rss_bytes"],
        },
        "observations": observations,
    }


def _verify_report(environment: _Env, document: dict[str, Any]) -> None:
    admitted = analyze.parse_document(json.dumps(document))
    _ = analyze.analyze(admitted)
    _ = evidence.validate_links(
        admitted,
        _ROOT,
        policy=evidence.EvidencePolicy(
            require_trial_run_identity=True,
            require_budget_agreement=True,
            challenge_root=f"{environment.prefix}/bundles",
        ),
    )


MAX_ARTIFACT_BYTES = 8 * 1024 * 1024


def _check_artifact_metadata(
    row: dict[str, Any],
    entry: dict[str, str],
) -> None:
    manifest = row["experiment_manifest"]
    if "/runs/" not in manifest:
        _fail("host-C artifact requires a run manifest path")
    prefix, filename = manifest.rsplit("/runs/", maxsplit=1)
    expected = f"{prefix}/candidates/{filename.removesuffix(".toml")}"
    if entry.get("path") != expected:
        _fail("host-C artifact path differs from its originating trial")
    if not isinstance(entry.get("sha256"), str):
        _fail("host-C artifact missing SHA-256 identity")
    if not set(entry["sha256"]) <= analyze.SHA256_ALPHABET:
        _fail("host-C artifact has noncanonical digest")
    if len(entry["sha256"]) != analyze.SHA256_HEX_LENGTH:
        _fail("host-C artifact has noncanonical digest")


def _checked_artifact(
    row: dict[str, Any],
    entry: dict[str, str],
) -> None:
    _check_artifact_metadata(row, entry)
    try:
        actual = evidence.read_bounded_regular(
            _ROOT,
            entry["path"],
            limit=MAX_ARTIFACT_BYTES,
        )
    except (OSError, evidence.EvidenceError) as error:
        message = f"host-C retained artifact cannot be admitted: {error}"
        raise ReferenceStudyError(message) from error
    if sha256(actual).hexdigest() != entry["sha256"]:
        _fail("host-C retained executable differs from its SHA-256 claim")
    if len(actual) != row["metrics"]["artifact_bytes"]:
        _fail("host-C retained executable size differs from study metric")


def _retained_trial_rows(document: object) -> list[dict[str, Any]]:
    """Admit exact row shapes before any retained evidence selection.

    Returns:
        Trial records with native outcome and manifest identity fields.

    """
    if type(document) is not dict or any(
        type(key) is not str for key in document
    ):
        _fail("host-C retained checks require a native study map")
    rows = document.get("observations")
    if type(rows) is not list:
        _fail("host-C retained checks require a trial observation list")
    for row in rows:
        if type(row) is not dict or any(type(key) is not str for key in row):
            _fail("host-C retained checks require native trial rows")
        outcome = row.get("outcome")
        if type(outcome) is not str or outcome not in {
            analyze.VERIFIED,
            FAILED_OUTCOME,
        }:
            _fail("host-C reference contains a non-runner outcome")
        manifest = row.get("experiment_manifest")
        if type(manifest) is not str or not manifest:
            _fail("host-C retained checks require a trial manifest identity")
    return rows


def _admit_retained_sidecars(sidecars: object, *, kind: str) -> None:
    """Reject foreign metadata containers before key-set comparisons."""
    if type(sidecars) is not dict or any(
        type(key) is not str for key in sidecars
    ):
        _fail(f"host-C retained {kind} requires a native metadata map")


def check_retained_artifacts(
    document: dict[str, Any],
    artifacts: dict[str, dict[str, str]],
) -> int:
    """Check successful binaries against reported size, path and SHA-256.

    Returns:
        Number of verified native host-C reference binaries checked.

    """
    rows = _retained_trial_rows(document)
    _admit_retained_sidecars(artifacts, kind="artifacts")
    if any(
        type(entry) is not dict
        or any(type(key) is not str for key in entry)
        or any(type(value) is not str for value in entry.values())
        for entry in artifacts.values()
    ):
        _fail("host-C retained artifacts require native metadata entries")
    verified: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row["outcome"] != analyze.VERIFIED:
            continue
        manifest = row["experiment_manifest"]
        if manifest in verified:
            _fail("host-C duplicate verified experiment manifest")
        verified[manifest] = row
    if set(artifacts) != set(verified):
        _fail("host-C artifact map must match exactly the successful trials")
    for row in verified.values():
        metrics = row.get("metrics")
        if (
            type(metrics) is not dict
            or any(type(key) is not str for key in metrics)
            or type(metrics.get("artifact_bytes")) is not int
            or metrics["artifact_bytes"] < 1
        ):
            _fail("host-C verified artifacts require native size metrics")
    for manifest, row in sorted(verified.items()):
        _checked_artifact(row, artifacts[manifest])
    return len(verified)


MAX_FAILURE_DIAGNOSTIC_BYTES = 256


def check_retained_failures(
    document: dict[str, Any],
    failures: dict[str, str],
) -> int:
    """Bind bounded diagnostics to every real host-C failed trial.

    Returns:
        Number of failed trial diagnostics checked.

    """
    rows = _retained_trial_rows(document)
    _admit_retained_sidecars(failures, kind="failures")
    expected: set[str] = set()
    for row in rows:
        if row["outcome"] != FAILED_OUTCOME:
            continue
        manifest = row["experiment_manifest"]
        if manifest in expected:
            _fail("host-C duplicate failed experiment manifest")
        expected.add(manifest)
    if set(failures) != expected:
        _fail("host-C failure diagnostics must match failed trial identities")
    if any(
        type(message) is not str
        or not 1 <= len(message) <= MAX_FAILURE_DIAGNOSTIC_BYTES
        or any(
            not ASCII_LOW <= character <= ASCII_HIGH for character in message
        )
        for message in failures.values()
    ):
        _fail("host-C failure diagnostics must be bounded printable ASCII")
    return len(failures)


def _write_retained_bytes(path: Path, content: bytes) -> None:
    """Reject short or foreign byte acknowledgements for retained evidence."""
    written = path.write_bytes(content)
    if type(written) is not int or written != len(content):
        _fail(f"host-C retained {path.name} has invalid write count")


def _write_retained_text(path: Path, content: str) -> None:
    """Require complete text writes before admitting a retained study."""
    written = path.write_text(content, encoding="utf-8")
    if type(written) is not int or written != len(content):
        _fail(f"host-C retained {path.name} has invalid write count")


def _run_study(root: Path, plan: StudyPlan, *, commit: str) -> dict[str, Any]:
    environment = _Env(
        root=root,
        plan=plan,
        commit=commit,
        host=f"{platform.system()}-{platform.machine()}-{platform.node()}",
        toolchain="repo-pinned-clang-22.1.8",
        prefix=root.relative_to(_ROOT).as_posix(),
    )
    observations: list[dict[str, Any]] = []
    artifacts: dict[str, dict[str, str]] = {}
    for nodes in plan.difficulties:
        rows, binaries = _write_case(environment, nodes)
        observations.extend(rows)
        artifacts.update(binaries)
    document = _document(environment, observations)
    _verify_report(environment, document)
    _ = check_retained_artifacts(document, artifacts)
    _ = check_retained_failures(document, environment.failures)
    _write_retained_text(
        root / "failures.json",
        json.dumps(
            {
                "schema_version": 1,
                "failures": environment.failures,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    _write_retained_text(
        root / "resource-controls.json",
        json.dumps(
            host_c_oracle.resource_controls_record(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    _write_retained_text(
        root / "artifacts.json",
        json.dumps(artifacts, indent=2, sort_keys=True) + "\n",
    )
    _write_retained_text(
        root / "study.json",
        json.dumps(document, indent=2, sort_keys=True) + "\n",
    )
    return document


def _validate_plan_shape(plan: StudyPlan) -> None:
    if type(plan) is not StudyPlan:
        _fail("host-C reference requires an exact StudyPlan")
    if type(plan.difficulties) is not tuple or any(
        type(nodes) is not int for nodes in plan.difficulties
    ):
        _fail("host-C reference difficulty levels require an exact integer tuple")
    if not plan.difficulties or len(plan.difficulties) > MAX_DIFFICULTIES:
        _fail("host-C reference requires one to four difficulty levels")
    if len(set(plan.difficulties)) != len(plan.difficulties):
        _fail("host-C reference difficulty levels must be distinct")
    if type(plan.trials) is not int or not 1 <= plan.trials <= MAX_TRIALS:
        _fail("host-C reference trial count must be an integer between 1 and 5")


def _validate_plan(plan: StudyPlan) -> None:
    _validate_plan_shape(plan)
    for nodes in plan.difficulties:
        _ = generate.ChallengeIdentity(
            plan.family,
            1,
            plan.seed,
            PROFILE,
            nodes,
        ).validate()
        if nodes > host_c_oracle.MAX_REPLAY_NODES:
            _fail("host-C reference exceeds 512-node limit")
    try:
        host_c_oracle.require_child_resource_controls()
    except host_c_oracle.HostOracleError as error:
        message = f"host-C reference requires enforced child limits: {error}"
        raise ReferenceStudyError(message) from error


def run_study(plan: StudyPlan) -> tuple[Path, dict[str, Any]]:
    """Measure host-C reference behavior into ignored local evidence.

    Returns:
        Local study directory and governed, independently linked report.

    """
    _validate_plan(plan)
    # Fail the Git provenance preflight before allocating retained evidence.
    commit = _commit()
    # Only an existing physical .temp directory may contain new host-C trials.
    # This is static admission, not a cross-process filesystem race guarantee.
    try:
        local_mode = _LOCAL.lstat().st_mode
    except OSError as error:
        message = "host-C reference workspace root is unavailable"
        raise ReferenceStudyError(message) from error
    if not stat.S_ISDIR(local_mode):
        _fail("host-C reference workspace requires a physical output directory")
    try:
        directory = Path(
            tempfile.mkdtemp(
                prefix="arena-host-c-study-",
                dir=_LOCAL,
            )
        )
    except OSError as error:
        message = "host-C reference workspace allocation failed"
        raise ReferenceStudyError(message) from error
    try:
        for child in ("raw", "runs", "candidates"):
            (directory / child).mkdir()
    except OSError as error:
        # Only remove our newly allocated, not-yet-measured study directory.
        # Preserve the original failure if cleanup also fails.
        try:
            shutil.rmtree(directory)
        except OSError as cleanup_error:
            error.add_note(f"host-C workspace cleanup also failed: {cleanup_error}")
        message = "host-C reference workspace setup failed"
        raise ReferenceStudyError(message) from error
    return directory, _run_study(directory, plan, commit=commit)


def main() -> int:
    """Capture host-C measurements without asserting Malbolge performance.

    Returns:
        Zero after validated local evidence or two on failure.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family")
    parser.add_argument("--difficulties", type=int, nargs="+", default=[8, 32])
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--trials", type=int, default=2)
    args = parser.parse_args()
    try:
        path, document = run_study(
            StudyPlan(
                args.family,
                tuple(args.difficulties),
                args.seed,
                args.trials,
            )
        )
    except (
        ReferenceStudyError,
        generate.ChallengeError,
        analyze.ArenaError,
        evidence.EvidenceError,
        OSError,
    ) as error:
        parser.exit(2, f"host-C reference study: {error}\n")
    try:
        report_output.publish(
            {
                "study": (path / "study.json").relative_to(_ROOT).as_posix(),
                "observations": len(document["observations"]),
                "scope": (
                    "real host-C reference only; not Malbolge compiler results"
                ),
            },
            sys.stdout,
        )
    except report_output.ReportOutputError as error:
        parser.exit(2, f"host-C reference study: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
