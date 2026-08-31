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

from accelerator.cuda.classic_step import XLAT1
from accelerator.profile_run import ProfileMemoryImage
import pytest
from scripts.validate import target_profile

from benchmarks.accelerator import profile_width_throughput as benchmark

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
    assert tuple(
        range(benchmark.MINIMUM_WIDTH, current.word_trits + 1)
    ) == benchmark.WIDTHS
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
    assert (
        request.step_budget
        == benchmark.STEP_BUDGET
        == EXPECTED_STEP_BUDGET
    )
    assert request.code_pointer == INITIAL_POINTER
    assert request.data_pointer == INITIAL_POINTER
    assert request.input_bytes == ()
    assert request.output_bytes == ()
    words = request.memory.words()
    assert len(words) == EXPECTED_MEMORY_WORDS[word_trits]
    for code_pointer in range(benchmark.STEP_BUDGET):
        encoded = words[code_pointer]
        decoded = XLAT1[
            (encoded - ENCODING_BASE + code_pointer) % len(XLAT1)
        ]
        assert decoded == ord("+")


def test_profile_width_throughput_rejects_unreviewed_width() -> None:
    """The harness cannot silently extend its reviewed width set."""
    with pytest.raises(ValueError, match="requires one of"):
        _ = benchmark.profile_width_geometry(UNREVIEWED_WIDTH)
