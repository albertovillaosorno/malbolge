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
#   - Deterministic contract tests for crazy-heavy adaptive-width fixtures.
# - Must-Not:
#   - Require CUDA hardware or turn benchmark timing into correctness authority.
# - Allows:
#   - Inputs: benchmark geometry, request, and expected-memory constructors.
#   - Outputs: deterministic contract assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when another compute-heavy fixture gains independent semantics.
# - Merge-When:
#   - Merge when another test owns these exact crazy-heavy fixture invariants.
# - Summary:
#   - Contract tests for equivalent-work N10-N14 crazy-heavy fixtures.
# - Description:
#   - Proves every width executes the same disjoint sequence of `p` operations.
# - Usage:
#   - Run as part of mathematics and benchmark validation.
# - Defaults:
#   - Hardware execution remains outside this deterministic test boundary.
#

"""Contract tests for equivalent-work N10-N14 crazy-heavy fixtures."""

from __future__ import annotations

import json
import sys
from array import array
from dataclasses import replace
from typing import Self, cast

import pytest
from accelerator.classic_run import RunError, RunStatus
from accelerator.classic_step import StepTermination
from accelerator.cuda.classic_step import XLAT1, XLAT2
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.profile_run import (
    ProfileMemoryImage,
    ProfileRunGeometry,
    ProfileRunResult,
)

from benchmarks.accelerator import profile_width_crazy_throughput as benchmark

EXPECTED_WIDTHS = (10, 11, 12, 13, 14)
EXPECTED_MEMORY_WORDS = {
    10: 59_049,
    11: 177_147,
    12: 531_441,
    13: 1_594_323,
    14: 4_782_969,
}
EXPECTED_STEP_BUDGET = 16_384
EXPECTED_DATA_START = 32_768
EXPECTED_DATA_STOP = 49_152
UNREVIEWED_WIDTH = 15


def test_crazy_width_sweep_is_exact_and_fits_n10() -> None:
    """The compute-heavy sweep is fixed to N10-N14 and fits the smallest VM."""
    assert benchmark.WIDTHS == EXPECTED_WIDTHS
    assert benchmark.STEP_BUDGET == EXPECTED_STEP_BUDGET
    assert benchmark.DATA_START == EXPECTED_DATA_START
    assert benchmark.DATA_STOP == EXPECTED_DATA_STOP
    assert benchmark.STEP_BUDGET <= benchmark.DATA_START
    assert EXPECTED_MEMORY_WORDS[10] > benchmark.DATA_STOP


@pytest.mark.parametrize("word_trits", list(benchmark.WIDTHS))
def test_crazy_width_request_keeps_equivalent_instruction_work(
    word_trits: int,
) -> None:
    """Every width starts the same disjoint sequence of decoded crazy steps."""
    request = benchmark.profile_width_crazy_request(word_trits)
    assert isinstance(request.memory, ProfileMemoryImage)
    assert request.accumulator == 0
    assert request.code_pointer == 0
    assert request.data_pointer == benchmark.DATA_START
    assert request.step_budget == benchmark.STEP_BUDGET
    words = request.memory.words()
    assert len(words) == EXPECTED_MEMORY_WORDS[word_trits]
    for code_pointer in range(benchmark.STEP_BUDGET):
        encoded = words[code_pointer]
        decoded = XLAT1[(encoded - 33 + code_pointer) % len(XLAT1)]
        assert decoded == ord("p")
    assert all(
        words[address] == 0
        for address in range(benchmark.DATA_START, benchmark.DATA_STOP)
    )


@pytest.mark.parametrize("word_trits", list(benchmark.WIDTHS))
def test_crazy_width_expected_memory_is_exact(word_trits: int) -> None:
    """Expected memory applies exact encryption and alternating writes."""
    request = benchmark.profile_width_crazy_request(word_trits)
    memory = request.memory
    assert isinstance(memory, ProfileMemoryImage)
    initial = memory.words()
    expected = benchmark.expected_profile_width_crazy_memory(word_trits)
    half = (EXPECTED_MEMORY_WORDS[word_trits] - 1) // 2
    for code_pointer in range(benchmark.STEP_BUDGET):
        assert expected[code_pointer] == XLAT2[initial[code_pointer] - 33]
    for offset in range(benchmark.STEP_BUDGET):
        value = half if offset % 2 == 0 else 0
        assert expected[benchmark.DATA_START + offset] == value
    assert expected[benchmark.DATA_STOP] == 0


