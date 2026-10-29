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
#   - Read-only producer-specific admission of retained classic target echoes.
# - Must-Not:
#   - Authenticate recorded timings or claim general guest correctness.
# - Allows:
#   - Inputs: canonical ignored echo-study path and optional VM replay.
#   - Outputs: independently decoded source identity and checked arena report.
#   - Side effects: read retained evidence; opt-in bounded VM subprocesses.
# - Split-When:
#   - A general target candidate verifier owns more than this fixed sublanguage.
# - Merge-When:
#   - One separately governed target audit subsumes this fixed classic oracle.
# - Summary:
#   - Checks observed source instructions, not merely reported sizes or hashes.
# - Description:
#   - Reopens the producer's study and exact per-trial artifact/run identities.
# - Usage:
#   - python3.14 -B -m benchmarks.arena.target_echo_audit STUDY.
# - Defaults:
#   - Offline read-only audit; opt-in executable VM replay, never remeasurement.
#

"""Strict post-run audit of the bounded classic Malbolge EOF echo study."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
import stat
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import Any
from typing import Never

from scripts.validate import experiment_manifest

from benchmarks.arena import analyze
from benchmarks.arena import evidence
from benchmarks.arena import report_output
from benchmarks.arena import target_echo_reference as producer

_ROOT = Path(__file__).resolve().parents[2]
MAX_STUDY_BYTES = 16 * 1024 * 1024
STUDY_LEAF = "study.json"
PATH_PART_COUNT = 3
UNDERSCORE = "_"
DIGEST_HEX_LENGTH = 64
PHASES = 94
METHOD_CLASS = "benchmarking"
ACCELERATOR = "none"
RUN_PREFIX = "arena-target-echo-"
ROOT_PART = ".temp"
DIRECTORY_NAMES = ("runs", "raw", "candidates")
PRODUCER_IMPLEMENTATION = "benchmarks/arena/target_echo_reference.py"
PRODUCER_CONFIGURATION = "benchmarks/arena/README.md"
SOURCE_INSTRUCTIONS = {
    "input": ord("/"),
    "output": ord("<"),
    "nop": ord("o"),
    "halt": ord("v"),
}
# Independently authored frozen classic XLAT1 mapping, not emitter output.
CLASSIC_DECODE = (
    b'+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA"lI'
    b".v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
)


class TargetEchoAuditError(ValueError):
    """Retained target echo evidence is inconsistent or unverifiable."""


def _fail(message: str) -> Never:
    raise TargetEchoAuditError(message)


def _prefix(relative: str) -> str:
    if type(relative) is not str:
        _fail("target audit requires a canonical study path")
    parts = relative.split("/")
    if (
        len(parts) != PATH_PART_COUNT
        or parts[0] != ROOT_PART
        or parts[2] != STUDY_LEAF
    ):
        _fail("target audit requires .temp/arena-target-echo-*/study.json")
    label = parts[1]
    suffix = label.removeprefix(RUN_PREFIX)
    if not label.startswith(RUN_PREFIX) or not suffix:
        _fail("target audit requires an arena-target-echo study directory")
    if not suffix.isascii() or not all(
        character.isalnum() or character == UNDERSCORE for character in suffix
    ):
        _fail("target audit requires a canonical generated directory")
    return "/".join(parts[:2])


def _document(relative: str) -> dict[str, Any]:
    data = evidence.read_bounded_regular(
        _ROOT,
        relative,
        limit=MAX_STUDY_BYTES,
    )
    return analyze.parse_document(data.decode("utf-8"))


def _producer_study(document: dict[str, Any]) -> None:
    study = document["study"]
    expected = {
        "id": "classic-eof-echo-geometry-v1",
        "question": (
            "Does redundant no-op padding worsen the classic VM frontier?"
        ),
        "hypothesis": "Direct code is smaller than no-op padded code.",
        "rejection_observation": (
            "Padded code is not larger or direct fails its EOF oracle."
        ),
        "baseline": producer.BASELINE,
        "stage": "measured-classic-malbolge-code-and-vm",
        "target_profile": producer.PROFILE,
        "budget": {
            "time_ns": producer.BUDGET_SECONDS * 1_000_000_000,
            "memory_bytes": producer.BUDGET_MIB * 1_048_576,
        },
        "objectives": ["elapsed_ns", "artifact_bytes"],
    }
    if any(study[name] != value for name, value in expected.items()):
        _fail("target study differs from the classic echo producer policy")
    fingerprint = study["toolchain"].removeprefix("local-compiler-vm-sha256:")
    if (
        study["toolchain"] != f"local-compiler-vm-sha256:{fingerprint}"
        or len(fingerprint) != DIGEST_HEX_LENGTH
        or any(
            character not in analyze.SHA256_ALPHABET
            for character in fingerprint
        )
    ):
        _fail("target study has an invalid producer toolchain fingerprint")


def _expected_case(pairs: int) -> dict[str, Any]:
    identity = f"classic-eof-echo-v1:pairs={pairs}:empty-input".encode("ascii")
    return {
        "family": producer.FAMILY,
        "version": 1,
        "difficulty": pairs,
        "seed": 0,
        "workload_sha256": sha256(identity).hexdigest(),
    }


def _expected_operations(pairs: int, algorithm: str) -> list[str]:
    chunk = ["input", "output"]
    if algorithm == producer.CANDIDATE:
        chunk = ["nop", *chunk]
    return chunk * pairs + ["halt"]


def _row_stem(row: dict[str, Any]) -> str:
    case = row["case"]
    return f"{row["algorithm"]}-pairs-{case["difficulty"]}-trial-{row["trial"]}"


def _check_row(row: dict[str, Any], prefix: str) -> str:
    case = row["case"]
    algorithm = row["algorithm"]
    if algorithm not in producer.ALGORITHMS:
        _fail("target audit trial has a foreign algorithm")
    if case != _expected_case(case["difficulty"]):
        _fail("target audit trial differs from the fixed echo case")
    if row["verifier"] != producer.VERIFIER:
        _fail("target audit trial differs from the fixed echo oracle")
    stem = _row_stem(row)
    if (
        row["experiment_manifest"] != f"{prefix}/runs/{stem}.toml"
        or row["raw_sample"] != f"{prefix}/raw/{stem}.csv"
    ):
        _fail("target audit trial path differs from the producer stem")
    return stem


def _check_levels(rows: list[dict[str, Any]]) -> set[int]:
    levels = {row["case"]["difficulty"] for row in rows}
    if not 1 <= len(levels) <= producer.MAX_LEVELS:
        _fail("target audit requires one to four difficulty levels")
    if any(not 1 <= level <= producer.MAX_PAIRS for level in levels):
        _fail("target audit difficulty exceeds the producer's 64-pair bound")
    return levels


def _check_plan(rows: list[dict[str, Any]]) -> tuple[set[int], set[int]]:
    levels = _check_levels(rows)
    trials = {row["trial"] for row in rows}
    if not 1 <= len(trials) <= producer.MAX_TRIALS:
        _fail("target audit requires one to three trial indices")
    if trials != set(range(len(trials))):
        _fail("target audit requires consecutive repetition indices")
    if len(rows) != len(levels) * len(trials) * len(producer.ALGORITHMS):
        _fail("target audit requires complete matched echo repetitions")
    return levels, trials


def _producer_rows(document: dict[str, Any], prefix: str) -> set[str]:
    rows = document["observations"]
    levels, trials = _check_plan(rows)
    names = {_check_row(row, prefix) for row in rows}
    expected = {
        f"{algorithm}-pairs-{level}-trial-{trial}"
        for level in levels
        for trial in trials
        for algorithm in producer.ALGORITHMS
    }
    if names != expected:
        _fail("target audit lacks a required paired trial")
    return names


def _check_directory(prefix: str, folder: str, expected: set[str]) -> None:
    parent = _ROOT / prefix / folder
    if parent.is_symlink() or not parent.is_dir():
        _fail(f"target audit requires ordinary {folder} directory")
    names = {entry.name for entry in parent.iterdir()}
    if names != expected:
        _fail(f"target audit has missing or unexpected {folder} files")
    for name in names:
        relative = f"{prefix}/{folder}/{name}"
        _ = evidence.regular_path(_ROOT, relative, limit=MAX_STUDY_BYTES)


def _check_provenance(document: dict[str, Any], prefix: str) -> str:
    commits: set[str] = set()
    for row in document["observations"]:
        relative = row["experiment_manifest"]
        raw = evidence.read_bounded_regular(
            _ROOT,
            relative,
            limit=evidence.MAX_MANIFEST_BYTES,
        )
        manifest = experiment_manifest.parse_manifest(raw.decode("utf-8"))
        run = manifest.run
        if run is None:
            _fail("target audit requires a recorded run manifest")
        expected = (
            experiment_manifest.RUN_RECORD_KIND,
            METHOD_CLASS,
            PRODUCER_IMPLEMENTATION,
            PRODUCER_CONFIGURATION,
            prefix,
            ACCELERATOR,
        )
        observed = (
            manifest.record_kind,
            manifest.method_class,
            manifest.implementation,
            manifest.configuration,
            manifest.output,
            run.accelerator,
        )
        if observed != expected:
            _fail("target audit manifest has foreign producer provenance")
        commits.add(run.commit)
    if len(commits) != 1:
        _fail("target audit run manifests disagree on source commit")
    return next(iter(commits))


def _decoded_instruction(cell: int, position: int) -> int:
    if not producer.GRAPHICAL_LOW <= cell <= producer.GRAPHICAL_HIGH:
        _fail("target audit source contains nongraphical code")
    phase = (cell - producer.GRAPHICAL_LOW + position) % PHASES
    return CLASSIC_DECODE[phase]


def _admit_source_bytes(source: bytes, row: dict[str, Any]) -> None:
    operations = _expected_operations(
        row["case"]["difficulty"],
        row["algorithm"],
    )
    if len(source) != len(operations):
        _fail("target audit source length differs from echo layout")
    if any(
        _decoded_instruction(cell, position) != SOURCE_INSTRUCTIONS[token]
        for position, (cell, token) in enumerate(
            zip(source, operations, strict=True)
        )
    ):
        _fail("target audit source instruction differs from echo layout")
    if row["metrics"]["artifact_bytes"] != len(source):
        _fail("target audit artifact size differs from source")


def _check_source(row: dict[str, Any], prefix: str) -> tuple[str, str]:
    relative = f"{prefix}/candidates/{_row_stem(row)}.malbolge"
    source = evidence.read_bounded_regular(
        _ROOT,
        relative,
        limit=producer.MAX_TARGET_BYTES,
    )
    _admit_source_bytes(source, row)
    return relative, sha256(source).hexdigest()


def _candidate_files(prefix: str, names: set[str]) -> None:
    directory = _ROOT / prefix / "candidates"
    if directory.is_symlink() or not directory.is_dir():
        _fail("target audit requires a real candidate directory")
    observed = {path.name for path in directory.iterdir()}
    expected = {f"{stem}.malbolge" for stem in names}
    if not observed <= expected:
        _fail("target audit has unexpected candidate source files")
    for name in observed:
        _ = evidence.regular_path(
            _ROOT,
            f"{prefix}/candidates/{name}",
            limit=producer.MAX_TARGET_BYTES,
        )


def _source_checks(
    document: dict[str, Any],
    prefix: str,
    names: set[str],
) -> dict[str, str]:
    _candidate_files(prefix, names)
    fingerprints: dict[str, str] = {}
    for row in document["observations"]:
        if row["outcome"] == analyze.VERIFIED:
            relative, fingerprint = _check_source(row, prefix)
            fingerprints[relative] = fingerprint
    return fingerprints


def _admit_tool(path: Path) -> Path:
    if not path.is_absolute():
        _fail("target audit requires absolute binary paths")
    details = path.lstat()
    if not stat.S_ISREG(details.st_mode) or details.st_size == 0:
        _fail("target audit requires regular nonempty executable files")
    return path


def _tool_identity(emitter: Path, runner: Path) -> str:
    digest = sha256()
    for path in (emitter, runner):
        digest.update(path.stat().st_size.to_bytes(8, "big"))
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    return "local-compiler-vm-sha256:" + digest.hexdigest()


def _invoke_runner(runner: Path, source: Path) -> sp.CompletedProcess[bytes]:
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(runner), str(source)],
        cwd=_ROOT,
        stdin=sp.DEVNULL,
        capture_output=True,
        check=False,
        timeout=producer.TIMEOUT_SECONDS,
    )


def _replay_one(
    row: dict[str, Any],
    relative: str,
    digest: str,
    *,
    runner: Path,
) -> None:
    execution = _invoke_runner(runner, _ROOT / relative)
    expected = bytes([producer.CLASSIC_EOF_BYTE]) * row["case"]["difficulty"]
    if execution.returncode != 0 or execution.stdout != expected:
        _fail(f"target audit VM replay rejected retained source: {relative}")
    current = evidence.read_bounded_regular(
        _ROOT,
        relative,
        limit=producer.MAX_TARGET_BYTES,
    )
    if sha256(current).hexdigest() != digest:
        _fail("target audit retained source changed during VM replay")


def _replay(
    document: dict[str, Any],
    source_hashes: dict[str, str],
    *,
    emitter: Path,
    runner: Path,
) -> int:
    emitter = _admit_tool(emitter)
    runner = _admit_tool(runner)
    claimed = document["study"]["toolchain"]
    if _tool_identity(emitter, runner) != claimed:
        _fail("target audit replay toolchain differs from recorded binaries")
    for relative, digest in source_hashes.items():
        name = relative.rsplit("/", maxsplit=1)[-1]
        row = next(
            record
            for record in document["observations"]
            if f"{_row_stem(record)}.malbolge" == name
        )
        _replay_one(row, relative, digest, runner=runner)
    if _tool_identity(emitter, runner) != claimed:
        _fail("target audit replay executables changed during execution")
    return len(source_hashes)


def _admit_study(
    relative_study: str,
    *,
    replay_candidates: bool,
    emitter: Path,
    runner: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str], str, int]:
    prefix = _prefix(relative_study)
    document = _document(relative_study)
    _producer_study(document)
    names = _producer_rows(document, prefix)
    for folder, extension in (("runs", ".toml"), ("raw", ".csv")):
        _check_directory(
            prefix,
            folder,
            {f"{stem}{extension}" for stem in names},
        )
    checked = evidence.validate_links(
        document,
        _ROOT,
        policy=evidence.EvidencePolicy(
            require_raw_rows=True,
            require_trial_run_identity=True,
            require_budget_agreement=True,
        ),
    )
    commit = _check_provenance(document, prefix)
    source_hashes = _source_checks(document, prefix, names)
    replayed = (
        _replay(document, source_hashes, emitter=emitter, runner=runner)
        if replay_candidates
        else 0
    )
    return document, checked, source_hashes, commit, replayed


def audit(
    relative_study: str,
    *,
    replay_candidates: bool = False,
    emitter: Path | None = None,
    runner: Path | None = None,
) -> dict[str, Any]:
    """Read retained target evidence and optionally replay successful sources.

    Returns:
        Source admission, optional VM witness count and arena comparison.

    Raises:
        TargetEchoAuditError: The producer evidence fails any required gate.

    """
    try:
        document, checked, source_hashes, commit, replayed = _admit_study(
            relative_study,
            replay_candidates=replay_candidates,
            emitter=emitter
            if emitter is not None
            else producer.DEFAULT_EMITTER,
            runner=runner if runner is not None else producer.DEFAULT_RUNNER,
        )
        report = analyze.analyze(document)
    except (
        analyze.ArenaError,
        evidence.EvidenceError,
        experiment_manifest.ExperimentManifestError,
        producer.TargetEchoStudyError,
        OSError,
        UnicodeError,
        sp.SubprocessError,
    ) as error:
        message = f"target echo retained study audit failed: {error}"
        raise TargetEchoAuditError(message) from error
    return {
        "schema_version": 1,
        "study": relative_study,
        "source_commit_reported": commit,
        "source_sha256": source_hashes,
        "verified_target_sources_checked": len(source_hashes),
        "target_sources_replayed": replayed,
        "reported_failed_trials_not_replayed": (
            len(document["observations"]) - len(source_hashes)
        ),
        "evidence_preflight": checked,
        "capacity_curve": report["capacity_curve"],
        "pareto_frontiers": report["pareto_frontiers"],
        "scope": (
            "Producer-specific retained classic EOF echo source admission; "
            "timings and study-wide resource budgets are not authenticated. "
            "VM replay checks only recorded successful fixed byte echoes."
        ),
    }


def main() -> int:
    """Audit one retained local target echo study and publish checked JSON.

    Returns:
        Zero for a complete audit, two for any rejected input or output.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", help=".temp/arena-target-echo-*/study.json")
    parser.add_argument("--replay-candidates", action="store_true")
    args = parser.parse_args()
    try:
        result = audit(args.study, replay_candidates=args.replay_candidates)
        report_output.publish(result, sys.stdout)
    except (TargetEchoAuditError, report_output.ReportOutputError) as error:
        parser.exit(2, f"target echo audit: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
