# File:
#   - classic_step_worker.py
# Path:
#   - accelerator/cuda/classic_step_worker.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
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
#   - Versioned process worker for optional CUDA compact classic transitions.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Versioned process worker for optional CUDA compact classic transitions."""

from __future__ import annotations

import sys

from accelerator.classic_step import ClassicStepRequest
from accelerator.classic_step import MAX_MEMORY_SLOTS
from accelerator.classic_step import REQUEST_WORDS
from accelerator.classic_step import StepMemoryCell
from accelerator.classic_step import StepTermination
from accelerator.cuda.classic_step import CudaClassicStepAdapter
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import InvalidPrimitiveBatchError

PROTOCOL = "MBSTEP1"
HEADER_WORDS = 2


class ClassicStepProtocolError(ValueError):
    """Malformed classic-step process protocol input."""


def main() -> int:
    """Read one request batch from stdin and write deterministic result rows.

    Returns:
        Process exit status: zero for protocol success/unavailable; one for
        invalid input or CUDA execution failure.

    """
    try:
        requests = _parse(sys.stdin.read())
        with CudaClassicStepAdapter() as adapter:
            results = adapter.evaluate(requests)
    except AcceleratorUnavailableError as error:
        _ = sys.stdout.write(f"{PROTOCOL} UNAVAILABLE {error}\n")
        return 0
    except (
        ClassicStepProtocolError,
        InvalidPrimitiveBatchError,
        ValueError,
    ) as error:
        _ = sys.stderr.write(f"{PROTOCOL} INVALID {error}\n")
        return 1
    lines = [f"{PROTOCOL} {len(results)}"]
    lines.extend(
        " ".join(str(word) for word in result.to_words()) for result in results
    )
    _ = sys.stdout.write("\n".join(lines) + "\n")
    return 0


def _parse(text: str) -> tuple[ClassicStepRequest, ...]:
    lines = [line for line in text.splitlines() if line]
    if not lines:
        message = "missing protocol header"
        raise ClassicStepProtocolError(message)
    header = lines[0].split()
    if len(header) != HEADER_WORDS or header[0] != PROTOCOL:
        message = "invalid protocol header"
        raise ClassicStepProtocolError(message)
    count = int(header[1])
    if count != len(lines) - 1:
        message = "request count does not match protocol rows"
        raise ClassicStepProtocolError(message)
    return tuple(_request(line) for line in lines[1:])


def _request(line: str) -> ClassicStepRequest:
    words = tuple(int(value) for value in line.split())
    if len(words) != REQUEST_WORDS:
        message = f"request row requires {REQUEST_WORDS} words"
        raise ClassicStepProtocolError(message)
    cells: list[StepMemoryCell] = []
    for slot in range(MAX_MEMORY_SLOTS):
        base = 8 + (slot * 3)
        if words[base]:
            cells.append(StepMemoryCell(words[base + 1], words[base + 2]))
    input_byte = words[7] if words[6] else None
    return ClassicStepRequest(
        accumulator=words[0],
        code_pointer=words[1],
        data_pointer=words[2],
        input_byte=input_byte,
        input_consumed=words[3],
        memory=tuple(cells),
        output_len=words[4],
        termination=StepTermination(words[5]),
    ).validated()


if __name__ == "__main__":
    raise SystemExit(main())
