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
from typing import TYPE_CHECKING
from typing import cast
from unittest import SkipTest

import pytest

from accelerator.classic_run import RunError
from accelerator.classic_run import RunStatus
from accelerator.classic_step import StepTermination
from accelerator.cuda.classic_step import XLAT1
from accelerator.cuda.profile_run import CudaProfileRunAdapter
from accelerator.cuda.profile_run import CudaProfileSnapshotWorkspace
from accelerator.cuda.profile_run import profile_snapshot_host_registration_id
from accelerator.cuda.profile_run import profile_snapshot_workspace_id
from accelerator.cuda.runtime import CudaHostMemoryRegistry
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.profile_run import ProfileMemoryImage
from accelerator.profile_run import ProfileRunGeometry
from accelerator.profile_run import ProfileRunRequest

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.cuda.profile_run import ProfileSnapshotHostRegistration

SYNTHETIC_TRITS: Final = 5
SYNTHETIC_WORDS: Final = 243
INITIAL_ACCUMULATOR: Final = 7
EXPECTED_DATA_POINTER: Final = 2
SESSION_BATCH_SIZE: Final = 2
SESSION_RUNS: Final = 3
SNAPSHOT_WORKSPACE_ID: Final = "caller-owned-independent-u32-arrays-v1"
SNAPSHOT_HOST_REGISTRATION_ID: Final = (
    "bounded-all-or-pageable-u32-arrays-v1"
)
_DEVICE_WORD_BYTES: Final = 4
_HOST_REGISTRATION_BUDGET_EXCEEDED: Final = "budget-exceeded"
_HOST_REGISTRATION_DRIVER_REJECTED: Final = "driver-rejected"
NO_OP_CELL: Final = 33
ENCRYPTED_NO_OP_CELL: Final = 53
GEOMETRY = ProfileRunGeometry(
    eof_word=SYNTHETIC_WORDS - 1,
    memory_words=SYNTHETIC_WORDS,
    word_modulus=SYNTHETIC_WORDS,
    word_trits=SYNTHETIC_TRITS,
)


def _corrupt_attribute(target: object, name: str, value: object) -> None:
    setattr(target, name, value)


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
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request, request),
            max_runs=SESSION_RUNS,
        ) as session,
    ):
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


def test_cuda_profile_session_snapshots_are_independent_between_calls() -> None:
    """Ordinary snapshots never alias a prior snapshot memory array."""
    request = _resident_session_request()
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request,),
            max_runs=1,
        ) as session,
    ):
        session.advance()
        first = session.snapshot()
        second = session.snapshot()

    assert first == second
    assert first[0].memory is not second[0].memory
    first[0].memory[0] = 0
    assert second[0].memory[0] != 0


def test_cuda_profile_snapshot_workspace_reuses_explicit_arrays() -> None:
    """Workspace snapshots alias and overwrite only caller-owned arrays."""
    request = _resident_session_request()
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request, request),
            max_runs=1,
        ) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_workspace()
        first = workspace.snapshot()
        first_value = first[0].memory[0]
        workspace.memories[0][0] = 0
        second, profile = workspace.profile_snapshot()

    assert first == expected
    assert second == expected
    assert all(
        result.memory is workspace.memories[index]
        for index, result in enumerate(second)
    )
    assert first[0].memory is second[0].memory
    assert first[0].memory[0] == first_value
    assert profile.host_memory_allocate_ns == 0
    assert profile.total_ns >= (
        profile.state_download_ns
        + profile.memory_download_ns
        + profile.output_download_ns
        + profile.decode_ns
    )


def test_cuda_profile_snapshot_workspace_registers_within_budget() -> None:
    """One stable workspace is page-locked and released explicitly."""
    request = _resident_session_request()
    expected_bytes = SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    with (
        _cuda() as adapter,
        adapter.open_session((request,), max_runs=1) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_workspace(
            host_registration_budget_bytes=expected_bytes,
        )
        registration = workspace.registration
        with pytest.raises(
            BufferError,
            match=r"cannot resize.*exporting buffers",
        ):
            workspace.memories[0].append(0)
        observed = workspace.snapshot()
        workspace.close()
        workspace.memories[0].append(0)
        _ = workspace.memories[0].pop()
        with pytest.raises(
            AcceleratorExecutionError,
            match="workspace is closed",
        ):
            _ = workspace.snapshot()

    assert observed == expected
    assert registration.active
    assert registration.budget_bytes == expected_bytes
    assert registration.fallback_reason is None
    assert registration.registered_arrays == 1
    assert registration.registered_bytes == expected_bytes
    assert registration.requested_bytes == expected_bytes


def test_cuda_profile_snapshot_workspace_falls_back_for_budget() -> None:
    """An insufficient explicit budget preserves the pageable contract."""
    request = _resident_session_request()
    requested_bytes = (
        SESSION_BATCH_SIZE * SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    )
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request, request),
            max_runs=1,
        ) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_workspace(
            host_registration_budget_bytes=requested_bytes - 1,
        )
        registration = workspace.registration
        workspace.memories[0].append(0)
        _ = workspace.memories[0].pop()
        observed = workspace.snapshot()

    assert observed == expected
    assert not registration.active
    assert (
        registration.fallback_reason
        == _HOST_REGISTRATION_BUDGET_EXCEEDED
    )
    assert registration.registered_arrays == 0
    assert registration.registered_bytes == 0
    assert registration.requested_bytes == requested_bytes


