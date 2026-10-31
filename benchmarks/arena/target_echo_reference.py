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
#   - Claim C lowering, historical attestation or study-wide resource caps.
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
import json
import os
import platform
import shutil
import stat
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
from dataclasses import dataclass, replace
from hashlib import sha256
from io import StringIO
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Never

from benchmarks.arena import (
    analyze,
    evidence,
    raw_samples,
    report_output,
    target_process,
)
from scripts.validate import experiment_manifest, target_profile

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
MAX_TOOL_BYTES = 128 * 1024 * 1024
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
EOF_STEPS_STUDY = "classic-eof-echo-steps-v2"
PATTERNED_STEPS_STUDY = "classic-patterned-byte-echo-steps-v2"
STEPS_PREFIX = b"malbolge-steps-v1:"
RUNTIME_STEPS = "runtime_steps"
MAX_STEPS_DIGITS = 20
LINEAR_LAYOUT = "linear"
FORWARD_SKIP_LAYOUT = "forward-skip"
LAYOUT_MODES = (LINEAR_LAYOUT, FORWARD_SKIP_LAYOUT)
WALK = "walk-padding-echo"
SKIP = "jump-skip-padding-echo"
FORWARD_ALGORITHMS = (WALK, SKIP)
FORWARD_STUDY = "classic-patterned-forward-skip-steps-v1"
FORWARD_VERIFIER_COST_STUDY = "classic-patterned-forward-skip-verifier-cost-v2"
FORWARD_REPLAY_COST_STUDY = "classic-patterned-forward-skip-replay-cost-v3"
FORWARD_LIMITED_REPLAY_STUDY = (
    "classic-patterned-forward-skip-limited-replay-v4"
)
FORWARD_RSS_STUDY = "classic-patterned-forward-skip-limited-rss-v5"
FORWARD_RSS_RECEIPTS_STUDY = "classic-patterned-forward-skip-rss-receipts-v6"
FORWARD_RAW_RSS_STUDY = "classic-patterned-forward-skip-raw-rss-v7"
SOURCE_VERIFIER_MODE = "source"
REPLAY_VERIFIER_MODE = "replay"
VERIFIER_MODES = (SOURCE_VERIFIER_MODE, REPLAY_VERIFIER_MODE)
VERIFIER_NS = "verifier_ns"
FORWARD_FAMILY = "bounded-classic-patterned-forward-skip-echo"
FORWARD_VERIFIER = "classic-forward-jump-patterned-byte-and-steps-v1"
FORWARD_REPLAY_VERIFIER = "classic-forward-jump-patterned-second-vm-v1"
FORWARD_LIMITED_REPLAY_VERIFIER = "classic-forward-jump-limited-second-vm-v1"
FORWARD_RSS_VERIFIER = "classic-forward-jump-limited-rss-second-vm-v1"
FORWARD_RSS_RECEIPTS_VERIFIER = "classic-forward-jump-rss-receipts-second-vm-v1"
FORWARD_RAW_RSS_VERIFIER = "classic-forward-jump-raw-rss-second-vm-v1"
PEAK_RSS = "peak_rss_bytes"
RSS_MEASURED_STAGES = 3
JUMP_OPERATION = "jump"
SKIPPED_NOOPS = 98
WALKED_NOOPS = SKIPPED_NOOPS + 1


class TargetEchoStudyError(ValueError):
    """The bounded target benchmark cannot establish its claimed evidence."""


@dataclass(frozen=True, slots=True)
class StudyPlan:
    """Explicit bounded source geometry and matched repetitions."""

    pairs: tuple[int, ...]
    trials: int
    input_mode: str = EOF_MODE
    measure_steps: bool = False
    layout_mode: str = LINEAR_LAYOUT
    measure_verifier: bool = False
    verifier_mode: str = SOURCE_VERIFIER_MODE
    limit_child_resources: bool = False
    measure_child_rss: bool = False
    retain_rss_stages: bool = False
    retain_raw_rss: bool = False


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
    measure_steps: bool = False
    layout_mode: str = LINEAR_LAYOUT
    measure_verifier: bool = False
    verifier_mode: str = SOURCE_VERIFIER_MODE
    limit_child_resources: bool = False
    measure_child_rss: bool = False
    retain_rss_stages: bool = False
    retain_raw_rss: bool = False
    rss_stages: list[int] | None = None
    raw_rss_stages: list[bytes] | None = None


def _fail(message: str) -> Never:
    raise TargetEchoStudyError(message)


