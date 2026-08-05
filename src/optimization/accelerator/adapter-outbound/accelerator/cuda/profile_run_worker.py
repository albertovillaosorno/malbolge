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
#   - Binary process worker for scalable resident CUDA profile execution.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Binary process worker for scalable resident CUDA profile execution."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
import sys
from typing import Final
from typing import TYPE_CHECKING

from accelerator.classic_step import StepTermination
from accelerator.cuda.profile_run import CudaProfileRunAdapter
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import InvalidPrimitiveBatchError
from accelerator.profile_run import ProfileRunGeometry
from accelerator.profile_run import ProfileRunRequest

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.profile_run import ProfileRunResult

MAGIC: Final = b"MBPRN2\x00\x00"
RESPONSE_RESULTS: Final = 0
RESPONSE_UNAVAILABLE: Final = 1
U32_BYTES: Final = 4
LITTLE_ENDIAN: Final = "little"
WORD_TYPECODE: Final = "I"


class ProfileRunProtocolError(ValueError):
    """Malformed scalable resident profile-run process protocol input."""


@dataclass(slots=True)
class _BinaryReader:
    data: memoryview
    offset: int = 0

    def finish(self) -> None:
        if self.offset != len(self.data):
            message = "trailing scalable resident protocol bytes"
            raise ProfileRunProtocolError(message)

    def take(self, byte_count: int) -> memoryview:
        end = self.offset + byte_count
        if end > len(self.data):
            message = "truncated scalable resident protocol payload"
            raise ProfileRunProtocolError(message)
        value = self.data[self.offset : end]
        self.offset = end
        return value

    def u32(self) -> int:
        return int.from_bytes(self.take(U32_BYTES), LITTLE_ENDIAN)

    def words(self, count: int) -> array[int]:
        return _words_from_view(self.take(count * U32_BYTES), count)


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
    """Read one homogeneous profile batch and emit complete binary results.

    Returns:
        Zero for successful execution or unavailable optional CUDA; one for
        malformed input or accelerator execution failure.

    """
    try:
        geometry, requests = _parse_requests(sys.stdin.buffer.read())
        with CudaProfileRunAdapter(geometry) as adapter:
            results = adapter.evaluate(requests)
    except AcceleratorUnavailableError as error:
        _ = sys.stdout.buffer.write(_response_prefix(RESPONSE_UNAVAILABLE, 0))
        _ = sys.stderr.write(f"MBPRN2 UNAVAILABLE {error}\n")
        return 0
    except (
        AcceleratorExecutionError,
        InvalidPrimitiveBatchError,
        ProfileRunProtocolError,
        ValueError,
    ) as error:
        _ = sys.stderr.write(f"MBPRN2 INVALID {error}\n")
        return 1
    output = sys.stdout.buffer
    _ = output.write(_response_prefix(RESPONSE_RESULTS, len(results)))
    for result in results:
        _write_result(output.write, result)
    return 0


def _parse_requests(
    data: bytes,
) -> tuple[ProfileRunGeometry, tuple[ProfileRunRequest, ...]]:
    reader = _BinaryReader(memoryview(data))
    if bytes(reader.take(len(MAGIC))) != MAGIC:
        message = "invalid scalable resident protocol magic"
        raise ProfileRunProtocolError(message)
    geometry = ProfileRunGeometry(
        eof_word=reader.u32(),
        input_instruction=reader.u32(),
        memory_words=reader.u32(),
        output_instruction=reader.u32(),
        word_modulus=reader.u32(),
        word_trits=reader.u32(),
    ).validated()
    count = reader.u32()
    requests = tuple(_parse_request(reader, geometry) for _item in range(count))
    reader.finish()
    return geometry, requests


def _parse_request(
    reader: _BinaryReader,
    geometry: ProfileRunGeometry,
) -> ProfileRunRequest:
    header = _RequestHeader.read(reader)
    memory = reader.words(geometry.memory_words)
    input_bytes = tuple(reader.take(header.input_len))
    output_bytes = tuple(reader.take(header.output_len))
    try:
        termination = StepTermination(header.termination)
    except ValueError as error:
        message = f"invalid resident termination: {header.termination}"
        raise ProfileRunProtocolError(message) from error
    return ProfileRunRequest(
        accumulator=header.accumulator,
        code_pointer=header.code_pointer,
        data_pointer=header.data_pointer,
        input_bytes=input_bytes,
        input_consumed=header.input_consumed,
        memory=memory,
        output_bytes=output_bytes,
        step_budget=header.step_budget,
        termination=termination,
    )


def _response_prefix(kind: int, count: int) -> bytes:
    return MAGIC + _u32_bytes(kind, count)


def _write_result(
    write: Callable[[bytes], int],
    result: ProfileRunResult,
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


def _words_from_view(data: memoryview, count: int) -> array[int]:
    expected = count * U32_BYTES
    if len(data) != expected:
        message = "scalable resident word payload has wrong width"
        raise ProfileRunProtocolError(message)
    words = array(WORD_TYPECODE)
    words.frombytes(data)
    if words.itemsize != U32_BYTES:
        message = "host unsigned int is not 32 bits"
        raise ProfileRunProtocolError(message)
    if sys.byteorder != LITTLE_ENDIAN:
        words.byteswap()
    return words


def _word_bytes(values: array[int]) -> bytes:
    if values.typecode != WORD_TYPECODE or values.itemsize != U32_BYTES:
        message = "scalable resident result memory is not 32-bit unsigned"
        raise ProfileRunProtocolError(message)
    if sys.byteorder == LITTLE_ENDIAN:
        return values.tobytes()
    copy = array(WORD_TYPECODE, values)
    copy.byteswap()
    return copy.tobytes()


if __name__ == "__main__":
    raise SystemExit(main())
