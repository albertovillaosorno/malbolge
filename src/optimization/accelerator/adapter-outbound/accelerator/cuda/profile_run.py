# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
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
#   - CUDA resident bounded execution for scalable modular Malbolge profiles.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""CUDA resident bounded execution for scalable modular Malbolge profiles."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from array import array
import ctypes
from dataclasses import dataclass
from time import perf_counter_ns
from typing import Final
from typing import Self
from typing import TYPE_CHECKING
from typing import cast
from typing import final
from typing import override

from accelerator.classic_run import MAX_U32
from accelerator.classic_run import RunError
from accelerator.classic_run import RunStatus
from accelerator.classic_run import STATE_WORDS
from accelerator.classic_step import StepTermination
from accelerator.cuda.resident_kernel import ResidentGeometry
from accelerator.cuda.resident_kernel import resident_kernel_source
from accelerator.cuda.runtime import CudaRuntime
from accelerator.cuda.runtime import create_ordered_dtoh_stream
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import InvalidPrimitiveBatchError
from accelerator.profile_run import ProfileMemoryImage
from accelerator.profile_run import ProfileRunObservation
from accelerator.profile_run import ProfileRunResult
from accelerator.profile_run import validate_profile_run_requests
from accelerator.resource_budget import ResourceBudgetError
from accelerator.resource_budget import plan_resident_batches

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Sequence

    from accelerator.cuda.resident_kernel import ResidentCrazyGeometry
    from accelerator.cuda.runtime import CudaKernelResources
    from accelerator.cuda.runtime import CudaOrderedDtoHStream
    from accelerator.profile_run import ProfileRunGeometry
    from accelerator.profile_run import ProfileRunRequest
    from accelerator.resource_budget import ResourcePlan

_STATUS_INDEX: Final = 11
_ERROR_INDEX: Final = 12
_ERROR_POINTER_INDEX: Final = 13
_ERROR_VALUE_INDEX: Final = 14
_STEPS_INDEX: Final = 15
_DEVICE_WORD_BYTES: Final = 4
_FIXED_CHUNK_BYTES: Final = 2 * _DEVICE_WORD_BYTES
_KERNEL_NAME: Final = "malbolge_profile_run_batch"
_SNAPSHOT_OVERLAP_WORKSPACE_PROOF = object()
_SNAPSHOT_STREAM_WORKSPACE_PROOF = object()
_SNAPSHOT_WORKSPACE_PROOF = object()
_WORD_TYPECODE: Final = "I"
PROFILE_SNAPSHOT_WORKSPACE_ID: Final = "caller-owned-independent-u32-arrays-v1"
PROFILE_SNAPSHOT_STREAM_WORKSPACE_ID: Final = (
    "caller-owned-windowed-u32-arrays-v1"
)
PROFILE_SNAPSHOT_OVERLAP_WORKSPACE_ID: Final = (
    "caller-owned-double-window-overlap-u32-arrays-v1"
)
PROFILE_SNAPSHOT_HOST_REGISTRATION_ID: Final = (
    "bounded-all-or-pageable-u32-arrays-v1"
)
_HOST_REGISTRATION_DISABLED: Final = "disabled"
_HOST_REGISTRATION_BUDGET_EXCEEDED: Final = "budget-exceeded"
_HOST_REGISTRATION_DRIVER_REJECTED: Final = "driver-rejected"
_SNAPSHOT_OVERLAP_SINGLE_BUFFER: Final = "single-buffer-budget"
_SNAPSHOT_OVERLAP_BUFFER_COUNT: Final = 2

type HostWords = ctypes.Array[ctypes.c_uint32]


@dataclass(frozen=True, slots=True)
class ProfileRunPhaseProfile:
    """Diagnostic wall-clock phase totals for one profiled evaluation."""

    allocate_ns: int
    chunks: int
    decode_ns: int
    download_ns: int
    host_build_ns: int
    kernel_ns: int
    release_ns: int
    total_ns: int
    upload_ns: int
    validation_plan_ns: int


def profile_snapshot_workspace_id() -> str:
    """Return the active explicit snapshot-workspace identity.

    Returns:
        Stable identity for benchmark and evidence provenance.

    """
    return PROFILE_SNAPSHOT_WORKSPACE_ID


def profile_snapshot_host_registration_id() -> str:
    """Return the bounded host-registration policy identity.

    Returns:
        Stable identity for benchmark and evidence provenance.

    """
    return PROFILE_SNAPSHOT_HOST_REGISTRATION_ID


def profile_snapshot_stream_workspace_id() -> str:
    """Return the bounded streaming-workspace identity.

    Returns:
        Stable identity for benchmark and evidence provenance.

    """
    return PROFILE_SNAPSHOT_STREAM_WORKSPACE_ID


def profile_snapshot_overlap_workspace_id() -> str:
    """Return the double-buffer overlap-workspace identity.

    Returns:
        Stable identity for benchmark and evidence provenance.

    """
    return PROFILE_SNAPSHOT_OVERLAP_WORKSPACE_ID


@dataclass(frozen=True, slots=True)
class ProfileSnapshotWindow:
    """One ordered result window aliasing reusable workspace arrays."""

    results: tuple[ProfileRunResult, ...]
    start: int
    stop: int

    @property
    def item_count(self) -> int:
        """Number of global request positions in this window."""
        return self.stop - self.start


@dataclass(frozen=True, slots=True)
class ProfileSnapshotStreamSummary:
    """Completed bounded streaming snapshot cardinality."""

    items: int
    windows: int


@dataclass(frozen=True, slots=True)
class ProfileSnapshotStreamCapacity:
    """Immutable host-window budget and cardinality evidence."""

    host_memory_budget_bytes: int
    total_items: int
    window_bytes: int
    window_items: int


@dataclass(frozen=True, slots=True)
class ProfileSnapshotOverlapCapacity:
    """Host-budget layout for one explicit double-buffer workspace."""

    bank_bytes: int
    bank_items: int
    buffer_count: int
    host_memory_budget_bytes: int
    planned_windows: int
    retained_bytes: int
    total_items: int


@dataclass(frozen=True, slots=True)
class ProfileSnapshotOverlapAdmission:
    """Observable overlap admission or synchronous fallback reason."""

    fallback_reason: str | None

    @property
    def active(self) -> bool:
        """Whether the workspace will prefetch into its second bank."""
        return self.fallback_reason is None


@dataclass(frozen=True, slots=True)
class ProfileSnapshotOverlapSummary:
    """Completed overlap stream cardinality and scheduled prefetch count."""

    items: int
    prefetched_windows: int
    windows: int


@dataclass(frozen=True, slots=True)
class ProfileSnapshotHostRegistration:
    """Observable all-or-none registration outcome for one workspace."""

    budget_bytes: int
    fallback_reason: str | None
    registered_arrays: int
    registered_bytes: int
    requested_bytes: int

    @property
    def active(self) -> bool:
        """Whether every workspace array is currently page-locked."""
        return self.fallback_reason is None


@dataclass(slots=True)
class _SnapshotHostRegistrationLease:
    """Exact runtime-owned host registrations for one workspace."""

    runtime: CudaRuntime
    registration_record: ProfileSnapshotHostRegistration
    addresses: tuple[int, ...] = ()
    memory_ids: tuple[int, ...] = ()
    released: bool = False

    @property
    def registration(self) -> ProfileSnapshotHostRegistration:
        """Immutable registration/fallback evidence."""
        return self.registration_record

    def release(self) -> None:
        """Unregister every page-locked array exactly once."""
        if self.released:
            return
        failure = _unregister_host_addresses(self.runtime, self.addresses)
        if failure is not None:
            raise failure
        self.addresses = ()
        self.released = True

    def validate_memories(self, memories: tuple[array[int], ...]) -> None:
        """Reject array substitution while registered buffers are live.

        Raises:
            AcceleratorExecutionError: If registered array identity changed.

        """
        if self.released or not self.registration.active:
            return
        if tuple(id(memory) for memory in memories) != self.memory_ids:
            message = "resident snapshot registered arrays changed"
            raise AcceleratorExecutionError(message)


def _unregister_host_addresses(
    runtime: CudaRuntime,
    addresses: tuple[int, ...] | list[int],
) -> AcceleratorExecutionError | None:
    """Attempt every host unregistration.

    Returns:
        First Driver API failure, or ``None`` after complete release.

    """
    failure: AcceleratorExecutionError | None = None
    for address in reversed(addresses):
        try:
            runtime.host_memory.unregister(address)
        except AcceleratorExecutionError as error:
            if failure is None:
                failure = error
    return failure


def _registration_record(
    budget_bytes: int,
    requested_bytes: int,
    fallback_reason: str | None,
    *,
    registered_arrays: int,
) -> ProfileSnapshotHostRegistration:
    registered_bytes = requested_bytes if fallback_reason is None else 0
    return ProfileSnapshotHostRegistration(
        budget_bytes=budget_bytes,
        fallback_reason=fallback_reason,
        registered_arrays=registered_arrays,
        registered_bytes=registered_bytes,
        requested_bytes=requested_bytes,
    )


def _pageable_registration_lease(
    runtime: CudaRuntime,
    memory_ids: tuple[int, ...],
    registration: ProfileSnapshotHostRegistration,
) -> _SnapshotHostRegistrationLease:
    return _SnapshotHostRegistrationLease(
        runtime=runtime,
        registration_record=registration,
        memory_ids=memory_ids,
    )


def _registration_fallback_reason(
    budget_bytes: int,
    requested_bytes: int,
) -> str | None:
    if budget_bytes == 0:
        return _HOST_REGISTRATION_DISABLED
    if requested_bytes > budget_bytes:
        return _HOST_REGISTRATION_BUDGET_EXCEEDED
    return None


def _register_snapshot_addresses(
    runtime: CudaRuntime,
    memories: tuple[array[int], ...],
) -> tuple[int, ...] | None:
    """Register all arrays or roll back prior registrations.

    Returns:
        Exact address tokens, or ``None`` after a clean driver fallback.

    """
    addresses: list[int] = []
    try:
        for memory in memories:
            address = runtime.host_memory.register(_word_buffer(memory).view)
            addresses.append(address)
    except AcceleratorExecutionError as registration_error:
        rollback_error = _unregister_host_addresses(runtime, addresses)
        if rollback_error is not None:
            raise rollback_error from registration_error
        return None
    return tuple(addresses)