def _validate_plan(plan: StudyPlan) -> None:
    if type(plan) is not StudyPlan:
        _fail("target echo requires an exact StudyPlan")
    if type(plan.pairs) is not tuple:
        _fail("target echo pairs require an exact tuple of integers")
    if not 1 <= len(plan.pairs) <= MAX_LEVELS:
        _fail("target echo requires between one and four difficulty levels")
    if any(type(value) is not int for value in plan.pairs):
        _fail("target echo pairs require an exact tuple of integers")
    if len(set(plan.pairs)) != len(plan.pairs):
        _fail("target echo difficulty levels must be distinct")
    if any(not 1 <= value <= MAX_PAIRS for value in plan.pairs):
        _fail("target echo requires 1..64 input/output pairs per level")
    if type(plan.trials) is not int or not 1 <= plan.trials <= MAX_TRIALS:
        _fail("target echo requires one to three paired trials")


def _validate_input_mode(mode: str) -> None:
    if type(mode) is not str or mode not in INPUT_MODES:
        _fail("target echo input mode must be eof or patterned")


def _admit_executable(path: Path) -> Path:
    if type(path) is not type(Path()):
        _fail("target echo executables require an exact native Path")
    if not path.is_absolute():
        _fail("target echo executables must have explicit absolute paths")
    try:
        details = path.lstat()
    except OSError as error:
        message = "target echo executable is missing"
        raise TargetEchoStudyError(message) from error
    if not path.is_file() or path.is_symlink() or details.st_size <= 0:
        _fail("target echo executables must be ordinary nonempty files")
    if details.st_size > MAX_TOOL_BYTES:
        _fail("target echo executable exceeds 128 MiB limit")
    return path


def _tool_file_identity(details: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        details.st_dev,
        details.st_ino,
        details.st_size,
        details.st_mtime_ns,
        details.st_ctime_ns,
    )


def _tool_identity(emitter: Path, runner: Path) -> str:
    # Hash admitted regular descriptors, not a newly followed pathname.
    # The same size framing preserves all prior toolchain digest values.
    digest = sha256()
    for path in (emitter, runner):
        try:
            original = path.lstat()
            if not stat.S_ISREG(original.st_mode) or original.st_size <= 0:
                _fail("target echo executable identity changed")
            if original.st_size > MAX_TOOL_BYTES:
                _fail("target echo executable exceeds 128 MiB limit")
            flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(
                os, "O_NOFOLLOW", 0
            )
            descriptor = os.open(path, flags)
            try:
                opened = os.fstat(descriptor)
                if not stat.S_ISREG(opened.st_mode) or (
                    _tool_file_identity(opened) != _tool_file_identity(original)
                ):
                    _fail("target echo executable identity changed")
                digest.update(opened.st_size.to_bytes(8, "big"))
                remaining = opened.st_size
                while remaining:
                    chunk = os.read(descriptor, min(remaining, 1024 * 1024))
                    if not chunk:
                        _fail("target echo executable identity changed")
                    digest.update(chunk)
                    remaining -= len(chunk)
                if os.read(descriptor, 1) or (
                    _tool_file_identity(os.fstat(descriptor))
                    != _tool_file_identity(opened)
                ):
                    _fail("target echo executable identity changed")
            finally:
                primary = sys.exception()
                try:
                    os.close(descriptor)
                except OSError as cleanup_error:
                    if primary is None:
                        raise
                    primary.add_note(
                        f"target echo executable descriptor cleanup failed: {cleanup_error}"
                    )
            latest = path.lstat()
            if not stat.S_ISREG(latest.st_mode) or (
                _tool_file_identity(latest) != _tool_file_identity(original)
            ):
                _fail("target echo executable identity changed")
        except OSError as error:
            message = "target echo executable identity changed"
            raise TargetEchoStudyError(message) from error
    return "local-compiler-vm-sha256:" + digest.hexdigest()


def _commit() -> str:
    try:
        git = shutil.which("git", path=os.defpath)
        if git is None:
            _fail("target echo reference requires Git")
        # Source revision must belong to this checkout, not an ambient Git dir.
        clean_env = {
            name: value
            for name, value in os.environ.items()
            if not name.startswith("GIT_")
        }
        output = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [git, "rev-parse", "HEAD"],
            cwd=_ROOT,
            stdin=sp.DEVNULL,
            env=clean_env,
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


def _parse_step_receipt(stderr: bytes) -> int:
    if (
        not stderr.startswith(STEPS_PREFIX)
        or not stderr.endswith(b"\n")
        or stderr.count(b"\n") != 1
    ):
        _fail("target VM returned no canonical step receipt")
    digits = stderr[len(STEPS_PREFIX) : -1]
    if not 1 <= len(digits) <= MAX_STEPS_DIGITS or not digits.isdigit():
        _fail("target VM returned malformed step count")
    if len(digits) > 1 and digits.startswith(b"0"):
        _fail("target VM returned noncanonical step count")
    return int(digits)


