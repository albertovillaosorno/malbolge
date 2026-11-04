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
#   - Deterministic protocol checks for crazy lookup address fanout evidence.
# - Must-Not:
#   - Require CUDA hardware or reinterpret fanout as physical cache counters.
# - Allows:
#   - Inputs: canonical full-domain and exact projected search workloads.
#   - Outputs: exact route, histogram, and serialization-pressure assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when another memory-space diagnostic gains a distinct protocol.
# - Merge-When:
#   - Merge when another test owns these exact fanout distributions.
# - Summary:
#   - Protocol regressions for CUDA crazy lookup address fanout.
# - Description:
#   - Locks canonical search order and exact unique-address counts by warp.
# - Usage:
#   - Run before using fanout as structural lookup/cache evidence.
# - Defaults:
#   - Fanout is deterministic address evidence, never cache hit-rate evidence.
#

"""Protocol tests for canonical crazy lookup constant-memory address fanout."""

from __future__ import annotations

import json
import sys
from typing import cast

import pytest

from benchmarks.accelerator import crazy_lookup_address_fanout as fanout

EXPECTED_BENCHMARK_ID = "cuda-crazy-lookup-address-fanout-v1"
EXPECTED_CHUNK_VALUES = 243
EXPECTED_WARP_SIZE = 32
CACHE_SCOPE_TEXT = "not cache hit/miss data"
EXPECTED_ROWS = {
    (fanout.ORDINARY_ROUTE, "low"): {
        "candidate_count": 59_049,
        "histogram": ((9, 1), (32, 1_845)),
        "total": 59_049,
        "warps": 1_846,
    },
    (fanout.ORDINARY_ROUTE, "middle"): {
        "candidate_count": 59_049,
        "histogram": ((1, 1_611), (2, 235)),
        "total": 2_081,
        "warps": 1_846,
    },
    (fanout.PREPARED_ROUTE, "low"): {
        "candidate_count": 1_024,
        "histogram": ((32, 32),),
        "total": 1_024,
        "warps": 32,
    },
    (fanout.PREPARED_ROUTE, "middle"): {
        "candidate_count": 1_024,
        "histogram": ((1, 32),),
        "total": 32,
        "warps": 32,
    },
}


def test_fanout_identity_uses_reviewed_cuda_and_crazy_geometry() -> None:
    """Bind the diagnostic to current warp and five-trit table geometry."""
    assert fanout.BENCHMARK_ID == EXPECTED_BENCHMARK_ID
    assert fanout.CRAZY_CHUNK_VALUES == EXPECTED_CHUNK_VALUES
    assert fanout.WARP_SIZE == EXPECTED_WARP_SIZE
    assert CACHE_SCOPE_TEXT in fanout.INTERPRETATION


def test_canonical_search_routes_have_exact_address_fanout() -> None:
    """Ordinary and exact projection preserve their known warp distributions."""
    rows = fanout.crazy_lookup_address_fanout()
    assert len(rows) == len(EXPECTED_ROWS)
    for row in rows:
        expected = EXPECTED_ROWS[row.route_id, row.lookup_chunk]
        histogram = tuple(
            (item.unique_addresses, item.warp_count) for item in row.histogram
        )
        assert row.candidate_count == expected["candidate_count"]
        assert histogram == expected["histogram"]
        assert row.total_unique_address_requests == expected["total"]
        assert row.warp_count == expected["warps"]


def test_raw_fanout_and_histograms_have_exact_accounting() -> None:
    """Summary counts cannot drift away from retained per-warp cardinalities."""
    for row in fanout.crazy_lookup_address_fanout():
        assert len(row.raw_unique_addresses_per_warp) == row.warp_count
        assert sum(row.raw_unique_addresses_per_warp) == (
            row.total_unique_address_requests
        )
        assert min(row.raw_unique_addresses_per_warp) == row.min_unique_addresses
        assert max(row.raw_unique_addresses_per_warp) == row.max_unique_addresses
        assert sum(item.warp_count for item in row.histogram) == row.warp_count


@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_fanout_report_rejects_forged_histogram_and_route_rows(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
) -> None:
    """Public JSON replacements cannot forge structural lookup fanout."""
    forged = '{"benchmark_id":"forged","rows":[],"warp_size":1}'

    class ForgedEncoder:
        def __init__(self, **_options: object) -> None:
            pass

        def encode(self, _payload: object) -> str:
            return forged

    def forged_writer(*_args: object, **_kwargs: object) -> str:
        return forged

    with monkeypatch.context() as patch:
        if provider in ("encoder", "joint"):
            patch.setattr(json, "JSONEncoder", ForgedEncoder)
        if provider in ("writer", "joint"):
            patch.setattr(json, "dumps", forged_writer)
        with pytest.raises(
            ValueError, match="crazy lookup fanout JSON writer differs from source"
        ):
            _ = fanout.main()
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("result", (0, False, "done"))
def test_fanout_report_rejects_nonexact_stdout_write(
    monkeypatch: pytest.MonkeyPatch,
    result: object,
) -> None:
    """Short and nonnative stdout acknowledgements cannot succeed."""

    class PartialOutput:
        def __init__(self) -> None:
            self.flushed: bool = False

        def write(self, _record: str) -> object:
            return result

        def flush(self) -> None:
            self.flushed = True

    output = PartialOutput()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        with pytest.raises(
            ValueError, match="crazy lookup fanout stdout write incomplete"
        ):
            _ = fanout.main()
    assert not output.flushed


