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
#   - Hardware-free classic CUDA throughput and phase report publication tests.
# - Must-Not:
#   - Execute CUDA hardware or infer VM correctness from benchmark timings.
# - Allows:
#   - Inputs: synthetic device resources, timings, and phase samples.
#   - Outputs: exact retained-report and transport-failure assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when a different performance workload needs its own evidence.
# - Merge-When:
#   - Merge when the classic benchmark owns these exact reporting contracts.
# - Summary:
#   - Source-bound JSON and stdout evidence for classic CUDA benchmarking.
# - Description:
#   - Locks raw/median timing and host-output boundaries without CUDA.
# - Usage:
#   - Run as part of mathematics regression validation.
# - Defaults:
#   - Native JSON agreement, exact write length, and void flush are required.
#

"""Hardware-free classic CUDA retained throughput/phase reporting tests."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Self, cast

import pytest
from accelerator.cuda.classic_run import ClassicRunPhaseProfile
from accelerator.exact_primitives import AcceleratorCapability

from benchmarks.accelerator import classic_run_phase_profile as phase
from benchmarks.accelerator import classic_run_throughput as throughput
from benchmarks.accelerator import classic_workload as workload

KIND_NAMES = ("throughput", "phase")


@dataclass(frozen=True, slots=True)
class _SyntheticResources:
    free_memory_bytes: int = 15_000_000_000
    max_threads_per_block: int = 1024
    multiprocessor_count: int = 30
    total_memory_bytes: int = 16_000_000_000


@dataclass(frozen=True, slots=True)
class _SyntheticPlan:
    resources: _SyntheticResources = _SyntheticResources()


def _synthetic_classic_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Publish both benchmark reports using no-CUDA synthetic observations."""

    class SyntheticAdapter:
        def __init__(self) -> None:
            pass

        def __enter__(self) -> Self:
            return self

        def __exit__(self, _type: object, _error: object, _trace: object) -> None:
            pass

        def capability(self) -> AcceleratorCapability:
            return AcceleratorCapability(
                backend_id="cuda-synthetic",
                device_arch="sm-test",
                device_name="synthetic-device",
            )

        def plan(self, _requests: object) -> _SyntheticPlan:
            return _SyntheticPlan()

    def synthetic_request() -> object:
        return object()

    def synthetic_timing(
        _adapter: object, _request: object, batch_size: int
    ) -> throughput.ThroughputRow:
        sample = batch_size * 1000
        return throughput.ThroughputRow(
            batch_size=batch_size,
            items_per_second_at_median=batch_size * 1_000_000_000 / sample,
            median_ns=sample,
            ns_per_item_at_median=sample / batch_size,
            pstdev_ns=0.0,
            raw_ns=(sample,) * throughput.SAMPLE_COUNT,
            step_budget=workload.STEP_BUDGET,
        )

    def synthetic_phase(
        _adapter: object, _request: object, batch_size: int
    ) -> tuple[phase.PhaseSummary, tuple[ClassicRunPhaseProfile, ...]]:
        sample = batch_size * 1000
        summary = phase.PhaseSummary(
            allocate_ns=sample,
            batch_size=batch_size,
            decode_ns=sample,
            download_ns=sample,
            host_build_ns=sample,
            kernel_ns=sample,
            release_ns=sample,
            total_ns=sample * 8,
            upload_ns=sample,
            validation_plan_ns=sample,
        )
        observation = ClassicRunPhaseProfile(
            allocate_ns=sample,
            chunks=1,
            decode_ns=sample,
            download_ns=sample,
            host_build_ns=sample,
            kernel_ns=sample,
            release_ns=sample,
            total_ns=sample * 8,
            upload_ns=sample,
            validation_plan_ns=sample,
        )
        return summary, (observation,) * phase.SAMPLE_COUNT

    monkeypatch.setattr(throughput, "CudaClassicRunAdapter", SyntheticAdapter)
    monkeypatch.setattr(phase, "CudaClassicRunAdapter", SyntheticAdapter)
    monkeypatch.setattr(throughput, "classic_noop_request", synthetic_request)
    monkeypatch.setattr(phase, "classic_noop_request", synthetic_request)
    monkeypatch.setattr(throughput, "_measure", synthetic_timing)
    monkeypatch.setattr(phase, "_measure", synthetic_phase)


def _run(kind: str) -> int:
    return throughput.main() if kind == "throughput" else phase.main()


