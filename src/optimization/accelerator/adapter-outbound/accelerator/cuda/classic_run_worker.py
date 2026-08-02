# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
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
#   - Binary process worker for resident CUDA classic bounded execution.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Binary process worker for resident CUDA classic bounded execution."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
import sys
from typing import Final
from typing import TYPE_CHECKING

from accelerator.classic_run import ClassicRunRequest
from accelerator.classic_run import MEMORY_WORDS
from accelerator.classic_step import StepTermination
from accelerator.cuda.classic_run import CudaClassicRunAdapter
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import InvalidPrimitiveBatchError

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.classic_run import ClassicRunResult

MAGIC: Final = b"MBRUN1\x00\x00"
RESPONSE_RESULTS: Final = 0
RESPONSE_UNAVAILABLE: Final = 1
U32_BYTES: Final = 4
LITTLE_ENDIAN: Final = "little"


class ClassicRunProtocolError(ValueError):
    """Malformed resident classic-run process protocol input."""


@dataclass(slots=True)
class _BinaryReader:
    data: bytes
    offset: int = 0

    def take(self, byte_count: int) -> bytes:
        end = self.offset + byte_count
        if end > len(self.data):
            message = "truncated resident protocol payload"
            raise ClassicRunProtocolError(message)
        value = self.data[self.offset : end]
        self.offset = end
        return value

    def u32(self) -> int:
        return int.from_bytes(self.take(U32_BYTES), LITTLE_ENDIAN)

    def words(self, count: int) -> tuple[int, ...]:
        return _words_from_bytes(self.take(count * U32_BYTES), count)

    def finish(self) -> None:
        if self.offset != len(self.data):
            message = "trailing resident protocol bytes"
            raise ClassicRunProtocolError(message)


@dataclass(frozen=True, slots=True)
class _RequestHeader:
    accumulator: int
    code_pointer: int
    data_pointer: int
    input_len: int
    input_consumed: int
    output_len: int
    step_budget: int
    termination: int

    @classmethod
    def read(cls, reader: _BinaryReader) -> _RequestHeader:
        """Read the fixed-width scalar request prefix.

        Returns:
            One typed request header in protocol field order.

        """
        return cls(
            accumulator=reader.u32(),
            code_pointer=reader.u32(),
            data_pointer=reader.u32(),
            input_len=reader.u32(),
            input_consumed=reader.u32(),
            output_len=reader.u32(),
            step_budget=reader.u32(),
            termination=reader.u32(),
        )


def main() -> int:
    """Read one binary request batch and emit complete binary VM results.

    Returns:
        Zero for successful execution or an unavailable optional CUDA backend;
        one for malformed input or accelerator execution failure.

    """
    try:
        requests = _parse_requests(sys.stdin.buffer.read())
        with CudaClassicRunAdapter() as adapter:
            results = adapter.evaluate(requests)
    except AcceleratorUnavailableError as error:
        _ = sys.stdout.buffer.write(_response_prefix(RESPONSE_UNAVAILABLE, 0))
        _ = sys.stderr.write(f"MBRUN1 UNAVAILABLE {error}\n")
        return 0
    except (
        AcceleratorExecutionError,
        ClassicRunProtocolError,
        InvalidPrimitiveBatchError,
        ValueError,
    ) as error:
        _ = sys.stderr.write(f"MBRUN1 INVALID {error}\n")
        return 1
    output = sys.stdout.buffer
    _ = output.write(_response_prefix(RESPONSE_RESULTS, len(results)))
    for result in results:
        _write_result(output.write, result)
    return 0


def _parse_requests(data: bytes) -> tuple[ClassicRunRequest, ...]:
    reader = _BinaryReader(data)
    if reader.take(len(MAGIC)) != MAGIC:
        message = "invalid resident protocol magic"
        raise ClassicRunProtocolError(message)
    count = reader.u32()
    requests = tuple(_parse_request(reader) for _item in range(count))
    reader.finish()
    return requests


def _parse_request(reader: _BinaryReader) -> ClassicRunRequest:
    header = _RequestHeader.read(reader)
    memory = reader.words(MEMORY_WORDS)
    input_bytes = tuple(reader.take(header.input_len))
    output_bytes = tuple(reader.take(header.output_len))
    try:
        termination = StepTermination(header.termination)
    except ValueError as error:
        message = f"invalid resident termination: {header.termination}"
        raise ClassicRunProtocolError(message) from error
    return ClassicRunRequest(
        accumulator=header.accumulator,
        code_pointer=header.code_pointer,
        data_pointer=header.data_pointer,
        input_bytes=input_bytes,
        input_consumed=header.input_consumed,
        memory=memory,
        output_bytes=output_bytes,
        step_budget=header.step_budget,
        termination=termination,
    ).validated()


def _response_prefix(kind: int, count: int) -> bytes:
    return MAGIC + _u32_bytes(kind, count)


def _write_result(
    write: Callable[[bytes], int],
    result: ClassicRunResult,
) -> None:
    _ = write(
        _u32_bytes(
            int(result.status),
            int(result.error),
            result.accumulator,
            result.code_pointer,
            result.data_pointer,
            result.input_consumed,
            len(result.output_bytes),
            int(result.termination),
            result.error_pointer,
            result.error_value,
            result.steps,
        )
    )
    _ = write(_word_bytes(result.memory))
    _ = write(bytes(result.output_bytes))


def _u32_bytes(*values: int) -> bytes:
    return b"".join(
        value.to_bytes(U32_BYTES, LITTLE_ENDIAN) for value in values
    )


def _words_from_bytes(data: bytes, count: int) -> tuple[int, ...]:
    expected = count * U32_BYTES
    if len(data) != expected:
        message = "resident word payload has wrong width"
        raise ClassicRunProtocolError(message)
    words = array("I")
    words.frombytes(data)
    if words.itemsize != U32_BYTES:
        message = "host unsigned int is not 32 bits"
        raise ClassicRunProtocolError(message)
    if sys.byteorder != LITTLE_ENDIAN:
        words.byteswap()
    return tuple(words)


def _word_bytes(values: tuple[int, ...]) -> bytes:
    words = array("I", values)
    if words.itemsize != U32_BYTES:
        message = "host unsigned int is not 32 bits"
        raise ClassicRunProtocolError(message)
    if sys.byteorder != LITTLE_ENDIAN:
        words.byteswap()
    return words.tobytes()


if __name__ == "__main__":
    raise SystemExit(main())
