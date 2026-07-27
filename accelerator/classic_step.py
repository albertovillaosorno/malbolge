# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Hardware-neutral compact classic one-step accelerator contract."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Final

from accelerator.exact_primitives import InvalidPrimitiveBatchError
from accelerator.exact_primitives import MAX_WORD

MAX_MEMORY_SLOTS: Final = 4
REQUEST_WORDS: Final = 20
RESULT_WORDS: Final = 26
MAX_U32: Final = 0xFFFF_FFFF
MAX_BYTE: Final = 0xFF


class StepError(IntEnum):
    """Stable compact transition failure code."""

    NONE = 0
    INVALID_ENCRYPTION = 1
    INVALID_REQUEST = 2


class StepInputKind(IntEnum):
    """Committed input observation for one transition."""

    NONE = 0
    BYTE = 1
    END_OF_INPUT = 2


class StepStatus(IntEnum):
    """Stable compact transition result category."""

    CONTINUED = 0
    TERMINATED = 1
    ERROR = 2


class StepTermination(IntEnum):
    """Stable compact classic termination reason."""

    NONE = 0
    HALT = 1
    NON_GRAPHICAL = 2


@dataclass(frozen=True, slots=True)
class StepMemoryCell:
    """One original guest memory cell available to a compact transition."""

    address: int
    value: int

    def validated(self) -> StepMemoryCell:
        """Validate address/value against the classic word domain.

        Returns:
            The unchanged cell after successful validation.

        """
        _check_word(self.address, "memory address")
        _check_word(self.value, "memory value")
        return self


@dataclass(frozen=True, slots=True)
class ClassicStepRequest:
    """One specification-mode classic transition over a compact memory view."""

    accumulator: int
    code_pointer: int
    data_pointer: int
    input_byte: int | None
    input_consumed: int
    memory: tuple[StepMemoryCell, ...]
    output_len: int
    termination: StepTermination | int = StepTermination.NONE

    def to_words(self) -> tuple[int, ...]:
        """Encode the fixed-width accelerator request representation.

        Returns:
            Exactly [`REQUEST_WORDS`] unsigned 32-bit values.

        """
        validated = self.validated()
        words = [
            validated.accumulator,
            validated.code_pointer,
            validated.data_pointer,
            validated.input_consumed,
            validated.output_len,
            int(validated.termination),
            int(validated.input_byte is not None),
            validated.input_byte or 0,
        ]
        for index in range(MAX_MEMORY_SLOTS):
            if index < len(validated.memory):
                cell = validated.memory[index]
                words.extend((1, cell.address, cell.value))
            else:
                words.extend((0, 0, 0))
        return tuple(words)

    def validated(self) -> ClassicStepRequest:
        """Validate deterministic compact-step request invariants.

        Returns:
            The unchanged request after validation.

        """
        _check_word(self.accumulator, "accumulator")
        _check_word(self.code_pointer, "code pointer")
        _check_word(self.data_pointer, "data pointer")
        _check_u32(self.input_consumed, "input consumed")
        _check_u32(self.output_len, "output length")
        _validate_input(self.input_byte)
        _validate_termination(self.termination)
        _validate_memory(self.memory, self.code_pointer, self.termination)
        return self


@dataclass(frozen=True, slots=True)
class StepMemoryWrite:
    """One actual final changed guest memory cell."""

    address: int
    after: int
    before: int