def _algorithms(layout_mode: str) -> tuple[str, str]:
    return (
        FORWARD_ALGORITHMS if layout_mode == FORWARD_SKIP_LAYOUT else ALGORITHMS
    )


def _operations(
    pairs: int,
    algorithm: str,
    mode: str = EOF_MODE,
    *,
    layout_mode: str = LINEAR_LAYOUT,
) -> list[str]:
    if layout_mode == FORWARD_SKIP_LAYOUT:
        echo = ["input", "output"] * (pairs + 1) + ["halt"]
        return (
            ["nop"] * WALKED_NOOPS + echo
            if algorithm == WALK
            else [JUMP_OPERATION, *echo]
        )
    step = ["input", "output"]
    if algorithm == CANDIDATE:
        step.insert(0, "nop")
    emitted_pairs = pairs + int(mode == PATTERNED_MODE)
    return [*step * emitted_pairs, "halt"]


def _invoke(command: list[str]) -> sp.CompletedProcess[bytes]:
    return target_process.invoke(command, timeout_seconds=TIMEOUT_SECONDS)


def _case(
    pairs: int, mode: str = EOF_MODE, layout_mode: str = LINEAR_LAYOUT
) -> dict[str, Any]:
    if layout_mode == FORWARD_SKIP_LAYOUT:
        payload = _input_bytes(pairs, mode)
        workload = (
            f"classic-forward-skip-byte-v1:pairs={pairs}:"
            f"input={payload.hex()}:eof-after"
        ).encode("ascii")
    elif mode == EOF_MODE:
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
        "family": (
            FORWARD_FAMILY
            if layout_mode == FORWARD_SKIP_LAYOUT
            else FAMILY
            if mode == EOF_MODE
            else PATTERNED_FAMILY
        ),
        "version": 1,
        "difficulty": pairs,
        "seed": 0,
        "workload_sha256": sha256(workload).hexdigest(),
    }


def _measure_guest_rss(
    context: _Context, command: list[str], pairs: int
) -> sp.CompletedProcess[bytes]:
    stages = context.rss_stages
    if stages is None:
        _fail("target echo RSS measurement missing per-trial stage witness")
    if context.retain_raw_rss:
        result, peak, raw = (
            target_process.invoke_with_input_limited_measured_raw(
                command,
                _input_bytes(pairs, context.input_mode),
                timeout_seconds=TIMEOUT_SECONDS,
            )
        )
        if context.raw_rss_stages is None:
            _fail("target echo raw RSS measurements need an owned stage list")
        context.raw_rss_stages.append(raw)
    else:
        result, peak = target_process.invoke_with_input_limited_measured(
            command,
            _input_bytes(pairs, context.input_mode),
            timeout_seconds=TIMEOUT_SECONDS,
        )
    stages.append(peak)
    return result


def _run_guest(
    context: _Context, path: Path, pairs: int
) -> sp.CompletedProcess[bytes]:
    command = [str(context.runner), str(path)]
    if context.input_mode == PATTERNED_MODE:
        command.append("--input-stdin")
    if context.measure_steps:
        command.append("--report-steps")
    if context.measure_child_rss:
        return _measure_guest_rss(context, command, pairs)
    if context.input_mode == EOF_MODE:
        return (
            target_process.invoke_limited(
                command, timeout_seconds=TIMEOUT_SECONDS
            )
            if context.limit_child_resources
            else _invoke(command)
        )
    method = (
        target_process.invoke_with_input_limited
        if context.limit_child_resources
        else target_process.invoke_with_input
    )
    return method(
        command,
        _input_bytes(pairs, context.input_mode),
        timeout_seconds=TIMEOUT_SECONDS,
    )


def _verified_steps(
    execution: sp.CompletedProcess[bytes],
    context: _Context,
    outcome: str,
) -> tuple[str, int | None]:
    if outcome != analyze.VERIFIED or not context.measure_steps:
        return outcome, None
    try:
        return outcome, _parse_step_receipt(execution.stderr)
    except TargetEchoStudyError:
        return "tool_failed", None


def _emit_attempt(
    context: _Context, command: list[str]
) -> sp.CompletedProcess[bytes]:
    if context.measure_child_rss:
        stages = context.rss_stages
        if stages is None:
            _fail("target echo RSS measurement missing per-trial stage witness")
        if context.retain_raw_rss:
            result, peak, raw = target_process.invoke_limited_measured_raw(
                command, timeout_seconds=TIMEOUT_SECONDS
            )
            if context.raw_rss_stages is None:
                _fail(
                    "target echo raw RSS measurements need an owned stage list"
                )
            context.raw_rss_stages.append(raw)
        else:
            result, peak = target_process.invoke_limited_measured(
                command, timeout_seconds=TIMEOUT_SECONDS
            )
        stages.append(peak)
        return result
    return (
        target_process.invoke_limited(command, timeout_seconds=TIMEOUT_SECONDS)
        if context.limit_child_resources
        else _invoke(command)
    )