def _prepare_snapshot_host_registration(
    runtime: CudaRuntime,
    memories: tuple[array[int], ...],
    budget_bytes: int,
) -> _SnapshotHostRegistrationLease:
    """Register every array within budget or return a pageable fallback.

    Returns:
        Registration lease with an observable active or fallback outcome.

    Raises:
        AcceleratorExecutionError: If the budget is invalid or rollback fails.

    """
    if type(budget_bytes) is not int or budget_bytes < 0:
        message = (
            "snapshot host registration budget must be a nonnegative integer"
        )
        raise AcceleratorExecutionError(message)
    requested_bytes = sum(len(memory) * memory.itemsize for memory in memories)
    memory_ids = tuple(id(memory) for memory in memories)
    fallback_reason = _registration_fallback_reason(
        budget_bytes,
        requested_bytes,
    )
    if fallback_reason is not None:
        registration = _registration_record(
            budget_bytes,
            requested_bytes,
            fallback_reason,
            registered_arrays=0,
        )
        return _pageable_registration_lease(
            runtime,
            memory_ids,
            registration,
        )
    addresses = _register_snapshot_addresses(runtime, memories)
    if addresses is None:
        registration = _registration_record(
            budget_bytes,
            requested_bytes,
            _HOST_REGISTRATION_DRIVER_REJECTED,
            registered_arrays=0,
        )
        return _pageable_registration_lease(
            runtime,
            memory_ids,
            registration,
        )
    registration = _registration_record(
        budget_bytes,
        requested_bytes,
        None,
        registered_arrays=len(memories),
    )
    return _SnapshotHostRegistrationLease(
        runtime=runtime,
        registration_record=registration,
        addresses=addresses,
        memory_ids=memory_ids,
    )


def _release_snapshot_registration_leases(
    leases: list[_SnapshotHostRegistrationLease],
) -> AcceleratorExecutionError | None:
    failure: AcceleratorExecutionError | None = None
    for lease in reversed(leases):
        try:
            lease.release()
        except AcceleratorExecutionError as error:
            if failure is None:
                failure = error
    if failure is None:
        leases.clear()
    return failure


@dataclass(frozen=True, slots=True)
class _SnapshotOverlapActions:
    stream: Callable[
        [
            tuple[tuple[array[int], ...], ...],
            Callable[[ProfileSnapshotWindow], None],
            ProfileSnapshotOverlapAdmission,
        ],
        ProfileSnapshotOverlapSummary,
    ]


@dataclass(frozen=True, slots=True)
class _SnapshotOverlapBinding:
    actions: _SnapshotOverlapActions
    admission: ProfileSnapshotOverlapAdmission
    bank_items: int
    buffer_count: int
    capacity: ProfileSnapshotOverlapCapacity
    memory_words: int
    registration_lease: _SnapshotHostRegistrationLease


@dataclass(frozen=True, slots=True)
class _SnapshotOverlapRequest:
    chunks: tuple[_ResidentChunk, ...]
    context: _ResidentContext
    host_memory_budget_bytes: int
    host_registration_budget_bytes: int
    total_items: int


@dataclass(frozen=True, slots=True)
class _SnapshotOverlapExecution:
    consumer: Callable[[ProfileSnapshotWindow], None]
    context: _ResidentContext
    memory_banks: tuple[tuple[array[int], ...], ...]
    stream: CudaOrderedDtoHStream


@dataclass(frozen=True, slots=True)
class _PreparedSnapshotOverlap:
    admission: ProfileSnapshotOverlapAdmission
    capacity: ProfileSnapshotOverlapCapacity
    memory_banks: tuple[tuple[array[int], ...], ...]
    registration_lease: _SnapshotHostRegistrationLease


@dataclass(frozen=True, slots=True)
class _ActiveSnapshotWindow:
    bank_index: int
    memories: tuple[array[int], ...]
    plan: _SnapshotWindowPlan


@dataclass(frozen=True, slots=True)
class _SnapshotWorkspaceActions:
    profile: Callable[
        [tuple[array[int], ...]],
        tuple[tuple[ProfileRunResult, ...], ProfileSnapshotPhaseProfile],
    ]
    snapshot: Callable[
        [tuple[array[int], ...]],
        tuple[ProfileRunResult, ...],
    ]


@dataclass(frozen=True, slots=True)
class _SnapshotWorkspaceBinding:
    actions: _SnapshotWorkspaceActions
    memory_words: int
    registration_lease: _SnapshotHostRegistrationLease


@dataclass(frozen=True, slots=True)
class _SnapshotStreamActions:
    stream: Callable[
        [
            tuple[array[int], ...],
            Callable[[ProfileSnapshotWindow], None],
        ],
        ProfileSnapshotStreamSummary,
    ]


@dataclass(frozen=True, slots=True)
class _SnapshotStreamBinding:
    actions: _SnapshotStreamActions
    capacity: ProfileSnapshotStreamCapacity
    memory_words: int
    registration_lease: _SnapshotHostRegistrationLease


@final
class CudaProfileSnapshotOverlapWorkspace:
    """Two callback-scoped banks with explicit async-prefetch admission."""

    def __init__(
        self,
        *,
        memory_banks: tuple[tuple[array[int], ...], ...],
        binding: _SnapshotOverlapBinding,
        _proof: object,
    ) -> None:
        """Bind fixed banks to one exact live resident session."""
        self._actions = binding.actions
        self._active = False
        self._admission = binding.admission
        self._bank_items = binding.bank_items
        self._buffer_count = binding.buffer_count
        self._capacity = binding.capacity
        self._closed = False
        self._memory_banks = memory_banks
        self._memory_words = binding.memory_words
        self._proof = _proof
        self._registration_lease = binding.registration_lease

    @property
    def admission(self) -> ProfileSnapshotOverlapAdmission:
        """Overlap activation or exact synchronous fallback reason."""
        return self._admission

    @property
    def capacity(self) -> ProfileSnapshotOverlapCapacity:
        """Retained double-buffer layout under the host-memory budget."""
        return self._capacity

    @property
    def memory_banks(self) -> tuple[tuple[array[int], ...], ...]:
        """Banks whose aliases are valid only inside their callback."""
        return self._memory_banks

    @property
    def registration(self) -> ProfileSnapshotHostRegistration:
        """All-or-none page-lock result for every retained bank array."""
        return self._registration_lease.registration

    def __enter__(self) -> Self:
        """Enter the explicit overlap-workspace scope.

        Returns:
            This workspace instance.

        """
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        """Release any page-locked bank arrays at scope exit."""
        self.close()

    def close(self) -> None:
        """Release every bank registration exactly once.

        Raises:
            AcceleratorExecutionError: If a callback stream is active.

        """
        if self._closed:
            return
        if self._active:
            message = "resident snapshot overlap workspace is active"
            raise AcceleratorExecutionError(message)
        self._closed = True
        self._registration_lease.release()

    def stream_snapshot(
        self,
        consumer: object,
    ) -> ProfileSnapshotOverlapSummary:
        """Deliver exact ordered windows with admitted next-bank prefetch.

        Result memory aliases are callback-scoped. After a callback returns,
        its bank may be reused by a later transfer and must not be accessed.

        Returns:
            Complete item/window counts and scheduled prefetch cardinality.

        Raises:
            AcceleratorExecutionError: If workspace or callback is invalid.

        """
        if not callable(consumer):
            message = "resident snapshot overlap consumer must be callable"
            raise AcceleratorExecutionError(message)
        admitted_consumer = cast(
            "Callable[[ProfileSnapshotWindow], None]",
            consumer,
        )
        memory_banks = self._validated_banks()
        if self._active:
            message = "resident snapshot overlap workspace is active"
            raise AcceleratorExecutionError(message)
        self._active = True
        try:
            return self._actions.stream(
                memory_banks,
                admitted_consumer,
                self._admission,
            )
        finally:
            self._active = False

    def _validated_banks(self) -> tuple[tuple[array[int], ...], ...]:
        if self._closed:
            message = "resident snapshot overlap workspace is closed"
            raise AcceleratorExecutionError(message)
        if self._proof is not _SNAPSHOT_OVERLAP_WORKSPACE_PROOF:
            message = "resident snapshot overlap workspace is forged"
            raise AcceleratorExecutionError(message)
        memories = _validate_snapshot_overlap_banks(
            self._memory_banks,
            buffer_count=self._buffer_count,
            bank_items=self._bank_items,
            memory_words=self._memory_words,
        )
        self._registration_lease.validate_memories(memories)
        return self._memory_banks


