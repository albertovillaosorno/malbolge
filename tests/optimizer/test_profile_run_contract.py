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
#   - Contract tests for scalable resident profile accelerator requests.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Contract tests for scalable resident profile accelerator requests."""

from __future__ import annotations

from array import array
from dataclasses import replace
from typing import Final
from typing import TYPE_CHECKING
from typing import cast

from accelerator.classic_step import StepTermination
from accelerator.exact_primitives import InvalidPrimitiveBatchError
from accelerator.profile_run import MAX_PROFILE_TRITS
from accelerator.profile_run import ProfileMemoryImage
from accelerator.profile_run import ProfileRunGeometry
from accelerator.profile_run import ProfileRunRequest
from accelerator.profile_run import validate_profile_run_requests
from benchmarks.accelerator.profile_workload import GEOMETRY as CURRENT_GEOMETRY
import pytest
from scripts.validate import target_profile

if TYPE_CHECKING:
    from collections.abc import Callable

SMALL_TRITS: Final = 5
SMALL_WORDS: Final = 243
BACKEND_TRITS: Final = 20
BACKEND_WORDS: Final = 3_486_784_401
UNSUPPORTED_BACKEND_TRITS: Final = 21
UNSUPPORTED_BACKEND_WORDS: Final = 10_460_353_203
PROFILE_TRITS_ERROR: Final = "outside supported domain"
WORD_BYTES: Final = 4
MODULUS_ERROR: Final = "modulus 244"
TOO_SMALL_ERROR: Final = "cannot represent graphical encryption values"
MEMORY_LENGTH_ERROR: Final = "requires 243 words"
REGISTER_ERROR: Final = "code pointer outside"
TERMINATION_ERROR: Final = "invalid resident termination"
IMAGE_GEOMETRY_ERROR: Final = "memory image geometry mismatch"
IO_ASSIGNMENT_ERROR: Final = "assign '<' and '/' exactly once"
EXACT_INTEGER_ERROR: Final = "exact integer"
BYTE_ERROR: Final = "byte outside byte domain"
U32_ERROR: Final = "unsigned 32-bit domain"
NONNEGATIVE_INTEGER_ERROR: Final = "nonnegative integer"
GEOMETRY = ProfileRunGeometry(
    eof_word=SMALL_WORDS - 1,
    input_instruction=ord("/"),
    memory_words=SMALL_WORDS,
    output_instruction=ord("<"),
    word_modulus=SMALL_WORDS,
    word_trits=SMALL_TRITS,
)


def test_current_benchmark_geometry_uses_canonical_profile() -> None:
    """Current CUDA evidence cannot reconstruct annual geometry by hand."""
    geometry = target_profile.current_profile_geometry()
    assert CURRENT_GEOMETRY.eof_word == geometry.eof_word
    assert CURRENT_GEOMETRY.input_instruction == ord(geometry.input_instruction)
    assert CURRENT_GEOMETRY.memory_words == geometry.memory_words
    assert CURRENT_GEOMETRY.output_instruction == ord(
        geometry.output_instruction
    )
    assert CURRENT_GEOMETRY.word_modulus == geometry.word_modulus
    assert CURRENT_GEOMETRY.word_trits == geometry.word_trits


def test_profile_memory_repeat_rejects_boolean_count() -> None:
    """Boolean repetition counts never become one copied memory image."""
    image = ProfileMemoryImage(GEOMETRY, array("I", [0]) * SMALL_WORDS)
    invalid_count = cast("int", cast("object", bool(1)))
    with pytest.raises(ValueError, match=NONNEGATIVE_INTEGER_ERROR):
        _ = image.repeat_words(invalid_count)


def test_profile_geometry_accepts_exact_ternary_modulus() -> None:
    """Exact single-word-modular ternary geometry is admitted."""
    assert GEOMETRY.validated() is GEOMETRY


def test_profile_geometry_rejects_boolean_fields() -> None:
    """Boolean geometry values never acquire integer profile semantics."""
    invalid = replace(GEOMETRY, memory_words=True)
    assert EXACT_INTEGER_ERROR in _invalid(invalid.validated)


def test_profile_geometry_rejects_nonternary_modulus() -> None:
    """Geometry cannot silently reinterpret a non-power-of-three word domain."""
    invalid = replace(
        GEOMETRY, word_modulus=244, memory_words=244, eof_word=243
    )
    assert MODULUS_ERROR in _invalid(invalid.validated)


def test_profile_geometry_rejects_aliased_io_instructions() -> None:
    """A profile must assign the two I/O opcodes exactly once."""
    invalid = replace(GEOMETRY, output_instruction=ord("/"))
    assert IO_ASSIGNMENT_ERROR in _invalid(invalid.validated)


def test_profile_geometry_uses_derived_u32_ternary_boundary() -> None:
    """Resident geometry admits the largest exact ternary modulus in u32."""
    boundary = ProfileRunGeometry(
        eof_word=BACKEND_WORDS - 1,
        input_instruction=ord("/"),
        memory_words=BACKEND_WORDS,
        output_instruction=ord("<"),
        word_modulus=BACKEND_WORDS,
        word_trits=BACKEND_TRITS,
    )

    assert MAX_PROFILE_TRITS == BACKEND_TRITS
    assert boundary.validated() is boundary
    assert BACKEND_WORDS == 3**MAX_PROFILE_TRITS
    assert 3 ** (MAX_PROFILE_TRITS + 1) > (1 << 32) - 1


