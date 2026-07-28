# File:
#   - benchmark_protocol.py
# Path:
#   - scripts/validate/benchmark_protocol.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
#
# Boundary-Contract:
# - Owns:
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Validate benchmark and statistical evidence protocol records.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Validate benchmark and statistical evidence protocol records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import tomllib
from typing import Never
from typing import cast

from scripts.validate import experiment_manifest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_ROOT = ROOT / "benchmarks" / "research" / "protocol" / "examples"
SCHEMA_VERSION = 1
PARENT_SEGMENT = ".."
MIN_REPETITIONS = 3
DETERMINISTIC_KIND = "deterministic"
STOCHASTIC_KIND = "stochastic"
STUDY_KINDS = frozenset({DETERMINISTIC_KIND, STOCHASTIC_KIND})
RETAIN_ALL = "retain-all"
PREREGISTERED_FILTER = "preregistered-filter"
NO_OUTLIER_RULE = "none"
OUTLIER_POLICIES = frozenset({PREREGISTERED_FILTER, RETAIN_ALL})
ORDERING_POLICIES = frozenset({"fixed", "seeded-random"})
CENTER_METHODS = frozenset({"mean", "median"})
DISPERSION_METHODS = frozenset({
    "bootstrap-ci",
    "iqr",
    "min-max",
    "standard-deviation",
    "trial-distribution",
})
UNCERTAINTY_METHODS = frozenset({
    "bootstrap-ci",
    "observed-range",
    "standard-error",
    "trial-distribution",
})
REQUIRED_TABLES = (
    "measurement",
    "objectives",
    "raw",
    "resources",
    "statistics",
    "stochastic",
    "study",
    "workload",
)


class BenchmarkProtocolError(ValueError):
    """Benchmark evidence record violates the statistical protocol."""


@dataclass(frozen=True, slots=True)
class BenchmarkProtocolRecord:
    """Validated benchmark protocol identity and statistical obligations."""

    accelerator: str
    experiment_manifest: str
    failed_trials: int
    host: str
    identifier: str
    kind: str
    metrics: tuple[str, ...]
    outlier_policy: str
    raw_path: str
    repetitions: int
    seeds: tuple[int, ...]
    trial_count: int
    workload_identity: str


@dataclass(frozen=True, slots=True)
class _Study:
    experiment_manifest: str
    identifier: str
    kind: str


@dataclass(frozen=True, slots=True)
class _Measurement:
    outlier_policy: str
    repetitions: int


@dataclass(frozen=True, slots=True)
class _Resources:
    accelerator: str
    host: str


@dataclass(frozen=True, slots=True)
class _Stochastic:
    failed_trials: int
    seeds: tuple[int, ...]
    trial_count: int


def _fail(message: str) -> Never:
    raise BenchmarkProtocolError(message)


