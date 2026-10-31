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

import os
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Never, cast

if TYPE_CHECKING:
    from collections.abc import Callable

import pytest

from scripts.validate import benchmark_protocol as validator

ROOT = Path(__file__).resolve().parents[1]
STOCHASTIC_TRIALS = 4
SWAP_PROTOCOL = "protocol"
SWAP_RUN = "run"
SWAP_FIFO = "fifo"
SWAP_LINK = "symlink"
SWAP_REGULAR = "regular"
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


class _DeniedExamplesRoot:
    @staticmethod
    def iterdir() -> Never:
        message = "injected benchmark examples scan failure"
        raise PermissionError(message)


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


def test_benchmark_decimal_digit_limit_fails_typed() -> None:
    """Host TOML integer limits must not escape as raw ValueErrors."""
    limit = sys.get_int_max_str_digits()
    if limit == 0 or limit > 20_000:
        pytest.skip("host decimal token limit unavailable")
    text = _text(DETERMINISTIC).replace(
        "repetitions = 5", "repetitions = " + "9" * (limit + 1)
    )
    _expect_failure(text, "invalid TOML exceeds host parser capacity")


def test_protocol_file_rejects_invalid_utf8(tmp_path: Path) -> None:
    """Protocol file encoding failure remains a typed validation error."""
    path = tmp_path / "invalid.benchmark.toml"
    _ = path.write_bytes(bytes((0x5B, 0xFF, 0x5D)))
    with pytest.raises(
        validator.BenchmarkProtocolError,
        match="invalid benchmark protocol UTF-8",
    ):
        _ = validator.validate_example(path)


def test_repository_example_scan_errors_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An inaccessible checked-in example directory cannot look empty."""
    denied = cast("Path", cast("object", _DeniedExamplesRoot()))
    monkeypatch.setattr(validator, "EXAMPLES_ROOT", denied)
    with pytest.raises(PermissionError, match="injected benchmark examples"):
        _ = validator.validate_repository_examples()


def test_protocol_status_errors_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An inaccessible protocol file cannot be misclassified as missing."""
    original_lstat = Path.lstat

    def fail_protocol_status(path: Path) -> object:
        if path == STOCHASTIC:
            message = "injected benchmark protocol status failure"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_protocol_status)
    with pytest.raises(
        validator.BenchmarkProtocolError,
        match="benchmark protocol example status failed",
    ):
        _ = validator.validate_example(STOCHASTIC)


def test_redirected_protocol_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A redirected protocol path cannot provide checked-in evidence."""
    original_is_junction = Path.is_junction

    def report_junction(path: Path) -> bool:
        if path == STOCHASTIC:
            return True
        return original_is_junction(path)

    monkeypatch.setattr(Path, "is_junction", report_junction)
    with pytest.raises(
        validator.BenchmarkProtocolError,
        match="benchmark protocol example must not redirect",
    ):
        _ = validator.validate_example(STOCHASTIC)


def _swap_admitted_benchmark_path(
    victim: Path,
    shadow: Path,
    replacement: str,
) -> None:
    """Inject one invalid regular, linked or FIFO source after admission."""
    _ = victim.unlink()
    if replacement == SWAP_LINK:
        _ = victim.symlink_to(shadow)
    elif replacement == SWAP_REGULAR:
        _ = shadow.replace(victim)
    else:
        mkfifo = cast("Callable[[Path], None]", getattr(os, "mkfifo", None))
        mkfifo(victim)


@pytest.mark.parametrize("swapped", [SWAP_PROTOCOL, SWAP_RUN])
@pytest.mark.parametrize("replacement", [SWAP_LINK, SWAP_REGULAR, SWAP_FIFO])
def test_benchmark_rejects_file_swapped_after_admission(
    swapped: str,
    replacement: str,
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A post-status replacement cannot substitute checked benchmark input."""
    if replacement == SWAP_FIFO and not hasattr(os, "mkfifo"):
        pytest.skip("FIFO regression requires os.mkfifo")
    fixture_dir, protocol, run = _isolated_benchmark_fixture(tmp_path, monkeypatch)
    victim = protocol if swapped == SWAP_PROTOCOL else run
    shadow = fixture_dir / "shadow.toml"
    _ = shutil.copyfile(victim, shadow)
    original_lstat = Path.lstat
    changed = False

    def redirect_after_status(path: Path) -> os.stat_result:
        nonlocal changed
        status = original_lstat(path)
        if path == victim and not changed:
            _swap_admitted_benchmark_path(victim, shadow, replacement)
            changed = True
        return status

    monkeypatch.setattr(Path, "lstat", redirect_after_status)
    with pytest.raises(
        validator.BenchmarkProtocolError, match=r"read failed|redirect|changed"
    ):
        _ = validator.validate_example(protocol)
    assert changed


def _isolated_benchmark_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, Path]:
    """Clone one complete benchmark fixture under an independent root.

    Returns:
        Fixture directory, benchmark protocol, and linked run paths.

    """
    fixture_dir = tmp_path / "benchmarks/research/protocol/examples"
    fixture_dir.mkdir(parents=True)
    for name in (
        "deterministic.benchmark.toml",
        "deterministic.experiment.toml",
        "deterministic-raw.csv",
    ):
        _ = shutil.copyfile(DETERMINISTIC.parent / name, fixture_dir / name)
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    return (
        fixture_dir,
        fixture_dir / "deterministic.benchmark.toml",
        fixture_dir / "deterministic.experiment.toml",
    )


