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
import json
import os
import shutil
import stat
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from statistics import median
from typing import Any, Never

import tomllib

from benchmarks.arena import (
    analyze,
    evidence,
    raw_samples,
    report_output,
    target_process,
)
from benchmarks.arena import target_echo_reference as producer
from scripts.validate import experiment_manifest

_ROOT = Path(__file__).resolve().parents[2]
MAX_STUDY_BYTES = 16 * 1024 * 1024
STUDY_LEAF = "study.json"
PATH_PART_COUNT = 3
UNDERSCORE = "_"
DIGEST_HEX_LENGTH = 64
PHASES = 94
METHOD_CLASS = "benchmarking"
ACCELERATOR = "none"
GIT_COMMIT_TYPE = b"commit"
GIT_TIMEOUT_SECONDS = 5
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
    "jump": ord("i"),
}
# Independently authored frozen classic XLAT1 mapping, not emitter output.
EOF_STUDY = "classic-eof-echo-geometry-v1"
PATTERNED_STUDY = "classic-patterned-byte-echo-geometry-v1"
EOF_STEPS_STUDY = "classic-eof-echo-steps-v2"
PATTERNED_STEPS_STUDY = "classic-patterned-byte-echo-steps-v2"
STEPS_REPORT_PREFIX = b"malbolge-steps-v1:"
RUNTIME_STEPS = "runtime_steps"
FORWARD_STUDY = "classic-patterned-forward-skip-steps-v1"
FORWARD_VERIFIER_COST_STUDY = "classic-patterned-forward-skip-verifier-cost-v2"
FORWARD_REPLAY_COST_STUDY = "classic-patterned-forward-skip-replay-cost-v3"
FORWARD_LIMITED_REPLAY_STUDY = (
    "classic-patterned-forward-skip-limited-replay-v4"
)
FORWARD_RSS_STUDY = "classic-patterned-forward-skip-limited-rss-v5"
FORWARD_RSS_RECEIPTS_STUDY = "classic-patterned-forward-skip-rss-receipts-v6"
FORWARD_RAW_RSS_STUDY = "classic-patterned-forward-skip-raw-rss-v7"
VERIFIER_NS = "verifier_ns"
FORWARD_FAMILY = "bounded-classic-patterned-forward-skip-echo"
FORWARD_VERIFIER = "classic-forward-jump-patterned-byte-and-steps-v1"
FORWARD_REPLAY_VERIFIER = "classic-forward-jump-patterned-second-vm-v1"
FORWARD_LIMITED_REPLAY_VERIFIER = "classic-forward-jump-limited-second-vm-v1"
FORWARD_RSS_VERIFIER = "classic-forward-jump-limited-rss-second-vm-v1"
FORWARD_RSS_RECEIPTS_VERIFIER = "classic-forward-jump-rss-receipts-second-vm-v1"
FORWARD_RAW_RSS_VERIFIER = "classic-forward-jump-raw-rss-second-vm-v1"
RSS_STAGE_NAMES = ("emitter", "primary_vm", "verifier_vm")
RSS_REPORT_LIMIT = 512
MIN_TIME_LINE_BYTES = 2
RSS_HASH_TABLE = "arena_rss"
RSS_RECEIPT_DIR = "rss"
PEAK_RSS = "peak_rss_bytes"
WALK = "walk-padding-echo"
SKIP = "jump-skip-padding-echo"
FORWARD_ALGORITHMS = (WALK, SKIP)
SKIPPED_NOOPS = 98
WALKED_NOOPS = SKIPPED_NOOPS + 1
FORWARD_JUMP_TARGET = SKIPPED_NOOPS + 1
PATTERNED_FAMILY = "bounded-classic-patterned-byte-echo"
PATTERNED_VERIFIER = "classic-malbolge-vm-exact-patterned-byte-v1"
# Independently fixed vector; do not defer to the producing algorithm.
PATTERN_BYTES = bytes((0x00, 0xFF, 0xA8, 0x5A, 0x80, 0x01, 0x7F, 0xFE))

CLASSIC_DECODE = (
    b'+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA"lI'
    b".v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
)


class TargetEchoAuditError(ValueError):
    """Retained target echo evidence is inconsistent or unverifiable."""


class TargetReplayToolError(sp.SubprocessError):
    """The second VM run did not produce a valid tool-level step receipt."""


@dataclass(frozen=True, slots=True)
class AuditOptions:
    """Explicit optional retained-study replay and provenance gates."""

    replay_candidates: bool = False
    require_source_commit_object: bool = False
    emitter: Path | None = None
    runner: Path | None = None
    stage_rss_breakdown: bool = False


DEFAULT_AUDIT_OPTIONS = AuditOptions()


def _fail(message: str) -> Never:
    raise TargetEchoAuditError(message)


def _admit_options(options: AuditOptions) -> None:
    """Require exact replay/provenance opt-ins before reading retained files."""
    if type(options) is not AuditOptions or any(
        type(value) is not bool
        for value in (
            options.replay_candidates,
            options.require_source_commit_object,
            options.stage_rss_breakdown,
        )
    ):
        _fail("target echo audit options require exact booleans")
    native_path_type = type(Path())
    if any(
        value is not None and type(value) is not native_path_type
        for value in (options.emitter, options.runner)
    ):
        _fail("target echo audit tool overrides require exact Paths")


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


def _document(relative: str) -> tuple[dict[str, Any], str]:
    data = evidence.read_bounded_regular(
        _ROOT,
        relative,
        limit=MAX_STUDY_BYTES,
    )
    return analyze.parse_document(data.decode("utf-8")), sha256(
        data
    ).hexdigest()