@final
class CudaProfileSnapshotStreamWorkspace:
    """Bounded reusable arrays delivered through ordered consumer windows."""

    def __init__(
        self,
        *,
        memories: tuple[array[int], ...],
        binding: _SnapshotStreamBinding,
        _proof: object,
    ) -> None:
        """Bind one fixed host window to one exact live resident session."""
        self._actions = binding.actions
        self._active = False
        self._capacity = binding.capacity
        self._closed = False
        self._memories = memories
        self._memory_words = binding.memory_words
        self._proof = _proof
        self._registration_lease = binding.registration_lease

    @property
    def capacity(self) -> ProfileSnapshotStreamCapacity:
        """Host-window budget and exact stream cardinality."""
        return self._capacity

    @property
    def memories(self) -> tuple[array[int], ...]:
        """Reusable arrays overwritten before each consumer callback."""
        return self._memories

    @property
    def registration(self) -> ProfileSnapshotHostRegistration:
        """All-or-none page-lock result for the bounded window arrays."""
        return self._registration_lease.registration

    def __enter__(self) -> Self:
        """Enter the explicit streaming-workspace scope.

        Returns:
            This workspace instance.

        """
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        """Release any page-locked window arrays at scope exit."""
        self.close()

    def close(self) -> None:
        """Release any page-locked window arrays exactly once.

        Raises:
            AcceleratorExecutionError: If a stream callback is active.

        """
        if self._closed:
            return
        if self._active:
            message = "resident snapshot stream workspace is active"
            raise AcceleratorExecutionError(message)
        self._closed = True
        self._registration_lease.release()

    def stream_snapshot(
        self,
        consumer: object,
    ) -> ProfileSnapshotStreamSummary:
        """Deliver one exact snapshot through ordered overwrite windows.

        Each callback receives results whose memory fields alias the prefix
        of ``memories``. A later callback may overwrite those same arrays.
        Consumers that need durable results must copy within the callback.

        Returns:
            Complete emitted item/window counts.

        Raises:
            AcceleratorExecutionError: If the workspace or callback is invalid.

        """
        if not callable(consumer):
            message = "resident snapshot stream consumer must be callable"
            raise AcceleratorExecutionError(message)
        admitted_consumer = cast(
            "Callable[[ProfileSnapshotWindow], None]",
            consumer,
        )
        memories = self._validated_memories()
        if self._active:
            message = "resident snapshot stream workspace is active"
            raise AcceleratorExecutionError(message)
        self._active = True
        try:
            return self._actions.stream(memories, admitted_consumer)
        finally:
            self._active = False

    def _validated_memories(self) -> tuple[array[int], ...]:
        if self._closed:
            message = "resident snapshot stream workspace is closed"
            raise AcceleratorExecutionError(message)
        if self._proof is not _SNAPSHOT_STREAM_WORKSPACE_PROOF:
            message = "resident snapshot stream workspace is forged"
            raise AcceleratorExecutionError(message)
        _validate_snapshot_workspace_memories(
            self._memories,
            self._memory_words,
        )
        self._registration_lease.validate_memories(self._memories)
        return self._memories


@final
class CudaProfileSnapshotWorkspace:
    """Explicit caller-owned arrays overwritten by repeated snapshots."""

    def __init__(
        self,
        *,
        memories: tuple[array[int], ...],
        binding: _SnapshotWorkspaceBinding,
        _proof: object,
    ) -> None:
        """Bind reusable arrays to one exact live resident session."""
        self._actions = binding.actions
        self._closed = False
        self._memories = memories
        self._memory_words = binding.memory_words
        self._proof = _proof
        self._registration_lease = binding.registration_lease

    @property
    def memories(self) -> tuple[array[int], ...]:
        """Arrays that each workspace call overwrites in place."""
        return self._memories

    @property
    def registration(self) -> ProfileSnapshotHostRegistration:
        """All-or-none page-lock result for these stable arrays."""
        return self._registration_lease.registration

    def __enter__(self) -> Self:
        """Enter the explicit caller-owned workspace scope.

        Returns:
            This workspace instance.

        """
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        """Release any page-locked host arrays at scope exit."""
        self.close()

    def close(self) -> None:
        """Release any page-locked arrays exactly once."""
        if self._closed:
            return
        self._closed = True
        self._registration_lease.release()

    def snapshot(self) -> tuple[ProfileRunResult, ...]:
        """Overwrite workspace arrays and return results aliasing those arrays.

        Returns:
            Complete results whose memory fields are workspace-owned arrays.

        """
        return self._actions.snapshot(self._validated_memories())

    def profile_snapshot(
        self,
    ) -> tuple[tuple[ProfileRunResult, ...], ProfileSnapshotPhaseProfile]:
        """Profile one overwrite of the reusable workspace arrays.

        Returns:
            Aliasing complete results plus transfer and decode diagnostics.

        """
        return self._actions.profile(self._validated_memories())

    def _validated_memories(self) -> tuple[array[int], ...]:
        if self._closed:
            message = "resident snapshot workspace is closed"
            raise AcceleratorExecutionError(message)
        if self._proof is not _SNAPSHOT_WORKSPACE_PROOF:
            message = "resident snapshot workspace is forged"
            raise AcceleratorExecutionError(message)
        _validate_snapshot_workspace_memories(
            self._memories,
            self._memory_words,
        )
        self._registration_lease.validate_memories(self._memories)
        return self._memories


@dataclass(frozen=True, slots=True)
class ProfileSnapshotPhaseProfile:
    """Diagnostic wall-clock phases for one explicit resident snapshot."""

    chunks: int
    decode_ns: int
    host_memory_allocate_ns: int
    memory_download_ns: int
    output_download_ns: int
    state_download_ns: int
    total_ns: int


@dataclass(slots=True)
class _SnapshotPhaseCounter:
    decode_ns: int = 0
    host_memory_allocate_ns: int = 0
    memory_download_ns: int = 0
    output_download_ns: int = 0
    state_download_ns: int = 0

    def freeze(
        self,
        *,
        chunks: int,
        total_ns: int,
    ) -> ProfileSnapshotPhaseProfile:
        """Freeze snapshot counters into public diagnostic evidence.

        Returns:
            Immutable aggregate snapshot timing evidence.

        """
        return ProfileSnapshotPhaseProfile(
            chunks=chunks,
            decode_ns=self.decode_ns,
            host_memory_allocate_ns=self.host_memory_allocate_ns,
            memory_download_ns=self.memory_download_ns,
            output_download_ns=self.output_download_ns,
            state_download_ns=self.state_download_ns,
            total_ns=total_ns,
        )


@dataclass(slots=True)
class _PhaseCounter:
    allocate_ns: int = 0
    decode_ns: int = 0
    download_ns: int = 0
    host_build_ns: int = 0
    kernel_ns: int = 0
    release_ns: int = 0
    upload_ns: int = 0

    def freeze(
        self,
        *,
        chunks: int,
        total_ns: int,
        validation_plan_ns: int,
    ) -> ProfileRunPhaseProfile:
        """Freeze accumulated phase counters into public evidence.

        Returns:
            Immutable aggregate timing evidence.

        """
        return ProfileRunPhaseProfile(
            allocate_ns=self.allocate_ns,
            chunks=chunks,
            decode_ns=self.decode_ns,
            download_ns=self.download_ns,
            host_build_ns=self.host_build_ns,
            kernel_ns=self.kernel_ns,
            release_ns=self.release_ns,
            total_ns=total_ns,
            upload_ns=self.upload_ns,
            validation_plan_ns=validation_plan_ns,
        )


@dataclass(frozen=True, slots=True)
class _WordBuffer:
    owner: array[int]
    view: HostWords


@dataclass(frozen=True, slots=True)
class _MemoryBuffer:
    owner: array[int]
    view: HostWords


@dataclass(frozen=True, slots=True)
class _HostBatch:
    count: int
    states: _WordBuffer
    memories: _MemoryBuffer | None
    memory_bytes: int
    shared_memory_source: _WordBuffer | None
    inputs: _WordBuffer
    outputs: _WordBuffer


@dataclass(frozen=True, slots=True)
class _ResidentChunk:
    """One independently launchable device-resident profile batch chunk."""

    count: int
    hosts: _HostBatch
    pointers: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class _ResidentContext:
    """CUDA handles and geometry shared by one scalable resident session."""

    geometry: ProfileRunGeometry
    kernel: ctypes.c_void_p
    runtime: CudaRuntime


def _profile_kernel_source(
    geometry: ProfileRunGeometry,
    crazy_geometry: ResidentCrazyGeometry | None,
) -> str:
    kernel_geometry = ResidentGeometry(
        interpreter_authority=False,
        eof_word=geometry.eof_word,
        input_instruction=geometry.input_instruction,
        memory_words=geometry.memory_words,
        output_instruction=geometry.output_instruction,
        word_modulus=geometry.word_modulus,
        word_trits=geometry.word_trits,
    )
    if crazy_geometry is None:
        return resident_kernel_source(kernel_geometry, _KERNEL_NAME)
    return resident_kernel_source(
        kernel_geometry,
        _KERNEL_NAME,
        crazy_geometry=crazy_geometry,
    )


