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
#   - Hardware-free publication checks for current-profile CUDA phase data.
# - Must-Not:
#   - Execute CUDA hardware or mistake synthetic phases for measured evidence.
# - Allows:
#   - Inputs: synthetic per-phase observations, geometry, and device resources.
#   - Outputs: exact report identity and stdout transport assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when other workload phase diagnostics need independent ownership.
# - Merge-When:
#   - Merge when the profile benchmark owns these exact phase output checks.
# - Summary:
#   - Protect current-profile full-run and resident-snapshot phase reports.
# - Description:
#   - Reject replaced JSON writers and false stdout receipts without CUDA.
# - Usage:
#   - Run as a mathematics regression suite on any supported Python host.
# - Defaults:
#   - Native encoder agreement, exact write, and void flush are mandatory.
#

"""Hardware-free current-profile CUDA phase report publication checks."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Self, cast

import pytest
from accelerator.cuda.profile_run import ProfileRunPhaseProfile
from accelerator.exact_primitives import AcceleratorCapability

from benchmarks.accelerator import profile_resident_snapshot_phase_profile as snapshot
from benchmarks.accelerator import profile_run_phase_profile as phase
from benchmarks.accelerator import profile_workload as workload

KINDS = ("run", "snapshot")


@dataclass(frozen=True, slots=True)
class _SyntheticResources:
    free_memory_bytes: int = 15_000_000_000
    max_threads_per_block: int = 1024
    multiprocessor_count: int = 30
    total_memory_bytes: int = 16_000_000_000


@dataclass(frozen=True, slots=True)
class _SyntheticPlan:
    resources: _SyntheticResources = _SyntheticResources()


def _synthetic_profile_phases(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generate canonical full-run and resident snapshot rows without CUDA."""

    class SyntheticAdapter:
        def __init__(self, _geometry: object) -> None:
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

    def run_measure(
        _adapter: object, _request: object, batch_size: int
    ) -> tuple[phase.PhaseSummary, tuple[ProfileRunPhaseProfile, ...]]:
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
        observation = ProfileRunPhaseProfile(
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

    def snapshot_measure(
        _adapter: object, _request: object, batch_size: int
    ) -> snapshot.SnapshotPhaseRow:
        sample = batch_size * 1000
        timing = snapshot.Timing(
            max_ns=sample,
            median_ns=sample,
            min_ns=sample,
            pstdev_ns=0.0,
            raw_ns=(sample,) * snapshot.SAMPLE_COUNT,
        )
        coverage = snapshot.Coverage(
            max_ratio=0.75,
            median_ratio=0.75,
            min_ratio=0.75,
            raw_ratio=(0.75,) * snapshot.SAMPLE_COUNT,
        )
        return snapshot.SnapshotPhaseRow(
            batch_size=batch_size,
            chunks=1,
            decode=timing,
            host_memory_allocate=timing,
            memory_download=timing,
            named_coverage=coverage,
            output_download=timing,
            state_download=timing,
            total=timing,
        )

    monkeypatch.setattr(phase, "CudaProfileRunAdapter", SyntheticAdapter)
    monkeypatch.setattr(snapshot, "CudaProfileRunAdapter", SyntheticAdapter)
    monkeypatch.setattr(phase, "profile_noop_request", synthetic_request)
    monkeypatch.setattr(snapshot, "profile_noop_request", synthetic_request)
    monkeypatch.setattr(phase, "_measure", run_measure)
    monkeypatch.setattr(snapshot, "_measure", snapshot_measure)


def _run(kind: str) -> int:
    return phase.main() if kind == "run" else snapshot.main()


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_profile_phase_report_rejects_forged_device_timing_and_coverage(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    provider: str,
) -> None:
    """Changed public JSON cannot forge measured diagnostic phases."""
    _synthetic_profile_phases(monkeypatch)
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
            ValueError, match="profile .* JSON writer differs from source"
        ):
            _ = _run(kind)
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("result", (0, False, "done"))
def test_profile_phase_report_rejects_incomplete_stdout_write(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    result: object,
) -> None:
    """A short or false native write cannot attest phase evidence delivery."""
    _synthetic_profile_phases(monkeypatch)

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
        with pytest.raises(ValueError, match="profile .* stdout write incomplete"):
            _ = _run(kind)
    assert not output.flushed


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("result", (False, 1, "done"))
def test_profile_phase_report_rejects_nonvoid_stdout_flush(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    result: object,
) -> None:
    """A forged flush receipt cannot certify retained phase evidence."""
    _synthetic_profile_phases(monkeypatch)

    class BadFlush:
        def write(self, text: str) -> int:
            return len(text)

        def flush(self) -> object:
            return result

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", BadFlush())
        with pytest.raises(ValueError, match="profile .* stdout flush incomplete"):
            _ = _run(kind)


