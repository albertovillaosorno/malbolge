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
#   - Deterministic contract tests for adaptive-width throughput fixtures.
# - Must-Not:
#   - Require CUDA hardware or turn performance observations into correctness.
# - Allows:
#   - Inputs: benchmark geometry and request constructors.
#   - Outputs: deterministic contract assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when retained live evidence gains an independent validation schema.
# - Merge-When:
#   - Merge when another test owns these exact benchmark fixture invariants.
# - Summary:
#   - Contract tests for equivalent-work N10-N15 throughput fixtures.
# - Description:
#   - Proves widths vary geometry while semantic work stays fixed.
# - Usage:
#   - Run as part of mathematics and benchmark validation.
# - Defaults:
#   - Hardware execution remains outside this deterministic test boundary.
#

"""Contract tests for equivalent-work N10-N15 throughput fixtures."""

from __future__ import annotations

import json
import sys
from typing import Self, cast

import pytest
from accelerator.cuda.classic_step import XLAT1
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.profile_run import ProfileMemoryImage, ProfileRunGeometry

from benchmarks.accelerator import profile_width_throughput as benchmark
from scripts.validate import target_profile

ENCODING_BASE = 33
EXPECTED_STEP_BUDGET = 64
EXPECTED_WIDTHS = (10, 11, 12, 13, 14, 15)
EXPECTED_MEMORY_WORDS = {
    10: 59_049,
    11: 177_147,
    12: 531_441,
    13: 1_594_323,
    14: 4_782_969,
    15: 14_348_907,
}
INITIAL_POINTER = 0
UNREVIEWED_WIDTH = 9


def test_profile_width_throughput_covers_every_admitted_width() -> None:
    """The memory-bound sweep covers N10 through the canonical N14 width."""
    current = target_profile.current_profile_geometry()
    assert current.word_trits == benchmark.MAXIMUM_WIDTH == EXPECTED_WIDTHS[-1]
    assert (
        tuple(range(benchmark.MINIMUM_WIDTH, current.word_trits + 1))
        == benchmark.WIDTHS
    )
    assert benchmark.WIDTHS == EXPECTED_WIDTHS


@pytest.mark.parametrize("word_trits", list(benchmark.WIDTHS))
def test_profile_width_throughput_geometry_is_exact(word_trits: int) -> None:
    """Each geometry preserves canonical profile opcode assignment."""
    current = target_profile.current_profile_geometry()
    geometry = benchmark.profile_width_geometry(word_trits)
    assert geometry.word_trits == word_trits
    expected_words = EXPECTED_MEMORY_WORDS[word_trits]
    assert geometry.word_modulus == expected_words
    assert geometry.memory_words == expected_words
    assert geometry.eof_word == expected_words - 1
    assert geometry.input_instruction == ord(current.input_instruction)
    assert geometry.output_instruction == ord(current.output_instruction)


@pytest.mark.parametrize("word_trits", list(benchmark.WIDTHS))
def test_profile_width_noop_request_keeps_equivalent_work(
    word_trits: int,
) -> None:
    """Each width prepares the identical 64 decoded no-op transitions."""
    request = benchmark.profile_width_noop_request(word_trits)
    assert isinstance(request.memory, ProfileMemoryImage)
    assert request.step_budget == benchmark.STEP_BUDGET == EXPECTED_STEP_BUDGET
    assert request.code_pointer == INITIAL_POINTER
    assert request.data_pointer == INITIAL_POINTER
    assert request.input_bytes == ()
    assert request.output_bytes == ()
    words = request.memory.words()
    assert len(words) == EXPECTED_MEMORY_WORDS[word_trits]
    for code_pointer in range(benchmark.STEP_BUDGET):
        encoded = words[code_pointer]
        decoded = XLAT1[(encoded - ENCODING_BASE + code_pointer) % len(XLAT1)]
        assert decoded == ord("+")


def test_profile_width_throughput_rejects_unreviewed_width() -> None:
    """The harness cannot silently extend its reviewed width set."""
    with pytest.raises(ValueError, match="requires one of"):
        _ = benchmark.profile_width_geometry(UNREVIEWED_WIDTH)


