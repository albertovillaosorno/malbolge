# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
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

from dataclasses import replace

from accelerator.classic_run import RunError
from accelerator.classic_run import RunStatus
from accelerator.classic_step import StepTermination
from accelerator.cuda.classic_step import XLAT1
from accelerator.cuda.classic_step import XLAT2
from accelerator.profile_run import ProfileMemoryImage
from accelerator.profile_run import ProfileRunResult
import pytest

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
