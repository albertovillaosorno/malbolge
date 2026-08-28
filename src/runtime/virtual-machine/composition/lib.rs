// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Public classic and profile-driven Malbolge execution semantics.
// - Must-Not:
//   - Encode JIT, accelerator, compiler, or implicit historical behavior.
// - Allows:
//   - Inputs: canonical profiles, validated source, machine state, byte input.
//   - Outputs: deterministic classic/profiled transitions, I/O, diagnostics.
//   - Side effects: none outside caller-owned in-memory VM state.
// - Split-When:
//   - Split when another machine profile requires an independent semantic API.
// - Merge-When:
//   - Merge when another VM module owns the same classic transition boundary.
// - Summary:
//   - Safe-Rust classic and schema-v2 profile-driven Malbolge interpreters.
// - Description:
//   - Keeps classic type safety while admitting explicit scalable profiles.
// - Usage:
//   - Used by interpreters, verification, compiler tests, and future executors.
// - Defaults:
//   - `Machine` stays classic; `ProfileMachine` requires explicit profile.
//

//! Safe deterministic classic and profile-driven Malbolge interpreters.

#[path = "../domain/annotated.rs"]
mod annotated;
#[path = "../application/batch.rs"]
mod batch;
#[path = "../domain/capsule.rs"]
mod capsule;
#[path = "../domain/cycle.rs"]
mod cycle;
#[path = "../domain/differential.rs"]
mod differential;
#[path = "../domain/execution.rs"]
mod execution;
#[path = "../domain/execution_ir.rs"]
mod execution_ir;
#[path = "../contract/host_capability.rs"]
mod host_capability;
#[path = "../application/host_capability_dispatch.rs"]
mod host_capability_dispatch;
#[path = "../contract/host_capability_mouse.rs"]
mod host_capability_mouse;
#[path = "../port-outbound/host_capability.rs"]
mod host_capability_port;
#[path = "../contract/host_capability_telemetry.rs"]
mod host_capability_telemetry;
#[path = "../contract/host_capability_time.rs"]
mod host_capability_time;
#[path = "../adapter-outbound/host_capability_time.rs"]
mod host_capability_time_adapter;
#[path = "../domain/instruction.rs"]
pub(crate) mod instruction;
#[path = "../domain/loader.rs"]
mod loader;
#[path = "../application/logical.rs"]
mod logical;
#[path = "../domain/machine.rs"]
mod machine;
#[path = "../domain/memory.rs"]
mod memory;
#[path = "../domain/mode.rs"]
mod mode;
#[path = "../port-outbound/parallel.rs"]
mod parallel_port;
#[path = "../domain/profile.rs"]
mod profile;
#[path = "../domain/profile_machine.rs"]
mod profile_machine;
#[path = "../domain/profile_trace.rs"]
mod profile_trace;
#[path = "../domain/profile_width.rs"]
mod profile_width;
#[path = "../adapter-outbound/threading.rs"]
mod threading;
#[path = "../domain/trace.rs"]
mod trace;
#[path = "../contract/word.rs"]
mod word;