def _mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        _fail(f"{context} must be a table")
    raw = cast("dict[object, object]", value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            _fail(f"{context} contains a non-string key")
        result[key] = item
    return result


def _table(document: dict[str, object], name: str) -> dict[str, object]:
    if name not in document:
        _fail(f"benchmark.{name} table is required")
    return _mapping(document[name], f"benchmark.{name}")


def _string(table: dict[str, object], name: str, context: str) -> str:
    value = table.get(name)
    if type(value) is not str or not value:
        _fail(f"{context}.{name} must be a non-empty string")
    return value


def _integer(table: dict[str, object], name: str, context: str) -> int:
    value = table.get(name)
    if type(value) is not int:
        _fail(f"{context}.{name} must be an integer")
    return value


def _boolean(table: dict[str, object], name: str, context: str) -> bool:
    value = table.get(name)
    if type(value) is not bool:
        _fail(f"{context}.{name} must be a boolean")
    return value


def _array(table: dict[str, object], name: str, context: str) -> list[object]:
    value = table.get(name)
    if not isinstance(value, list):
        _fail(f"{context}.{name} must be an array")
    return cast("list[object]", value)


def _string_array(
    table: dict[str, object],
    name: str,
    context: str,
) -> tuple[str, ...]:
    values = _array(table, name, context)
    result: list[str] = []
    for index, value in enumerate(values):
        if type(value) is not str or not value:
            _fail(f"{context}.{name}[{index}] must be a non-empty string")
        result.append(value)
    return tuple(result)


def _integer_array(
    table: dict[str, object],
    name: str,
    context: str,
) -> tuple[int, ...]:
    values = _array(table, name, context)
    result: list[int] = []
    for index, value in enumerate(values):
        if type(value) is not int or value < 0:
            _fail(f"{context}.{name}[{index}] must be a non-negative integer")
        result.append(value)
    return tuple(result)


def _enum(value: str, allowed: frozenset[str], context: str) -> str:
    if value not in allowed:
        _fail(f"unsupported {context}: {value}")
    return value


def _relative_path(value: str, context: str) -> str:
    path = Path(value)
    if path.is_absolute() or PARENT_SEGMENT in path.parts:
        _fail(f"{context} must be repository-relative: {value}")
    return path.as_posix()


def _parse_document(text: str) -> dict[str, object]:
    try:
        parsed = cast("object", tomllib.loads(text))
    except tomllib.TOMLDecodeError as error:
        _fail(f"invalid TOML: {error}")
    document = _mapping(parsed, "benchmark")
    version = document.get("schema_version")
    if type(version) is not int or version != SCHEMA_VERSION:
        _fail(f"unsupported benchmark protocol schema: {version}")
    for table_name in REQUIRED_TABLES:
        _ = _table(document, table_name)
    return document


def _study(document: dict[str, object]) -> _Study:
    table = _table(document, "study")
    for field in (
        "baseline",
        "hypothesis",
        "question",
        "rejection_observation",
    ):
        _ = _string(table, field, "benchmark.study")
    kind = _enum(
        _string(table, "kind", "benchmark.study"),
        STUDY_KINDS,
        "study kind",
    )
    experiment_path = _relative_path(
        _string(table, "experiment_manifest", "benchmark.study"),
        "benchmark.study.experiment_manifest",
    )
    return _Study(
        experiment_manifest=experiment_path,
        identifier=_string(table, "id", "benchmark.study"),
        kind=kind,
    )


def _workload(document: dict[str, object]) -> str:
    table = _table(document, "workload")
    if not _boolean(table, "equivalent", "benchmark.workload"):
        _fail("benchmark comparisons require equivalent_workload = true")
    return _string(table, "identity", "benchmark.workload")


def _measurement(document: dict[str, object]) -> _Measurement:
    table = _table(document, "measurement")
    warmups = _integer(table, "warmup_iterations", "benchmark.measurement")
    repetitions = _integer(table, "repetitions", "benchmark.measurement")
    if warmups < 0:
        _fail("benchmark.measurement.warmup_iterations must be non-negative")
    if repetitions < MIN_REPETITIONS:
        _fail(f"benchmark.measurement.repetitions must be >= {MIN_REPETITIONS}")
    _ = _string(table, "warmup_policy", "benchmark.measurement")
    _ = _string(table, "stopping_rule", "benchmark.measurement")
    _ = _enum(
        _string(table, "ordering", "benchmark.measurement"),
        ORDERING_POLICIES,
        "measurement ordering",
    )
    policy = _enum(
        _string(table, "outlier_policy", "benchmark.measurement"),
        OUTLIER_POLICIES,
        "outlier policy",
    )
    _validate_outlier_rule(table, policy)
    return _Measurement(outlier_policy=policy, repetitions=repetitions)


def _validate_outlier_rule(table: dict[str, object], policy: str) -> None:
    rule = _string(table, "outlier_rule", "benchmark.measurement")
    if policy == RETAIN_ALL and rule != NO_OUTLIER_RULE:
        _fail("retain-all outlier policy requires outlier_rule = none")
    if policy == PREREGISTERED_FILTER and rule == NO_OUTLIER_RULE:
        _fail("preregistered-filter requires an explicit outlier rule")


def _statistics(document: dict[str, object]) -> None:
    table = _table(document, "statistics")
    _ = _enum(
        _string(table, "center", "benchmark.statistics"),
        CENTER_METHODS,
        "center statistic",
    )
    _ = _enum(
        _string(table, "dispersion", "benchmark.statistics"),
        DISPERSION_METHODS,
        "dispersion statistic",
    )
    _ = _enum(
        _string(table, "uncertainty", "benchmark.statistics"),
        UNCERTAINTY_METHODS,
        "uncertainty statistic",
    )


def _objectives(document: dict[str, object]) -> tuple[str, ...]:
    table = _table(document, "objectives")
    metrics = _string_array(table, "metrics", "benchmark.objectives")
    if not metrics:
        _fail("benchmark.objectives.metrics must not be empty")
    if len(metrics) != len(set(metrics)):
        _fail("benchmark.objectives.metrics must be unique")
    _ = _string(table, "tradeoff_policy", "benchmark.objectives")
    return metrics


def _resources(document: dict[str, object]) -> _Resources:
    table = _table(document, "resources")
    host = _string(table, "host", "benchmark.resources")
    accelerator = _string(table, "accelerator", "benchmark.resources")
    memory_mib = _integer(table, "memory_mib", "benchmark.resources")
    if memory_mib <= 0:
        _fail("benchmark.resources.memory_mib must be positive")
    return _Resources(accelerator=accelerator, host=host)


def _raw_path(document: dict[str, object]) -> str:
    table = _table(document, "raw")
    if not _boolean(table, "retained", "benchmark.raw"):
        _fail("benchmark.raw.retained must be true")
    return _relative_path(
        _string(table, "path", "benchmark.raw"),
        "benchmark.raw.path",
    )


def _stochastic(document: dict[str, object], kind: str) -> _Stochastic:
    table = _table(document, "stochastic")
    trial_count = _integer(table, "trial_count", "benchmark.stochastic")
    failed_trials = _integer(table, "failed_trials", "benchmark.stochastic")
    seeds = _integer_array(table, "seeds", "benchmark.stochastic")
    if kind == STOCHASTIC_KIND:
        _validate_stochastic_trials(trial_count, failed_trials, seeds)
    else:
        _validate_deterministic_trials(trial_count, failed_trials, seeds)
    return _Stochastic(
        failed_trials=failed_trials,
        seeds=seeds,
        trial_count=trial_count,
    )


def _validate_stochastic_trials(
    trial_count: int,
    failed_trials: int,
    seeds: tuple[int, ...],
) -> None:
    if trial_count <= 0:
        _fail("stochastic benchmark requires a positive trial_count")
    if failed_trials < 0 or failed_trials > trial_count:
        _fail("stochastic failed_trials must be within trial_count")
    if len(seeds) != trial_count or len(set(seeds)) != trial_count:
        _fail("stochastic benchmark requires one unique seed per trial")


def _validate_deterministic_trials(
    trial_count: int,
    failed_trials: int,
    seeds: tuple[int, ...],
) -> None:
    if trial_count != 0 or failed_trials != 0 or seeds:
        _fail("deterministic benchmark stochastic fields must be zero/empty")


def parse_protocol(text: str) -> BenchmarkProtocolRecord:
    """Parse and validate one benchmark statistical-protocol record.

    Returns:
        Immutable core obligations for one valid comparison record.

    """
    document = _parse_document(text)
    study = _study(document)
    workload_identity = _workload(document)
    measurement = _measurement(document)
    _statistics(document)
    metrics = _objectives(document)
    resources = _resources(document)
    raw_path = _raw_path(document)
    stochastic = _stochastic(document, study.kind)
    return BenchmarkProtocolRecord(
        accelerator=resources.accelerator,
        experiment_manifest=study.experiment_manifest,
        failed_trials=stochastic.failed_trials,
        host=resources.host,
        identifier=study.identifier,
        kind=study.kind,
        metrics=metrics,
        outlier_policy=measurement.outlier_policy,
        raw_path=raw_path,
        repetitions=measurement.repetitions,
        seeds=stochastic.seeds,
        trial_count=stochastic.trial_count,
        workload_identity=workload_identity,
    )


def validate_example(path: Path) -> BenchmarkProtocolRecord:
    """Validate one protocol example and its linked run/raw evidence.

    Returns:
        Parsed protocol after run-identity and raw-output checks.

    """
    if not path.is_file():
        _fail(f"benchmark protocol example not found: {path}")
    record = parse_protocol(path.read_text(encoding="utf-8"))
    run = _linked_run(record)
    _validate_linked_identity(record, run)
    raw_path = ROOT / record.raw_path
    if not raw_path.is_file() or raw_path.stat().st_size == 0:
        _fail(f"benchmark raw samples not retained: {record.raw_path}")
    return record


def _linked_run(
    record: BenchmarkProtocolRecord,
) -> experiment_manifest.RunIdentity:
    path = ROOT / record.experiment_manifest
    if not path.is_file():
        _fail(
            f"benchmark experiment run not found: {record.experiment_manifest}"
        )
    manifest = experiment_manifest.parse_manifest(
        path.read_text(encoding="utf-8")
    )
    if manifest.record_kind != experiment_manifest.RUN_RECORD_KIND:
        _fail("benchmark protocol must reference record_kind = run")
    if manifest.run is None:
        _fail("benchmark protocol linked run identity is missing")
    return manifest.run


def _validate_linked_identity(
    record: BenchmarkProtocolRecord,
    run: experiment_manifest.RunIdentity,
) -> None:
    if run.host != record.host or run.accelerator != record.accelerator:
        _fail("benchmark resources do not match linked experiment run")
    if run.raw_output != record.raw_path:
        _fail("benchmark raw path does not match linked experiment run")


def validate_repository_examples() -> tuple[BenchmarkProtocolRecord, ...]:
    """Validate every checked-in deterministic/stochastic protocol fixture.

    Returns:
        Protocol examples in stable path order.

    """
    examples = tuple(
        validate_example(path)
        for path in sorted(EXAMPLES_ROOT.glob("*.benchmark.toml"))
    )
    if not examples:
        _fail("repository contains no benchmark protocol examples")
    return examples


def main() -> int:
    """Validate checked-in benchmark protocol fixtures and return status.

    Returns:
        Zero for valid fixtures and one for deterministic policy failure.

    """
    try:
        examples = validate_repository_examples()
    except (BenchmarkProtocolError, OSError) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    _ = sys.stdout.write(
        f"benchmark protocol examples valid: {len(examples)}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