@pytest.mark.parametrize("result", (False, 1, "done"))
def test_fanout_report_rejects_foreign_flush_receipt(
    monkeypatch: pytest.MonkeyPatch,
    result: object,
) -> None:
    """Foreign flush receipts cannot certify fanout evidence delivery."""

    class BadFlush:
        def write(self, record: str) -> int:
            return len(record)

        def flush(self) -> object:
            return result

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", BadFlush())
        with pytest.raises(
            ValueError, match="crazy lookup fanout stdout flush incomplete"
        ):
            _ = fanout.main()


def test_fanout_report_retains_exact_address_histogram_and_warp_matrix(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Canonical output retains four exact routes and 3756 warp counts."""
    assert fanout.main() == 0
    output = capsys.readouterr().out
    assert output.endswith("\n")
    payload = cast("dict[str, object]", json.loads(output))
    rows = cast("list[dict[str, object]]", payload["rows"])
    assert payload["benchmark_id"] == EXPECTED_BENCHMARK_ID
    assert payload["warp_size"] == EXPECTED_WARP_SIZE
    assert payload["workload_id"] == fanout.WORKLOAD_ID
    assert len(rows) == len(EXPECTED_ROWS)
    assert {(row["route_id"], row["lookup_chunk"]) for row in rows} == set(
        EXPECTED_ROWS
    )
    assert sum(cast("int", row["warp_count"]) for row in rows) == 3756
    for row in rows:
        raw = cast("list[int]", row["raw_unique_addresses_per_warp"])
        assert len(raw) == row["warp_count"]


@pytest.mark.parametrize("provider", ("writer", "encoder"))
def test_fanout_report_json_fault_preserves_original_cause(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
) -> None:
    """A failed serializer cannot publish an unverified lookup histogram."""
    fault = RuntimeError("synthetic serializer failure")

    class FailingEncoder:
        def __init__(self, **_options: object) -> None:
            pass

        def encode(self, _payload: object) -> str:
            raise fault

    def failing_writer(*_args: object, **_kwargs: object) -> str:
        raise fault

    with monkeypatch.context() as patch:
        if provider == "writer":
            patch.setattr(json, "dumps", failing_writer)
        else:
            patch.setattr(json, "JSONEncoder", FailingEncoder)
        with pytest.raises(
            fanout.CrazyLookupFanoutReportError,
            match="crazy lookup fanout JSON writer failed: RuntimeError",
        ) as caught:
            _ = fanout.main()
        assert caught.value.__cause__ is fault
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("stage", ("write", "flush"))
def test_fanout_report_stdout_fault_preserves_original_cause(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """Host output failures cannot be treated as complete fanout delivery."""
    fault = OSError("synthetic stdout failure")

    class FailingOutput:
        def __init__(self) -> None:
            self.records: list[str] = []

        def write(self, text: str) -> int:
            if stage == "write":
                raise fault
            self.records.append(text)
            return len(text)

        def flush(self) -> None:
            raise fault

    output = FailingOutput()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        with pytest.raises(
            fanout.CrazyLookupFanoutReportError,
            match=f"crazy lookup fanout stdout {stage} failed: OSError",
        ) as caught:
            _ = fanout.main()
        assert caught.value.__cause__ is fault
    assert len(output.records) == (0 if stage == "write" else 1)


def test_fanout_report_rejects_subclassed_integer_write_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A subclassed integer does not prove complete output delivery."""

    class ForeignInt(int):
        pass

    class ForgedOutput:
        def __init__(self) -> None:
            self.flushed: bool = False

        def write(self, text: str) -> int:
            return ForeignInt(len(text))

        def flush(self) -> None:
            self.flushed = True

    output = ForgedOutput()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        with pytest.raises(
            fanout.CrazyLookupFanoutReportError,
            match="crazy lookup fanout stdout write incomplete",
        ):
            _ = fanout.main()
    assert not output.flushed


def test_fanout_report_accepts_equivalent_public_encoder(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Equivalent JSON encoding leaves exact structural records unchanged."""
    native_encoder = json.JSONEncoder

    class EquivalentEncoder(native_encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        assert fanout.main() == 0
        payload = cast("dict[str, object]", json.loads(capsys.readouterr().out))
        assert payload["benchmark_id"] == EXPECTED_BENCHMARK_ID
        assert len(cast("list[object]", payload["rows"])) == len(EXPECTED_ROWS)