def _synthetic_width_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deliver deterministic width timing without initializing CUDA memory."""

    class SyntheticAdapter:
        def __init__(self, _geometry: ProfileRunGeometry) -> None:
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

    def synthetic_request(_word_trits: int) -> object:
        return object()

    def synthetic_measure(
        _adapter: object, _request: object, geometry: ProfileRunGeometry
    ) -> benchmark.WidthThroughputRow:
        sample = geometry.word_trits * 1000
        return benchmark.WidthThroughputRow(
            items_per_second_at_median=1_000_000_000 / sample,
            median_ns=sample,
            memory_bytes_per_vm=geometry.memory_words * benchmark.WORD_BYTES,
            memory_words=geometry.memory_words,
            pstdev_ns=0.0,
            raw_ns=(sample,) * benchmark.SAMPLE_COUNT,
            vm_steps_per_second_at_median=(
                benchmark.STEP_BUDGET * 1_000_000_000 / sample
            ),
            word_trits=geometry.word_trits,
        )

    monkeypatch.setattr(benchmark, "CudaProfileRunAdapter", SyntheticAdapter)
    monkeypatch.setattr(benchmark, "profile_width_noop_request", synthetic_request)
    monkeypatch.setattr(benchmark, "_measure", synthetic_measure)


@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_width_report_rejects_forged_device_and_timing_rows(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
) -> None:
    """Public JSON replacements cannot publish unmeasured width timings."""
    _synthetic_width_run(monkeypatch)
    forged = '{"benchmark_id":"forged","rows":[],"device":null}'

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
            ValueError, match="profile width JSON writer differs from source"
        ):
            _ = benchmark.main()
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("result", (0, False, "done"))
def test_width_report_rejects_incomplete_stdout_write(
    monkeypatch: pytest.MonkeyPatch,
    result: object,
) -> None:
    """A short or foreign write receipt cannot certify retained samples."""
    _synthetic_width_run(monkeypatch)

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
        with pytest.raises(ValueError, match="profile width stdout write incomplete"):
            _ = benchmark.main()
    assert not output.flushed


@pytest.mark.parametrize("result", (False, 1, "done"))
def test_width_report_rejects_nonvoid_stdout_flush(
    monkeypatch: pytest.MonkeyPatch,
    result: object,
) -> None:
    """A foreign flush receipt cannot claim complete report delivery."""
    _synthetic_width_run(monkeypatch)

    class BadFlush:
        def write(self, record: str) -> int:
            return len(record)

        def flush(self) -> object:
            return result

    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", BadFlush())
        with pytest.raises(ValueError, match="profile width stdout flush incomplete"):
            _ = benchmark.main()


def test_width_report_retains_frozen_widths_and_raw_samples(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Canonical report emits all six original N10-N15 width sample groups."""
    _synthetic_width_run(monkeypatch)
    assert benchmark.main() == 0
    output = capsys.readouterr().out
    assert output.endswith("\n")
    payload = cast("dict[str, object]", json.loads(output))
    rows = cast("list[dict[str, object]]", payload["rows"])
    assert payload["benchmark_id"] == benchmark.BENCHMARK_ID
    assert payload["backend"] == "cuda-synthetic"
    assert payload["device"] == {"arch": "sm-test", "name": "synthetic-device"}
    assert payload["widths"] == list(benchmark.WIDTHS)
    assert tuple(row["word_trits"] for row in rows) == benchmark.WIDTHS
    for row in rows:
        assert len(cast("list[int]", row["raw_ns"])) == benchmark.SAMPLE_COUNT


@pytest.mark.parametrize("provider", ("writer", "encoder"))
def test_width_report_json_fault_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
) -> None:
    """A broken serializer cannot publish untrusted width throughput rows."""
    _synthetic_width_run(monkeypatch)
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
            benchmark.ProfileWidthReportError,
            match="profile width JSON writer failed: RuntimeError",
        ) as caught:
            _ = benchmark.main()
        assert caught.value.__cause__ is fault
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("stage", ("write", "flush"))
def test_width_report_stdout_fault_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """Host stdout errors cannot be treated as successful sample delivery."""
    _synthetic_width_run(monkeypatch)
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
            benchmark.ProfileWidthReportError,
            match=f"profile width stdout {stage} failed: OSError",
        ) as caught:
            _ = benchmark.main()
        assert caught.value.__cause__ is fault
    assert len(output.records) == (0 if stage == "write" else 1)


def test_width_report_rejects_subclassed_write_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An integer-like receipt cannot certify complete output delivery."""
    _synthetic_width_run(monkeypatch)

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
            benchmark.ProfileWidthReportError,
            match="profile width stdout write incomplete",
        ):
            _ = benchmark.main()
    assert not output.flushed


def test_width_report_accepts_equivalent_public_json_encoder(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Equivalent public JSON adapters retain native width evidence bytes."""
    _synthetic_width_run(monkeypatch)
    source_encoder = json.JSONEncoder

    class EquivalentEncoder(source_encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        assert benchmark.main() == 0
        report = cast("dict[str, object]", json.loads(capsys.readouterr().out))
        rows = cast("list[dict[str, object]]", report["rows"])
        assert report["workload_id"] == benchmark.WORKLOAD_ID
        assert len(rows) == len(benchmark.WIDTHS)