def _measure_driver_rejection_fallback(
    monkeypatch: pytest.MonkeyPatch,
    request: ProfileRunRequest,
    requested_bytes: int,
) -> tuple[
    tuple[object, ...],
    tuple[object, ...],
    ProfileSnapshotHostRegistration,
    int,
]:
    original = cast("Callable[..., int]", CudaHostMemoryRegistry.register)
    calls = 0

    def reject_second(registry: object, host: object) -> int:
        nonlocal calls
        calls += 1
        if calls == SESSION_BATCH_SIZE:
            message = "synthetic CUDA host registration rejection"
            raise AcceleratorExecutionError(message)
        return original(registry, host)

    monkeypatch.setattr(CudaHostMemoryRegistry, "register", reject_second)
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request, request),
            max_runs=1,
        ) as session,
    ):
        session.advance()
        expected = session.snapshot()
        workspace = session.allocate_snapshot_workspace(
            host_registration_budget_bytes=requested_bytes,
        )
        registration = workspace.registration
        workspace.memories[0].append(0)
        _ = workspace.memories[0].pop()
        observed = workspace.snapshot()
    return expected, observed, registration, calls


def test_cuda_profile_snapshot_workspace_rolls_back_driver_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A later registration rejection releases earlier page locks."""
    requested_bytes = (
        SESSION_BATCH_SIZE * SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    )
    measured = _measure_driver_rejection_fallback(
        monkeypatch,
        _resident_session_request(),
        requested_bytes,
    )
    expected, observed, registration, calls = measured

    assert calls == SESSION_BATCH_SIZE
    assert observed == expected
    assert not registration.active
    assert (
        registration.fallback_reason
        == _HOST_REGISTRATION_DRIVER_REJECTED
    )
    assert registration.registered_arrays == 0
    assert registration.registered_bytes == 0


def test_cuda_profile_snapshot_workspace_rejects_invalid_budget() -> None:
    """Registration budgets require exact nonnegative integer authority."""
    request = _resident_session_request()
    with (
        _cuda() as adapter,
        adapter.open_session((request,), max_runs=1) as session,
    ):
        for budget in (-1, True):
            with pytest.raises(
                AcceleratorExecutionError,
                match="nonnegative integer",
            ):
                _ = session.allocate_snapshot_workspace(
                    host_registration_budget_bytes=budget,
                )


def test_cuda_profile_snapshot_session_close_releases_registration() -> None:
    """Session close releases page locks before closed-session errors."""
    request = _resident_session_request()
    expected_bytes = SYNTHETIC_WORDS * _DEVICE_WORD_BYTES
    with _cuda() as adapter:
        session = adapter.open_session((request,), max_runs=1)
        workspace = session.allocate_snapshot_workspace(
            host_registration_budget_bytes=expected_bytes,
        )
        assert workspace.registration.active
        session.close()
        workspace.memories[0].append(0)
        _ = workspace.memories[0].pop()
        with pytest.raises(
            AcceleratorExecutionError,
            match="session is closed",
        ):
            _ = workspace.snapshot()


def test_cuda_profile_snapshot_workspace_rejects_mutated_shape() -> None:
    """Resized or duplicated caller arrays fail before a snapshot download."""
    request = _resident_session_request()
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request, request),
            max_runs=1,
        ) as session,
    ):
        workspace = session.allocate_snapshot_workspace()
        _ = workspace.memories[0].pop()
        with pytest.raises(
            AcceleratorExecutionError, match="word count changed"
        ):
            _ = workspace.snapshot()

        replacement = session.allocate_snapshot_workspace()
        same = replacement.memories[0]
        _corrupt_attribute(replacement, "_memories", (same, same))
        with pytest.raises(
            AcceleratorExecutionError, match="independent arrays"
        ):
            _ = replacement.snapshot()


def test_cuda_profile_snapshot_workspace_rejects_forged_or_closed_use() -> None:
    """Proof drift and closed-session actions fail explicitly."""
    request = _resident_session_request()
    with _cuda() as adapter:
        session = adapter.open_session((request,), max_runs=1)
        workspace = session.allocate_snapshot_workspace()
        _corrupt_attribute(workspace, "_proof", object())
        with pytest.raises(
            AcceleratorExecutionError, match="workspace is forged"
        ):
            _ = workspace.snapshot()

        valid = session.allocate_snapshot_workspace()
        session.close()
        with pytest.raises(
            AcceleratorExecutionError, match="session is closed"
        ):
            _ = valid.snapshot()


def test_cuda_profile_snapshot_workspace_rejects_count_drift() -> None:
    """Workspace cardinality remains bound to its exact resident session."""
    request = _resident_session_request()
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request, request),
            max_runs=1,
        ) as session,
    ):
        workspace = session.allocate_snapshot_workspace()
        _corrupt_attribute(workspace, "_memories", workspace.memories[:1])
        with pytest.raises(
            AcceleratorExecutionError, match="workspace count changed"
        ):
            _ = workspace.snapshot()


def test_cuda_profile_snapshot_workspace_type_is_public() -> None:
    """The caller-owned workspace has an explicit public runtime type."""
    request = _resident_session_request()
    with (
        _cuda() as adapter,
        adapter.open_session(
            (request,),
            max_runs=1,
        ) as session,
    ):
        workspace = session.allocate_snapshot_workspace()

    assert isinstance(workspace, CudaProfileSnapshotWorkspace)
    assert profile_snapshot_workspace_id() == SNAPSHOT_WORKSPACE_ID
    assert (
        profile_snapshot_host_registration_id()
        == SNAPSHOT_HOST_REGISTRATION_ID
    )


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