def _classify_attempt(
    path: Path,
    context: _Context,
    operations: list[str],
    *,
    pairs: int,
) -> tuple[str, int | None, int | None]:
    command = [
        str(context.emitter),
        "--profile",
        PROFILE,
        "--output",
        str(path),
        "--",
    ]
    if (
        context.layout_mode == FORWARD_SKIP_LAYOUT
        and operations[0] == JUMP_OPERATION
    ):
        command.append("--auto-layout")
    emitted = _emit_attempt(context, [*command, *operations])
    if emitted.returncode != 0 or emitted.stdout or not path.is_file():
        return "tool_failed", None, None
    source = evidence.read_bounded_regular(
        _ROOT,
        path.relative_to(_ROOT).as_posix(),
        limit=MAX_TARGET_BYTES,
    )
    expected_length = (
        2 * (pairs + 1) + WALKED_NOOPS + 1
        if context.layout_mode == FORWARD_SKIP_LAYOUT
        else len(operations)
    )
    if len(source) != expected_length or not all(
        GRAPHICAL_LOW <= byte <= GRAPHICAL_HIGH for byte in source
    ):
        return analyze.VERIFIER_REJECTED, None, None
    execution = _run_guest(context, path, pairs)
    expected = (
        bytes([CLASSIC_EOF_BYTE]) * pairs
        if context.input_mode == EOF_MODE
        else _input_bytes(pairs, context.input_mode) + bytes([CLASSIC_EOF_BYTE])
    )
    outcome = (
        "tool_failed"
        if execution.returncode != 0
        else analyze.VERIFIED
        if execution.stdout == expected
        else analyze.VERIFIER_REJECTED
    )
    outcome, measured_steps = _verified_steps(execution, context, outcome)
    return (
        outcome,
        len(source) if outcome == analyze.VERIFIED else None,
        measured_steps if outcome == analyze.VERIFIED else None,
    )


def _timed_source_verifier(path: Path, pairs: int, algorithm: str) -> int:
    """Time only the independently decoded source admission, not VM replay.

    Returns:
        Observed wall nanoseconds spent opening and checking one source.

    """
    from benchmarks.arena import (
        target_echo_audit,  # ruff: ignore[import-outside-top-level]
    )

    started = perf_counter_ns()
    source = evidence.read_bounded_regular(
        _ROOT, path.relative_to(_ROOT).as_posix(), limit=MAX_TARGET_BYTES
    )
    target_echo_audit.check_forward_candidate_source(
        source, pairs=pairs, algorithm=algorithm
    )
    return perf_counter_ns() - started


def _timed_replay_verifier(
    path: Path,
    context: _Context,
    case: tuple[int, str],
    *,
    steps: int | None,
) -> int:
    """Time independent source admission and a second exact VM execution.

    Returns:
        Wall nanoseconds of the entire verifier pass, including VM startup.

    Raises:
        TargetProcessError: The measured verifier child omitted an RSS sample.

    """
    from benchmarks.arena import (
        target_echo_audit,  # ruff: ignore[import-outside-top-level]
    )

    started = perf_counter_ns()
    peak = target_echo_audit.check_forward_vm_replay(
        path,
        context.runner,
        case=case,
        replay_options=(
            steps,
            context.limit_child_resources,
            context.measure_child_rss,
            context.raw_rss_stages if context.retain_raw_rss else None,
        ),
    )
    if context.measure_child_rss:
        if peak is None or context.rss_stages is None:
            message = "target echo RSS verifier is missing per-trial witness"
            raise target_process.TargetProcessError(message)
        context.rss_stages.append(peak)
    return perf_counter_ns() - started


def _optional_verifier_cost(
    path: Path,
    context: _Context,
    attempt: tuple[str, int | None, int | None],
    *,
    case: tuple[int, str],
) -> tuple[tuple[str, int | None, int | None], int | None]:
    if attempt[0] != analyze.VERIFIED or not context.measure_verifier:
        return attempt, None
    from benchmarks.arena import (
        target_echo_audit,  # ruff: ignore[import-outside-top-level]
    )

    timing = None
    try:
        timing = (
            _timed_replay_verifier(path, context, case, steps=attempt[2])
            if context.verifier_mode == REPLAY_VERIFIER_MODE
            else _timed_source_verifier(path, *case)
        )
    except target_echo_audit.TargetReplayToolError:
        attempt = ("tool_failed", None, None)
    except target_echo_audit.TargetEchoAuditError:
        attempt = (analyze.VERIFIER_REJECTED, None, None)
    except OSError, sp.SubprocessError, evidence.EvidenceError:
        attempt = ("tool_failed", None, None)
    return attempt, timing


