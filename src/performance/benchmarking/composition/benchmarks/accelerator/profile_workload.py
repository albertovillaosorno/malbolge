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
#   - Shared exact current-profile workload for CUDA performance evidence.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Shared exact current-profile workload for CUDA performance evidence."""

from __future__ import annotations

from array import array
from typing import Final
from typing import TYPE_CHECKING

from accelerator.classic_run import RunError
from accelerator.classic_run import RunStatus
from accelerator.classic_step import StepTermination
from accelerator.cuda.classic_step import XLAT1
from accelerator.profile_run import ProfileMemoryImage
from accelerator.profile_run import ProfileRunGeometry
from accelerator.profile_run import ProfileRunRequest
from accelerator.profile_run import validate_profile_run_requests
from scripts.validate import target_profile

if TYPE_CHECKING:
    from accelerator.profile_run import ProfileRunResult

NOOP_DECODED: Final = ord("+")
_CURRENT_PROFILE: Final = target_profile.current_profile_geometry()
PROFILE_TRITS: Final = _CURRENT_PROFILE.word_trits
PROFILE_WORDS: Final = _CURRENT_PROFILE.memory_words
STEP_BUDGET: Final = 64
WORD_BYTES: Final = 4
WORKLOAD_DESCRIPTION: Final = (
    f"64 committed no-op transitions per {PROFILE_TRITS}-trit profile VM"
)
GEOMETRY: Final = ProfileRunGeometry(
    eof_word=_CURRENT_PROFILE.eof_word,
    input_instruction=ord(_CURRENT_PROFILE.input_instruction),
    memory_words=_CURRENT_PROFILE.memory_words,
    output_instruction=ord(_CURRENT_PROFILE.output_instruction),
    word_modulus=_CURRENT_PROFILE.word_modulus,
    word_trits=_CURRENT_PROFILE.word_trits,
).validated()


def profile_noop_request(
    *,
    step_budget: int = STEP_BUDGET,
    prepared_steps: int = STEP_BUDGET,
) -> ProfileRunRequest:
    """Build one exact 14-trit no-op benchmark request.

    Returns:
        Validated request with the requested prepared no-op code span.

    Raises:
        ValueError: If the prepared span cannot cover the execution budget.

    """
    if not step_budget <= prepared_steps <= PROFILE_WORDS:
        message = (
            "profile benchmark prepared span must cover the step budget within "
            f"memory: {step_budget} <= {prepared_steps} <= {PROFILE_WORDS}"
        )
        raise ValueError(message)
    request = ProfileRunRequest(
        accumulator=0,
        code_pointer=0,
        data_pointer=0,
        input_bytes=(),
        input_consumed=0,
        memory=ProfileMemoryImage(GEOMETRY, _noop_memory(prepared_steps)),
        output_bytes=(),
        step_budget=step_budget,
        termination=StepTermination.NONE,
    )
    return validate_profile_run_requests(GEOMETRY, (request,))[0]


def validate_profile_noop_results(
    results: tuple[ProfileRunResult, ...],
    expected_count: int,
) -> None:
    """Require complete budget-exhausted results for the benchmark workload.

    Raises:
        RuntimeError: If result count or observable state differs from expected.

    """
    if len(results) != expected_count:
        message = "profile CUDA benchmark batch returned wrong result count"
        raise RuntimeError(message)
    for result in results:
        _validate_result(result)


def _noop_memory(prepared_steps: int) -> array[int]:
    try:
        target_index = XLAT1.index(NOOP_DECODED)
    except ValueError as error:
        message = "reviewed XLAT1 table has no benchmark no-op decode"
        raise RuntimeError(message) from error
    words = array("I", [0]) * PROFILE_WORDS
    for code_pointer in range(prepared_steps):
        encoded_index = (target_index - code_pointer) % len(XLAT1)
        words[code_pointer] = 33 + encoded_index
    return words


def _validate_result(result: ProfileRunResult) -> None:
    _validate_outcome(result)
    _validate_materialized_state(result)


def _validate_outcome(result: ProfileRunResult) -> None:
    if result.status != RunStatus.BUDGET_EXHAUSTED:
        message = "profile CUDA benchmark workload terminated unexpectedly"
        raise RuntimeError(message)
    if result.error != RunError.NONE:
        message = "profile CUDA benchmark workload returned an execution error"
        raise RuntimeError(message)
    if result.steps != STEP_BUDGET:
        message = "profile CUDA benchmark workload executed wrong step count"
        raise RuntimeError(message)
    if result.termination != StepTermination.NONE:
        message = "profile CUDA benchmark gained unexpected termination"
        raise RuntimeError(message)


def _validate_materialized_state(result: ProfileRunResult) -> None:
    if result.code_pointer != STEP_BUDGET or result.data_pointer != STEP_BUDGET:
        message = "profile CUDA benchmark advanced wrong pointers"
        raise RuntimeError(message)
    if len(result.memory) != PROFILE_WORDS:
        message = "profile CUDA benchmark did not materialize full memory"
        raise RuntimeError(message)
