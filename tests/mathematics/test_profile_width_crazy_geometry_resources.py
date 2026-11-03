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
#   - Protocol checks for CRAZY geometry resident-resource diagnostics.
# - Must-Not:
#   - Require CUDA hardware or infer performance from resource accounting.
# - Allows:
#   - Inputs: diagnostic constants and frozen crazy-width workload authority.
#   - Outputs: stable identity and exact footprint-formula assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when another resource protocol gains independent identity.
# - Merge-When:
#   - Merge when another test owns this exact resource diagnostic protocol.
# - Summary:
#   - Protocol regression for CRAZY geometry VRAM and transfer accounting.
# - Description:
#   - Locks workload reuse and the 100,000-request planning horizon.
# - Usage:
#   - Run under mathematics validation without CUDA hardware.
# - Defaults:
#   - Geometry arithmetic must not change per-VM state shape.
#

"""Protocol checks for CRAZY geometry resident-resource diagnostics."""

from __future__ import annotations

import json
import sys
from typing import cast

import pytest
from accelerator.classic_run import STATE_WORDS
from accelerator.cuda.profile_run import cuda_profile_resident_footprint

from benchmarks.accelerator import profile_width_crazy_geometry_resources as res
from benchmarks.accelerator import (
    profile_width_crazy_geometry_throughput as geom,
)
from benchmarks.accelerator import profile_width_crazy_throughput as baseline

EXPECTED_BENCHMARK_ID = "cuda-profile-width-crazy-geometry-resources-v1"
EXPECTED_PLANNING_REQUESTS = 100_000


def test_geometry_resource_diagnostic_reuses_frozen_workload() -> None:
    """Resource evidence cannot silently fork widths, routes, or workload."""
    assert res.BENCHMARK_ID == EXPECTED_BENCHMARK_ID
    assert res.PLANNING_REQUESTS == EXPECTED_PLANNING_REQUESTS
    assert res.WIDTHS == geom.WIDTHS == baseline.WIDTHS
    assert res.CRAZY_GEOMETRIES == geom.CRAZY_GEOMETRIES
    assert res.WORKLOAD_ID == geom.WORKLOAD_ID == baseline.WORKLOAD_ID


def test_geometry_resource_expected_one_vm_bytes_are_route_independent() -> None:
    """Arithmetic route cannot alter one request's semantic resident shape."""
    for word_trits in res.WIDTHS:
        geometry = baseline.profile_width_crazy_geometry(word_trits)
        state_bytes = STATE_WORDS * baseline.WORD_BYTES
        memory_bytes = geometry.memory_words * baseline.WORD_BYTES
        input_buffer_bytes = baseline.WORD_BYTES
        output_buffer_bytes = baseline.STEP_BUDGET * baseline.WORD_BYTES
        allocated = (
            state_bytes + memory_bytes + input_buffer_bytes + output_buffer_bytes
        )
        planner_item = allocated - input_buffer_bytes
        assert planner_item > memory_bytes
        assert allocated == planner_item + baseline.WORD_BYTES


def test_cuda_profile_resident_footprint_matches_exact_buffer_layout() -> None:
    """Public accounting matches the four one-request CUDA allocations."""
    for word_trits in res.WIDTHS:
        geometry = baseline.profile_width_crazy_geometry(word_trits)
        request = baseline.profile_width_crazy_request(word_trits)
        footprint = cuda_profile_resident_footprint(geometry, request)
        assert footprint.state_bytes == STATE_WORDS * baseline.WORD_BYTES
        assert footprint.memory_bytes == (geometry.memory_words * baseline.WORD_BYTES)
        assert footprint.input_buffer_bytes == baseline.WORD_BYTES
        assert footprint.output_buffer_bytes == (
            baseline.STEP_BUDGET * baseline.WORD_BYTES
        )
        assert footprint.device_allocated_bytes == (
            footprint.state_bytes
            + footprint.memory_bytes
            + footprint.input_buffer_bytes
            + footprint.output_buffer_bytes
        )
        assert footprint.initial_host_to_device_bytes == (
            footprint.device_allocated_bytes
        )
        assert footprint.planner_item_bytes == (
            footprint.device_allocated_bytes - footprint.input_buffer_bytes
        )
        assert footprint.planner_fixed_chunk_bytes == 2 * baseline.WORD_BYTES


def _synthetic_cuda_width(
    word_trits: int,
) -> tuple[tuple[res.CrazyGeometryResourceRow, ...], dict[str, str]]:
    """Construct full diagnostic rows without requiring a CUDA device."""
    geometry = baseline.profile_width_crazy_geometry(word_trits)
    request = baseline.profile_width_crazy_request(word_trits)
    footprint = cuda_profile_resident_footprint(geometry, request)
    chunk_bytes = footprint.planner_item_bytes + footprint.planner_fixed_chunk_bytes
    rows = tuple(
        res.CrazyGeometryResourceRow(
            crazy_geometry=route.value,
            device_allocated_bytes_per_vm=footprint.device_allocated_bytes,
            first_chunk_bytes=chunk_bytes,
            first_chunk_items=1,
            free_memory_bytes=chunk_bytes + 1024,
            initial_host_to_device_bytes_per_vm=(
                footprint.initial_host_to_device_bytes
            ),
            input_buffer_bytes_per_vm=footprint.input_buffer_bytes,
            memory_bytes_per_vm=footprint.memory_bytes,
            output_buffer_bytes_per_vm=footprint.output_buffer_bytes,
            planner_fixed_chunk_bytes=footprint.planner_fixed_chunk_bytes,
            planner_item_bytes_per_vm=footprint.planner_item_bytes,
            planning_requested_items=res.PLANNING_REQUESTS,
            reserve_bytes=0,
            state_bytes_per_vm=footprint.state_bytes,
            total_chunks=res.PLANNING_REQUESTS,
            total_memory_bytes=chunk_bytes + 1024,
            usable_memory_bytes=chunk_bytes + 1024,
            word_trits=word_trits,
        )
        for route in res.CRAZY_GEOMETRIES
    )
    return rows, {"arch": "test-arch", "name": "synthetic-device"}