def _measure(
    path: Path,
    context: _Context,
    pairs: int,
    *,
    algorithm: str,
) -> tuple[str, dict[str, int]]:
    started = perf_counter_ns()
    try:
        outcome, size, steps = _classify_attempt(
            path,
            context,
            _operations(
                pairs,
                algorithm,
                context.input_mode,
                layout_mode=context.layout_mode,
            ),
            pairs=pairs,
        )
    except OSError, sp.SubprocessError, evidence.EvidenceError:
        outcome, size, steps = "tool_failed", None, None
    (outcome, size, steps), verification_ns = _optional_verifier_cost(
        path, context, (outcome, size, steps), case=(pairs, algorithm)
    )
    return _finalize_attempt_metrics(
        context,
        (outcome, size, steps, verification_ns),
        elapsed_ns=perf_counter_ns() - started,
    )


def _finalize_attempt_metrics(
    context: _Context,
    attempt: tuple[str, int | None, int | None, int | None],
    *,
    elapsed_ns: int,
) -> tuple[str, dict[str, int]]:
    outcome, size, steps, verification_ns = attempt
    metrics = {"elapsed_ns": elapsed_ns}
    if size is not None:
        metrics["artifact_bytes"] = size
    if steps is not None:
        metrics[RUNTIME_STEPS] = steps
    if verification_ns is not None and outcome == analyze.VERIFIED:
        metrics[VERIFIER_NS] = verification_ns
    return _admit_peak_rss(context, outcome, metrics), metrics


def _complete_raw_rss_stages(context: _Context) -> bool:
    if not context.retain_raw_rss:
        return True
    readings = context.raw_rss_stages
    return readings is not None and len(readings) == RSS_MEASURED_STAGES


def _admit_peak_rss(
    context: _Context, outcome: str, metrics: dict[str, int]
) -> str:
    if not context.measure_child_rss or outcome != analyze.VERIFIED:
        return outcome
    stages = context.rss_stages or []
    if (
        not _complete_raw_rss_stages(context)
        or len(stages) != RSS_MEASURED_STAGES
        or any(
            type(value) is not int
            or value <= 0
            or value > target_process.CHILD_VIRTUAL_MEMORY_BYTES
            or value % target_process.KIB_BYTES != 0
            for value in stages
        )
    ):
        elapsed_ns = metrics["elapsed_ns"]
        metrics.clear()
        metrics["elapsed_ns"] = elapsed_ns
        return "tool_failed"
    metrics[PEAK_RSS] = max(stages)
    return outcome


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
    *,
    rss_hash: str | None = None,
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
    if context.retain_rss_stages and row["outcome"] == analyze.VERIFIED:
        if rss_hash is None:
            _fail("retained RSS stage receipt digest is required")
        lines.extend([
            "[arena_rss]",
            f"schema_version = {2 if context.retain_raw_rss else 1}",
            f"sha256 = {quote(rss_hash)}",
            "",
        ])
    text = "\n".join(lines)
    experiment_manifest.parse_manifest(text)
    return text


def _initialize_workspace_folders(directory: Path, names: tuple[str, ...]) -> None:
    """Create study subdirectories with typed failure and owned cleanup."""
    try:
        for name in names:
            (directory / name).mkdir()
    except OSError as error:
        # Only remove the unique study directory created by this invocation.
        # A cleanup failure must not erase the original setup failure.
        try:
            shutil.rmtree(directory)
        except OSError as cleanup_error:
            error.add_note(f"target echo workspace cleanup failed: {cleanup_error}")
        message = "target echo study workspace initialization failed"
        raise TargetEchoStudyError(message) from error


