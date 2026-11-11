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
#   - Hardware-free publication checks for current-profile CUDA throughput.
# - Must-Not:
#   - Require a CUDA device or treat measured speed as correctness authority.
# - Allows:
#   - Inputs: synthetic N14 timing rows and device resource snapshots.
#   - Outputs: exact, source-bound JSON and delivery regression assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when a different benchmark needs independent report evidence.
# - Merge-When:
#   - Merge when the current-profile throughput harness owns report tests.
# - Summary:
#   - Reject forged profile throughput samples and stdout acknowledgements.
# - Description:
#   - Protects retained device, geometry, plan, and raw timing identity.
# - Usage:
#   - Run with mathematics tests on hardware-free hosts.
# - Defaults:
#   - Exact native JSON, native write length, and void flush are mandatory.
#

"""Hardware-free retained current-profile CUDA throughput reporting tests."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Self, cast

import pytest
from accelerator.exact_primitives import AcceleratorCapability

from benchmarks.accelerator import profile_run_throughput as run
from benchmarks.accelerator import profile_workload as workload


@dataclass(frozen=True, slots=True)
class _SyntheticResources:
    free_memory_bytes: int = 15_000_000_000
    max_threads_per_block: int = 1024
    multiprocessor_count: int = 30
    total_memory_bytes: int = 16_000_000_000


@dataclass(frozen=True, slots=True)
class _SyntheticPlan:
    resources: _SyntheticResources = _SyntheticResources()


def _synthetic_profile_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace CUDA work with synthetic timing and capacity observations."""

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

    def synthetic_measure(
        _adapter: object, _request: object, batch_size: int
    ) -> run.ThroughputRow:
        sample = batch_size * 1000
        throughput = batch_size * 1_000_000_000 / sample
        return run.ThroughputRow(
            batch_size=batch_size,
            items_per_second_at_median=throughput,
            median_ns=sample,
            ns_per_item_at_median=sample / batch_size,
            pstdev_ns=0.0,
            raw_ns=(sample,) * run.SAMPLE_COUNT,
            step_budget=workload.STEP_BUDGET,
            vm_steps_per_second_at_median=throughput * workload.STEP_BUDGET,
        )

    monkeypatch.setattr(run, "CudaProfileRunAdapter", SyntheticAdapter)
    monkeypatch.setattr(run, "profile_noop_request", synthetic_request)
    monkeypatch.setattr(run, "_measure", synthetic_measure)


@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_throughput_report_rejects_forged_resource_and_sample_rows(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
) -> None:
    """Changed JSON helpers cannot substitute a fake device or throughput."""
    _synthetic_profile_run(monkeypatch)
    forged = '{"backend":"forged","rows":[],"device":null}'

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
            ValueError, match="profile run JSON writer differs from source"
        ):
            _ = run.main()
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("result", (0, False, "done"))
def test_throughput_report_rejects_partial_native_output(
    monkeypatch: pytest.MonkeyPatch,
    result: object,
) -> None:
    """Short or nonnative writes cannot certify complete measured results."""
    _synthetic_profile_run(monkeypatch)

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
        with pytest.raises(ValueError, match="profile run stdout write incomplete"):
            _ = run.main()
    assert not output.flushed


@pytest.mark.parametrize("result", (False, 1, "done"))
def test_throughput_report_rejects_forged_flush_receipt(
    monkeypatch: pytest.MonkeyPatch,
    result: object,
) -> None:
    """A foreign flush receipt is not successful evidence delivery."""
    _synthetic_profile_run(monkeypatch)

    class BadFlush:
        def write(self, record: str) -> int:
            return len(record)

        def flush(self) -> object:
            return result

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", BadFlush())
        with pytest.raises(ValueError, match="profile run stdout flush incomplete"):
            _ = run.main()


def test_throughput_report_retains_all_batches_and_device_resource_fields(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Canonical JSON retains batch sizes, plan, device, and raw samples."""
    _synthetic_profile_run(monkeypatch)
    assert run.main() == 0
    output = capsys.readouterr().out
    assert output.endswith("\n")
    payload = cast("dict[str, object]", json.loads(output))
    rows = cast("list[dict[str, object]]", payload["rows"])
    device = cast("dict[str, object]", payload["device"])
    assert payload["backend"] == "cuda-synthetic"
    assert payload["batch_sizes"] == list(run.BATCH_SIZES)
    assert tuple(row["batch_size"] for row in rows) == run.BATCH_SIZES
    assert device["name"] == "synthetic-device"
    assert device["arch"] == "sm-test"
    assert device["free_memory_bytes"] == _SyntheticResources().free_memory_bytes
    assert device["total_memory_bytes"] == _SyntheticResources().total_memory_bytes
    assert device["max_threads_per_block"] == 1024
    assert device["multiprocessor_count"] == 30
    for row in rows:
        assert len(cast("list[int]", row["raw_ns"])) == run.SAMPLE_COUNT


@pytest.mark.parametrize("provider", ("writer", "encoder"))
def test_throughput_report_json_fault_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
) -> None:
    """A broken serializer cannot publish unverified batch measurements."""
    _synthetic_profile_run(monkeypatch)
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
            run.ProfileRunReportError,
            match="profile run JSON writer failed: RuntimeError",
        ) as caught:
            _ = run.main()
        assert caught.value.__cause__ is fault
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("stage", ("write", "flush"))
def test_throughput_report_stdout_fault_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """Host write/flush failures cannot return a successful measurement."""
    _synthetic_profile_run(monkeypatch)
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
            run.ProfileRunReportError,
            match=f"profile run stdout {stage} failed: OSError",
        ) as caught:
            _ = run.main()
        assert caught.value.__cause__ is fault
    assert len(output.records) == (0 if stage == "write" else 1)


def test_throughput_report_rejects_subclassed_write_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fake subclassed integer is not a native stdout acknowledgement."""
    _synthetic_profile_run(monkeypatch)

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
        with pytest.raises(
            run.ProfileRunReportError,
            match="profile run stdout write incomplete",
        ):
            _ = run.main()
    assert not output.flushed


def test_throughput_report_accepts_equivalent_public_json_encoder(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An equivalent encoder leaves raw timing and resource evidence intact."""
    _synthetic_profile_run(monkeypatch)
    source_encoder = json.JSONEncoder

    class EquivalentEncoder(source_encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        assert run.main() == 0
        payload = cast("dict[str, object]", json.loads(capsys.readouterr().out))
        rows = cast("list[dict[str, object]]", payload["rows"])
        assert len(rows) == len(run.BATCH_SIZES)
        assert payload["step_budget"] == workload.STEP_BUDGET
