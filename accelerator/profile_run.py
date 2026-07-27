# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Hardware-neutral scalable resident profile-run accelerator contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from typing import TYPE_CHECKING

from accelerator.classic_run import MAX_U32
from accelerator.classic_step import StepTermination
from accelerator.exact_primitives import InvalidPrimitiveBatchError

if TYPE_CHECKING:
    from array import array

    from accelerator.classic_run import RunError
    from accelerator.classic_run import RunStatus

MAX_BYTE: Final = 0xFF
MAX_GRAPHICAL_WORD: Final = 126
MAX_PROFILE_TRITS: Final = 20
TERNARY_RADIX: Final = 3
WORD_BYTES: Final = 4
WORD_TYPECODE: Final = "I"


@dataclass(frozen=True, slots=True)
class ProfileRunGeometry:
    """Exact single-word-modular profile geometry for resident execution."""

    eof_word: int
    memory_words: int
    word_modulus: int
    word_trits: int

    def validated(self) -> ProfileRunGeometry:
        """Validate the profile geometry supported by the resident kernel.

        Returns:
            The unchanged geometry after validation.

        """
        expected = _validated_ternary_modulus(self.word_trits)
        _validate_geometry_shape(self, expected)
        return self


@dataclass(frozen=True, slots=True)
class ProfileRunRequest:
    """One complete scalable profile VM state plus a bounded step budget."""

    accumulator: int
    code_pointer: int
    data_pointer: int
    input_bytes: tuple[int, ...]
    input_consumed: int
    memory: array[int]
    output_bytes: tuple[int, ...]
    step_budget: int
    termination: StepTermination | int = StepTermination.NONE


@dataclass(frozen=True, slots=True)
class ProfileRunResult:
    """Complete scalable resident profile result after one GPU run."""

    accumulator: int
    code_pointer: int
    data_pointer: int
    error: RunError
    error_pointer: int
    error_value: int
    input_consumed: int
    memory: array[int]
    output_bytes: tuple[int, ...]
    status: RunStatus
    steps: int
    termination: StepTermination


def validate_profile_run_requests(
    geometry: ProfileRunGeometry,
    requests: tuple[ProfileRunRequest, ...],
) -> tuple[ProfileRunRequest, ...]:
    """Validate one homogeneous scalable batch and shared memories once.

    Returns:
        The unchanged request tuple after complete validation.

    """
    admitted = geometry.validated()
    validated_memories: dict[int, array[int]] = {}
    for request in requests:
        _validate_request_metadata(admitted, request)
        memory = request.memory
        identity = id(memory)
        known = validated_memories.get(identity)
        if known is memory:
            continue
        _validate_memory(admitted, memory)
        validated_memories[identity] = memory
    return requests


def _validated_ternary_modulus(word_trits: int) -> int:
    if not 1 <= word_trits <= MAX_PROFILE_TRITS:
        message = (
            f"resident profile trits outside supported domain: {word_trits}"
        )
        raise InvalidPrimitiveBatchError(message)
    expected = 1
    trit = 0
    while trit < word_trits:
        expected *= TERNARY_RADIX
        trit += 1
    if expected <= MAX_GRAPHICAL_WORD:
        message = (
            "resident profile word domain cannot represent graphical "
            f"encryption values: {expected} <= {MAX_GRAPHICAL_WORD}"
        )
        raise InvalidPrimitiveBatchError(message)
    if expected > MAX_U32:
        message = f"resident profile modulus exceeds u32: {expected}"
        raise InvalidPrimitiveBatchError(message)
    return expected


def _validate_geometry_shape(
    geometry: ProfileRunGeometry,
    expected_modulus: int,
) -> None:
    if geometry.word_modulus != expected_modulus:
        message = (
            f"resident profile modulus {geometry.word_modulus} != "
            f"3^{geometry.word_trits} ({expected_modulus})"
        )
        raise InvalidPrimitiveBatchError(message)
    if geometry.memory_words != geometry.word_modulus:
        message = (
            "resident profile requires single-word-modular memory: "
            f"{geometry.memory_words} != {geometry.word_modulus}"
        )
        raise InvalidPrimitiveBatchError(message)
    if geometry.eof_word != geometry.word_modulus - 1:
        message = (
            f"resident profile EOF {geometry.eof_word} != "
            f"modulus-1 ({geometry.word_modulus - 1})"
        )
        raise InvalidPrimitiveBatchError(message)


def _validate_registers(
    geometry: ProfileRunGeometry,
    request: ProfileRunRequest,
) -> None:
    for value, label in (
        (request.accumulator, "accumulator"),
        (request.code_pointer, "code pointer"),
        (request.data_pointer, "data pointer"),
    ):
        if not 0 <= value < geometry.word_modulus:
            message = f"{label} outside profile word domain: {value}"
            raise InvalidPrimitiveBatchError(message)


def _validate_step_metadata(request: ProfileRunRequest) -> None:
    if not 0 <= request.step_budget <= MAX_U32:
        message = (
            f"step budget outside unsigned 32-bit domain: {request.step_budget}"
        )
        raise InvalidPrimitiveBatchError(message)
    if type(request.termination) is not StepTermination:
        message = f"invalid resident termination: {request.termination!r}"
        raise InvalidPrimitiveBatchError(message)


def _validate_io_metadata(request: ProfileRunRequest) -> None:
    _validate_bytes(request.input_bytes, "input")
    _validate_bytes(request.output_bytes, "output")
    if not 0 <= request.input_consumed <= len(request.input_bytes):
        message = (
            "input consumed exceeds resident input length: "
            f"{request.input_consumed} > {len(request.input_bytes)}"
        )
        raise InvalidPrimitiveBatchError(message)
    for value, label in (
        (len(request.input_bytes), "input length"),
        (len(request.output_bytes), "output length"),
        (
            len(request.output_bytes) + request.step_budget,
            "maximum output capacity",
        ),
    ):
        if value > MAX_U32:
            message = f"{label} outside unsigned 32-bit domain: {value}"
            raise InvalidPrimitiveBatchError(message)


def _validate_memory(
    geometry: ProfileRunGeometry,
    memory: array[int],
) -> None:
    if memory.typecode != WORD_TYPECODE or memory.itemsize != WORD_BYTES:
        message = (
            "resident profile memory must use contiguous 32-bit array('I')"
        )
        raise InvalidPrimitiveBatchError(message)
    if len(memory) != geometry.memory_words:
        message = (
            f"resident profile memory requires {geometry.memory_words} words, "
            f"got {len(memory)}"
        )
        raise InvalidPrimitiveBatchError(message)
    if not memory:
        return
    maximum = max(memory)
    if maximum >= geometry.word_modulus:
        message = f"profile memory value outside word domain: {maximum}"
        raise InvalidPrimitiveBatchError(message)


def _validate_request_metadata(
    geometry: ProfileRunGeometry,
    request: ProfileRunRequest,
) -> None:
    _validate_registers(geometry, request)
    _validate_step_metadata(request)
    _validate_io_metadata(request)


def _validate_bytes(values: tuple[int, ...], label: str) -> None:
    if not values:
        return
    minimum = min(values)
    maximum = max(values)
    if minimum < 0 or maximum > MAX_BYTE:
        rejected = minimum if minimum < 0 else maximum
        message = f"{label} byte outside byte domain: {rejected}"
        raise InvalidPrimitiveBatchError(message)