pub use annotated::{
    AnnotatedLoadError, AnnotatedSourceError, AnnotatedSourceLocation,
    CanonicalizedAnnotatedSource, canonicalize_annotated_source,
    format_annotated_source,
};
pub use batch::{
    BatchBackendCompletion, BatchBackendRequest, BatchError,
    BatchExecutionBackend, BatchExecutionOrigin, BatchExecutionReport,
    BatchRequest, BatchResult, ProfileBatchBackendCompletion,
    ProfileBatchBackendRequest, ProfileBatchExecutionBackend,
    ProfileBatchRequest, ProfileBatchResult, execute_batch,
    execute_batch_parallel_with, execute_batch_with_backend,
    execute_batch_with_backend_report, execute_profile_batch,
    execute_profile_batch_parallel_with, execute_profile_batch_with_backend,
    execute_profile_batch_with_backend_report,
};
pub use capsule::{
    Capsule, CapsuleBuildError, CapsuleError, build_capsule, parse_capsule,
};
pub use cycle::{
    CycleDetectionError, DiagnosticCycleDetector, DiagnosticCycleObservation,
    ExactCycleDetector, ExactCycleObservation,
};
pub use differential::{
    DifferentialCandidate, DifferentialVerificationError,
    verify_differential_candidates,
};
pub use execution::{ExecutionError, ExecutionErrorKind, ExecutionMachine};
pub use execution_ir::{
    EFFECT_IR_VERSION, EffectOp, IrEncodingError, MemoryLiveIn,
    RegionEffectProgram, StepProgramProjectionError,
};
pub use host_capability::{
    HOST_CALL_FLAG_NONBLOCKING, HOST_CAPABILITY_ABI_VERSION,
    HOST_CAPABILITY_DESCRIPTOR_WIRE_SIZE, HOST_CAPABILITY_FLAG_AVAILABLE,
    HOST_CAPABILITY_FLAG_MAY_BLOCK, HOST_CAPABILITY_FLAG_PARTIAL_PROGRESS,
    HOST_CAPABILITY_FRAME_WIRE_SIZE, HOST_CAPABILITY_SPAN_WIRE_SIZE,
    HostCapabilityDescriptor, HostCapabilityError, HostCapabilityFrame,
    HostCapabilityResponseBuffers, HostCapabilitySpan, HostCapabilityStatus,
    commit_host_capability_response, discover_host_capability,
    discover_host_capability_wire, validate_host_capability_registry,
    validate_host_capability_response, validate_host_capability_wire_registry,
};
pub use host_capability_dispatch::{
    HOST_BUILTIN_CAPABILITY_COUNT, HostBuiltinCapabilityAvailability,
    HostCapabilityAvailability, HostCapabilityDispatchError,
    HostCapabilityDispatchResult, dispatch_builtin_host_capability,
    dispatch_host_capability, host_builtin_capability_registry,
};
pub use host_capability_mouse::{
    HOST_RELATIVE_MOUSE_CAPTURE_CAPABILITY_ID,
    HOST_RELATIVE_MOUSE_CAPTURE_V1_OPERATION,
    HOST_RELATIVE_MOUSE_CAPTURE_V1_REQUEST_SIZE,
    HOST_RELATIVE_MOUSE_CAPTURE_V1_VERSION, HostRelativeMouseCaptureV1,
    decode_host_relative_mouse_capture_v1,
    encode_host_relative_mouse_capture_v1,
    host_relative_mouse_capture_v1_descriptor,
    validate_host_relative_mouse_capture_v1_call,
};
pub use host_capability_port::{
    HostCapabilityInvocation, HostCapabilityTransport,
    HostCapabilityTransportResponse,
};
pub use host_capability_telemetry::{
    HOST_EXECUTION_TELEMETRY_CAPABILITY_ID,
    HOST_EXECUTION_TELEMETRY_V1_HEADER_SIZE,
    HOST_EXECUTION_TELEMETRY_V1_OPERATION, HOST_EXECUTION_TELEMETRY_V1_VERSION,
    HostExecutionTelemetryV1, decode_host_execution_telemetry_v1,
    encode_host_execution_telemetry_v1, host_execution_telemetry_v1_descriptor,
    validate_host_execution_telemetry_v1_call,
};
pub use host_capability_time::{
    HOST_MONOTONIC_TIME_CAPABILITY_ID, HOST_MONOTONIC_TIME_V1_OPERATION,
    HOST_MONOTONIC_TIME_V1_RESULT_SIZE, HOST_MONOTONIC_TIME_V1_VERSION,
    HOST_SLEEP_CAPABILITY_ID, HOST_SLEEP_V1_OPERATION,
    HOST_SLEEP_V1_REQUEST_SIZE, HOST_SLEEP_V1_VERSION,
    decode_host_monotonic_time_v1_result, decode_host_sleep_v1_request,
    encode_host_monotonic_time_v1_result, encode_host_sleep_v1_request,
    host_monotonic_time_v1_descriptor, host_sleep_v1_descriptor,
    validate_host_monotonic_time_v1_call,
    validate_host_monotonic_time_v1_result, validate_host_sleep_v1_call,
};
pub use host_capability_time_adapter::{
    SystemTimingHostCapabilityTransport, SystemTimingTransportError,
};
pub use instruction::decode_instruction;
pub use loader::{LoadError, is_source_whitespace, load};
pub use logical::{
    LogicalConcurrencyError, LogicalJoinError, LogicalTask, LogicalTaskId,
    LogicalTaskResult, ProfileLogicalJoinError, ProfileLogicalTask,
    ProfileLogicalTaskResult, execute_logical_tasks,
    execute_logical_tasks_parallel_with, execute_profile_logical_tasks,
    execute_profile_logical_tasks_parallel_with, join_logical_outputs,
    join_profile_logical_outputs,
};
pub use machine::{
    InterpreterUndefinedBehavior, Machine, MachineError, MachineIoState,
    MachineState, MachineStateError, Registers, RunOutcome, StepOutcome,
    Termination,
};
pub use memory::{Memory, MemoryError};
pub use mode::{ExecutionMode, ExecutionModeParseError};
pub use parallel_port::{ParallelExecutionError, ParallelExecutionPort};
pub use profile::{
    PortableProfileRequirementError, ProfileDescriptor, ProfileFeature,
    ProfileKind, ProfileRequirementError, ProfileRequirementErrorKind,
    RuntimeCapability, RuntimeProfileRequirementError,
    TargetProfileRequirement, current_profile, historical_profile,
    preflight_portable_profile_requirement, preflight_profile,
    preflight_runtime_requirement, safe_rust_classic_capability,
    safe_rust_profiled_capability, target_profile,
};
pub use profile_machine::{
    ProfileLoadError, ProfileMachine, ProfileMachineError,
    ProfileMachineIoState, ProfileMachineState, ProfileRegisterName,
    ProfileRegisters, decode_profile_instruction, encrypt_profile_cell,
    profile_cell_decodes_to_no_operation, profile_cell_is_graphical,
    profile_pointer_successor, profile_rotate,
};
pub use profile_trace::{
    ProfileMachineObservation, ProfileMemoryDelta, ProfileMemoryRead,
    ProfileMemoryReads, ProfileMemoryWrite, ProfileStepTrace,
};
pub use profile_width::{
    ProfileWidthProofKind, ProfileWidthVerificationError,
    VerifiedProfileExecutionGeometry, verify_initial_halt_profile_width,
};
pub use threading::ScopedThreadParallelism;
pub use trace::{
    MachineObservation, MemoryDelta, MemoryWrite, StepTrace, TraceInput,
};
pub use word::{
    MAX_WORD_VALUE, MEMORY_WORDS, Word, WordError, profile_crazy,
    profile_eof_word, profile_low_byte,
};

