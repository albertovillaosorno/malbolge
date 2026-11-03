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
#   - CPU-only verification of CUDA search throughput and phase publication.
# - Must-Not:
#   - Treat synthetic search measurements as genuine device evidence.
# - Allows:
#   - Inputs: deterministic search samples, workload identity, device identity.
#   - Outputs: exact JSON/host-write verification and failure regression tests.
#   - Side effects: none.
# - Split-When:
#   - Split when a distinct search protocol needs independent reporting checks.
# - Merge-When:
#   - Merge when the search performance harness owns this exact publication.
# - Summary:
#   - Source-validate CPU-versus-CUDA benchmark search report transport.
# - Description:
#   - Rejects fabricated speedups and per-phase reports before publication.
# - Usage:
#   - Run as hardware-free mathematics regression tests.
# - Defaults:
#   - Native JSON, complete write and successful flush required.
#

"""Hardware-free source-bound search throughput and phase report tests."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Self, cast

import pytest
from accelerator.exact_primitives import AcceleratorCapability

from benchmarks.accelerator import search_phase_profile as phase
from benchmarks.accelerator import search_throughput as throughput
from benchmarks.accelerator import search_workload as workload

KINDS = ("throughput", "phase")


@dataclass(frozen=True, slots=True)
class _SyntheticWorkload:
    problem: bytes = b"synthetic CPU/CUDA full-domain input"
    request: object = object()
    verifier: object = object()


def _synthetic_search_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use fixed CPU/CUDA observations without executing real search or CUDA."""

    class SyntheticPrimitive:
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

    def synthetic_workload() -> _SyntheticWorkload:
        return _SyntheticWorkload()

    def synthetic_cpu() -> object:
        return object()

    def synthetic_cuda(_primitive: object) -> object:
        return object()

    def synthetic_pair(
        _cpu: object, _cuda: object, _request: object, *, verifier: object
    ) -> tuple[throughput.SearchTiming, throughput.SearchTiming]:
        _ = verifier
        return (
            throughput.SearchTiming(
                backend_id=workload.CPU_BACKEND,
                max_ns=1000,
                median_ns=1000,
                min_ns=1000,
                pstdev_ns=0.0,
                raw_ns=(1000,) * throughput.SAMPLE_COUNT,
            ),
            throughput.SearchTiming(
                backend_id=workload.CUDA_BACKEND,
                max_ns=500,
                median_ns=500,
                min_ns=500,
                pstdev_ns=0.0,
                raw_ns=(500,) * throughput.SAMPLE_COUNT,
            ),
        )

    def synthetic_phases(
        _adapter: object, _workload: object, backend_id: str
    ) -> dict[str, phase.PhaseTiming]:
        sample = 500 if backend_id == workload.CUDA_BACKEND else 1000
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

    for module in (throughput, phase):
        monkeypatch.setattr(module, "CudaExactPrimitiveAdapter", SyntheticPrimitive)
        monkeypatch.setattr(
            module, "full_domain_rotate_target_workload", synthetic_workload
        )
        monkeypatch.setattr(module, "cpu_rotate_target_search_adapter", synthetic_cpu)
        monkeypatch.setattr(module, "rotate_target_search_adapter", synthetic_cuda)
    monkeypatch.setattr(throughput, "_measure_pair", synthetic_pair)
    monkeypatch.setattr(phase, "_measure", synthetic_phases)


def _run(kind: str) -> int:
    return throughput.main() if kind == "throughput" else phase.main()


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_search_report_rejects_forged_speedup_phases_and_device(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    provider: str,
) -> None:
    """Substituted serializer cannot publish fabricated CPU/CUDA comparisons."""
    _synthetic_search_run(monkeypatch)
    forged = '{"benchmark_id":"forged","device":null,"cpu":null,"cuda":null}'

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
            ValueError, match="search .* JSON writer differs from source"
        ):
            _ = _run(kind)
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("result", (0, False, "done"))
def test_search_report_rejects_partial_stdout_write(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    result: object,
) -> None:
    """No successful search report after a short or foreign write receipt."""
    _synthetic_search_run(monkeypatch)

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
        with pytest.raises(ValueError, match="search .* stdout write incomplete"):
            _ = _run(kind)
    assert not output.flushed


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("result", (False, 1, "done"))
def test_search_report_rejects_nonvoid_stdout_flush(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    result: object,
) -> None:
    """A forged flush cannot certify retained search evidence."""
    _synthetic_search_run(monkeypatch)

    class BadFlush:
        def write(self, record: str) -> int:
            return len(record)

        def flush(self) -> object:
            return result

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", BadFlush())
        with pytest.raises(ValueError, match="search .* stdout flush incomplete"):
            _ = _run(kind)


