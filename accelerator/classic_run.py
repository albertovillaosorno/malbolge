# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Hardware-neutral resident classic bounded-run accelerator contract."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Final

from accelerator.classic_step import StepTermination
from accelerator.exact_primitives import InvalidPrimitiveBatchError
from accelerator.exact_primitives import MAX_WORD

MEMORY_WORDS: Final = 59_049
MAX_U32: Final = 0xFFFF_FFFF
MAX_BYTE: Final = 0xFF
STATE_WORDS: Final = 16


class RunError(IntEnum):
    """Stable resident-run failure code."""

    NONE = 0
    INVALID_ENCRYPTION = 1
    INVALID_REQUEST = 2


class RunStatus(IntEnum):
    """Stable bounded-run result category."""

    BUDGET_EXHAUSTED = 0
    TERMINATED = 1
    ERROR = 2


@dataclass(frozen=True, slots=True)
class ClassicRunRequest:
    """One complete classic VM state plus a bounded execution budget."""

    accumulator: int
    code_pointer: int
    data_pointer: int
    input_bytes: tuple[int, ...]
    input_consumed: int
    memory: tuple[int, ...]
    output_bytes: tuple[int, ...]
    step_budget: int
    termination: StepTermination | int = StepTermination.NONE

    def validated(self) -> ClassicRunRequest:
        """Validate a complete resumable specification-mode classic state.

        Returns:
            The unchanged request after validation succeeds.

        """
        _validate_request_metadata(self)
        _validate_memory(self.memory)
        return self


def validate_classic_run_requests(
    requests: tuple[ClassicRunRequest, ...],
) -> tuple[ClassicRunRequest, ...]:
    """Validate one batch while scanning shared immutable memory only once.

    Returns:
        The unchanged request tuple after complete validation.

    """
    validated_memories: dict[int, tuple[int, ...]] = {}
    for request in requests:
        _validate_request_metadata(request)
        memory = request.memory
        identity = id(memory)
        known = validated_memories.get(identity)
        if known is memory:
            continue
        _validate_memory(memory)
        validated_memories[identity] = memory
    return requests


@dataclass(frozen=True, slots=True)
class ClassicRunResult:
    """Complete resident classic VM result after one bounded GPU run."""

    accumulator: int
    code_pointer: int
    data_pointer: int
    error: RunError
    error_pointer: int
    error_value: int
    input_consumed: int
    memory: tuple[int, ...]
    output_bytes: tuple[int, ...]
    status: RunStatus
    steps: int
    termination: StepTermination


def _validate_memory(memory: tuple[int, ...]) -> None:
    if len(memory) != MEMORY_WORDS:
        message = (
            f"resident classic memory requires {MEMORY_WORDS} words, "
            f"got {len(memory)}"
        )
        raise InvalidPrimitiveBatchError(message)
    _validate_words(memory, "memory value")


def _validate_request_metadata(request: ClassicRunRequest) -> None:
    _check_word(request.accumulator, "accumulator")
    _check_word(request.code_pointer, "code pointer")
    _check_word(request.data_pointer, "data pointer")
    _check_u32(request.step_budget, "step budget")
    _validate_termination(request.termination)
    _validate_bytes(request.input_bytes, "input")
    _validate_bytes(request.output_bytes, "output")
    if not 0 <= request.input_consumed <= len(request.input_bytes):
        message = (
            "input consumed exceeds resident input length: "
            f"{request.input_consumed} > {len(request.input_bytes)}"
        )
        raise InvalidPrimitiveBatchError(message)
    _check_u32(len(request.input_bytes), "input length")
    _check_u32(len(request.output_bytes), "output length")
    _check_u32(
        len(request.output_bytes) + request.step_budget,
        "maximum output capacity",
    )


def _check_u32(value: int, label: str) -> None:
    if not 0 <= value <= MAX_U32:
        message = f"{label} outside unsigned 32-bit domain: {value}"
        raise InvalidPrimitiveBatchError(message)


def _check_word(value: int, label: str) -> None:
    if not 0 <= value <= MAX_WORD:
        message = f"{label} outside classic word domain: {value}"
        raise InvalidPrimitiveBatchError(message)


def _validate_bytes(values: tuple[int, ...], label: str) -> None:
    if not values:
        return
    minimum = min(values)
    maximum = max(values)
    if minimum < 0:
        message = f"{label} byte outside byte domain: {minimum}"
        raise InvalidPrimitiveBatchError(message)
    if maximum > MAX_BYTE:
        message = f"{label} byte outside byte domain: {maximum}"
        raise InvalidPrimitiveBatchError(message)


def _validate_words(values: tuple[int, ...], label: str) -> None:
    minimum = min(values)
    maximum = max(values)
    if minimum < 0:
        _check_word(minimum, label)
    if maximum > MAX_WORD:
        _check_word(maximum, label)


def _validate_termination(termination: StepTermination | int) -> None:
    if type(termination) is not StepTermination:
        message = f"invalid resident termination: {termination!r}"
        raise InvalidPrimitiveBatchError(message)
