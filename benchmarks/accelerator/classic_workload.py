# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Shared exact classic workload for CUDA performance evidence."""

from __future__ import annotations

from typing import Final
from typing import TYPE_CHECKING

from accelerator.classic_run import ClassicRunRequest
from accelerator.classic_run import MEMORY_WORDS
from accelerator.classic_run import RunStatus
from accelerator.classic_step import StepTermination
from accelerator.cuda.classic_step import XLAT1

if TYPE_CHECKING:
    from accelerator.classic_run import ClassicRunResult

NOOP_DECODED: Final = ord("+")
STEP_BUDGET: Final = 64
WORKLOAD_DESCRIPTION: Final = "64 committed no-op transitions per classic VM"


def classic_noop_request() -> ClassicRunRequest:
    """Build the canonical exact 64-step classic benchmark request.

    Returns:
        Validated resident classic request with 64 committed no-op transitions.

    """
    return ClassicRunRequest(
        accumulator=0,
        code_pointer=0,
        data_pointer=0,
        input_bytes=(),
        input_consumed=0,
        memory=_noop_memory(),
        output_bytes=(),
        step_budget=STEP_BUDGET,
        termination=StepTermination.NONE,
    ).validated()


def validate_classic_noop_results(
    results: tuple[ClassicRunResult, ...],
    expected_count: int,
) -> None:
    """Require exact budget exhaustion for every benchmark result.

    Raises:
        RuntimeError: If result count or VM outcome differs from the workload.

    """
    if len(results) != expected_count:
        message = "CUDA benchmark batch returned wrong result count"
        raise RuntimeError(message)
    for result in results:
        _validate_result(result)


def _noop_memory() -> tuple[int, ...]:
    try:
        target_index = XLAT1.index(NOOP_DECODED)
    except ValueError as error:
        message = "reviewed XLAT1 table has no benchmark no-op decode"
        raise RuntimeError(message) from error
    words = [0] * MEMORY_WORDS
    for code_pointer in range(STEP_BUDGET):
        encoded_index = (target_index - code_pointer) % len(XLAT1)
        words[code_pointer] = 33 + encoded_index
    return tuple(words)


def _validate_result(result: ClassicRunResult) -> None:
    if result.status != RunStatus.BUDGET_EXHAUSTED:
        message = "CUDA benchmark workload terminated unexpectedly"
        raise RuntimeError(message)
    if result.steps != STEP_BUDGET:
        message = "CUDA benchmark workload executed wrong step count"
        raise RuntimeError(message)
    if result.termination != StepTermination.NONE:
        message = "CUDA benchmark workload gained unexpected termination"
        raise RuntimeError(message)
