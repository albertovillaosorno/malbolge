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
#   - Deterministic protocol checks for CUDA crazy-geometry throughput.
# - Must-Not:
#   - Require CUDA hardware or treat benchmark timing as semantic evidence.
# - Allows:
#   - Inputs: benchmark identities, route order, and inherited v1 workload.
#   - Outputs: deterministic comparison-protocol assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when another geometry benchmark gains a distinct protocol.
# - Merge-When:
#   - Merge when another test owns this exact three-route measurement identity.
# - Summary:
#   - Protocol tests for the N10-N14 CUDA crazy-geometry benchmark.
# - Description:
#   - Locks route identity/order and reuse of the reviewed v1 workload.
# - Usage:
#   - Run before collecting any retained geometry throughput evidence.
# - Defaults:
#   - Resource assertions cover declared constant bytes, not occupancy or
#     registers.
#

"""Protocol tests for the N10-N14 CUDA crazy-geometry throughput benchmark."""

from __future__ import annotations

import json
import sys
from typing import cast

import pytest
from accelerator.cuda.resident_kernel import ResidentCrazyGeometry
from accelerator.exact_primitives import AcceleratorCapability

from benchmarks.accelerator import (
    profile_width_crazy_geometry_throughput as geom,
)
from benchmarks.accelerator import profile_width_crazy_throughput as baseline

EXPECTED_BENCHMARK_ID = "cuda-profile-width-crazy-geometry-throughput-v1"
EXPECTED_GEOMETRIES = (
    ResidentCrazyGeometry.TRITWISE,
    ResidentCrazyGeometry.NATIVE,
    ResidentCrazyGeometry.PADDED,
)
EXPECTED_TRITWISE_CONSTANT_BYTES = 188
EXPECTED_LOOKUP_CONSTANT_BYTES = 59_237


def test_geometry_benchmark_reuses_exact_v1_workload_authority() -> None:
    """Geometry comparison cannot fork the reviewed workload or oracle."""
    assert geom.BENCHMARK_ID == EXPECTED_BENCHMARK_ID
    assert geom.BASELINE_BENCHMARK_ID == baseline.BENCHMARK_ID
    assert geom.WORKLOAD_ID == baseline.WORKLOAD_ID
    assert geom.WIDTHS == baseline.WIDTHS
    assert geom.STEP_BUDGET == baseline.STEP_BUDGET
    assert geom.SAMPLE_COUNT == baseline.SAMPLE_COUNT


def test_geometry_route_order_rotates_first_block_without_omissions() -> None:
    """Consecutive widths rotate the first route while retaining all routes."""
    assert geom.CRAZY_GEOMETRIES == EXPECTED_GEOMETRIES
    assert geom.rotated_crazy_geometry_order(0) == EXPECTED_GEOMETRIES
    assert geom.rotated_crazy_geometry_order(1) == (
        EXPECTED_GEOMETRIES[1:] + EXPECTED_GEOMETRIES[:1]
    )
    assert geom.rotated_crazy_geometry_order(2) == (
        EXPECTED_GEOMETRIES[2:] + EXPECTED_GEOMETRIES[:2]
    )
    assert geom.rotated_crazy_geometry_order(3) == EXPECTED_GEOMETRIES


def test_geometry_declared_constant_bytes_separate_lookup_pressure() -> None:
    """Lookup routes report their extra source-declared constant footprint."""
    assert (
        geom.declared_constant_bytes(ResidentCrazyGeometry.TRITWISE)
        == EXPECTED_TRITWISE_CONSTANT_BYTES
    )
    for route in (
        ResidentCrazyGeometry.NATIVE,
        ResidentCrazyGeometry.PADDED,
    ):
        assert geom.declared_constant_bytes(route) == EXPECTED_LOOKUP_CONSTANT_BYTES


def _synthetic_width(
    width_index: int,
    word_trits: int,
) -> tuple[tuple[geom.CrazyGeometryThroughputRow, ...], AcceleratorCapability]:
    """Provide fully shaped benchmark timing rows without invoking CUDA."""
    memory_words = baseline.profile_width_crazy_geometry(word_trits).memory_words
    rows: list[geom.CrazyGeometryThroughputRow] = []
    for route_index, route in enumerate(geom.rotated_crazy_geometry_order(width_index)):
        sample = word_trits * 1000 + route_index * 100
        rows.append(
            geom.CrazyGeometryThroughputRow(
                crazy_geometry=route.value,
                declared_constant_bytes=geom.declared_constant_bytes(route),
                driver_active_blocks_per_multiprocessor_at_launch=6,
                driver_constant_memory_bytes=geom.declared_constant_bytes(route),
                driver_launch_threads_per_block=256,
                driver_local_memory_bytes_per_thread=0,
                driver_max_threads_per_multiprocessor=1536,
                driver_max_threads_per_block=1024,
                driver_registers_per_thread=35,
                driver_static_shared_memory_bytes=0,
                end_to_end_median_ns=sample * 2,
                end_to_end_pstdev_ns=0.0,
                end_to_end_raw_ns=(sample * 2,) * geom.SAMPLE_COUNT,
                end_to_end_vm_steps_per_second=(geom.STEP_BUDGET * 1e9 / (sample * 2)),
                memory_bytes_per_vm=memory_words * geom.WORD_BYTES,
                memory_words=memory_words,
                resident_median_ns=sample,
                resident_pstdev_ns=0.0,
                resident_raw_ns=(sample,) * geom.SAMPLE_COUNT,
                resident_vm_steps_per_second=geom.STEP_BUDGET * 1e9 / sample,
                word_trits=word_trits,
            )
        )
    return tuple(rows), AcceleratorCapability(
        backend_id="cuda-synthetic",
        device_arch="sm-test",
        device_name="synthetic-device",
    )


