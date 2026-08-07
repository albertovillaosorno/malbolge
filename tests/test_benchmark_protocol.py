# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
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
#   - Regression tests for benchmark statistical-protocol records.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Regression tests for benchmark statistical-protocol records."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.validate import benchmark_protocol as validator

ROOT = Path(__file__).resolve().parents[1]
STOCHASTIC_TRIALS = 4
DETERMINISTIC = (
    ROOT
    / "benchmarks"
    / "research"
    / "protocol"
    / "examples"
    / "deterministic.benchmark.toml"
)
STOCHASTIC = (
    ROOT
    / "benchmarks"
    / "research"
    / "protocol"
    / "examples"
    / "stochastic.benchmark.toml"
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _expect_failure(text: str, message: str) -> None:
    try:
        _ = validator.parse_protocol(text)
    except validator.BenchmarkProtocolError as error:
        if message not in str(error):
            mismatch = f"unexpected benchmark protocol error: {error}"
            raise AssertionError(mismatch) from error
        return
    failure = "invalid benchmark protocol unexpectedly succeeded"
    raise AssertionError(failure)


def test_protocol_file_rejects_invalid_utf8(tmp_path: Path) -> None:
    """Protocol file encoding failure remains a typed validation error."""
    path = tmp_path / "invalid.benchmark.toml"
    _ = path.write_bytes(bytes((0x5b, 0xff, 0x5d)))
    with pytest.raises(
        validator.BenchmarkProtocolError,
        match="invalid benchmark protocol UTF-8",
    ):
        _ = validator.validate_example(path)


def test_repository_protocol_examples_are_valid_and_retain_raw_data() -> None:
    """Deterministic and stochastic fixtures satisfy the complete protocol."""
    records = validator.validate_repository_examples()
    assert tuple(record.kind for record in records) == (
        "deterministic",
        "stochastic",
    )


def test_protocol_rejects_windows_drive_relative_path() -> None:
    """Drive-relative Windows syntax is not repository-relative authority."""
    text = _text(DETERMINISTIC).replace(
        'path = "benchmarks/research/protocol/examples/deterministic-raw.csv"',
        'path = "D:escape"',
    )
    _expect_failure(text, "must be repository-relative")


def test_comparison_rejects_unequal_workload() -> None:
    """Performance comparison cannot change the workload between variants."""
    text = _text(DETERMINISTIC).replace(
        "equivalent = true",
        "equivalent = false",
    )
    _expect_failure(text, "equivalent_workload = true")


def test_raw_samples_must_be_retained() -> None:
    """Summary-only benchmark records are rejected."""
    text = _text(DETERMINISTIC).replace("retained = true", "retained = false")
    _expect_failure(text, "benchmark.raw.retained must be true")


def test_repetitions_must_support_dispersion_reporting() -> None:
    """One-shot timing cannot satisfy statistical evidence requirements."""
    text = _text(DETERMINISTIC).replace("repetitions = 5", "repetitions = 1")
    _expect_failure(text, "benchmark.measurement.repetitions must be >= 3")


def test_outlier_filter_requires_preregistered_rule() -> None:
    """Filtering samples cannot be introduced after observing benchmark data."""
    text = _text(DETERMINISTIC).replace(
        'outlier_policy = "retain-all"',
        'outlier_policy = "preregistered-filter"',
    )
    _expect_failure(text, "requires an explicit outlier rule")


def test_deterministic_study_cannot_hide_stochastic_trials() -> None:
    """Deterministic records must not carry seeds or failed trial counts."""
    text = _text(DETERMINISTIC).replace("seeds = []", "seeds = [1]")
    _expect_failure(text, "stochastic fields must be zero/empty")


def test_stochastic_study_requires_one_unique_seed_per_trial() -> None:
    """Stochastic comparison fixes replay identity for every trial."""
    text = _text(STOCHASTIC).replace(
        "seeds = [11, 17, 23, 29]",
        "seeds = [11, 17, 23, 23]",
    )
    _expect_failure(text, "one unique seed per trial")


def test_stochastic_failed_trials_are_preserved_in_record() -> None:
    """Failed search trials remain part of the benchmark population."""
    record = validator.parse_protocol(_text(STOCHASTIC))
    assert record.trial_count == STOCHASTIC_TRIALS
    assert record.failed_trials == 1
    assert record.seeds == (11, 17, 23, 29)


def test_protocol_requires_linked_recorded_run_identity() -> None:
    """A performance record cannot point only at an unexecuted plan."""
    text = _text(DETERMINISTIC).replace(
        "benchmarks/research/protocol/examples/deterministic.experiment.toml",
        "src/research/algorithms/domain/algorithms/template/experiment.toml",
    )
    path = DETERMINISTIC.parent / "temporary-invalid-link.benchmark.toml"
    _ = path.write_text(text, encoding="utf-8")
    try:
        _expect_validation_failure(path, "record_kind = run")
    finally:
        _ = path.unlink(missing_ok=True)


def _expect_validation_failure(path: Path, message: str) -> None:
    try:
        _ = validator.validate_example(path)
    except validator.BenchmarkProtocolError as error:
        if message not in str(error):
            mismatch = f"unexpected linked-run error: {error}"
            raise AssertionError(mismatch) from error
        return
    failure = "invalid linked benchmark record unexpectedly succeeded"
    raise AssertionError(failure)
