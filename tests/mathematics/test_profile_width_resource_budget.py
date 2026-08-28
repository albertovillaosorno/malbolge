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
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Adaptive profile-width resource-budget evidence tests.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Adaptive profile-width resource-budget evidence tests."""

from __future__ import annotations

from array import array
from itertools import pairwise

from accelerator.classic_run import MAX_U32
from accelerator.classic_run import STATE_WORDS
from accelerator.cuda.resident_kernel import ResidentGeometry
from accelerator.cuda.resident_kernel import resident_kernel_source
from accelerator.profile_run import ProfileMemoryImage
from accelerator.profile_run import ProfileRunGeometry
from accelerator.profile_run import ProfileRunRequest
from accelerator.profile_run import WORD_BYTES
from accelerator.profile_run import validate_profile_run_requests
from algorithms.profile_width.certificate import execution_geometry

from benchmarks.accelerator import resource_budget_measure as measure

EXPECTED_128_MIB_CAPACITY = {
    10: 532,
    11: 177,
    12: 59,
    13: 19,
    14: 6,
}


def test_adaptive_width_sweep_uses_exact_execution_geometry() -> None:
    """Capacity scenarios consume exact certified ternary memory geometry."""
    results = {
        result.word_trits: result
        for result in measure.synthetic_results()
        if result.word_trits is not None
    }
    assert set(results) == set(EXPECTED_128_MIB_CAPACITY)
    for width, expected_capacity in EXPECTED_128_MIB_CAPACITY.items():
        geometry = execution_geometry(width)
        assert geometry is not None
        result = results[width]
        assert result.memory_words == geometry.memory_words
        assert result.item_bytes == (
            geometry.memory_words + STATE_WORDS
        ) * WORD_BYTES
        assert result.fixed_chunk_bytes == 2 * WORD_BYTES
        assert result.max_items_per_chunk == (
            MAX_U32 // geometry.memory_words
        ) + 1
        assert result.first_chunk_items == expected_capacity
        assert result.synthetic


def test_derived_widths_fit_resident_geometry() -> None:
    """Derived N fits the resident contract without new profile identity."""
    for width in EXPECTED_128_MIB_CAPACITY:
        resident = _resident_geometry(width)
        derived = execution_geometry(width)
        assert derived is not None
        assert resident.validated() is resident
        assert resident.memory_words == derived.memory_words
        assert resident.word_trits == derived.word_trits


def test_derived_widths_own_exact_resident_memory_images() -> None:
    """Host resident memory and requests accept every derived geometry."""
    for width in EXPECTED_128_MIB_CAPACITY:
        resident = _resident_geometry(width)
        source = array("I", [0]) * resident.memory_words
        image = ProfileMemoryImage(resident, source)
        request = ProfileRunRequest(
            accumulator=0,
            code_pointer=0,
            data_pointer=0,
            input_bytes=(),
            input_consumed=0,
            memory=image,
            output_bytes=(),
            step_budget=0,
        )
        assert image.geometry == resident
        assert len(image) == resident.memory_words
        assert image.words().readonly
        assert validate_profile_run_requests(resident, (request,)) == (request,)


def test_derived_widths_render_exact_resident_kernel_geometry() -> None:
    """CUDA source receives exact derived geometry without profile identity."""
    for width in EXPECTED_128_MIB_CAPACITY:
        resident = _resident_geometry(width)
        kernel = resident_kernel_source(
            ResidentGeometry(
                interpreter_authority=True,
                eof_word=resident.eof_word,
                input_instruction=resident.input_instruction,
                memory_words=resident.memory_words,
                output_instruction=resident.output_instruction,
                word_modulus=resident.word_modulus,
                word_trits=resident.word_trits,
            ),
            "adaptive_width_probe",
        )
        assert f"#define MEMORY_WORDS {resident.memory_words}u" in kernel
        assert f"#define WORD_TRITS {resident.word_trits}u" in kernel
        assert f"#define MAX_WORD {resident.word_modulus - 1}u" in kernel
        assert f"#define EOF_WORD {resident.eof_word}u" in kernel
        assert (
            f"#define ROTATE_HIGH_WEIGHT {resident.word_modulus // 3}u"
            in kernel
        )


def test_narrower_certified_width_strictly_increases_128_mib_capacity() -> None:
    """The same synthetic device admits more complete VMs at narrower width."""
    results = tuple(
        result
        for result in measure.synthetic_results()
        if result.word_trits is not None
    )
    capacities = tuple(result.first_chunk_items for result in results)
    assert capacities == tuple(EXPECTED_128_MIB_CAPACITY.values())
    assert all(
        left > right
        for left, right in pairwise(capacities)
    )


def _resident_geometry(width: int) -> ProfileRunGeometry:
    derived = execution_geometry(width)
    if derived is None:
        message = f"expected checked adaptive width: {width}"
        raise AssertionError(message)
    return ProfileRunGeometry(
        eof_word=derived.memory_words - 1,
        input_instruction=ord("/"),
        memory_words=derived.memory_words,
        output_instruction=ord("<"),
        word_modulus=derived.memory_words,
        word_trits=derived.word_trits,
    )
