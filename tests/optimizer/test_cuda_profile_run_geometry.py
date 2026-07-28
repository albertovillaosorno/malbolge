# File:
#   - test_cuda_profile_run_geometry.py
# Path:
#   - tests/optimizer/test_cuda_profile_run_geometry.py
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
#   - Live CUDA evidence that resident execution is not fixed to known profiles.
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

"""Live CUDA evidence that resident execution is not fixed to known profiles."""

from __future__ import annotations

from array import array
from dataclasses import replace
from typing import Final
from unittest import SkipTest

from accelerator.classic_run import RunError
from accelerator.classic_run import RunStatus
from accelerator.classic_step import StepTermination
from accelerator.cuda.classic_step import XLAT1
from accelerator.cuda.profile_run import CudaProfileRunAdapter
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.profile_run import ProfileMemoryImage
from accelerator.profile_run import ProfileRunGeometry
from accelerator.profile_run import ProfileRunRequest

SYNTHETIC_TRITS: Final = 5
SYNTHETIC_WORDS: Final = 243
INITIAL_ACCUMULATOR: Final = 7
EXPECTED_DATA_POINTER: Final = 2
SESSION_BATCH_SIZE: Final = 2
SESSION_RUNS: Final = 3
NO_OP_CELL: Final = 33
ENCRYPTED_NO_OP_CELL: Final = 53
GEOMETRY = ProfileRunGeometry(
    eof_word=SYNTHETIC_WORDS - 1,
    memory_words=SYNTHETIC_WORDS,
    word_modulus=SYNTHETIC_WORDS,
    word_trits=SYNTHETIC_TRITS,
)


def _cuda() -> CudaProfileRunAdapter:
    try:
        return CudaProfileRunAdapter(GEOMETRY)
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


def _request() -> ProfileRunRequest:
    memory = array("I", [0]) * SYNTHETIC_WORDS
    memory[0] = NO_OP_CELL
    return ProfileRunRequest(
        accumulator=INITIAL_ACCUMULATOR,
        code_pointer=0,
        data_pointer=1,
        input_bytes=(),
        input_consumed=0,
        memory=memory,
        output_bytes=(),
        step_budget=1,
        termination=StepTermination.NONE,
    )


def test_cuda_resident_kernel_executes_synthetic_five_trit_geometry() -> None:
    """Execute a valid NVRTC profile distinct from 10/14 trits."""
    request = _request()

    with _cuda() as adapter:
        (result,) = adapter.evaluate((request,))

    assert result.accumulator == INITIAL_ACCUMULATOR
    assert result.code_pointer == 1
    assert isinstance(request.memory, array)
    assert result.memory is not request.memory
    assert request.memory[0] == NO_OP_CELL
    assert result.data_pointer == EXPECTED_DATA_POINTER
    assert result.error is RunError.NONE
    assert result.input_consumed == 0
    assert result.memory[0] == ENCRYPTED_NO_OP_CELL
    assert isinstance(request.memory, array)
    assert result.memory[1:] == request.memory[1:]
    assert result.output_bytes == ()
    assert result.status is RunStatus.BUDGET_EXHAUSTED
    assert result.steps == 1
    assert result.termination is StepTermination.NONE


def test_cuda_profile_diagnostics_preserve_exact_results() -> None:
    """Phase instrumentation must not change the scalable execution result."""
    request = _request()
    with _cuda() as adapter:
        expected = adapter.evaluate((request,))
        observed, profile = adapter.profile_evaluate((request,))

    assert observed == expected
    assert profile.chunks == 1
    assert profile.total_ns >= profile.validation_plan_ns
    assert profile.host_build_ns >= 0
    assert profile.kernel_ns >= 0
    assert profile.decode_ns >= 0


def test_cuda_shared_profile_memory_is_replicated_per_vm() -> None:
    """Initialize private device memories from one shared host image."""
    request = _request()
    with _cuda() as adapter:
        first, second = adapter.evaluate((request, request))

    assert first == second
    assert first.memory == second.memory
    first.memory[1] = 1
    assert second.memory[1] == 0


def _resident_session_request() -> ProfileRunRequest:
    memory = array("I", [0]) * SYNTHETIC_WORDS
    target_index = XLAT1.index(ord("+"))
    for code_pointer in range(SESSION_RUNS):
        encoded_index = (target_index - code_pointer) % len(XLAT1)
        memory[code_pointer] = 33 + encoded_index
    return ProfileRunRequest(
        accumulator=INITIAL_ACCUMULATOR,
        code_pointer=0,
        data_pointer=1,
        input_bytes=(),
        input_consumed=0,
        memory=memory,
        output_bytes=(),
        step_budget=1,
        termination=StepTermination.NONE,
    )


def test_cuda_profile_session_matches_contiguous_execution() -> None:
    """Repeated resident segments preserve exact scalable VM state."""
    request = _resident_session_request()
    contiguous = replace(request, step_budget=SESSION_RUNS)
    with _cuda() as adapter:
        expected = adapter.evaluate((contiguous, contiguous))
        with adapter.open_session(
            (request, request), max_runs=SESSION_RUNS
        ) as session:
            for _ in range(SESSION_RUNS):
                session.advance()
            observations = session.observe()
            observed = session.snapshot()
            runs_executed = session.runs_executed

    expected_segmented = tuple(replace(result, steps=1) for result in expected)
    assert observed == expected_segmented
    assert runs_executed == SESSION_RUNS
    assert len(observations) == SESSION_BATCH_SIZE
    assert all(item.code_pointer == SESSION_RUNS for item in observations)
    assert all(item.steps == 1 for item in observations)
    assert all(
        item.status is RunStatus.BUDGET_EXHAUSTED for item in observations
    )


def test_cuda_profile_session_snapshot_phases_preserve_exact_results() -> None:
    """Snapshot profiling separates host allocation, transfers, and decode."""
    request = _resident_session_request()
    with _cuda() as adapter, adapter.open_session(
        (request, request),
        max_runs=SESSION_RUNS,
    ) as session:
        for _ in range(SESSION_RUNS):
            session.advance()
        expected = session.snapshot()
        observed, profile = session.profile_snapshot()

    assert observed == expected
    assert profile.chunks == 1
    components = (
        profile.host_memory_allocate_ns,
        profile.state_download_ns,
        profile.memory_download_ns,
        profile.output_download_ns,
        profile.decode_ns,
    )
    assert all(value >= 0 for value in components)
    assert profile.total_ns >= sum(components)


def test_cuda_profile_accepts_validated_memory_image() -> None:
    """Immutable validated memory images preserve exact CUDA execution."""
    request = _request()
    assert isinstance(request.memory, array)
    image_request = replace(
        request,
        memory=ProfileMemoryImage(GEOMETRY, request.memory),
    )
    with _cuda() as adapter:
        expected = adapter.evaluate((request,))
        observed = adapter.evaluate((image_request,))

    assert observed == expected