def _without_cuda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(res, "_measure_width", _synthetic_cuda_width)


@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_resource_json_report_rejects_forged_geometry_rows(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
) -> None:
    """Modified JSON providers cannot publish unrelated device measurements."""
    _without_cuda(monkeypatch)
    forged = '{"benchmark_id":"forged","rows":[],"device":null}'

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
            ValueError,
            match="geometry resource JSON writer differs from source",
        ):
            _ = res.main()
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("result", (0, False, "done"))
def test_resource_report_rejects_incomplete_write_receipts(
    monkeypatch: pytest.MonkeyPatch,
    result: object,
) -> None:
    """No successful report after a short or non-native stdout receipt."""
    _without_cuda(monkeypatch)

    class PartialOutput:
        def __init__(self) -> None:
            self.flushed: bool = False

        def write(self, _text: str) -> object:
            return result

        def flush(self) -> None:
            self.flushed = True

    output = PartialOutput()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        with pytest.raises(
            ValueError,
            match="geometry resource stdout write incomplete",
        ):
            _ = res.main()
    assert not output.flushed


@pytest.mark.parametrize("result", (False, 1, "done"))
def test_resource_report_rejects_nonvoid_flush_receipts(
    monkeypatch: pytest.MonkeyPatch,
    result: object,
) -> None:
    """An output flush must return the expected native success receipt."""
    _without_cuda(monkeypatch)

    class BadFlush:
        def write(self, text: str) -> int:
            return len(text)

        def flush(self) -> object:
            return result

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", BadFlush())
        with pytest.raises(
            ValueError,
            match="geometry resource stdout flush incomplete",
        ):
            _ = res.main()


def test_resource_report_normal_stdout_keeps_all_width_and_route_rows(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Synthetic device evidence includes every frozen width and route."""
    _without_cuda(monkeypatch)
    assert res.main() == 0
    output = capsys.readouterr().out
    assert output.endswith("\n")
    report = cast("dict[str, object]", json.loads(output))
    rows = cast("list[dict[str, object]]", report["rows"])
    assert report["benchmark_id"] == EXPECTED_BENCHMARK_ID
    assert report["device"] == {"arch": "test-arch", "name": "synthetic-device"}
    assert report["widths"] == list(res.WIDTHS)
    assert len(rows) == len(res.WIDTHS) * len(res.CRAZY_GEOMETRIES)
    assert {(row["word_trits"], row["crazy_geometry"]) for row in rows} == {
        (width, route.value) for width in res.WIDTHS for route in res.CRAZY_GEOMETRIES
    }


@pytest.mark.parametrize("provider", ("writer", "encoder"))
def test_resource_report_serializer_fault_keeps_original_cause(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
) -> None:
    """A failed JSON provider does not publish partial resource evidence."""
    _without_cuda(monkeypatch)
    fault = RuntimeError("synthetic serializer fault")

    class FailingEncoder:
        def __init__(self, **_options: object) -> None:
            pass

        def encode(self, _document: object) -> str:
            raise fault

    def failing_writer(*_args: object, **_kwargs: object) -> str:
        raise fault

    with monkeypatch.context() as patch:
        if provider == "writer":
            patch.setattr(json, "dumps", failing_writer)
        else:
            patch.setattr(json, "JSONEncoder", FailingEncoder)
        with pytest.raises(
            res.GeometryResourceReportError,
            match="geometry resource JSON writer failed: RuntimeError",
        ) as caught:
            _ = res.main()
        assert caught.value.__cause__ is fault
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("stage", ("write", "flush"))
def test_resource_report_stdout_fault_keeps_original_cause(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """Failed delivery cannot return a successful resource measurement."""
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
            res.GeometryResourceReportError,
            match=f"geometry resource stdout {stage} failed: OSError",
        ) as caught:
            _ = res.main()
        assert caught.value.__cause__ is fault
    assert len(output.records) == (0 if stage == "write" else 1)


def test_resource_report_rejects_foreign_int_write_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Integer-like but nonnative length values cannot acknowledge delivery."""
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
            res.GeometryResourceReportError,
            match="geometry resource stdout write incomplete",
        ):
            _ = res.main()
    assert not output.flushed


def test_resource_report_accepts_equivalent_public_json_encoder(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Equivalent public JSON implementations preserve exact diagnostics."""
    _without_cuda(monkeypatch)
    source_encoder = json.JSONEncoder

    class EquivalentEncoder(source_encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        assert res.main() == 0
        report = cast("dict[str, object]", json.loads(capsys.readouterr().out))
        rows = cast("list[dict[str, object]]", report["rows"])
        assert report["workload_id"] == res.WORKLOAD_ID
        assert len(rows) == len(res.WIDTHS) * len(res.CRAZY_GEOMETRIES)
