# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Hardware-free CRAZY geometry resource failure-policy regressions.
# - Must-Not:
#   - Require CUDA, allocate device memory, or infer product route selection.
# - Allows:
#   - Inputs: deterministic failure-policy benchmark rows.
#   - Outputs: exact one-byte rejection/admission boundary assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when operational backend fallback gains independent Python evidence.
# - Merge-When:
#   - Merge when another test owns this exact N10-N14 boundary matrix.
# - Summary:
#   - Locks fail-closed resident resource boundaries for CRAZY widths.
# - Description:
#   - Verifies one-byte-below rejection and exact-byte admission for N10-N14.
# - Usage:
#   - Run with mathematics/resource tests on every host.
# - Defaults:
#   - Product fallback semantics remain owned and tested by the Rust VM layer.
#

"""Hardware-free CRAZY geometry resource failure-policy regressions."""

from __future__ import annotations

import json
import sys
from typing import cast

import pytest

from benchmarks.accelerator import (
    profile_width_crazy_geometry_failure_policy as failure,
)
from benchmarks.accelerator import profile_width_crazy_throughput as baseline

EXPECTED_BENCHMARK_ID = "cuda-profile-width-crazy-geometry-failure-policy-v1"
EXPECTED_FIXED_CHUNK_BYTES = 8
EXPECTED_POLICY = "planner-fail-closed-before-allocation"
EXPECTED_PRODUCT_FALLBACK = "optional-backend-unavailable-safe-rust"


def test_failure_policy_reuses_frozen_crazy_width_workload() -> None:
    """Failure evidence cannot fork the reviewed N10-N14 workload identity."""
    assert failure.BENCHMARK_ID == EXPECTED_BENCHMARK_ID
    assert failure.WIDTHS == baseline.WIDTHS
    assert failure.WORKLOAD_ID == baseline.WORKLOAD_ID
    assert failure.FAILURE_POLICY == EXPECTED_POLICY
    assert failure.PRODUCT_FALLBACK_POLICY == EXPECTED_PRODUCT_FALLBACK


def test_each_width_rejects_one_byte_below_exact_required_chunk() -> None:
    """Every N10-N14 state crosses from rejection to admission at one byte."""
    rows = failure.failure_boundaries()
    assert tuple(row.word_trits for row in rows) == baseline.WIDTHS
    for row in rows:
        assert row.planner_fixed_chunk_bytes == EXPECTED_FIXED_CHUNK_BYTES
        assert row.required_chunk_bytes == (
            row.planner_fixed_chunk_bytes + row.planner_item_bytes_per_vm
        )
        assert row.failing_usable_memory_bytes + 1 == row.required_chunk_bytes
        assert row.admitted_usable_memory_bytes == row.required_chunk_bytes
        assert row.admitted_free_memory_bytes == (
            row.failing_free_memory_bytes + 1
        )
        assert row.reserve_bytes == failure.RESERVE_BYTES
        assert (
            f"requires {row.required_chunk_bytes} bytes"
            in row.failure_message
        )
        assert (
            f"only {row.failing_usable_memory_bytes} bytes are budgeted"
            in row.failure_message
        )


@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_failure_policy_json_output_rejects_forged_boundary_rows(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
) -> None:
    """A substituted serializer cannot publish empty N10-N14 evidence."""
    forged = '{"benchmark_id":"forged","rows":[]}'

    class ForgedEncoder:
        def __init__(self, **_options: object) -> None:
            pass

        def encode(self, _document: object) -> str:
            return forged

    def forged_writer(*_args: object, **_kwargs: object) -> str:
        return forged

    with monkeypatch.context() as patch:
        if provider in ("encoder", "joint"):
            patch.setattr(json, "JSONEncoder", ForgedEncoder)
        if provider in ("writer", "joint"):
            patch.setattr(json, "dumps", forged_writer)
        with pytest.raises(
            ValueError, match="failure-policy JSON writer differs from source"
        ):
            _ = failure.main()
        output = capsys.readouterr()
        assert output.out == ""