def _prepare_context(emitter: Path, runner: Path) -> _Context:
    emitter, runner = _admit_executable(emitter), _admit_executable(runner)
    try:
        workspace = _TEMP.lstat()
    except OSError as error:
        message = "target echo reference requires repository .temp directory"
        raise TargetEchoStudyError(message) from error
    if not stat.S_ISDIR(workspace.st_mode):
        _fail("target echo reference requires repository .temp directory")
    # Validate identity before retaining any study output.
    profile = target_profile.load_document(_ROOT / "malbolge.json")
    fingerprint = target_profile.profile_fingerprint(profile, PROFILE)
    commit = _commit()
    host = platform.platform()
    toolchain = _tool_identity(emitter, runner)
    try:
        directory = Path(tempfile.mkdtemp(prefix="arena-target-echo-", dir=_TEMP))
    except OSError as error:
        message = "target echo study workspace creation failed"
        raise TargetEchoStudyError(message) from error
    _initialize_workspace_folders(directory, ("runs", "raw", "candidates"))
    return _Context(
        directory=directory,
        prefix=directory.relative_to(_ROOT).as_posix(),
        fingerprint=fingerprint,
        commit=commit,
        host=host,
        toolchain=toolchain,
        emitter=emitter,
        runner=runner,
    )


def _write_retained_bytes(path: Path, content: bytes) -> None:
    """Require a complete host byte-write acknowledgement before publication."""
    written = path.write_bytes(content)
    if type(written) is not int or written != len(content):
        _fail(f"target echo retained {path.name} has invalid write count")


def _write_retained_text(path: Path, content: str) -> None:
    """Require a complete host text-write acknowledgement before publication."""
    written = path.write_text(content, encoding="utf-8")
    if type(written) is not int or written != len(content):
        _fail(f"target echo retained {path.name} has invalid write count")