@pytest.mark.parametrize("kind", KINDS)
def test_profile_phase_report_retains_complete_rows_and_identity(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    """Native current-profile reports preserve sample counts and geometry."""
    _synthetic_profile_phases(monkeypatch)
    assert _run(kind) == 0
    output = capsys.readouterr().out
    assert output.endswith("\n")
    payload = cast("dict[str, object]", json.loads(output))
    rows = cast("list[dict[str, object]]", payload["rows"])
    geometry = cast("dict[str, object]", payload["geometry"])
    device = cast("dict[str, object]", payload["device"])
    assert payload["backend"] == "cuda-synthetic"
    assert device["name"] == "synthetic-device"
    assert device["arch"] == "sm-test"
    assert geometry["word_trits"] == workload.PROFILE_TRITS
    assert geometry["memory_words"] == workload.PROFILE_WORDS
    assert tuple(row["batch_size"] for row in rows) == phase.BATCH_SIZES
    for row in rows:
        if kind == "run":
            assert len(cast("list[object]", row["samples"])) == phase.SAMPLE_COUNT
            median = cast("dict[str, object]", row["median"])
            assert median["kernel_ns"] == cast("int", row["batch_size"]) * 1000
        else:
            total = cast("dict[str, object]", row["total"])
            coverage = cast("dict[str, object]", row["named_coverage"])
            assert len(cast("list[int]", total["raw_ns"])) == snapshot.SAMPLE_COUNT
            assert (
                len(cast("list[float]", coverage["raw_ratio"])) == snapshot.SAMPLE_COUNT
            )


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("provider", ("writer", "encoder"))
def test_profile_phase_report_json_fault_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    provider: str,
) -> None:
    """Broken public JSON provider cannot certify measured CUDA phase work."""
    _synthetic_profile_phases(monkeypatch)
    fault = RuntimeError("synthetic JSON fault")

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
            ValueError, match="profile .* JSON writer failed: RuntimeError"
        ) as caught:
            _ = _run(kind)
        assert caught.value.__cause__ is fault
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("stage", ("write", "flush"))
def test_profile_phase_report_stdout_fault_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    stage: str,
) -> None:
    """Host output failure cannot return success on incomplete phase output."""
    _synthetic_profile_phases(monkeypatch)
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
            ValueError, match=f"profile .* stdout {stage} failed: OSError"
        ) as caught:
            _ = _run(kind)
        assert caught.value.__cause__ is fault
    assert len(output.records) == (0 if stage == "write" else 1)


@pytest.mark.parametrize("kind", KINDS)
def test_profile_phase_report_rejects_subclassed_integer_write_receipt(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Subclassed write lengths cannot attest native complete output."""
    _synthetic_profile_phases(monkeypatch)

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
        with pytest.raises(ValueError, match="profile .* stdout write incomplete"):
            _ = _run(kind)
    assert not output.flushed


@pytest.mark.parametrize("kind", KINDS)
def test_profile_phase_report_accepts_equivalent_public_json_encoder(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    """Equivalent JSON adapters preserve each frozen phase report field."""
    _synthetic_profile_phases(monkeypatch)
    native_encoder = json.JSONEncoder

    class EquivalentEncoder(native_encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        assert _run(kind) == 0
        payload = cast("dict[str, object]", json.loads(capsys.readouterr().out))
        rows = cast("list[dict[str, object]]", payload["rows"])
        assert payload["sample_count"] == phase.SAMPLE_COUNT
        assert len(rows) == len(phase.BATCH_SIZES)