@pytest.mark.parametrize("linked", ["protocol", "run", "raw"])
def test_benchmark_rejects_linked_parent_evidence(
    linked: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid manifest or raw CSV via an alias parent is not evidence."""
    fixture_dir, protocol, run = _isolated_benchmark_fixture(tmp_path, monkeypatch)
    if linked == SWAP_PROTOCOL:
        payload = tmp_path / "source-directory"
        _ = fixture_dir.rename(payload)
        _ = fixture_dir.symlink_to(payload, target_is_directory=True)
    else:
        alias = tmp_path / "untrusted-parent"
        _ = alias.symlink_to(fixture_dir, target_is_directory=True)
        if linked == SWAP_RUN:
            text = protocol.read_text(encoding="utf-8").replace(
                "benchmarks/research/protocol/examples/deterministic.experiment.toml",
                "untrusted-parent/deterministic.experiment.toml",
            )
            _ = protocol.write_text(text, encoding="utf-8")
        else:
            original = "benchmarks/research/protocol/examples/deterministic-raw.csv"
            changed = "untrusted-parent/deterministic-raw.csv"
            _ = protocol.write_text(
                protocol.read_text(encoding="utf-8").replace(original, changed),
                encoding="utf-8",
            )
            _ = run.write_text(
                run.read_text(encoding="utf-8").replace(original, changed),
                encoding="utf-8",
            )
    with pytest.raises(validator.BenchmarkProtocolError, match=r"redirect|linked"):
        _ = validator.validate_example(protocol)


@pytest.mark.parametrize("swapped", ["protocol", "run"])
def test_benchmark_rejects_linked_parent_swapped_during_read(
    swapped: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Moving a folder behind an alias must not retain trusted file bytes."""
    fixture_dir, protocol, _ = _isolated_benchmark_fixture(tmp_path, monkeypatch)
    original_read = os.read
    reads = 0
    changed = False

    def swap_parent_on_read(descriptor: int, length: int) -> bytes:
        nonlocal reads, changed
        read = original_read(descriptor, length)
        reads += 1
        target = 1 if swapped == SWAP_PROTOCOL else 2
        if reads == target and not changed:
            payload = tmp_path / "source-directory"
            _ = fixture_dir.rename(payload)
            _ = fixture_dir.symlink_to(payload, target_is_directory=True)
            changed = True
        return read

    monkeypatch.setattr(os, "read", swap_parent_on_read)
    with pytest.raises(validator.BenchmarkProtocolError, match=r"redirect|linked"):
        _ = validator.validate_example(protocol)
    assert changed


def test_benchmark_reader_rejects_in_place_change_during_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The exact admitted contents must survive all read chunks."""
    _, protocol, _ = _isolated_benchmark_fixture(tmp_path, monkeypatch)
    source = (
        protocol.read_bytes() + b"\n#" + b"x" * (validator.FILE_READ_CHUNK_BYTES + 3)
    )
    _ = protocol.write_bytes(source)
    original_read = os.read
    changed = False

    def mutate_after_first_chunk(fd: int, length: int) -> bytes:
        nonlocal changed
        chunk = original_read(fd, length)
        if not changed:
            _ = protocol.write_bytes(b"#" + b"y" * (len(source) - 1))
            changed = True
        return chunk

    monkeypatch.setattr(os, "read", mutate_after_first_chunk)
    with pytest.raises(validator.BenchmarkProtocolError, match="changed"):
        _ = validator.validate_example(protocol)
    assert changed


def test_benchmark_reader_bounds_text_and_reads_in_chunks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Large evidence fails before read; multi-chunk valid TOML completes."""
    _, protocol, _ = _isolated_benchmark_fixture(tmp_path, monkeypatch)
    contents = (
        protocol.read_text(encoding="utf-8")
        + "\n#"
        + "x" * (validator.FILE_READ_CHUNK_BYTES + 17)
    )
    _ = protocol.write_text(contents, encoding="utf-8")
    record = validator.validate_example(protocol)
    assert record.kind == validator.DETERMINISTIC_KIND

    _ = protocol.write_bytes(b"x" * (validator.MAX_PROTOCOL_BYTES + 1))
    with pytest.raises(validator.BenchmarkProtocolError, match="admission limit"):
        _ = validator.validate_example(protocol)


def test_repository_protocol_examples_are_valid_and_retain_raw_data() -> None:
    """Deterministic and stochastic fixtures satisfy the complete protocol."""
    records = validator.validate_repository_examples()
    assert tuple(record.kind for record in records) == (
        "deterministic",
        "stochastic",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("experiment_manifest", "deterministic.experiment.toml"),
        ("path", "deterministic-raw.csv"),
    ),
)
def test_benchmark_evidence_paths_reject_escaped_nul(field: str, value: str) -> None:
    """TOML NUL escapes cannot reach host path APIs as raw ValueErrors."""
    text = _text(DETERMINISTIC).replace(
        f'{field} = "benchmarks/research/protocol/examples/{value}"',
        f'{field} = "benchmarks/\\u0000invalid"',
    )
    _expect_failure(text, "must not contain NUL")


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