def _mode(document: dict[str, Any]) -> str:
    study_id = document["study"]["id"]
    if study_id in {
        PATTERNED_STUDY,
        PATTERNED_STEPS_STUDY,
        FORWARD_STUDY,
        FORWARD_VERIFIER_COST_STUDY,
        FORWARD_REPLAY_COST_STUDY,
        FORWARD_LIMITED_REPLAY_STUDY,
        FORWARD_RSS_STUDY,
        FORWARD_RSS_RECEIPTS_STUDY,
        FORWARD_RAW_RSS_STUDY,
    }:
        return producer.PATTERNED_MODE
    if study_id in {EOF_STUDY, EOF_STEPS_STUDY}:
        return producer.EOF_MODE
    _fail("target audit has unrecognized classic echo study mode")


def _has_steps(document: dict[str, Any]) -> bool:
    return document["study"]["id"] in {
        EOF_STEPS_STUDY,
        PATTERNED_STEPS_STUDY,
        FORWARD_STUDY,
        FORWARD_VERIFIER_COST_STUDY,
        FORWARD_REPLAY_COST_STUDY,
        FORWARD_LIMITED_REPLAY_STUDY,
        FORWARD_RSS_STUDY,
        FORWARD_RSS_RECEIPTS_STUDY,
        FORWARD_RAW_RSS_STUDY,
    }


def _forward(document: dict[str, Any]) -> bool:
    return document["study"]["id"] in {
        FORWARD_STUDY,
        FORWARD_VERIFIER_COST_STUDY,
        FORWARD_REPLAY_COST_STUDY,
        FORWARD_LIMITED_REPLAY_STUDY,
        FORWARD_RSS_STUDY,
        FORWARD_RSS_RECEIPTS_STUDY,
        FORWARD_RAW_RSS_STUDY,
    }


def _has_verifier_cost(document: dict[str, Any]) -> bool:
    return document["study"]["id"] in {
        FORWARD_VERIFIER_COST_STUDY,
        FORWARD_REPLAY_COST_STUDY,
        FORWARD_LIMITED_REPLAY_STUDY,
        FORWARD_RSS_STUDY,
        FORWARD_RSS_RECEIPTS_STUDY,
        FORWARD_RAW_RSS_STUDY,
    }


def _algorithms(document: dict[str, Any]) -> tuple[str, str]:
    return FORWARD_ALGORITHMS if _forward(document) else producer.ALGORITHMS


