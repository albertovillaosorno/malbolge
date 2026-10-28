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
#   - Deterministic multi-objective summaries of retained trial records.
# - Must-Not:
#   - Execute guest programs, certify candidates, or invent measurements.
# - Allows:
#   - Inputs: versioned JSON study and per-trial observation records.
#   - Outputs: capacity and Pareto JSON on standard output.
#   - Side effects: read one caller-supplied input file.
# - Split-When:
#   - Independent experiment/benchmark manifest admission is implemented.
# - Merge-When:
#   - A repository-owned arena aggregator replaces this boundary.
# - Summary:
#   - Keeps failed trials and fair comparison cohorts visible.
# - Description:
#   - Summarizes reported verifier outcomes; never certifies them.
# - Usage:
#   - python3.14 -B benchmarks/arena/analyze.py records.json
# - Defaults:
#   - Unknown metrics, missing trials and mismatched workloads fail closed.
#

"""Deterministic capacity and Pareto analysis of reported benchmark trials."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
import json
from pathlib import Path
import stat
import sys
from typing import Any
from typing import Never

from benchmarks.arena import median_intervals

SCHEMA_VERSION = 1
SHA256_HEX_LENGTH = 64
SHA256_ALPHABET = frozenset("0123456789abcdef")
NUL = "\x00"
BACKSLASH = "\\"
COLON = ":"
CURRENT_DIR = "."
PARENT_DIR = ".."
VERIFIED = "verified"
ACCEPTED = "accepted"
REJECTED = "rejected"
VERIFIER_REJECTED = "verifier_rejected"
NOT_RUN = "not_run"
ELAPSED = "elapsed_ns"
COST_METRICS = frozenset({
    ELAPSED,
    "artifact_bytes",
    "energy_uj",
    "runtime_steps",
    "peak_rss_bytes",
    "peak_vram_bytes",
    "verifier_ns",
})
OUTCOMES = frozenset({
    VERIFIED,
    VERIFIER_REJECTED,
    "no_solution",
    "resource_exhausted",
    "tool_failed",
})
MAX_INPUT_BYTES = 16 * 1024 * 1024
MIN_COMPARISON_ALGORITHMS = 2
PEAK_RSS = "peak_rss_bytes"
STUDY_FIELDS = {
    "id",
    "question",
    "hypothesis",
    "baseline",
    "rejection_observation",
    "stage",
    "target_profile",
    "host",
    "toolchain",
    "budget",
    "objectives",
}
OBSERVATION_FIELDS = {
    "algorithm",
    "case",
    "trial",
    "outcome",
    "verifier",
    "verifier_verdict",
    "experiment_manifest",
    "raw_sample",
    "metrics",
}
CASE_FIELDS = {"family", "version", "difficulty", "seed", "workload_sha256"}


class ArenaError(ValueError):
    """Invalid or incomparable arena evidence."""


def _fail(message: str) -> Never:
    raise ArenaError(message)


def _mapping(value: object, keys: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        _fail(f"{where}: expected fields {sorted(keys)}")
    return value


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        _fail(f"{where}: expected nonempty, unpadded text")
    if NUL in value:
        _fail(f"{where}: NUL not allowed")
    return value


def _integer(value: object, where: str, *, positive: bool = False) -> int:
    if type(value) is not int or value < int(positive):
        kind = "positive" if positive else "nonnegative"
        _fail(f"{where}: expected {kind} integer")
    return value


def _hash(value: object, where: str) -> str:
    text = _text(value, where)
    if len(text) != SHA256_HEX_LENGTH or not set(text) <= SHA256_ALPHABET:
        _fail(f"{where}: expected lowercase SHA-256 hex")
    return text


def _relative(value: object, where: str) -> str:
    path = _text(value, where)
    if path.startswith(("/", BACKSLASH)) or BACKSLASH in path:
        _fail(f"{where}: expected repository-relative path")
    if COLON in path or set(path.split("/")) & {"", CURRENT_DIR, PARENT_DIR}:
        _fail(f"{where}: expected canonical repository-relative path")
    return path


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> Never:
    _fail(f"nonfinite JSON number: {value}")


def _objectives(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        _fail("study.objectives: expected nonempty list")
    if any(
        not isinstance(item, str) or item not in COST_METRICS for item in value
    ):
        _fail("study.objectives: unknown cost metric")
    if len(set(value)) != len(value):
        _fail("study.objectives: duplicate cost metric")
    return value


def _study(value: object) -> dict[str, Any]:
    study = _mapping(value, STUDY_FIELDS, "study")
    text_fields = STUDY_FIELDS - {"budget", "objectives"}
    for name in sorted(text_fields):
        _text(study[name], f"study.{name}")
    budget = _mapping(study["budget"], {"time_ns", "memory_bytes"}, "budget")
    for name, quantity in budget.items():
        _integer(quantity, f"budget.{name}", positive=True)
    _objectives(study["objectives"])
    return study


def _case(value: object, where: str) -> dict[str, Any]:
    case = _mapping(value, CASE_FIELDS, f"{where}.case")
    _text(case["family"], f"{where}.case.family")
    for key in ("version", "difficulty"):
        _integer(case[key], f"{where}.case.{key}", positive=True)
    _integer(case["seed"], f"{where}.case.seed")
    _hash(case["workload_sha256"], f"{where}.case.workload_sha256")
    return case


def _verdict(row: dict[str, Any], where: str) -> None:
    outcome = row["outcome"]
    if not isinstance(outcome, str) or outcome not in OUTCOMES:
        _fail(f"{where}.outcome: unknown outcome")
    verifier = _text(row["verifier"], f"{where}.verifier")
    verdict = row["verifier_verdict"]
    if not isinstance(verdict, str) or verdict not in {
        ACCEPTED,
        REJECTED,
        NOT_RUN,
    }:
        _fail(f"{where}.verifier_verdict: unknown verdict")
    accepted = (outcome == VERIFIED) == (verdict == ACCEPTED)
    rejected = (outcome == VERIFIER_REJECTED) == (verdict == REJECTED)
    separate = outcome != VERIFIED or verifier != row["algorithm"]
    if not (accepted and rejected and separate):
        _fail(f"{where}: inconsistent independent verifier evidence")


def _metrics_shape(value: object, where: str) -> dict[str, int]:
    if not isinstance(value, dict) or not set(value) <= COST_METRICS:
        _fail(f"{where}.metrics: unknown metric")
    if ELAPSED not in value:
        _fail(f"{where}.metrics: elapsed_ns required even on failure")
    for name, quantity in value.items():
        _integer(quantity, f"{where}.metrics.{name}")
    return value


def _metrics(
    row: dict[str, Any],
    objectives: list[str],
    where: str,
    *,
    budget: dict[str, int],
) -> None:
    metrics = _metrics_shape(row["metrics"], where)
    if row["outcome"] != VERIFIED:
        return
    if not set(objectives) <= set(metrics):
        _fail(f"{where}: verified trial missing declared objective")
    _within_budget(metrics, budget, where)


def _within_budget(
    metrics: dict[str, int],
    budget: dict[str, int],
    where: str,
) -> None:
    if metrics[ELAPSED] > budget["time_ns"]:
        _fail(f"{where}: verified elapsed time exceeds study budget")
    if PEAK_RSS in metrics and metrics[PEAK_RSS] > budget["memory_bytes"]:
        _fail(f"{where}: verified resident memory exceeds study budget")


def _observation(
    value: object,
    objectives: list[str],
    index: int,
    *,
    budget: dict[str, int],
) -> dict[str, Any]:
    where = f"observations[{index}]"
    row = _mapping(value, OBSERVATION_FIELDS, where)
    _text(row["algorithm"], f"{where}.algorithm")
    _case(row["case"], where)
    _integer(row["trial"], f"{where}.trial")
    _verdict(row, where)
    _relative(row["experiment_manifest"], f"{where}.experiment_manifest")
    _relative(row["raw_sample"], f"{where}.raw_sample")
    _metrics(row, objectives, where, budget=budget)
    return row


def _trial_key(row: dict[str, Any]) -> tuple[Any, ...]:
    case = row["case"]
    return (
        row["algorithm"],
        case["family"],
        case["version"],
        case["difficulty"],
        case["seed"],
        row["trial"],
    )


def _decode_document(text: str) -> dict[str, Any]:
    try:
        document = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except (ValueError, TypeError, RecursionError) as error:
        message = f"invalid arena JSON: {error}"
        raise ArenaError(message) from error
    root = _mapping(
        document,
        {"schema_version", "study", "observations"},
        "root",
    )
    version = root["schema_version"]
    if type(version) is not int or version != SCHEMA_VERSION:
        _fail("unsupported arena schema version")
    return root


def parse_document(text: str) -> dict[str, Any]:
    """Admit exact version-one input and all reported outcomes.

    Returns:
        A structurally admitted study; references are not authenticated.

    """
    root = _decode_document(text)
    study = _study(root["study"])
    observations = root["observations"]
    if not isinstance(observations, list) or not observations:
        _fail("observations: expected nonempty array")
    seen: set[tuple[Any, ...]] = set()
    for index, item in enumerate(observations):
        row = _observation(
            item,
            study["objectives"],
            index,
            budget=study["budget"],
        )
        key = _trial_key(row)
        if key in seen:
            _fail(f"observations[{index}]: duplicate algorithm/case/trial")
        seen.add(key)
    return root


def _case_key(row: dict[str, Any]) -> tuple[Any, ...]:
    case = row["case"]
    return (case["family"], case["version"], case["difficulty"])


def _median_fraction(values: list[Fraction]) -> Fraction:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _exact_pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _exact_median(values: list[int]) -> list[int]:
    return _exact_pair(_median_fraction([Fraction(value) for value in values]))


def _exact_mad(values: list[int]) -> list[int]:
    values_as_fractions = [Fraction(value) for value in values]
    center = _median_fraction(values_as_fractions)
    deviations = [abs(value - center) for value in values_as_fractions]
    return _exact_pair(_median_fraction(deviations))


def _dominates(
    a: dict[str, Any], b: dict[str, Any], objectives: list[str]
) -> bool:
    # More verified trials is better; every declared cost is minimized.
    if a["verified"] < b["verified"]:
        return False
    cost_pairs = [
        (Fraction(*a["medians"][name]), Fraction(*b["medians"][name]))
        for name in objectives
    ]
    if any(left > right for left, right in cost_pairs):
        return False
    return a["verified"] > b["verified"] or any(
        left < right for left, right in cost_pairs
    )


def _workload_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row["case"]["seed"], row["case"]["workload_sha256"], row["trial"])


def _cohort(rows: list[dict[str, Any]]) -> set[tuple[Any, ...]]:
    return {_workload_key(row) for row in rows}


def _verifier_cohort(rows: list[dict[str, Any]]) -> set[tuple[Any, ...]]:
    return {
        (
            row["case"]["seed"],
            row["case"]["workload_sha256"],
            row["trial"],
            row["verifier"],
        )
        for row in rows
    }


def _paired_outcomes(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, int]:
    names = {
        (True, True): "both_verified",
        (True, False): "baseline_only_verified",
        (False, True): "candidate_only_verified",
        (False, False): "neither_verified",
    }
    counts = dict.fromkeys(names.values(), 0)
    for baseline, candidate in pairs:
        state = (
            baseline["outcome"] == VERIFIED,
            candidate["outcome"] == VERIFIED,
        )
        counts[names[state]] += 1
    return counts


def _paired_cost(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    name: str,
    *,
    median_intervals_95: bool = False,
) -> dict[str, Any]:
    differences = [
        candidate["metrics"][name] - baseline["metrics"][name]
        for baseline, candidate in pairs
        if baseline["outcome"] == VERIFIED and candidate["outcome"] == VERIFIED
    ]
    result = {
        "candidate_lower": sum(diff < 0 for diff in differences),
        "candidate_equal": sum(diff == 0 for diff in differences),
        "candidate_higher": sum(diff > 0 for diff in differences),
        "median_candidate_minus_baseline": (
            _exact_median(differences) if differences else None
        ),
    }
    if median_intervals_95:
        result["median_confidence_interval_95"] = (
            median_intervals.median_interval_95(differences)
        )
    return result


@dataclass(frozen=True, slots=True)
class _AnalysisPolicy:
    objectives: list[str]
    median_intervals_95: bool


def _paired_per_cohort(
    key: tuple[Any, ...],
    algorithms: dict[str, list[dict[str, Any]]],
    baseline: str,
    *,
    policy: _AnalysisPolicy,
) -> list[dict[str, Any]]:
    baseline_rows = sorted(algorithms[baseline], key=_workload_key)
    result = []
    for algorithm, candidate in sorted(algorithms.items()):
        if algorithm == baseline:
            continue
        paired = list(
            zip(
                baseline_rows,
                sorted(candidate, key=_workload_key),
                strict=True,
            )
        )
        result.append({
            "family": key[0],
            "version": key[1],
            "difficulty": key[2],
            "baseline": baseline,
            "algorithm": algorithm,
            "paired_trials": len(paired),
            "outcomes": _paired_outcomes(paired),
            "cost_differences": {
                name: _paired_cost(
                    paired,
                    name,
                    median_intervals_95=policy.median_intervals_95,
                )
                for name in policy.objectives
            },
        })
    return result


def _point(
    algorithm: str,
    key: tuple[Any, ...],
    rows: list[dict[str, Any]],
    *,
    policy: _AnalysisPolicy,
) -> dict[str, Any]:
    successes = [row for row in rows if row["outcome"] == VERIFIED]
    success_values = {
        name: [row["metrics"][name] for row in successes]
        for name in policy.objectives
    }
    all_elapsed = [row["metrics"][ELAPSED] for row in rows]
    point = {
        "algorithm": algorithm,
        "family": key[0],
        "version": key[1],
        "difficulty": key[2],
        "attempts": len(rows),
        "verified": len(successes),
        "success_fraction": [len(successes), len(rows)],
        "outcomes": {
            kind: sum(row["outcome"] == kind for row in rows)
            for kind in sorted(OUTCOMES)
        },
        "medians": {
            name: _exact_median(values) if values else None
            for name, values in success_values.items()
        },
        "median_absolute_deviation": {
            name: _exact_mad(values) if values else None
            for name, values in success_values.items()
        },
        "successful_range": {
            name: [min(values), max(values)] if values else None
            for name, values in success_values.items()
        },
        "all_attempt_elapsed_ns": {
            "median": _exact_median(all_elapsed),
            "median_absolute_deviation": _exact_mad(all_elapsed),
            "range": [min(all_elapsed), max(all_elapsed)],
        },
    }
    if policy.median_intervals_95:
        point["median_confidence_intervals_95"] = {
            name: median_intervals.median_interval_95(values)
            for name, values in success_values.items()
        }
        point["all_attempt_elapsed_ns"]["median_confidence_interval_95"] = (
            median_intervals.median_interval_95(all_elapsed)
        )
    return point


def _frontier(
    key: tuple[Any, ...],
    points: list[dict[str, Any]],
    objectives: list[str],
) -> dict[str, Any]:
    successful = [point for point in points if point["verified"] > 0]
    winners = sorted(
        point["algorithm"]
        for point in successful
        if not any(
            _dominates(other, point, objectives)
            for other in successful
            if other is not point
        )
    )
    return {
        "family": key[0],
        "version": key[1],
        "difficulty": key[2],
        "algorithms": winners,
        "excluded_without_verified_solution": sorted(
            point["algorithm"] for point in points if point["verified"] == 0
        ),
    }


def _capacities(curve: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, int], list[int]] = defaultdict(list)
    for point in curve:
        key = (point["algorithm"], point["family"], point["version"])
        if point["verified"] > 0:
            groups[key].append(point["difficulty"])
        else:
            _ = groups[key]
    return [
        {
            "algorithm": key[0],
            "family": key[1],
            "version": key[2],
            "highest_observed_verified_difficulty": max(values, default=None),
        }
        for key, values in sorted(groups.items())
    ]


def _validate_comparison(
    key: tuple[Any, ...],
    algorithms: dict[str, list[dict[str, Any]]],
    baseline: str,
) -> None:
    first = _cohort(next(iter(algorithms.values())))
    if any(_cohort(rows) != first for rows in algorithms.values()):
        _fail(f"unmatched trial/workload cohort for {key}")
    verifier_reference = _verifier_cohort(next(iter(algorithms.values())))
    if any(
        _verifier_cohort(rows) != verifier_reference
        for rows in algorithms.values()
    ):
        _fail(f"unmatched verifier cohort for {key}")
    if baseline not in algorithms:
        _fail(f"missing declared baseline for {key}")
    if len(algorithms) < MIN_COMPARISON_ALGORITHMS:
        _fail(f"no comparison algorithm for declared baseline in {key}")


def analyze(
    document: dict[str, Any],
    *,
    median_intervals_95: bool = False,
) -> dict[str, Any]:
    """Summarize exact trial counts and matched Pareto sets.

    Returns:
        Deterministically ordered capacity and conditional Pareto evidence.

    """
    study = document["study"]
    objectives: list[str] = study["objectives"]
    policy = _AnalysisPolicy(objectives, median_intervals_95)
    grouped: dict[tuple[Any, ...], dict[str, list[dict[str, Any]]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    for row in document["observations"]:
        grouped[_case_key(row)][row["algorithm"]].append(row)
    capacity = []
    frontiers = []
    paired_comparisons = []
    for key, algorithms in sorted(grouped.items()):
        _validate_comparison(key, algorithms, study["baseline"])
        points = [
            _point(
                name,
                key,
                rows,
                policy=policy,
            )
            for name, rows in sorted(algorithms.items())
        ]
        capacity.extend(points)
        frontiers.append(_frontier(key, points, objectives))
        paired_comparisons.extend(
            _paired_per_cohort(
                key,
                algorithms,
                study["baseline"],
                policy=policy,
            )
        )
    report = {
        "schema_version": SCHEMA_VERSION,
        "study_id": study["id"],
        "stage": study["stage"],
        "objectives": objectives,
        "capacity_curve": capacity,
        "highest_observed_verified_difficulty": _capacities(capacity),
        "pareto_frontiers": frontiers,
        "paired_baseline_comparisons": paired_comparisons,
        "verification_note": (
            "Outcomes are reported, not independently certified by this "
            "analyzer. Pareto costs are exact rational medians conditional "
            "on verified success. Descriptive dispersion is not a "
            "confidence interval."
        ),
    }
    if median_intervals_95:
        report["median_interval_policy"] = {
            "method": "exact-symmetric-binomial-order-statistics",
            "requested_confidence": [19, 20],
            "minimum_samples": median_intervals.MIN_SAMPLES,
            "maximum_samples": median_intervals.MAX_SAMPLES,
            "assumptions": (
                "Independent identically distributed trials; bounds are "
                "conservative under ties. Conditional success-only and "
                "both-success paired intervals do not generalize to failures. "
                "Sample independence and physical measurements are not "
                "established by this analyzer."
            ),
            "pareto_uses_intervals": False,
        }
    return report


def read_input(path: Path) -> str:
    """Read only a bounded ordinary source file under strict UTF-8.

    Returns:
        A UTF-8 study document bounded to the declared input limit.

    """
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        _fail("arena input must be a regular file, not a link or device")
    if info.st_size > MAX_INPUT_BYTES:
        _fail("arena input exceeds 16 MiB limit")
    with path.open("rb") as stream:
        data = stream.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        _fail("arena input exceeds 16 MiB limit")
    return data.decode("utf-8")


def main() -> int:
    """Read one bounded study input and write deterministic JSON to stdout.

    Returns:
        Zero on successful analysis; invalid input exits with status two.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--median-intervals-95", action="store_true")
    args = parser.parse_args()
    try:
        document = parse_document(read_input(args.input))
        report = analyze(document, median_intervals_95=args.median_intervals_95)
    except (ArenaError, OSError, UnicodeError) as error:
        parser.exit(2, f"arena: {error}\n")
    _ = sys.stdout.write(json.dumps(report, sort_keys=True, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