@pytest.mark.parametrize("kind", KINDS)
def test_search_report_retains_complete_workload_and_samples(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    """Canonical output retains 15 samples and reviewed workload metadata."""
    _synthetic_search_run(monkeypatch)
    assert _run(kind) == 0
    output = capsys.readouterr().out
    assert output.endswith("\n")
    payload = cast("dict[str, object]", json.loads(output))
    cuda = cast("dict[str, object]", payload["cuda"])
    cpu = cast("dict[str, object]", payload["cpu"])
    identity = cast("dict[str, object]", payload["workload"])
    device = cast("dict[str, object]", payload["device"])
    assert device == {
        "arch": "sm-test",
        "backend": "cuda-synthetic",
        "name": "synthetic-device",
    }
    assert identity["identity"] == workload.WORKLOAD_ID
    assert identity["corpus_size"] == workload.CORPUS_SIZE
    if kind == "throughput":
        assert payload["cuda_speedup_at_median"] == 2
        assert len(cast("list[int]", cpu["raw_ns"])) == throughput.SAMPLE_COUNT
        assert len(cast("list[int]", cuda["raw_ns"])) == throughput.SAMPLE_COUNT
    else:
        assert set(cuda) == set(phase.PHASE_NAMES)
        assert set(cpu) == set(phase.PHASE_NAMES)
        for name in phase.PHASE_NAMES:
            data = cast("dict[str, object]", cuda[name])
            assert len(cast("list[int]", data["raw_ns"])) == phase.SAMPLE_COUNT


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("provider", ("writer", "encoder"))
def test_search_report_json_fault_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    provider: str,
) -> None:
    """A broken JSON writer cannot publish unsupported search results."""
    _synthetic_search_run(monkeypatch)
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
            ValueError, match="search .* JSON writer failed: RuntimeError"
        ) as caught:
            _ = _run(kind)
        assert caught.value.__cause__ is fault
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("stage", ("write", "flush"))
def test_search_report_stdout_fault_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    stage: str,
) -> None:
    """Output transport errors cannot certify complete CPU/CUDA evidence."""
    _synthetic_search_run(monkeypatch)
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
            ValueError, match=f"search .* stdout {stage} failed: OSError"
        ) as caught:
            _ = _run(kind)
        assert caught.value.__cause__ is fault
    assert len(output.records) == (0 if stage == "write" else 1)


@pytest.mark.parametrize("kind", KINDS)
def test_search_report_rejects_subclassed_integer_stdout_receipt(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """A subclassed int cannot replace a native output length receipt."""
    _synthetic_search_run(monkeypatch)

    class ForeignInt(int):
        pass

    class ForgedOutput:
        def __init__(self) -> None:
            self.flushed: bool = False

        def write(self, record: str) -> int:
            return ForeignInt(len(record))

        def flush(self) -> None:
            self.flushed = True

    output = ForgedOutput()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        with pytest.raises(ValueError, match="search .* stdout write incomplete"):
            _ = _run(kind)
    assert not output.flushed


@pytest.mark.parametrize("kind", KINDS)
def test_search_report_accepts_equivalent_public_json_encoder(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    """Equivalent encoding leaves canonical CPU/CUDA evidence unchanged."""
    _synthetic_search_run(monkeypatch)
    native_encoder = json.JSONEncoder

    class EquivalentEncoder(native_encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        assert _run(kind) == 0
        payload = cast("dict[str, object]", json.loads(capsys.readouterr().out))
        assert payload["benchmark_id"] == (
            "rotate-target-search-cpu-vs-cuda-v1"
            if kind == "throughput"
            else "rotate-target-search-phase-profile-v1"
        )