def _write_rss_stages(
    context: _Context,
    row: dict[str, Any],
    *,
    values: list[int] | None,
) -> str | None:
    if not context.retain_rss_stages or row["outcome"] != analyze.VERIFIED:
        return None
    if values is None or len(values) != RSS_MEASURED_STAGES:
        _fail("retained RSS stage receipt requires all three samples")
    stages = dict(
        zip(("emitter", "primary_vm", "verifier_vm"), values, strict=True)
    )
    case = row["case"]
    identity = {
        "algorithm": row["algorithm"],
        "pairs": case["difficulty"],
        "trial": row["trial"],
        "workload_sha256": case["workload_sha256"],
    }
    receipt = {"schema_version": 1, "identity": identity, "stages": stages}
    if context.retain_raw_rss:
        raw = context.raw_rss_stages
        if raw is None or len(raw) != RSS_MEASURED_STAGES:
            _fail("retained raw RSS requires three complete GNU time reports")
        receipt["schema_version"] = 2
        receipt["raw_kib"] = dict(
            zip(
                ("emitter", "primary_vm", "verifier_vm"),
                [item.decode("ascii") for item in raw],
                strict=True,
            )
        )
    content = (
        json.dumps(
            receipt,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    stem = f"{row["algorithm"]}-pairs-{case["difficulty"]}-trial-{row["trial"]}"
    path = context.directory / "rss" / f"{stem}.json"
    _write_retained_bytes(path, content)
    return sha256(content).hexdigest()


def _write_attempt(
    context: _Context,
    pairs: int,
    trial: int,
    *,
    algorithm: str,
) -> dict[str, Any]:
    stem = f"{algorithm}-pairs-{pairs}-trial-{trial}"
    artifact = context.directory / "candidates" / f"{stem}.malbolge"
    observed_context = (
        replace(
            context,
            rss_stages=[],
            raw_rss_stages=[] if context.retain_raw_rss else None,
        )
        if context.measure_child_rss
        else context
    )
    outcome, metrics = _measure(
        artifact, observed_context, pairs, algorithm=algorithm
    )
    verdict = {
        analyze.VERIFIED: analyze.ACCEPTED,
        analyze.VERIFIER_REJECTED: analyze.REJECTED,
    }.get(outcome, analyze.NOT_RUN)
    row = {
        "algorithm": algorithm,
        "case": _case(pairs, context.input_mode, context.layout_mode),
        "trial": trial,
        "outcome": outcome,
        "verifier": (
            FORWARD_RAW_RSS_VERIFIER
            if context.retain_raw_rss
            else FORWARD_RSS_RECEIPTS_VERIFIER
            if context.retain_rss_stages
            else FORWARD_RSS_VERIFIER
            if context.measure_child_rss
            else FORWARD_LIMITED_REPLAY_VERIFIER
            if context.limit_child_resources
            else FORWARD_REPLAY_VERIFIER
            if context.measure_verifier
            and context.verifier_mode == REPLAY_VERIFIER_MODE
            else FORWARD_VERIFIER
            if context.layout_mode == FORWARD_SKIP_LAYOUT
            else VERIFIER
            if context.input_mode == EOF_MODE
            else PATTERNED_VERIFIER
        ),
        "verifier_verdict": verdict,
        "experiment_manifest": f"{context.prefix}/runs/{stem}.toml",
        "raw_sample": f"{context.prefix}/raw/{stem}.csv",
        "metrics": metrics,
    }
    raw = _raw_csv(row)
    _write_retained_bytes(context.directory / "raw" / f"{stem}.csv", raw)
    receipt_hash = _write_rss_stages(
        observed_context,
        row,
        values=observed_context.rss_stages,
    )
    receipt = _manifest(
        row, context, sha256(raw).hexdigest(), rss_hash=receipt_hash
    )
    _write_retained_text(context.directory / "runs" / f"{stem}.toml", receipt)
    return row


def _make_document(
    context: _Context,
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    patterned = context.input_mode == PATTERNED_MODE
    study_id = (
        FORWARD_RAW_RSS_STUDY
        if context.retain_raw_rss
        else FORWARD_RSS_RECEIPTS_STUDY
        if context.retain_rss_stages
        else FORWARD_RSS_STUDY
        if context.measure_child_rss
        else FORWARD_LIMITED_REPLAY_STUDY
        if context.limit_child_resources
        else FORWARD_REPLAY_COST_STUDY
        if context.measure_verifier
        and context.verifier_mode == REPLAY_VERIFIER_MODE
        else FORWARD_VERIFIER_COST_STUDY
        if context.measure_verifier
        else FORWARD_STUDY
        if context.layout_mode == FORWARD_SKIP_LAYOUT
        else (PATTERNED_STEPS_STUDY if patterned else EOF_STEPS_STUDY)
        if context.measure_steps
        else (PATTERNED_STUDY if patterned else "classic-eof-echo-geometry-v1")
    )
    return {
        "schema_version": 1,
        "study": {
            "id": study_id,
            "question": (
                "Can a forward jump skip otherwise executed graphical padding?"
                if context.layout_mode == FORWARD_SKIP_LAYOUT
                else (
                    "Does padding worsen the classic patterned "
                    "byte-echo frontier?"
                )
                if patterned
                else (
                    "Does redundant no-op padding worsen the "
                    "classic VM frontier?"
                )
            ),
            "hypothesis": (
                "Equal-sized forward-jump code executes fewer guest steps."
                if context.layout_mode == FORWARD_SKIP_LAYOUT
                else "Direct code is smaller than no-op padded code."
            ),
            "rejection_observation": (
                "Jump changes source size, fails output, or saves no VM work."
                if context.layout_mode == FORWARD_SKIP_LAYOUT
                else "Padded code is not larger or direct fails "
                "its patterned-byte oracle."
                if patterned
                else "Padded code is not larger or direct fails its EOF oracle."
            ),
            "baseline": (
                WALK if context.layout_mode == FORWARD_SKIP_LAYOUT else BASELINE
            ),
            "stage": "measured-classic-malbolge-code-and-vm",
            "target_profile": PROFILE,
            "host": context.host,
            "toolchain": context.toolchain,
            "budget": {
                "time_ns": BUDGET_SECONDS * 1_000_000_000,
                "memory_bytes": BUDGET_MIB * 1_048_576,
            },
            "objectives": (
                [
                    "elapsed_ns",
                    "artifact_bytes",
                    RUNTIME_STEPS,
                    VERIFIER_NS,
                    PEAK_RSS,
                ]
                if context.measure_child_rss
                else [
                    "elapsed_ns",
                    "artifact_bytes",
                    RUNTIME_STEPS,
                    VERIFIER_NS,
                ]
                if context.measure_verifier
                else ["elapsed_ns", "artifact_bytes", RUNTIME_STEPS]
                if context.measure_steps
                else ["elapsed_ns", "artifact_bytes"]
            ),
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
    from benchmarks.arena import (
        target_echo_audit,  # ruff: ignore[import-outside-top-level]
    )

    relative = path.relative_to(_ROOT).as_posix()
    try:
        checked = target_echo_audit.audit(relative)
    except target_echo_audit.TargetEchoAuditError as error:
        message = f"target echo source admission failed: {error}"
        raise TargetEchoStudyError(message) from error
    raw = evidence.read_bounded_regular(
        _ROOT, relative, limit=target_echo_audit.MAX_STUDY_BYTES
    )
    if sha256(raw).hexdigest() != checked["retained_study_sha256"]:
        _fail("target echo retained study changed after independent audit")
    return analyze.parse_document(raw.decode("utf-8"))


def _validate_verifier_measurement(plan: StudyPlan) -> None:
    if type(plan.measure_verifier) is not bool:
        _fail("target echo requires a boolean verifier timing selection")
    if plan.measure_verifier and plan.layout_mode != FORWARD_SKIP_LAYOUT:
        _fail("target echo verifier cost requires the forward-skip study")
    if (
        type(plan.verifier_mode) is not str
        or plan.verifier_mode not in VERIFIER_MODES
    ):
        _fail("target echo verifier mode must be source or replay")
    if plan.verifier_mode == REPLAY_VERIFIER_MODE and not plan.measure_verifier:
        _fail("target echo replay verifier requires measured verifier cost")
    _validate_child_resource_selection(plan)


def _validate_child_resource_selection(plan: StudyPlan) -> None:
    if type(plan.limit_child_resources) is not bool:
        _fail("target echo child resource controls require boolean selection")
    if plan.limit_child_resources and (
        not plan.measure_verifier or plan.verifier_mode != REPLAY_VERIFIER_MODE
    ):
        _fail("target echo child limits require measured verifier replay")


def _validate_rss_selection(plan: StudyPlan) -> None:
    if type(plan.measure_child_rss) is not bool:
        _fail("target echo requires boolean peak RSS measurement selection")
    if plan.measure_child_rss and not plan.limit_child_resources:
        _fail("target echo peak RSS requires resource-limited replay")
    if type(plan.retain_rss_stages) is not bool:
        _fail("target echo RSS receipts require boolean retention selection")
    if plan.retain_rss_stages and not plan.measure_child_rss:
        _fail("target echo RSS receipts require measured child RSS")


def _validate_raw_rss_selection(plan: StudyPlan) -> None:
    if type(plan.retain_raw_rss) is not bool:
        _fail("target echo raw RSS retention requires a boolean selection")
    if plan.retain_raw_rss and not plan.retain_rss_stages:
        _fail("target echo raw RSS retention requires per-stage RSS receipts")


def _validate_study_options(plan: StudyPlan) -> None:
    _validate_input_mode(plan.input_mode)
    if type(plan.measure_steps) is not bool:
        _fail("target echo requires a boolean measure_steps selection")
    if (
        type(plan.layout_mode) is not str
        or plan.layout_mode not in LAYOUT_MODES
    ):
        _fail("target echo layout mode must be linear or forward-skip")
    if plan.layout_mode == FORWARD_SKIP_LAYOUT and (
        plan.input_mode != PATTERNED_MODE or not plan.measure_steps
    ):
        _fail("target echo forward-skip requires pattern and measured steps")
    _validate_verifier_measurement(plan)
    _validate_rss_selection(plan)
    _validate_raw_rss_selection(plan)


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
    _validate_study_options(plan)
    if plan.measure_child_rss:
        target_process.require_child_rss_measurement()
    elif plan.limit_child_resources:
        target_process.require_child_resource_controls()
    context = replace(
        _prepare_context(emitter, runner),
        input_mode=plan.input_mode,
        measure_steps=plan.measure_steps,
        layout_mode=plan.layout_mode,
        measure_verifier=plan.measure_verifier,
        verifier_mode=plan.verifier_mode,
        limit_child_resources=plan.limit_child_resources,
        measure_child_rss=plan.measure_child_rss,
        retain_rss_stages=plan.retain_rss_stages,
        retain_raw_rss=plan.retain_raw_rss,
    )
    if context.retain_rss_stages:
        _initialize_workspace_folders(context.directory, ("rss",))
    observations = [
        _write_attempt(context, pairs, trial, algorithm=algorithm)
        for pairs in plan.pairs
        for trial in range(plan.trials)
        for algorithm in (
            _algorithms(plan.layout_mode)
            if trial % 2 == 0
            else _algorithms(plan.layout_mode)[::-1]
        )
    ]
    document = _make_document(context, observations)
    path = context.directory / "study.json"
    _write_retained_text(
        path, json.dumps(document, sort_keys=True, indent=2) + "\n"
    )
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
    parser.add_argument("--measure-steps", action="store_true")
    parser.add_argument(
        "--layout-mode", choices=LAYOUT_MODES, default=LINEAR_LAYOUT
    )
    parser.add_argument("--measure-verifier", action="store_true")
    parser.add_argument(
        "--verifier-mode", choices=VERIFIER_MODES, default=SOURCE_VERIFIER_MODE
    )
    parser.add_argument("--limit-child-resources", action="store_true")
    parser.add_argument("--measure-child-rss", action="store_true")
    parser.add_argument("--retain-rss-stages", action="store_true")
    parser.add_argument("--retain-raw-rss", action="store_true")
    args = parser.parse_args()
    try:
        directory, document = run_study(
            StudyPlan(
                tuple(args.pairs),
                args.trials,
                args.input_mode,
                args.measure_steps,
                args.layout_mode,
                args.measure_verifier,
                args.verifier_mode,
                args.limit_child_resources,
                args.measure_child_rss,
                args.retain_rss_stages,
                args.retain_raw_rss,
            )
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