def test_profile_geometry_rejects_first_width_beyond_u32_capacity() -> None:
    """N21 fails before a non-u32 resident modulus can enter the wire."""
    invalid = ProfileRunGeometry(
        eof_word=UNSUPPORTED_BACKEND_WORDS - 1,
        input_instruction=ord("/"),
        memory_words=UNSUPPORTED_BACKEND_WORDS,
        output_instruction=ord("<"),
        word_modulus=UNSUPPORTED_BACKEND_WORDS,
        word_trits=UNSUPPORTED_BACKEND_TRITS,
    )

    assert UNSUPPORTED_BACKEND_TRITS == MAX_PROFILE_TRITS + 1
    assert UNSUPPORTED_BACKEND_WORDS == 3**UNSUPPORTED_BACKEND_TRITS
    assert PROFILE_TRITS_ERROR in _invalid(invalid.validated)


def test_profile_geometry_rejects_too_small_encryption_domain() -> None:
    """A profile must represent every graphical self-encryption result."""
    too_small = ProfileRunGeometry(
        eof_word=80,
        input_instruction=ord("/"),
        memory_words=81,
        output_instruction=ord("<"),
        word_modulus=81,
        word_trits=4,
    )
    assert TOO_SMALL_ERROR in _invalid(too_small.validated)


def test_profile_request_uses_compact_u32_memory() -> None:
    """Scalable memory is a compact contiguous unsigned-word array."""
    request = _request()
    observed = validate_profile_run_requests(GEOMETRY, (request,))
    assert observed == (request,)
    assert isinstance(request.memory, array)
    assert request.memory.itemsize == WORD_BYTES


def test_profile_memory_image_isolated_read_only_and_reusable() -> None:
    """Validated images isolate storage from caller mutation."""
    source = array("I", [0]) * SMALL_WORDS
    image = ProfileMemoryImage(GEOMETRY, source)
    source[0] = 1

    assert image.geometry == GEOMETRY
    assert len(image) == SMALL_WORDS
    assert image.words().readonly
    assert image.words()[0] == 0
    assert image.copy_words()[0] == 0

    request = replace(_request(), memory=image)
    assert validate_profile_run_requests(GEOMETRY, (request,)) == (request,)


def test_profile_memory_image_rejects_geometry_drift() -> None:
    """Validated proof cannot be reused under a different ternary geometry."""
    other_words = 3**6
    other = ProfileRunGeometry(
        eof_word=other_words - 1,
        input_instruction=ord("/"),
        memory_words=other_words,
        output_instruction=ord("<"),
        word_modulus=other_words,
        word_trits=6,
    )
    image = ProfileMemoryImage(other, array("I", [0]) * other_words)
    request = replace(_request(), memory=image)
    assert IMAGE_GEOMETRY_ERROR in _invalid(
        lambda: validate_profile_run_requests(GEOMETRY, (request,))
    )


def test_profile_request_rejects_memory_and_register_drift() -> None:
    """Memory shape/domain and registers remain geometry-bound."""
    short = _request(memory=array("I", [0]) * (SMALL_WORDS - 1))
    assert MEMORY_LENGTH_ERROR in _invalid(
        lambda: validate_profile_run_requests(GEOMETRY, (short,))
    )
    bad_register = replace(_request(), code_pointer=SMALL_WORDS)
    assert REGISTER_ERROR in _invalid(
        lambda: validate_profile_run_requests(GEOMETRY, (bad_register,))
    )


def test_profile_request_rejects_boolean_numeric_fields() -> None:
    """Boolean state, I/O, and budgets fail before resident execution."""
    cases = (
        (replace(_request(), accumulator=True), "word domain"),
        (replace(_request(), step_budget=True), U32_ERROR),
        (replace(_request(), input_consumed=False), EXACT_INTEGER_ERROR),
        (replace(_request(), input_bytes=(True,)), BYTE_ERROR),
    )
    for request, message in cases:
        assert message in _invalid(
            lambda request=request: validate_profile_run_requests(
                GEOMETRY,
                (request,),
            )
        )


def test_profile_request_rejects_raw_termination_integer() -> None:
    """Dynamic callers cannot substitute an untyped termination integer."""
    request = replace(_request(), termination=1)
    assert TERMINATION_ERROR in _invalid(
        lambda: validate_profile_run_requests(GEOMETRY, (request,))
    )


def _request(
    *,
    memory: array[int] | None = None,
) -> ProfileRunRequest:
    return ProfileRunRequest(
        accumulator=0,
        code_pointer=0,
        data_pointer=0,
        input_bytes=(),
        input_consumed=0,
        memory=memory if memory is not None else array("I", [0]) * SMALL_WORDS,
        output_bytes=(),
        step_budget=1,
        termination=StepTermination.NONE,
    )


def _invalid(call: Callable[[], object]) -> str:
    try:
        _ = call()
    except InvalidPrimitiveBatchError as error:
        return str(error)
    message = "expected InvalidPrimitiveBatchError"
    raise AssertionError(message)