def _without_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(geom, "_measure_width", _synthetic_width)


@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_throughput_report_cannot_publish_forged_raw_sample_rows(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
) -> None:
    """A replaced public JSON provider cannot rewrite reviewed timings."""
    _without_cuda(monkeypatch)
    forged = '{"benchmark_id":"forged","rows":[],"backend":"cuda"}'

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
            ValueError,
            match="geometry throughput JSON writer differs from source",
        ):
            _ = geom.main()
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("result", (0, False, "done"))
def test_throughput_report_rejects_incomplete_output_receipts(
    monkeypatch: pytest.MonkeyPatch,
    result: object,
) -> None:
    """A short or nonnative write cannot certify sample delivery."""
    _without_cuda(monkeypatch)

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
            ValueError,
            match="geometry throughput stdout write incomplete",
        ):
            _ = geom.main()
    assert not output.flushed


@pytest.mark.parametrize("result", (False, 1, "done"))
def test_throughput_report_rejects_nonvoid_flush_receipts(
    monkeypatch: pytest.MonkeyPatch,
    result: object,
) -> None:
    """A forged flush cannot claim successful retained timing delivery."""
    _without_cuda(monkeypatch)

    class NonvoidFlush:
        def write(self, record: str) -> int:
            return len(record)

        def flush(self) -> object:
            return result

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", NonvoidFlush())
        with pytest.raises(
            ValueError,
            match="geometry throughput stdout flush incomplete",
        ):
            _ = geom.main()


def test_throughput_report_retains_all_sample_and_route_identifiers(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every synthetic N10-N14 route retains 15 original timed samples."""
    _without_cuda(monkeypatch)
    assert geom.main() == 0
    output = capsys.readouterr().out
    assert output.endswith("\n")
    payload = cast("dict[str, object]", json.loads(output))
    rows = cast("list[dict[str, object]]", payload["rows"])
    assert payload["benchmark_id"] == EXPECTED_BENCHMARK_ID
    assert payload["backend"] == "cuda-synthetic"
    assert payload["device"] == {"arch": "sm-test", "name": "synthetic-device"}
    assert len(rows) == len(geom.WIDTHS) * len(geom.CRAZY_GEOMETRIES)
    assert {(row["word_trits"], row["crazy_geometry"]) for row in rows} == {
        (width, route.value) for width in geom.WIDTHS for route in geom.CRAZY_GEOMETRIES
    }
    for row in rows:
        assert len(cast("list[int]", row["resident_raw_ns"])) == geom.SAMPLE_COUNT
        assert len(cast("list[int]", row["end_to_end_raw_ns"])) == geom.SAMPLE_COUNT


@pytest.mark.parametrize("provider", ("writer", "encoder"))
def test_throughput_report_serializer_failure_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
) -> None:
    """JSON provider failures cannot be mistaken for measured timing evidence."""
    _without_cuda(monkeypatch)
    fault = RuntimeError("synthetic report fault")

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
            geom.GeometryThroughputReportError,
            match="geometry throughput JSON writer failed: RuntimeError",
        ) as caught:
            _ = geom.main()
        assert caught.value.__cause__ is fault
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("stage", ("write", "flush"))
def test_throughput_report_stdout_failure_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """The CLI rejects output transport faults after validated timing."""
    _without_cuda(monkeypatch)
    fault = OSError("synthetic output failure")

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
            geom.GeometryThroughputReportError,
            match=f"geometry throughput stdout {stage} failed: OSError",
        ) as caught:
            _ = geom.main()
        assert caught.value.__cause__ is fault
    assert len(output.records) == (0 if stage == "write" else 1)


def test_throughput_report_rejects_foreign_int_write_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Subclassed write lengths do not prove complete timing publication."""
    _without_cuda(monkeypatch)

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
            geom.GeometryThroughputReportError,
            match="geometry throughput stdout write incomplete",
        ):
            _ = geom.main()
    assert not output.flushed


def test_throughput_report_accepts_equivalent_public_encoder(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Functionally equivalent JSON adapters retain sample provenance."""
    _without_cuda(monkeypatch)
    native_encoder = json.JSONEncoder

    class EquivalentEncoder(native_encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        assert geom.main() == 0
        payload = cast("dict[str, object]", json.loads(capsys.readouterr().out))
        rows = cast("list[dict[str, object]]", payload["rows"])
        assert payload["workload_id"] == baseline.WORKLOAD_ID
        assert len(rows) == len(geom.WIDTHS) * len(geom.CRAZY_GEOMETRIES)
