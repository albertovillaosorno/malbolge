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
#   - Bounded measured classic Malbolge EOF-echo geometry reference study.
# - Must-Not:
#   - Claim general C lowering, independent historical attestation, or budgets.
# - Allows:
#   - Inputs: explicit local emitter/VM executables and bounded echo sizes.
#   - Outputs: ignored local target code, run/raw receipts and arena study JSON.
#   - Side effects: external executable processes and ignored local evidence.
# - Split-When:
#   - General source/compiler benchmarks need their own correctness oracle.
# - Merge-When:
#   - A verified target-stage research runner absorbs this narrow reference.
# - Summary:
#   - Measures actual executable .malbolge code under the classic profile.
# - Description:
#   - Compares direct and redundant-nop EOF echo programs using the real VM.
# - Usage:
#   - python -B -m benchmarks.arena.target_echo_reference --pairs 1 4 16.
# - Defaults:
#   - Reject missing tools or unverified program behavior before crediting it.
#

"""Small actual-target arena reference, not a C-to-Malbolge benchmark."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from dataclasses import replace
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import platform
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
from time import perf_counter_ns
from typing import Any
from typing import Never

from scripts.validate import experiment_manifest
from scripts.validate import target_profile

from benchmarks.arena import analyze
from benchmarks.arena import evidence
from benchmarks.arena import raw_samples
from benchmarks.arena import report_output
from benchmarks.arena import target_process

_ROOT = Path(__file__).resolve().parents[2]
_TEMP = _ROOT / ".temp"
_BUILD = _ROOT / ".cache/rust/target/debug"
DEFAULT_EMITTER = _BUILD / "malbolge_layout"
DEFAULT_RUNNER = _BUILD / "malbolge"
PROFILE = "malbolge-1998"
FAMILY = "bounded-classic-eof-echo"
VERIFIER = "classic-malbolge-vm-exact-eof-byte-v1"
BASELINE = "direct-echo"
CANDIDATE = "nop-padded-echo"
ALGORITHMS = (BASELINE, CANDIDATE)
MAX_PAIRS = 64
MAX_LEVELS = 4
MAX_TRIALS = 3
MAX_TARGET_BYTES = 256
COMMIT_HEX_WIDTH = 40
GRAPHICAL_LOW = 33
GRAPHICAL_HIGH = 126
TIMEOUT_SECONDS = 15
BUDGET_SECONDS = 60
BUDGET_MIB = 1024
CLASSIC_EOF_BYTE = 0xA8
EOF_MODE = "eof"
PATTERNED_MODE = "patterned"
INPUT_MODES = (EOF_MODE, PATTERNED_MODE)
PATTERN_BYTES = (0, 255, 168, 90, 128, 1, 127, 254)
PATTERNED_FAMILY = "bounded-classic-patterned-byte-echo"
PATTERNED_VERIFIER = "classic-malbolge-vm-exact-patterned-byte-v1"
PATTERNED_STUDY = "classic-patterned-byte-echo-geometry-v1"


class TargetEchoStudyError(ValueError):
    """The bounded target benchmark cannot establish its claimed evidence."""


@dataclass(frozen=True, slots=True)
class StudyPlan:
    """Explicit bounded source geometry and matched repetitions."""

    pairs: tuple[int, ...]
    trials: int
    input_mode: str = EOF_MODE


@dataclass(frozen=True, slots=True)
class _Context:
    directory: Path
    prefix: str
    fingerprint: str
    commit: str
    host: str
    toolchain: str
    emitter: Path
    runner: Path
    input_mode: str = EOF_MODE


def _fail(message: str) -> Never:
    raise TargetEchoStudyError(message)


def _validate_plan(plan: StudyPlan) -> None:
    if not 1 <= len(plan.pairs) <= MAX_LEVELS:
        _fail("target echo requires between one and four difficulty levels")
    if len(set(plan.pairs)) != len(plan.pairs):
        _fail("target echo difficulty levels must be distinct")
    if any(
        type(value) is not int or not 1 <= value <= MAX_PAIRS
        for value in plan.pairs
    ):
        _fail("target echo requires 1..64 input/output pairs per level")
    if type(plan.trials) is not int or not 1 <= plan.trials <= MAX_TRIALS:
        _fail("target echo requires one to three paired trials")


def _validate_input_mode(mode: str) -> None:
    if type(mode) is not str or mode not in INPUT_MODES:
        _fail("target echo input mode must be eof or patterned")


def _admit_executable(path: Path) -> Path:
    if not path.is_absolute():
        _fail("target echo executables must have explicit absolute paths")
    try:
        details = path.lstat()
    except OSError as error:
        message = "target echo executable is missing"
        raise TargetEchoStudyError(message) from error
    if not path.is_file() or path.is_symlink() or details.st_size == 0:
        _fail("target echo executables must be ordinary nonempty files")
    return path


def _tool_identity(emitter: Path, runner: Path) -> str:
    # Exact executable-byte fingerprint; it is provenance, not host attestation.
    digest = sha256()
    for path in (emitter, runner):
        digest.update(path.stat().st_size.to_bytes(8, "big"))
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    return "local-compiler-vm-sha256:" + digest.hexdigest()


def _commit() -> str:
    try:
        git = shutil.which("git")
        if git is None:
            _fail("target echo reference requires Git")
        output = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [git, "rev-parse", "HEAD"],
            cwd=_ROOT,
            capture_output=True,
            check=True,
            timeout=5,
            text=True,
        )
    except (OSError, sp.SubprocessError) as error:
        message = "target echo reference cannot bind source revision"
        raise TargetEchoStudyError(message) from error
    commit = output.stdout.strip()
    if (
        len(commit) != COMMIT_HEX_WIDTH
        or not set(commit) <= analyze.SHA256_ALPHABET
    ):
        _fail("target echo reference has invalid Git revision")
    return commit


def _input_bytes(pairs: int, mode: str) -> bytes:
    if mode == EOF_MODE:
        return b""
    return bytes(
        PATTERN_BYTES[index % len(PATTERN_BYTES)] for index in range(pairs)
    )


def _operations(pairs: int, algorithm: str, mode: str = EOF_MODE) -> list[str]:
    step = ["input", "output"]
    if algorithm == CANDIDATE:
        step.insert(0, "nop")
    emitted_pairs = pairs + int(mode == PATTERNED_MODE)
    return [*step * emitted_pairs, "halt"]


def _invoke(command: list[str]) -> sp.CompletedProcess[bytes]:
    return target_process.invoke(command, timeout_seconds=TIMEOUT_SECONDS)


def _case(pairs: int, mode: str = EOF_MODE) -> dict[str, Any]:
    if mode == EOF_MODE:
        workload = f"classic-eof-echo-v1:pairs={pairs}:empty-input".encode(
            "ascii"
        )
    else:
        payload = _input_bytes(pairs, mode)
        workload = (
            f"classic-patterned-byte-echo-v1:pairs={pairs}:"
            f"input={payload.hex()}:eof-after"
        ).encode("ascii")
    return {
        "family": FAMILY if mode == EOF_MODE else PATTERNED_FAMILY,
        "version": 1,
        "difficulty": pairs,
        "seed": 0,
        "workload_sha256": sha256(workload).hexdigest(),
    }


def _classify_attempt(
    path: Path,
    context: _Context,
    operations: list[str],
    *,
    pairs: int,
) -> tuple[str, int | None]:
    emitted = _invoke([
        str(context.emitter),
        "--profile",
        PROFILE,
        "--output",
        str(path),
        "--",
        *operations,
    ])
    if emitted.returncode != 0 or emitted.stdout or not path.is_file():
        return "tool_failed", None
    source = evidence.read_bounded_regular(
        _ROOT,
        path.relative_to(_ROOT).as_posix(),
        limit=MAX_TARGET_BYTES,
    )
    if len(source) != len(operations) or not all(
        GRAPHICAL_LOW <= byte <= GRAPHICAL_HIGH for byte in source
    ):
        return analyze.VERIFIER_REJECTED, None
    payload = _input_bytes(pairs, context.input_mode)
    execution = (
        _invoke([str(context.runner), str(path)])
        if context.input_mode == EOF_MODE
        else target_process.invoke_with_input(
            [str(context.runner), str(path), "--input-stdin"],
            payload,
            timeout_seconds=TIMEOUT_SECONDS,
        )
    )
    expected = (
        bytes([CLASSIC_EOF_BYTE]) * pairs
        if context.input_mode == EOF_MODE
        else payload + bytes([CLASSIC_EOF_BYTE])
    )
    outcome = (
        "tool_failed"
        if execution.returncode != 0
        else analyze.VERIFIED
        if execution.stdout == expected
        else analyze.VERIFIER_REJECTED
    )
    return outcome, len(source) if outcome == analyze.VERIFIED else None


def _measure(
    path: Path,
    context: _Context,
    pairs: int,
    *,
    algorithm: str,
) -> tuple[str, dict[str, int]]:
    started = perf_counter_ns()
    try:
        outcome, size = _classify_attempt(
            path,
            context,
            _operations(pairs, algorithm, context.input_mode),
            pairs=pairs,
        )
    except OSError, sp.SubprocessError, evidence.EvidenceError:
        outcome, size = "tool_failed", None
    metrics = {"elapsed_ns": perf_counter_ns() - started}
    if size is not None:
        metrics["artifact_bytes"] = size
    return outcome, metrics


def _raw_csv(row: dict[str, Any]) -> bytes:
    case = row["case"]
    fields = {
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
        **{name: str(value) for name, value in row["metrics"].items()},
    }
    stream = StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(raw_samples.HEADER)
    writer.writerow([fields.get(name, "") for name in raw_samples.HEADER])
    return stream.getvalue().encode("utf-8")


def _manifest(
    row: dict[str, Any],
    context: _Context,
    raw_hash: str,
) -> str:
    case = row["case"]
    quote = json.dumps
    lines = [
        "schema_version = 1",
        "",
        "[experiment]",
        f"id = {quote(row["algorithm"])}",
        'record_kind = "run"',
        'method_class = "benchmarking"',
        "seed = 0",
        "",
        "[challenge]",
        f"family = {quote(case["family"])}",
        f"difficulty = {case["difficulty"]}",
        f"target_profile = {quote(PROFILE)}",
        f"target_profile_fingerprint = {quote(context.fingerprint)}",
        "",
        "[budget]",
        f"seconds = {BUDGET_SECONDS}",
        f"memory_mib = {BUDGET_MIB}",
        "",
        "[verification]",
        "required = true",
        f"oracle = {quote(row["verifier"])}",
        "",
        "[provenance]",
        'implementation = "benchmarks/arena/target_echo_reference.py"',
        'configuration = "benchmarks/arena/README.md"',
        f"output = {quote(context.prefix)}",
        "",
        "[run]",
        f"commit = {quote(context.commit)}",
        f"workload_sha256 = {quote(case["workload_sha256"])}",
        f"host = {quote(context.host)}",
        'accelerator = "none"',
        f"toolchain = {quote(context.toolchain)}",
        f"outcome = {quote(evidence.RUN_OUTCOMES[row["outcome"]])}",
        f"raw_output = {quote(row["raw_sample"])}",
        "",
        "[arena_trial]",
        "schema_version = 1",
        f"trial = {row["trial"]}",
        f"raw_sha256 = {quote(raw_hash)}",
        "",
    ]
    text = "\n".join(lines)
    experiment_manifest.parse_manifest(text)
    return text


def _prepare_context(emitter: Path, runner: Path) -> _Context:
    emitter, runner = _admit_executable(emitter), _admit_executable(runner)
    if not _TEMP.is_dir():
        _fail("target echo reference requires repository .temp directory")
    directory = Path(tempfile.mkdtemp(prefix="arena-target-echo-", dir=_TEMP))
    for name in ("runs", "raw", "candidates"):
        (directory / name).mkdir()
    profile = target_profile.load_document(_ROOT / "malbolge.json")
    return _Context(
        directory=directory,
        prefix=directory.relative_to(_ROOT).as_posix(),
        fingerprint=target_profile.profile_fingerprint(profile, PROFILE),
        commit=_commit(),
        host=platform.platform(),
        toolchain=_tool_identity(emitter, runner),
        emitter=emitter,
        runner=runner,
    )


def _write_attempt(
    context: _Context,
    pairs: int,
    trial: int,
    *,
    algorithm: str,
) -> dict[str, Any]:
    stem = f"{algorithm}-pairs-{pairs}-trial-{trial}"
    artifact = context.directory / "candidates" / f"{stem}.malbolge"
    outcome, metrics = _measure(artifact, context, pairs, algorithm=algorithm)
    verdict = {
        analyze.VERIFIED: analyze.ACCEPTED,
        analyze.VERIFIER_REJECTED: analyze.REJECTED,
    }.get(outcome, analyze.NOT_RUN)
    row = {
        "algorithm": algorithm,
        "case": _case(pairs, context.input_mode),
        "trial": trial,
        "outcome": outcome,
        "verifier": (
            VERIFIER if context.input_mode == EOF_MODE else PATTERNED_VERIFIER
        ),
        "verifier_verdict": verdict,
        "experiment_manifest": f"{context.prefix}/runs/{stem}.toml",
        "raw_sample": f"{context.prefix}/raw/{stem}.csv",
        "metrics": metrics,
    }
    raw = _raw_csv(row)
    (context.directory / "raw" / f"{stem}.csv").write_bytes(raw)
    receipt = _manifest(row, context, sha256(raw).hexdigest())
    (context.directory / "runs" / f"{stem}.toml").write_text(
        receipt,
        encoding="utf-8",
    )
    return row


def _make_document(
    context: _Context,
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    patterned = context.input_mode == PATTERNED_MODE
    return {
        "schema_version": 1,
        "study": {
            "id": PATTERNED_STUDY
            if patterned
            else "classic-eof-echo-geometry-v1",
            "question": (
                "Does padding worsen the classic patterned byte-echo frontier?"
                if patterned
                else (
                    "Does redundant no-op padding worsen the "
                    "classic VM frontier?"
                )
            ),
            "hypothesis": "Direct code is smaller than no-op padded code.",
            "rejection_observation": (
                "Padded code is not larger or direct fails "
                "its patterned-byte oracle."
                if patterned
                else "Padded code is not larger or direct fails its EOF oracle."
            ),
            "baseline": BASELINE,
            "stage": "measured-classic-malbolge-code-and-vm",
            "target_profile": PROFILE,
            "host": context.host,
            "toolchain": context.toolchain,
            "budget": {
                "time_ns": BUDGET_SECONDS * 1_000_000_000,
                "memory_bytes": BUDGET_MIB * 1_048_576,
            },
            "objectives": ["elapsed_ns", "artifact_bytes"],
        },
        "observations": observations,
    }


def _audit_retained_study(path: Path) -> dict[str, Any]:
    """Admit the complete retained source graph before returning a study.

    Returns:
        Strictly parsed version-one study after producer-specific source audit.

    Raises:
        TargetEchoStudyError: A retained candidate or source claim is invalid.

    """
    # The read-only auditor owns inverse decoding, not the emitting backend.
    from benchmarks.arena import target_echo_audit  # ruff: ignore[import-outside-top-level]

    relative = path.relative_to(_ROOT).as_posix()
    try:
        _ = target_echo_audit.audit(relative)
    except target_echo_audit.TargetEchoAuditError as error:
        message = f"target echo source admission failed: {error}"
        raise TargetEchoStudyError(message) from error
    return analyze.parse_document(path.read_text(encoding="utf-8"))


def run_study(
    plan: StudyPlan,
    *,
    emitter: Path = DEFAULT_EMITTER,
    runner: Path = DEFAULT_RUNNER,
) -> tuple[Path, dict[str, Any]]:
    """Retain real classic executable/source and reported paired measurements.

    Returns:
        Ignored local study directory and admitted report.

    """
    _validate_plan(plan)
    _validate_input_mode(plan.input_mode)
    context = replace(
        _prepare_context(emitter, runner), input_mode=plan.input_mode
    )
    observations = [
        _write_attempt(context, pairs, trial, algorithm=algorithm)
        for pairs in plan.pairs
        for trial in range(plan.trials)
        for algorithm in (ALGORITHMS if trial % 2 == 0 else ALGORITHMS[::-1])
    ]
    document = _make_document(context, observations)
    path = context.directory / "study.json"
    path.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n")
    admitted = _audit_retained_study(path)
    if _tool_identity(context.emitter, context.runner) != context.toolchain:
        _fail("target echo executables changed during the measured study")
    return context.directory, admitted


def main() -> int:
    """Run a bounded measured classic target geometry reference.

    Returns:
        Zero after a valid local study or two on rejected setup/evidence.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, nargs="+", default=[1, 4, 16])
    parser.add_argument("--trials", type=int, default=2)
    parser.add_argument("--input-mode", choices=INPUT_MODES, default=EOF_MODE)
    args = parser.parse_args()
    try:
        directory, document = run_study(
            StudyPlan(tuple(args.pairs), args.trials, args.input_mode)
        )
        report_output.publish(
            {
                "study": (directory / "study.json")
                .relative_to(_ROOT)
                .as_posix(),
                "observations": len(document["observations"]),
                "scope": (
                    "Actual classic VM execution with bounded I/O oracle; "
                    "unattested time and unenforced study-wide RAM budget; "
                    "not general C/ternary code generation."
                ),
            },
            sys.stdout,
        )
    except (
        TargetEchoStudyError,
        analyze.ArenaError,
        evidence.EvidenceError,
        experiment_manifest.ExperimentManifestError,
        OSError,
        sp.SubprocessError,
        report_output.ReportOutputError,
    ) as error:
        parser.exit(2, f"target echo reference: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
