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
#   - Hardware-neutral scalable resident profile-run accelerator contract.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Hardware-neutral scalable resident profile-run accelerator contract."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from typing import Final
from typing import TYPE_CHECKING
from typing import final

from accelerator.classic_run import MAX_U32
from accelerator.classic_step import StepTermination
from accelerator.exact_primitives import InvalidPrimitiveBatchError

if TYPE_CHECKING:
    from accelerator.classic_run import RunError
    from accelerator.classic_run import RunStatus

MAX_BYTE: Final = 0xFF
MAX_GRAPHICAL_WORD: Final = 126
PROFILE_IO_INSTRUCTIONS: Final = frozenset((ord("<"), ord("/")))
TERNARY_RADIX: Final = 3
WORD_BYTES: Final = 4
WORD_TYPECODE: Final = "I"


def _maximum_ternary_trits(limit: int) -> int:
    word_trits = 0
    modulus = 1
    while modulus <= limit // TERNARY_RADIX:
        modulus *= TERNARY_RADIX
        word_trits += 1
    return word_trits


MAX_PROFILE_TRITS: Final = _maximum_ternary_trits(MAX_U32)


@dataclass(frozen=True, slots=True)
class ProfileRunGeometry:
    """Exact single-word-modular profile geometry for resident execution."""

    eof_word: int
    input_instruction: int
    memory_words: int
    output_instruction: int
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


@final
class ProfileMemoryImage:
    """Owned immutable-by-contract profile memory validated for one geometry."""

    __slots__ = ("__geometry", "__storage")

    def __init__(
        self,
        geometry: ProfileRunGeometry,
        memory: array[int],
    ) -> None:
        """Validate and own an isolated copy of one complete memory image."""
        admitted = geometry.validated()
        _validate_memory(admitted, memory)
        self.__geometry = admitted
        self.__storage = array(WORD_TYPECODE, memory)

    def __len__(self) -> int:
        """Return the exact number of profile words in this image.

        Returns:
            Exact geometry-bound word count.

        """
        return self.__geometry.memory_words

    @property
    def geometry(self) -> ProfileRunGeometry:
        """Geometry whose word-domain validation this image carries."""
        return self.__geometry

    def copy_words(self) -> array[int]:
        """Materialize one independent compact 32-bit mutable word array.

        Returns:
            Fresh compact words with no mutable alias to this image.

        """
        return array(WORD_TYPECODE, self.__storage)

    def repeat_words(self, count: int) -> array[int]:
        """Materialize independent repeated copies of this validated image.

        Returns:
            Fresh compact repeated words with no alias to this image.

        Raises:
            ValueError: If `count` is not a nonnegative integer.

        """
        if type(count) is not int or count < 0:
            message = (
                "profile memory repeat count must be a nonnegative integer: "
                f"{count!r}"
            )
            raise ValueError(message)
        return self.__storage * count

    def words(self) -> memoryview:
        """Return a read-only zero-copy view for inspection and bulk copying.

        Returns:
            Read-only native 32-bit view over the validated owned storage.

        """
        return memoryview(self.__storage).toreadonly()


@dataclass(frozen=True, slots=True)
class ProfileRunRequest:
    """One complete scalable profile VM state plus a bounded step budget."""

    accumulator: int
    code_pointer: int
    data_pointer: int
    input_bytes: tuple[int, ...]
    input_consumed: int
    memory: array[int] | ProfileMemoryImage
    output_bytes: tuple[int, ...]
    step_budget: int
    termination: StepTermination | int = StepTermination.NONE


@dataclass(frozen=True, slots=True)
class ProfileRunObservation:
    """Compact host observation of one resident scalable profile VM."""

    accumulator: int
    code_pointer: int
    data_pointer: int
    error: RunError
    error_pointer: int
    error_value: int
    input_consumed: int
    output_length: int
    status: RunStatus
    steps: int
    termination: StepTermination


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
        if isinstance(memory, ProfileMemoryImage):
            _validate_memory_image(admitted, memory)
            continue
        identity = id(memory)
        known = validated_memories.get(identity)
        if known is memory:
            continue
        _validate_memory(admitted, memory)
        validated_memories[identity] = memory
    return requests


def _validated_ternary_modulus(word_trits: int) -> int:
    if type(word_trits) is not int or not 1 <= word_trits <= MAX_PROFILE_TRITS:
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


def _validate_geometry_integers(geometry: ProfileRunGeometry) -> None:
    for value, label in (
        (geometry.eof_word, "resident profile EOF"),
        (geometry.input_instruction, "resident profile input instruction"),
        (geometry.memory_words, "resident profile memory words"),
        (geometry.output_instruction, "resident profile output instruction"),
        (geometry.word_modulus, "resident profile modulus"),
    ):
        if type(value) is not int:
            message = f"{label} must be an exact integer: {value!r}"
            raise InvalidPrimitiveBatchError(message)


def _validate_geometry_shape(
    geometry: ProfileRunGeometry,
    expected_modulus: int,
) -> None:
    _validate_geometry_integers(geometry)
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
    _validate_io_instructions(geometry)


def _validate_io_instructions(geometry: ProfileRunGeometry) -> None:
    observed = frozenset((
        geometry.input_instruction,
        geometry.output_instruction,
    ))
    if observed != PROFILE_IO_INSTRUCTIONS:
        message = (
            "resident profile I/O instructions must assign '<' and '/' "
            "exactly once"
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
        if type(value) is not int or not 0 <= value < geometry.word_modulus:
            message = f"{label} outside profile word domain: {value}"
            raise InvalidPrimitiveBatchError(message)


def _validate_step_metadata(request: ProfileRunRequest) -> None:
    if (
        type(request.step_budget) is not int
        or not 0 <= request.step_budget <= MAX_U32
    ):
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
    if type(request.input_consumed) is not int:
        message = (
            "input consumed must be an exact integer: "
            f"{request.input_consumed!r}"
        )
        raise InvalidPrimitiveBatchError(message)
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


def _validate_memory_image(
    geometry: ProfileRunGeometry,
    memory: ProfileMemoryImage,
) -> None:
    if memory.geometry != geometry:
        message = (
            "resident profile memory image geometry mismatch: "
            f"{memory.geometry!r} != {geometry!r}"
        )
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
    for value in values:
        if type(value) is not int:
            message = f"{label} byte outside byte domain: {value!r}"
            raise InvalidPrimitiveBatchError(message)
    minimum = min(values)
    maximum = max(values)
    if minimum < 0 or maximum > MAX_BYTE:
        rejected = minimum if minimum < 0 else maximum
        message = f"{label} byte outside byte domain: {rejected}"
        raise InvalidPrimitiveBatchError(message)