def test_crazy_width_result_validator_is_fail_closed() -> None:
    """The benchmark accepts only exact final outcome and complete memory."""
    width = EXPECTED_WIDTHS[0]
    geometry = benchmark.profile_width_crazy_geometry(width)
    memory = benchmark.expected_profile_width_crazy_memory(width)
    result = ProfileRunResult(
        accumulator=0,
        code_pointer=benchmark.STEP_BUDGET,
        data_pointer=benchmark.DATA_STOP,
        error=RunError.NONE,
        error_pointer=0,
        error_value=0,
        input_consumed=0,
        memory=memory,
        output_bytes=(),
        status=RunStatus.BUDGET_EXHAUSTED,
        steps=benchmark.STEP_BUDGET,
        termination=StepTermination.NONE,
    )
    benchmark.validate_profile_width_crazy_results((result,), geometry, memory)
    with pytest.raises(RuntimeError, match="drifted from equivalent work"):
        benchmark.validate_profile_width_crazy_results(
            (replace(result, code_pointer=result.code_pointer + 1),),
            geometry,
            memory,
        )


def test_crazy_width_benchmark_rejects_n15() -> None:
    """The compute-heavy acceptance sweep cannot silently expand past N14."""
    with pytest.raises(ValueError, match="requires one of"):
        _ = benchmark.profile_width_crazy_geometry(UNREVIEWED_WIDTH)


def _synthetic_reporting_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the full report publisher with deterministic no-CUDA samples."""

    class SyntheticAdapter:
        def __init__(self, _geometry: ProfileRunGeometry) -> None:
            pass

        def __enter__(self) -> Self:
            return self

        def __exit__(
            self, _error_type: object, _error: object, _traceback: object
        ) -> None:
            pass

        def capability(self) -> AcceleratorCapability:
            return AcceleratorCapability(
                backend_id="cuda-synthetic",
                device_arch="sm-test",
                device_name="synthetic-device",
            )

    def measure(
        _adapter: object,
        _request: object,
        geometry: ProfileRunGeometry,
        *,
        expected_memory: array[int],
    ) -> benchmark.CrazyWidthThroughputRow:
        _ = expected_memory
        sample = geometry.word_trits * 1000
        return benchmark.CrazyWidthThroughputRow(
            end_to_end_median_ns=sample * 2,
            end_to_end_pstdev_ns=0.0,
            end_to_end_raw_ns=(sample * 2,) * benchmark.SAMPLE_COUNT,
            end_to_end_vm_steps_per_second=(benchmark.STEP_BUDGET * 1e9 / (sample * 2)),
            memory_bytes_per_vm=geometry.memory_words * benchmark.WORD_BYTES,
            memory_words=geometry.memory_words,
            resident_median_ns=sample,
            resident_pstdev_ns=0.0,
            resident_raw_ns=(sample,) * benchmark.SAMPLE_COUNT,
            resident_vm_steps_per_second=benchmark.STEP_BUDGET * 1e9 / sample,
            word_trits=geometry.word_trits,
        )

    monkeypatch.setattr(benchmark, "CudaProfileRunAdapter", SyntheticAdapter)

    def synthetic_request(_word_trits: int) -> object:
        return object()

    def synthetic_memory(_word_trits: int) -> array[int]:
        return array("I")

    monkeypatch.setattr(benchmark, "profile_width_crazy_request", synthetic_request)
    monkeypatch.setattr(
        benchmark, "expected_profile_width_crazy_memory", synthetic_memory
    )
    monkeypatch.setattr(benchmark, "_measure", measure)


@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_crazy_width_report_rejects_forged_timing_and_device(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
) -> None:
    """Substituted public JSON cannot forge N10-N14 timing measurements."""
    _synthetic_reporting_run(monkeypatch)
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
            ValueError, match="crazy width JSON writer differs from source"
        ):
            _ = benchmark.main()
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("result", (0, False, "done"))
def test_crazy_width_report_rejects_incomplete_stdout_ack(
    monkeypatch: pytest.MonkeyPatch,
    result: object,
) -> None:
    """No successful timing report after a partial or foreign write receipt."""
    _synthetic_reporting_run(monkeypatch)

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
        with pytest.raises(ValueError, match="crazy width stdout write incomplete"):
            _ = benchmark.main()
    assert not output.flushed


@pytest.mark.parametrize("result", (False, 1, "done"))
def test_crazy_width_report_rejects_nonvoid_flush_ack(
    monkeypatch: pytest.MonkeyPatch,
    result: object,
) -> None:
    """A forged flush receipt cannot certify the timing report."""
    _synthetic_reporting_run(monkeypatch)

    class BadFlush:
        def write(self, record: str) -> int:
            return len(record)

        def flush(self) -> object:
            return result

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", BadFlush())
        with pytest.raises(ValueError, match="crazy width stdout flush incomplete"):
            _ = benchmark.main()


def test_crazy_width_report_keeps_full_frozen_width_sample_matrix(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Native output preserves all five widths and fifteen raw samples each."""
    _synthetic_reporting_run(monkeypatch)
    assert benchmark.main() == 0
    output = capsys.readouterr().out
    assert output.endswith("\n")
    report = cast("dict[str, object]", json.loads(output))
    rows = cast("list[dict[str, object]]", report["rows"])
    assert report["benchmark_id"] == benchmark.BENCHMARK_ID
    assert report["backend"] == "cuda-synthetic"
    assert report["device"] == {"arch": "sm-test", "name": "synthetic-device"}
    assert report["widths"] == list(benchmark.WIDTHS)
    assert len(rows) == len(benchmark.WIDTHS)
    assert tuple(row["word_trits"] for row in rows) == benchmark.WIDTHS
    for row in rows:
        assert len(cast("list[int]", row["resident_raw_ns"])) == benchmark.SAMPLE_COUNT
        assert (
            len(cast("list[int]", row["end_to_end_raw_ns"])) == benchmark.SAMPLE_COUNT
        )


