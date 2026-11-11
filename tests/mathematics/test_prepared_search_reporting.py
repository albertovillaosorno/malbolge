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
#   - Hardware-free reports for CPU/CUDA prepared search comparison paths.
# - Must-Not:
#   - Initialize CUDA or call synthetic metrics real device performance.
# - Allows:
#   - Inputs: deterministic prepared-search timing and resource evidence.
#   - Outputs: source-bound JSON and exact host-write acknowledgment tests.
#   - Side effects: none.
# - Split-When:
#   - Split when another independent search workload owns new reporting.
# - Merge-When:
#   - Merge when prepared search owns the same transport contract.
# - Summary:
#   - Validate retained ordinary/prepared CPU/CUDA search report integrity.
# - Description:
#   - Reject forged speedup/phase/proof evidence and incomplete publication.
# - Usage:
#   - Run alongside mathematics regressions without requiring a GPU.
# - Defaults:
#   - Native JSON agreement, exact stdout write and void flush required.
#

"""Hardware-free prepared CPU/CUDA search report integrity tests."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import cast

import pytest
from accelerator.cpu import CpuPreparedPrimitiveStats
from accelerator.cuda import CudaPreparedPrimitiveStats
from accelerator.exact_primitives import AcceleratorCapability

from benchmarks.accelerator import search_prepared_phase_profile as phase
from benchmarks.accelerator import search_prepared_throughput as throughput
from benchmarks.accelerator import search_workload as workload

KINDS = ("throughput", "phase")


@dataclass(frozen=True, slots=True)
class _SyntheticWorkload:
    problem: bytes = b"synthetic prepared search"


@dataclass(frozen=True, slots=True)
class _SyntheticMeasuredSearch:
    capability: AcceleratorCapability
    cpu_stats: CpuPreparedPrimitiveStats
    cuda_stats: CudaPreparedPrimitiveStats
    membership_count: int
    reference_word_count: int
    rows: tuple[throughput.SearchTiming, ...]
    selection_count: int


@dataclass(frozen=True, slots=True)
class _SyntheticMeasuredPhases:
    capability: AcceleratorCapability
    cpu: dict[str, phase.PhaseTiming]
    cpu_stats: CpuPreparedPrimitiveStats
    cuda: dict[str, phase.PhaseTiming]
    cuda_stats: CudaPreparedPrimitiveStats
    membership_count: int
    reference_word_count: int
    selection_count: int


def _synthetic_prepared_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject complete prepared proof and sample shapes without CUDA work."""
    capability = AcceleratorCapability(
        backend_id="cuda-synthetic",
        device_arch="sm-test",
        device_name="synthetic-device",
    )
    cpu_stats = CpuPreparedPrimitiveStats(
        builds=1,
        evaluations=16,
        resident_count=workload.CORPUS_SIZE,
        resident_kind=None,
        reuses=15,
        rotate_table_entries=workload.CORPUS_SIZE,
    )
    cuda_stats = CudaPreparedPrimitiveStats(
        builds=1,
        evaluations=16,
        packed_evaluations=16,
        resident_count=workload.CORPUS_SIZE,
        resident_kind=None,
        reuses=15,
    )

    def synthetic_workload() -> _SyntheticWorkload:
        return _SyntheticWorkload()

    def synthetic_throughput(_workload: object) -> _SyntheticMeasuredSearch:
        routes = (
            throughput.CPU_ORDINARY,
            throughput.CPU_PREPARED,
            throughput.CUDA_ORDINARY,
            throughput.CUDA_PREPARED,
        )
        medians = (4000, 2000, 3000, 1000)
        rows = tuple(
            throughput.SearchTiming(
                route_id=route,
                max_ns=sample,
                median_ns=sample,
                min_ns=sample,
                pstdev_ns=0.0,
                raw_ns=(sample,) * throughput.SAMPLE_COUNT,
            )
            for route, sample in zip(routes, medians, strict=True)
        )
        return _SyntheticMeasuredSearch(
            capability=capability,
            cpu_stats=cpu_stats,
            cuda_stats=cuda_stats,
            membership_count=workload.CORPUS_SIZE,
            reference_word_count=1,
            rows=rows,
            selection_count=1,
        )

    def synthetic_phases(_workload: object) -> _SyntheticMeasuredPhases:
        def timings(sample: int) -> dict[str, phase.PhaseTiming]:
            return {
                name: phase.PhaseTiming(
                    max_ns=sample,
                    median_ns=sample,
                    min_ns=sample,
                    pstdev_ns=0.0,
                    raw_ns=(sample,) * phase.SAMPLE_COUNT,
                )
                for name in phase.PHASE_NAMES
            }

        return _SyntheticMeasuredPhases(
            capability=capability,
            cpu=timings(2000),
            cpu_stats=cpu_stats,
            cuda=timings(1000),
            cuda_stats=cuda_stats,
            membership_count=workload.CORPUS_SIZE,
            reference_word_count=1,
            selection_count=1,
        )

    monkeypatch.setattr(
        throughput, "full_domain_rotate_target_workload", synthetic_workload
    )
    monkeypatch.setattr(phase, "full_domain_rotate_target_workload", synthetic_workload)
    monkeypatch.setattr(throughput, "_measure_search", synthetic_throughput)
    monkeypatch.setattr(phase, "_measure_phases", synthetic_phases)