@pytest.mark.parametrize("kind", KIND_NAMES)
@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_classic_report_rejects_forged_device_and_timing_rows(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    provider: str,
) -> None:
    """Neither classic report can publish substitute raw samples."""
    _synthetic_classic_run(monkeypatch)
    forged = '{"backend":"forged","device":null,"rows":[]}'

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
            ValueError, match="classic .* JSON writer differs from source"
        ):
            _ = _run(kind)
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("kind", KIND_NAMES)
@pytest.mark.parametrize("result", (0, False, "done"))
def test_classic_report_rejects_nonexact_stdout_write(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    result: object,
) -> None:
    """No successful retained JSON after a short or nonnative write."""
    _synthetic_classic_run(monkeypatch)

    class ShortOutput:
        def __init__(self) -> None:
            self.flushed: bool = False

        def write(self, _record: str) -> object:
            return result

        def flush(self) -> None:
            self.flushed = True

    output = ShortOutput()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        with pytest.raises(ValueError, match="classic .* stdout write incomplete"):
            _ = _run(kind)
    assert not output.flushed


@pytest.mark.parametrize("kind", KIND_NAMES)
@pytest.mark.parametrize("result", (False, 1, "done"))
def test_classic_report_rejects_nonvoid_stdout_flush(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    result: object,
) -> None:
    """A forged flush receipt cannot certify retained timing evidence."""
    _synthetic_classic_run(monkeypatch)

    class BadFlush:
        def write(self, record: str) -> int:
            return len(record)

        def flush(self) -> object:
            return result

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", BadFlush())
        with pytest.raises(ValueError, match="classic .* stdout flush incomplete"):
            _ = _run(kind)


@pytest.mark.parametrize("kind", KIND_NAMES)
def test_classic_report_retains_original_batch_raw_samples_and_device(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    """Native output preserves all four batch sizes and complete resources."""
    _synthetic_classic_run(monkeypatch)
    assert _run(kind) == 0
    output = capsys.readouterr().out
    assert output.endswith("\n")
    payload = cast("dict[str, object]", json.loads(output))
    rows = cast("list[dict[str, object]]", payload["rows"])
    device = cast("dict[str, object]", payload["device"])
    assert payload["backend"] == "cuda-synthetic"
    assert device["name"] == "synthetic-device"
    assert device["arch"] == "sm-test"
    assert device["free_memory_bytes"] == _SyntheticResources().free_memory_bytes
    assert device["total_memory_bytes"] == _SyntheticResources().total_memory_bytes
    assert tuple(row["batch_size"] for row in rows) == throughput.BATCH_SIZES
    assert payload["step_budget"] == workload.STEP_BUDGET
    for row in rows:
        if kind == "phase":
            assert len(cast("list[object]", row["samples"])) == phase.SAMPLE_COUNT
            median = cast("dict[str, object]", row["median"])
            assert median["kernel_ns"] == cast("int", row["batch_size"]) * 1000
        else:
            assert len(cast("list[int]", row["raw_ns"])) == throughput.SAMPLE_COUNT


@pytest.mark.parametrize("kind", KIND_NAMES)
@pytest.mark.parametrize("provider", ("writer", "encoder"))
def test_classic_report_json_fault_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    provider: str,
) -> None:
    """A failed serializer cannot publish a spurious classic benchmark."""
    _synthetic_classic_run(monkeypatch)
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
            ValueError, match="classic .* JSON writer failed: RuntimeError"
        ) as caught:
            _ = _run(kind)
        assert caught.value.__cause__ is fault
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("kind", KIND_NAMES)
@pytest.mark.parametrize("stage", ("write", "flush"))
def test_classic_report_stdout_fault_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    stage: str,
) -> None:
    """Host output errors cannot falsely acknowledge classic sample delivery."""
    _synthetic_classic_run(monkeypatch)
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
            ValueError, match=f"classic .* stdout {stage} failed: OSError"
        ) as caught:
            _ = _run(kind)
        assert caught.value.__cause__ is fault
    assert len(output.records) == (0 if stage == "write" else 1)


@pytest.mark.parametrize("kind", KIND_NAMES)
def test_classic_report_rejects_subclassed_write_receipt(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Integer-like output receipts cannot stand in for native write lengths."""
    _synthetic_classic_run(monkeypatch)

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
        with pytest.raises(ValueError, match="classic .* stdout write incomplete"):
            _ = _run(kind)
    assert not output.flushed


@pytest.mark.parametrize("kind", KIND_NAMES)
def test_classic_report_accepts_equivalent_public_encoder(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    """Equivalent public JSON encoding preserves the complete classic matrix."""
    _synthetic_classic_run(monkeypatch)
    source_encoder = json.JSONEncoder

    class EquivalentEncoder(source_encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        assert _run(kind) == 0
        payload = cast("dict[str, object]", json.loads(capsys.readouterr().out))
        rows = cast("list[dict[str, object]]", payload["rows"])
        assert len(rows) == len(throughput.BATCH_SIZES)
        assert payload["step_budget"] == workload.STEP_BUDGET
