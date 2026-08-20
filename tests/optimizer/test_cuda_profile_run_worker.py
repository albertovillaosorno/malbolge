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
#   - Scalable resident CUDA worker binary-input streaming regressions.
# - Must-Not:
#   - Load CUDA, execute kernels, or treat the worker as semantic authority.
# - Allows:
#   - Inputs: small synthetic binary protocol payloads.
#   - Outputs: exact decoded requests and malformed-input diagnostics.
#   - Side effects: in-memory byte-stream reads only.
# - Split-When:
#   - Split when the worker protocol gains independently versioned framing.
# - Merge-When:
#   - Merge when another suite owns this exact worker input boundary.
# - Summary:
#   - Proves profile worker input is parsed incrementally and fail closed.
# - Description:
#   - Exercises the binary parser without accelerator hardware.
# - Usage:
#   - Collected with optimizer tests on every host.
# - Defaults:
#   - Five-trit geometry keeps the regression deliberately small.
#

"""Scalable resident CUDA worker binary-input streaming regressions."""

from __future__ import annotations

from array import array
from io import BytesIO
from typing import Final
from typing import override

from accelerator.cuda import profile_run_worker
import pytest

TRITS: Final = 5
WORDS: Final = 243
EOF_WORD: Final = WORDS - 1
INPUT_INSTRUCTION: Final = ord("<")
OUTPUT_INSTRUCTION: Final = ord("/")
ACCUMULATOR: Final = 7
CODE_POINTER: Final = 2
DATA_POINTER: Final = 3
STEP_BUDGET: Final = 9

parse_requests = profile_run_worker.parse_requests


class _ChunkedStream(BytesIO):
    """Return deliberately short bounded reads like a pipe may produce."""

    @override
    def read(self, size: int | None = -1, /) -> bytes:
        if size is None or size < 0:
            message = "profile worker attempted an aggregate stream read"
            raise AssertionError(message)
        return super().read(min(size, 7))


def test_profile_worker_stream_parser_preserves_complete_request() -> None:
    """A complete stream decodes without retaining an aggregate payload."""
    geometry, requests = parse_requests(_ChunkedStream(_request_payload()))

    assert geometry.memory_words == WORDS
    assert geometry.word_modulus == WORDS
    assert geometry.word_trits == TRITS
    assert len(requests) == 1
    request = requests[0]
    assert request.accumulator == ACCUMULATOR
    assert request.code_pointer == CODE_POINTER
    assert request.data_pointer == DATA_POINTER
    assert request.input_bytes == (0xA5, 0x5A)
    assert request.input_consumed == 1
    assert isinstance(request.memory, array)
    assert tuple(request.memory) == tuple(range(WORDS))
    assert request.output_bytes == (0x42,)
    assert request.step_budget == STEP_BUDGET


def test_profile_worker_stream_parser_rejects_truncation() -> None:
    """A short stream fails before constructing a partial request batch."""
    payload = _request_payload()

    with pytest.raises(
        profile_run_worker.ProfileRunProtocolError,
        match="truncated scalable resident protocol payload",
    ):
        _ = parse_requests(BytesIO(payload[:-1]))


def test_profile_worker_stream_parser_rejects_trailing_bytes() -> None:
    """Unexpected bytes after the declared batch remain fail closed."""
    with pytest.raises(
        profile_run_worker.ProfileRunProtocolError,
        match="trailing scalable resident protocol bytes",
    ):
        _ = parse_requests(BytesIO(_request_payload() + b"x"))


def _request_payload() -> bytes:
    memory = b"".join(_u32_bytes(value) for value in range(WORDS))
    geometry = _u32_bytes(
        EOF_WORD,
        INPUT_INSTRUCTION,
        WORDS,
        OUTPUT_INSTRUCTION,
        WORDS,
        TRITS,
        1,
    )
    header = _u32_bytes(
        ACCUMULATOR, CODE_POINTER, DATA_POINTER, 2, 1, 1, STEP_BUDGET, 0
    )
    return (
        profile_run_worker.MAGIC
        + geometry
        + header
        + memory
        + bytes((0xA5, 0x5A, 0x42))
    )


def _u32_bytes(*values: int) -> bytes:
    return b"".join(value.to_bytes(4, "little") for value in values)