@dataclass(frozen=True, slots=True)
class ClassicStepResult:
    """Exact compact projection of one classic `StepTrace`."""

    accumulator: int
    code_pointer: int
    data_pointer: int
    data_write: StepMemoryWrite | None
    decoded: int | None
    encryption_write: StepMemoryWrite | None
    error: StepError
    error_pointer: int
    error_value: int
    fetched: int | None
    input_consumed: int
    input_kind: StepInputKind
    input_value: int
    output_len: int
    output_value: int | None
    status: StepStatus
    termination: StepTermination

    @classmethod
    def from_words(cls, words: tuple[int, ...]) -> ClassicStepResult:
        """Decode one fixed-width GPU result row.

        Returns:
            Typed compact transition result.

        Raises:
            InvalidPrimitiveBatchError: If the row width is not canonical.

        """
        if len(words) != RESULT_WORDS:
            message = f"classic step result requires {RESULT_WORDS} words"
            raise InvalidPrimitiveBatchError(message)
        return cls(
            accumulator=words[2],
            code_pointer=words[3],
            data_pointer=words[4],
            data_write=_write(words, 16),
            decoded=words[11] if words[10] else None,
            encryption_write=_write(words, 20),
            error=StepError(words[1]),
            error_pointer=words[24],
            error_value=words[25],
            fetched=words[9] if words[8] else None,
            input_consumed=words[5],
            input_kind=StepInputKind(words[12]),
            input_value=words[13],
            output_len=words[6],
            output_value=words[15] if words[14] else None,
            status=StepStatus(words[0]),
            termination=StepTermination(words[7]),
        )

    def to_words(self) -> tuple[int, ...]:
        """Encode one result for the versioned process protocol.

        Returns:
            Exactly [`RESULT_WORDS`] unsigned 32-bit values.

        """
        words = [
            int(self.status),
            int(self.error),
            self.accumulator,
            self.code_pointer,
            self.data_pointer,
            self.input_consumed,
            self.output_len,
            int(self.termination),
            int(self.fetched is not None),
            self.fetched or 0,
            int(self.decoded is not None),
            self.decoded or 0,
            int(self.input_kind),
            self.input_value,
            int(self.output_value is not None),
            self.output_value or 0,
        ]
        words.extend(_write_words(self.data_write))
        words.extend(_write_words(self.encryption_write))
        words.extend((self.error_pointer, self.error_value))
        return tuple(words)


def _check_u32(value: int, label: str) -> None:
    if not 0 <= value <= MAX_U32:
        message = f"{label} outside unsigned 32-bit domain: {value}"
        raise InvalidPrimitiveBatchError(message)


def _check_word(value: int, label: str) -> None:
    if not 0 <= value <= MAX_WORD:
        message = f"{label} outside classic word domain: {value}"
        raise InvalidPrimitiveBatchError(message)


def _validate_input(input_byte: int | None) -> None:
    if input_byte is not None and not 0 <= input_byte <= MAX_BYTE:
        message = f"input byte outside byte domain: {input_byte}"
        raise InvalidPrimitiveBatchError(message)


def _validate_termination(termination: StepTermination | int) -> None:
    if type(termination) is not StepTermination:
        message = f"invalid compact termination: {termination!r}"
        raise InvalidPrimitiveBatchError(message)


def _validate_memory(
    memory: tuple[StepMemoryCell, ...],
    code_pointer: int,
    termination: StepTermination | int,
) -> None:
    if len(memory) > MAX_MEMORY_SLOTS:
        message = f"compact step exceeds {MAX_MEMORY_SLOTS} memory slots"
        raise InvalidPrimitiveBatchError(message)
    addresses: set[int] = set()
    for cell in memory:
        _ = cell.validated()
        if cell.address in addresses:
            message = f"duplicate compact memory address: {cell.address}"
            raise InvalidPrimitiveBatchError(message)
        addresses.add(cell.address)
    if termination is StepTermination.NONE and code_pointer not in addresses:
        message = "live compact step is missing its code-pointer cell"
        raise InvalidPrimitiveBatchError(message)


def _write(words: tuple[int, ...], offset: int) -> StepMemoryWrite | None:
    if not words[offset]:
        return None
    return StepMemoryWrite(
        address=words[offset + 1],
        before=words[offset + 2],
        after=words[offset + 3],
    )


def _write_words(write: StepMemoryWrite | None) -> tuple[int, int, int, int]:
    if write is None:
        return (0, 0, 0, 0)
    return (1, write.address, write.before, write.after)
