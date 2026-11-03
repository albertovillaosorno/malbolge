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
#   - Hardware-free evidence publication checks for resident CUDA sessions.
# - Must-Not:
#   - Execute CUDA hardware or claim kernel throughput from synthetic samples.
# - Allows:
#   - Inputs: frozen classic/current-profile resident timing and device rows.
#   - Outputs: source-bound JSON and exact stdout receipt assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when another independent session diagnostic needs its own tests.
# - Merge-When:
#   - Merge when resident throughput harness owns these exact report contracts.
# - Summary:
#   - Safeguard raw launch-only timings and device identity from JSON mutation.
# - Description:
#   - Exercises report correctness without allocating resident GPU memory.
# - Usage:
#   - Run alongside mathematics tests on CPU-only environments.
# - Defaults:
#   - Exact source encoding, write length, and void flush are mandatory.
#

"""Hardware-free publication tests for resident CUDA session throughput."""

from __future__ import annotations

import json
import sys
from typing import Self, cast

import pytest
from accelerator.exact_primitives import AcceleratorCapability

from benchmarks.accelerator import classic_resident_session_throughput as classic
from benchmarks.accelerator import profile_resident_session_throughput as profile
from benchmarks.accelerator import profile_workload

KINDS = ("classic", "profile")


def _synthetic_resident_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use deterministic resident timing without starting CUDA contexts."""

    class SyntheticAdapter:
        def __init__(self, *_args: object) -> None:
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

    def synthetic_request(*, step_budget: int, prepared_steps: int) -> object:
        assert step_budget == classic.SEGMENT_STEPS
        assert prepared_steps == classic.PREPARED_STEPS
        return object()

    def classic_measure(
        _adapter: object, _request: object, batch_size: int
    ) -> classic.ResidentThroughputRow:
        sample = batch_size * 1000
        segments = batch_size * 1_000_000_000 / sample
        return classic.ResidentThroughputRow(
            batch_size=batch_size,
            median_ns=sample,
            pstdev_ns=0.0,
            raw_ns=(sample,) * classic.SAMPLE_COUNT,
            vm_segments_per_second=segments,
            vm_steps_per_second=segments * classic.SEGMENT_STEPS,
        )

    def profile_measure(
        _adapter: object, _request: object, batch_size: int
    ) -> profile.ResidentProfileThroughputRow:
        sample = batch_size * 1000
        segments = batch_size * 1_000_000_000 / sample
        return profile.ResidentProfileThroughputRow(
            batch_size=batch_size,
            median_ns=sample,
            pstdev_ns=0.0,
            raw_ns=(sample,) * profile.SAMPLE_COUNT,
            vm_segments_per_second=segments,
            vm_steps_per_second=segments * profile.SEGMENT_STEPS,
        )

    monkeypatch.setattr(classic, "CudaClassicRunAdapter", SyntheticAdapter)
    monkeypatch.setattr(profile, "CudaProfileRunAdapter", SyntheticAdapter)
    monkeypatch.setattr(classic, "classic_noop_request", synthetic_request)
    monkeypatch.setattr(profile, "profile_noop_request", synthetic_request)
    monkeypatch.setattr(classic, "_measure", classic_measure)
    monkeypatch.setattr(profile, "_measure", profile_measure)


def _run(kind: str) -> int:
    return classic.main() if kind == "classic" else profile.main()


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_resident_session_report_rejects_forged_timings_and_device(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    provider: str,
) -> None:
    """Public serializer replacements cannot swap measured resident launches."""
    _synthetic_resident_run(monkeypatch)
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
            ValueError, match="resident .* JSON writer differs from source"
        ):
            _ = _run(kind)
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("result", (0, False, "done"))
def test_resident_session_report_rejects_incomplete_stdout_write(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    result: object,
) -> None:
    """Incomplete stdout writes cannot publish raw launch timings."""
    _synthetic_resident_run(monkeypatch)

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
        with pytest.raises(ValueError, match="resident .* stdout write incomplete"):
            _ = _run(kind)
    assert not output.flushed


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("result", (False, 1, "done"))
def test_resident_session_report_rejects_nonvoid_stdout_flush(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    result: object,
) -> None:
    """Foreign flush receipts cannot acknowledge retained timing evidence."""
    _synthetic_resident_run(monkeypatch)

    class BadFlush:
        def write(self, record: str) -> int:
            return len(record)

        def flush(self) -> object:
            return result

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", BadFlush())
        with pytest.raises(ValueError, match="resident .* stdout flush incomplete"):
            _ = _run(kind)


@pytest.mark.parametrize("kind", KINDS)
def test_resident_session_report_keeps_original_device_and_raw_samples(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    """Normal output retains all 15 samples and 4 comparable batch sizes."""
    _synthetic_resident_run(monkeypatch)
    assert _run(kind) == 0
    output = capsys.readouterr().out
    assert output.endswith("\n")
    payload = cast("dict[str, object]", json.loads(output))
    rows = cast("list[dict[str, object]]", payload["rows"])
    device = cast("dict[str, object]", payload["device"])
    assert payload["backend"] == "cuda-synthetic"
    assert device == {"arch": "sm-test", "name": "synthetic-device"}
    assert payload["prepared_steps"] == classic.PREPARED_STEPS
    assert payload["segment_steps"] == classic.SEGMENT_STEPS
    assert tuple(row["batch_size"] for row in rows) == classic.BATCH_SIZES
    if kind == "profile":
        geometry = cast("dict[str, object]", payload["geometry"])
        assert geometry["word_trits"] == profile_workload.PROFILE_TRITS
        assert geometry["memory_words"] == profile_workload.PROFILE_WORDS
    for row in rows:
        assert len(cast("list[int]", row["raw_ns"])) == classic.SAMPLE_COUNT


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("provider", ("writer", "encoder"))
def test_resident_session_report_json_fault_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
    provider: str,
) -> None:
    """An exceptional JSON provider cannot publish forged timing evidence."""
    _synthetic_resident_run(monkeypatch)
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
            ValueError, match="resident .* JSON writer failed: RuntimeError"
        ) as caught:
            _ = _run(kind)
        assert caught.value.__cause__ is fault
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("stage", ("write", "flush"))
def test_resident_session_report_stdout_fault_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    stage: str,
) -> None:
    """Host write and flush faults cannot be reported as successful delivery."""
    _synthetic_resident_run(monkeypatch)
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
            ValueError, match=f"resident .* stdout {stage} failed: OSError"
        ) as caught:
            _ = _run(kind)
        assert caught.value.__cause__ is fault
    assert len(output.records) == (0 if stage == "write" else 1)


@pytest.mark.parametrize("kind", KINDS)
def test_resident_session_report_rejects_foreign_integer_receipt(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """A subclassed integer output length is not native write evidence."""
    _synthetic_resident_run(monkeypatch)

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
        with pytest.raises(ValueError, match="resident .* stdout write incomplete"):
            _ = _run(kind)
    assert not output.flushed


@pytest.mark.parametrize("kind", KINDS)
def test_resident_session_report_accepts_equivalent_public_json_encoder(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    """Native-equivalent JSON adapters retain frozen resident samples."""
    _synthetic_resident_run(monkeypatch)
    source_encoder = json.JSONEncoder

    class EquivalentEncoder(source_encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        assert _run(kind) == 0
        payload = cast("dict[str, object]", json.loads(capsys.readouterr().out))
        rows = cast("list[dict[str, object]]", payload["rows"])
        assert len(rows) == len(classic.BATCH_SIZES)
        assert payload["sample_count"] == classic.SAMPLE_COUNT