@pytest.mark.parametrize("fault", (RuntimeError, OverflowError))
def test_failure_policy_json_writer_faults_are_typed(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault: type[Exception],
) -> None:
    """Public writer faults preserve cause and cannot publish a policy."""
    original = fault("untrusted failure")

    def broken_writer(*_args: object, **_kwargs: object) -> str:
        raise original

    with monkeypatch.context() as patch:
        patch.setattr(json, "dumps", broken_writer)
        with pytest.raises(
            ValueError, match="failure-policy JSON writer failed"
        ) as caught:
            _ = failure.main()
        assert caught.value.__cause__ is original
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("result", (False, 0, -1, "none"))
def test_failure_policy_requires_exact_stdout_write_ack(
    monkeypatch: pytest.MonkeyPatch,
    result: object,
) -> None:
    """No success is claimed after partial or nonnative output completion."""
    class ShortWriter:
        def __init__(self) -> None:
            self.records: list[str] = []
            self.flushed: bool = False

        def write(self, record: str) -> object:
            self.records.append(record)
            return result

        def flush(self) -> None:
            self.flushed = True

    output = ShortWriter()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        with pytest.raises(ValueError, match="failure-policy stdout write incomplete"):
            _ = failure.main()
    assert len(output.records) == 1
    assert not output.flushed


@pytest.mark.parametrize("result", (False, 1, "done"))
def test_failure_policy_rejects_nonvoid_stdout_flush(
    monkeypatch: pytest.MonkeyPatch,
    result: object,
) -> None:
    """A forged flush receipt cannot certify complete evidence delivery."""
    class BadFlush:
        def __init__(self) -> None:
            self.records: list[str] = []

        def write(self, record: str) -> int:
            self.records.append(record)
            return len(record)

        def flush(self) -> object:
            return result

    output = BadFlush()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        with pytest.raises(ValueError, match="failure-policy stdout flush incomplete"):
            _ = failure.main()
    assert len(output.records) == 1


def test_failure_policy_normal_stdout_is_exact_canonical_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A complete report carries all expected N10-N14 rows unchanged."""
    assert failure.main() == 0
    report = cast("dict[str, object]", json.loads(capsys.readouterr().out))
    assert report["benchmark_id"] == EXPECTED_BENCHMARK_ID
    rows = cast("list[dict[str, object]]", report["rows"])
    assert tuple(row["word_trits"] for row in rows) == baseline.WIDTHS


@pytest.mark.parametrize("stage", ("write", "flush"))
def test_failure_policy_stdout_host_failures_preserve_cause(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """Failure of either output stage must not certify a resource report."""
    fault = RuntimeError("untrusted output stream")

    class FailingWriter:
        def __init__(self) -> None:
            self.records: list[str] = []

        def write(self, record: str) -> int:
            if stage == "write":
                raise fault
            self.records.append(record)
            return len(record)

        def flush(self) -> None:
            raise fault

    output = FailingWriter()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        with pytest.raises(
            failure.FailurePolicyReportError,
            match=f"failure-policy stdout {stage} failed",
        ) as caught:
            _ = failure.main()
        assert caught.value.__cause__ is fault
    assert len(output.records) == (0 if stage == "write" else 1)


def test_failure_policy_rejects_forged_native_length_subclass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even an integer-like receipt cannot fake native write completion."""
    class ForeignInt(int):
        pass

    class ForgedWrite:
        def __init__(self) -> None:
            self.flushed: bool = False

        def write(self, record: str) -> int:
            return ForeignInt(len(record))

        def flush(self) -> None:
            self.flushed = True

    output = ForgedWrite()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        with pytest.raises(
            failure.FailurePolicyReportError,
            match="failure-policy stdout write incomplete",
        ):
            _ = failure.main()
    assert not output.flushed


def test_failure_policy_accepts_equivalent_public_json_encoder(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Source-equivalent JSON adapters keep N10-N14 evidence unchanged."""
    native_encoder = json.JSONEncoder

    class EquivalentEncoder(native_encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        assert failure.main() == 0
        document = cast("dict[str, object]", json.loads(capsys.readouterr().out))
        assert document["benchmark_id"] == EXPECTED_BENCHMARK_ID