/// Executes independent classic requests across scoped host workers.
///
/// Results remain in input order regardless of physical completion order.
///
/// # Errors
///
/// Returns [`BatchError`] when zero workers are requested or a worker panics.
pub fn execute_batch_parallel(
    requests: Vec<BatchRequest>,
    worker_count: usize,
) -> Result<Vec<BatchResult>, BatchError> {
    execute_batch_parallel_with::<ScopedThreadParallelism>(
        requests,
        worker_count,
    )
}

/// Executes independent logical tasks across scoped host workers.
///
/// # Errors
///
/// Returns duplicate logical identity or shared batch scheduler failure.
pub fn execute_logical_tasks_parallel(
    tasks: Vec<LogicalTask>,
    worker_count: usize,
) -> Result<Vec<LogicalTaskResult>, LogicalConcurrencyError> {
    execute_logical_tasks_parallel_with::<ScopedThreadParallelism>(
        tasks,
        worker_count,
    )
}

/// Executes independent profile requests across scoped host workers.
///
/// Results retain canonical profile identity and input order.
///
/// # Errors
///
/// Returns [`BatchError`] when zero workers are requested or a worker panics.
pub fn execute_profile_batch_parallel(
    requests: Vec<ProfileBatchRequest>,
    worker_count: usize,
) -> Result<Vec<ProfileBatchResult>, BatchError> {
    execute_profile_batch_parallel_with::<ScopedThreadParallelism>(
        requests,
        worker_count,
    )
}

/// Executes independent profile logical tasks across scoped host workers.
///
/// # Errors
///
/// Returns duplicate logical identity or shared batch scheduler failure.
pub fn execute_profile_logical_tasks_parallel(
    tasks: Vec<ProfileLogicalTask>,
    worker_count: usize,
) -> Result<Vec<ProfileLogicalTaskResult>, LogicalConcurrencyError> {
    execute_profile_logical_tasks_parallel_with::<ScopedThreadParallelism>(
        tasks,
        worker_count,
    )
}