def _run(kind: str) -> int:
    return throughput.main() if kind == "throughput" else phase.main()


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_prepared_search_report_rejects_forged_speedups_and_proofs(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    provider: str,
) -> None:
    """Substituted JSON cannot forge prepared proof or four-route speedups."""
    _synthetic_prepared_run(monkeypatch)
    forged = '{"device":null,"benchmark_id":"forged","routes":null}'

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
            ValueError, match="prepared .* JSON writer differs from source"
        ):
            _ = _run(kind)
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("result", (0, False, "done"))
def test_prepared_search_report_rejects_nonexact_stdout_write(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    result: object,
) -> None:
    """A short or nonnative output receipt cannot attest retained results."""
    _synthetic_prepared_run(monkeypatch)

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
        with pytest.raises(ValueError, match="prepared .* stdout write incomplete"):
            _ = _run(kind)
    assert not output.flushed


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("result", (False, 1, "done"))
def test_prepared_search_report_rejects_forged_flush_receipt(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    result: object,
) -> None:
    """Foreign flush receipts are not successful report delivery."""
    _synthetic_prepared_run(monkeypatch)

    class BadFlush:
        def write(self, record: str) -> int:
            return len(record)

        def flush(self) -> object:
            return result

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", BadFlush())
        with pytest.raises(ValueError, match="prepared .* stdout flush incomplete"):
            _ = _run(kind)


@pytest.mark.parametrize("kind", KINDS)
def test_prepared_search_report_retains_device_samples_and_proof_fields(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    """Native encoding retains four routes or named phases with proof IDs."""
    _synthetic_prepared_run(monkeypatch)
    assert _run(kind) == 0
    output = capsys.readouterr().out
    assert output.endswith("\n")
    payload = cast("dict[str, object]", json.loads(output))
    device = cast("dict[str, object]", payload["device"])
    session = cast("dict[str, object]", payload["cuda_prepared_session"])
    assert device == {
        "backend": "cuda-synthetic",
        "arch": "sm-test",
        "name": "synthetic-device",
    }
    assert session["builds"] == 1
    assert session["reuses"] == 15
    assert payload["prepared_membership_count"] == workload.CORPUS_SIZE
    assert payload["prepared_selection_count"] == 1
    if kind == "throughput":
        routes = cast("dict[str, dict[str, object]]", payload["routes"])
        assert set(routes) == {
            throughput.CPU_ORDINARY,
            throughput.CPU_PREPARED,
            throughput.CUDA_ORDINARY,
            throughput.CUDA_PREPARED,
        }
        for row in routes.values():
            assert len(cast("list[int]", row["raw_ns"])) == throughput.SAMPLE_COUNT
        speedups = cast("dict[str, float]", payload["speedups_at_median"])
        assert speedups["cuda_prepared_over_ordinary"] == 3
    else:
        cpu = cast("dict[str, dict[str, object]]", payload["cpu"])
        cuda = cast("dict[str, dict[str, object]]", payload["cuda"])
        assert set(cpu) == set(phase.PHASE_NAMES)
        for row in cuda.values():
            assert len(cast("list[int]", row["raw_ns"])) == phase.SAMPLE_COUNT


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("provider", ("writer", "encoder"))
def test_prepared_search_report_json_fault_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    provider: str,
) -> None:
    """Broken JSON providers cannot publish fabricated prepared samples."""
    _synthetic_prepared_run(monkeypatch)
    fault = RuntimeError("synthetic JSON failure")

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
            ValueError, match="prepared .* JSON writer failed: RuntimeError"
        ) as caught:
            _ = _run(kind)
        assert caught.value.__cause__ is fault
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("stage", ("write", "flush"))
def test_prepared_search_report_stdout_fault_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    stage: str,
) -> None:
    """Host write/flush failures cannot certify complete prepared evidence."""
    _synthetic_prepared_run(monkeypatch)
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
            ValueError, match=f"prepared .* stdout {stage} failed: OSError"
        ) as caught:
            _ = _run(kind)
        assert caught.value.__cause__ is fault
    assert len(output.records) == (0 if stage == "write" else 1)


@pytest.mark.parametrize("kind", KINDS)
def test_prepared_search_report_rejects_subclassed_write_receipt(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """A subclassed integer is not a native stdout delivery receipt."""
    _synthetic_prepared_run(monkeypatch)

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
        with pytest.raises(ValueError, match="prepared .* stdout write incomplete"):
            _ = _run(kind)
    assert not output.flushed


@pytest.mark.parametrize("kind", KINDS)
def test_prepared_search_report_accepts_equivalent_public_encoder(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    """Equivalent JSON encoding preserves the retained prepared evidence."""
    _synthetic_prepared_run(monkeypatch)
    native_encoder = json.JSONEncoder

    class EquivalentEncoder(native_encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        assert _run(kind) == 0
        payload = cast("dict[str, object]", json.loads(capsys.readouterr().out))
        assert payload["benchmark_id"] == (
            "rotate-target-prepared-search-throughput-v3"
            if kind == "throughput"
            else "rotate-target-prepared-search-phase-profile-v3"
        )