def _pattern_bytes(pairs: int) -> bytes:
    return (
        PATTERN_BYTES * ((pairs + len(PATTERN_BYTES) - 1) // len(PATTERN_BYTES))
    )[:pairs]


def _producer_study(document: dict[str, Any]) -> None:
    study = document["study"]
    patterned = _mode(document) == producer.PATTERNED_MODE
    steps = _has_steps(document)
    forward = _forward(document)
    study_id = (
        (PATTERNED_STEPS_STUDY if patterned else EOF_STEPS_STUDY)
        if steps
        else (PATTERNED_STUDY if patterned else EOF_STUDY)
    )
    if forward:
        study_id = (
            FORWARD_RAW_RSS_STUDY
            if study["id"] == FORWARD_RAW_RSS_STUDY
            else FORWARD_RSS_RECEIPTS_STUDY
            if study["id"] == FORWARD_RSS_RECEIPTS_STUDY
            else FORWARD_RSS_STUDY
            if study["id"] == FORWARD_RSS_STUDY
            else FORWARD_LIMITED_REPLAY_STUDY
            if study["id"] == FORWARD_LIMITED_REPLAY_STUDY
            else FORWARD_REPLAY_COST_STUDY
            if study["id"] == FORWARD_REPLAY_COST_STUDY
            else FORWARD_VERIFIER_COST_STUDY
            if _has_verifier_cost(document)
            else FORWARD_STUDY
        )
    expected = {
        "id": study_id,
        "question": (
            "Can a forward jump skip otherwise executed graphical padding?"
            if forward
            else "Does padding worsen the classic patterned byte-echo frontier?"
            if patterned
            else "Does redundant no-op padding worsen the classic VM frontier?"
        ),
        "hypothesis": (
            "Equal-sized forward-jump code executes fewer guest steps."
            if forward
            else "Direct code is smaller than no-op padded code."
        ),
        "rejection_observation": (
            "Jump changes source size, fails output, or saves no VM work."
            if forward
            else "Padded code is not larger or direct fails "
            "its patterned-byte oracle."
            if patterned
            else "Padded code is not larger or direct fails its EOF oracle."
        ),
        "baseline": WALK if forward else producer.BASELINE,
        "stage": "measured-classic-malbolge-code-and-vm",
        "target_profile": producer.PROFILE,
        "budget": {
            "time_ns": producer.BUDGET_SECONDS * 1_000_000_000,
            "memory_bytes": producer.BUDGET_MIB * 1_048_576,
        },
        "objectives": (
            [
                "elapsed_ns",
                "artifact_bytes",
                RUNTIME_STEPS,
                VERIFIER_NS,
                PEAK_RSS,
            ]
            if study["id"]
            in {
                FORWARD_RSS_STUDY,
                FORWARD_RSS_RECEIPTS_STUDY,
                FORWARD_RAW_RSS_STUDY,
            }
            else ["elapsed_ns", "artifact_bytes", RUNTIME_STEPS, VERIFIER_NS]
            if _has_verifier_cost(document)
            else ["elapsed_ns", "artifact_bytes", RUNTIME_STEPS]
            if steps
            else ["elapsed_ns", "artifact_bytes"]
        ),
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


def _expected_case(
    pairs: int, mode: str = producer.EOF_MODE, *, forward: bool = False
) -> dict[str, Any]:
    if forward:
        payload = _pattern_bytes(pairs)
        identity = (
            f"classic-forward-skip-byte-v1:pairs={pairs}:"
            f"input={payload.hex()}:eof-after"
        ).encode("ascii")
    elif mode == producer.EOF_MODE:
        identity = f"classic-eof-echo-v1:pairs={pairs}:empty-input".encode(
            "ascii"
        )
    else:
        payload = _pattern_bytes(pairs)
        identity = (
            f"classic-patterned-byte-echo-v1:pairs={pairs}:"
            f"input={payload.hex()}:eof-after"
        ).encode("ascii")
    return {
        "family": (
            FORWARD_FAMILY
            if forward
            else producer.FAMILY
            if mode == producer.EOF_MODE
            else PATTERNED_FAMILY
        ),
        "version": 1,
        "difficulty": pairs,
        "seed": 0,
        "workload_sha256": sha256(identity).hexdigest(),
    }


def _expected_operations(
    pairs: int,
    algorithm: str,
    mode: str = producer.EOF_MODE,
    *,
    forward: bool = False,
) -> list[str]:
    if forward:
        echo = ["input", "output"] * (pairs + 1) + ["halt"]
        return (
            ["nop"] * WALKED_NOOPS + echo
            if algorithm == WALK
            else ["jump", *["nop"] * SKIPPED_NOOPS, *echo]
        )
    chunk = ["input", "output"]
    if algorithm == producer.CANDIDATE:
        chunk = ["nop", *chunk]
    count = pairs + int(mode == producer.PATTERNED_MODE)
    return chunk * count + ["halt"]


def _row_stem(row: dict[str, Any]) -> str:
    case = row["case"]
    return f"{row["algorithm"]}-pairs-{case["difficulty"]}-trial-{row["trial"]}"


def _check_row(
    row: dict[str, Any],
    prefix: str,
    mode: str,
    *,
    protocol: tuple[bool, bool, bool, bool, bool, bool],
) -> str:
    forward, replay_cost, limited, rss, receipt, raw_rss = protocol
    case = row["case"]
    algorithm = row["algorithm"]
    if algorithm not in (
        FORWARD_ALGORITHMS if forward else producer.ALGORITHMS
    ):
        _fail("target audit trial has a foreign algorithm")
    if case != _expected_case(case["difficulty"], mode, forward=forward):
        _fail("target audit trial differs from the fixed echo case")
    expected_verifier = (
        FORWARD_RAW_RSS_VERIFIER
        if raw_rss
        else FORWARD_RSS_RECEIPTS_VERIFIER
        if receipt
        else FORWARD_RSS_VERIFIER
        if rss
        else FORWARD_LIMITED_REPLAY_VERIFIER
        if limited
        else FORWARD_REPLAY_VERIFIER
        if replay_cost
        else FORWARD_VERIFIER
        if forward
        else producer.VERIFIER
        if mode == producer.EOF_MODE
        else PATTERNED_VERIFIER
    )
    if row["verifier"] != expected_verifier:
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


def _check_plan(
    rows: list[dict[str, Any]], *, algorithm_count: int = 2
) -> tuple[set[int], set[int]]:
    levels = _check_levels(rows)
    trials = {row["trial"] for row in rows}
    if not 1 <= len(trials) <= producer.MAX_TRIALS:
        _fail("target audit requires one to three trial indices")
    if trials != set(range(len(trials))):
        _fail("target audit requires consecutive repetition indices")
    if len(rows) != len(levels) * len(trials) * algorithm_count:
        _fail("target audit requires complete matched echo repetitions")
    return levels, trials


def _check_one_step_claim(
    row: dict[str, Any], *, measured: bool, mode: str, forward: bool = False
) -> None:
    actual = row["metrics"].get(RUNTIME_STEPS)
    if not measured or row["outcome"] != analyze.VERIFIED:
        if actual is not None:
            _fail("unmeasured or failed target trial claims guest steps")
    else:
        expected = len(
            _expected_operations(
                row["case"]["difficulty"],
                row["algorithm"],
                mode,
                forward=forward,
            )
        )
        if forward and row["algorithm"] == SKIP:
            expected -= SKIPPED_NOOPS
        if actual != expected:
            _fail("target runtime step claim differs from decoded source")


def _check_verifier_cost_claims(document: dict[str, Any]) -> None:
    timed = _has_verifier_cost(document)
    for row in document["observations"]:
        actual = row["metrics"].get(VERIFIER_NS)
        if timed and row["outcome"] == analyze.VERIFIED:
            if (
                type(actual) is not int
                or actual <= 0
                or actual > row["metrics"]["elapsed_ns"]
            ):
                _fail("target verifier timing is missing or invalid")
        elif actual is not None:
            _fail("untimed or unverified target trial claims verifier cost")


def _check_peak_rss_claims(document: dict[str, Any]) -> None:
    measured = document["study"]["id"] in {
        FORWARD_RSS_STUDY,
        FORWARD_RSS_RECEIPTS_STUDY,
        FORWARD_RAW_RSS_STUDY,
    }
    for row in document["observations"]:
        peak = row["metrics"].get(PEAK_RSS)
        if measured and row["outcome"] == analyze.VERIFIED:
            if (
                type(peak) is not int
                or not 0 < peak <= producer.BUDGET_MIB * 1024 * 1024
                or peak % target_process.KIB_BYTES != 0
            ):
                _fail("target peak RSS observation is missing or invalid")
        elif peak is not None:
            _fail("unmeasured or unsuccessful target claims peak RSS")


def _check_runtime_step_claims(document: dict[str, Any]) -> None:
    measured = _has_steps(document)
    mode = _mode(document)
    forward = _forward(document)
    for row in document["observations"]:
        _check_one_step_claim(
            row, measured=measured, mode=mode, forward=forward
        )


def _protocol(
    document: dict[str, Any],
) -> tuple[bool, bool, bool, bool, bool, bool]:
    study_id = document["study"]["id"]
    return (
        _forward(document),
        study_id
        in {
            FORWARD_REPLAY_COST_STUDY,
            FORWARD_LIMITED_REPLAY_STUDY,
            FORWARD_RSS_STUDY,
            FORWARD_RSS_RECEIPTS_STUDY,
            FORWARD_RAW_RSS_STUDY,
        },
        study_id
        in {
            FORWARD_LIMITED_REPLAY_STUDY,
            FORWARD_RSS_STUDY,
            FORWARD_RSS_RECEIPTS_STUDY,
            FORWARD_RAW_RSS_STUDY,
        },
        study_id
        in {
            FORWARD_RSS_STUDY,
            FORWARD_RSS_RECEIPTS_STUDY,
            FORWARD_RAW_RSS_STUDY,
        },
        study_id in {FORWARD_RSS_RECEIPTS_STUDY, FORWARD_RAW_RSS_STUDY},
        study_id == FORWARD_RAW_RSS_STUDY,
    )


def _producer_rows(document: dict[str, Any], prefix: str) -> set[str]:
    rows = document["observations"]
    algorithms = _algorithms(document)
    levels, trials = _check_plan(rows, algorithm_count=len(algorithms))
    _check_runtime_step_claims(document)
    _check_verifier_cost_claims(document)
    _check_peak_rss_claims(document)
    mode = _mode(document)
    names = {
        _check_row(row, prefix, mode, protocol=_protocol(document))
        for row in rows
    }
    expected = {
        f"{algorithm}-pairs-{level}-trial-{trial}"
        for level in levels
        for trial in trials
        for algorithm in algorithms
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


def _require_git_commit(commit: str) -> None:
    """Check local commit-object type; never attest historical execution.

    Raises:
        TargetEchoAuditError: Git is missing or cannot admit a commit object.

    """
    executable = shutil.which("git", path=os.defpath)
    if executable is None:
        _fail("target audit source commit admission requires local Git")
    # Ambient Git object/database selectors cannot redirect local admission.
    clean_env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("GIT_")
    }
    try:
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [executable, "cat-file", "-t", commit],
            cwd=_ROOT,
            stdin=sp.DEVNULL,
            check=False,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
            env=clean_env,
        )
    except (OSError, sp.SubprocessError) as error:
        message = "target audit Git commit object lookup failed"
        raise TargetEchoAuditError(message) from error
    if completed.returncode != 0 or completed.stdout.strip() != GIT_COMMIT_TYPE:
        _fail("target audit source revision is not a local Git commit object")


def _decoded_instruction(cell: int, position: int) -> int:
    if not producer.GRAPHICAL_LOW <= cell <= producer.GRAPHICAL_HIGH:
        _fail("target audit source contains nongraphical code")
    phase = (cell - producer.GRAPHICAL_LOW + position) % PHASES
    return CLASSIC_DECODE[phase]


def _check_forward_jump(source: bytes, row: dict[str, Any]) -> None:
    if row["algorithm"] != SKIP:
        return
    if not source or source[0] + 1 != FORWARD_JUMP_TARGET:
        _fail("target audit forward jump target differs from source operand")


def check_forward_candidate_source(
    source: bytes, *, pairs: int, algorithm: str
) -> None:
    """Admit source bytes with the independent fixed jump/echo decoder."""
    if algorithm not in FORWARD_ALGORITHMS:
        _fail("target verifier received an unrecognized forward algorithm")
    row = {
        "algorithm": algorithm,
        "case": {"difficulty": pairs},
        "metrics": {"artifact_bytes": len(source)},
    }
    _admit_source_bytes(source, row, producer.PATTERNED_MODE, forward=True)


def _admit_source_bytes(
    source: bytes,
    row: dict[str, Any],
    mode: str,
    *,
    forward: bool = False,
) -> None:
    operations = _expected_operations(
        row["case"]["difficulty"],
        row["algorithm"],
        mode,
        forward=forward,
    )
    if forward:
        _check_forward_jump(source, row)
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


def _check_source(
    row: dict[str, Any],
    prefix: str,
    mode: str,
    *,
    forward: bool = False,
) -> tuple[str, str]:
    relative = f"{prefix}/candidates/{_row_stem(row)}.malbolge"
    source = evidence.read_bounded_regular(
        _ROOT,
        relative,
        limit=producer.MAX_TARGET_BYTES,
    )
    _admit_source_bytes(source, row, mode, forward=forward)
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
    mode = _mode(document)
    forward = _forward(document)
    for row in document["observations"]:
        if row["outcome"] == analyze.VERIFIED:
            relative, fingerprint = _check_source(
                row, prefix, mode, forward=forward
            )
            fingerprints[relative] = fingerprint
    return fingerprints


def _admit_tool(path: Path) -> Path:
    if not path.is_absolute():
        _fail("target audit requires absolute binary paths")
    details = path.lstat()
    if not stat.S_ISREG(details.st_mode) or details.st_size == 0:
        _fail("target audit requires regular nonempty executable files")
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
                _fail("target audit executable identity changed")
            flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(
                os, "O_NOFOLLOW", 0
            )
            descriptor = os.open(path, flags)
            try:
                opened = os.fstat(descriptor)
                if not stat.S_ISREG(opened.st_mode) or (
                    _tool_file_identity(opened) != _tool_file_identity(original)
                ):
                    _fail("target audit executable identity changed")
                digest.update(opened.st_size.to_bytes(8, "big"))
                remaining = opened.st_size
                while remaining:
                    chunk = os.read(descriptor, min(remaining, 1024 * 1024))
                    if not chunk:
                        _fail("target audit executable identity changed")
                    digest.update(chunk)
                    remaining -= len(chunk)
                if os.read(descriptor, 1) or (
                    _tool_file_identity(os.fstat(descriptor))
                    != _tool_file_identity(opened)
                ):
                    _fail("target audit executable identity changed")
            finally:
                os.close(descriptor)
            latest = path.lstat()
            if not stat.S_ISREG(latest.st_mode) or (
                _tool_file_identity(latest) != _tool_file_identity(original)
            ):
                _fail("target audit executable identity changed")
        except OSError as error:
            message = "target audit executable identity changed"
            raise TargetEchoAuditError(message) from error
    return "local-compiler-vm-sha256:" + digest.hexdigest()


def _invoke_runner_command(command: list[str]) -> sp.CompletedProcess[bytes]:
    return target_process.invoke(
        command, timeout_seconds=producer.TIMEOUT_SECONDS
    )


def _invoke_runner(runner: Path, source: Path) -> sp.CompletedProcess[bytes]:
    return _invoke_runner_command([str(runner), str(source)])


def _replay_execution(
    row: dict[str, Any], runner: Path, source: Path, *, limited: bool = False
) -> tuple[sp.CompletedProcess[bytes], bytes]:
    pairs = row["case"]["difficulty"]
    patterned = row["case"]["family"] in {PATTERNED_FAMILY, FORWARD_FAMILY}
    receipt = row["metrics"].get(RUNTIME_STEPS) is not None
    if not patterned and not receipt:
        return (
            _invoke_runner(runner, source),
            bytes([producer.CLASSIC_EOF_BYTE]) * pairs,
        )
    command = [str(runner), str(source)]
    if patterned:
        command.append("--input-stdin")
    if receipt:
        command.append("--report-steps")
    if not patterned:
        return (
            _invoke_runner_command(command),
            bytes([producer.CLASSIC_EOF_BYTE]) * pairs,
        )
    payload = _pattern_bytes(pairs)
    return (
        (
            target_process.invoke_with_input_limited
            if limited
            else target_process.invoke_with_input
        )(command, payload, timeout_seconds=producer.TIMEOUT_SECONDS),
        payload + bytes([producer.CLASSIC_EOF_BYTE]),
    )


def _check_forward_replay_result(
    result: sp.CompletedProcess[bytes], payload: bytes, steps: int
) -> None:
    if result.returncode != 0:
        message = "target replay executable failed"
        raise TargetReplayToolError(message)
    receipt = STEPS_REPORT_PREFIX + str(steps).encode("ascii") + b"\n"
    if result.stderr != receipt:
        message = "target replay VM step receipt is invalid"
        raise TargetReplayToolError(message)
    if result.stdout != payload + bytes([producer.CLASSIC_EOF_BYTE]):
        _fail("target replay VM output differs from independent byte oracle")


def _run_forward_guest(
    command: list[str],
    payload: bytes,
    *,
    mode: tuple[bool, bool],
    raw_rss: list[bytes] | None = None,
) -> tuple[sp.CompletedProcess[bytes], int | None]:
    limited, measured = mode
    if measured and raw_rss is not None:
        result, peak, raw = (
            target_process.invoke_with_input_limited_measured_raw(
                command, payload, timeout_seconds=producer.TIMEOUT_SECONDS
            )
        )
        raw_rss.append(raw)
        return result, peak
    if measured:
        return target_process.invoke_with_input_limited_measured(
            command, payload, timeout_seconds=producer.TIMEOUT_SECONDS
        )
    method = (
        target_process.invoke_with_input_limited
        if limited
        else target_process.invoke_with_input
    )
    result = method(command, payload, timeout_seconds=producer.TIMEOUT_SECONDS)
    return result, None


def _replay_forward_result(
    paths: tuple[Path, Path],
    payload: bytes,
    *,
    steps: int,
    options: tuple[bool, bool, list[bytes] | None],
) -> int | None:
    runner, source = paths
    result, peak = _run_forward_guest(
        [str(runner), str(source), "--input-stdin", "--report-steps"],
        payload,
        mode=options[:2],
        raw_rss=options[2],
    )
    _check_forward_replay_result(result, payload, steps)
    return peak


def _assert_forward_source_stable(source: Path, original: bytes) -> None:
    relative = source.relative_to(_ROOT).as_posix()
    after = evidence.read_bounded_regular(
        _ROOT, relative, limit=producer.MAX_TARGET_BYTES
    )
    if after != original:
        _fail("target replay changed candidate source after admission")


def check_forward_vm_replay(
    source: Path,
    runner: Path,
    *,
    case: tuple[int, str],
    replay_options: tuple[int | None, bool, bool, list[bytes] | None],
) -> int | None:
    """Read/check the fixed source, then replay exact guest bytes and steps.

    The second VM uses the same normative executable, not another engine.
    Invalid output or source bytes reject the candidate; invalid tool status
    or step receipts reject the measurement as an instrumentation failure.

    Returns:
        Observed verifier VM RSS bytes only when explicitly measured.

    """
    pairs, algorithm = case
    steps, limit_child_resources, measure_rss = replay_options[:3]
    relative = source.relative_to(_ROOT).as_posix()
    original = evidence.read_bounded_regular(
        _ROOT, relative, limit=producer.MAX_TARGET_BYTES
    )
    check_forward_candidate_source(original, pairs=pairs, algorithm=algorithm)
    expected_steps = 2 * pairs + (102 if algorithm == WALK else 4)
    if type(steps) is not int or steps != expected_steps:
        _fail("target replay requested inconsistent guest instruction count")
    payload = _pattern_bytes(pairs)
    peak = _replay_forward_result(
        (runner, source),
        payload,
        steps=steps,
        options=(limit_child_resources, measure_rss, replay_options[3]),
    )
    _assert_forward_source_stable(source, original)
    return peak


def _replay_one(
    row: dict[str, Any],
    relative: str,
    digest: str,
    *,
    replay_tool: tuple[Path, bool],
) -> None:
    runner, limited = replay_tool
    measured_steps = row["metrics"].get(RUNTIME_STEPS)
    execution, expected = (
        _replay_execution(row, runner, _ROOT / relative, limited=True)
        if limited
        else _replay_execution(row, runner, _ROOT / relative)
    )
    if execution.returncode != 0 or execution.stdout != expected:
        _fail(f"target audit VM replay rejected retained source: {relative}")
    if measured_steps is not None:
        expected_stderr = (
            STEPS_REPORT_PREFIX + str(measured_steps).encode("ascii") + b"\n"
        )
        if execution.stderr != expected_stderr:
            _fail("target audit VM replay step receipt differs from count")
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
        _replay_one(
            row,
            relative,
            digest,
            replay_tool=(
                runner,
                document["study"]["id"]
                in {
                    FORWARD_LIMITED_REPLAY_STUDY,
                    FORWARD_RSS_STUDY,
                    FORWARD_RSS_RECEIPTS_STUDY,
                    FORWARD_RAW_RSS_STUDY,
                },
            ),
        )
    if _tool_identity(emitter, runner) != claimed:
        _fail("target audit replay executables changed during execution")
    return len(source_hashes)


def _retained_rss_document(document: dict[str, Any]) -> bool:
    return document["study"]["id"] in {
        FORWARD_RSS_RECEIPTS_STUDY,
        FORWARD_RAW_RSS_STUDY,
    }


def _rss_receipt_paths(
    document: dict[str, Any],
    prefix: str,
) -> set[str]:
    if not _retained_rss_document(document):
        return set()
    return {
        f"{prefix}/{RSS_RECEIPT_DIR}/{_row_stem(row)}.json"
        for row in document["observations"]
        if row["outcome"] == analyze.VERIFIED
    }


def _check_rss_receipt_inventory(
    document: dict[str, Any],
    prefix: str,
    names: set[str],
) -> None:
    if not _retained_rss_document(document):
        return
    expected = {
        f"{stem}.json"
        for stem in names
        if any(
            _row_stem(row) == stem and row["outcome"] == analyze.VERIFIED
            for row in document["observations"]
        )
    }
    _check_directory(prefix, RSS_RECEIPT_DIR, expected)


def _admit_rss_manifest_table(table: object, *, version: int) -> str:
    if not isinstance(table, dict) or set(table) != {
        "schema_version",
        "sha256",
    }:
        _fail("v6 target run is missing exact RSS receipt link")
    if (
        type(table["schema_version"]) is not int
        or table["schema_version"] != version
    ):
        _fail("target RSS receipt manifest schema_version differs from study")
    digest = table["sha256"]
    if type(digest) is not str or len(digest) != DIGEST_HEX_LENGTH:
        _fail("v6 RSS receipt manifest requires lowercase SHA-256")
    if not set(digest) <= analyze.SHA256_ALPHABET:
        _fail("v6 RSS receipt manifest digest is not lowercase SHA-256")
    return digest


def _rss_digest(
    record: dict[str, Any],
    *,
    version: int | None,
) -> str | None:
    manifest = evidence.read_bounded_regular(
        _ROOT,
        record["experiment_manifest"],
        limit=evidence.MAX_MANIFEST_BYTES,
    )
    try:
        table = tomllib.loads(manifest.decode("utf-8")).get(RSS_HASH_TABLE)
    except (ValueError, RecursionError, UnicodeError) as error:
        message = "target RSS run manifest is invalid TOML"
        raise TargetEchoAuditError(message) from error
    if version is None:
        if table is not None:
            _fail("unmeasured target run has unexpected RSS receipt link")
        return None
    return _admit_rss_manifest_table(table, version=version)


def _rss_record(data: bytes, *, raw: bool) -> dict[str, Any]:
    try:
        record = json.loads(data)
    except (UnicodeError, ValueError) as error:
        message = "v6 RSS stage receipt is not canonical JSON"
        raise TargetEchoAuditError(message) from error
    expected = {"schema_version", "identity", "stages"}
    if raw:
        expected.add("raw_kib")
    if type(record) is not dict or set(record) != expected:
        _fail("target RSS stage receipt must have exact fields")
    version = 2 if raw else 1
    if (
        type(record["schema_version"]) is not int
        or record["schema_version"] != version
    ):
        _fail("target RSS stage receipt schema version differs from study")
    return record


def _validate_rss_identity(
    identity: object,
    row: dict[str, Any],
) -> None:
    case = row["case"]
    expected = {
        "algorithm": row["algorithm"],
        "pairs": case["difficulty"],
        "trial": row["trial"],
        "workload_sha256": case["workload_sha256"],
    }
    if type(identity) is not dict or identity != expected:
        _fail("v6 RSS stage receipt differs from recorded trial identity")
    if type(identity["pairs"]) is not int or type(identity["trial"]) is not int:
        _fail("v6 RSS stage receipt trial/difficulty must be integers")
    if (
        type(identity["algorithm"]) is not str
        or type(identity["workload_sha256"]) is not str
    ):
        _fail("v6 RSS stage receipt algorithm/workload must be strings")


def _read_original_time_line(raw: object) -> int:
    if type(raw) is not str or not raw.isascii():
        _fail("v7 raw GNU time RSS must be ASCII text")
    encoded = raw.encode("ascii")
    if (
        not MIN_TIME_LINE_BYTES
        <= len(encoded)
        <= target_process.RSS_REPORT_LIMIT
        or not encoded.endswith(b"\n")
        or not encoded[:-1].isdigit()
    ):
        _fail("v7 raw GNU time RSS is not one exact integer line")
    kib = int(encoded[:-1])
    if (
        not 0
        < kib
        <= (
            target_process.CHILD_VIRTUAL_MEMORY_BYTES
            // target_process.KIB_BYTES
        )
    ):
        _fail("v7 raw GNU time RSS exceeds child resource limits")
    return kib * target_process.KIB_BYTES


def _validate_original_time_readings(
    raw_kib: object,
    stages: dict[str, int],
) -> None:
    if type(raw_kib) is not dict or set(raw_kib) != set(RSS_STAGE_NAMES):
        _fail("v7 GNU time raw RSS receipt has foreign stage names")
    for stage in RSS_STAGE_NAMES:
        if _read_original_time_line(raw_kib[stage]) != stages[stage]:
            _fail("v7 raw GNU time RSS differs from reported per-stage bytes")


def _validate_rss_stage_bytes(
    data: bytes,
    row: dict[str, Any],
    *,
    raw: bool,
) -> None:
    record = _rss_record(data, raw=raw)
    _validate_rss_identity(record["identity"], row)
    stages = record["stages"]
    if type(stages) is not dict or set(stages) != set(RSS_STAGE_NAMES):
        _fail("v6 RSS stage receipt has foreign stage names")
    if any(
        type(value) is not int
        or not 0 < value <= target_process.CHILD_VIRTUAL_MEMORY_BYTES
        or value % target_process.KIB_BYTES != 0
        for value in stages.values()
    ):
        _fail("v6 RSS stage receipt has invalid measured bytes")
    if raw:
        _validate_original_time_readings(record["raw_kib"], stages)
    canonical = (
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    if data != canonical or max(stages.values()) != row["metrics"][PEAK_RSS]:
        _fail("v6 RSS stage receipt differs from exact reported peak")


def _check_rss_receipts(
    document: dict[str, Any],
    prefix: str,
    names: set[str],
) -> None:
    raw = document["study"]["id"] == FORWARD_RAW_RSS_STUDY
    retained = _retained_rss_document(document)
    _check_rss_receipt_inventory(document, prefix, names)
    for row in document["observations"]:
        required = retained and row["outcome"] == analyze.VERIFIED
        version = (2 if raw else 1) if required else None
        digest = _rss_digest(row, version=version)
        if not required:
            continue
        relative = f"{prefix}/{RSS_RECEIPT_DIR}/{_row_stem(row)}.json"
        data = evidence.read_bounded_regular(
            _ROOT, relative, limit=RSS_REPORT_LIMIT
        )
        if sha256(data).hexdigest() != digest:
            _fail("v6 RSS receipt digest differs from linked run manifest")
        _validate_rss_stage_bytes(data, row, raw=raw)


def _snapshot_linked_inputs(
    document: dict[str, Any],
    relative_study: str,
    study_hash: str,
) -> dict[str, tuple[str, int]]:
    """Pin the inspected study and complete declared evidence byte sets.

    Returns:
        Original SHA-256 and read limit for each retained input path.

    """
    snapshots = {relative_study: (study_hash, MAX_STUDY_BYTES)}
    linked = {
        (row["experiment_manifest"], evidence.MAX_MANIFEST_BYTES)
        for row in document["observations"]
    }
    linked.update({
        (row["raw_sample"], raw_samples.MAX_RAW_BYTES)
        for row in document["observations"]
    })
    linked.update({
        (relative, RSS_REPORT_LIMIT)
        for relative in _rss_receipt_paths(document, _prefix(relative_study))
    })
    for relative, limit in sorted(linked):
        data = evidence.read_bounded_regular(_ROOT, relative, limit=limit)
        snapshots[relative] = (sha256(data).hexdigest(), limit)
    return snapshots


def _recheck_linked_inputs(
    snapshots: dict[str, tuple[str, int]],
) -> None:
    """Reject inspected study and linked-byte changes before publishing."""
    for relative, (original, limit) in snapshots.items():
        current = evidence.read_bounded_regular(_ROOT, relative, limit=limit)
        if sha256(current).hexdigest() != original:
            _fail(
                f"target audit linked input changed before report: {relative}"
            )


def _admit_study(
    relative_study: str,
    *,
    options: AuditOptions,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, str],
    dict[str, tuple[str, int]],
    str,
    int,
]:
    prefix = _prefix(relative_study)
    document, study_hash = _document(relative_study)
    _producer_study(document)
    names = _producer_rows(document, prefix)
    snapshots = _snapshot_linked_inputs(document, relative_study, study_hash)
    for folder, extension in (("runs", ".toml"), ("raw", ".csv")):
        _check_directory(
            prefix,
            folder,
            {f"{stem}{extension}" for stem in names},
        )
    _check_rss_receipts(document, prefix, names)
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
    if options.require_source_commit_object:
        _require_git_commit(commit)
    source_hashes = _source_checks(document, prefix, names)
    replayed = (
        _replay(
            document,
            source_hashes,
            emitter=options.emitter or producer.DEFAULT_EMITTER,
            runner=options.runner or producer.DEFAULT_RUNNER,
        )
        if options.replay_candidates
        else 0
    )
    return document, checked, source_hashes, snapshots, commit, replayed


def _recheck_sources(source_hashes: dict[str, str]) -> None:
    """Refuse observed retained-source drift before reporting an audit."""
    for relative, recorded in source_hashes.items():
        current = evidence.read_bounded_regular(
            _ROOT,
            relative,
            limit=producer.MAX_TARGET_BYTES,
        )
        if sha256(current).hexdigest() != recorded:
            _fail("target audit retained source changed before report")


def _recheck_inventory(document: dict[str, Any], relative_study: str) -> None:
    """Refuse late additions, removals, or linked file substitutions."""
    prefix = _prefix(relative_study)
    names = _producer_rows(document, prefix)
    for folder, extension in (("runs", ".toml"), ("raw", ".csv")):
        _check_directory(
            prefix,
            folder,
            {f"{stem}{extension}" for stem in names},
        )
    _check_rss_receipt_inventory(document, prefix, names)
    _candidate_files(prefix, names)


def _stage_rss_values(
    row: dict[str, Any],
    prefix: str,
    *,
    raw: bool,
) -> dict[str, int]:
    path = f"{prefix}/{RSS_RECEIPT_DIR}/{_row_stem(row)}.json"
    data = evidence.read_bounded_regular(_ROOT, path, limit=RSS_REPORT_LIMIT)
    _validate_rss_stage_bytes(data, row, raw=raw)
    record = _rss_record(data, raw=raw)
    return {key: record["stages"][key] for key in RSS_STAGE_NAMES}


def _stage_rss_group(
    observations: list[dict[str, Any]],
    *,
    difficulty: int,
    algorithm: str,
) -> dict[str, Any]:
    results: dict[str, Any] = {
        "difficulty": difficulty,
        "algorithm": algorithm,
        "attempts": len(observations),
        "verified": sum(entry["stages"] is not None for entry in observations),
        "not_verified": sum(entry["stages"] is None for entry in observations),
    }
    for stage in RSS_STAGE_NAMES:
        samples = [
            entry["stages"][stage]
            for entry in observations
            if entry["stages"] is not None
        ]
        if samples:
            results[stage] = {
                "median_bytes": int(median(samples)),
                "range_bytes": [min(samples), max(samples)],
            }
    return results


def _stage_rss_pairs(
    rows: dict[tuple[int, str], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    report = []
    for difficulty in sorted({key[0] for key in rows}):
        walk = {x["trial"]: x["stages"] for x in rows[difficulty, WALK]}
        skip = {x["trial"]: x["stages"] for x in rows[difficulty, SKIP]}
        both = [
            (walk[trial], skip[trial])
            for trial in sorted(set(walk) & set(skip))
            if walk[trial] is not None and skip[trial] is not None
        ]
        deltas = (
            {
                name: int(
                    median([
                        candidate[name] - baseline[name]
                        for baseline, candidate in both
                    ])
                )
                for name in RSS_STAGE_NAMES
            }
            if both
            else {}
        )
        report.append({
            "difficulty": difficulty,
            "both_verified": len(both),
            "median_skip_minus_walk_bytes": deltas,
        })
    return report


def _stage_rss_breakdown(
    document: dict[str, Any],
    prefix: str,
) -> dict[str, Any]:
    if not _retained_rss_document(document):
        _fail("stage RSS breakdown requires version-six or seven receipts")
    rows: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    raw = document["study"]["id"] == FORWARD_RAW_RSS_STUDY
    for row in document["observations"]:
        stages = (
            _stage_rss_values(row, prefix, raw=raw)
            if row["outcome"] == analyze.VERIFIED
            else None
        )
        key = (row["case"]["difficulty"], row["algorithm"])
        rows[key].append({"trial": row["trial"], "stages": stages})
    return {
        "scope": (
            "Conditional on verified trials; independently checked source-"
            "reported child peak RSS, not whole-study memory or attestation."
        ),
        "groups": [
            _stage_rss_group(samples, difficulty=level, algorithm=name)
            for (level, name), samples in sorted(rows.items())
        ],
        "paired": _stage_rss_pairs(rows),
    }


def _checked_report(
    document: dict[str, Any],
    relative: str,
    options: AuditOptions,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    report = analyze.analyze(document)
    breakdown = (
        _stage_rss_breakdown(document, _prefix(relative))
        if options.stage_rss_breakdown
        else None
    )
    return report, breakdown


def audit(
    relative_study: str,
    *,
    options: AuditOptions = DEFAULT_AUDIT_OPTIONS,
) -> dict[str, Any]:
    """Read retained target evidence and optionally replay successful sources.

    Returns:
        Source admission, optional VM witness count and arena comparison.

    Raises:
        TargetEchoAuditError: The producer evidence fails any required gate.

    """
    _admit_options(options)
    try:
        (document, checked, source_hashes, snapshots, commit, replayed) = (
            _admit_study(relative_study, options=options)
        )
        report, stage_rss = _checked_report(document, relative_study, options)
        _recheck_sources(source_hashes)
        _recheck_linked_inputs(snapshots)
        _recheck_inventory(document, relative_study)
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
    answer = {
        "schema_version": 1,
        "study": relative_study,
        "retained_study_sha256": snapshots[relative_study][0],
        "source_commit_reported": commit,
        "source_commit_object_verified": options.require_source_commit_object,
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
    if stage_rss is not None:
        answer["stage_rss_breakdown"] = stage_rss
    return answer


def main() -> int:
    """Audit one retained local target echo study and publish checked JSON.

    Returns:
        Zero for a complete audit, two for any rejected input or output.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", help=".temp/arena-target-echo-*/study.json")
    parser.add_argument("--replay-candidates", action="store_true")
    parser.add_argument("--require-source-commit-object", action="store_true")
    parser.add_argument("--stage-rss-breakdown", action="store_true")
    args = parser.parse_args()
    try:
        result = audit(
            args.study,
            options=AuditOptions(
                replay_candidates=args.replay_candidates,
                require_source_commit_object=args.require_source_commit_object,
                stage_rss_breakdown=args.stage_rss_breakdown,
            ),
        )
        report_output.publish(result, sys.stdout)
    except (TargetEchoAuditError, report_output.ReportOutputError) as error:
        parser.exit(2, f"target echo audit: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