@final
class CudaProfileRunAdapter:
    """Resident CUDA executor for one validated modular profile geometry."""

    def __init__(
        self,
        geometry: ProfileRunGeometry,
        device_id: int = 0,
        *,
        crazy_geometry: ResidentCrazyGeometry | None = None,
    ) -> None:
        """Compile one geometry-bound resident profile kernel.

        Raises:
            AcceleratorExecutionError: If CUDA compilation or loading fails.

        """
        admitted = geometry.validated()
        source = _profile_kernel_source(admitted, crazy_geometry)
        runtime = CudaRuntime(device_id)
        try:
            info = runtime.device_info
            module = runtime.compile_module(source, info.arch)
            kernel = runtime.get_kernel(module, _KERNEL_NAME.encode("ascii"))
        except AcceleratorExecutionError:
            runtime.close()
            raise
        self._capability = AcceleratorCapability(
            backend_id="cuda-profile-run",
            device_arch=info.arch,
            device_name=info.name,
        )
        self._closed = False
        self._geometry = admitted
        self._kernel = kernel
        self._module = module
        self._runtime = runtime

    def __enter__(self) -> Self:
        """Return this live adapter for scoped use.

        Returns:
            This adapter instance.

        """
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        """Release the CUDA module and context at scope exit."""
        self.close()

    def capability(self) -> AcceleratorCapability:
        """Return stable backend and selected-device identity.

        Returns:
            Stable CUDA backend and device metadata.

        """
        return self._capability

    def kernel_resources(self) -> CudaKernelResources:
        """Return Driver-reported resources for this compiled resident kernel.

        Returns:
            Resource observations for the exact loaded function.

        Raises:
            AcceleratorExecutionError: If the adapter is closed or CUDA fails.

        """
        if self._closed:
            message = "CUDA profile-run adapter is closed"
            raise AcceleratorExecutionError(message)
        return self._runtime.kernel_resources.measure(self._kernel)

    def close(self) -> None:
        """Release module and CUDA context exactly once."""
        if self._closed:
            return
        self._closed = True
        try:
            self._runtime.unload_module(self._module)
        finally:
            self._runtime.close()

    def evaluate(
        self,
        requests: Sequence[ProfileRunRequest],
    ) -> tuple[ProfileRunResult, ...]:
        """Execute complete scalable states in deterministic request order.

        Returns:
            Complete final states in request order.

        Raises:
            AcceleratorExecutionError: If the adapter is closed or CUDA fails.

        """
        if self._closed:
            message = "CUDA profile-run adapter is closed"
            raise AcceleratorExecutionError(message)
        validated = validate_profile_run_requests(
            self._geometry,
            tuple(requests),
        )
        if not validated:
            return ()
        plan = self._plan_validated(validated)
        results: list[ProfileRunResult] = []
        for chunk in plan.chunks:
            results.extend(
                self._evaluate_chunk(validated[chunk.start : chunk.stop])
            )
        return tuple(results)

    def open_session(
        self,
        requests: Sequence[ProfileRunRequest],
        *,
        max_runs: int,
    ) -> CudaProfileRunSession:
        """Upload scalable states once for repeated resident launches.

        Returns:
            Scoped session retaining complete state in device memory.

        Raises:
            AcceleratorExecutionError: If the adapter is closed or CUDA fails.
            InvalidPrimitiveBatchError: If session capacity is invalid.

        """
        if self._closed:
            message = "CUDA profile-run adapter is closed"
            raise AcceleratorExecutionError(message)
        if max_runs <= 0:
            message = f"resident max runs must be positive: {max_runs}"
            raise InvalidPrimitiveBatchError(message)
        validated = _validate_session_requests(
            self._geometry,
            tuple(requests),
            max_runs=max_runs,
        )
        chunks = self._build_session_chunks(validated, max_runs=max_runs)
        context = _ResidentContext(
            geometry=self._geometry,
            kernel=self._kernel,
            runtime=self._runtime,
        )
        return CudaProfileRunSession(
            context=context,
            chunks=chunks,
            max_runs=max_runs,
        )

    def profile_evaluate(
        self,
        requests: Sequence[ProfileRunRequest],
    ) -> tuple[tuple[ProfileRunResult, ...], ProfileRunPhaseProfile]:
        """Execute the ordinary path while recording diagnostic wall time.

        Returns:
            Exact results plus aggregate per-phase timing for this evaluation.

        Raises:
            AcceleratorExecutionError: If the adapter is closed or CUDA fails.

        """
        total_start = perf_counter_ns()
        if self._closed:
            message = "CUDA profile-run adapter is closed"
            raise AcceleratorExecutionError(message)
        phase = _PhaseCounter()
        plan_start = perf_counter_ns()
        validated = validate_profile_run_requests(
            self._geometry,
            tuple(requests),
        )
        plan = self._plan_validated(validated) if validated else None
        validation_plan_ns = perf_counter_ns() - plan_start
        if plan is None:
            total_ns = perf_counter_ns() - total_start
            return (), phase.freeze(
                chunks=0,
                total_ns=total_ns,
                validation_plan_ns=validation_plan_ns,
            )
        results: list[ProfileRunResult] = []
        for chunk in plan.chunks:
            results.extend(
                self._profile_chunk(
                    validated[chunk.start : chunk.stop],
                    phase,
                )
            )
        total_ns = perf_counter_ns() - total_start
        return tuple(results), phase.freeze(
            chunks=len(plan.chunks),
            total_ns=total_ns,
            validation_plan_ns=validation_plan_ns,
        )

    def plan(
        self,
        requests: Sequence[ProfileRunRequest],
    ) -> ResourcePlan:
        """Plan memory-safe scalable resident chunks from live device resources.

        Returns:
            Deterministic resource plan for the validated homogeneous batch.

        Raises:
            AcceleratorExecutionError: If the adapter is closed or planning
                rejects the measured resource budget.

        """
        if self._closed:
            message = "CUDA profile-run adapter is closed"
            raise AcceleratorExecutionError(message)
        validated = validate_profile_run_requests(
            self._geometry,
            tuple(requests),
        )
        return self._plan_validated(validated)

    def _profile_chunk(
        self,
        requests: tuple[ProfileRunRequest, ...],
        phase: _PhaseCounter,
    ) -> tuple[ProfileRunResult, ...]:
        start = perf_counter_ns()
        hosts = _build_host_batch(self._geometry, requests)
        phase.host_build_ns += perf_counter_ns() - start
        pointers = self._profile_uploads(hosts, phase)
        try:
            start = perf_counter_ns()
            self._runtime.launch(self._kernel, tuple(pointers), len(requests))
            phase.kernel_ns += perf_counter_ns() - start
            memories = self._profile_downloads(hosts, pointers, phase)
            start = perf_counter_ns()
            results = _decode_results(hosts, memories)
            phase.decode_ns += perf_counter_ns() - start
            return results
        finally:
            start = perf_counter_ns()
            _free_all(self._runtime, pointers)
            phase.release_ns += perf_counter_ns() - start

    def _profile_downloads(
        self,
        hosts: _HostBatch,
        pointers: list[int],
        phase: _PhaseCounter,
    ) -> tuple[array[int], ...]:
        start = perf_counter_ns()
        memories = _result_memories(self._geometry, hosts)
        phase.decode_ns += perf_counter_ns() - start
        start = perf_counter_ns()
        self._runtime.copy_from_device(hosts.states.view, pointers[0])
        _download_result_memories(
            self._runtime,
            self._geometry,
            device_pointer=pointers[1],
            memories=memories,
        )
        self._runtime.copy_from_device(hosts.outputs.view, pointers[3])
        phase.download_ns += perf_counter_ns() - start
        return memories

    def _profile_upload(
        self,
        host: _WordBuffer,
        phase: _PhaseCounter,
    ) -> int:
        start = perf_counter_ns()
        pointer = self._runtime.allocate(ctypes.sizeof(host.view))
        phase.allocate_ns += perf_counter_ns() - start
        try:
            start = perf_counter_ns()
            self._runtime.copy_to_device(pointer, host.view)
            phase.upload_ns += perf_counter_ns() - start
        except AcceleratorExecutionError:
            self._runtime.free(pointer)
            raise
        return pointer

    def _profile_memory_upload(
        self,
        hosts: _HostBatch,
        phase: _PhaseCounter,
    ) -> int:
        start = perf_counter_ns()
        pointer = self._runtime.allocate(hosts.memory_bytes)
        phase.allocate_ns += perf_counter_ns() - start
        try:
            start = perf_counter_ns()
            _initialize_device_memories(self._runtime, pointer, hosts)
            phase.upload_ns += perf_counter_ns() - start
        except AcceleratorExecutionError:
            self._runtime.free(pointer)
            raise
        return pointer

    def _profile_uploads(
        self,
        hosts: _HostBatch,
        phase: _PhaseCounter,
    ) -> list[int]:
        pointers: list[int] = []
        try:
            pointers.extend((self._profile_upload(hosts.states, phase),))
            pointers.extend((self._profile_memory_upload(hosts, phase),))
            pointers.extend((self._profile_upload(hosts.inputs, phase),))
            pointers.extend((self._profile_upload(hosts.outputs, phase),))
        except AcceleratorExecutionError:
            _free_all(self._runtime, pointers)
            raise
        return pointers

    def _evaluate_chunk(
        self,
        requests: tuple[ProfileRunRequest, ...],
    ) -> tuple[ProfileRunResult, ...]:
        hosts = _build_host_batch(self._geometry, requests)
        pointers: list[int] = []
        try:
            pointers.extend((_copy_words(self._runtime, hosts.states),))
            pointers.extend((_copy_memories(self._runtime, hosts),))
            pointers.extend((_copy_words(self._runtime, hosts.inputs),))
            pointers.extend((_copy_words(self._runtime, hosts.outputs),))
            self._runtime.launch(self._kernel, tuple(pointers), len(requests))
            memories = _download_complete_results(
                self._runtime,
                self._geometry,
                hosts=hosts,
                pointers=pointers,
            )
            return _decode_results(hosts, memories)
        finally:
            _free_all(self._runtime, pointers)

    def _build_session_chunks(
        self,
        requests: tuple[ProfileRunRequest, ...],
        *,
        max_runs: int,
    ) -> tuple[_ResidentChunk, ...]:
        if not requests:
            return ()
        plan = self._plan_session_validated(requests, max_runs=max_runs)
        chunks: list[_ResidentChunk] = []
        try:
            for chunk in plan.chunks:
                chunk_requests = requests[chunk.start : chunk.stop]
                hosts = _build_host_batch(
                    self._geometry,
                    chunk_requests,
                    output_budget_multiplier=max_runs,
                )
                pointers = _upload_host_batch(self._runtime, hosts)
                chunks.append(
                    _ResidentChunk(
                        count=len(chunk_requests),
                        hosts=hosts,
                        pointers=pointers,
                    )
                )
        except AcceleratorExecutionError, InvalidPrimitiveBatchError:
            _free_resident_chunks(self._runtime, chunks)
            raise
        return tuple(chunks)

    def _plan_session_validated(
        self,
        requests: tuple[ProfileRunRequest, ...],
        *,
        max_runs: int,
    ) -> ResourcePlan:
        item_bytes = tuple(
            _resident_item_bytes(
                self._geometry,
                request,
                output_budget_multiplier=max_runs,
            )
            for request in requests
        )
        max_items = (MAX_U32 // self._geometry.memory_words) + 1
        try:
            return plan_resident_batches(
                item_bytes,
                self._runtime.resources.snapshot(),
                fixed_chunk_bytes=_FIXED_CHUNK_BYTES,
                max_items_per_chunk=max_items,
            )
        except ResourceBudgetError as error:
            message = f"CUDA profile resource budget rejected session: {error}"
            raise AcceleratorExecutionError(message) from error

    def _plan_validated(
        self,
        requests: tuple[ProfileRunRequest, ...],
    ) -> ResourcePlan:
        item_bytes = tuple(
            _resident_item_bytes(self._geometry, request)
            for request in requests
        )
        max_items = (MAX_U32 // self._geometry.memory_words) + 1
        try:
            return plan_resident_batches(
                item_bytes,
                self._runtime.resources.snapshot(),
                fixed_chunk_bytes=_FIXED_CHUNK_BYTES,
                max_items_per_chunk=max_items,
            )
        except ResourceBudgetError as error:
            message = f"CUDA profile resource budget rejected batch: {error}"
            raise AcceleratorExecutionError(message) from error


class _CudaCloseScope(ABC):
    """Shared context-manager behavior for explicit CUDA lifetimes."""

    def __enter__(self) -> Self:
        """Enter one explicit CUDA resource scope.

        Returns:
            This live resource owner.

        """
        return self

    def __exit__(
        self,
        _exc_type: object,
        _exc_value: object,
        _traceback: object,
    ) -> None:
        """Release owned CUDA resources at scope exit."""
        self.close()

    @abstractmethod
    def close(self) -> None:
        """Release owned CUDA resources exactly once."""


@final
class CudaProfileRunSession(_CudaCloseScope):
    """Repeated scalable CUDA execution with complete state kept resident."""

    def __init__(
        self,
        *,
        context: _ResidentContext,
        chunks: tuple[_ResidentChunk, ...],
        max_runs: int,
    ) -> None:
        """Adopt already-uploaded resident chunks owned by one live adapter."""
        self._chunks = chunks
        self._closed = False
        self._context = context
        self._failed = False
        self._max_runs = max_runs
        self._runs_executed = 0
        self._snapshot_stream_active = False
        self._snapshot_registration_leases: list[
            _SnapshotHostRegistrationLease
        ] = []

    @property
    def runs_executed(self) -> int:
        """Number of complete resident launches committed by this session."""
        return self._runs_executed

    def advance(self) -> None:
        """Execute one bounded segment without materializing a host snapshot.

        Raises:
            AcceleratorExecutionError: If the session is closed, poisoned,
                exhausted, or a CUDA launch fails.

        """
        self._ensure_usable()
        self._ensure_snapshot_stream_inactive()
        if self._runs_executed >= self._max_runs:
            message = "resident CUDA profile session run budget exhausted"
            raise AcceleratorExecutionError(message)
        try:
            for chunk in self._chunks:
                self._context.runtime.launch(
                    self._context.kernel,
                    chunk.pointers,
                    chunk.count,
                )
        except AcceleratorExecutionError:
            self._failed = True
            raise
        self._runs_executed += 1

    @override
    def close(self) -> None:
        """Release registered host arrays and device allocations."""
        if self._closed:
            return
        self._ensure_snapshot_stream_inactive()
        self._closed = True
        failure = _release_snapshot_registration_leases(
            self._snapshot_registration_leases
        )
        try:
            _free_resident_chunks(self._context.runtime, self._chunks)
        except AcceleratorExecutionError as error:
            if failure is None:
                failure = error
        if failure is not None:
            raise failure

    def observe(self) -> tuple[ProfileRunObservation, ...]:
        """Download compact scalar outcomes without full resident memory.

        Returns:
            Compact observations in original request order.

        """
        self._ensure_usable()
        self._ensure_snapshot_stream_inactive()
        observations: list[ProfileRunObservation] = []
        for chunk in self._chunks:
            self._context.runtime.copy_from_device(
                chunk.hosts.states.view,
                chunk.pointers[0],
            )
            observations.extend(
                _decode_observations(chunk.hosts.states.owner, chunk.count)
            )
        return tuple(observations)

    def allocate_snapshot_workspace(
        self,
        *,
        host_registration_budget_bytes: int = 0,
    ) -> CudaProfileSnapshotWorkspace:
        """Allocate reusable arrays with optional bounded host registration.

        Returns:
            Workspace whose calls overwrite the same independent mutable arrays.
            Registration is all-or-none; budget or driver rejection falls back
            to the ordinary pageable workspace contract.

        """
        self._ensure_usable()
        self._ensure_snapshot_stream_inactive()
        count = sum(chunk.count for chunk in self._chunks)
        memories = tuple(
            array(_WORD_TYPECODE, [0]) * self._context.geometry.memory_words
            for _ in range(count)
        )
        lease = _prepare_snapshot_host_registration(
            self._context.runtime,
            memories,
            host_registration_budget_bytes,
        )
        self._snapshot_registration_leases.append(lease)
        binding = _SnapshotWorkspaceBinding(
            actions=_SnapshotWorkspaceActions(
                profile=self._profile_snapshot_into_memories,
                snapshot=self._snapshot_into_memories,
            ),
            memory_words=self._context.geometry.memory_words,
            registration_lease=lease,
        )
        return CudaProfileSnapshotWorkspace(
            memories=memories,
            binding=binding,
            _proof=_SNAPSHOT_WORKSPACE_PROOF,
        )

    def allocate_snapshot_overlap_workspace(
        self,
        *,
        host_memory_budget_bytes: int,
        host_registration_budget_bytes: int = 0,
    ) -> CudaProfileSnapshotOverlapWorkspace:
        """Allocate one or two fixed banks with explicit overlap admission.

        Returns:
            Workspace that prefetches only when two fully registered banks and
            at least two planned windows exist. Otherwise it falls back to the
            exact synchronous callback route with an observable reason.

        """
        self._ensure_usable()
        self._ensure_snapshot_stream_inactive()
        prepared = _prepare_snapshot_overlap(
            _SnapshotOverlapRequest(
                chunks=self._chunks,
                context=self._context,
                host_memory_budget_bytes=host_memory_budget_bytes,
                host_registration_budget_bytes=host_registration_budget_bytes,
                total_items=self._snapshot_count(),
            )
        )
        self._snapshot_registration_leases.append(prepared.registration_lease)
        binding = _SnapshotOverlapBinding(
            actions=_SnapshotOverlapActions(
                stream=self._stream_snapshot_overlap_into_banks,
            ),
            admission=prepared.admission,
            bank_items=prepared.capacity.bank_items,
            buffer_count=prepared.capacity.buffer_count,
            capacity=prepared.capacity,
            memory_words=self._context.geometry.memory_words,
            registration_lease=prepared.registration_lease,
        )
        return CudaProfileSnapshotOverlapWorkspace(
            memory_banks=prepared.memory_banks,
            binding=binding,
            _proof=_SNAPSHOT_OVERLAP_WORKSPACE_PROOF,
        )

    def allocate_snapshot_stream_workspace(
        self,
        *,
        host_memory_budget_bytes: int,
        host_registration_budget_bytes: int = 0,
    ) -> CudaProfileSnapshotStreamWorkspace:
        """Allocate one fixed reusable host window for complete snapshots.

        Returns:
            Workspace that emits every resident result in global request order.

        """
        self._ensure_usable()
        self._ensure_snapshot_stream_inactive()
        total_items = self._snapshot_count()
        memory_bytes = self._context.geometry.memory_words * _DEVICE_WORD_BYTES
        window_items = _snapshot_stream_window_items(
            total_items,
            memory_bytes,
            host_memory_budget_bytes,
        )
        memories = _fresh_result_memories(
            self._context.geometry,
            window_items,
        )
        lease = _prepare_snapshot_host_registration(
            self._context.runtime,
            memories,
            host_registration_budget_bytes,
        )
        self._snapshot_registration_leases.append(lease)
        window_bytes = window_items * memory_bytes
        capacity = ProfileSnapshotStreamCapacity(
            host_memory_budget_bytes=host_memory_budget_bytes,
            total_items=total_items,
            window_bytes=window_bytes,
            window_items=window_items,
        )
        binding = _SnapshotStreamBinding(
            actions=_SnapshotStreamActions(
                stream=self._stream_snapshot_into_memories,
            ),
            capacity=capacity,
            memory_words=self._context.geometry.memory_words,
            registration_lease=lease,
        )
        return CudaProfileSnapshotStreamWorkspace(
            memories=memories,
            binding=binding,
            _proof=_SNAPSHOT_STREAM_WORKSPACE_PROOF,
        )

    def _stream_snapshot_overlap_into_banks(
        self,
        memory_banks: tuple[tuple[array[int], ...], ...],
        consumer: Callable[[ProfileSnapshotWindow], None],
        admission: ProfileSnapshotOverlapAdmission,
    ) -> ProfileSnapshotOverlapSummary:
        self._ensure_usable()
        self._begin_snapshot_stream()
        try:
            for chunk in self._chunks:
                _download_resident_chunk_metadata(self._context, chunk)
            plans = _snapshot_window_plans(
                self._chunks,
                len(memory_banks[0]),
            )
            if admission.active:
                return self._stream_snapshot_overlap_plans(
                    memory_banks,
                    plans,
                    consumer,
                )
            return self._stream_snapshot_synchronous_plans(
                memory_banks,
                plans,
                consumer,
            )
        finally:
            self._snapshot_stream_active = False

    def _stream_snapshot_overlap_plans(
        self,
        memory_banks: tuple[tuple[array[int], ...], ...],
        plans: tuple[_SnapshotWindowPlan, ...],
        consumer: Callable[[ProfileSnapshotWindow], None],
    ) -> ProfileSnapshotOverlapSummary:
        stream = create_ordered_dtoh_stream(self._context.runtime)
        try:
            execution = _SnapshotOverlapExecution(
                consumer=consumer,
                context=self._context,
                memory_banks=memory_banks,
                stream=stream,
            )
            return _execute_snapshot_overlap_plans(execution, plans)
        finally:
            stream.close()

    def _stream_snapshot_synchronous_plans(
        self,
        memory_banks: tuple[tuple[array[int], ...], ...],
        plans: tuple[_SnapshotWindowPlan, ...],
        consumer: Callable[[ProfileSnapshotWindow], None],
    ) -> ProfileSnapshotOverlapSummary:
        emitted = 0
        bank = memory_banks[0]
        for plan in plans:
            _ = _validate_snapshot_overlap_banks(
                memory_banks,
                buffer_count=len(memory_banks),
                bank_items=len(bank),
                memory_words=self._context.geometry.memory_words,
            )
            active_memories = bank[: plan.count]
            _download_resident_memory_window(
                self._context,
                plan.chunk,
                active_memories,
                item_offset=plan.local_start,
            )
            _consume_snapshot_plan(plan, active_memories, consumer)
            emitted += plan.count
            _ = _validate_snapshot_overlap_banks(
                memory_banks,
                buffer_count=len(memory_banks),
                bank_items=len(bank),
                memory_words=self._context.geometry.memory_words,
            )
        return ProfileSnapshotOverlapSummary(
            items=emitted,
            prefetched_windows=0,
            windows=len(plans),
        )

    def _stream_snapshot_into_memories(
        self,
        memories: tuple[array[int], ...],
        consumer: Callable[[ProfileSnapshotWindow], None],
    ) -> ProfileSnapshotStreamSummary:
        self._ensure_usable()
        self._begin_snapshot_stream()
        global_start = 0
        windows = 0
        try:
            for chunk in self._chunks:
                _download_resident_chunk_metadata(self._context, chunk)
                local_start = 0
                while local_start < chunk.count:
                    _validate_snapshot_workspace_memories(
                        memories,
                        self._context.geometry.memory_words,
                    )
                    count = min(len(memories), chunk.count - local_start)
                    active_memories = memories[:count]
                    _download_resident_memory_window(
                        self._context,
                        chunk,
                        active_memories,
                        item_offset=local_start,
                    )
                    results = _decode_results_window(
                        chunk.hosts,
                        active_memories,
                        item_offset=local_start,
                    )
                    start = global_start + local_start
                    consumer(
                        ProfileSnapshotWindow(
                            results=results,
                            start=start,
                            stop=start + count,
                        )
                    )
                    _validate_snapshot_workspace_memories(
                        memories,
                        self._context.geometry.memory_words,
                    )
                    local_start += count
                    windows += 1
                global_start += chunk.count
        finally:
            self._snapshot_stream_active = False
        return ProfileSnapshotStreamSummary(
            items=global_start,
            windows=windows,
        )

    def _snapshot_into_memories(
        self,
        memories: tuple[array[int], ...],
    ) -> tuple[ProfileRunResult, ...]:
        self._ensure_usable()
        self._ensure_snapshot_stream_inactive()
        _validate_snapshot_workspace_count(memories, self._snapshot_count())
        results: list[ProfileRunResult] = []
        offset = 0
        for chunk in self._chunks:
            chunk_memories = memories[offset : offset + chunk.count]
            _download_resident_chunk_into(
                self._context,
                chunk,
                chunk_memories,
            )
            results.extend(_decode_results(chunk.hosts, chunk_memories))
            offset += chunk.count
        return tuple(results)

    def _profile_snapshot_into_memories(
        self,
        memories: tuple[array[int], ...],
    ) -> tuple[tuple[ProfileRunResult, ...], ProfileSnapshotPhaseProfile]:
        total_start = perf_counter_ns()
        self._ensure_usable()
        self._ensure_snapshot_stream_inactive()
        _validate_snapshot_workspace_count(memories, self._snapshot_count())
        phase = _SnapshotPhaseCounter()
        results: list[ProfileRunResult] = []
        offset = 0
        for chunk in self._chunks:
            chunk_memories = memories[offset : offset + chunk.count]
            _profile_snapshot_downloads_into(
                self._context,
                chunk,
                memories=chunk_memories,
                phase=phase,
            )
            start = perf_counter_ns()
            results.extend(_decode_results(chunk.hosts, chunk_memories))
            phase.decode_ns += perf_counter_ns() - start
            offset += chunk.count
        total_ns = perf_counter_ns() - total_start
        return tuple(results), phase.freeze(
            chunks=len(self._chunks),
            total_ns=total_ns,
        )

    def _snapshot_count(self) -> int:
        return sum(chunk.count for chunk in self._chunks)

    def snapshot(self) -> tuple[ProfileRunResult, ...]:
        """Materialize complete resident profile states on explicit demand.

        Returns:
            Complete scalable results in original request order.

        """
        self._ensure_usable()
        self._ensure_snapshot_stream_inactive()
        results: list[ProfileRunResult] = []
        for chunk in self._chunks:
            memories = _download_resident_chunk(
                self._context,
                chunk,
            )
            results.extend(_decode_results(chunk.hosts, memories))
        return tuple(results)

    def profile_snapshot(
        self,
    ) -> tuple[tuple[ProfileRunResult, ...], ProfileSnapshotPhaseProfile]:
        """Materialize one snapshot with phase-separated diagnostics.

        Returns:
            Complete results plus host allocation, transfer, and decode timing.

        """
        total_start = perf_counter_ns()
        self._ensure_usable()
        self._ensure_snapshot_stream_inactive()
        phase = _SnapshotPhaseCounter()
        results: list[ProfileRunResult] = []
        for chunk in self._chunks:
            memories = _profile_snapshot_downloads(
                self._context,
                chunk,
                phase,
            )
            start = perf_counter_ns()
            results.extend(_decode_results(chunk.hosts, memories))
            phase.decode_ns += perf_counter_ns() - start
        total_ns = perf_counter_ns() - total_start
        return tuple(results), phase.freeze(
            chunks=len(self._chunks),
            total_ns=total_ns,
        )

    def _begin_snapshot_stream(self) -> None:
        self._ensure_snapshot_stream_inactive()
        self._snapshot_stream_active = True

    def _ensure_snapshot_stream_inactive(self) -> None:
        if self._snapshot_stream_active:
            message = "resident CUDA profile snapshot stream is active"
            raise AcceleratorExecutionError(message)

    def _ensure_usable(self) -> None:
        if self._closed:
            message = "resident CUDA profile session is closed"
            raise AcceleratorExecutionError(message)
        if self._failed:
            message = (
                "resident CUDA profile session is poisoned after execution "
                "failure"
            )
            raise AcceleratorExecutionError(message)


def _validate_session_requests(
    geometry: ProfileRunGeometry,
    requests: tuple[ProfileRunRequest, ...],
    *,
    max_runs: int,
) -> tuple[ProfileRunRequest, ...]:
    validated = validate_profile_run_requests(geometry, requests)
    for request in validated:
        _ = _session_output_capacity(request, max_runs=max_runs)
    return validated


def _session_output_capacity(
    request: ProfileRunRequest,
    *,
    max_runs: int,
) -> int:
    output_capacity = len(request.output_bytes) + (
        request.step_budget * max_runs
    )
    if output_capacity > MAX_U32:
        message = (
            "resident profile session output capacity exceeds unsigned 32-bit "
            f"domain: {output_capacity}"
        )
        raise InvalidPrimitiveBatchError(message)
    return output_capacity


def _resident_item_bytes(
    geometry: ProfileRunGeometry,
    request: ProfileRunRequest,
    *,
    output_budget_multiplier: int = 1,
) -> int:
    output_capacity = _session_output_capacity(
        request,
        max_runs=output_budget_multiplier,
    )
    words = (
        STATE_WORDS
        + geometry.memory_words
        + len(request.input_bytes)
        + output_capacity
    )
    return words * _DEVICE_WORD_BYTES


def _encode_variable_state(
    requests: tuple[ProfileRunRequest, ...],
    *,
    output_budget_multiplier: int = 1,
) -> tuple[array[int], array[int], array[int]]:
    states = array("I")
    inputs = array("I")
    outputs = array("I")
    for request in requests:
        input_offset = len(inputs)
        inputs.extend(request.input_bytes)
        output_offset = len(outputs)
        output_capacity = _session_output_capacity(
            request,
            max_runs=output_budget_multiplier,
        )
        outputs.extend(request.output_bytes)
        additional_output = output_capacity - len(request.output_bytes)
        outputs.extend(0 for _slot in range(additional_output))
        _validate_buffer_offsets(input_offset, output_offset, output_capacity)
        states.extend((
            request.accumulator,
            request.code_pointer,
            request.data_pointer,
            input_offset,
            len(request.input_bytes),
            request.input_consumed,
            output_offset,
            len(request.output_bytes),
            output_capacity,
            request.step_budget,
            int(request.termination),
            int(RunStatus.BUDGET_EXHAUSTED),
            int(RunError.NONE),
            0,
            0,
            0,
        ))
    return states, inputs, outputs


def _validate_buffer_offsets(
    input_offset: int,
    output_offset: int,
    output_capacity: int,
) -> None:
    for value, label in (
        (input_offset, "resident input offset"),
        (output_offset, "resident output offset"),
        (output_capacity, "resident output capacity"),
    ):
        if value > MAX_U32:
            message = f"{label} outside unsigned 32-bit domain: {value}"
            raise AcceleratorExecutionError(message)


def _build_host_batch(
    geometry: ProfileRunGeometry,
    requests: tuple[ProfileRunRequest, ...],
    *,
    output_budget_multiplier: int = 1,
) -> _HostBatch:
    states, inputs, outputs = _encode_variable_state(
        requests,
        output_budget_multiplier=output_budget_multiplier,
    )
    memories, shared_memory_source, memory_bytes = _build_memory_buffers(
        requests
    )
    if not inputs:
        inputs.append(0)
    if not outputs:
        outputs.append(0)
    expected_memory_bytes = (
        geometry.memory_words * len(requests) * _DEVICE_WORD_BYTES
    )
    if memory_bytes != expected_memory_bytes:
        message = "profile host memory assembly invariant failed"
        raise AcceleratorExecutionError(message)
    return _HostBatch(
        count=len(requests),
        states=_word_buffer(states),
        memories=memories,
        memory_bytes=memory_bytes,
        shared_memory_source=shared_memory_source,
        inputs=_word_buffer(inputs),
        outputs=_word_buffer(outputs),
    )


def _build_memory_buffers(
    requests: tuple[ProfileRunRequest, ...],
) -> tuple[_MemoryBuffer | None, _WordBuffer | None, int]:
    first = requests[0].memory
    if len(requests) == 1:
        owner = _owned_memory_source(first)
        buffer = _memory_buffer(owner)
        return buffer, None, ctypes.sizeof(buffer.view)
    if all(request.memory is first for request in requests):
        source = _memory_source(first)
        memory_bytes = len(source) * len(requests) * _DEVICE_WORD_BYTES
        return None, _word_buffer(source), memory_bytes
    memories = array("I")
    for request in requests:
        memory = request.memory
        if isinstance(memory, ProfileMemoryImage):
            memories.extend(memory.words())
        else:
            memories.extend(memory)
    buffer = _memory_buffer(memories)
    return buffer, None, ctypes.sizeof(buffer.view)


def _memory_source(memory: array[int] | ProfileMemoryImage) -> array[int]:
    if isinstance(memory, ProfileMemoryImage):
        return memory.copy_words()
    return memory


def _owned_memory_source(memory: array[int] | ProfileMemoryImage) -> array[int]:
    if isinstance(memory, ProfileMemoryImage):
        return memory.copy_words()
    return array("I", memory)


def _upload_host_batch(
    runtime: CudaRuntime,
    hosts: _HostBatch,
) -> tuple[int, int, int, int]:
    pointers: list[int] = []
    try:
        pointers.extend((_copy_words(runtime, hosts.states),))
        pointers.extend((_copy_memories(runtime, hosts),))
        pointers.extend((_copy_words(runtime, hosts.inputs),))
        pointers.extend((_copy_words(runtime, hosts.outputs),))
    except AcceleratorExecutionError:
        _free_all(runtime, pointers)
        raise
    return (pointers[0], pointers[1], pointers[2], pointers[3])


def _copy_memories(runtime: CudaRuntime, hosts: _HostBatch) -> int:
    pointer = runtime.allocate(hosts.memory_bytes)
    try:
        _initialize_device_memories(runtime, pointer, hosts)
    except AcceleratorExecutionError:
        runtime.free(pointer)
        raise
    return pointer


def _initialize_device_memories(
    runtime: CudaRuntime,
    pointer: int,
    hosts: _HostBatch,
) -> None:
    source = hosts.shared_memory_source
    if source is None:
        memories = hosts.memories
        if memories is None:
            message = "profile memory upload has no host source"
            raise AcceleratorExecutionError(message)
        runtime.copy_to_device(pointer, memories.view)
        return
    stride_bytes = ctypes.sizeof(source.view)
    total_bytes = hosts.memory_bytes
    if stride_bytes == 0 or total_bytes % stride_bytes != 0:
        message = "profile shared-memory replication invariant failed"
        raise AcceleratorExecutionError(message)
    repeat_count = total_bytes // stride_bytes
    runtime.copy_to_device(
        pointer,
        source.view,
        repeat_count=repeat_count,
    )


def _copy_words(runtime: CudaRuntime, host: _WordBuffer) -> int:
    pointer = runtime.allocate(ctypes.sizeof(host.view))
    try:
        runtime.copy_to_device(pointer, host.view)
    except AcceleratorExecutionError:
        runtime.free(pointer)
        raise
    return pointer


def _snapshot_stream_window_items(
    total_items: int,
    memory_bytes: int,
    host_memory_budget_bytes: int,
) -> int:
    """Resolve a positive fixed window under the exact host-memory budget.

    Returns:
        Maximum resident items whose complete memories fit the budget.

    Raises:
        AcceleratorExecutionError: If the budget is invalid or too small.

    """
    if (
        type(host_memory_budget_bytes) is not int
        or host_memory_budget_bytes <= 0
    ):
        message = "snapshot stream host budget must be a positive integer"
        raise AcceleratorExecutionError(message)
    if total_items <= 0:
        message = "snapshot stream workspace requires resident items"
        raise AcceleratorExecutionError(message)
    if host_memory_budget_bytes < memory_bytes:
        message = (
            "snapshot stream host budget cannot hold one memory: "
            f"{host_memory_budget_bytes} < {memory_bytes}"
        )
        raise AcceleratorExecutionError(message)
    return min(total_items, host_memory_budget_bytes // memory_bytes)


def _prepare_snapshot_overlap(
    request: _SnapshotOverlapRequest,
) -> _PreparedSnapshotOverlap:
    context = request.context
    memory_bytes = context.geometry.memory_words * _DEVICE_WORD_BYTES
    buffer_count, bank_items = _snapshot_overlap_layout(
        request.total_items,
        memory_bytes,
        request.host_memory_budget_bytes,
    )
    memory_banks = tuple(
        _fresh_result_memories(context.geometry, bank_items)
        for _ in range(buffer_count)
    )
    lease = _prepare_snapshot_host_registration(
        context.runtime,
        tuple(memory for bank in memory_banks for memory in bank),
        request.host_registration_budget_bytes,
    )
    bank_bytes = bank_items * memory_bytes
    planned_windows = _snapshot_overlap_planned_windows(
        request.chunks, bank_items
    )
    capacity = ProfileSnapshotOverlapCapacity(
        bank_bytes=bank_bytes,
        bank_items=bank_items,
        buffer_count=buffer_count,
        host_memory_budget_bytes=request.host_memory_budget_bytes,
        planned_windows=planned_windows,
        retained_bytes=bank_bytes * buffer_count,
        total_items=request.total_items,
    )
    admission = ProfileSnapshotOverlapAdmission(
        fallback_reason=_snapshot_overlap_fallback_reason(
            buffer_count=buffer_count,
            registration=lease.registration,
        )
    )
    return _PreparedSnapshotOverlap(
        admission=admission,
        capacity=capacity,
        memory_banks=memory_banks,
        registration_lease=lease,
    )


def _snapshot_overlap_layout(
    total_items: int,
    memory_bytes: int,
    host_memory_budget_bytes: int,
) -> tuple[int, int]:
    """Resolve one- or two-bank layout under the total host-memory budget.

    Returns:
        Buffer count and equal per-bank item capacity.

    """
    one_bank_items = _snapshot_stream_window_items(
        total_items,
        memory_bytes,
        host_memory_budget_bytes,
    )
    if total_items == 1 or one_bank_items == 1:
        return 1, 1
    available_items = host_memory_budget_bytes // memory_bytes
    bank_items = min((total_items + 1) // 2, available_items // 2)
    if bank_items <= 0:
        return 1, 1
    return _SNAPSHOT_OVERLAP_BUFFER_COUNT, bank_items


def _snapshot_overlap_planned_windows(
    chunks: tuple[_ResidentChunk, ...],
    bank_items: int,
) -> int:
    return sum((chunk.count + bank_items - 1) // bank_items for chunk in chunks)


def _snapshot_overlap_fallback_reason(
    *,
    buffer_count: int,
    registration: ProfileSnapshotHostRegistration,
) -> str | None:
    if buffer_count < _SNAPSHOT_OVERLAP_BUFFER_COUNT:
        return _SNAPSHOT_OVERLAP_SINGLE_BUFFER
    return registration.fallback_reason


def _validate_snapshot_overlap_banks(
    memory_banks: tuple[tuple[array[int], ...], ...],
    *,
    buffer_count: int,
    bank_items: int,
    memory_words: int,
) -> tuple[array[int], ...]:
    if type(memory_banks) is not tuple or len(memory_banks) != buffer_count:
        message = "resident snapshot overlap buffer count changed"
        raise AcceleratorExecutionError(message)
    flattened: list[array[int]] = []
    for bank in memory_banks:
        if type(bank) is not tuple or len(bank) != bank_items:
            message = "resident snapshot overlap bank capacity changed"
            raise AcceleratorExecutionError(message)
        _validate_snapshot_workspace_memories(bank, memory_words)
        flattened.extend(bank)
    memories = tuple(flattened)
    _validate_snapshot_workspace_memories(memories, memory_words)
    return memories


def _validate_snapshot_workspace_memories(
    memories: tuple[array[int], ...],
    memory_words: int,
) -> None:
    if type(memories) is not tuple:
        message = "resident snapshot workspace memories must use a tuple"
        raise AcceleratorExecutionError(message)
    identities: set[int] = set()
    for memory in memories:
        _validate_snapshot_workspace_memory(memory, memory_words)
        identity = id(memory)
        if identity in identities:
            message = "resident snapshot workspace requires independent arrays"
            raise AcceleratorExecutionError(message)
        identities.add(identity)


def _validate_snapshot_workspace_memory(
    memory: object,
    memory_words: int,
) -> None:
    if not isinstance(memory, array):
        message = "resident snapshot workspace memory has wrong type"
        raise AcceleratorExecutionError(message)
    if (
        memory.typecode != _WORD_TYPECODE
        or memory.itemsize != _DEVICE_WORD_BYTES
    ):
        message = "resident snapshot workspace requires 32-bit array('I')"
        raise AcceleratorExecutionError(message)
    if len(memory) != memory_words:
        message = "resident snapshot workspace word count changed"
        raise AcceleratorExecutionError(message)


def _validate_snapshot_workspace_count(
    memories: tuple[array[int], ...],
    expected_count: int,
) -> None:
    if len(memories) != expected_count:
        message = "resident snapshot workspace count changed"
        raise AcceleratorExecutionError(message)


def _fresh_result_memories(
    geometry: ProfileRunGeometry,
    count: int,
) -> tuple[array[int], ...]:
    return tuple(
        array(_WORD_TYPECODE, [0]) * geometry.memory_words for _ in range(count)
    )


@dataclass(frozen=True, slots=True)
class _SnapshotWindowPlan:
    chunk: _ResidentChunk
    count: int
    global_start: int
    local_start: int


def _snapshot_window_plans(
    chunks: tuple[_ResidentChunk, ...],
    window_items: int,
) -> tuple[_SnapshotWindowPlan, ...]:
    plans: list[_SnapshotWindowPlan] = []
    global_start = 0
    for chunk in chunks:
        local_start = 0
        while local_start < chunk.count:
            count = min(window_items, chunk.count - local_start)
            plans.append(
                _SnapshotWindowPlan(
                    chunk=chunk,
                    count=count,
                    global_start=global_start + local_start,
                    local_start=local_start,
                )
            )
            local_start += count
        global_start += chunk.count
    return tuple(plans)


def _consume_snapshot_plan(
    plan: _SnapshotWindowPlan,
    memories: tuple[array[int], ...],
    consumer: Callable[[ProfileSnapshotWindow], None],
) -> None:
    results = _decode_results_window(
        plan.chunk.hosts,
        memories,
        item_offset=plan.local_start,
    )
    consumer(
        ProfileSnapshotWindow(
            results=results,
            start=plan.global_start,
            stop=plan.global_start + plan.count,
        )
    )


def _execute_snapshot_overlap_plans(
    execution: _SnapshotOverlapExecution,
    plans: tuple[_SnapshotWindowPlan, ...],
) -> ProfileSnapshotOverlapSummary:
    current = _start_snapshot_overlap_window(execution, 0, plans[0])
    _wait_for_memory_window(
        execution.stream,
        current.plan.count,
        execution.context.geometry.memory_words,
    )
    emitted = 0
    prefetched = 0
    for next_plan in plans[1:]:
        next_window = _start_snapshot_overlap_window(
            execution,
            1 - current.bank_index,
            next_plan,
        )
        prefetched += 1
        _consume_snapshot_plan(
            current.plan,
            current.memories,
            execution.consumer,
        )
        emitted += current.plan.count
        _ = _validate_snapshot_overlap_banks(
            execution.memory_banks,
            buffer_count=_SNAPSHOT_OVERLAP_BUFFER_COUNT,
            bank_items=len(execution.memory_banks[0]),
            memory_words=execution.context.geometry.memory_words,
        )
        _wait_for_memory_window(
            execution.stream,
            next_window.plan.count,
            execution.context.geometry.memory_words,
        )
        current = next_window
    _consume_snapshot_plan(
        current.plan,
        current.memories,
        execution.consumer,
    )
    emitted += current.plan.count
    _ = _validate_snapshot_overlap_banks(
        execution.memory_banks,
        buffer_count=_SNAPSHOT_OVERLAP_BUFFER_COUNT,
        bank_items=len(execution.memory_banks[0]),
        memory_words=execution.context.geometry.memory_words,
    )
    return ProfileSnapshotOverlapSummary(
        items=emitted,
        prefetched_windows=prefetched,
        windows=len(plans),
    )


def _start_snapshot_overlap_window(
    execution: _SnapshotOverlapExecution,
    bank_index: int,
    plan: _SnapshotWindowPlan,
) -> _ActiveSnapshotWindow:
    _ = _validate_snapshot_overlap_banks(
        execution.memory_banks,
        buffer_count=_SNAPSHOT_OVERLAP_BUFFER_COUNT,
        bank_items=len(execution.memory_banks[0]),
        memory_words=execution.context.geometry.memory_words,
    )
    memories = execution.memory_banks[bank_index][: plan.count]
    _submit_resident_memory_window(
        execution.stream,
        context=execution.context,
        plan=plan,
        memories=memories,
    )
    return _ActiveSnapshotWindow(
        bank_index=bank_index,
        memories=memories,
        plan=plan,
    )


def _submit_resident_memory_window(
    stream: CudaOrderedDtoHStream,
    *,
    context: _ResidentContext,
    plan: _SnapshotWindowPlan,
    memories: tuple[array[int], ...],
) -> None:
    stride_bytes = context.geometry.memory_words * _DEVICE_WORD_BYTES
    base_pointer = plan.chunk.pointers[1] + (plan.local_start * stride_bytes)
    for index, memory in enumerate(memories):
        stream.submit_copy_from_device(
            _word_buffer(memory).view,
            base_pointer + (index * stride_bytes),
        )


def _wait_for_memory_window(
    stream: CudaOrderedDtoHStream,
    item_count: int,
    memory_words: int,
) -> None:
    completed = stream.wait()
    expected_bytes = item_count * memory_words * _DEVICE_WORD_BYTES
    if completed.copies != item_count or completed.bytes != expected_bytes:
        message = "resident snapshot overlap transfer cardinality changed"
        raise AcceleratorExecutionError(message)


def _download_resident_chunk(
    context: _ResidentContext,
    chunk: _ResidentChunk,
) -> tuple[array[int], ...]:
    memories = _fresh_result_memories(context.geometry, chunk.count)
    _download_resident_chunk_into(context, chunk, memories)
    return memories


def _result_memories(
    geometry: ProfileRunGeometry,
    hosts: _HostBatch,
) -> tuple[array[int], ...]:
    if hosts.count == 1 and hosts.memories is not None:
        return (hosts.memories.owner,)
    return tuple(
        array("I", [0]) * geometry.memory_words for _ in range(hosts.count)
    )


def _download_result_memories(
    runtime: CudaRuntime,
    geometry: ProfileRunGeometry,
    *,
    device_pointer: int,
    memories: tuple[array[int], ...],
) -> None:
    stride_bytes = geometry.memory_words * _DEVICE_WORD_BYTES
    for index, memory in enumerate(memories):
        runtime.copy_from_device(
            _word_buffer(memory).view,
            device_pointer + (index * stride_bytes),
        )


def _profile_snapshot_downloads(
    context: _ResidentContext,
    chunk: _ResidentChunk,
    phase: _SnapshotPhaseCounter,
) -> tuple[array[int], ...]:
    start = perf_counter_ns()
    memories = _fresh_result_memories(context.geometry, chunk.count)
    phase.host_memory_allocate_ns += perf_counter_ns() - start
    _profile_snapshot_downloads_into(
        context,
        chunk,
        memories=memories,
        phase=phase,
    )
    return memories


def _profile_snapshot_downloads_into(
    context: _ResidentContext,
    chunk: _ResidentChunk,
    *,
    memories: tuple[array[int], ...],
    phase: _SnapshotPhaseCounter,
) -> None:
    start = perf_counter_ns()
    context.runtime.copy_from_device(chunk.hosts.states.view, chunk.pointers[0])
    phase.state_download_ns += perf_counter_ns() - start

    start = perf_counter_ns()
    _download_result_memories(
        context.runtime,
        context.geometry,
        device_pointer=chunk.pointers[1],
        memories=memories,
    )
    phase.memory_download_ns += perf_counter_ns() - start

    start = perf_counter_ns()
    context.runtime.copy_from_device(
        chunk.hosts.outputs.view, chunk.pointers[3]
    )
    phase.output_download_ns += perf_counter_ns() - start


def _download_complete_results(
    runtime: CudaRuntime,
    geometry: ProfileRunGeometry,
    *,
    hosts: _HostBatch,
    pointers: Sequence[int],
) -> tuple[array[int], ...]:
    memories = _result_memories(geometry, hosts)
    runtime.copy_from_device(hosts.states.view, pointers[0])
    _download_result_memories(
        runtime,
        geometry,
        device_pointer=pointers[1],
        memories=memories,
    )
    runtime.copy_from_device(hosts.outputs.view, pointers[3])
    return memories


def _download_resident_chunk_metadata(
    context: _ResidentContext,
    chunk: _ResidentChunk,
) -> None:
    context.runtime.copy_from_device(chunk.hosts.states.view, chunk.pointers[0])
    context.runtime.copy_from_device(
        chunk.hosts.outputs.view,
        chunk.pointers[3],
    )


def _download_resident_memory_window(
    context: _ResidentContext,
    chunk: _ResidentChunk,
    memories: tuple[array[int], ...],
    *,
    item_offset: int,
) -> None:
    stride_bytes = context.geometry.memory_words * _DEVICE_WORD_BYTES
    _download_result_memories(
        context.runtime,
        context.geometry,
        device_pointer=chunk.pointers[1] + (item_offset * stride_bytes),
        memories=memories,
    )


def _download_resident_chunk_into(
    context: _ResidentContext,
    chunk: _ResidentChunk,
    memories: tuple[array[int], ...],
) -> None:
    context.runtime.copy_from_device(chunk.hosts.states.view, chunk.pointers[0])
    _download_result_memories(
        context.runtime,
        context.geometry,
        device_pointer=chunk.pointers[1],
        memories=memories,
    )
    context.runtime.copy_from_device(
        chunk.hosts.outputs.view,
        chunk.pointers[3],
    )


def _decode_observations(
    states: array[int],
    count: int,
) -> tuple[ProfileRunObservation, ...]:
    observations: list[ProfileRunObservation] = []
    for index in range(count):
        base = index * STATE_WORDS
        observations.append(
            ProfileRunObservation(
                accumulator=states[base],
                code_pointer=states[base + 1],
                data_pointer=states[base + 2],
                error=RunError(states[base + _ERROR_INDEX]),
                error_pointer=states[base + _ERROR_POINTER_INDEX],
                error_value=states[base + _ERROR_VALUE_INDEX],
                input_consumed=states[base + 5],
                output_length=states[base + 7],
                status=RunStatus(states[base + _STATUS_INDEX]),
                steps=states[base + _STEPS_INDEX],
                termination=StepTermination(states[base + 10]),
            )
        )
    return tuple(observations)


def _decode_results_window(
    hosts: _HostBatch,
    memories: tuple[array[int], ...],
    *,
    item_offset: int,
) -> tuple[ProfileRunResult, ...]:
    if item_offset < 0 or item_offset + len(memories) > hosts.count:
        message = "profile result window outside resident chunk"
        raise AcceleratorExecutionError(message)
    states = hosts.states.owner
    outputs = hosts.outputs.owner
    results: list[ProfileRunResult] = []
    for local_index, memory in enumerate(memories):
        index = item_offset + local_index
        base = index * STATE_WORDS
        output_offset = states[base + 6]
        output_len = states[base + 7]
        results.append(
            ProfileRunResult(
                accumulator=states[base],
                code_pointer=states[base + 1],
                data_pointer=states[base + 2],
                error=RunError(states[base + _ERROR_INDEX]),
                error_pointer=states[base + _ERROR_POINTER_INDEX],
                error_value=states[base + _ERROR_VALUE_INDEX],
                input_consumed=states[base + 5],
                memory=memory,
                output_bytes=tuple(
                    outputs[output_offset : output_offset + output_len]
                ),
                status=RunStatus(states[base + _STATUS_INDEX]),
                steps=states[base + _STEPS_INDEX],
                termination=StepTermination(states[base + 10]),
            )
        )
    return tuple(results)


def _decode_results(
    hosts: _HostBatch,
    memories: tuple[array[int], ...],
) -> tuple[ProfileRunResult, ...]:
    if len(memories) != hosts.count:
        message = "profile result memory count invariant failed"
        raise AcceleratorExecutionError(message)
    return _decode_results_window(hosts, memories, item_offset=0)


def _free_resident_chunks(
    runtime: CudaRuntime,
    chunks: list[_ResidentChunk] | tuple[_ResidentChunk, ...],
) -> None:
    for chunk in reversed(chunks):
        _free_all(runtime, list(chunk.pointers))


def _free_all(runtime: CudaRuntime, pointers: list[int]) -> None:
    while pointers:
        runtime.free(pointers.pop())


def _memory_buffer(owner: array[int]) -> _MemoryBuffer:
    view_type = ctypes.c_uint32 * len(owner)
    return _MemoryBuffer(owner=owner, view=view_type.from_buffer(owner))


def _word_buffer(owner: array[int]) -> _WordBuffer:
    view_type = ctypes.c_uint32 * len(owner)
    return _WordBuffer(owner=owner, view=view_type.from_buffer(owner))