@pytest.mark.parametrize("provider", ("writer", "encoder"))
def test_crazy_width_report_json_faults_preserve_cause(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
) -> None:
    """A broken JSON provider must not publish unverified timing rows."""
    _synthetic_reporting_run(monkeypatch)
    fault = RuntimeError("synthetic serializer error")

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
            benchmark.CrazyWidthReportError,
            match="crazy width JSON writer failed: RuntimeError",
        ) as caught:
            _ = benchmark.main()
        assert caught.value.__cause__ is fault
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("stage", ("write", "flush"))
def test_crazy_width_report_stdout_faults_preserve_cause(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """Explicit output transport faults cannot be reported as success."""
    _synthetic_reporting_run(monkeypatch)
    fault = OSError("synthetic stdout failure")

    class BrokenOutput:
        def __init__(self) -> None:
            self.records: list[str] = []

        def write(self, text: str) -> int:
            if stage == "write":
                raise fault
            self.records.append(text)
            return len(text)

        def flush(self) -> None:
            raise fault

    output = BrokenOutput()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", output)
        with pytest.raises(
            benchmark.CrazyWidthReportError,
            match=f"crazy width stdout {stage} failed: OSError",
        ) as caught:
            _ = benchmark.main()
        assert caught.value.__cause__ is fault
    assert len(output.records) == (0 if stage == "write" else 1)


def test_crazy_width_report_rejects_foreign_int_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Subclassed integer output lengths are not native delivery evidence."""
    _synthetic_reporting_run(monkeypatch)

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
            benchmark.CrazyWidthReportError,
            match="crazy width stdout write incomplete",
        ):
            _ = benchmark.main()
    assert not output.flushed


def test_crazy_width_report_accepts_equivalent_public_encoder(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Equivalent public JSON adapters retain original sampled work."""
    _synthetic_reporting_run(monkeypatch)
    native_encoder = json.JSONEncoder

    class EquivalentEncoder(native_encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        assert benchmark.main() == 0
        report = cast("dict[str, object]", json.loads(capsys.readouterr().out))
        rows = cast("list[dict[str, object]]", report["rows"])
        assert report["workload_id"] == benchmark.WORKLOAD_ID
        assert len(rows) == len(benchmark.WIDTHS)
