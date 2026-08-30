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
//   - Product execution-IR canonicalization and native-cache identity evidence.
// - Must-Not:
//   - Depend on architecture machine code or state-graph private internals.
// - Allows:
//   - Inputs: public VM value types and product execution/cache modules.
//   - Outputs: deterministic encoding and collision-safe cache-key assertions.
//   - Side effects: test-process allocation only.
// - Split-When:
//   - Split when native backend differential fixtures need separate lifecycle.
// - Merge-When:
//   - Merge when product tiered execution tests own the same identity surface.
// - Summary:
//   - Proves portable IR and host-target cache identity are
//   - architecture-stable.
// - Description:
//   - Mutates semantic and target fields and forces bucket collisions.
// - Usage:
//   - Auto-discovered by the root Cargo workspace.
// - Defaults:
//   - Full canonical equality, never a digest alone, decides reuse.
//

//! Product tiered-execution identity and cache-key conformance.

#[path = "../src/runtime/tiered-execution/composition/tier/cached_cycle.rs"]
pub mod cached_cycle;
#[path = "../src/runtime/tiered-execution/composition/tier/cached_retry.rs"]
pub mod cached_retry;
#[path = "../src/runtime/tiered-execution/composition/tier/scheduler.rs"]
pub mod continuation_scheduler;
#[path = "../src/runtime/tiered-execution/adapter-outbound/cache/main.rs"]
pub mod execution_cache;
#[path = "../src/runtime/tiered-execution/adapter-outbound/native/main.rs"]
pub mod execution_native;
#[path = "../src/runtime/tiered-execution/composition/tier/geometry_handoff.rs"]
pub mod geometry_interpreter_handoff;
#[path = "../src/runtime/tiered-execution/composition/tier/geometry_native.rs"]
pub mod geometry_native_admission;
#[path = "../src/runtime/tiered-execution/composition/tier/geometry_jump.rs"]
pub mod geometry_native_initial_jump_data;
#[path = "../src/runtime/tiered-execution/composition/tier/geometry_jcache.rs"]
pub mod geometry_native_jump_rotate_halt_cache;
#[path = "../src/runtime/tiered-execution/composition/tier/geometry_jmcache.rs"]
pub mod geometry_native_jump_rotate_halt_multi_cache;
#[path = "../src/runtime/tiered-execution/composition/tier/geometry_jrh.rs"]
pub mod geometry_native_jump_rotate_halt_sequence;
#[path = "../src/runtime/tiered-execution/composition/tier/geometry_noop.rs"]
pub mod geometry_native_no_operation;
#[path = "../src/runtime/tiered-execution/composition/tier/geometry_cache.rs"]
pub mod geometry_native_pair_cache;
#[path = "../src/runtime/tiered-execution/composition/tier/geometry_rotate.rs"]
pub mod geometry_native_rotate;
#[path = "../src/runtime/tiered-execution/composition/tier/geometry_rhcache.rs"]
pub mod geometry_native_rotate_pair_cache;
#[path = "../src/runtime/tiered-execution/composition/tier/geometry_rotseq.rs"]
pub mod geometry_native_rotate_sequence;
#[path = "../src/runtime/tiered-execution/composition/tier/geometry_seq.rs"]
pub mod geometry_native_sequence;
#[path = "../src/runtime/tiered-execution/composition/tier/handoff.rs"]
pub mod interpreter_handoff;
#[path = "../src/runtime/tiered-execution/composition/tier/leased_retry.rs"]
pub mod leased_retry;
#[path = "../src/runtime/tiered-execution/composition/tier/native_retry.rs"]
pub mod native_retry;
#[path = "../src/runtime/tiered-execution/composition/tier/retry_cycle.rs"]
pub mod retry_cycle;
#[path = "../src/runtime/tiered-execution/composition/tier/retry_planner.rs"]
pub mod retry_planner;
#[path = "../src/runtime/tiered-execution/composition/tier/retry_policy.rs"]
pub mod retry_policy;
#[path = "../src/runtime/tiered-execution/composition/tier/retry_router.rs"]
pub mod retry_router;
#[path = "../src/runtime/tiered-execution/composition/tier/retry_turn.rs"]
pub mod retry_turn;

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;
use std::path::Path;
use std::str::from_utf8;
use std::sync::Arc;
use std::thread;

use cached_cycle::{
    NativeContinuationCachedRetryAttempt,
    NativeContinuationCachedRetryCompletion,
    NativeContinuationCachedRetryCycleFailure,
    NativeContinuationCachedRetryCycleOutcome,
    NativeContinuationCachedRetryCycleRequest,
    NativeContinuationCachedRetryInterpreterOutcome,
    NativeContinuationCachedRetryLatencyCodecError,
    NativeContinuationCachedRetryLatencyHistogram,
    NativeContinuationCachedRetryLatencyHistogramError,
    NativeContinuationCachedRetryLatencyHistogramSnapshot,
    NativeContinuationCachedRetryLatencyMergeError,
    NativeContinuationCachedRetryLatencySample,
    NativeContinuationCachedRetryLatencySnapshotCounts,
    NativeContinuationCachedRetryLatencySnapshotError,
    NativeContinuationCachedRetryLatencySnapshotRange,
    NativeContinuationCachedRetryNativeFailure,
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryAssessment,
    NativeContinuationCachedRetryTelemetryAssessmentMaximums,
    NativeContinuationCachedRetryTelemetryAssessmentMinimums,
    NativeContinuationCachedRetryTelemetryAssessmentSignal,
    NativeContinuationCachedRetryTelemetryAssessmentThresholds,
    NativeContinuationCachedRetryTelemetryCodecError,
    NativeContinuationCachedRetryTelemetryObservation,
    NativeContinuationCachedRetryTelemetrySnapshotError,
    NativeContinuationCachedRetryTelemetrySnapshotMetadata,
    NativeContinuationCachedRetryTelemetrySource,
    NativeContinuationCachedRetryTelemetryWindow,
    NativeContinuationCachedRetryTelemetryWindowCounter,
    NativeContinuationCachedRetryTelemetryWindowError,
    NativeContinuationCachedRetryTelemetryWindowSnapshot,
    assess_cached_retry_telemetry, decode_cached_retry_latency_snapshot,
    decode_cached_retry_telemetry_snapshot,
    encode_cached_retry_latency_snapshot,
    encode_cached_retry_telemetry_snapshot, execute_cached_native_retry_cycle,
    summarize_cached_retry_attempts,
};
use cached_retry::{
    NativeContinuationCachedRetryFailure, execute_cached_native_retry,
};
use continuation_scheduler::{
    NativeContinuationScheduleDecision, NativeContinuationScheduleOutcome,
    NativeContinuationScheduleStopReason, NativeContinuationScheduleSuspension,
    NativeContinuationYieldTarget, schedule_native_interpreter_handoff,
};
use execution_cache::{
    HostIsa, HostOperatingSystem, NativeArtifactCache, NativeArtifactKey,
    NativeIdentityError, NativeTargetConfig, NativeTargetIdentity,
    RegionEffectIdentity,
};
use execution_native::{
    BootstrapCompilerError, BootstrapProfilePreflightError,
    CLANG_C23_BOOTSTRAP_BACKEND_ID, CLANG_C23_BOOTSTRAP_BACKEND_REVISION,
    CachedPreflightedExecutionTier, CoffAdmissionError,
    DIRECT_CRAZY_BACKEND_ID, DIRECT_CRAZY_BACKEND_REVISION,
    DIRECT_DEOPT_BACKEND_ID, DIRECT_DEOPT_BACKEND_REVISION,
    DIRECT_EXECUTION_GEOMETRY_INITIAL_HALT_BACKEND_ID,
    DIRECT_EXECUTION_GEOMETRY_INITIAL_HALT_BACKEND_REVISION,
    DIRECT_EXECUTION_GEOMETRY_INITIAL_JUMP_DATA_BACKEND_ID,
    DIRECT_EXECUTION_GEOMETRY_INITIAL_JUMP_DATA_BACKEND_REVISION,
    DIRECT_EXECUTION_GEOMETRY_NO_OPERATION_BACKEND_ID,
    DIRECT_EXECUTION_GEOMETRY_NO_OPERATION_BACKEND_REVISION,
    DIRECT_EXECUTION_GEOMETRY_ROTATE_BACKEND_ID,
    DIRECT_EXECUTION_GEOMETRY_ROTATE_BACKEND_REVISION,
    DIRECT_HALT_FETCH_BACKEND_ID, DIRECT_HALT_FETCH_BACKEND_REVISION,
    DIRECT_HALT_REGISTERS_BACKEND_ID, DIRECT_HALT_REGISTERS_BACKEND_REVISION,
    DIRECT_INITIAL_HALT_BACKEND_ID, DIRECT_INITIAL_HALT_BACKEND_REVISION,
    DIRECT_INPUT_BACKEND_ID, DIRECT_INPUT_BACKEND_REVISION,
    DIRECT_JUMP_CODE_BACKEND_ID, DIRECT_JUMP_CODE_BACKEND_REVISION,
    DIRECT_JUMP_DATA_BACKEND_ID, DIRECT_JUMP_DATA_BACKEND_REVISION,
    DIRECT_NO_OPERATION_BACKEND_ID, DIRECT_NO_OPERATION_BACKEND_REVISION,
    DIRECT_NON_GRAPHICAL_BACKEND_ID, DIRECT_NON_GRAPHICAL_BACKEND_REVISION,
    DIRECT_OUTPUT_BACKEND_ID, DIRECT_OUTPUT_BACKEND_REVISION,
    DIRECT_ROTATE_BACKEND_ID, DIRECT_ROTATE_BACKEND_REVISION,
    DirectCacheDisposition, DirectCrazyError, DirectDeoptError,
    DirectExecutionGeometryInitialHaltError,
    DirectExecutionGeometryInitialJumpDataError,
    DirectExecutionGeometryNoOperationError,
    DirectExecutionGeometryRotateError, DirectHaltFetchError,
    DirectHaltRegistersError, DirectHost, DirectInitialHaltError,
    DirectInputError, DirectJumpCodeError, DirectJumpDataError,
    DirectNativeKind, DirectNoOperationError, DirectNonGraphicalError,
    DirectOutputError, DirectRotateError, DirectSelectionError,
    DirectSequenceError, ExecutionGeometryNativeRunner,
    NATIVE_REGION_ABI_REVISION, NATIVE_REGION_ACCUMULATOR_OFFSET,
    NATIVE_REGION_CODE_POINTER_OFFSET, NATIVE_REGION_DATA_POINTER_OFFSET,
    NATIVE_REGION_INPUT_CONSUMED_OFFSET, NATIVE_REGION_INPUT_LEN_OFFSET,
    NATIVE_REGION_INPUT_OFFSET, NATIVE_REGION_MEMORY_OFFSET,
    NATIVE_REGION_MEMORY_WORDS_OFFSET, NATIVE_REGION_OUTPUT_CAPACITY_OFFSET,
    NATIVE_REGION_OUTPUT_LEN_OFFSET, NATIVE_REGION_OUTPUT_OFFSET,
    NATIVE_REGION_STATE_SIZE, NATIVE_REGION_TERMINATION_OFFSET,
    NativeArtifactError, NativeExecutableAllocationRequest,
    NativeExecutableCodeCopyReport, NativeExecutableExecutionPhase,
    NativeExecutableInvocationBindingError, NativeExecutableLifecycleError,
    NativeExecutableLoadPhase, NativeExecutableMappingId,
    NativeExecutableMappingReport, NativeExecutableMemoryAdapter,
    NativeExecutableOperationEvidenceError, NativeExecutablePermission,
    NativeExecutableReleaseRequest, NativeExecutableRunner,
    NativeExecutableSequenceCache, NativeExecutableSequenceCacheCapacityError,
    NativeExecutableSequenceCacheDisposition,
    NativeExecutableSequenceCacheLimits, NativeExecutableSequenceKey,
    NativeExecutableSequenceLease, NativeExecutableSequenceLeaseCache,
    NativeExecutableSequenceLeaseCacheAcquisition,
    NativeExecutableSequenceLeaseCacheDisposition,
    NativeExecutableSequenceLeaseCacheEntryReleaseFailure,
    NativeExecutableSequenceLeaseCacheInvalidation,
    NativeInstructionSyncReport, NativeInstructionSyncRequest,
    NativeInterpreterContinuation, NativeInterpreterContinuationError,
    NativeInterpreterContinuationReason, NativeLoadedSequenceAdmissionError,
    NativeRegionBuffers, NativeRegionCallFrame, NativeRegionCallFrameError,
    NativeRegionInvocationError, NativeRegionInvocationOutcome,
    NativeRegionMutationSurface, NativeRegionStatus,
    NativeSequenceExecutionOutcome, NativeTerminationTag,
    PreflightedExecutionTier, PreparedExecutionGeometryNativeInvocation,
    PreparedNativeExecutableInvocation, PreparedNativeRegionInvocation,
    PreparedVerifiedDirectInvocation, ReadyExecutionGeometryNativeExecutable,
    ReadyNativeExecutable, ReadyNativeExecutableSequence,
    StagedExecutionGeometryNativeExecutable, StagedNativeExecutable,
    UntrustedNativeObjectArtifact, VerifiedDirectInvocationError,
    VerifiedDirectLoadError, VerifiedDirectLoadImage,
    VerifiedDirectNativeCache, VerifiedDirectSequencePlan,
    VerifiedExecutionGeometryLoadImage, compile_preflighted_clang_c23,
    emit_direct_crazy_coff, emit_direct_deopt_coff,
    emit_direct_execution_geometry_initial_halt_coff,
    emit_direct_execution_geometry_initial_jump_data_coff,
    emit_direct_execution_geometry_no_operation_coff,
    emit_direct_execution_geometry_rotate_coff, emit_direct_halt_fetch_coff,
    emit_direct_halt_registers_coff, emit_direct_initial_halt_coff,
    emit_direct_input_coff, emit_direct_jump_code_coff,
    emit_direct_jump_data_coff, emit_direct_no_operation_coff,
    emit_direct_non_graphical_coff, emit_direct_output_coff,
    emit_direct_rotate_coff, execute_cached_verified_native_sequence,
    execute_loaded_cached_verified_native_sequence,
    execute_loaded_verified_native_sequence, execute_verified_native,
    execute_verified_native_sequence, load_cached_verified_native_sequence,
    load_execution_geometry_native_executable, load_native_executable,
    load_verified_native_sequence, lower_clang_c23,
    lower_preflighted_clang_c23, release_execution_geometry_native_executable,
    release_native_executable, release_native_executable_sequence,
    select_cached_preflighted_execution_tier,
    select_cached_verified_direct_sequence, select_preflighted_execution_tier,
    select_verified_direct_native, select_verified_direct_sequence,
    structurally_admit_coff, verify_direct_crazy, verify_direct_deopt_stub,
    verify_direct_execution_geometry_initial_halt,
    verify_direct_execution_geometry_initial_jump_data,
    verify_direct_execution_geometry_no_operation,
    verify_direct_execution_geometry_rotate, verify_direct_halt_fetch,
    verify_direct_halt_registers, verify_direct_initial_halt,
    verify_direct_input, verify_direct_jump_code, verify_direct_jump_data,
    verify_direct_no_operation, verify_direct_non_graphical,
    verify_direct_output, verify_direct_rotate,
};
use geometry_interpreter_handoff::{
    ExecutionGeometryContinuationAdmissionError,
    ExecutionGeometryContinuationBudgetOutcome,
    ExecutionGeometryContinuationExecutionCause,
    ExecutionGeometryHandoffAdmissionError,
    ExecutionGeometryHandoffExecutionCause,
    ExecutionGeometryInterpreterContinuation,
    ExecutionGeometryInterpreterHandoff,
};
use geometry_native_admission::{
    ExecutionGeometryNativeInitialHaltAdmission,
    ExecutionGeometryNativeInitialHaltAdmissionError,
    ExecutionGeometryNativeInitialHaltBindingError,
    ExecutionGeometryNativeInitialHaltCompletionError,
    ExecutionGeometryNativeInitialHaltExecutionError,
    ExecutionGeometryNativeInitialHaltPreparationError,
    ExecutionGeometryNativeInitialHaltTransactionFailure,
};
use geometry_native_initial_jump_data as jump_native;
use geometry_native_jump_rotate_halt_cache::{
    GeometryNativeJumpRotateHaltTripleCacheAcquireFailure as FullCacheFailure,
    GeometryNativeJumpRotateHaltTripleCacheDisposition as FullCacheDisposition,
    GeometryNativeJumpRotateHaltTripleCacheRelease as FullCacheRelease,
    GeometryNativeJumpRotateHaltTripleLeaseCache as FullLeaseCache,
};
use geometry_native_jump_rotate_halt_multi_cache::{
    GeometryNativeJumpRotateHaltLruAcquireFailure as FullLruFailure,
    GeometryNativeJumpRotateHaltLruCache as FullLruCache,
    GeometryNativeJumpRotateHaltLruDisposition as FullLruDisposition,
    GeometryNativeJumpRotateHaltLruRelease as FullLruRelease,
};
use geometry_native_jump_rotate_halt_sequence as full_native;
use geometry_native_no_operation::{
    ExecutionGeometryNativeNoOperationAdmission,
    ExecutionGeometryNativeNoOperationBindingError,
    ExecutionGeometryNativeNoOperationCompletionError,
    ExecutionGeometryNativeNoOperationExecutionError,
    ExecutionGeometryNativeNoOperationPreparationError,
    ExecutionGeometryNativeNoOperationTransactionFailure,
};
use geometry_native_pair_cache::{
    GeometryNativeNoopHaltPairCacheAcquireFailure,
    GeometryNativeNoopHaltPairCacheDisposition,
    GeometryNativeNoopHaltPairCacheRelease,
    GeometryNativeNoopHaltPairLeaseCache,
};
use geometry_native_rotate::{
    ExecutionGeometryNativeRotateAdmission,
    ExecutionGeometryNativeRotateBindingError,
    ExecutionGeometryNativeRotateCompletionError,
    ExecutionGeometryNativeRotateExecutionError,
    ExecutionGeometryNativeRotatePreparationError,
    ExecutionGeometryNativeRotateTransactionFailure,
};
use geometry_native_rotate_pair_cache::{
    GeometryNativeRotateHaltPairCacheAcquireFailure,
    GeometryNativeRotateHaltPairCacheDisposition,
    GeometryNativeRotateHaltPairCacheRelease,
    GeometryNativeRotateHaltPairLeaseCache,
};
use geometry_native_rotate_sequence::{
    ExecutionGeometryNativeRotateHaltAdmissionError,
    ExecutionGeometryNativeRotateHaltEvidence,
    ExecutionGeometryNativeRotateHaltExecutableBindingError,
    ExecutionGeometryNativeRotateHaltFailureCause,
    ExecutionGeometryNativeRotateHaltLoadedFailureCause as RHLoadedCause,
    ExecutionGeometryNativeRotateHaltOutcome,
    ExecutionGeometryNativeRotateHaltPairLoadFailure,
    ExecutionGeometryNativeRotateHaltSequence,
};
use geometry_native_sequence::{
    ExecutionGeometryNativeNoopHaltAdmissionError,
    ExecutionGeometryNativeNoopHaltEvidence,
    ExecutionGeometryNativeNoopHaltExecutableBindingError,
    ExecutionGeometryNativeNoopHaltFailureCause,
    ExecutionGeometryNativeNoopHaltLoadedFailureCause as LoadedNoopHaltCause,
    ExecutionGeometryNativeNoopHaltOutcome,
    ExecutionGeometryNativeNoopHaltPairLoadFailure,
    ExecutionGeometryNativeNoopHaltSequence,
};
use interpreter_handoff::{
    NativeInterpreterHandoff, NativeInterpreterHandoffAdmissionError,
    NativeInterpreterHandoffBudgetOutcome, NativeInterpreterHandoffCompletion,
    NativeInterpreterHandoffExecutionCause,
};
use leased_retry::{
    NativeContinuationLeasedRetry, NativeContinuationLeasedRetryAdmissionError,
    NativeContinuationLeasedRetryExecutionFailure,
};
use malbolge::{
    EFFECT_IR_EXECUTION_GEOMETRY_VERSION, EFFECT_IR_VERSION,
    EFFECT_IR_WIDE_PROFILE_VERSION, EffectOp,
    ExecutionGeometryRegionEffectProgram, IrEncodingError, MemoryLiveIn,
    ProfileMachine, ProfileMachineError, ProfileMachineIoState,
    ProfileMachineObservation, ProfileMachineState, ProfileMemoryDelta,
    ProfileMemoryRead, ProfileMemoryWrite, ProfileRegisters,
    ProfileRequirementErrorKind, ProfileStepTrace, RegionEffectProgram,
    RunOutcome, RuntimeCapability, StepOutcome, StepProgramProjectionError,
    TargetProfileRequirement, Termination, TraceInput, current_profile,
    decode_profile_instruction, historical_profile, preflight_profile,
    preflight_runtime_requirement, safe_rust_classic_capability,
    safe_rust_profiled_capability, target_profile,
    verify_initial_halt_profile_width, verify_input_then_halt_profile_width,
    verify_jump_rotate_halt_profile_width,
    verify_minimum_initial_halt_profile_width,
    verify_noop_prefix_halt_profile_width,
};
use native_retry::{
    NativeContinuationNativeRetry, NativeContinuationRetryAdmissionError,
    NativeContinuationRetryDisposition, NativeContinuationRetryResumption,
};
use retry_cycle::{
    NativeContinuationRetryCycleOutcome, NativeContinuationRetryCycleRequest,
    execute_native_continuation_retry_cycle,
};
use retry_planner::{
    NativeContinuationRetryPlanningError,
    NativeContinuationRetryPlanningOutcome,
    NativeContinuationRetryStepPlanningError, plan_native_continuation_retry,
};
use retry_policy::{
    NativeContinuationRetryFallback, NativeContinuationRetryPolicy,
    NativeContinuationRetryPolicyError, NativeContinuationRetryPolicyOutcome,
};
use retry_router::{
    NativeContinuationRetryHost, NativeContinuationRetryRoute,
    NativeContinuationRetryRoutingError, NativeContinuationRetryRoutingRequest,
    route_native_continuation_retry,
};
use retry_turn::{
    NativeContinuationRetryTurnOutcome, execute_native_continuation_retry_turn,
};

const FIXTURE_PROFILE_ID: &str = "malbolge-2026.3";
const FIXTURE_PROFILE_VERSION: &str = "2026.3";

#[derive(Clone, Copy)]
struct CoffCompileCase {
    expected_machine: [u8; 2],
    isa: HostIsa,
}

type CollisionKeys = (NativeArtifactKey, NativeArtifactKey);

type DirectSelectionCase =
    (RegionEffectProgram, DirectNativeKind, &'static str);

type LeaseCacheFixture = (
    NativeExecutableSequenceLeaseCache,
    FakeNativeExecutableAdapter,
);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum FakeNativeAdapterOperation {
    Allocate,
    Copy,
    Protect,
    Release,
    Synchronize,
}

impl Display for FakeNativeAdapterOperation {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Allocate => "allocate",
            Self::Copy => "copy",
            Self::Protect => "protect",
            Self::Release => "release",
            Self::Synchronize => "synchronize",
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum FakeNativeAdapterDrift {
    AllocationAlignment,
    AllocationCapacity,
    AllocationPermission,
    CopyBytes,
    CopyMappingIdentity,
    CopyStartAddress,
    ProtectMappingIdentity,
    ProtectPermissions,
    SynchronizeMappingIdentity,
    SynchronizeRange,
}

#[derive(Debug)]
struct FakeNativeExecutableAdapter {
    allocation_requests: Vec<NativeExecutableAllocationRequest>,
    base_address: NonZeroUsize,
    copied_code: Vec<Vec<u8>>,
    drift: Option<FakeNativeAdapterDrift>,
    failure: Option<FakeNativeAdapterOperation>,
    failure_at: Option<(FakeNativeAdapterOperation, usize)>,
    mapped_len_overrides: Vec<usize>,
    mapping_id: NativeExecutableMappingId,
    operations: Vec<FakeNativeAdapterOperation>,
    release_attempts: usize,
    release_failure_at: Option<usize>,
    release_failures_remaining: usize,
    release_requests: Vec<NativeExecutableReleaseRequest>,
    synchronization_requests: Vec<NativeInstructionSyncRequest>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum FakeNativeRunnerBehavior {
    Applied,
    CompletionDrift,
    FailureAfterMutation,
    GuardMiss,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum FakeNativeRunnerError {
    Call,
}

impl Display for FakeNativeRunnerError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("fake native runner call failed")
    }
}

#[derive(Debug)]
struct FakeExecutionGeometryNativeRunner {
    behavior: FakeNativeRunnerBehavior,
    calls: usize,
    entry_addresses: Vec<NonZeroUsize>,
    mapping_ids: Vec<NativeExecutableMappingId>,
    state_pointers_non_null: Vec<bool>,
}

#[derive(Debug)]
struct FakeExecutionGeometrySequenceRunner {
    behaviors: Vec<FakeNativeRunnerBehavior>,
    calls: usize,
    entry_addresses: Vec<NonZeroUsize>,
    mapping_ids: Vec<NativeExecutableMappingId>,
}

#[derive(Debug)]
struct FakeNativeExecutableRunner {
    behavior: FakeNativeRunnerBehavior,
    calls: usize,
    entry_addresses: Vec<NonZeroUsize>,
    mapping_ids: Vec<NativeExecutableMappingId>,
    state_pointers_non_null: Vec<bool>,
}

#[derive(Debug)]
struct FakeNativeSequenceRunner {
    behaviors: Vec<FakeNativeRunnerBehavior>,
    calls: usize,
    entry_addresses: Vec<NonZeroUsize>,
    mapping_ids: Vec<NativeExecutableMappingId>,
}

#[derive(Debug)]
struct NativeHandoffFixture {
    continuation: NativeInterpreterContinuation,
    input: Vec<u8>,
    memory: Vec<u32>,
    output: Vec<u8>,
    plan: VerifiedDirectSequencePlan,
}

struct NativeScheduleFixture {
    handoff: NativeInterpreterHandoff,
    memory: Vec<u32>,
    plan: VerifiedDirectSequencePlan,
}

struct NativeRetryFixture {
    full_plan: VerifiedDirectSequencePlan,
    retry_plan: VerifiedDirectSequencePlan,
    suspension: NativeContinuationScheduleSuspension,
}

struct LeasedNativeRetryFixture {
    adapter: FakeNativeExecutableAdapter,
    cache: NativeExecutableSequenceLeaseCache,
    full_plan: VerifiedDirectSequencePlan,
    leased: NativeContinuationLeasedRetry,
}

type CachedRetryCycleNativeFailure =
    Box<NativeContinuationCachedRetryNativeFailure<FakeNativeRunnerError>>;

type CachedRetryTelemetryWindowError =
    NativeContinuationCachedRetryTelemetryWindowError;

type CachedRetryCodecFixture = (
    NativeContinuationCachedRetryTelemetryWindowSnapshot,
    Vec<u8>,
);
type CachedRetryLatencyCodecFixture = (
    NativeContinuationCachedRetryLatencyHistogramSnapshot,
    Vec<u8>,
);

struct AdmittedNativeRetryFixture {
    full_plan: VerifiedDirectSequencePlan,
    retry: NativeContinuationNativeRetry,
    retry_plan: VerifiedDirectSequencePlan,
}

struct CachedRetryTelemetryExpectation {
    attempts: usize,
    completed_steps: usize,
    evicted_keys: usize,
    hits: usize,
    insertions: usize,
    retired_keys: usize,
}

#[derive(Debug)]
struct NativeSequenceFixture {
    final_memory: Vec<u32>,
    final_output: Vec<u8>,
    first_memory: Vec<u32>,
    first_output: Vec<u8>,
    initial_memory: Vec<u32>,
    initial_output: Vec<u8>,
    input: Vec<u8>,
    programs: Vec<RegionEffectProgram>,
}

struct SecondStepContinuationExpectation<'plan> {
    expected_exit: ProfileMachineObservation,
    expected_outcome: RunOutcome,
    plan_key: &'plan NativeExecutableSequenceKey,
    programs: &'plan [RegionEffectProgram],
    reason: NativeInterpreterContinuationReason,
}

type FullGeometryAdmissionError =
    full_native::ExecutionGeometryNativeJumpRotateHaltAdmissionError;
type FullGeometryBindingError =
    full_native::ExecutionGeometryNativeJumpRotateHaltExecutableBindingError;
type FullGeometryEvidence =
    full_native::ExecutionGeometryNativeJumpRotateHaltEvidence;
type FullGeometryFailureCause<MemoryError, RunnerError> =
    full_native::ExecutionGeometryNativeJumpRotateHaltFailureCause<
        MemoryError,
        RunnerError,
    >;
type FullGeometryLoadedFailureCause<RunnerError> =
    full_native::ExecutionGeometryNativeJumpRotateHaltLoadedFailureCause<
        RunnerError,
    >;
type FullGeometryTripleLoadFailure<MemoryError> =
    full_native::ExecutionGeometryNativeJumpRotateHaltTripleLoadFailure<
        MemoryError,
    >;
type FullGeometryTripleReleaseFailure<MemoryError> =
    full_native::ExecutionGeometryNativeJumpRotateHaltTripleReleaseFailure<
        MemoryError,
    >;
type FullGeometryOutcome =
    full_native::ExecutionGeometryNativeJumpRotateHaltOutcome;
type FullGeometrySequence =
    full_native::ExecutionGeometryNativeJumpRotateHaltSequence;
type FullGeometrySequenceTriple = (
    FullGeometrySequence,
    FullGeometrySequence,
    FullGeometrySequence,
);

type InitialJumpAdmission =
    jump_native::ExecutionGeometryNativeInitialJumpDataAdmission;
type InitialJumpBindingError =
    jump_native::ExecutionGeometryNativeInitialJumpDataBindingError;
type InitialJumpCompletionError =
    jump_native::ExecutionGeometryNativeInitialJumpDataCompletionError;
type InitialJumpExecutionError<RunnerError> =
    jump_native::ExecutionGeometryNativeInitialJumpDataExecutionError<
        RunnerError,
    >;
type InitialJumpPreparationError =
    jump_native::ExecutionGeometryNativeInitialJumpDataPreparationError;
type InitialJumpTransactionFailure<MemoryError, RunnerError> =
    jump_native::ExecutionGeometryNativeInitialJumpDataTransactionFailure<
        MemoryError,
        RunnerError,
    >;

type DerivedV5HandoffFixture = (
    ExecutionGeometryRegionEffectProgram,
    ProfileMachineState,
    malbolge::ProfileExecutionGeometry,
);
type GeometryNativeAdmissionFixture = (
    ExecutionGeometryNativeInitialHaltAdmission,
    malbolge::ProfileExecutionGeometry,
);
type GeometryNativeInitialJumpDataAdmissionFixture =
    (InitialJumpAdmission, malbolge::ProfileExecutionGeometry);
type GeometryNativeNoOperationAdmissionFixture = (
    ExecutionGeometryNativeNoOperationAdmission,
    malbolge::ProfileExecutionGeometry,
);
type GeometryNativeRotateAdmissionFixture = (
    ExecutionGeometryNativeRotateAdmission,
    malbolge::ProfileExecutionGeometry,
);
type GeometryNativeNoopHaltReadyPair = (
    ReadyExecutionGeometryNativeExecutable,
    ReadyExecutionGeometryNativeExecutable,
);
type GeometryNativeRotateHaltReadyPair = (
    ReadyExecutionGeometryNativeExecutable,
    ReadyExecutionGeometryNativeExecutable,
);
type GeometryNativeJumpRotateHaltReadyTriple = (
    ReadyExecutionGeometryNativeExecutable,
    ReadyExecutionGeometryNativeExecutable,
    ReadyExecutionGeometryNativeExecutable,
);

struct GeometryNativeInitialJumpDataRunnerFixture {
    adapter: FakeNativeExecutableAdapter,
    admission: InitialJumpAdmission,
    geometry: malbolge::ProfileExecutionGeometry,
    ready: ReadyExecutionGeometryNativeExecutable,
}

struct GeometryNativeNoOperationRunnerFixture {
    adapter: FakeNativeExecutableAdapter,
    admission: ExecutionGeometryNativeNoOperationAdmission,
    geometry: malbolge::ProfileExecutionGeometry,
    ready: ReadyExecutionGeometryNativeExecutable,
}

struct GeometryNativeRotateRunnerFixture {
    adapter: FakeNativeExecutableAdapter,
    admission: ExecutionGeometryNativeRotateAdmission,
    geometry: malbolge::ProfileExecutionGeometry,
    ready: ReadyExecutionGeometryNativeExecutable,
}

struct GeometryNativeRunnerFixture {
    adapter: FakeNativeExecutableAdapter,
    admission: ExecutionGeometryNativeInitialHaltAdmission,
    geometry: malbolge::ProfileExecutionGeometry,
    ready: ReadyExecutionGeometryNativeExecutable,
}

#[derive(Debug)]
struct DerivedV5SequenceFixture {
    geometry: malbolge::ProfileExecutionGeometry,
    programs: Vec<ExecutionGeometryRegionEffectProgram>,
    states: Vec<ProfileMachineState>,
    traces: Vec<ProfileStepTrace>,
}

impl FakeExecutionGeometryNativeRunner {
    const fn new(behavior: FakeNativeRunnerBehavior) -> Self {
        Self {
            behavior,
            calls: 0,
            entry_addresses: Vec::new(),
            mapping_ids: Vec::new(),
            state_pointers_non_null: Vec::new(),
        }
    }
}

impl FakeExecutionGeometrySequenceRunner {
    fn new(behaviors: impl Into<Vec<FakeNativeRunnerBehavior>>) -> Self {
        Self {
            behaviors: behaviors.into(),
            calls: 0,
            entry_addresses: Vec::new(),
            mapping_ids: Vec::new(),
        }
    }
}

impl FakeNativeExecutableRunner {
    const fn new(behavior: FakeNativeRunnerBehavior) -> Self {
        Self {
            behavior,
            calls: 0,
            entry_addresses: Vec::new(),
            mapping_ids: Vec::new(),
            state_pointers_non_null: Vec::new(),
        }
    }
}

impl FakeNativeSequenceRunner {
    fn new(behaviors: impl Into<Vec<FakeNativeRunnerBehavior>>) -> Self {
        Self {
            behaviors: behaviors.into(),
            calls: 0,
            entry_addresses: Vec::new(),
            mapping_ids: Vec::new(),
        }
    }
}

impl FakeNativeExecutableAdapter {
    fn fail_if_requested(
        &self,
        operation: FakeNativeAdapterOperation,
    ) -> Result<(), FakeNativeAdapterOperation> {
        let attempt = self
            .operations
            .iter()
            .filter(|observed| **observed == operation)
            .count();
        if self.failure == Some(operation)
            || self.failure_at == Some((operation, attempt))
        {
            Err(operation)
        } else {
            Ok(())
        }
    }

    const fn new(
        mapping_id: NativeExecutableMappingId,
        base_address: NonZeroUsize,
    ) -> Self {
        Self {
            allocation_requests: Vec::new(),
            base_address,
            copied_code: Vec::new(),
            drift: None,
            failure: None,
            failure_at: None,
            mapped_len_overrides: Vec::new(),
            mapping_id,
            operations: Vec::new(),
            release_attempts: 0,
            release_failure_at: None,
            release_failures_remaining: 0,
            release_requests: Vec::new(),
            synchronization_requests: Vec::new(),
        }
    }

    const fn with_drift(mut self, drift: FakeNativeAdapterDrift) -> Self {
        self.drift = Some(drift);
        self
    }

    const fn with_failure(
        mut self,
        failure: FakeNativeAdapterOperation,
    ) -> Self {
        self.failure = Some(failure);
        self
    }

    const fn with_failure_at(
        mut self,
        failure: FakeNativeAdapterOperation,
        attempt: usize,
    ) -> Self {
        self.failure_at = Some((failure, attempt));
        self
    }

    fn with_mapped_len_overrides(
        mut self,
        mapped_len_overrides: Vec<usize>,
    ) -> Self {
        self.mapped_len_overrides = mapped_len_overrides;
        self
    }

    const fn with_release_failure_at(mut self, attempt: usize) -> Self {
        self.release_failure_at = Some(attempt);
        self
    }

    const fn with_release_failures(mut self, count: usize) -> Self {
        self.release_failures_remaining = count;
        self
    }
}

impl NativeExecutableMemoryAdapter for FakeNativeExecutableAdapter {
    type Error = FakeNativeAdapterOperation;

    fn allocate_writable(
        &mut self,
        request: NativeExecutableAllocationRequest,
    ) -> Result<NativeExecutableMappingReport, Self::Error> {
        self.operations.push(FakeNativeAdapterOperation::Allocate);
        self.allocation_requests.push(request);
        self.fail_if_requested(FakeNativeAdapterOperation::Allocate)?;
        let allocation_index = self.allocation_requests.len().saturating_sub(1);
        let sequence_index = allocation_index;
        let address_offset = sequence_index.saturating_mul(0x10_000);
        let sequence_address = NonZeroUsize::new(
            self.base_address.get().saturating_add(address_offset),
        )
        .unwrap_or(self.base_address);
        let base_address = if self.drift
            == Some(FakeNativeAdapterDrift::AllocationAlignment)
        {
            NonZeroUsize::new(sequence_address.get().saturating_add(1))
                .unwrap_or(sequence_address)
        } else {
            sequence_address
        };
        let mapping_id = NativeExecutableMappingId::new(
            self.mapping_id.get().saturating_add(
                u64::try_from(sequence_index).unwrap_or(u64::MAX),
            ),
        )
        .unwrap_or(self.mapping_id);
        let mapped_len =
            if self.drift == Some(FakeNativeAdapterDrift::AllocationCapacity) {
                request.byte_len().saturating_sub(1)
            } else {
                self.mapped_len_overrides
                    .get(allocation_index)
                    .copied()
                    .unwrap_or_else(|| request.byte_len())
            };
        let permissions = if self.drift
            == Some(FakeNativeAdapterDrift::AllocationPermission)
        {
            NativeExecutablePermission::ReadExecute
        } else {
            request.permissions()
        };
        Ok(NativeExecutableMappingReport::new(
            mapping_id,
            base_address,
            mapped_len,
            permissions,
        ))
    }

    fn copy_code(
        &mut self,
        mapping: NativeExecutableMappingReport,
        code: &[u8],
    ) -> Result<NativeExecutableCodeCopyReport, Self::Error> {
        self.operations.push(FakeNativeAdapterOperation::Copy);
        self.copied_code.push(code.to_vec());
        self.fail_if_requested(FakeNativeAdapterOperation::Copy)?;
        let mapping_id = if self.drift
            == Some(FakeNativeAdapterDrift::CopyMappingIdentity)
        {
            NativeExecutableMappingId::new(
                self.mapping_id.get().saturating_add(1),
            )
            .unwrap_or(self.mapping_id)
        } else {
            mapping.mapping_id()
        };
        let start_address = if self.drift
            == Some(FakeNativeAdapterDrift::CopyStartAddress)
        {
            NonZeroUsize::new(mapping.base_address().get().saturating_add(1))
                .unwrap_or_else(|| mapping.base_address())
        } else {
            mapping.base_address()
        };
        let mut copied = code.to_vec();
        if self.drift == Some(FakeNativeAdapterDrift::CopyBytes)
            && let Some(first) = copied.first_mut()
        {
            *first ^= 1;
        }
        Ok(NativeExecutableCodeCopyReport::new(
            mapping_id,
            start_address,
            copied,
        ))
    }

    fn protect_read_execute(
        &mut self,
        mapping: NativeExecutableMappingReport,
    ) -> Result<NativeExecutableMappingReport, Self::Error> {
        self.operations.push(FakeNativeAdapterOperation::Protect);
        self.fail_if_requested(FakeNativeAdapterOperation::Protect)?;
        let mapping_id = if self.drift
            == Some(FakeNativeAdapterDrift::ProtectMappingIdentity)
        {
            NativeExecutableMappingId::new(
                self.mapping_id.get().saturating_add(1),
            )
            .unwrap_or(self.mapping_id)
        } else {
            mapping.mapping_id()
        };
        let permissions =
            if self.drift == Some(FakeNativeAdapterDrift::ProtectPermissions) {
                NativeExecutablePermission::ReadWrite
            } else {
                NativeExecutablePermission::ReadExecute
            };
        Ok(NativeExecutableMappingReport::new(
            mapping_id,
            mapping.base_address(),
            mapping.mapped_len(),
            permissions,
        ))
    }

    fn release(
        &mut self,
        request: NativeExecutableReleaseRequest,
    ) -> Result<(), Self::Error> {
        self.operations.push(FakeNativeAdapterOperation::Release);
        self.release_requests.push(request);
        self.release_attempts = self.release_attempts.saturating_add(1);
        if self.release_failure_at == Some(self.release_attempts) {
            return Err(FakeNativeAdapterOperation::Release);
        }
        if self.release_failures_remaining > 0 {
            self.release_failures_remaining =
                self.release_failures_remaining.saturating_sub(1);
            return Err(FakeNativeAdapterOperation::Release);
        }
        self.fail_if_requested(FakeNativeAdapterOperation::Release)
    }

    fn synchronize_instructions(
        &mut self,
        request: NativeInstructionSyncRequest,
    ) -> Result<NativeInstructionSyncReport, Self::Error> {
        self.operations
            .push(FakeNativeAdapterOperation::Synchronize);
        self.synchronization_requests.push(request);
        self.fail_if_requested(FakeNativeAdapterOperation::Synchronize)?;
        let mapping_id = if self.drift
            == Some(FakeNativeAdapterDrift::SynchronizeMappingIdentity)
        {
            NativeExecutableMappingId::new(
                self.mapping_id.get().saturating_add(1),
            )
            .unwrap_or(self.mapping_id)
        } else {
            request.mapping_id()
        };
        let byte_len =
            if self.drift == Some(FakeNativeAdapterDrift::SynchronizeRange) {
                request.byte_len().saturating_sub(1)
            } else {
                request.byte_len()
            };
        Ok(NativeInstructionSyncReport::new(
            mapping_id,
            request.start_address(),
            byte_len,
        ))
    }
}

impl ExecutionGeometryNativeRunner for FakeExecutionGeometryNativeRunner {
    type Error = FakeNativeRunnerError;

    fn run(
        &mut self,
        invocation: &mut PreparedExecutionGeometryNativeInvocation<'_, '_>,
    ) -> Result<i32, Self::Error> {
        self.calls = self.calls.saturating_add(1);
        self.entry_addresses.push(invocation.entry_address());
        self.mapping_ids.push(invocation.mapping_id());
        self.state_pointers_non_null
            .push(!invocation.state_mut_ptr().is_null());
        match self.behavior {
            FakeNativeRunnerBehavior::Applied => {
                invocation.apply_expected_for_test();
                Ok(NativeRegionStatus::Applied.code())
            },
            FakeNativeRunnerBehavior::CompletionDrift => {
                invocation.apply_expected_for_test();
                if invocation.write_memory_for_test(0, 999) {
                    Ok(NativeRegionStatus::Applied.code())
                } else {
                    Err(FakeNativeRunnerError::Call)
                }
            },
            FakeNativeRunnerBehavior::FailureAfterMutation => {
                let _mutated = invocation.write_memory_for_test(0, 999);
                Err(FakeNativeRunnerError::Call)
            },
            FakeNativeRunnerBehavior::GuardMiss => {
                Ok(NativeRegionStatus::GuardMiss.code())
            },
        }
    }
}

impl ExecutionGeometryNativeRunner for FakeExecutionGeometrySequenceRunner {
    type Error = FakeNativeRunnerError;

    fn run(
        &mut self,
        invocation: &mut PreparedExecutionGeometryNativeInvocation<'_, '_>,
    ) -> Result<i32, Self::Error> {
        let behavior = self
            .behaviors
            .get(self.calls)
            .copied()
            .ok_or(FakeNativeRunnerError::Call)?;
        self.calls = self.calls.saturating_add(1);
        self.entry_addresses.push(invocation.entry_address());
        self.mapping_ids.push(invocation.mapping_id());
        match behavior {
            FakeNativeRunnerBehavior::Applied => {
                invocation.apply_expected_for_test();
                Ok(NativeRegionStatus::Applied.code())
            },
            FakeNativeRunnerBehavior::CompletionDrift => {
                invocation.apply_expected_for_test();
                if invocation.write_memory_for_test(0, 999) {
                    Ok(NativeRegionStatus::Applied.code())
                } else {
                    Err(FakeNativeRunnerError::Call)
                }
            },
            FakeNativeRunnerBehavior::FailureAfterMutation => {
                let _mutated = invocation.write_memory_for_test(0, 999);
                Err(FakeNativeRunnerError::Call)
            },
            FakeNativeRunnerBehavior::GuardMiss => {
                Ok(NativeRegionStatus::GuardMiss.code())
            },
        }
    }
}

impl NativeExecutableRunner for FakeNativeExecutableRunner {
    type Error = FakeNativeRunnerError;

    fn run(
        &mut self,
        invocation: &mut PreparedNativeExecutableInvocation<'_, '_, '_>,
    ) -> Result<i32, Self::Error> {
        self.calls = self.calls.saturating_add(1);
        self.entry_addresses.push(invocation.entry_address());
        self.mapping_ids.push(invocation.mapping_id());
        self.state_pointers_non_null
            .push(!invocation.state_mut_ptr().is_null());
        match self.behavior {
            FakeNativeRunnerBehavior::Applied => {
                invocation.apply_expected_for_test();
                Ok(NativeRegionStatus::Applied.code())
            },
            FakeNativeRunnerBehavior::CompletionDrift => {
                invocation.apply_expected_for_test();
                if invocation.write_memory_for_test(5, 999) {
                    Ok(NativeRegionStatus::Applied.code())
                } else {
                    Err(FakeNativeRunnerError::Call)
                }
            },
            FakeNativeRunnerBehavior::FailureAfterMutation => {
                let _mutated = invocation.write_memory_for_test(5, 999);
                Err(FakeNativeRunnerError::Call)
            },
            FakeNativeRunnerBehavior::GuardMiss => {
                Ok(NativeRegionStatus::GuardMiss.code())
            },
        }
    }
}

impl NativeExecutableRunner for FakeNativeSequenceRunner {
    type Error = FakeNativeRunnerError;

    fn run(
        &mut self,
        invocation: &mut PreparedNativeExecutableInvocation<'_, '_, '_>,
    ) -> Result<i32, Self::Error> {
        let behavior = self
            .behaviors
            .get(self.calls)
            .copied()
            .ok_or(FakeNativeRunnerError::Call)?;
        self.calls = self.calls.saturating_add(1);
        self.entry_addresses.push(invocation.entry_address());
        self.mapping_ids.push(invocation.mapping_id());
        match behavior {
            FakeNativeRunnerBehavior::Applied => {
                invocation.apply_expected_for_test();
                Ok(NativeRegionStatus::Applied.code())
            },
            FakeNativeRunnerBehavior::CompletionDrift => {
                invocation.apply_expected_for_test();
                if invocation.write_memory_for_test(0, 999) {
                    Ok(NativeRegionStatus::Applied.code())
                } else {
                    Err(FakeNativeRunnerError::Call)
                }
            },
            FakeNativeRunnerBehavior::FailureAfterMutation => {
                let _mutated = invocation.write_memory_for_test(0, 999);
                Err(FakeNativeRunnerError::Call)
            },
            FakeNativeRunnerBehavior::GuardMiss => {
                Ok(NativeRegionStatus::GuardMiss.code())
            },
        }
    }
}

fn canonical_fixture_bytes() -> Result<Vec<u8>, String> {
    decode_hex_fixture(include_str!("execution/fixtures/region-effect-v3.hex"))
}

fn decode_hex_fixture(text: &str) -> Result<Vec<u8>, String> {
    let compact = text.split_whitespace().collect::<String>();
    let (pairs, remainder) = compact.as_bytes().as_chunks::<2>();
    if !remainder.is_empty() {
        return Err(String::from("canonical fixture has odd hex length"));
    }
    let mut bytes = Vec::new();
    for pair in pairs {
        let digits = from_utf8(pair)
            .map_err(|error| format!("canonical fixture UTF-8: {error}"))?;
        let value = u8::from_str_radix(digits, 16)
            .map_err(|error| format!("canonical fixture hex: {error}"))?;
        bytes.push(value);
    }
    Ok(bytes)
}

fn expected_profile_metadata(
    program: &RegionEffectProgram,
) -> Result<Vec<u8>, String> {
    fn push_bytes(output: &mut Vec<u8>, value: &[u8]) -> Result<(), String> {
        let length = u32::try_from(value.len()).map_err(|_error| {
            String::from("profile metadata length overflow")
        })?;
        output.extend_from_slice(&length.to_le_bytes());
        output.extend_from_slice(value);
        Ok(())
    }

    let feature_count =
        u32::try_from(program.profile_requirement.features.len())
            .map_err(|_error| String::from("profile feature count overflow"))?;
    let metadata_version = match program.format_version {
        EFFECT_IR_VERSION => 3u16,
        EFFECT_IR_WIDE_PROFILE_VERSION => 4u16,
        _ => {
            return Err(String::from(
                "unsupported profile metadata IR version",
            ));
        },
    };
    let mut bytes = Vec::new();
    bytes.extend_from_slice(b"MBPF");
    bytes.extend_from_slice(&metadata_version.to_le_bytes());
    bytes.extend_from_slice(&0u16.to_le_bytes());
    push_bytes(&mut bytes, program.profile_id.as_bytes())?;
    push_bytes(&mut bytes, program.profile_fingerprint.as_bytes())?;
    push_bytes(&mut bytes, program.profile_requirement.version.as_bytes())?;
    bytes.extend_from_slice(&feature_count.to_le_bytes());
    for feature in &program.profile_requirement.features {
        push_bytes(&mut bytes, feature.as_bytes())?;
    }
    bytes.push(program.profile_requirement.word_trits);
    match program.format_version {
        EFFECT_IR_VERSION => {
            let memory_words =
                u32::try_from(program.profile_requirement.memory_words)
                    .map_err(|_error| {
                        String::from("MBPF v3 capacity overflow")
                    })?;
            bytes.extend_from_slice(&memory_words.to_le_bytes());
        },
        EFFECT_IR_WIDE_PROFILE_VERSION => {
            bytes.extend_from_slice(
                &program.profile_requirement.memory_words.to_le_bytes(),
            );
        },
        _ => {
            return Err(String::from(
                "unsupported profile metadata IR version",
            ));
        },
    }
    bytes.extend_from_slice(&program.required_memory_words().to_le_bytes());
    Ok(bytes)
}

fn rendered_profile_metadata(source: &str) -> Result<Vec<u8>, String> {
    let marker = "const unsigned char malbolge_profile_metadata[] = {\n";
    let start = source
        .find(marker)
        .map(|offset| offset.saturating_add(marker.len()))
        .ok_or_else(|| {
            String::from("bootstrap metadata declaration missing")
        })?;
    let remainder = source
        .get(start..)
        .ok_or_else(|| String::from("bootstrap metadata start invalid"))?;
    let end = remainder
        .find("};\n\n")
        .ok_or_else(|| String::from("bootstrap metadata terminator missing"))?;
    remainder
        .get(..end)
        .ok_or_else(|| String::from("bootstrap metadata range invalid"))?
        .split(',')
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(|value| {
            let digits = value.strip_prefix("0x").ok_or_else(|| {
                format!("bootstrap metadata byte lacks hex prefix: {value}")
            })?;
            u8::from_str_radix(digits, 16)
                .map_err(|error| format!("bootstrap metadata hex: {error}"))
        })
        .collect()
}

fn fixture_profile_requirement() -> TargetProfileRequirement {
    let profile =
        target_profile(FIXTURE_PROFILE_ID).unwrap_or_else(|| current_profile());
    let mut requirement = TargetProfileRequirement::from_descriptor(profile);
    requirement.version = String::from(FIXTURE_PROFILE_VERSION);
    requirement
}

fn observation(seed: u32) -> ProfileMachineObservation {
    ProfileMachineObservation {
        input_consumed: usize::try_from(seed).unwrap_or(0),
        output_len: usize::try_from(seed.saturating_add(1)).unwrap_or(0),
        registers: ProfileRegisters {
            accumulator: seed.saturating_add(2),
            code_pointer: seed.saturating_add(3),
            data_pointer: seed.saturating_add(4),
        },
        termination: None,
    }
}

fn program() -> RegionEffectProgram {
    RegionEffectProgram {
        effects: vec![EffectOp {
            after: ProfileMachineObservation {
                termination: Some(Termination::HaltInstruction),
                ..observation(10)
            },
            before: observation(1),
            input: Some(TraceInput::Byte(0x41)),
            memory_delta: ProfileMemoryDelta {
                data: Some(ProfileMemoryWrite {
                    address: 7,
                    after: 9,
                    before: 8,
                }),
                encryption: Some(ProfileMemoryWrite {
                    address: 11,
                    after: 13,
                    before: 12,
                }),
            },
            output: Some(0x42),
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![
            MemoryLiveIn { address: 17, value: 18 },
            MemoryLiveIn { address: 19, value: 20 },
        ],
        outcome: RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 1,
        },
        profile_fingerprint: String::from("malbolge-profile-v1:sha256:fixture"),
        profile_id: String::from("malbolge-2026.3"),
        profile_requirement: fixture_profile_requirement(),
        step_budget: 8,
    }
}

fn target(
    os: HostOperatingSystem,
    isa: HostIsa,
    features: Vec<String>,
) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from("baseline"),
        backend_revision: 3,
        host_isa: isa,
        host_os: os,
        native_abi_revision: 1,
        required_features: features,
    })
}

fn base_target_config() -> NativeTargetConfig {
    NativeTargetConfig {
        backend_id: String::from("baseline"),
        backend_revision: 3,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: 1,
        required_features: vec![String::from("sse2")],
    }
}

fn target_variant_configs() -> Vec<NativeTargetConfig> {
    let base = base_target_config();
    let mut linux = base.clone();
    linux.host_os = HostOperatingSystem::Linux;
    let mut aarch64 = base.clone();
    aarch64.host_isa = HostIsa::AArch64;
    let mut backend = base.clone();
    backend.backend_id = String::from("other-backend");
    let mut revision = base.clone();
    revision.backend_revision = revision.backend_revision.saturating_add(1);
    let mut abi = base.clone();
    abi.native_abi_revision = abi.native_abi_revision.saturating_add(1);
    let mut feature = base;
    feature.required_features.push(String::from("avx2"));
    vec![linux, aarch64, backend, revision, abi, feature]
}

fn assert_key_differs(
    base: &NativeArtifactKey,
    candidate: Result<NativeArtifactKey, NativeIdentityError>,
) -> Result<(), String> {
    let observed =
        candidate.map_err(|error| format!("variant key failed: {error:?}"))?;
    if &observed == base {
        Err(String::from("target assumption did not change cache key"))
    } else {
        Ok(())
    }
}

#[test]
fn canonical_ir_matches_versioned_byte_fixture() -> Result<(), String> {
    let observed = program().canonical_bytes().map_err(|error| {
        format!("canonical fixture render failed: {error:?}")
    })?;
    let expected = canonical_fixture_bytes()?;
    if observed == expected {
        Ok(())
    } else {
        Err(format!(
            "canonical IR fixture mismatch: observed={} expected={}",
            observed.len(),
            expected.len()
        ))
    }
}

#[test]
fn ir_v3_rejects_profile_capacity_wider_than_u32() -> Result<(), String> {
    let mut wide = program();
    wide.profile_requirement.word_trits = 21;
    wide.profile_requirement.memory_words = 10_460_353_203;
    if wide.canonical_bytes()
        == Err(IrEncodingError::ProfileMemoryWordsOverflow)
    {
        Ok(())
    } else {
        Err(String::from(
            "IR v3 admitted an N21 profile-capacity envelope",
        ))
    }
}

#[test]
fn canonical_ir_v4_encodes_wide_profile_capacity() -> Result<(), String> {
    let v3 = program()
        .canonical_bytes()
        .map_err(|error| format!("canonical v3 baseline failed: {error:?}"))?;
    let mut wide = program();
    wide.format_version = EFFECT_IR_WIDE_PROFILE_VERSION;
    wide.profile_requirement.word_trits = 21;
    wide.profile_requirement.memory_words = 10_460_353_203;
    let observed = wide.canonical_bytes().map_err(|error| {
        format!("canonical v4 wide encoding failed: {error:?}")
    })?;
    let encoded_capacity = wide.profile_requirement.memory_words.to_le_bytes();
    if observed.get(..6) != Some(b"MBIR\x04\x00")
        || observed.len() != v3.len().saturating_add(4)
        || !observed
            .windows(encoded_capacity.len())
            .any(|window| window == encoded_capacity)
    {
        return Err(String::from("IR v4 wide profile encoding drifted"));
    }
    Ok(())
}

#[test]
fn canonical_ir_rejects_unknown_format_version() -> Result<(), String> {
    let mut unknown = program();
    unknown.format_version = EFFECT_IR_WIDE_PROFILE_VERSION.saturating_add(1);
    if unknown.canonical_bytes()
        == Err(IrEncodingError::UnsupportedFormatVersion)
    {
        Ok(())
    } else {
        Err(String::from("unknown IR version acquired canonical bytes"))
    }
}

#[test]
fn native_identity_rejects_profile_capacity_wider_than_ir_v3()
-> Result<(), String> {
    let mut wide = program();
    wide.profile_requirement.word_trits = 21;
    wide.profile_requirement.memory_words = 10_460_353_203;
    let encoding_error = NativeIdentityError::Encoding(
        IrEncodingError::ProfileMemoryWordsOverflow,
    );
    if RegionEffectIdentity::new(&wide) != Err(encoding_error) {
        return Err(String::from(
            "N21 envelope acquired an IR-v3 region identity",
        ));
    }
    let target = NativeTargetIdentity::new(base_target_config());
    if NativeArtifactKey::new(&wide, target) == Err(encoding_error) {
        Ok(())
    } else {
        Err(String::from("N21 envelope acquired an IR-v3 native key"))
    }
}

#[test]
fn native_identity_binds_explicit_execution_geometry_v5() -> Result<(), String>
{
    let n10 = derived_v5_input_halt_sequence_fixture(10, vec![0xa5])?;
    let n11 = derived_v5_input_halt_sequence_fixture(11, vec![0xa5])?;
    let n10_program = derived_v5_fixture_program(&n10, 0)?;
    let n11_program = derived_v5_fixture_program(&n11, 0)?;
    let identity = RegionEffectIdentity::new_execution_geometry(n10_program)
        .map_err(|error| format!("IR v5 region identity failed: {error:?}"))?;
    let canonical = n10_program
        .canonical_bytes()
        .map_err(|error| format!("IR v5 canonical bytes failed: {error:?}"))?;
    if identity.format_version() != EFFECT_IR_EXECUTION_GEOMETRY_VERSION
        || identity.execution_geometry()
            != Some(n10_program.execution_geometry())
        || identity.canonical_bytes() != canonical
        || identity.required_memory_words()
            != n10_program.required_memory_words()
    {
        return Err(String::from("IR v5 region identity lost geometry"));
    }
    let target = NativeTargetIdentity::new(base_target_config());
    let n10_key =
        NativeArtifactKey::new_execution_geometry(n10_program, target.clone())
            .map_err(|error| {
                format!("IR v5 N10 native key failed: {error:?}")
            })?;
    let n11_key =
        NativeArtifactKey::new_execution_geometry(n11_program, target)
            .map_err(|error| {
                format!("IR v5 N11 native key failed: {error:?}")
            })?;
    if n10_key == n11_key {
        return Err(String::from(
            "IR v5 native key ignored execution geometry",
        ));
    }
    let mut cache = NativeArtifactCache::default();
    let _n10_old = cache.insert(n10_key, "n10");
    let _n11_old = cache.insert(n11_key, "n11");
    if cache.len() == 2 {
        Ok(())
    } else {
        Err(String::from("IR v5 geometry identities collided in cache"))
    }
}

#[test]
fn native_identity_and_deopt_bind_portable_ir_v4() -> Result<(), String> {
    let mut wide = program();
    wide.format_version = EFFECT_IR_WIDE_PROFILE_VERSION;
    wide.profile_requirement.word_trits = 21;
    wide.profile_requirement.memory_words = 10_460_353_203;
    let identity = RegionEffectIdentity::new(&wide)
        .map_err(|error| format!("IR v4 region identity failed: {error:?}"))?;
    if identity.format_version() != EFFECT_IR_WIDE_PROFILE_VERSION {
        return Err(String::from("IR v4 identity lost its schema version"));
    }
    let key = NativeArtifactKey::new(
        &wide,
        NativeTargetIdentity::new(base_target_config()),
    )
    .map_err(|error| format!("IR v4 native key failed: {error:?}"))?;
    if key.ir() != &identity {
        return Err(String::from("IR v4 native key changed region identity"));
    }
    let expected_metadata = expected_profile_metadata(&wide)?;
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        let artifact = emit_direct_deopt_coff(&wide, direct_deopt_target(isa))
            .map_err(|error| {
                format!("IR v4 {isa:?} deopt emission failed: {error}")
            })?;
        if !artifact
            .object()
            .windows(expected_metadata.len())
            .any(|window| window == expected_metadata)
        {
            return Err(format!("IR v4 {isa:?} deopt lost MBPF v4 metadata"));
        }
        let admitted = structurally_admit_coff(&artifact).map_err(|error| {
            format!("IR v4 {isa:?} deopt structure failed: {error}")
        })?;
        assert_tampered_direct_profile_metadata(&artifact)?;
        let verified =
            verify_direct_deopt_stub(&artifact).map_err(|error| {
                format!("IR v4 {isa:?} deopt verification failed: {error}")
            })?;
        if admitted.object() != artifact.object()
            || verified.object() != artifact.object()
        {
            return Err(format!("IR v4 {isa:?} deopt authority changed bytes"));
        }
    }
    Ok(())
}

#[test]
fn bootstrap_backend_accepts_v4_with_u32_geometry() -> Result<(), String> {
    let mut v4 = native_program();
    v4.format_version = EFFECT_IR_WIDE_PROFILE_VERSION;
    let artifact = lower_clang_c23(&v4, native_target(HostIsa::X86_64))
        .map_err(|error| {
            format!("v4 bootstrap rejected u32 geometry: {error}")
        })?;
    if artifact.key().ir().format_version() != EFFECT_IR_WIDE_PROFILE_VERSION {
        return Err(String::from("v4 bootstrap key lost IR version"));
    }
    assert_bootstrap_source_profile_metadata(&v4, artifact.source())
}

#[test]
fn bootstrap_backend_rejects_v4_beyond_u32_geometry() -> Result<(), String> {
    let mut wide = native_program();
    wide.format_version = EFFECT_IR_WIDE_PROFILE_VERSION;
    wide.profile_requirement.word_trits = 21;
    wide.profile_requirement.memory_words = 10_460_353_203;
    if lower_clang_c23(&wide, native_target(HostIsa::X86_64))
        == Err(NativeArtifactError::ProfileGeometry)
    {
        Ok(())
    } else {
        Err(String::from("N21 v4 reached the u32 bootstrap backend"))
    }
}

#[test]
fn state_applying_native_backend_accepts_v4_with_u32_geometry()
-> Result<(), String> {
    let mut v4 = direct_rotate_program();
    v4.format_version = EFFECT_IR_WIDE_PROFILE_VERSION;
    let expected_metadata = expected_profile_metadata(&v4)?;
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        let artifact = emit_direct_rotate_coff(&v4, direct_rotate_target(isa))
            .map_err(|error| {
                format!("v4 {isa:?} direct rotate emission failed: {error}")
            })?;
        if !artifact
            .object()
            .windows(expected_metadata.len())
            .any(|window| window == expected_metadata)
        {
            return Err(format!("v4 {isa:?} direct rotate lost MBPF v4"));
        }
        let verified =
            verify_direct_rotate(&artifact, &v4).map_err(|error| {
                format!("v4 {isa:?} direct rotate verification failed: {error}")
            })?;
        if verified.object() != artifact.object() {
            return Err(format!("v4 {isa:?} direct rotate changed bytes"));
        }
    }
    Ok(())
}

#[test]
fn state_applying_native_backend_rejects_v4_beyond_u32_geometry()
-> Result<(), String> {
    let mut wide = direct_rotate_program();
    wide.format_version = EFFECT_IR_WIDE_PROFILE_VERSION;
    wide.profile_requirement.word_trits = 21;
    wide.profile_requirement.memory_words = 10_460_353_203;
    if emit_direct_rotate_coff(&wide, direct_rotate_target(HostIsa::X86_64))
        == Err(DirectRotateError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("N21 v4 reached state-applying direct rotate"))
    }
}

#[test]
fn canonical_ir_changes_when_any_semantic_field_changes() -> Result<(), String>
{
    let baseline = program();
    let bytes = baseline
        .canonical_bytes()
        .map_err(|error| format!("canonical baseline failed: {error:?}"))?;
    let mut variants = Vec::new();

    let mut profile_id = baseline.clone();
    profile_id.profile_id.push('x');
    variants.push(profile_id);

    let mut profile_fingerprint = baseline.clone();
    profile_fingerprint.profile_fingerprint.push('x');
    variants.push(profile_fingerprint);

    let mut profile_features = baseline.clone();
    let _removed = profile_features.profile_requirement.features.pop();
    variants.push(profile_features);

    let mut profile_memory = baseline.clone();
    profile_memory.profile_requirement.memory_words = profile_memory
        .profile_requirement
        .memory_words
        .saturating_add(1);
    variants.push(profile_memory);

    let mut profile_version = baseline.clone();
    profile_version.profile_requirement.version.push('x');
    variants.push(profile_version);

    let mut profile_word_trits = baseline.clone();
    profile_word_trits.profile_requirement.word_trits = profile_word_trits
        .profile_requirement
        .word_trits
        .saturating_add(1);
    variants.push(profile_word_trits);

    let mut budget = baseline.clone();
    budget.step_budget = budget.step_budget.saturating_add(1);
    variants.push(budget);

    let mut outcome = baseline.clone();
    outcome.outcome = RunOutcome::BudgetExhausted { steps: 1 };
    variants.push(outcome);

    let mut live_in = baseline.clone();
    let first_live_in = live_in
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("fixture has no memory live-in"))?;
    first_live_in.value = first_live_in.value.saturating_add(1);
    variants.push(live_in);

    let mut effect = baseline;
    let first_effect = effect
        .effects
        .first_mut()
        .ok_or_else(|| String::from("fixture has no effect"))?;
    first_effect.output = None;
    variants.push(effect);

    for variant in variants {
        let observed = variant
            .canonical_bytes()
            .map_err(|error| format!("canonical variant failed: {error:?}"))?;
        if observed == bytes {
            return Err(String::from(
                "semantic IR mutation kept canonical bytes",
            ));
        }
    }
    Ok(())
}

#[test]
fn portable_ir_derives_exact_required_memory_words() -> Result<(), String> {
    let baseline = program();
    if baseline.required_memory_words() != 20 {
        return Err(format!(
            "baseline IR memory footprint: {}",
            baseline.required_memory_words()
        ));
    }

    let mut effect_only = baseline;
    effect_only.memory_live_ins.clear();
    if effect_only.required_memory_words() != 15 {
        return Err(format!(
            "observation IR memory footprint: {}",
            effect_only.required_memory_words()
        ));
    }

    let first_effect = effect_only
        .effects
        .first_mut()
        .ok_or_else(|| String::from("fixture has no effect"))?;
    let data_write = first_effect
        .memory_delta
        .data
        .as_mut()
        .ok_or_else(|| String::from("fixture has no data write"))?;
    data_write.address = 100;
    if effect_only.required_memory_words() != 101 {
        return Err(String::from("write address was omitted from footprint"));
    }

    let max_pointer_effect = effect_only
        .effects
        .first_mut()
        .ok_or_else(|| String::from("fixture lost effect"))?;
    max_pointer_effect.after.registers.data_pointer = u32::MAX;
    if effect_only.required_memory_words() == 4_294_967_296 {
        Ok(())
    } else {
        Err(String::from("u32::MAX address footprint was truncated"))
    }
}

#[test]
fn native_identity_rejects_profile_capacity_inconsistent_ir()
-> Result<(), String> {
    let program = profile_invalid_native_program();
    let canonical = program
        .canonical_bytes()
        .map_err(|error| format!("untrusted IR transport failed: {error:?}"))?;
    if canonical.is_empty() || program.fits_declared_profile_capacity() {
        return Err(String::from("profile-invalid IR classification drifted"));
    }
    if RegionEffectIdentity::new(&program)
        != Err(NativeIdentityError::ProfileCapacity)
    {
        return Err(String::from("profile-invalid IR gained cache identity"));
    }
    let target = NativeTargetIdentity::new(base_target_config());
    if NativeArtifactKey::new(&program, target)
        == Err(NativeIdentityError::ProfileCapacity)
    {
        Ok(())
    } else {
        Err(String::from("profile-invalid IR gained native key"))
    }
}

#[test]
fn native_emitters_reject_profile_capacity_inconsistent_ir()
-> Result<(), String> {
    let program = profile_invalid_native_program();
    if lower_clang_c23(&program, native_target(HostIsa::X86_64))
        != Err(NativeArtifactError::Identity(
            NativeIdentityError::ProfileCapacity,
        ))
    {
        return Err(String::from("bootstrap admitted profile-invalid IR"));
    }
    if emit_direct_deopt_coff(&program, direct_deopt_target(HostIsa::X86_64))
        == Err(DirectDeoptError::Identity(
            NativeIdentityError::ProfileCapacity,
        ))
    {
        Ok(())
    } else {
        Err(String::from("direct deopt admitted profile-invalid IR"))
    }
}

#[test]
fn preflighted_bootstrap_rejects_requirement_before_target()
-> Result<(), String> {
    let mut forged = native_program();
    forged.profile_requirement =
        TargetProfileRequirement::from_descriptor(historical_profile());
    if matches!(
        lower_preflighted_clang_c23(
            &forged,
            safe_rust_classic_capability(),
            NativeTargetIdentity::new(base_target_config()),
        ),
        Err(BootstrapProfilePreflightError::ProfileRequirement(_))
    ) {
        Ok(())
    } else {
        Err(String::from(
            "bootstrap target validation masked profile requirement drift",
        ))
    }
}

#[test]
fn preflighted_bootstrap_rejects_runtime_before_target() -> Result<(), String> {
    let program = native_program();
    let Err(BootstrapProfilePreflightError::Profile(runtime_error)) =
        lower_preflighted_clang_c23(
            &program,
            safe_rust_classic_capability(),
            NativeTargetIdentity::new(base_target_config()),
        )
    else {
        return Err(String::from(
            "bootstrap target validation masked runtime profile preflight",
        ));
    };
    if runtime_error.kind()
        != ProfileRequirementErrorKind::RuntimeCapabilityMissing
    {
        return Err(String::from(
            "bootstrap runtime preflight changed diagnostic category",
        ));
    }
    let profile = target_profile(&program.profile_id)
        .ok_or_else(|| String::from("bootstrap fixture profile is missing"))?;
    let Err(canonical) = preflight_profile(
        profile,
        program.required_memory_words(),
        safe_rust_classic_capability(),
    ) else {
        return Err(String::from("bootstrap profile unexpectedly preflighted"));
    };
    if runtime_error.to_string() == canonical.to_string() {
        Ok(())
    } else {
        Err(String::from(
            "bootstrap runtime preflight changed canonical diagnostic text",
        ))
    }
}

#[test]
fn preflighted_bootstrap_rejects_capacity_before_target() -> Result<(), String>
{
    let overflow = profile_capacity_overflow_native_program()?;
    let Err(BootstrapProfilePreflightError::Profile(capacity_error)) =
        lower_preflighted_clang_c23(
            &overflow,
            safe_rust_classic_capability(),
            NativeTargetIdentity::new(base_target_config()),
        )
    else {
        return Err(String::from(
            "bootstrap target validation masked profile capacity preflight",
        ));
    };
    if capacity_error.kind()
        != ProfileRequirementErrorKind::ProfileCapacityExceeded
    {
        return Err(String::from(
            "bootstrap capacity preflight changed diagnostic category",
        ));
    }
    let expected = concat!(
        "MALBOLGE-PROFILE-002 profile=malbolge-2026.3 version=2026.3 ",
        "constraint=profile-capacity-ceiling required_memory_words=4782970 ",
        "profile_memory_words=4782969"
    );
    if capacity_error.to_string() == expected {
        Ok(())
    } else {
        Err(format!(
            "bootstrap capacity diagnostic changed: {capacity_error}"
        ))
    }
}

#[test]
fn bootstrap_compiler_rejects_runtime_before_process_launch()
-> Result<(), String> {
    let program = native_program();
    let compiler = Path::new("./.temp/missing-bootstrap-clang");
    let Err(BootstrapCompilerError::Preflight(
        BootstrapProfilePreflightError::Profile(error),
    )) = compile_preflighted_clang_c23(
        compiler,
        &program,
        safe_rust_classic_capability(),
        native_target(HostIsa::X86_64),
    )
    else {
        return Err(String::from(
            "compiler launch masked runtime profile error",
        ));
    };
    let profile = target_profile(&program.profile_id)
        .ok_or_else(|| String::from("bootstrap compiler profile is missing"))?;
    let Err(canonical) = preflight_profile(
        profile,
        program.required_memory_words(),
        safe_rust_classic_capability(),
    ) else {
        return Err(String::from(
            "bootstrap compiler profile unexpectedly passed",
        ));
    };
    if error.to_string() == canonical.to_string() {
        Ok(())
    } else {
        Err(String::from(
            "compiler wrapper changed MALBOLGE-PROFILE-001",
        ))
    }
}

#[test]
fn bootstrap_compiler_rejects_capacity_before_process_launch()
-> Result<(), String> {
    let program = profile_capacity_overflow_native_program()?;
    let compiler = Path::new("./.temp/missing-bootstrap-clang");
    let Err(BootstrapCompilerError::Preflight(
        BootstrapProfilePreflightError::Profile(error),
    )) = compile_preflighted_clang_c23(
        compiler,
        &program,
        safe_rust_profiled_capability(),
        native_target(HostIsa::X86_64),
    )
    else {
        return Err(String::from(
            "compiler launch masked profile capacity error",
        ));
    };
    let profile = target_profile(&program.profile_id)
        .ok_or_else(|| String::from("overflow compiler profile is missing"))?;
    let Err(canonical) = preflight_profile(
        profile,
        program.required_memory_words(),
        safe_rust_profiled_capability(),
    ) else {
        return Err(String::from(
            "overflow compiler profile unexpectedly passed",
        ));
    };
    if error.kind() == ProfileRequirementErrorKind::ProfileCapacityExceeded
        && error.to_string() == canonical.to_string()
    {
        Ok(())
    } else {
        Err(String::from(
            "compiler wrapper changed MALBOLGE-PROFILE-002",
        ))
    }
}

#[test]
fn bootstrap_compiler_launch_failure_follows_profile_admission()
-> Result<(), String> {
    let compiler = Path::new("./.temp/missing-bootstrap-clang");
    if matches!(
        compile_preflighted_clang_c23(
            compiler,
            &native_program(),
            safe_rust_profiled_capability(),
            native_target(HostIsa::X86_64),
        ),
        Err(BootstrapCompilerError::Launch(_))
    ) {
        Ok(())
    } else {
        Err(String::from(
            "admitted bootstrap did not reach compiler launch",
        ))
    }
}

#[test]
fn preflighted_bootstrap_preserves_raw_lowering_after_admission()
-> Result<(), String> {
    let program = native_program();
    let target = native_target(HostIsa::X86_64);
    let raw = lower_clang_c23(&program, target.clone())
        .map_err(|error| error.to_string())?;
    let admitted = lower_preflighted_clang_c23(
        &program,
        safe_rust_profiled_capability(),
        target,
    )
    .map_err(|error| error.to_string())?;
    if admitted == raw {
        Ok(())
    } else {
        Err(String::from(
            "profile admission changed bootstrap source candidate",
        ))
    }
}

#[test]
fn cache_key_includes_declared_profile_identity() -> Result<(), String> {
    let program = program();
    let target = NativeTargetIdentity::new(base_target_config());
    let base = NativeArtifactKey::new(&program, target.clone())
        .map_err(|error| format!("base profile key failed: {error:?}"))?;
    if base.ir().profile_id() != program.profile_id
        || base.ir().profile_fingerprint() != program.profile_fingerprint
        || base.ir().profile_requirement() != &program.profile_requirement
        || base.ir().required_memory_words() != program.required_memory_words()
    {
        return Err(String::from("native key lost exact profile identity"));
    }
    let mut renamed = program;
    renamed.profile_id = String::from("malbolge-2026.3-alias");
    let candidate = NativeArtifactKey::new(&renamed, target)
        .map_err(|error| format!("renamed profile key failed: {error:?}"))?;
    if base == candidate {
        return Err(String::from(
            "declared profile identity did not change cache key",
        ));
    }
    Ok(())
}

#[test]
fn cache_key_includes_host_and_backend_assumptions() -> Result<(), String> {
    let program = program();
    let base = NativeArtifactKey::new(
        &program,
        NativeTargetIdentity::new(base_target_config()),
    )
    .map_err(|error| format!("base key failed: {error:?}"))?;
    for config in target_variant_configs() {
        assert_key_differs(
            &base,
            NativeArtifactKey::new(&program, NativeTargetIdentity::new(config)),
        )?;
    }
    Ok(())
}

#[test]
fn process_cache_removes_all_variants_for_exact_region() -> Result<(), String> {
    let program = program();
    let mut other_program = program.clone();
    other_program.profile_id.push_str("-other");
    let x86 = NativeArtifactKey::new(
        &program,
        target(HostOperatingSystem::Windows, HostIsa::X86_64, Vec::new()),
    )
    .map_err(|error| format!("x86 region key failed: {error:?}"))?;
    let arm = NativeArtifactKey::new(
        &program,
        target(HostOperatingSystem::Windows, HostIsa::AArch64, Vec::new()),
    )
    .map_err(|error| format!("ARM region key failed: {error:?}"))?;
    let other = NativeArtifactKey::new(
        &other_program,
        target(HostOperatingSystem::Windows, HostIsa::X86_64, Vec::new()),
    )
    .map_err(|error| format!("other region key failed: {error:?}"))?;
    let identity = RegionEffectIdentity::new(&program)
        .map_err(|error| format!("region identity failed: {error:?}"))?;
    let mut cache = NativeArtifactCache::default();
    let _x86 = cache.insert(x86, "x86");
    let _arm = cache.insert(arm, "arm");
    let _other = cache.insert(other.clone(), "other");
    if cache.remove_region(&identity) != 2
        || cache.remove_region(&identity) != 0
        || cache.len() != 1
        || cache.get(&other) != Some(&"other")
    {
        Err(String::from("region invalidation crossed exact identity"))
    } else {
        Ok(())
    }
}

#[test]
fn process_cache_removes_all_regions_for_exact_target() -> Result<(), String> {
    let program = program();
    let mut other_program = program.clone();
    other_program.profile_id.push_str("-other");
    let x86_target =
        target(HostOperatingSystem::Windows, HostIsa::X86_64, Vec::new());
    let arm_target =
        target(HostOperatingSystem::Windows, HostIsa::AArch64, Vec::new());
    let x86 = NativeArtifactKey::new(&program, x86_target.clone())
        .map_err(|error| format!("x86 target key failed: {error:?}"))?;
    let other_x86 = NativeArtifactKey::new(&other_program, x86_target.clone())
        .map_err(|error| format!("other x86 key failed: {error:?}"))?;
    let arm = NativeArtifactKey::new(&program, arm_target)
        .map_err(|error| format!("ARM target key failed: {error:?}"))?;
    let mut cache = NativeArtifactCache::default();
    let _x86 = cache.insert(x86, "x86");
    let _other_x86 = cache.insert(other_x86, "other-x86");
    let _arm = cache.insert(arm.clone(), "arm");
    if cache.remove_target(&x86_target) != 2
        || cache.remove_target(&x86_target) != 0
        || cache.len() != 1
        || cache.get(&arm) != Some(&"arm")
    {
        Err(String::from(
            "target invalidation crossed exact assumptions",
        ))
    } else {
        Ok(())
    }
}

#[test]
fn portable_ir_uses_shared_runtime_diagnostic() -> Result<(), String> {
    let program = program();
    let fixture = target_profile(FIXTURE_PROFILE_ID)
        .ok_or_else(|| String::from("fixture profile is missing"))?;
    let Err(canonical) = preflight_profile(
        fixture,
        u64::from(fixture.memory_words()),
        safe_rust_classic_capability(),
    ) else {
        return Err(String::from(
            "classic runtime unexpectedly admitted fixture profile",
        ));
    };
    let Err(portable) = preflight_runtime_requirement(
        &program.profile_id,
        &program.profile_requirement,
        safe_rust_classic_capability(),
    ) else {
        return Err(String::from(
            "classic runtime unexpectedly admitted portable requirement",
        ));
    };
    if format!("{portable}") != format!("{canonical}") {
        return Err(String::from(
            "portable IR requirement changed shared runtime diagnostic",
        ));
    }
    preflight_runtime_requirement(
        &program.profile_id,
        &program.profile_requirement,
        safe_rust_profiled_capability(),
    )
    .map_err(|error| format!("profiled runtime rejected portable IR: {error}"))
}

#[test]
fn required_feature_order_is_canonical() -> Result<(), String> {
    let program = program();
    let left = NativeArtifactKey::new(
        &program,
        target(HostOperatingSystem::Linux, HostIsa::X86_64, vec![
            String::from("avx2"),
            String::from("sse2"),
        ]),
    )
    .map_err(|error| format!("left feature key failed: {error:?}"))?;
    let right = NativeArtifactKey::new(
        &program,
        target(HostOperatingSystem::Linux, HostIsa::X86_64, vec![
            String::from("sse2"),
            String::from("avx2"),
            String::from("sse2"),
        ]),
    )
    .map_err(|error| format!("right feature key failed: {error:?}"))?;
    if left == right {
        Ok(())
    } else {
        Err(String::from(
            "feature order/duplicates changed canonical key",
        ))
    }
}

const fn constant_bucket_digest(_bytes: &[u8]) -> u64 {
    0
}

const fn alternate_bucket_digest(_bytes: &[u8]) -> u64 {
    1
}

fn forced_collision_keys() -> Result<CollisionKeys, String> {
    let left_program = program();
    let mut right_program = left_program.clone();
    let first_effect = right_program
        .effects
        .first_mut()
        .ok_or_else(|| String::from("collision fixture has no effect"))?;
    first_effect.output = Some(0x43);
    let left = NativeArtifactKey::with_digest(
        &left_program,
        target(HostOperatingSystem::Windows, HostIsa::X86_64, Vec::new()),
        constant_bucket_digest,
    )
    .map_err(|error| format!("left collision key failed: {error:?}"))?;
    let right = NativeArtifactKey::with_digest(
        &right_program,
        target(HostOperatingSystem::Windows, HostIsa::X86_64, Vec::new()),
        constant_bucket_digest,
    )
    .map_err(|error| format!("right collision key failed: {error:?}"))?;
    Ok((left, right))
}

#[test]
fn cache_digest_never_participates_in_exact_identity() -> Result<(), String> {
    let program = program();
    let target =
        target(HostOperatingSystem::Windows, HostIsa::X86_64, Vec::new());
    let left = NativeArtifactKey::with_digest(
        &program,
        target.clone(),
        constant_bucket_digest,
    )
    .map_err(|error| format!("left digest key failed: {error:?}"))?;
    let right = NativeArtifactKey::with_digest(
        &program,
        target,
        alternate_bucket_digest,
    )
    .map_err(|error| format!("right digest key failed: {error:?}"))?;
    if left.bucket_digest() == right.bucket_digest()
        || left.ir().bucket_digest() == right.ir().bucket_digest()
        || left != right
        || left.ir() != right.ir()
    {
        return Err(String::from("lookup digest changed exact identity"));
    }

    let mut cache = NativeArtifactCache::default();
    if cache.insert(left.clone(), "left").is_some()
        || cache.get(&right) != Some(&"left")
        || cache.insert(right.clone(), "right") != Some("left")
        || cache.len() != 1
        || cache.get(&left) != Some(&"right")
        || cache.remove(&right) != Some("right")
        || !cache.is_empty()
    {
        Err(String::from("cache promoted digest to reuse authority"))
    } else {
        Ok(())
    }
}

#[test]
fn cache_equality_ignores_bucket_accelerator_layout() -> Result<(), String> {
    let program = program();
    let target =
        target(HostOperatingSystem::Windows, HostIsa::X86_64, Vec::new());
    let left_key = NativeArtifactKey::with_digest(
        &program,
        target.clone(),
        constant_bucket_digest,
    )
    .map_err(|error| format!("left cache key failed: {error:?}"))?;
    let right_key = NativeArtifactKey::with_digest(
        &program,
        target,
        alternate_bucket_digest,
    )
    .map_err(|error| format!("right cache key failed: {error:?}"))?;
    let mut left = NativeArtifactCache::default();
    let mut right = NativeArtifactCache::default();
    let _left = left.insert(left_key, "value");
    let _right = right.insert(right_key.clone(), "value");
    if left != right {
        return Err(String::from("cache equality retained bucket layout"));
    }
    let _changed = right.insert(right_key, "changed");
    if left == right {
        Err(String::from("cache equality ignored retained values"))
    } else {
        Ok(())
    }
}

#[test]
fn forced_bucket_collision_never_authorizes_reuse() -> Result<(), String> {
    let (left, right) = forced_collision_keys()?;
    if left.bucket_digest() != right.bucket_digest() {
        return Err(String::from("forced cache digest did not collide"));
    }
    if left == right {
        return Err(String::from(
            "bucket collision incorrectly merged cache keys",
        ));
    }
    Ok(())
}

#[test]
fn process_cache_confirms_full_keys_after_collision() -> Result<(), String> {
    let (left, right) = forced_collision_keys()?;
    let mut cache = NativeArtifactCache::default();
    if !cache.is_empty() {
        return Err(String::from("new native cache was not empty"));
    }
    if cache.insert(left.clone(), "left").is_some()
        || cache.insert(right.clone(), "right").is_some()
        || cache.len() != 2
        || cache.get(&left) != Some(&"left")
        || cache.get(&right) != Some(&"right")
    {
        return Err(String::from("collision bucket lost exact entries"));
    }
    if cache.insert(left.clone(), "left-replaced") != Some("left")
        || cache.len() != 2
        || cache.get(&left) != Some(&"left-replaced")
        || cache.get(&right) != Some(&"right")
    {
        return Err(String::from("exact replacement crossed collision key"));
    }
    if cache.remove(&left) != Some("left-replaced")
        || cache.get(&left).is_some()
        || cache.get(&right) != Some(&"right")
        || cache.len() != 1
    {
        return Err(String::from("exact removal crossed collision key"));
    }
    cache.clear();
    if cache.is_empty() && cache.get(&right).is_none() {
        Ok(())
    } else {
        Err(String::from("native cache clear retained an entry"))
    }
}

const fn native_observation(
    input_consumed: usize,
    output_len: usize,
    registers: ProfileRegisters,
    termination: Option<Termination>,
) -> ProfileMachineObservation {
    ProfileMachineObservation {
        input_consumed,
        output_len,
        registers,
        termination,
    }
}

const fn native_first_effect(
    entry: ProfileMachineObservation,
    middle: ProfileMachineObservation,
) -> EffectOp {
    EffectOp {
        after: middle,
        before: entry,
        input: Some(TraceInput::Byte(0x41)),
        memory_delta: ProfileMemoryDelta {
            data: Some(ProfileMemoryWrite {
                address: 7,
                after: 9,
                before: 8,
            }),
            encryption: Some(ProfileMemoryWrite {
                address: 11,
                after: 13,
                before: 12,
            }),
        },
        output: Some(0x42),
    }
}

const fn native_second_effect(
    middle: ProfileMachineObservation,
    exit: ProfileMachineObservation,
) -> EffectOp {
    EffectOp {
        after: exit,
        before: middle,
        input: None,
        memory_delta: ProfileMemoryDelta {
            data: Some(ProfileMemoryWrite {
                address: 7,
                after: 10,
                before: 9,
            }),
            encryption: Some(ProfileMemoryWrite {
                address: 11,
                after: 14,
                before: 13,
            }),
        },
        output: None,
    }
}

fn native_program() -> RegionEffectProgram {
    let entry = native_observation(
        0,
        0,
        ProfileRegisters {
            accumulator: 3,
            code_pointer: 4,
            data_pointer: 5,
        },
        None,
    );
    let middle = native_observation(
        1,
        1,
        ProfileRegisters {
            accumulator: 6,
            code_pointer: 7,
            data_pointer: 8,
        },
        None,
    );
    let exit = native_observation(
        1,
        1,
        ProfileRegisters {
            accumulator: 9,
            code_pointer: 10,
            data_pointer: 11,
        },
        Some(Termination::HaltInstruction),
    );
    RegionEffectProgram {
        effects: vec![
            native_first_effect(entry, middle),
            native_second_effect(middle, exit),
        ],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 17, value: 18 }],
        outcome: RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 2,
        },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:native-bootstrap-fixture",
        ),
        profile_id: String::from("malbolge-2026.3"),
        profile_requirement: fixture_profile_requirement(),
        step_budget: 2,
    }
}

fn profile_invalid_native_program() -> RegionEffectProgram {
    let mut program = native_program();
    program.profile_requirement.memory_words = 1;
    program
}

fn profile_capacity_overflow_native_program()
-> Result<RegionEffectProgram, String> {
    let mut program = native_program();
    let address = current_profile().memory_words();
    let effect = program
        .effects
        .first_mut()
        .ok_or_else(|| String::from("bootstrap fixture has no effect"))?;
    effect.before.registers.code_pointer = address;
    effect.after.registers.code_pointer = address;
    Ok(program)
}

fn native_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(CLANG_C23_BOOTSTRAP_BACKEND_ID),
        backend_revision: CLANG_C23_BOOTSTRAP_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_deopt_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_DEOPT_BACKEND_ID),
        backend_revision: DIRECT_DEOPT_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_execution_geometry_initial_halt_target(
    isa: HostIsa,
) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(
            DIRECT_EXECUTION_GEOMETRY_INITIAL_HALT_BACKEND_ID,
        ),
        backend_revision:
            DIRECT_EXECUTION_GEOMETRY_INITIAL_HALT_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_execution_geometry_initial_jump_data_target(
    isa: HostIsa,
) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(
            DIRECT_EXECUTION_GEOMETRY_INITIAL_JUMP_DATA_BACKEND_ID,
        ),
        backend_revision:
            DIRECT_EXECUTION_GEOMETRY_INITIAL_JUMP_DATA_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_execution_geometry_no_operation_target(
    isa: HostIsa,
) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(
            DIRECT_EXECUTION_GEOMETRY_NO_OPERATION_BACKEND_ID,
        ),
        backend_revision:
            DIRECT_EXECUTION_GEOMETRY_NO_OPERATION_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_execution_geometry_rotate_target(
    isa: HostIsa,
) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_EXECUTION_GEOMETRY_ROTATE_BACKEND_ID),
        backend_revision: DIRECT_EXECUTION_GEOMETRY_ROTATE_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_halt_registers_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0x1234_5678,
            code_pointer: 0x0034_5678,
            data_pointer: 0x0013_579b,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        termination: Some(Termination::HaltInstruction),
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta::default(),
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: Vec::new(),
        outcome: RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 1,
        },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-halt-registers-fixture",
        ),
        profile_id: String::from("malbolge-2026.3"),
        profile_requirement: fixture_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_halt_registers_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_HALT_REGISTERS_BACKEND_ID),
        backend_revision: DIRECT_HALT_REGISTERS_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_halt_fetch_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        termination: Some(Termination::HaltInstruction),
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta::default(),
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 5, value: 76 }],
        outcome: RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 1,
        },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-halt-fetch-fixture",
        ),
        profile_id: String::from("malbolge-2026.3"),
        profile_requirement: fixture_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_halt_fetch_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_HALT_FETCH_BACKEND_ID),
        backend_revision: DIRECT_HALT_FETCH_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_non_graphical_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        termination: Some(Termination::NonGraphicalCell),
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta::default(),
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 5, value: 0 }],
        outcome: RunOutcome::Terminated {
            reason: Termination::NonGraphicalCell,
            steps: 1,
        },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-non-graphical-fixture",
        ),
        profile_id: String::from("malbolge-2026.3"),
        profile_requirement: fixture_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_non_graphical_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_NON_GRAPHICAL_BACKEND_ID),
        backend_revision: DIRECT_NON_GRAPHICAL_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_jump_code_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 12,
            data_pointer: 8,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta {
                data: None,
                encryption: Some(ProfileMemoryWrite {
                    address: 11,
                    after: 33,
                    before: 68,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![
            MemoryLiveIn { address: 5, value: 93 },
            MemoryLiveIn { address: 7, value: 11 },
            MemoryLiveIn { address: 11, value: 68 },
        ],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-jump-code-fixture",
        ),
        profile_id: String::from("malbolge-2026.3"),
        profile_requirement: fixture_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_jump_code_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_JUMP_CODE_BACKEND_ID),
        backend_revision: DIRECT_JUMP_CODE_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_jump_data_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 6,
            data_pointer: 124,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta {
                data: None,
                encryption: Some(ProfileMemoryWrite {
                    address: 5,
                    after: 93,
                    before: 35,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![
            MemoryLiveIn { address: 5, value: 35 },
            MemoryLiveIn { address: 7, value: 123 },
        ],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-jump-data-fixture",
        ),
        profile_id: String::from("malbolge-2026.3"),
        profile_requirement: fixture_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_jump_data_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_JUMP_DATA_BACKEND_ID),
        backend_revision: DIRECT_JUMP_DATA_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_crazy_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 20,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: 2_391_494,
            code_pointer: 6,
            data_pointer: 8,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta {
                data: Some(ProfileMemoryWrite {
                    address: 7,
                    after: 2_391_494,
                    before: 10,
                }),
                encryption: Some(ProfileMemoryWrite {
                    address: 5,
                    after: 91,
                    before: 57,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![
            MemoryLiveIn { address: 5, value: 57 },
            MemoryLiveIn { address: 7, value: 10 },
        ],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-crazy-fixture",
        ),
        profile_id: String::from("malbolge-2026.3"),
        profile_requirement: fixture_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_crazy_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_CRAZY_BACKEND_ID),
        backend_revision: DIRECT_CRAZY_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_input_byte_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 2,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        input_consumed: 3,
        registers: ProfileRegisters {
            accumulator: 0x41,
            code_pointer: 6,
            data_pointer: 8,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: Some(TraceInput::Byte(0x41)),
            memory_delta: ProfileMemoryDelta {
                data: None,
                encryption: Some(ProfileMemoryWrite {
                    address: 5,
                    after: 68,
                    before: 112,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 5, value: 112 }],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-input-byte-fixture",
        ),
        profile_id: String::from("malbolge-2026.3"),
        profile_requirement: fixture_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_input_eof_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 2,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: 4_782_968,
            code_pointer: 6,
            data_pointer: 8,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: Some(TraceInput::EndOfInput),
            memory_delta: ProfileMemoryDelta {
                data: None,
                encryption: Some(ProfileMemoryWrite {
                    address: 5,
                    after: 68,
                    before: 112,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 5, value: 112 }],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-input-eof-fixture",
        ),
        profile_id: String::from("malbolge-2026.3"),
        profile_requirement: fixture_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_input_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_INPUT_BACKEND_ID),
        backend_revision: DIRECT_INPUT_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_output_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 3,
        registers: ProfileRegisters {
            accumulator: 0xdead_bea8,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        output_len: 4,
        registers: ProfileRegisters {
            accumulator: 0xdead_bea8,
            code_pointer: 6,
            data_pointer: 8,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta {
                data: None,
                encryption: Some(ProfileMemoryWrite {
                    address: 5,
                    after: 57,
                    before: 94,
                }),
            },
            output: Some(0xa8),
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 5, value: 94 }],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-output-fixture",
        ),
        profile_id: String::from("malbolge-2026.3"),
        profile_requirement: fixture_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_output_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_OUTPUT_BACKEND_ID),
        backend_revision: DIRECT_OUTPUT_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_rotate_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: 1_594_326,
            code_pointer: 6,
            data_pointer: 8,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta {
                data: Some(ProfileMemoryWrite {
                    address: 7,
                    after: 1_594_326,
                    before: 10,
                }),
                encryption: Some(ProfileMemoryWrite {
                    address: 5,
                    after: 122,
                    before: 34,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![
            MemoryLiveIn { address: 5, value: 34 },
            MemoryLiveIn { address: 7, value: 10 },
        ],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-rotate-fixture",
        ),
        profile_id: String::from("malbolge-2026.3"),
        profile_requirement: fixture_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_rotate_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_ROTATE_BACKEND_ID),
        backend_revision: DIRECT_ROTATE_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_no_operation_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 6,
            data_pointer: 8,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta {
                data: None,
                encryption: Some(ProfileMemoryWrite {
                    address: 5,
                    after: 65,
                    before: 77,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 5, value: 77 }],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-no-operation-fixture",
        ),
        profile_id: String::from("malbolge-2026.3"),
        profile_requirement: fixture_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_no_operation_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_NO_OPERATION_BACKEND_ID),
        backend_revision: DIRECT_NO_OPERATION_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_initial_halt_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0,
        output_len: 0,
        registers: ProfileRegisters::default(),
        termination: None,
    };
    let after = ProfileMachineObservation {
        termination: Some(Termination::HaltInstruction),
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta::default(),
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: Vec::new(),
        outcome: RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 1,
        },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-initial-halt-fixture",
        ),
        profile_id: String::from("malbolge-2026.3"),
        profile_requirement: fixture_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_initial_halt_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_INITIAL_HALT_BACKEND_ID),
        backend_revision: DIRECT_INITIAL_HALT_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn assert_cached_direct_cycle(
    cache: &mut VerifiedDirectNativeCache,
    program: &RegionEffectProgram,
    expected_kind: DirectNativeKind,
    expected_len: usize,
) -> Result<(), String> {
    let inserted = select_cached_preflighted_execution_tier(
        program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact: inserted_artifact,
        cache: DirectCacheDisposition::Inserted,
    } = inserted
    else {
        return Err(String::from("cache miss did not insert direct artifact"));
    };
    let uncached = select_verified_direct_native(
        program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|selection_error| selection_error.to_string())?;
    if inserted_artifact.kind() != expected_kind
        || inserted_artifact.key() != uncached.key()
        || inserted_artifact.object() != uncached.object()
        || cache.len() != expected_len
    {
        return Err(String::from("inserted direct artifact identity drifted"));
    }

    let hit = select_cached_preflighted_execution_tier(
        program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact: hit_artifact,
        cache: DirectCacheDisposition::Hit,
    } = hit
    else {
        return Err(String::from("exact direct cache key was not reused"));
    };
    if Arc::ptr_eq(&hit_artifact, &inserted_artifact)
        && cache.len() == expected_len
    {
        Ok(())
    } else {
        Err(String::from("direct cache hit cloned or changed artifact"))
    }
}

#[test]
fn cached_tier_planner_reuses_each_verified_template() -> Result<(), String> {
    let mut cache = VerifiedDirectNativeCache::default();
    if !cache.is_empty() {
        return Err(String::from("new verified direct cache was not empty"));
    }
    let cases = [
        (direct_initial_halt_program(), DirectNativeKind::InitialHalt),
        (
            direct_halt_registers_program(),
            DirectNativeKind::HaltRegisters,
        ),
        (direct_halt_fetch_program(), DirectNativeKind::HaltFetch),
        (
            direct_non_graphical_program(),
            DirectNativeKind::NonGraphical,
        ),
        (direct_jump_code_program(), DirectNativeKind::JumpCode),
        (direct_jump_data_program(), DirectNativeKind::JumpData),
        (direct_crazy_program(), DirectNativeKind::Crazy),
        (direct_rotate_program(), DirectNativeKind::Rotate),
        (direct_input_byte_program(), DirectNativeKind::Input),
        (direct_output_program(), DirectNativeKind::Output),
        (direct_no_operation_program(), DirectNativeKind::NoOperation),
        (native_program(), DirectNativeKind::Deopt),
    ];
    for (index, (program, kind)) in cases.iter().enumerate() {
        assert_cached_direct_cycle(&mut cache, program, *kind, index + 1)?;
    }
    cache.clear();
    if cache.is_empty() {
        Ok(())
    } else {
        Err(String::from(
            "verified direct cache clear retained artifacts",
        ))
    }
}

fn seed_verified_direct_cache(
    program: &RegionEffectProgram,
    cache: &mut VerifiedDirectNativeCache,
) -> Result<(), String> {
    let seeded = select_cached_preflighted_execution_tier(
        program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        cache,
    )
    .map_err(|error| error.to_string())?;
    if matches!(seeded, CachedPreflightedExecutionTier::Direct {
        cache: DirectCacheDisposition::Inserted,
        ..
    }) && cache.len() == 1
    {
        Ok(())
    } else {
        Err(String::from("failed to seed verified direct cache"))
    }
}

fn assert_cached_runtime_preflight(
    program: &RegionEffectProgram,
    cache: &mut VerifiedDirectNativeCache,
) -> Result<(), String> {
    let Err(error) = select_cached_preflighted_execution_tier(
        program,
        safe_rust_classic_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        cache,
    ) else {
        return Err(String::from("cache hit bypassed runtime preflight"));
    };
    let DirectSelectionError::Profile(profile) = error else {
        return Err(String::from("cached runtime error changed category"));
    };
    if profile.kind() == ProfileRequirementErrorKind::RuntimeCapabilityMissing
        && cache.len() == 1
    {
        Ok(())
    } else {
        Err(String::from("cached path lost MALBOLGE-PROFILE-001"))
    }
}

fn assert_cached_requirement_admission(
    program: &RegionEffectProgram,
    cache: &mut VerifiedDirectNativeCache,
) -> Result<(), String> {
    let mut forged = program.clone();
    forged.profile_requirement =
        TargetProfileRequirement::from_descriptor(historical_profile());
    let Err(error) = select_cached_preflighted_execution_tier(
        &forged,
        safe_rust_classic_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        cache,
    ) else {
        return Err(String::from(
            "cache hit bypassed profile requirement admission",
        ));
    };
    if error == DirectSelectionError::ProfileRequirement && cache.len() == 1 {
        Ok(())
    } else {
        Err(String::from(
            "cached path lost profile requirement admission",
        ))
    }
}

fn assert_cached_host_selection(
    program: &RegionEffectProgram,
    cache: &mut VerifiedDirectNativeCache,
) -> Result<(), String> {
    let tier = select_cached_preflighted_execution_tier(
        program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Linux, HostIsa::X86_64),
        cache,
    )
    .map_err(|error| error.to_string())?;
    if tier == CachedPreflightedExecutionTier::Interpreter && cache.len() == 1 {
        Ok(())
    } else {
        Err(String::from("cache hit bypassed host-format selection"))
    }
}

fn assert_cached_capacity_preflight(
    program: &RegionEffectProgram,
    cache: &mut VerifiedDirectNativeCache,
) -> Result<(), String> {
    let mut overflow = program.clone();
    let address = current_profile().memory_words();
    let effect = overflow
        .effects
        .first_mut()
        .ok_or_else(|| String::from("initial-halt fixture has no effect"))?;
    effect.before.registers.code_pointer = address;
    effect.after.registers.code_pointer = address;
    let Err(error) = select_cached_preflighted_execution_tier(
        &overflow,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        cache,
    ) else {
        return Err(String::from("cache lookup bypassed capacity preflight"));
    };
    let DirectSelectionError::Profile(profile) = error else {
        return Err(String::from("cached capacity error changed category"));
    };
    if profile.kind() == ProfileRequirementErrorKind::ProfileCapacityExceeded
        && cache.len() == 1
    {
        Ok(())
    } else {
        Err(String::from("cached path lost MALBOLGE-PROFILE-002"))
    }
}

fn insert_cached_direct_for_isa(
    cache: &mut VerifiedDirectNativeCache,
    program: &RegionEffectProgram,
    isa: HostIsa,
) -> Result<Arc<execution_native::VerifiedDirectNativeArtifact>, String> {
    let selected = select_cached_preflighted_execution_tier(
        program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, isa),
        cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact,
        cache: DirectCacheDisposition::Inserted,
    } = selected
    else {
        return Err(String::from("direct cache fixture was not inserted"));
    };
    Ok(artifact)
}

fn hit_cached_direct_for_isa(
    cache: &mut VerifiedDirectNativeCache,
    program: &RegionEffectProgram,
    isa: HostIsa,
) -> Result<Arc<execution_native::VerifiedDirectNativeArtifact>, String> {
    let selected = select_cached_preflighted_execution_tier(
        program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, isa),
        cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact,
        cache: DirectCacheDisposition::Hit,
    } = selected
    else {
        return Err(String::from("direct cache fixture was not reused"));
    };
    Ok(artifact)
}

#[test]
fn verified_direct_cache_invalidation_is_exact_and_nonrevoking()
-> Result<(), String> {
    let program = direct_initial_halt_program();
    let mut cache = VerifiedDirectNativeCache::default();
    let first = select_cached_preflighted_execution_tier(
        &program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        &mut cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact: first_artifact,
        cache: DirectCacheDisposition::Inserted,
    } = first
    else {
        return Err(String::from("failed to seed invalidation fixture"));
    };
    if !cache.invalidate(&first_artifact)
        || !cache.is_empty()
        || cache.invalidate(&first_artifact)
        || first_artifact.object().is_empty()
    {
        return Err(String::from(
            "exact invalidation violated cache ownership",
        ));
    }
    let second = select_cached_preflighted_execution_tier(
        &program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        &mut cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact: second_artifact,
        cache: DirectCacheDisposition::Inserted,
    } = second
    else {
        return Err(String::from("invalidated key did not reinsert"));
    };
    if Arc::ptr_eq(&first_artifact, &second_artifact)
        || first_artifact.key() != second_artifact.key()
        || first_artifact.object() != second_artifact.object()
        || !cache.invalidate(&first_artifact)
        || !cache.is_empty()
    {
        Err(String::from("invalidation changed exact-key semantics"))
    } else {
        Ok(())
    }
}

#[test]
fn verified_cache_invalidates_program_variants() -> Result<(), String> {
    let program = direct_initial_halt_program();
    let survivor = native_program();
    let mut cache = VerifiedDirectNativeCache::default();
    let x86 =
        insert_cached_direct_for_isa(&mut cache, &program, HostIsa::X86_64)?;
    let arm =
        insert_cached_direct_for_isa(&mut cache, &program, HostIsa::AArch64)?;
    let survivor_artifact =
        insert_cached_direct_for_isa(&mut cache, &survivor, HostIsa::X86_64)?;
    let mut invalid = program.clone();
    invalid.profile_requirement.memory_words = 0;
    if cache.invalidate_program(&invalid)
        != Err(NativeIdentityError::ProfileCapacity)
        || cache.len() != 3
    {
        return Err(String::from("invalid program mutated verified cache"));
    }
    if cache
        .invalidate_program(&program)
        .map_err(|error| format!("{error:?}"))?
        != 2
        || cache
            .invalidate_program(&program)
            .map_err(|error| format!("{error:?}"))?
            != 0
        || cache.len() != 1
        || x86.object().is_empty()
        || arm.object().is_empty()
    {
        return Err(String::from("program invalidation lost exact variants"));
    }
    let new_x86 =
        insert_cached_direct_for_isa(&mut cache, &program, HostIsa::X86_64)?;
    let new_arm =
        insert_cached_direct_for_isa(&mut cache, &program, HostIsa::AArch64)?;
    let survivor_plan = select_cached_preflighted_execution_tier(
        &survivor,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        &mut cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact: survivor_hit,
        cache: DirectCacheDisposition::Hit,
    } = survivor_plan
    else {
        return Err(String::from("unrelated program was invalidated"));
    };
    if Arc::ptr_eq(&x86, &new_x86)
        || Arc::ptr_eq(&arm, &new_arm)
        || x86.key() != new_x86.key()
        || arm.key() != new_arm.key()
        || !Arc::ptr_eq(&survivor_artifact, &survivor_hit)
        || cache.len() != 3
    {
        Err(String::from("program invalidation changed cache semantics"))
    } else {
        Ok(())
    }
}

#[test]
fn verified_cache_invalidates_exact_target_regions() -> Result<(), String> {
    let program = native_program();
    let mut variant = program.clone();
    variant.profile_fingerprint.push('x');
    let halt = direct_initial_halt_program();
    let mut cache = VerifiedDirectNativeCache::default();
    let x86 =
        insert_cached_direct_for_isa(&mut cache, &program, HostIsa::X86_64)?;
    let x86_variant =
        insert_cached_direct_for_isa(&mut cache, &variant, HostIsa::X86_64)?;
    let arm =
        insert_cached_direct_for_isa(&mut cache, &program, HostIsa::AArch64)?;
    let halt_x86 =
        insert_cached_direct_for_isa(&mut cache, &halt, HostIsa::X86_64)?;
    if x86.kind() != DirectNativeKind::Deopt
        || x86_variant.kind() != DirectNativeKind::Deopt
        || halt_x86.kind() != DirectNativeKind::InitialHalt
        || cache.invalidate_target(&x86) != 2
        || cache.invalidate_target(&x86_variant) != 0
        || cache.len() != 2
        || x86.object().is_empty()
        || x86_variant.object().is_empty()
    {
        return Err(String::from(
            "verified target invalidation crossed identity",
        ));
    }
    let arm_hit =
        hit_cached_direct_for_isa(&mut cache, &program, HostIsa::AArch64)?;
    let halt_hit =
        hit_cached_direct_for_isa(&mut cache, &halt, HostIsa::X86_64)?;
    let new_x86 =
        insert_cached_direct_for_isa(&mut cache, &program, HostIsa::X86_64)?;
    let new_variant =
        insert_cached_direct_for_isa(&mut cache, &variant, HostIsa::X86_64)?;
    if !Arc::ptr_eq(&arm, &arm_hit)
        || !Arc::ptr_eq(&halt_x86, &halt_hit)
        || Arc::ptr_eq(&x86, &new_x86)
        || Arc::ptr_eq(&x86_variant, &new_variant)
        || x86.key() != new_x86.key()
        || x86_variant.key() != new_variant.key()
        || cache.len() != 4
    {
        Err(String::from("target invalidation changed reuse semantics"))
    } else {
        Ok(())
    }
}

#[test]
fn cached_tier_planner_preflights_before_lookup() -> Result<(), String> {
    let program = direct_initial_halt_program();
    let mut cache = VerifiedDirectNativeCache::default();
    seed_verified_direct_cache(&program, &mut cache)?;
    assert_cached_requirement_admission(&program, &mut cache)?;
    assert_cached_runtime_preflight(&program, &mut cache)?;
    assert_cached_host_selection(&program, &mut cache)?;
    assert_cached_capacity_preflight(&program, &mut cache)
}

#[test]
fn tier_planner_uses_interpreter_only_for_missing_direct_format()
-> Result<(), String> {
    let direct = select_preflighted_execution_tier(
        &direct_initial_halt_program(),
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let PreflightedExecutionTier::Direct(artifact) = direct else {
        return Err(String::from("Windows direct tier selected interpreter"));
    };
    if artifact.kind() != DirectNativeKind::InitialHalt {
        return Err(String::from("tier planner changed direct specialization"));
    }
    for host_os in [HostOperatingSystem::Linux, HostOperatingSystem::MacOs] {
        let selected = select_preflighted_execution_tier(
            &native_program(),
            safe_rust_profiled_capability(),
            host_os,
            HostIsa::X86_64,
        )
        .map_err(|error| error.to_string())?;
        if selected != PreflightedExecutionTier::Interpreter {
            return Err(format!("{host_os:?} did not select interpreter"));
        }
    }
    Ok(())
}

fn assert_tier_planner_rejects_forged_requirement(
    current: &RegionEffectProgram,
) -> Result<(), String> {
    let mut forged = current.clone();
    forged.profile_requirement =
        TargetProfileRequirement::from_descriptor(historical_profile());
    if select_preflighted_execution_tier(
        &forged,
        safe_rust_classic_capability(),
        HostOperatingSystem::Linux,
        HostIsa::X86_64,
    ) == Err(DirectSelectionError::ProfileRequirement)
    {
        Ok(())
    } else {
        Err(String::from(
            "profile requirement mismatch degraded to interpreter",
        ))
    }
}

#[test]
fn tier_planner_preserves_profile_errors_before_fallback() -> Result<(), String>
{
    let current = direct_initial_halt_program();
    assert_tier_planner_rejects_forged_requirement(&current)?;
    let Err(runtime_error) = select_preflighted_execution_tier(
        &current,
        safe_rust_classic_capability(),
        HostOperatingSystem::Linux,
        HostIsa::X86_64,
    ) else {
        return Err(String::from("runtime mismatch degraded to interpreter"));
    };
    let DirectSelectionError::Profile(runtime_profile) = runtime_error else {
        return Err(format!(
            "runtime mismatch changed category: {runtime_error}"
        ));
    };
    if runtime_profile.kind()
        != ProfileRequirementErrorKind::RuntimeCapabilityMissing
    {
        return Err(String::from("runtime mismatch lost MALBOLGE-PROFILE-001"));
    }

    let mut overflow = direct_initial_halt_program();
    let address = current_profile().memory_words();
    let effect = overflow
        .effects
        .first_mut()
        .ok_or_else(|| String::from("initial-halt fixture has no effect"))?;
    effect.before.registers.data_pointer = address;
    effect.after.registers.data_pointer = address;
    let Err(capacity_error) = select_preflighted_execution_tier(
        &overflow,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Linux,
        HostIsa::X86_64,
    ) else {
        return Err(String::from("capacity mismatch degraded to interpreter"));
    };
    let DirectSelectionError::Profile(capacity_profile) = capacity_error else {
        return Err(format!(
            "capacity mismatch changed category: {capacity_error}"
        ));
    };
    if capacity_profile.kind()
        == ProfileRequirementErrorKind::ProfileCapacityExceeded
    {
        Ok(())
    } else {
        Err(String::from("capacity mismatch lost MALBOLGE-PROFILE-002"))
    }
}

fn selected_direct_triple(
    program: &RegionEffectProgram,
    isa: HostIsa,
    kind: DirectNativeKind,
    backend_id: &str,
) -> Result<&'static str, String> {
    let selected = select_verified_direct_native(
        program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        isa,
    )
    .map_err(|error| error.to_string())?;
    if selected.kind() != kind
        || selected.key().target().backend_id() != backend_id
        || selected.object().is_empty()
    {
        Err(format!("direct selector missed {backend_id}"))
    } else {
        Ok(selected.target_triple())
    }
}

fn direct_selection_cases() -> Vec<DirectSelectionCase> {
    let mut cases = direct_selection_terminal_cases();
    cases.extend(direct_selection_effect_cases());
    cases
}

fn direct_selection_terminal_cases() -> Vec<DirectSelectionCase> {
    vec![
        (
            direct_initial_halt_program(),
            DirectNativeKind::InitialHalt,
            DIRECT_INITIAL_HALT_BACKEND_ID,
        ),
        (
            direct_halt_registers_program(),
            DirectNativeKind::HaltRegisters,
            DIRECT_HALT_REGISTERS_BACKEND_ID,
        ),
        (
            direct_halt_fetch_program(),
            DirectNativeKind::HaltFetch,
            DIRECT_HALT_FETCH_BACKEND_ID,
        ),
        (
            direct_non_graphical_program(),
            DirectNativeKind::NonGraphical,
            DIRECT_NON_GRAPHICAL_BACKEND_ID,
        ),
    ]
}

fn direct_selection_effect_cases() -> Vec<DirectSelectionCase> {
    vec![
        (
            direct_jump_code_program(),
            DirectNativeKind::JumpCode,
            DIRECT_JUMP_CODE_BACKEND_ID,
        ),
        (
            direct_jump_data_program(),
            DirectNativeKind::JumpData,
            DIRECT_JUMP_DATA_BACKEND_ID,
        ),
        (
            direct_crazy_program(),
            DirectNativeKind::Crazy,
            DIRECT_CRAZY_BACKEND_ID,
        ),
        (
            direct_rotate_program(),
            DirectNativeKind::Rotate,
            DIRECT_ROTATE_BACKEND_ID,
        ),
        (
            direct_input_byte_program(),
            DirectNativeKind::Input,
            DIRECT_INPUT_BACKEND_ID,
        ),
        (
            direct_output_program(),
            DirectNativeKind::Output,
            DIRECT_OUTPUT_BACKEND_ID,
        ),
        (
            direct_no_operation_program(),
            DirectNativeKind::NoOperation,
            DIRECT_NO_OPERATION_BACKEND_ID,
        ),
        (
            native_program(),
            DirectNativeKind::Deopt,
            DIRECT_DEOPT_BACKEND_ID,
        ),
    ]
}

#[test]
fn direct_selector_chooses_fast_path_or_verified_deopt_deterministically()
-> Result<(), String> {
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        let mut expected = None;
        for (program, kind, backend_id) in direct_selection_cases() {
            let triple =
                selected_direct_triple(&program, isa, kind, backend_id)?;
            if let Some(previous) = expected
                && previous != triple
            {
                return Err(String::from("direct tier changed target triple"));
            }
            expected = Some(triple);
        }
    }
    Ok(())
}

#[test]
fn direct_selector_prioritizes_program_capacity() -> Result<(), String> {
    let mut program = direct_initial_halt_program();
    let overflow_address = current_profile().memory_words();
    let effect = program
        .effects
        .first_mut()
        .ok_or_else(|| String::from("initial-halt fixture has no effect"))?;
    effect.before.registers.code_pointer = overflow_address;
    effect.after.registers.code_pointer = overflow_address;

    let Err(error) = select_verified_direct_native(
        &program,
        safe_rust_classic_capability(),
        HostOperatingSystem::Linux,
        HostIsa::X86_64,
    ) else {
        return Err(String::from("profile-capacity overflow was selected"));
    };
    let DirectSelectionError::Profile(profile_error) = error else {
        return Err(format!("program capacity lost precedence: {error}"));
    };
    if profile_error.kind()
        != ProfileRequirementErrorKind::ProfileCapacityExceeded
    {
        return Err(format!("program capacity category: {profile_error}"));
    }
    let expected = concat!(
        "MALBOLGE-PROFILE-002 profile=malbolge-2026.3 version=2026.3 ",
        "constraint=profile-capacity-ceiling required_memory_words=4782970 ",
        "profile_memory_words=4782969"
    );
    if profile_error.to_string() == expected {
        Ok(())
    } else {
        Err(format!("program capacity diagnostic: {profile_error}"))
    }
}

#[test]
fn direct_sequence_blocks_capacity_overflow_before_retry_authority()
-> Result<(), String> {
    let mut program = direct_initial_halt_program();
    let overflow_address = current_profile().memory_words();
    let effect = program
        .effects
        .first_mut()
        .ok_or_else(|| String::from("initial-halt fixture has no effect"))?;
    effect.before.registers.code_pointer = overflow_address;
    effect.after.registers.code_pointer = overflow_address;
    let programs = [program];

    let Err(sequence_error) = select_verified_direct_sequence(
        &programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    ) else {
        return Err(String::from(
            "capacity overflow published a verified sequence plan",
        ));
    };
    let DirectSequenceError::Step {
        error: selection_error,
        index: 0,
    } = sequence_error
    else {
        return Err(format!(
            "capacity overflow changed sequence error: {sequence_error}"
        ));
    };
    let DirectSelectionError::Profile(profile_error) = *selection_error else {
        return Err(String::from(
            "capacity overflow lost profile error before sequence publication",
        ));
    };
    if profile_error.kind()
        == ProfileRequirementErrorKind::ProfileCapacityExceeded
        && profile_error
            .to_string()
            .starts_with("MALBOLGE-PROFILE-002 ")
    {
        Ok(())
    } else {
        Err(format!(
            "sequence capacity preflight diagnostic drifted: {profile_error}"
        ))
    }
}

#[test]
fn direct_selector_rejects_forged_profile_requirement() -> Result<(), String> {
    let mut program = direct_initial_halt_program();
    program.profile_requirement =
        TargetProfileRequirement::from_descriptor(historical_profile());

    if select_verified_direct_native(
        &program,
        safe_rust_classic_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    ) == Err(DirectSelectionError::ProfileRequirement)
    {
        Ok(())
    } else {
        Err(String::from(
            "forged profile requirement bypassed direct admission",
        ))
    }
}

#[test]
fn direct_selector_prioritizes_profile_preflight() -> Result<(), String> {
    let program = direct_initial_halt_program();
    let Err(error) = select_verified_direct_native(
        &program,
        safe_rust_classic_capability(),
        HostOperatingSystem::Linux,
        HostIsa::X86_64,
    ) else {
        return Err(String::from(
            "unsupported profile reached direct native construction",
        ));
    };
    let DirectSelectionError::Profile(profile_error) = error else {
        return Err(format!(
            "profile preflight lost precedence to direct selection: {error}"
        ));
    };
    let fixture = target_profile(FIXTURE_PROFILE_ID)
        .ok_or_else(|| String::from("fixture profile is missing"))?;
    let Err(canonical) = preflight_profile(
        fixture,
        u64::from(fixture.memory_words()),
        safe_rust_classic_capability(),
    ) else {
        return Err(String::from("fixture profile was admitted"));
    };
    if format!("{profile_error}") == format!("{canonical}") {
        Ok(())
    } else {
        Err(String::from(
            "direct selector changed shared profile diagnostic",
        ))
    }
}

#[test]
fn direct_selector_rejects_unsupported_host_format_without_fallback()
-> Result<(), String> {
    for host_os in [HostOperatingSystem::Linux, HostOperatingSystem::MacOs] {
        if select_verified_direct_native(
            &native_program(),
            safe_rust_profiled_capability(),
            host_os,
            HostIsa::X86_64,
        ) != Err(DirectSelectionError::TargetFormat)
        {
            return Err(format!(
                "unsupported direct host {host_os:?} was admitted"
            ));
        }
    }
    Ok(())
}

#[test]
fn direct_halt_register_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!(
                "execution/fixtures/native-halt-registers-x86_64-coff.hex"
            ),
        ),
        (
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-halt-registers-aarch64-coff.hex"
            ),
        ),
    ];
    let program = direct_halt_registers_program();
    for (isa, fixture) in cases {
        let artifact = emit_direct_halt_registers_coff(
            &program,
            direct_halt_registers_target(isa),
        )
        .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!(
                "direct register-halt fixture mismatch for {isa:?}"
            ));
        }
        let verified = verify_direct_halt_registers(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from(
                "verified register-halt identity drifted",
            ));
        }
    }
    Ok(())
}

#[test]
fn direct_halt_observation_revision_rejects_v4_identity() -> Result<(), String>
{
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_HALT_REGISTERS_BACKEND_ID),
        backend_revision: 4,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_halt_registers_coff(
        &direct_halt_registers_program(),
        obsolete,
    ) == Err(DirectHaltRegistersError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("historical halt revision was admitted"))
    }
}

fn assert_halt_counter_identity_rejected(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut mismatch = program.clone();
    let effect = mismatch.effects.first_mut().ok_or_else(|| {
        String::from("register-halt counter fixture lost effect")
    })?;
    effect.before.input_consumed =
        effect.before.input_consumed.saturating_add(1);
    effect.after.input_consumed = effect.after.input_consumed.saturating_add(1);
    if verify_direct_halt_registers(artifact, &mismatch)
        == Err(DirectHaltRegistersError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("counter-mismatched halt object was admitted"))
    }
}

#[test]
fn direct_halt_registers_rejects_ir_and_opcode_tampering() -> Result<(), String>
{
    let program = direct_halt_registers_program();
    let artifact = emit_direct_halt_registers_coff(
        &program,
        direct_halt_registers_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let immediate = 0x1234_5678u32.to_le_bytes();
    let offset = mutated_object
        .windows(immediate.len())
        .position(|window| window == immediate)
        .ok_or_else(|| {
            String::from("register-halt accumulator immediate missing")
        })?;
    let first = mutated_object.get_mut(offset).ok_or_else(|| {
        String::from("register-halt immediate offset invalid")
    })?;
    *first ^= 1;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered).map_err(|error| {
        format!("tampered register-halt structure: {error}")
    })?;
    if verify_direct_halt_registers(&tampered, &program)
        != Err(DirectHaltRegistersError::ObjectBytes)
    {
        return Err(String::from("tampered register-halt object was admitted"));
    }

    assert_halt_counter_identity_rejected(&artifact, &program)?;

    let mut with_output = program;
    let first_effect = with_output
        .effects
        .first_mut()
        .ok_or_else(|| String::from("register-halt fixture lost effect"))?;
    first_effect.output = Some(0x41);
    if emit_direct_halt_registers_coff(
        &with_output,
        direct_halt_registers_target(HostIsa::X86_64),
    ) != Err(DirectHaltRegistersError::ProgramShape)
    {
        return Err(String::from("register-halt output mutation was admitted"));
    }
    Ok(())
}

#[test]
fn direct_halt_fetch_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!(
                "execution/fixtures/native-halt-fetch-x86_64-coff.hex"
            ),
        ),
        (
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-halt-fetch-aarch64-coff.hex"
            ),
        ),
    ];
    let program = direct_halt_fetch_program();
    for (isa, fixture) in cases {
        let artifact = emit_direct_halt_fetch_coff(
            &program,
            direct_halt_fetch_target(isa),
        )
        .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!(
                "direct halt-fetch fixture mismatch for {isa:?}"
            ));
        }
        let verified = verify_direct_halt_fetch(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified halt-fetch identity drifted"));
        }
    }
    Ok(())
}

fn assert_halt_fetch_shape_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_decode = program.clone();
    let decoded_live_in = wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("halt-fetch fixture lost live-in"))?;
    decoded_live_in.value = 77;
    if emit_direct_halt_fetch_coff(
        &wrong_decode,
        direct_halt_fetch_target(HostIsa::X86_64),
    ) != Err(DirectHaltFetchError::ProgramShape)
    {
        return Err(String::from("non-halt graphical live-in was admitted"));
    }
    let mut wrong_address = program.clone();
    let address_live_in =
        wrong_address.memory_live_ins.first_mut().ok_or_else(|| {
            String::from("halt-fetch fixture lost address live-in")
        })?;
    address_live_in.address = 6;
    if emit_direct_halt_fetch_coff(
        &wrong_address,
        direct_halt_fetch_target(HostIsa::X86_64),
    ) == Err(DirectHaltFetchError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("wrong halt-fetch live-in was admitted"))
    }
}

fn assert_halt_fetch_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_HALT_FETCH_BACKEND_ID),
        backend_revision: 1,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_halt_fetch_coff(program, obsolete)
        == Err(DirectHaltFetchError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete halt-fetch revision was admitted"))
    }
}

#[test]
fn direct_halt_fetch_rejects_ir_opcode_and_revision_tampering()
-> Result<(), String> {
    let program = direct_halt_fetch_program();
    let artifact = emit_direct_halt_fetch_coff(
        &program,
        direct_halt_fetch_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0xc6u8, 0x41, 0x4c, 0x01];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("halt-fetch commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(3))
        .ok_or_else(|| String::from("halt-fetch commit immediate missing"))?;
    *immediate = 2;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered halt-fetch structure: {error}"))?;
    if verify_direct_halt_fetch(&tampered, &program)
        != Err(DirectHaltFetchError::ObjectBytes)
    {
        return Err(String::from("tampered halt-fetch object was admitted"));
    }
    assert_halt_fetch_shape_rejections(&program)?;
    assert_halt_fetch_revision_rejected(&program)
}

#[test]
fn direct_jump_code_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!("execution/fixtures/native-jump-code-x86_64-coff.hex"),
        ),
        (
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-jump-code-aarch64-coff.hex"
            ),
        ),
    ];
    let program = direct_jump_code_program();
    for (isa, fixture) in cases {
        let artifact =
            emit_direct_jump_code_coff(&program, direct_jump_code_target(isa))
                .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!(
                "direct jump-code fixture mismatch for {isa:?}"
            ));
        }
        let verified = verify_direct_jump_code(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified jump-code identity drifted"));
        }
    }
    Ok(())
}

fn assert_jump_code_live_in_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_decode = program.clone();
    wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("jump-code fixture lost code live-in"))?
        .value = 35;
    if emit_direct_jump_code_coff(
        &wrong_decode,
        direct_jump_code_target(HostIsa::X86_64),
    ) != Err(DirectJumpCodeError::ProgramShape)
    {
        return Err(String::from("jump-data decode was admitted as jump-code"));
    }

    let mut wrong_target = program.clone();
    wrong_target
        .memory_live_ins
        .get_mut(1)
        .ok_or_else(|| String::from("jump-code fixture lost data live-in"))?
        .value = 12;
    if emit_direct_jump_code_coff(
        &wrong_target,
        direct_jump_code_target(HostIsa::X86_64),
    ) != Err(DirectJumpCodeError::ProgramShape)
    {
        return Err(String::from("wrong jump-code target was admitted"));
    }

    let mut wrong_encryption = program.clone();
    wrong_encryption
        .memory_live_ins
        .get_mut(2)
        .ok_or_else(|| {
            String::from("jump-code fixture lost encryption live-in")
        })?
        .value = 69;
    if emit_direct_jump_code_coff(
        &wrong_encryption,
        direct_jump_code_target(HostIsa::X86_64),
    ) == Err(DirectJumpCodeError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from(
            "wrong jump-code encryption live-in was admitted",
        ))
    }
}

fn assert_jump_code_transition_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut aliased = program.clone();
    aliased
        .memory_live_ins
        .get_mut(1)
        .ok_or_else(|| String::from("jump-code fixture lost data live-in"))?
        .value = 5;
    if emit_direct_jump_code_coff(
        &aliased,
        direct_jump_code_target(HostIsa::X86_64),
    ) != Err(DirectJumpCodeError::ProgramShape)
    {
        return Err(String::from("aliased jump-code was admitted"));
    }

    let mut wrong_exit = program.clone();
    wrong_exit
        .effects
        .first_mut()
        .ok_or_else(|| String::from("jump-code fixture lost effect"))?
        .after
        .registers
        .code_pointer = 13;
    if emit_direct_jump_code_coff(
        &wrong_exit,
        direct_jump_code_target(HostIsa::X86_64),
    ) != Err(DirectJumpCodeError::ProgramShape)
    {
        return Err(String::from("wrong jump-code exit was admitted"));
    }

    let mut wrong_delta = program.clone();
    wrong_delta
        .effects
        .first_mut()
        .and_then(|operation| operation.memory_delta.encryption.as_mut())
        .ok_or_else(|| String::from("jump-code fixture lost encryption"))?
        .after = 34;
    if emit_direct_jump_code_coff(
        &wrong_delta,
        direct_jump_code_target(HostIsa::X86_64),
    ) == Err(DirectJumpCodeError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("wrong jump-code encryption was admitted"))
    }
}

fn assert_jump_code_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_JUMP_CODE_BACKEND_ID),
        backend_revision: 0,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_jump_code_coff(program, obsolete)
        == Err(DirectJumpCodeError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete jump-code revision was admitted"))
    }
}

#[test]
fn direct_jump_code_rejects_ir_opcode_and_revision_tampering()
-> Result<(), String> {
    let program = direct_jump_code_program();
    let artifact = emit_direct_jump_code_coff(
        &program,
        direct_jump_code_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0xc7u8, 0x82, 0x2c, 0x00, 0x00, 0x00, 0x21, 0x00, 0x00, 0x00];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("jump-code commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(6))
        .ok_or_else(|| String::from("jump-code commit immediate missing"))?;
    *immediate = 34;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered jump-code structure: {error}"))?;
    if verify_direct_jump_code(&tampered, &program)
        != Err(DirectJumpCodeError::ObjectBytes)
    {
        return Err(String::from("tampered jump-code object was admitted"));
    }
    assert_jump_code_live_in_rejections(&program)?;
    assert_jump_code_transition_rejections(&program)?;
    assert_jump_code_revision_rejected(&program)
}

#[test]
fn direct_jump_data_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!("execution/fixtures/native-jump-data-x86_64-coff.hex"),
        ),
        (
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-jump-data-aarch64-coff.hex"
            ),
        ),
    ];
    let program = direct_jump_data_program();
    for (isa, fixture) in cases {
        let artifact =
            emit_direct_jump_data_coff(&program, direct_jump_data_target(isa))
                .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!(
                "direct jump-data fixture mismatch for {isa:?}"
            ));
        }
        let verified = verify_direct_jump_data(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified jump-data identity drifted"));
        }
    }
    Ok(())
}

fn assert_jump_data_shape_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_decode = program.clone();
    wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("jump-data fixture lost code live-in"))?
        .value = 77;
    if emit_direct_jump_data_coff(
        &wrong_decode,
        direct_jump_data_target(HostIsa::X86_64),
    ) != Err(DirectJumpDataError::ProgramShape)
    {
        return Err(String::from("no-op decode was admitted as jump-data"));
    }

    let mut aliased = program.clone();
    let effect = aliased
        .effects
        .first_mut()
        .ok_or_else(|| String::from("jump-data fixture lost effect"))?;
    effect.before.registers.data_pointer = 5;
    if emit_direct_jump_data_coff(
        &aliased,
        direct_jump_data_target(HostIsa::X86_64),
    ) != Err(DirectJumpDataError::ProgramShape)
    {
        return Err(String::from("aliased jump-data was admitted"));
    }

    let mut wrong_exit = program.clone();
    wrong_exit
        .effects
        .first_mut()
        .ok_or_else(|| String::from("jump-data fixture lost effect"))?
        .after
        .registers
        .data_pointer = 125;
    if emit_direct_jump_data_coff(
        &wrong_exit,
        direct_jump_data_target(HostIsa::X86_64),
    ) != Err(DirectJumpDataError::ProgramShape)
    {
        return Err(String::from("wrong jump-data exit was admitted"));
    }

    let mut wrong_delta = program.clone();
    wrong_delta
        .effects
        .first_mut()
        .and_then(|operation| operation.memory_delta.encryption.as_mut())
        .ok_or_else(|| String::from("jump-data fixture lost encryption"))?
        .after = 94;
    if emit_direct_jump_data_coff(
        &wrong_delta,
        direct_jump_data_target(HostIsa::X86_64),
    ) == Err(DirectJumpDataError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("wrong jump-data encryption was admitted"))
    }
}

fn assert_jump_data_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_JUMP_DATA_BACKEND_ID),
        backend_revision: 0,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_jump_data_coff(program, obsolete)
        == Err(DirectJumpDataError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete jump-data revision was admitted"))
    }
}

#[test]
fn direct_jump_data_rejects_ir_opcode_and_revision_tampering()
-> Result<(), String> {
    let program = direct_jump_data_program();
    let artifact = emit_direct_jump_data_coff(
        &program,
        direct_jump_data_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0xc7u8, 0x82, 0x14, 0x00, 0x00, 0x00, 0x5d, 0x00, 0x00, 0x00];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("jump-data commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(6))
        .ok_or_else(|| String::from("jump-data commit immediate missing"))?;
    *immediate = 94;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered jump-data structure: {error}"))?;
    if verify_direct_jump_data(&tampered, &program)
        != Err(DirectJumpDataError::ObjectBytes)
    {
        return Err(String::from("tampered jump-data object was admitted"));
    }
    assert_jump_data_shape_rejections(&program)?;
    assert_jump_data_revision_rejected(&program)
}

#[test]
fn direct_crazy_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!("execution/fixtures/native-crazy-x86_64-coff.hex"),
        ),
        (
            HostIsa::AArch64,
            include_str!("execution/fixtures/native-crazy-aarch64-coff.hex"),
        ),
    ];
    let program = direct_crazy_program();
    for (isa, fixture) in cases {
        let artifact =
            emit_direct_crazy_coff(&program, direct_crazy_target(isa))
                .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!("direct crazy fixture mismatch for {isa:?}"));
        }
        let verified = verify_direct_crazy(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified crazy identity drifted"));
        }
    }
    Ok(())
}

fn assert_crazy_decode_and_alias_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_decode = program.clone();
    wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("crazy fixture lost code live-in"))?
        .value = 34;
    if emit_direct_crazy_coff(
        &wrong_decode,
        direct_crazy_target(HostIsa::X86_64),
    ) != Err(DirectCrazyError::ProgramShape)
    {
        return Err(String::from("rotate decode was admitted as crazy"));
    }
    let mut aliased = program.clone();
    aliased
        .effects
        .first_mut()
        .ok_or_else(|| String::from("crazy fixture lost effect"))?
        .before
        .registers
        .data_pointer = 5;
    if emit_direct_crazy_coff(&aliased, direct_crazy_target(HostIsa::X86_64))
        != Err(DirectCrazyError::ProgramShape)
    {
        return Err(String::from("aliased crazy was admitted"));
    }
    Ok(())
}

fn assert_crazy_value_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut out_of_domain = program.clone();
    out_of_domain
        .effects
        .first_mut()
        .ok_or_else(|| String::from("crazy fixture lost effect"))?
        .before
        .registers
        .accumulator = current_profile().memory_words();
    if emit_direct_crazy_coff(
        &out_of_domain,
        direct_crazy_target(HostIsa::X86_64),
    ) != Err(DirectCrazyError::ProgramShape)
    {
        return Err(String::from("out-of-domain crazy accumulator admitted"));
    }
    let mut wrong_exit = program.clone();
    wrong_exit
        .effects
        .first_mut()
        .ok_or_else(|| String::from("crazy fixture lost effect"))?
        .after
        .registers
        .accumulator = 2_391_495;
    if emit_direct_crazy_coff(&wrong_exit, direct_crazy_target(HostIsa::X86_64))
        != Err(DirectCrazyError::ProgramShape)
    {
        return Err(String::from("wrong crazy accumulator was admitted"));
    }
    Ok(())
}

fn assert_crazy_delta_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_data = program.clone();
    wrong_data
        .effects
        .first_mut()
        .and_then(|effect| effect.memory_delta.data.as_mut())
        .ok_or_else(|| String::from("crazy fixture lost data write"))?
        .after = 2_391_495;
    if emit_direct_crazy_coff(&wrong_data, direct_crazy_target(HostIsa::X86_64))
        != Err(DirectCrazyError::ProgramShape)
    {
        return Err(String::from("wrong crazy data write was admitted"));
    }
    let mut wrong_encryption = program.clone();
    wrong_encryption
        .effects
        .first_mut()
        .and_then(|effect| effect.memory_delta.encryption.as_mut())
        .ok_or_else(|| String::from("crazy fixture lost encryption write"))?
        .after = 92;
    if emit_direct_crazy_coff(
        &wrong_encryption,
        direct_crazy_target(HostIsa::X86_64),
    ) != Err(DirectCrazyError::ProgramShape)
    {
        return Err(String::from("wrong crazy encryption was admitted"));
    }
    Ok(())
}

fn assert_crazy_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_CRAZY_BACKEND_ID),
        backend_revision: 0,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_crazy_coff(program, obsolete)
        == Err(DirectCrazyError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete crazy revision was admitted"))
    }
}

#[test]
fn direct_crazy_rejects_ir_and_opcode_tampering() -> Result<(), String> {
    let program = direct_crazy_program();
    let artifact =
        emit_direct_crazy_coff(&program, direct_crazy_target(HostIsa::X86_64))
            .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0xc7u8, 0x82, 0x1c, 0, 0, 0, 0xc6, 0x7d, 0x24, 0];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("crazy data commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(6))
        .ok_or_else(|| String::from("crazy data commit immediate missing"))?;
    *immediate = 0xc7;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered crazy structure: {error}"))?;
    if verify_direct_crazy(&tampered, &program)
        != Err(DirectCrazyError::ObjectBytes)
    {
        return Err(String::from("tampered crazy object was admitted"));
    }
    assert_crazy_decode_and_alias_rejected(&program)?;
    assert_crazy_value_rejections(&program)?;
    assert_crazy_delta_rejections(&program)?;
    assert_crazy_revision_rejected(&program)
}

#[test]
fn direct_input_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            direct_input_byte_program(),
            HostIsa::X86_64,
            include_str!(
                "execution/fixtures/native-input-byte-x86_64-coff.hex"
            ),
        ),
        (
            direct_input_byte_program(),
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-input-byte-aarch64-coff.hex"
            ),
        ),
        (
            direct_input_eof_program(),
            HostIsa::X86_64,
            include_str!("execution/fixtures/native-input-eof-x86_64-coff.hex"),
        ),
        (
            direct_input_eof_program(),
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-input-eof-aarch64-coff.hex"
            ),
        ),
    ];
    for (program, isa, fixture) in cases {
        let artifact =
            emit_direct_input_coff(&program, direct_input_target(isa))
                .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!("direct input fixture mismatch for {isa:?}"));
        }
        let verified = verify_direct_input(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified input identity drifted"));
        }
    }
    Ok(())
}

fn assert_input_shape_rejections() -> Result<(), String> {
    let mut wrong_decode = direct_input_byte_program();
    wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("input fixture lost live-in"))?
        .value = 94;
    if emit_direct_input_coff(
        &wrong_decode,
        direct_input_target(HostIsa::X86_64),
    ) != Err(DirectInputError::ProgramShape)
    {
        return Err(String::from("output decode was admitted as input"));
    }
    let mut wrong_byte = direct_input_byte_program();
    wrong_byte
        .effects
        .first_mut()
        .ok_or_else(|| String::from("input fixture lost effect"))?
        .input = Some(TraceInput::Byte(0x42));
    if emit_direct_input_coff(&wrong_byte, direct_input_target(HostIsa::X86_64))
        != Err(DirectInputError::ProgramShape)
    {
        return Err(String::from("wrong input byte was admitted"));
    }
    let mut wrong_cursor = direct_input_byte_program();
    wrong_cursor
        .effects
        .first_mut()
        .ok_or_else(|| String::from("input fixture lost effect"))?
        .after
        .input_consumed = 4;
    if emit_direct_input_coff(
        &wrong_cursor,
        direct_input_target(HostIsa::X86_64),
    ) != Err(DirectInputError::ProgramShape)
    {
        return Err(String::from("wrong input cursor was admitted"));
    }
    let mut wrong_eof = direct_input_eof_program();
    wrong_eof
        .effects
        .first_mut()
        .ok_or_else(|| String::from("EOF fixture lost effect"))?
        .after
        .registers
        .accumulator = 4_782_967;
    if emit_direct_input_coff(&wrong_eof, direct_input_target(HostIsa::X86_64))
        != Err(DirectInputError::ProgramShape)
    {
        return Err(String::from("wrong EOF word was admitted"));
    }
    Ok(())
}

fn assert_input_revision_rejected() -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_INPUT_BACKEND_ID),
        backend_revision: 0,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_input_coff(&direct_input_byte_program(), obsolete)
        == Err(DirectInputError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete input revision was admitted"))
    }
}

#[test]
fn direct_input_rejects_ir_and_opcode_tampering() -> Result<(), String> {
    let program = direct_input_byte_program();
    let artifact =
        emit_direct_input_coff(&program, direct_input_target(HostIsa::X86_64))
            .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let guard = [0x43u8, 0x80, 0x3c, 0x13, 0x41];
    let offset = mutated_object
        .windows(guard.len())
        .position(|window| window == guard)
        .ok_or_else(|| String::from("input byte guard missing"))?;
    let byte = mutated_object
        .get_mut(offset.saturating_add(4))
        .ok_or_else(|| String::from("input byte immediate missing"))?;
    *byte = 0x42;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered input structure: {error}"))?;
    if verify_direct_input(&tampered, &program)
        != Err(DirectInputError::ObjectBytes)
    {
        return Err(String::from("tampered input object was admitted"));
    }
    assert_input_shape_rejections()?;
    assert_input_revision_rejected()
}

#[test]
fn direct_output_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!("execution/fixtures/native-output-x86_64-coff.hex"),
        ),
        (
            HostIsa::AArch64,
            include_str!("execution/fixtures/native-output-aarch64-coff.hex"),
        ),
    ];
    let program = direct_output_program();
    for (isa, fixture) in cases {
        let artifact =
            emit_direct_output_coff(&program, direct_output_target(isa))
                .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!("direct output fixture mismatch for {isa:?}"));
        }
        let verified = verify_direct_output(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified output identity drifted"));
        }
    }
    Ok(())
}

fn assert_output_shape_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_decode = program.clone();
    wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("output fixture lost live-in"))?
        .value = 77;
    if emit_direct_output_coff(
        &wrong_decode,
        direct_output_target(HostIsa::X86_64),
    ) != Err(DirectOutputError::ProgramShape)
    {
        return Err(String::from("no-op decode was admitted as output"));
    }
    let mut wrong_output = program.clone();
    wrong_output
        .effects
        .first_mut()
        .ok_or_else(|| String::from("output fixture lost effect"))?
        .output = Some(0xa9);
    if emit_direct_output_coff(
        &wrong_output,
        direct_output_target(HostIsa::X86_64),
    ) != Err(DirectOutputError::ProgramShape)
    {
        return Err(String::from("wrong output byte was admitted"));
    }
    let mut wrong_length = program.clone();
    wrong_length
        .effects
        .first_mut()
        .ok_or_else(|| String::from("output fixture lost effect"))?
        .after
        .output_len = 5;
    if emit_direct_output_coff(
        &wrong_length,
        direct_output_target(HostIsa::X86_64),
    ) != Err(DirectOutputError::ProgramShape)
    {
        return Err(String::from("wrong output length was admitted"));
    }
    Ok(())
}

fn assert_output_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_OUTPUT_BACKEND_ID),
        backend_revision: 0,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_output_coff(program, obsolete)
        == Err(DirectOutputError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete output revision was admitted"))
    }
}

#[test]
fn direct_output_rejects_ir_and_opcode_tampering() -> Result<(), String> {
    let program = direct_output_program();
    let artifact = emit_direct_output_coff(
        &program,
        direct_output_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0x43u8, 0xc6, 0x04, 0x13, 0xa8];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("output byte commit missing"))?;
    let byte = mutated_object
        .get_mut(offset.saturating_add(4))
        .ok_or_else(|| String::from("output byte immediate missing"))?;
    *byte = 0xa9;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered output structure: {error}"))?;
    if verify_direct_output(&tampered, &program)
        != Err(DirectOutputError::ObjectBytes)
    {
        return Err(String::from("tampered output object was admitted"));
    }
    assert_output_shape_rejections(&program)?;
    assert_output_revision_rejected(&program)
}

#[test]
fn direct_rotate_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!("execution/fixtures/native-rotate-x86_64-coff.hex"),
        ),
        (
            HostIsa::AArch64,
            include_str!("execution/fixtures/native-rotate-aarch64-coff.hex"),
        ),
    ];
    let program = direct_rotate_program();
    for (isa, fixture) in cases {
        let artifact =
            emit_direct_rotate_coff(&program, direct_rotate_target(isa))
                .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!("direct rotate fixture mismatch for {isa:?}"));
        }
        let verified = verify_direct_rotate(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified rotate identity drifted"));
        }
    }
    Ok(())
}

fn assert_rotate_shape_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_decode = program.clone();
    wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("rotate fixture lost code live-in"))?
        .value = 35;
    if emit_direct_rotate_coff(
        &wrong_decode,
        direct_rotate_target(HostIsa::X86_64),
    ) != Err(DirectRotateError::ProgramShape)
    {
        return Err(String::from("jump-data decode was admitted as rotate"));
    }
    let mut aliased = program.clone();
    aliased
        .effects
        .first_mut()
        .ok_or_else(|| String::from("rotate fixture lost effect"))?
        .before
        .registers
        .data_pointer = 5;
    if emit_direct_rotate_coff(&aliased, direct_rotate_target(HostIsa::X86_64))
        != Err(DirectRotateError::ProgramShape)
    {
        return Err(String::from("aliased rotate was admitted"));
    }
    let mut out_of_domain = program.clone();
    out_of_domain
        .memory_live_ins
        .get_mut(1)
        .ok_or_else(|| String::from("rotate fixture lost data live-in"))?
        .value = current_profile().memory_words();
    if emit_direct_rotate_coff(
        &out_of_domain,
        direct_rotate_target(HostIsa::X86_64),
    ) != Err(DirectRotateError::ProgramShape)
    {
        return Err(String::from("out-of-domain rotate data was admitted"));
    }
    let mut wrong_exit = program.clone();
    wrong_exit
        .effects
        .first_mut()
        .ok_or_else(|| String::from("rotate fixture lost effect"))?
        .after
        .registers
        .accumulator = 1_594_327;
    if emit_direct_rotate_coff(
        &wrong_exit,
        direct_rotate_target(HostIsa::X86_64),
    ) != Err(DirectRotateError::ProgramShape)
    {
        return Err(String::from("wrong rotate accumulator was admitted"));
    }
    assert_rotate_delta_rejections(program)
}

fn assert_rotate_delta_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_data = program.clone();
    wrong_data
        .effects
        .first_mut()
        .and_then(|effect| effect.memory_delta.data.as_mut())
        .ok_or_else(|| String::from("rotate fixture lost data write"))?
        .after = 1_594_327;
    if emit_direct_rotate_coff(
        &wrong_data,
        direct_rotate_target(HostIsa::X86_64),
    ) != Err(DirectRotateError::ProgramShape)
    {
        return Err(String::from("wrong rotate data write was admitted"));
    }
    let mut wrong_encryption = program.clone();
    wrong_encryption
        .effects
        .first_mut()
        .and_then(|effect| effect.memory_delta.encryption.as_mut())
        .ok_or_else(|| String::from("rotate fixture lost encryption write"))?
        .after = 123;
    if emit_direct_rotate_coff(
        &wrong_encryption,
        direct_rotate_target(HostIsa::X86_64),
    ) == Err(DirectRotateError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("wrong rotate encryption was admitted"))
    }
}

fn assert_rotate_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_ROTATE_BACKEND_ID),
        backend_revision: 0,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_rotate_coff(program, obsolete)
        == Err(DirectRotateError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete rotate revision was admitted"))
    }
}

#[test]
fn direct_rotate_rejects_ir_and_opcode_tampering() -> Result<(), String> {
    let program = direct_rotate_program();
    let artifact = emit_direct_rotate_coff(
        &program,
        direct_rotate_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0xc7u8, 0x82, 0x1c, 0x00, 0x00, 0x00, 0xd6, 0x53, 0x18, 0x00];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("rotate data commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(6))
        .ok_or_else(|| String::from("rotate data commit immediate missing"))?;
    *immediate = 0xd7;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered rotate structure: {error}"))?;
    if verify_direct_rotate(&tampered, &program)
        != Err(DirectRotateError::ObjectBytes)
    {
        return Err(String::from("tampered rotate object was admitted"));
    }
    assert_rotate_shape_rejections(&program)?;
    assert_rotate_revision_rejected(&program)
}

#[test]
fn direct_no_operation_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!(
                "execution/fixtures/native-no-operation-x86_64-coff.hex"
            ),
        ),
        (
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-no-operation-aarch64-coff.hex"
            ),
        ),
    ];
    let program = direct_no_operation_program();
    for (isa, fixture) in cases {
        let artifact = emit_direct_no_operation_coff(
            &program,
            direct_no_operation_target(isa),
        )
        .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!(
                "direct no-operation fixture mismatch for {isa:?}"
            ));
        }
        let verified = verify_direct_no_operation(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified no-operation identity drifted"));
        }
    }
    Ok(())
}

fn assert_no_operation_shape_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_decode = program.clone();
    wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("no-operation fixture lost live-in"))?
        .value = 76;
    if emit_direct_no_operation_coff(
        &wrong_decode,
        direct_no_operation_target(HostIsa::X86_64),
    ) != Err(DirectNoOperationError::ProgramShape)
    {
        return Err(String::from("halt decode was admitted as no-operation"));
    }

    let mut wrong_pointer = program.clone();
    wrong_pointer
        .effects
        .first_mut()
        .ok_or_else(|| String::from("no-operation fixture lost effect"))?
        .after
        .registers
        .code_pointer = 7;
    if emit_direct_no_operation_coff(
        &wrong_pointer,
        direct_no_operation_target(HostIsa::X86_64),
    ) != Err(DirectNoOperationError::ProgramShape)
    {
        return Err(String::from("wrong no-operation pointer was admitted"));
    }

    let mut wrong_delta = program.clone();
    wrong_delta
        .effects
        .first_mut()
        .and_then(|effect| effect.memory_delta.encryption.as_mut())
        .ok_or_else(|| String::from("no-operation fixture lost encryption"))?
        .after = 66;
    if emit_direct_no_operation_coff(
        &wrong_delta,
        direct_no_operation_target(HostIsa::X86_64),
    ) == Err(DirectNoOperationError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("wrong no-operation encryption was admitted"))
    }
}

fn assert_no_operation_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_NO_OPERATION_BACKEND_ID),
        backend_revision: 1,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_no_operation_coff(program, obsolete)
        == Err(DirectNoOperationError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete no-operation revision was admitted"))
    }
}

#[test]
fn direct_no_operation_rejects_ir_opcode_and_revision_tampering()
-> Result<(), String> {
    let program = direct_no_operation_program();
    let artifact = emit_direct_no_operation_coff(
        &program,
        direct_no_operation_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0x42u8, 0xc7, 0x04, 0x8a, 0x41, 0x00, 0x00, 0x00];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("no-operation commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(4))
        .ok_or_else(|| String::from("no-operation commit immediate missing"))?;
    *immediate = 66;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered no-operation structure: {error}"))?;
    if verify_direct_no_operation(&tampered, &program)
        != Err(DirectNoOperationError::ObjectBytes)
    {
        return Err(String::from("tampered no-operation object was admitted"));
    }
    assert_no_operation_shape_rejections(&program)?;
    assert_no_operation_revision_rejected(&program)
}

#[test]
fn direct_non_graphical_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!(
                "execution/fixtures/native-non-graphical-x86_64-coff.hex"
            ),
        ),
        (
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-non-graphical-aarch64-coff.hex"
            ),
        ),
    ];
    let program = direct_non_graphical_program();
    for (isa, fixture) in cases {
        let artifact = emit_direct_non_graphical_coff(
            &program,
            direct_non_graphical_target(isa),
        )
        .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!(
                "direct non-graphical fixture mismatch for {isa:?}"
            ));
        }
        let verified = verify_direct_non_graphical(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from(
                "verified non-graphical identity drifted",
            ));
        }
    }
    Ok(())
}

fn assert_non_graphical_shape_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut graphical = program.clone();
    let graphical_live_in = graphical
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("non-graphical fixture lost live-in"))?;
    graphical_live_in.value = 33;
    if emit_direct_non_graphical_coff(
        &graphical,
        direct_non_graphical_target(HostIsa::X86_64),
    ) != Err(DirectNonGraphicalError::ProgramShape)
    {
        return Err(String::from("graphical live-in was admitted"));
    }
    let mut wrong_address = program.clone();
    let address_live_in =
        wrong_address.memory_live_ins.first_mut().ok_or_else(|| {
            String::from("non-graphical fixture lost address live-in")
        })?;
    address_live_in.address = 6;
    if emit_direct_non_graphical_coff(
        &wrong_address,
        direct_non_graphical_target(HostIsa::X86_64),
    ) == Err(DirectNonGraphicalError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("wrong fetch live-in was admitted"))
    }
}

fn assert_non_graphical_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_NON_GRAPHICAL_BACKEND_ID),
        backend_revision: 1,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_non_graphical_coff(program, obsolete)
        == Err(DirectNonGraphicalError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete non-graphical revision was admitted"))
    }
}

#[test]
fn direct_non_graphical_rejects_ir_opcode_and_revision_tampering()
-> Result<(), String> {
    let program = direct_non_graphical_program();
    let artifact = emit_direct_non_graphical_coff(
        &program,
        direct_non_graphical_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0xc6u8, 0x41, 0x4c, 0x02];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("non-graphical commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(3))
        .ok_or_else(|| {
            String::from("non-graphical commit immediate missing")
        })?;
    *immediate = 1;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered).map_err(|error| {
        format!("tampered non-graphical structure: {error}")
    })?;
    if verify_direct_non_graphical(&tampered, &program)
        != Err(DirectNonGraphicalError::ObjectBytes)
    {
        return Err(String::from("tampered non-graphical object was admitted"));
    }
    assert_non_graphical_shape_rejections(&program)?;
    assert_non_graphical_revision_rejected(&program)
}

#[test]
fn direct_initial_halt_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!(
                "execution/fixtures/native-initial-halt-x86_64-coff.hex"
            ),
        ),
        (
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-initial-halt-aarch64-coff.hex"
            ),
        ),
    ];
    let program = direct_initial_halt_program();
    for (isa, fixture) in cases {
        let artifact = emit_direct_initial_halt_coff(
            &program,
            direct_initial_halt_target(isa),
        )
        .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!(
                "direct initial-halt fixture mismatch for {isa:?}"
            ));
        }
        let verified = verify_direct_initial_halt(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified initial-halt identity drifted"));
        }
    }
    Ok(())
}

#[test]
fn direct_initial_halt_rejects_ir_and_opcode_tampering() -> Result<(), String> {
    let program = direct_initial_halt_program();
    let artifact = emit_direct_initial_halt_coff(
        &program,
        direct_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;

    let mut mutated_object = artifact.object().to_vec();
    let commit = [0xc6u8, 0x41, 0x4c, 0x01];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("initial-halt commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(3))
        .ok_or_else(|| String::from("initial-halt commit immediate missing"))?;
    *immediate = 2;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered initial-halt structure: {error}"))?;
    if verify_direct_initial_halt(&tampered, &program)
        != Err(DirectInitialHaltError::ObjectBytes)
    {
        return Err(String::from("tampered initial-halt object was admitted"));
    }

    let mut with_live_in = program.clone();
    with_live_in
        .memory_live_ins
        .push(MemoryLiveIn { address: 7, value: 8 });
    if emit_direct_initial_halt_coff(
        &with_live_in,
        direct_initial_halt_target(HostIsa::X86_64),
    ) != Err(DirectInitialHaltError::ProgramShape)
    {
        return Err(String::from("initial-halt live-in mutation was admitted"));
    }

    let mut with_input = program;
    let first = with_input.effects.first_mut().ok_or_else(|| {
        String::from("initial-halt fixture lost first effect")
    })?;
    first.input = Some(TraceInput::EndOfInput);
    if emit_direct_initial_halt_coff(
        &with_input,
        direct_initial_halt_target(HostIsa::X86_64),
    ) != Err(DirectInitialHaltError::ProgramShape)
    {
        return Err(String::from("initial-halt input mutation was admitted"));
    }
    Ok(())
}

fn assert_jump_code_capacity_rejected() -> Result<(), String> {
    let mut jump_code = direct_jump_code_program();
    jump_code.profile_requirement.memory_words = 12;
    if emit_direct_jump_code_coff(
        &jump_code,
        direct_jump_code_target(HostIsa::X86_64),
    ) == Err(DirectJumpCodeError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from(
            "jump-code profile-capacity mismatch was admitted",
        ))
    }
}

fn assert_jump_data_capacity_rejected() -> Result<(), String> {
    let mut jump_data = direct_jump_data_program();
    jump_data.profile_requirement.memory_words = 124;
    if emit_direct_jump_data_coff(
        &jump_data,
        direct_jump_data_target(HostIsa::X86_64),
    ) == Err(DirectJumpDataError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from(
            "jump-data profile-capacity mismatch was admitted",
        ))
    }
}

fn assert_crazy_capacity_rejected() -> Result<(), String> {
    let mut crazy = direct_crazy_program();
    crazy.profile_requirement.memory_words = 7;
    if emit_direct_crazy_coff(&crazy, direct_crazy_target(HostIsa::X86_64))
        == Err(DirectCrazyError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("crazy profile-capacity mismatch was admitted"))
    }
}

fn assert_input_capacity_rejected() -> Result<(), String> {
    let mut input = direct_input_byte_program();
    input.profile_requirement.memory_words = 8;
    if emit_direct_input_coff(&input, direct_input_target(HostIsa::X86_64))
        == Err(DirectInputError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("input profile-capacity mismatch was admitted"))
    }
}

fn assert_output_capacity_rejected() -> Result<(), String> {
    let mut output = direct_output_program();
    output.profile_requirement.memory_words = 8;
    if emit_direct_output_coff(&output, direct_output_target(HostIsa::X86_64))
        == Err(DirectOutputError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from(
            "output profile-capacity mismatch was admitted",
        ))
    }
}

fn assert_rotate_capacity_rejected() -> Result<(), String> {
    let mut rotate = direct_rotate_program();
    rotate.profile_requirement.memory_words = 7;
    if emit_direct_rotate_coff(&rotate, direct_rotate_target(HostIsa::X86_64))
        == Err(DirectRotateError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from(
            "rotate profile-capacity mismatch was admitted",
        ))
    }
}

fn assert_initial_halt_capacity_rejected() -> Result<(), String> {
    let mut initial_halt = direct_initial_halt_program();
    initial_halt.profile_requirement.memory_words = 0;
    if emit_direct_initial_halt_coff(
        &initial_halt,
        direct_initial_halt_target(HostIsa::X86_64),
    ) == Err(DirectInitialHaltError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from(
            "initial-halt profile-capacity mismatch was admitted",
        ))
    }
}

#[test]
fn direct_fast_paths_reject_undersized_profile_capacity() -> Result<(), String>
{
    assert_jump_code_capacity_rejected()?;
    assert_crazy_capacity_rejected()?;
    assert_input_capacity_rejected()?;
    assert_output_capacity_rejected()?;
    assert_rotate_capacity_rejected()?;
    assert_jump_data_capacity_rejected()?;
    let mut register_halt = direct_halt_registers_program();
    register_halt.profile_requirement.memory_words = 1;
    if emit_direct_halt_registers_coff(
        &register_halt,
        direct_halt_registers_target(HostIsa::X86_64),
    ) != Err(DirectHaltRegistersError::ProgramShape)
    {
        return Err(String::from(
            "register-halt profile-capacity mismatch was admitted",
        ));
    }

    let mut halt_fetch = direct_halt_fetch_program();
    halt_fetch.profile_requirement.memory_words = 5;
    if emit_direct_halt_fetch_coff(
        &halt_fetch,
        direct_halt_fetch_target(HostIsa::X86_64),
    ) != Err(DirectHaltFetchError::ProgramShape)
    {
        return Err(String::from(
            "halt-fetch profile-capacity mismatch was admitted",
        ));
    }

    let mut no_operation = direct_no_operation_program();
    no_operation.profile_requirement.memory_words = 8;
    if emit_direct_no_operation_coff(
        &no_operation,
        direct_no_operation_target(HostIsa::X86_64),
    ) != Err(DirectNoOperationError::ProgramShape)
    {
        return Err(String::from(
            "no-operation profile-capacity mismatch was admitted",
        ));
    }

    let mut non_graphical = direct_non_graphical_program();
    non_graphical.profile_requirement.memory_words = 5;
    if emit_direct_non_graphical_coff(
        &non_graphical,
        direct_non_graphical_target(HostIsa::X86_64),
    ) != Err(DirectNonGraphicalError::ProgramShape)
    {
        return Err(String::from(
            "non-graphical profile-capacity mismatch was admitted",
        ));
    }

    assert_initial_halt_capacity_rejected()
}

#[test]
fn direct_deopt_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!("execution/fixtures/native-deopt-x86_64-coff.hex"),
        ),
        (
            HostIsa::AArch64,
            include_str!("execution/fixtures/native-deopt-aarch64-coff.hex"),
        ),
    ];
    for (isa, fixture) in cases {
        let artifact =
            emit_direct_deopt_coff(&native_program(), direct_deopt_target(isa))
                .map_err(|error| error.to_string())?;
        let expected = decode_hex_fixture(fixture)?;
        if artifact.object() != expected {
            return Err(format!("direct deopt fixture mismatch for {isa:?}"));
        }
        let verified = verify_direct_deopt_stub(&artifact)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified direct deopt identity drifted"));
        }
    }
    Ok(())
}

fn assert_direct_profile_metadata_mismatch(
    program: &RegionEffectProgram,
    artifact: &UntrustedNativeObjectArtifact,
) -> Result<(), String> {
    let mut renamed_program = program.clone();
    renamed_program.profile_id = String::from("malbolge-2026.3-alias");
    let renamed = emit_direct_deopt_coff(
        &renamed_program,
        direct_deopt_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mismatched = UntrustedNativeObjectArtifact::from_emitter_output(
        renamed.key().clone(),
        artifact.object().to_vec(),
        artifact.target_triple(),
    );
    if structurally_admit_coff(&mismatched)
        != Err(CoffAdmissionError::ProfileMetadata)
    {
        return Err(String::from("object/key profile mismatch was admitted"));
    }

    let mut geometry_program = program.clone();
    geometry_program.profile_requirement.word_trits = geometry_program
        .profile_requirement
        .word_trits
        .saturating_add(1);
    let geometry = emit_direct_deopt_coff(
        &geometry_program,
        direct_deopt_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let geometry_mismatch = UntrustedNativeObjectArtifact::from_emitter_output(
        geometry.key().clone(),
        artifact.object().to_vec(),
        artifact.target_triple(),
    );
    if structurally_admit_coff(&geometry_mismatch)
        != Err(CoffAdmissionError::ProfileMetadata)
    {
        return Err(String::from("object/key geometry mismatch was admitted"));
    }
    Ok(())
}

fn assert_direct_profile_footprint_mismatch(
    program: &RegionEffectProgram,
    artifact: &UntrustedNativeObjectArtifact,
) -> Result<(), String> {
    let mut footprint_program = program.clone();
    let footprint_live_in = footprint_program
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("profile fixture has no memory live-in"))?;
    footprint_live_in.address = footprint_live_in.address.saturating_add(1);
    let footprint = emit_direct_deopt_coff(
        &footprint_program,
        direct_deopt_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    if footprint.key().ir().required_memory_words()
        == artifact.key().ir().required_memory_words()
    {
        return Err(String::from("footprint mutation kept native identity"));
    }
    let mismatch = UntrustedNativeObjectArtifact::from_emitter_output(
        footprint.key().clone(),
        artifact.object().to_vec(),
        artifact.target_triple(),
    );
    if structurally_admit_coff(&mismatch)
        == Err(CoffAdmissionError::ProfileMetadata)
    {
        Ok(())
    } else {
        Err(String::from("object/key footprint mismatch was admitted"))
    }
}

fn assert_missing_direct_profile_metadata(
    artifact: &UntrustedNativeObjectArtifact,
) -> Result<(), String> {
    let mut missing = artifact.object().to_vec();
    let section_name = b".mbprof";
    let section_offset = missing
        .windows(section_name.len())
        .position(|window| window == section_name)
        .ok_or_else(|| String::from("direct object lacks profile section"))?;
    let section_marker = missing
        .get_mut(section_offset.saturating_add(1))
        .ok_or_else(|| String::from("profile section name offset invalid"))?;
    *section_marker = b'x';
    let missing_artifact = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        missing,
        artifact.target_triple(),
    );
    if structurally_admit_coff(&missing_artifact)
        != Err(CoffAdmissionError::ProfileMetadata)
    {
        return Err(String::from(
            "direct object without metadata was admitted",
        ));
    }
    Ok(())
}

fn assert_tampered_direct_profile_metadata(
    artifact: &UntrustedNativeObjectArtifact,
) -> Result<(), String> {
    let mut tampered = artifact.object().to_vec();
    let metadata_offset = tampered
        .windows(4)
        .position(|window| window == b"MBPF")
        .ok_or_else(|| String::from("direct object lacks profile metadata"))?;
    let metadata_version = tampered
        .get_mut(metadata_offset.saturating_add(4))
        .ok_or_else(|| {
            String::from("profile metadata version offset invalid")
        })?;
    *metadata_version ^= 1;
    let tampered_artifact = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        tampered,
        artifact.target_triple(),
    );
    if structurally_admit_coff(&tampered_artifact)
        != Err(CoffAdmissionError::ProfileMetadata)
    {
        return Err(String::from("tampered profile metadata was admitted"));
    }
    Ok(())
}

#[test]
fn direct_profile_metadata_rejects_missing_tampered_and_mismatched_identity()
-> Result<(), String> {
    let program = native_program();
    let artifact =
        emit_direct_deopt_coff(&program, direct_deopt_target(HostIsa::X86_64))
            .map_err(|error| error.to_string())?;
    assert_missing_direct_profile_metadata(&artifact)?;
    assert_tampered_direct_profile_metadata(&artifact)?;
    assert_direct_profile_metadata_mismatch(&program, &artifact)?;
    assert_direct_profile_footprint_mismatch(&program, &artifact)
}

#[test]
fn direct_deopt_semantic_admission_rejects_byte_and_target_tampering()
-> Result<(), String> {
    let artifact = emit_direct_deopt_coff(
        &native_program(),
        direct_deopt_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated = artifact.object().to_vec();
    let opcode = [0xb8u8, 0x01, 0x00, 0x00, 0x00, 0xc3];
    let offset = mutated
        .windows(opcode.len())
        .position(|window| window == opcode)
        .ok_or_else(|| {
            String::from("direct x86 deopt opcode fixture missing")
        })?;
    let first = mutated
        .get_mut(offset)
        .ok_or_else(|| String::from("direct deopt opcode offset invalid"))?;
    *first = 0x90;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated,
        artifact.target_triple(),
    );
    let _structurally_admitted =
        structurally_admit_coff(&tampered).map_err(|error| {
            format!("tampered structure unexpectedly rejected: {error}")
        })?;
    if verify_direct_deopt_stub(&tampered) != Err(DirectDeoptError::ObjectBytes)
    {
        return Err(String::from("tampered direct deopt opcode was admitted"));
    }

    let mut wrong_backend = base_target_config();
    wrong_backend.backend_id = String::from("not-direct-deopt");
    wrong_backend.backend_revision = DIRECT_DEOPT_BACKEND_REVISION;
    wrong_backend.native_abi_revision = NATIVE_REGION_ABI_REVISION;
    if emit_direct_deopt_coff(
        &native_program(),
        NativeTargetIdentity::new(wrong_backend),
    ) != Err(DirectDeoptError::TargetBackend)
    {
        return Err(String::from("wrong direct-deopt backend was admitted"));
    }
    Ok(())
}

#[test]
fn bootstrap_profile_metadata_requirement_starts_at_revision_two()
-> Result<(), String> {
    let program = native_program();
    let direct =
        emit_direct_deopt_coff(&program, direct_deopt_target(HostIsa::X86_64))
            .map_err(|error| error.to_string())?;
    let revision_two_key =
        NativeArtifactKey::new(&program, native_target(HostIsa::X86_64))
            .map_err(|error| format!("bootstrap v2 key: {error:?}"))?;
    let revision_two = UntrustedNativeObjectArtifact::from_emitter_output(
        revision_two_key,
        direct.object().to_vec(),
        direct.target_triple(),
    );
    let _admitted_revision_two = structurally_admit_coff(&revision_two)
        .map_err(|error| format!("bootstrap v2 metadata rejected: {error}"))?;

    let mut missing = direct.object().to_vec();
    let section = b".mbprof";
    let offset = missing
        .windows(section.len())
        .position(|window| window == section)
        .ok_or_else(|| {
            String::from("bootstrap fixture lacks metadata section")
        })?;
    let marker =
        missing.get_mut(offset.saturating_add(1)).ok_or_else(|| {
            String::from("bootstrap metadata name offset invalid")
        })?;
    *marker = b'x';
    let revision_two_missing =
        UntrustedNativeObjectArtifact::from_emitter_output(
            revision_two.key().clone(),
            missing.clone(),
            direct.target_triple(),
        );
    if structurally_admit_coff(&revision_two_missing)
        != Err(CoffAdmissionError::ProfileMetadata)
    {
        return Err(String::from("bootstrap v2 admitted missing metadata"));
    }

    let revision_one_target = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(CLANG_C23_BOOTSTRAP_BACKEND_ID),
        backend_revision: 1,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    let revision_one_key =
        NativeArtifactKey::new(&program, revision_one_target)
            .map_err(|error| format!("bootstrap v1 key: {error:?}"))?;
    let revision_one_missing =
        UntrustedNativeObjectArtifact::from_emitter_output(
            revision_one_key,
            missing,
            direct.target_triple(),
        );
    let _admitted_revision_one = structurally_admit_coff(&revision_one_missing)
        .map_err(|error| format!("historical bootstrap v1 changed: {error}"))?;
    Ok(())
}

fn assert_bootstrap_source_profile_metadata(
    program: &RegionEffectProgram,
    source: &str,
) -> Result<(), String> {
    if !source.contains("/* Profile ID: malbolge-2026.3 */") {
        return Err(String::from("native source lost profile identity"));
    }
    let fingerprint_comment =
        format!("/* Profile fingerprint: {} */", program.profile_fingerprint);
    if !source.contains(&fingerprint_comment) {
        return Err(String::from("native source lost profile fingerprint"));
    }
    if !source.contains(r#"#pragma section(".mbprof", read)"#)
        || !source.contains(r#"__declspec(allocate(".mbprof"))"#)
        || !source.contains("/* Backend: clang-c23-bootstrap rev 2 / ABI 1 */")
    {
        return Err(String::from(
            "native source lost bootstrap metadata policy",
        ));
    }
    if rendered_profile_metadata(source)? == expected_profile_metadata(program)?
    {
        Ok(())
    } else {
        Err(String::from("native source profile metadata drifted"))
    }
}

#[test]
fn native_bootstrap_source_is_deterministic_atomic_and_key_bound()
-> Result<(), String> {
    let program = native_program();
    let first = lower_clang_c23(&program, native_target(HostIsa::X86_64))
        .map_err(|error| error.to_string())?;
    let second = lower_clang_c23(&program, native_target(HostIsa::X86_64))
        .map_err(|error| error.to_string())?;
    if first != second {
        return Err(String::from(
            "native bootstrap source is not deterministic",
        ));
    }
    let expected_key =
        NativeArtifactKey::new(&program, native_target(HostIsa::X86_64))
            .map_err(|error| {
                format!("native expected key failed: {error:?}")
            })?;
    if first.key() != &expected_key {
        return Err(String::from("native source lost exact artifact key"));
    }
    let source = first.source();
    assert_bootstrap_source_profile_metadata(&program, source)?;
    let guard = source
        .find("state->memory_words <= MB_U64(7)")
        .ok_or_else(|| String::from("native memory preflight missing"))?;
    if !source.contains("return MB_NATIVE_INVALID_ARGUMENT")
        || !source.contains("return MB_NATIVE_GUARD_MISS")
    {
        return Err(String::from("native status split is missing"));
    }
    let commit = source
        .find("state->output[MB_U64(0)] = MB_U8(66);")
        .ok_or_else(|| String::from("native output commit missing"))?;
    let final_write = source
        .find("state->memory[MB_U64(7)] = MB_U32(10);")
        .ok_or_else(|| String::from("collapsed final memory write missing"))?;
    if guard >= commit || guard >= final_write {
        return Err(String::from("native commit precedes complete preflight"));
    }
    if source.contains("state->memory[MB_U64(7)] = MB_U32(9);") {
        return Err(String::from(
            "intermediate memory state leaked into commit",
        ));
    }
    Ok(())
}

#[test]
fn native_bootstrap_rejects_structural_and_target_mismatches()
-> Result<(), String> {
    let mut broken_chain = native_program();
    let second = broken_chain
        .effects
        .get_mut(1)
        .ok_or_else(|| String::from("native fixture has no second effect"))?;
    second.before.registers.accumulator = 99;
    if lower_clang_c23(&broken_chain, native_target(HostIsa::X86_64))
        != Err(NativeArtifactError::ObservationChain)
    {
        return Err(String::from(
            "broken native observation chain was admitted",
        ));
    }

    let mut post_termination = native_program();
    let first = post_termination
        .effects
        .first_mut()
        .ok_or_else(|| String::from("native fixture has no first effect"))?;
    first.after.termination = Some(Termination::HaltInstruction);
    let post_termination_second = post_termination
        .effects
        .get_mut(1)
        .ok_or_else(|| String::from("native fixture has no second effect"))?;
    post_termination_second.before.termination =
        Some(Termination::HaltInstruction);
    if lower_clang_c23(&post_termination, native_target(HostIsa::X86_64))
        != Err(NativeArtifactError::ObservationChain)
    {
        return Err(String::from(
            "native lowering admitted effects after termination",
        ));
    }

    let mut feature_target = NativeTargetConfig {
        backend_id: String::from(CLANG_C23_BOOTSTRAP_BACKEND_ID),
        backend_revision: CLANG_C23_BOOTSTRAP_BACKEND_REVISION,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: vec![String::from("avx2")],
    };
    if lower_clang_c23(
        &native_program(),
        NativeTargetIdentity::new(feature_target.clone()),
    ) != Err(NativeArtifactError::TargetFeatures)
    {
        return Err(String::from("bootstrap claimed unsupported CPU features"));
    }
    feature_target.backend_id = String::from("direct-x86");
    feature_target.required_features.clear();
    if lower_clang_c23(
        &native_program(),
        NativeTargetIdentity::new(feature_target),
    ) != Err(NativeArtifactError::TargetBackend)
    {
        return Err(String::from("wrong native backend identity was admitted"));
    }
    Ok(())
}

#[test]
fn native_bootstrap_rejects_observation_counter_overflow() -> Result<(), String>
{
    let target = native_target(HostIsa::X86_64);
    let mut input_overflow = native_program();
    for effect in &mut input_overflow.effects {
        effect.before.input_consumed = usize::MAX;
        effect.after.input_consumed = usize::MAX;
    }
    if lower_clang_c23(&input_overflow, target.clone())
        != Err(NativeArtifactError::InputTransition)
    {
        return Err(String::from(
            "bootstrap admitted overflowing input transition",
        ));
    }

    let mut output_overflow = native_program();
    for effect in &mut output_overflow.effects {
        effect.before.output_len = usize::MAX;
        effect.after.output_len = usize::MAX;
    }
    if lower_clang_c23(&output_overflow, target)
        == Err(NativeArtifactError::OutputTransition)
    {
        Ok(())
    } else {
        Err(String::from(
            "bootstrap admitted overflowing output transition",
        ))
    }
}

#[test]
fn native_bootstrap_compiler_emits_real_x86_64_and_aarch64_coff_objects()
-> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let clang = root.join(".dependencies/llvm/22.1.8/jig-bin/clang.bin");
    if !clang.is_file() {
        return Err(format!("pinned Clang missing: {}", clang.display()));
    }
    let program = native_program();
    let cases = [
        CoffCompileCase {
            expected_machine: [0x64u8, 0x86u8],
            isa: HostIsa::X86_64,
        },
        CoffCompileCase {
            expected_machine: [0x64u8, 0xaau8],
            isa: HostIsa::AArch64,
        },
    ];
    for case in cases {
        check_compiled_coff_case(&clang, &program, case)?;
    }
    Ok(())
}

fn check_compiled_coff_case(
    clang: &Path,
    program: &RegionEffectProgram,
    case: CoffCompileCase,
) -> Result<(), String> {
    let target = native_target(case.isa);
    let source = lower_preflighted_clang_c23(
        program,
        safe_rust_profiled_capability(),
        target.clone(),
    )
    .map_err(|error| error.to_string())?;
    let artifact = compile_preflighted_clang_c23(
        clang,
        program,
        safe_rust_profiled_capability(),
        target,
    )
    .map_err(|error| error.to_string())?;
    if artifact.key() != source.key()
        || artifact.target_triple() != source.target_triple()
    {
        return Err(String::from("native object lost source identity"));
    }
    if artifact.object().get(..2) != Some(case.expected_machine.as_slice()) {
        return Err(String::from("unexpected compiled COFF machine"));
    }
    let admitted = structurally_admit_coff(&artifact)
        .map_err(|error| format!("COFF structural admission: {error}"))?;
    if admitted.key() != artifact.key()
        || admitted.object() != artifact.object()
        || admitted.target_triple() != artifact.target_triple()
    {
        return Err(String::from("COFF admission changed artifact identity"));
    }
    if case.isa == HostIsa::X86_64 {
        check_rejected_coff_mutations(&source, &artifact)?;
    }
    Ok(())
}

fn check_rejected_coff_mutations(
    source: &execution_native::UntrustedNativeSourceArtifact,
    artifact: &UntrustedNativeObjectArtifact,
) -> Result<(), String> {
    let truncated = artifact.object().iter().copied().take(16).collect();
    let truncated_artifact =
        UntrustedNativeObjectArtifact::from_compiler_output(source, truncated)
            .map_err(|error| error.to_string())?;
    if structurally_admit_coff(&truncated_artifact)
        != Err(CoffAdmissionError::Bounds)
    {
        return Err(String::from("truncated COFF object was admitted"));
    }

    let mut wrong_machine = artifact.object().to_vec();
    let machine = wrong_machine
        .get_mut(..2)
        .ok_or_else(|| String::from("COFF fixture has no machine field"))?;
    machine.copy_from_slice(&0xaa64u16.to_le_bytes());
    let wrong_machine_artifact =
        UntrustedNativeObjectArtifact::from_compiler_output(
            source,
            wrong_machine,
        )
        .map_err(|error| error.to_string())?;
    if structurally_admit_coff(&wrong_machine_artifact)
        != Err(CoffAdmissionError::Machine)
    {
        return Err(String::from("wrong COFF machine was admitted"));
    }

    let mut wrong_entry = artifact.object().to_vec();
    let entry = b"malbolge_native_region_apply";
    let offset = wrong_entry
        .windows(entry.len())
        .position(|window| window == entry)
        .ok_or_else(|| String::from("COFF fixture has no native entry name"))?;
    let first = wrong_entry
        .get_mut(offset)
        .ok_or_else(|| String::from("COFF entry name offset is invalid"))?;
    *first = b'X';
    let wrong_entry_artifact =
        UntrustedNativeObjectArtifact::from_compiler_output(
            source,
            wrong_entry,
        )
        .map_err(|error| error.to_string())?;
    if structurally_admit_coff(&wrong_entry_artifact)
        != Err(CoffAdmissionError::ExtraExternalFunction)
    {
        return Err(String::from("renamed native entry was admitted"));
    }
    Ok(())
}

fn direct_normative_sequence_state() -> Result<ProfileMachineState, String> {
    let base =
        ProfileMachine::from_source(current_profile(), b"(=%r_L", Vec::new())
            .map_err(|error| format!("direct sequence base load: {error}"))?;
    let mut memory = base.snapshot_state().memory().to_vec();
    *memory
        .get_mut(5)
        .ok_or_else(|| String::from("direct sequence code cell 5 missing"))? =
        34;
    let output_cell = (33u32..=126u32)
        .find(|cell| decode_profile_instruction(*cell, 6) == Some(b'<'))
        .ok_or_else(|| String::from("phase-six output cell missing"))?;
    *memory
        .get_mut(6)
        .ok_or_else(|| String::from("direct sequence code cell 6 missing"))? =
        output_cell;
    *memory
        .get_mut(7)
        .ok_or_else(|| String::from("direct sequence data cell 7 missing"))? =
        10;
    let io = ProfileMachineIoState::new(Vec::new(), 0, Vec::new(), None)
        .map_err(|error| format!("direct sequence IO: {error}"))?;
    ProfileMachineState::new(
        current_profile(),
        memory,
        ProfileRegisters {
            accumulator: 20,
            code_pointer: 5,
            data_pointer: 7,
        },
        io,
    )
    .map_err(|error| format!("direct sequence state: {error}"))
}

fn direct_normative_sequence_traces() -> Result<Vec<ProfileStepTrace>, String> {
    let mut machine =
        ProfileMachine::from_snapshot(direct_normative_sequence_state()?);
    let mut traces = Vec::new();
    let outcome = machine
        .run_traced(2, &mut |trace: &ProfileStepTrace| traces.push(*trace))
        .map_err(|error| format!("direct sequence trace: {error}"))?;
    if outcome != (RunOutcome::BudgetExhausted { steps: 2 }) {
        return Err(format!("direct sequence outcome mismatch: {outcome:?}"));
    }
    Ok(traces)
}

fn direct_normative_sequence_fixture() -> Result<NativeSequenceFixture, String>
{
    let state = direct_normative_sequence_state()?;
    let initial_memory = state.memory().to_vec();
    let input = state.io().input().to_vec();

    let mut first_machine = ProfileMachine::from_snapshot(state.clone());
    let first_outcome = first_machine
        .run_traced(1, &mut |_trace: &ProfileStepTrace| {})
        .map_err(|error| format!("direct sequence first step: {error}"))?;
    if first_outcome != (RunOutcome::BudgetExhausted { steps: 1 }) {
        return Err(format!(
            "direct sequence first outcome mismatch: {first_outcome:?}"
        ));
    }

    let mut final_machine = ProfileMachine::from_snapshot(state);
    let mut traces = Vec::new();
    let final_outcome = final_machine
        .run_traced(2, &mut |trace: &ProfileStepTrace| traces.push(*trace))
        .map_err(|error| format!("direct sequence final steps: {error}"))?;
    if final_outcome != (RunOutcome::BudgetExhausted { steps: 2 }) {
        return Err(format!(
            "direct sequence final outcome mismatch: {final_outcome:?}"
        ));
    }
    let programs = traces
        .iter()
        .map(|trace| {
            RegionEffectProgram::from_profile_step_trace(trace).map_err(
                |error| format!("direct sequence projection: {error:?}"),
            )
        })
        .collect::<Result<Vec<_>, _>>()?;
    let output_capacity = final_machine.output().len().max(1);
    let initial_output = vec![0u8; output_capacity];
    let mut first_output = initial_output.clone();
    first_output
        .get_mut(..first_machine.output().len())
        .ok_or_else(|| String::from("first sequence output exceeds capacity"))?
        .copy_from_slice(first_machine.output());
    let mut final_output = initial_output.clone();
    final_output
        .get_mut(..final_machine.output().len())
        .ok_or_else(|| String::from("final sequence output exceeds capacity"))?
        .copy_from_slice(final_machine.output());
    Ok(NativeSequenceFixture {
        final_memory: final_machine.memory().to_vec(),
        final_output,
        first_memory: first_machine.memory().to_vec(),
        first_output,
        initial_memory,
        initial_output,
        input,
        programs,
    })
}

fn direct_normative_sequence_programs()
-> Result<Vec<RegionEffectProgram>, String> {
    direct_normative_sequence_traces()?
        .iter()
        .map(|trace| {
            RegionEffectProgram::from_profile_step_trace(trace).map_err(
                |error| format!("direct sequence projection: {error:?}"),
            )
        })
        .collect()
}

#[test]
fn normative_trace_sequence_selects_mixed_exact_direct_steps()
-> Result<(), String> {
    let traces = direct_normative_sequence_traces()?;
    let programs = direct_normative_sequence_programs()?;
    let [first_program, second_program] = programs.as_slice() else {
        return Err(String::from("direct sequence program length mismatch"));
    };
    let [first_trace, second_trace] = traces.as_slice() else {
        return Err(String::from("direct sequence trace length mismatch"));
    };
    let second_fetch = second_trace
        .memory_reads
        .fetch
        .ok_or_else(|| String::from("direct sequence second fetch missing"))?;
    if first_program.memory_live_ins
        != [MemoryLiveIn { address: 5, value: 34 }, MemoryLiveIn {
            address: 7,
            value: 10,
        }]
        || second_program.memory_live_ins
            != [MemoryLiveIn {
                address: second_fetch.address,
                value: second_fetch.value,
            }]
        || first_trace.decoded != Some(b'*')
        || second_trace.decoded != Some(b'<')
        || second_trace.output != Some(0xd6)
    {
        let detail = format!("traces={traces:?} programs={programs:?}");
        return Err(format!("direct sequence VM evidence mismatch: {detail}"));
    }
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        let plan = select_verified_direct_sequence(
            &programs,
            safe_rust_profiled_capability(),
            HostOperatingSystem::Windows,
            isa,
        )
        .map_err(|error| format!("direct sequence select: {error}"))?;
        let [rotate, output] = plan.artifacts() else {
            return Err(format!("direct sequence plan length: {plan:?}"));
        };
        if plan.len() != 2
            || plan.entry() != first_trace.before
            || plan.exit() != second_trace.after
            || plan.outcome() != (RunOutcome::BudgetExhausted { steps: 2 })
            || rotate.kind() != DirectNativeKind::Rotate
            || output.kind() != DirectNativeKind::Output
        {
            return Err(format!("direct sequence plan mismatch: {plan:?}"));
        }
    }
    Ok(())
}

#[test]
fn cached_direct_sequence_inserts_then_reuses_exact_arcs() -> Result<(), String>
{
    let programs = direct_normative_sequence_programs()?;
    let host = DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64);
    let mut cache = VerifiedDirectNativeCache::default();
    let inserted = select_cached_verified_direct_sequence(
        &programs,
        safe_rust_profiled_capability(),
        host,
        &mut cache,
    )
    .map_err(|error| error.to_string())?;
    let [inserted_rotate, inserted_output] = inserted.artifacts() else {
        return Err(format!("inserted sequence length: {inserted:?}"));
    };
    if inserted.cache_hits() != 0
        || inserted.cache_insertions() != 2
        || inserted.len() != 2
        || inserted.is_empty()
        || inserted_rotate.kind() != DirectNativeKind::Rotate
        || inserted_output.kind() != DirectNativeKind::Output
        || cache.len() != 2
    {
        return Err(format!("inserted sequence mismatch: {inserted:?}"));
    }

    let hit = select_cached_verified_direct_sequence(
        &programs,
        safe_rust_profiled_capability(),
        host,
        &mut cache,
    )
    .map_err(|error| error.to_string())?;
    let [hit_rotate, hit_output] = hit.artifacts() else {
        return Err(format!("hit sequence length: {hit:?}"));
    };
    if hit.cache_hits() != 2
        || hit.cache_insertions() != 0
        || cache.len() != 2
        || !Arc::ptr_eq(inserted_rotate, hit_rotate)
        || !Arc::ptr_eq(inserted_output, hit_output)
        || hit.entry() != inserted.entry()
        || hit.exit() != inserted.exit()
        || hit.outcome() != inserted.outcome()
    {
        Err(String::from("cached sequence lost exact Arc reuse"))
    } else {
        Ok(())
    }
}

#[test]
fn cached_direct_sequence_combines_hit_and_verified_miss() -> Result<(), String>
{
    let programs = direct_normative_sequence_programs()?;
    let first = programs
        .first()
        .ok_or_else(|| String::from("first sequence program missing"))?;
    let host = DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64);
    let mut cache = VerifiedDirectNativeCache::default();
    let seeded = select_cached_preflighted_execution_tier(
        first,
        safe_rust_profiled_capability(),
        host,
        &mut cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact: seeded_rotate,
        cache: DirectCacheDisposition::Inserted,
    } = seeded
    else {
        return Err(String::from("failed to seed sequence cache"));
    };

    let plan = select_cached_verified_direct_sequence(
        &programs,
        safe_rust_profiled_capability(),
        host,
        &mut cache,
    )
    .map_err(|error| error.to_string())?;
    let [rotate, output] = plan.artifacts() else {
        return Err(format!("mixed sequence length: {plan:?}"));
    };
    if plan.cache_hits() == 1
        && plan.cache_insertions() == 1
        && cache.len() == 2
        && Arc::ptr_eq(&seeded_rotate, rotate)
        && output.kind() == DirectNativeKind::Output
    {
        Ok(())
    } else {
        Err(String::from("mixed sequence cache transaction drifted"))
    }
}

#[test]
fn cached_direct_sequence_preflights_before_lookup() -> Result<(), String> {
    let programs = direct_normative_sequence_programs()?;
    let host = DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64);
    let mut cache = VerifiedDirectNativeCache::default();
    let inserted = select_cached_verified_direct_sequence(
        &programs,
        safe_rust_profiled_capability(),
        host,
        &mut cache,
    )
    .map_err(|error| error.to_string())?;
    let snapshot = cache.clone();

    let rejected = select_cached_verified_direct_sequence(
        &programs,
        safe_rust_classic_capability(),
        host,
        &mut cache,
    );
    let Err(DirectSequenceError::Step { error, index: 0 }) = rejected else {
        return Err(format!("cached sequence preflight changed: {rejected:?}"));
    };
    let DirectSelectionError::Profile(profile) = *error else {
        return Err(String::from("cached sequence preflight category changed"));
    };
    if profile.kind() != ProfileRequirementErrorKind::RuntimeCapabilityMissing
        || cache != snapshot
    {
        return Err(String::from("cached sequence lookup bypassed preflight"));
    }

    let retained = select_cached_verified_direct_sequence(
        &programs,
        safe_rust_profiled_capability(),
        host,
        &mut cache,
    )
    .map_err(|selection_error| selection_error.to_string())?;
    if inserted
        .artifacts()
        .iter()
        .zip(retained.artifacts())
        .all(|(left, right)| Arc::ptr_eq(left, right))
        && retained.cache_hits() == 2
        && cache == snapshot
    {
        Ok(())
    } else {
        Err(String::from(
            "cached sequence preflight changed retained hits",
        ))
    }
}

#[test]
fn cached_direct_sequence_rolls_back_late_rejection() -> Result<(), String> {
    let seed_program = direct_initial_halt_program();
    let host = DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64);
    let mut cache = VerifiedDirectNativeCache::default();
    let seeded = select_cached_preflighted_execution_tier(
        &seed_program,
        safe_rust_profiled_capability(),
        host,
        &mut cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact: seeded_artifact,
        cache: DirectCacheDisposition::Inserted,
    } = seeded
    else {
        return Err(String::from("failed to seed rollback cache"));
    };

    let mut programs = direct_normative_sequence_programs()?;
    programs
        .get_mut(1)
        .ok_or_else(|| String::from("second rollback program missing"))?
        .memory_live_ins
        .clear();
    let snapshot = cache.clone();
    let result = select_cached_verified_direct_sequence(
        &programs,
        safe_rust_profiled_capability(),
        host,
        &mut cache,
    );
    if result != Err(DirectSequenceError::Deoptimization { index: 1 })
        || cache != snapshot
        || cache.len() != 1
    {
        return Err(format!("failed sequence mutated cache: {result:?}"));
    }

    let retained = select_cached_preflighted_execution_tier(
        &seed_program,
        safe_rust_profiled_capability(),
        host,
        &mut cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact: retained_artifact,
        cache: DirectCacheDisposition::Hit,
    } = retained
    else {
        return Err(String::from("rollback cache lost seeded hit"));
    };
    if Arc::ptr_eq(&seeded_artifact, &retained_artifact) && cache.len() == 1 {
        Ok(())
    } else {
        Err(String::from("rollback changed retained cache identity"))
    }
}

#[test]
fn trace_projection_rejects_conflicting_same_address_reads()
-> Result<(), String> {
    let mut trace = direct_normative_sequence_traces()?
        .first()
        .copied()
        .ok_or_else(|| String::from("direct sequence trace missing"))?;
    trace.memory_reads.encryption =
        Some(ProfileMemoryRead { address: 5, value: 35 });
    let result = RegionEffectProgram::from_profile_step_trace(&trace);
    if result != Err(StepProgramProjectionError::ConflictingMemoryRead) {
        return Err(format!("conflicting trace read admitted: {result:?}"));
    }
    Ok(())
}

fn assert_projection_error(
    trace: &ProfileStepTrace,
    expected: StepProgramProjectionError,
) -> Result<(), String> {
    let observed = RegionEffectProgram::from_profile_step_trace(trace);
    if observed == Err(expected) {
        Ok(())
    } else {
        let detail = format!("observed={observed:?} expected={expected:?}");
        Err(format!("trace projection error mismatch: {detail}"))
    }
}

#[test]
fn trace_projection_rejects_inconsistent_evidence() -> Result<(), String> {
    let baseline = direct_normative_sequence_traces()?
        .first()
        .copied()
        .ok_or_else(|| String::from("direct sequence trace missing"))?;

    let mut missing_fetch = baseline;
    missing_fetch.memory_reads.fetch = None;
    assert_projection_error(
        &missing_fetch,
        StepProgramProjectionError::MissingFetch,
    )?;

    let mut wrong_address = baseline;
    let fetch = wrong_address
        .memory_reads
        .fetch
        .as_mut()
        .ok_or_else(|| String::from("direct sequence fetch missing"))?;
    fetch.address = fetch.address.saturating_add(1);
    assert_projection_error(
        &wrong_address,
        StepProgramProjectionError::FetchAddress,
    )?;

    let mut wrong_value = baseline;
    wrong_value.fetched_cell = wrong_value.fetched_cell.map(|value| value ^ 1);
    assert_projection_error(
        &wrong_value,
        StepProgramProjectionError::FetchValue,
    )?;

    let mut outcome = baseline;
    outcome.after.termination = Some(Termination::HaltInstruction);
    assert_projection_error(&outcome, StepProgramProjectionError::Outcome)?;

    let mut rejected = baseline;
    rejected.result = Err(ProfileMachineError::TranslationTableInvariant);
    assert_projection_error(
        &rejected,
        StepProgramProjectionError::RejectedTrace,
    )?;

    let mut terminated = baseline;
    terminated.before.termination = Some(Termination::HaltInstruction);
    assert_projection_error(
        &terminated,
        StepProgramProjectionError::TerminatedEntry,
    )
}

#[test]
fn direct_sequence_rejects_non_unit_programs() -> Result<(), String> {
    let mut programs = direct_normative_sequence_programs()?;
    programs
        .get_mut(0)
        .ok_or_else(|| String::from("first shape program missing"))?
        .step_budget = 2;
    let result = select_verified_direct_sequence(
        &programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    );
    if result == Err(DirectSequenceError::ProgramShape { index: 0 }) {
        Ok(())
    } else {
        Err(format!("non-unit direct sequence admitted: {result:?}"))
    }
}

#[test]
fn direct_sequence_rejects_empty_discontinuous_and_profile_mixed_shapes()
-> Result<(), String> {
    let empty = select_verified_direct_sequence(
        &[],
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    );
    if empty != Err(DirectSequenceError::Empty) {
        return Err(format!("empty direct sequence admitted: {empty:?}"));
    }

    let mut discontinuous = direct_normative_sequence_programs()?;
    let second = discontinuous.get_mut(1).ok_or_else(|| {
        String::from("second direct sequence program missing")
    })?;
    let effect = second
        .effects
        .first_mut()
        .ok_or_else(|| String::from("second direct sequence effect missing"))?;
    effect.before.registers.accumulator ^= 1;
    let chain_result = select_verified_direct_sequence(
        &discontinuous,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    );
    if chain_result != Err(DirectSequenceError::ObservationChain { index: 1 }) {
        return Err(format!(
            "discontinuous direct sequence admitted: {chain_result:?}"
        ));
    }

    let mut profile_mixed = direct_normative_sequence_programs()?;
    profile_mixed
        .get_mut(1)
        .ok_or_else(|| String::from("second profile program missing"))?
        .profile_id
        .push_str("-other");
    let profile_result = select_verified_direct_sequence(
        &profile_mixed,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    );
    if profile_result != Err(DirectSequenceError::ProfileMismatch { index: 1 })
    {
        return Err(format!(
            "profile-mixed direct sequence admitted: {profile_result:?}"
        ));
    }
    Ok(())
}

#[test]
fn direct_sequence_preserves_step_selection_errors() -> Result<(), String> {
    let programs = direct_normative_sequence_programs()?;
    let result = select_verified_direct_sequence(
        &programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Linux,
        HostIsa::X86_64,
    );
    let Err(DirectSequenceError::Step { error, index: 0 }) = result else {
        return Err(format!("direct sequence step error changed: {result:?}"));
    };
    if *error == DirectSelectionError::TargetFormat {
        Ok(())
    } else {
        Err(format!("direct sequence target error changed: {error}"))
    }
}

#[test]
fn direct_sequence_rejects_hidden_deopt_and_post_termination_steps()
-> Result<(), String> {
    let mut hidden_deopt = direct_normative_sequence_programs()?;
    hidden_deopt
        .get_mut(1)
        .ok_or_else(|| String::from("second deopt program missing"))?
        .memory_live_ins
        .clear();
    let deopt_result = select_verified_direct_sequence(
        &hidden_deopt,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    );
    if deopt_result != Err(DirectSequenceError::Deoptimization { index: 1 }) {
        return Err(format!(
            "hidden deopt direct sequence admitted: {deopt_result:?}"
        ));
    }

    let terminal = [direct_halt_fetch_program(), direct_no_operation_program()];
    let terminal_result = select_verified_direct_sequence(
        &terminal,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    );
    if terminal_result
        != Err(DirectSequenceError::TerminationBeforeEnd { index: 0 })
    {
        return Err(format!(
            "post-termination direct step admitted: {terminal_result:?}"
        ));
    }
    Ok(())
}

#[test]
fn native_region_abi_layout_matches_reviewed_64_bit_templates()
-> Result<(), String> {
    let observed = [
        NATIVE_REGION_STATE_SIZE,
        NATIVE_REGION_MEMORY_OFFSET,
        NATIVE_REGION_MEMORY_WORDS_OFFSET,
        NATIVE_REGION_INPUT_OFFSET,
        NATIVE_REGION_INPUT_LEN_OFFSET,
        NATIVE_REGION_INPUT_CONSUMED_OFFSET,
        NATIVE_REGION_OUTPUT_OFFSET,
        NATIVE_REGION_OUTPUT_CAPACITY_OFFSET,
        NATIVE_REGION_OUTPUT_LEN_OFFSET,
        NATIVE_REGION_ACCUMULATOR_OFFSET,
        NATIVE_REGION_CODE_POINTER_OFFSET,
        NATIVE_REGION_DATA_POINTER_OFFSET,
        NATIVE_REGION_TERMINATION_OFFSET,
    ];
    let expected = [80, 0, 8, 16, 24, 32, 40, 48, 56, 64, 68, 72, 76];
    if observed == expected {
        Ok(())
    } else {
        Err(format!("native region ABI layout changed: {observed:?}"))
    }
}

#[test]
fn native_region_status_and_termination_values_fail_closed()
-> Result<(), String> {
    for (code, expected) in [
        (0i32, NativeRegionStatus::Applied),
        (1i32, NativeRegionStatus::GuardMiss),
        (2i32, NativeRegionStatus::InvalidArgument),
    ] {
        let observed = NativeRegionStatus::try_from(code)
            .map_err(|error| error.to_string())?;
        if observed != expected || observed.code() != code {
            return Err(format!("native status roundtrip changed: {code}"));
        }
    }
    let Err(status_error) = NativeRegionStatus::try_from(3i32) else {
        return Err(String::from("unknown native status was admitted"));
    };
    if status_error.code() != 3i32 {
        return Err(String::from("native status error lost foreign value"));
    }

    for (termination, expected) in [
        (None, NativeTerminationTag::Running),
        (
            Some(Termination::HaltInstruction),
            NativeTerminationTag::HaltInstruction,
        ),
        (
            Some(Termination::NonGraphicalCell),
            NativeTerminationTag::NonGraphicalCell,
        ),
    ] {
        let tag = NativeTerminationTag::from_termination(termination);
        let decoded = NativeTerminationTag::try_from(tag.code())
            .map_err(|error| error.to_string())?;
        if tag != expected || decoded.termination() != termination {
            return Err(String::from("native termination roundtrip changed"));
        }
    }
    let Err(tag_error) = NativeTerminationTag::try_from(3u8) else {
        return Err(String::from("unknown termination tag was admitted"));
    };
    if tag_error.value() == 3u8 {
        Ok(())
    } else {
        Err(String::from("termination error lost foreign value"))
    }
}

#[test]
fn native_region_call_frame_binds_exact_state() -> Result<(), String> {
    let mut memory = [34u32, 10, 112];
    let input = [0x10u8, 0x41, 0x20];
    let mut output = [0xa0u8, 0xa1, 0, 0];
    let observation = ProfileMachineObservation {
        input_consumed: 1,
        output_len: 2,
        registers: ProfileRegisters {
            accumulator: 20,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let mut frame = NativeRegionCallFrame::new(
        &mut memory,
        &input,
        &mut output,
        observation,
    )
    .map_err(|error| error.to_string())?;
    let state = frame.state();
    if state.memory_words() != 3
        || state.input_len() != 3
        || state.input_consumed() != 1
        || state.output_capacity() != 4
        || state.output_len() != 2
        || state.accumulator() != 20
        || state.code_pointer() != 5
        || state.data_pointer() != 7
        || state.termination_tag() != 0
        || state.observation().map_err(|error| error.to_string())?
            != observation
        || frame.memory() != [34, 10, 112]
        || frame.input() != input
        || frame.output_prefix().map_err(|error| error.to_string())?
            != [0xa0, 0xa1]
        || frame.state_mut_ptr().is_null()
    {
        Err(String::from("native call frame changed ABI state"))
    } else {
        Ok(())
    }
}

#[test]
fn native_region_call_frame_rejects_out_of_bounds_counters()
-> Result<(), String> {
    let mut memory = [0u32; 1];
    let input = [0u8; 1];
    let mut output = [0u8; 1];
    let mut observation = ProfileMachineObservation {
        input_consumed: 2,
        output_len: 0,
        registers: ProfileRegisters {
            accumulator: 0,
            code_pointer: 0,
            data_pointer: 0,
        },
        termination: None,
    };
    let input_result = NativeRegionCallFrame::new(
        &mut memory,
        &input,
        &mut output,
        observation,
    );
    if !matches!(input_result, Err(NativeRegionCallFrameError::InputConsumed)) {
        return Err(String::from("invalid native input cursor admitted"));
    }
    observation.input_consumed = 0;
    observation.output_len = 2;
    let output_result = NativeRegionCallFrame::new(
        &mut memory,
        &input,
        &mut output,
        observation,
    );
    if matches!(output_result, Err(NativeRegionCallFrameError::OutputLength)) {
        Ok(())
    } else {
        Err(String::from("invalid native output length admitted"))
    }
}

fn native_invocation_output_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0,
        output_len: 1,
        registers: ProfileRegisters {
            accumulator: 0x0000_00a8,
            code_pointer: 0,
            data_pointer: 1,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        output_len: 2,
        registers: ProfileRegisters {
            code_pointer: 1,
            data_pointer: 2,
            ..before.registers
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta {
                data: None,
                encryption: Some(ProfileMemoryWrite {
                    address: 0,
                    after: 66,
                    before: 65,
                }),
            },
            output: Some(0xa8),
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 0, value: 65 }],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:native-invocation-output",
        ),
        profile_id: String::from("malbolge-2026.3"),
        profile_requirement: fixture_profile_requirement(),
        step_budget: 1,
    }
}

#[test]
fn native_region_invocation_admits_atomic_guard_miss() -> Result<(), String> {
    let program = native_invocation_output_program();
    let mut memory = [65u32, 10, 20];
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let invocation = PreparedNativeRegionInvocation::new(
        &program,
        &mut memory,
        &input,
        &mut output,
    )
    .map_err(|error| error.to_string())?;
    let outcome = invocation
        .complete(NativeRegionStatus::GuardMiss.code())
        .map_err(|error| error.to_string())?;
    if outcome == NativeRegionInvocationOutcome::GuardMiss
        && memory == [65, 10, 20]
        && output == [0x10, 0, 0]
    {
        Ok(())
    } else {
        Err(String::from("atomic native guard miss changed state"))
    }
}

#[test]
fn native_region_invocation_accepts_v4_with_u32_geometry() -> Result<(), String>
{
    let mut program = native_invocation_output_program();
    program.format_version = EFFECT_IR_WIDE_PROFILE_VERSION;
    let expected = program
        .effects
        .first()
        .ok_or_else(|| String::from("v4 invocation fixture has no effect"))?
        .after;
    let mut memory = [65u32, 10, 20];
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let mut invocation = PreparedNativeRegionInvocation::new(
        &program,
        &mut memory,
        &input,
        &mut output,
    )
    .map_err(|error| format!("v4 invocation rejected u32 geometry: {error}"))?;
    invocation.apply_expected_for_test();
    let outcome = invocation
        .complete(NativeRegionStatus::Applied.code())
        .map_err(|error| format!("v4 invocation completion failed: {error}"))?;
    if outcome == NativeRegionInvocationOutcome::Applied(expected)
        && memory == [66, 10, 20]
        && output == [0x10, 0xa8, 0]
    {
        Ok(())
    } else {
        Err(String::from("v4 invocation did not apply exact effect"))
    }
}

#[test]
fn native_region_invocation_rejects_v4_beyond_u32_geometry()
-> Result<(), String> {
    let mut program = native_invocation_output_program();
    program.format_version = EFFECT_IR_WIDE_PROFILE_VERSION;
    program.profile_requirement.word_trits = 21;
    program.profile_requirement.memory_words = 10_460_353_203;
    let mut memory = [65u32, 10, 20];
    let input = [];
    let mut output = [0x10u8, 0, 0];
    if matches!(
        PreparedNativeRegionInvocation::new(
            &program,
            &mut memory,
            &input,
            &mut output,
        ),
        Err(NativeRegionInvocationError::ProgramShape)
    ) {
        Ok(())
    } else {
        Err(String::from("N21 v4 reached the u32 invocation ABI"))
    }
}

#[test]
fn native_region_invocation_admits_exact_applied_effect() -> Result<(), String>
{
    let program = native_invocation_output_program();
    let expected = program
        .effects
        .first()
        .ok_or_else(|| String::from("native fixture has no effect"))?
        .after;
    let mut memory = [65u32, 10, 20];
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let mut invocation = PreparedNativeRegionInvocation::new(
        &program,
        &mut memory,
        &input,
        &mut output,
    )
    .map_err(|error| error.to_string())?;
    if invocation.expected_observation() != expected
        || invocation.memory() != [65, 10, 20]
        || invocation.input() != input
        || invocation.output() != [0x10, 0, 0]
    {
        return Err(String::from("prepared native invocation changed entry"));
    }
    invocation.apply_expected_for_test();
    let outcome = invocation
        .complete(NativeRegionStatus::Applied.code())
        .map_err(|error| error.to_string())?;
    if outcome == NativeRegionInvocationOutcome::Applied(expected)
        && memory == [66, 10, 20]
        && output == [0x10, 0xa8, 0]
    {
        Ok(())
    } else {
        Err(String::from("exact native application was not admitted"))
    }
}

#[test]
fn native_region_invocation_rejects_and_rolls_back_applied_drift()
-> Result<(), String> {
    let program = native_invocation_output_program();
    let mut memory = [65u32, 10, 20];
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let mut invocation = PreparedNativeRegionInvocation::new(
        &program,
        &mut memory,
        &input,
        &mut output,
    )
    .map_err(|error| error.to_string())?;
    invocation.apply_expected_for_test();
    if !invocation.write_memory_for_test(0, 99) {
        return Err(String::from("native mutation fixture address is absent"));
    }
    let result = invocation.complete(NativeRegionStatus::Applied.code());
    if matches!(
        result,
        Err(NativeRegionInvocationError::AppliedMemory {
            address: 0,
            expected: 66,
            observed: 99,
        })
    ) && memory == [65, 10, 20]
        && output == [0x10, 0, 0]
    {
        Ok(())
    } else {
        Err(String::from("applied native drift was not rolled back"))
    }
}

#[test]
fn native_region_invocation_rejects_incomplete_applied_state()
-> Result<(), String> {
    let program = native_invocation_output_program();
    let mut memory = [65u32, 10, 20];
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let invocation = PreparedNativeRegionInvocation::new(
        &program,
        &mut memory,
        &input,
        &mut output,
    )
    .map_err(|error| error.to_string())?;
    if matches!(
        invocation.complete(NativeRegionStatus::Applied.code()),
        Err(NativeRegionInvocationError::AppliedObservation)
    ) {
        Ok(())
    } else {
        Err(String::from("incomplete native application was admitted"))
    }
}

#[test]
fn native_region_invocation_rejects_invalid_argument_status()
-> Result<(), String> {
    let program = native_invocation_output_program();
    let mut memory = [65u32, 10, 20];
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let invocation = PreparedNativeRegionInvocation::new(
        &program,
        &mut memory,
        &input,
        &mut output,
    )
    .map_err(|error| error.to_string())?;
    if matches!(
        invocation.complete(NativeRegionStatus::InvalidArgument.code()),
        Err(NativeRegionInvocationError::InvalidArgument)
    ) {
        Ok(())
    } else {
        Err(String::from("invalid-argument status was admitted"))
    }
}

#[test]
fn native_region_invocation_rejects_non_applied_mutation() -> Result<(), String>
{
    let program = native_invocation_output_program();
    let mut memory = [65u32, 10, 20];
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let mut invocation = PreparedNativeRegionInvocation::new(
        &program,
        &mut memory,
        &input,
        &mut output,
    )
    .map_err(|error| error.to_string())?;
    if !invocation.write_memory_for_test(0, 99) {
        return Err(String::from("native mutation fixture address is absent"));
    }
    let result = invocation.complete(NativeRegionStatus::GuardMiss.code());
    if matches!(
        result,
        Err(NativeRegionInvocationError::NonAppliedMutation {
            status: NativeRegionStatus::GuardMiss,
            surface: NativeRegionMutationSurface::Memory,
        })
    ) && memory == [65, 10, 20]
        && output == [0x10, 0, 0]
    {
        Ok(())
    } else {
        Err(String::from(
            "native guard-miss mutation was not rolled back",
        ))
    }
}

#[test]
fn native_region_invocation_rejects_unknown_status() -> Result<(), String> {
    let program = native_invocation_output_program();
    let mut memory = [65u32, 10, 20];
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let mut invocation = PreparedNativeRegionInvocation::new(
        &program,
        &mut memory,
        &input,
        &mut output,
    )
    .map_err(|error| error.to_string())?;
    if !invocation.write_memory_for_test(0, 99) {
        return Err(String::from("native mutation fixture address is absent"));
    }
    if matches!(
        invocation.complete(9),
        Err(NativeRegionInvocationError::Status(error)) if error.code() == 9
    ) && memory == [65, 10, 20]
        && output == [0x10, 0, 0]
    {
        Ok(())
    } else {
        Err(String::from("unknown native status was not rolled back"))
    }
}

#[test]
fn native_region_invocation_rejects_invalid_live_in() -> Result<(), String> {
    let program = native_invocation_output_program();
    let mut memory = [64u32, 10, 20];
    let input = [];
    let mut output = [0x10u8, 0, 0];
    if matches!(
        PreparedNativeRegionInvocation::new(
            &program,
            &mut memory,
            &input,
            &mut output,
        ),
        Err(NativeRegionInvocationError::EntryMemory {
            address: 0,
            expected: 65,
            observed: 64,
        })
    ) {
        Ok(())
    } else {
        Err(String::from("invalid native live-in was admitted"))
    }
}

#[test]
fn native_region_invocation_rejects_invalid_output_transition()
-> Result<(), String> {
    let mut program = native_invocation_output_program();
    let effect = program
        .effects
        .first_mut()
        .ok_or_else(|| String::from("native fixture has no effect"))?;
    effect.after.output_len = 3;
    let mut memory = [65u32, 10, 20];
    let input = [];
    let mut output = [0x10u8, 0, 0];
    if matches!(
        PreparedNativeRegionInvocation::new(
            &program,
            &mut memory,
            &input,
            &mut output,
        ),
        Err(NativeRegionInvocationError::OutputTransition)
    ) {
        Ok(())
    } else {
        Err(String::from(
            "invalid native output transition was admitted",
        ))
    }
}

#[test]
fn native_region_invocation_rejects_non_unit_program() -> Result<(), String> {
    let mut program = native_invocation_output_program();
    program.step_budget = 2;
    let mut memory = [65u32, 10, 20];
    let input = [];
    let mut output = [0x10u8, 0, 0];
    if matches!(
        PreparedNativeRegionInvocation::new(
            &program,
            &mut memory,
            &input,
            &mut output,
        ),
        Err(NativeRegionInvocationError::ProgramShape)
    ) {
        Ok(())
    } else {
        Err(String::from("non-unit native program was admitted"))
    }
}

#[test]
fn native_region_invocation_rejects_short_memory() -> Result<(), String> {
    let program = native_invocation_output_program();
    let mut memory = [65u32, 10];
    let input = [];
    let mut output = [0x10u8, 0, 0];
    if matches!(
        PreparedNativeRegionInvocation::new(
            &program,
            &mut memory,
            &input,
            &mut output,
        ),
        Err(NativeRegionInvocationError::MemoryCapacity {
            available: 2,
            required: 3,
        })
    ) {
        Ok(())
    } else {
        Err(String::from("short native memory was admitted"))
    }
}

fn native_verified_output_program() -> Result<RegionEffectProgram, String> {
    let mut program = direct_output_program();
    let effect = program
        .effects
        .first_mut()
        .ok_or_else(|| String::from("verified output fixture has no effect"))?;
    effect.before.input_consumed = 0;
    effect.before.output_len = 1;
    effect.after.input_consumed = 0;
    effect.after.output_len = 2;
    Ok(program)
}

const fn native_verified_output_memory() -> [u32; 9] {
    let mut memory = [0u32; 9];
    memory[5] = 94;
    memory
}

#[test]
fn verified_direct_invocation_binds_exact_artifact_and_call()
-> Result<(), String> {
    let program = native_verified_output_program()?;
    let artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let mut memory = native_verified_output_memory();
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let mut invocation = PreparedVerifiedDirectInvocation::new(
        &artifact,
        &program,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    )
    .map_err(|error| error.to_string())?;
    if invocation.artifact() != &artifact
        || invocation.object() != artifact.object()
        || invocation.target() != artifact.key().target()
        || invocation.target_triple() != artifact.target_triple()
        || invocation.load_image().key() != artifact.key()
        || invocation.load_image().code()
            != direct_object_text(artifact.object())?
        || invocation.state_mut_ptr().is_null()
    {
        return Err(String::from("verified invocation binding drifted"));
    }
    invocation.apply_expected_for_test();
    let outcome = invocation
        .complete(NativeRegionStatus::Applied.code())
        .map_err(|error| error.to_string())?;
    let expected = program
        .effects
        .first()
        .ok_or_else(|| String::from("verified output fixture has no effect"))?
        .after;
    if outcome == NativeRegionInvocationOutcome::Applied(expected)
        && memory[5] == 57
        && output == [0x10, 0xa8, 0]
    {
        Ok(())
    } else {
        Err(String::from(
            "verified invocation did not apply exact effect",
        ))
    }
}

#[test]
fn verified_direct_invocation_rejects_artifact_identity_drift()
-> Result<(), String> {
    let program = native_verified_output_program()?;
    let artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let mut mismatched = program;
    mismatched.profile_fingerprint.push_str("-drift");
    let mut memory = native_verified_output_memory();
    let input = [];
    let mut output = [0x10u8, 0, 0];
    if matches!(
        PreparedVerifiedDirectInvocation::new(
            &artifact,
            &mismatched,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        ),
        Err(VerifiedDirectInvocationError::ArtifactIdentity)
    ) && memory == native_verified_output_memory()
        && output == [0x10, 0, 0]
    {
        Ok(())
    } else {
        Err(String::from("artifact identity drift was admitted"))
    }
}

#[test]
fn verified_direct_invocation_rejects_deoptimization_artifact()
-> Result<(), String> {
    let program = native_program();
    let artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    if artifact.kind() != DirectNativeKind::Deopt {
        return Err(String::from(
            "deoptimization fixture selected a fast path",
        ));
    }
    let mut memory = [];
    let input = [];
    let mut output = [];
    if matches!(
        PreparedVerifiedDirectInvocation::new(
            &artifact,
            &program,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        ),
        Err(VerifiedDirectInvocationError::ArtifactDeoptimization)
    ) {
        Ok(())
    } else {
        Err(String::from(
            "deoptimization artifact gained invocation authority",
        ))
    }
}

#[test]
fn verified_direct_invocation_rejects_invalid_identity() -> Result<(), String> {
    let program = native_verified_output_program()?;
    let artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let mut invalid = program;
    invalid.profile_requirement.memory_words = 1;
    let mut memory = native_verified_output_memory();
    let input = [];
    let mut output = [0x10u8, 0, 0];
    if matches!(
        PreparedVerifiedDirectInvocation::new(
            &artifact,
            &invalid,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        ),
        Err(VerifiedDirectInvocationError::Identity(
            NativeIdentityError::ProfileCapacity,
        ))
    ) {
        Ok(())
    } else {
        Err(String::from("invalid invocation identity was admitted"))
    }
}

#[test]
fn verified_direct_invocation_propagates_buffer_error() -> Result<(), String> {
    let program = native_verified_output_program()?;
    let artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let mut memory = native_verified_output_memory();
    memory[5] = 111;
    let input = [];
    let mut output = [0x10u8, 0, 0];
    if matches!(
        PreparedVerifiedDirectInvocation::new(
            &artifact,
            &program,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        ),
        Err(VerifiedDirectInvocationError::Invocation(
            NativeRegionInvocationError::EntryMemory {
                address: 5,
                expected: 94,
                observed: 111,
            },
        ))
    ) {
        Ok(())
    } else {
        Err(String::from("verified invocation masked buffer rejection"))
    }
}

fn direct_object_text(object: &[u8]) -> Result<&[u8], String> {
    const TEXT_HEADER: usize = 20;
    const RAW_SIZE_OFFSET: usize = 16;
    const RAW_START_OFFSET: usize = 20;
    let raw_size = read_fixture_u32(
        object,
        TEXT_HEADER
            .checked_add(RAW_SIZE_OFFSET)
            .ok_or_else(|| String::from("text size offset overflow"))?,
    )?;
    let raw_start = read_fixture_u32(
        object,
        TEXT_HEADER
            .checked_add(RAW_START_OFFSET)
            .ok_or_else(|| String::from("text start offset overflow"))?,
    )?;
    let size = usize::try_from(raw_size)
        .map_err(|error| format!("text size conversion: {error}"))?;
    let start = usize::try_from(raw_start)
        .map_err(|error| format!("text start conversion: {error}"))?;
    let end = start
        .checked_add(size)
        .ok_or_else(|| String::from("text range overflow"))?;
    object
        .get(start..end)
        .ok_or_else(|| String::from("text range exceeds object"))
}

fn read_fixture_u32(bytes: &[u8], offset: usize) -> Result<u32, String> {
    let end = offset
        .checked_add(4)
        .ok_or_else(|| String::from("fixture u32 offset overflow"))?;
    let raw = bytes
        .get(offset..end)
        .ok_or_else(|| String::from("fixture u32 exceeds object"))?;
    let array = <[u8; 4]>::try_from(raw)
        .map_err(|error| format!("fixture u32 width: {error}"))?;
    Ok(u32::from_le_bytes(array))
}

fn write_fixture_u16(
    bytes: &mut [u8],
    offset: usize,
    value: u16,
) -> Result<(), String> {
    let end = offset
        .checked_add(2)
        .ok_or_else(|| String::from("fixture u16 offset overflow"))?;
    let target = bytes
        .get_mut(offset..end)
        .ok_or_else(|| String::from("fixture u16 exceeds object"))?;
    target.copy_from_slice(&value.to_le_bytes());
    Ok(())
}

fn write_fixture_u32(
    bytes: &mut [u8],
    offset: usize,
    value: u32,
) -> Result<(), String> {
    let end = offset
        .checked_add(4)
        .ok_or_else(|| String::from("fixture u32 offset overflow"))?;
    let target = bytes
        .get_mut(offset..end)
        .ok_or_else(|| String::from("fixture u32 exceeds object"))?;
    target.copy_from_slice(&value.to_le_bytes());
    Ok(())
}

#[test]
fn verified_direct_load_image_extracts_every_template_on_both_isas()
-> Result<(), String> {
    let cases = direct_selection_cases();
    if cases.len() != 12 {
        return Err(format!(
            "direct load corpus size drifted: {}",
            cases.len()
        ));
    }
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        for (program, kind, _backend_id) in &cases {
            let artifact = select_verified_direct_native(
                program,
                safe_rust_profiled_capability(),
                HostOperatingSystem::Windows,
                isa,
            )
            .map_err(|error| error.to_string())?;
            let image =
                VerifiedDirectLoadImage::from_artifact_for_test(&artifact)
                    .map_err(|error| error.to_string())?;
            let expected_code = direct_object_text(artifact.object())?;
            let expected_alignment = match isa {
                HostIsa::AArch64 => 4,
                HostIsa::X86_64 => 1,
            };
            let policy = image.policy();
            if artifact.kind() != *kind
                || image.code() != expected_code
                || image.entry_code() != expected_code
                || image.entry_offset() != 0
                || image.allocation_len() != expected_code.len()
                || image.host_isa() != isa
                || image.key() != artifact.key()
                || image.minimum_instruction_alignment() != expected_alignment
                || image.target() != artifact.key().target()
                || image.target_triple() != artifact.target_triple()
                || policy.initial_permissions()
                    != NativeExecutablePermission::ReadWrite
                || policy.final_permissions()
                    != NativeExecutablePermission::ReadExecute
                || !policy.requires_instruction_sync()
            {
                return Err(format!(
                    "direct load image drifted for {kind:?} on {isa:?}",
                ));
            }
        }
    }
    Ok(())
}

#[test]
fn verified_direct_load_image_rejects_machine_drift() -> Result<(), String> {
    let program = direct_output_program();
    let artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let mut object = artifact.object().to_vec();
    write_fixture_u16(&mut object, 0, 0)?;
    if VerifiedDirectLoadImage::from_object_for_test(&artifact, &object)
        == Err(VerifiedDirectLoadError::Object(CoffAdmissionError::Machine))
    {
        Ok(())
    } else {
        Err(String::from("load image admitted machine drift"))
    }
}

#[test]
fn verified_direct_load_image_rejects_relocations() -> Result<(), String> {
    const TEXT_HEADER: usize = 20;
    const RELOCATION_START_OFFSET: usize = 24;
    const RELOCATION_COUNT_OFFSET: usize = 32;
    let program = direct_output_program();
    let artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let mut object = artifact.object().to_vec();
    let relocation_start = u32::try_from(object.len())
        .map_err(|error| format!("relocation offset conversion: {error}"))?;
    object.extend_from_slice(&[0u8; 10]);
    let start_offset = TEXT_HEADER
        .checked_add(RELOCATION_START_OFFSET)
        .ok_or_else(|| String::from("relocation start offset overflow"))?;
    let count_offset = TEXT_HEADER
        .checked_add(RELOCATION_COUNT_OFFSET)
        .ok_or_else(|| String::from("relocation count offset overflow"))?;
    write_fixture_u32(&mut object, start_offset, relocation_start)?;
    write_fixture_u16(&mut object, count_offset, 1)?;
    if VerifiedDirectLoadImage::from_object_for_test(&artifact, &object)
        == Err(VerifiedDirectLoadError::Relocations)
    {
        Ok(())
    } else {
        Err(String::from("load image admitted relocations"))
    }
}

fn native_executable_mapping_id(
    value: u64,
) -> Result<NativeExecutableMappingId, String> {
    NativeExecutableMappingId::new(value)
        .ok_or_else(|| String::from("native mapping identity must be non-zero"))
}

fn native_executable_address(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("native mapping address must be non-zero"))
}

fn ready_native_executable(
    artifact: &execution_native::VerifiedDirectNativeArtifact,
    mapping_value: u64,
    base_value: usize,
) -> Result<ReadyNativeExecutable, String> {
    let image = VerifiedDirectLoadImage::from_artifact_for_test(artifact)
        .map_err(|error| error.to_string())?;
    let mapping_id = native_executable_mapping_id(mapping_value)?;
    let base_address = native_executable_address(base_value)?;
    let writable = NativeExecutableMappingReport::new(
        mapping_id,
        base_address,
        image.allocation_len(),
        NativeExecutablePermission::ReadWrite,
    );
    let staged = StagedNativeExecutable::stage(&image, writable, image.code())
        .map_err(|error| error.to_string())?;
    let executable = NativeExecutableMappingReport::new(
        mapping_id,
        base_address,
        image.allocation_len(),
        NativeExecutablePermission::ReadExecute,
    );
    let sealed = staged
        .admit_read_execute(executable)
        .map_err(|error| error.to_string())?;
    sealed
        .admit_instruction_sync(NativeInstructionSyncReport::new(
            mapping_id,
            base_address,
            image.allocation_len(),
        ))
        .map_err(|error| error.to_string())
}

fn direct_output_load_image(
    isa: HostIsa,
) -> Result<VerifiedDirectLoadImage, String> {
    let artifact = select_verified_direct_native(
        &direct_output_program(),
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        isa,
    )
    .map_err(|error| error.to_string())?;
    VerifiedDirectLoadImage::from_artifact_for_test(&artifact)
        .map_err(|error| error.to_string())
}

#[test]
fn native_executable_lifecycle_admits_every_direct_template()
-> Result<(), String> {
    let cases = direct_selection_cases();
    let mut sequence = 1u64;
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        for (index, (program, kind, _backend_id)) in cases.iter().enumerate() {
            let artifact = select_verified_direct_native(
                program,
                safe_rust_profiled_capability(),
                HostOperatingSystem::Windows,
                isa,
            )
            .map_err(|error| error.to_string())?;
            let base_value = 0x1000usize
                .checked_mul(index.saturating_add(1))
                .ok_or_else(|| {
                String::from("native mapping base overflow")
            })?;
            let ready =
                ready_native_executable(&artifact, sequence, base_value)?;
            sequence = sequence.saturating_add(1);
            let release = ready.release_request();
            let expected_entry = base_value
                .checked_add(ready.image().entry_offset())
                .ok_or_else(|| String::from("native entry address overflow"))?;
            if artifact.kind() != *kind
                || ready.entry_address().get() != expected_entry
                || ready.image().key() != artifact.key()
                || ready.key() != artifact.key()
                || ready.mapping().permissions()
                    != NativeExecutablePermission::ReadExecute
                || ready.target() != artifact.key().target()
                || ready.target_triple() != artifact.target_triple()
                || release.base_address().get() != base_value
                || release.mapped_len() != ready.image().allocation_len()
                || release.mapping_id() != ready.mapping().mapping_id()
            {
                let detail = format!("{kind:?} on {isa:?}");
                return Err(format!(
                    "native executable lifecycle drifted for {detail}",
                ));
            }
        }
    }
    Ok(())
}

#[test]
fn native_executable_lifecycle_rejects_permission_and_code_drift()
-> Result<(), String> {
    if NativeExecutableMappingId::new(0).is_some() {
        return Err(String::from("zero native mapping identity was admitted"));
    }
    let image = direct_output_load_image(HostIsa::AArch64)?;
    let mapping_id = native_executable_mapping_id(31)?;
    let base = native_executable_address(0x4000)?;
    let writable = NativeExecutableMappingReport::new(
        mapping_id,
        base,
        image.allocation_len(),
        NativeExecutablePermission::ReadWrite,
    );
    let executable = NativeExecutableMappingReport::new(
        mapping_id,
        base,
        image.allocation_len(),
        NativeExecutablePermission::ReadExecute,
    );
    let mut drifted_code = image.code().to_vec();
    let first = drifted_code
        .first_mut()
        .ok_or_else(|| String::from("direct code image was empty"))?;
    *first ^= 1;
    if StagedNativeExecutable::stage(&image, executable, image.code())
        == Err(NativeExecutableLifecycleError::Permissions)
        && StagedNativeExecutable::stage(&image, writable, &drifted_code)
            == Err(NativeExecutableLifecycleError::CodeImage)
    {
        Ok(())
    } else {
        Err(String::from(
            "native staging permission/code drift was admitted",
        ))
    }
}

#[test]
fn native_executable_lifecycle_rejects_capacity_alignment_and_overflow()
-> Result<(), String> {
    let arm_image = direct_output_load_image(HostIsa::AArch64)?;
    let mapping_id = native_executable_mapping_id(32)?;
    let aligned = native_executable_address(0x4000)?;
    let short = NativeExecutableMappingReport::new(
        mapping_id,
        aligned,
        arm_image.allocation_len().saturating_sub(1),
        NativeExecutablePermission::ReadWrite,
    );
    let misaligned = NativeExecutableMappingReport::new(
        mapping_id,
        native_executable_address(0x4001)?,
        arm_image.allocation_len(),
        NativeExecutablePermission::ReadWrite,
    );
    let x86_image = direct_output_load_image(HostIsa::X86_64)?;
    let overflowing = NativeExecutableMappingReport::new(
        mapping_id,
        native_executable_address(usize::MAX)?,
        x86_image.allocation_len(),
        NativeExecutablePermission::ReadWrite,
    );
    if StagedNativeExecutable::stage(&arm_image, short, arm_image.code())
        == Err(NativeExecutableLifecycleError::MappingCapacity)
        && StagedNativeExecutable::stage(
            &arm_image,
            misaligned,
            arm_image.code(),
        ) == Err(NativeExecutableLifecycleError::MappingAlignment)
        && StagedNativeExecutable::stage(
            &x86_image,
            overflowing,
            x86_image.code(),
        ) == Err(NativeExecutableLifecycleError::AddressOverflow)
    {
        Ok(())
    } else {
        Err(String::from("native staging range drift was admitted"))
    }
}

#[test]
fn native_executable_lifecycle_rejects_seal_drift() -> Result<(), String> {
    let image = direct_output_load_image(HostIsa::X86_64)?;
    let mapping_id = native_executable_mapping_id(41)?;
    let other_id = native_executable_mapping_id(42)?;
    let base = native_executable_address(0x5000)?;
    let other_base = native_executable_address(0x6000)?;
    let writable = NativeExecutableMappingReport::new(
        mapping_id,
        base,
        image.allocation_len(),
        NativeExecutablePermission::ReadWrite,
    );
    let staged = StagedNativeExecutable::stage(&image, writable, image.code())
        .map_err(|error| error.to_string())?;
    let wrong_identity = NativeExecutableMappingReport::new(
        other_id,
        base,
        image.allocation_len(),
        NativeExecutablePermission::ReadExecute,
    );
    let wrong_range = NativeExecutableMappingReport::new(
        mapping_id,
        other_base,
        image.allocation_len(),
        NativeExecutablePermission::ReadExecute,
    );
    if staged.clone().admit_read_execute(wrong_identity)
        == Err(NativeExecutableLifecycleError::MappingIdentity)
        && staged.clone().admit_read_execute(wrong_range)
            == Err(NativeExecutableLifecycleError::MappingIdentity)
        && staged.admit_read_execute(writable)
            == Err(NativeExecutableLifecycleError::Permissions)
    {
        Ok(())
    } else {
        Err(String::from("native executable seal drift was admitted"))
    }
}

#[test]
fn native_executable_lifecycle_rejects_sync_drift() -> Result<(), String> {
    let image = direct_output_load_image(HostIsa::X86_64)?;
    let mapping_id = native_executable_mapping_id(43)?;
    let other_id = native_executable_mapping_id(44)?;
    let base = native_executable_address(0x7000)?;
    let other_base = native_executable_address(0x8000)?;
    let writable = NativeExecutableMappingReport::new(
        mapping_id,
        base,
        image.allocation_len(),
        NativeExecutablePermission::ReadWrite,
    );
    let staged = StagedNativeExecutable::stage(&image, writable, image.code())
        .map_err(|error| error.to_string())?;
    let executable = NativeExecutableMappingReport::new(
        mapping_id,
        base,
        image.allocation_len(),
        NativeExecutablePermission::ReadExecute,
    );
    let sealed = staged
        .admit_read_execute(executable)
        .map_err(|error| error.to_string())?;
    let wrong_id = NativeInstructionSyncReport::new(
        other_id,
        base,
        image.allocation_len(),
    );
    let wrong_start = NativeInstructionSyncReport::new(
        mapping_id,
        other_base,
        image.allocation_len(),
    );
    let wrong_len = NativeInstructionSyncReport::new(
        mapping_id,
        base,
        image.allocation_len().saturating_sub(1),
    );
    if sealed.clone().admit_instruction_sync(wrong_id)
        == Err(NativeExecutableLifecycleError::MappingIdentity)
        && sealed.clone().admit_instruction_sync(wrong_start)
            == Err(NativeExecutableLifecycleError::SynchronizationRange)
        && sealed.admit_instruction_sync(wrong_len)
            == Err(NativeExecutableLifecycleError::SynchronizationRange)
    {
        Ok(())
    } else {
        Err(String::from("native executable sync drift was admitted"))
    }
}

#[test]
fn native_executable_invocation_binds_ready_mapping() -> Result<(), String> {
    let program = native_verified_output_program()?;
    let artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let ready = ready_native_executable(&artifact, 51, 0x7000)?;
    let mut memory = native_verified_output_memory();
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let prepared = PreparedVerifiedDirectInvocation::new(
        &artifact,
        &program,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    )
    .map_err(|error| error.to_string())?;
    let mut invocation = prepared
        .bind_executable(&ready)
        .map_err(|error| error.to_string())?;
    if invocation.entry_address() != ready.entry_address()
        || invocation.executable() != &ready
        || invocation.mapping_id() != ready.mapping().mapping_id()
        || invocation.state_mut_ptr().is_null()
    {
        return Err(String::from("ready executable call binding drifted"));
    }
    invocation.apply_expected_for_test();
    let outcome = invocation
        .complete(NativeRegionStatus::Applied.code())
        .map_err(|error| error.to_string())?;
    let expected = program
        .effects
        .first()
        .ok_or_else(|| String::from("verified output fixture has no effect"))?
        .after;
    if outcome == NativeRegionInvocationOutcome::Applied(expected)
        && memory[5] == 57
        && output == [0x10, 0xa8, 0]
    {
        Ok(())
    } else {
        Err(String::from(
            "ready executable call did not apply exact effect",
        ))
    }
}

#[test]
fn native_executable_invocation_rejects_different_image() -> Result<(), String>
{
    let program = native_verified_output_program()?;
    let x86_artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let arm_artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::AArch64,
    )
    .map_err(|error| error.to_string())?;
    let ready = ready_native_executable(&arm_artifact, 61, 0x8000)?;
    let mut memory = native_verified_output_memory();
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let prepared = PreparedVerifiedDirectInvocation::new(
        &x86_artifact,
        &program,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    )
    .map_err(|error| error.to_string())?;
    if matches!(
        prepared.bind_executable(&ready),
        Err(NativeExecutableInvocationBindingError::ExecutableIdentity)
    ) && memory == native_verified_output_memory()
        && output == [0x10, 0, 0]
    {
        Ok(())
    } else {
        Err(String::from("different executable image was bound to call"))
    }
}

fn assert_native_loader_success(
    artifact: &execution_native::VerifiedDirectNativeArtifact,
    mapping_value: u64,
    base_value: usize,
) -> Result<(), String> {
    let image = VerifiedDirectLoadImage::from_artifact_for_test(artifact)
        .map_err(|error| error.to_string())?;
    let mapping_id = native_executable_mapping_id(mapping_value)?;
    let base_address = native_executable_address(base_value)?;
    let mut adapter =
        FakeNativeExecutableAdapter::new(mapping_id, base_address);
    let ready = load_native_executable(&mut adapter, &image)
        .map_err(|error| error.to_string())?;
    let allocation = adapter
        .allocation_requests
        .first()
        .ok_or_else(|| String::from("loader omitted allocation request"))?;
    let synchronization = adapter
        .synchronization_requests
        .first()
        .ok_or_else(|| String::from("loader omitted sync request"))?;
    if *allocation
        != NativeExecutableAllocationRequest::new(
            image.allocation_len(),
            image.minimum_instruction_alignment(),
            NativeExecutablePermission::ReadWrite,
        )
        || adapter.copied_code.as_slice() != [image.code()]
        || synchronization.mapping_id() != mapping_id
        || synchronization.start_address() != base_address
        || synchronization.byte_len() != image.allocation_len()
        || ready.key() != artifact.key()
        || adapter.operations
            != [
                FakeNativeAdapterOperation::Allocate,
                FakeNativeAdapterOperation::Copy,
                FakeNativeAdapterOperation::Protect,
                FakeNativeAdapterOperation::Synchronize,
            ]
    {
        return Err(String::from("native loader success evidence drifted"));
    }
    let release = ready.release_request();
    release_native_executable(&mut adapter, ready)
        .map_err(|error| error.to_string())?;
    if adapter.release_requests == [release]
        && adapter.operations.last()
            == Some(&FakeNativeAdapterOperation::Release)
    {
        Ok(())
    } else {
        Err(String::from("native loader release evidence drifted"))
    }
}

#[test]
fn native_executable_loader_runs_every_direct_template() -> Result<(), String> {
    let cases = direct_selection_cases();
    let mut mapping_value = 100u64;
    let mut base_value = 0x10_000usize;
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        for (program, _kind, _backend_id) in &cases {
            let artifact = select_verified_direct_native(
                program,
                safe_rust_profiled_capability(),
                HostOperatingSystem::Windows,
                isa,
            )
            .map_err(|error| error.to_string())?;
            assert_native_loader_success(&artifact, mapping_value, base_value)?;
            mapping_value = mapping_value.saturating_add(1);
            base_value = base_value.saturating_add(0x1000);
        }
    }
    Ok(())
}

const fn expected_failure_operations(
    failure: FakeNativeAdapterOperation,
) -> &'static [FakeNativeAdapterOperation] {
    match failure {
        FakeNativeAdapterOperation::Allocate => {
            &[FakeNativeAdapterOperation::Allocate]
        },
        FakeNativeAdapterOperation::Copy => &[
            FakeNativeAdapterOperation::Allocate,
            FakeNativeAdapterOperation::Copy,
            FakeNativeAdapterOperation::Release,
        ],
        FakeNativeAdapterOperation::Protect => &[
            FakeNativeAdapterOperation::Allocate,
            FakeNativeAdapterOperation::Copy,
            FakeNativeAdapterOperation::Protect,
            FakeNativeAdapterOperation::Release,
        ],
        FakeNativeAdapterOperation::Synchronize => &[
            FakeNativeAdapterOperation::Allocate,
            FakeNativeAdapterOperation::Copy,
            FakeNativeAdapterOperation::Protect,
            FakeNativeAdapterOperation::Synchronize,
            FakeNativeAdapterOperation::Release,
        ],
        FakeNativeAdapterOperation::Release => &[],
    }
}

#[test]
fn native_executable_loader_cleans_up_adapter_failures() -> Result<(), String> {
    let image = direct_output_load_image(HostIsa::X86_64)?;
    let cases = [
        (
            FakeNativeAdapterOperation::Allocate,
            NativeExecutableLoadPhase::Allocate,
        ),
        (
            FakeNativeAdapterOperation::Copy,
            NativeExecutableLoadPhase::Copy,
        ),
        (
            FakeNativeAdapterOperation::Protect,
            NativeExecutableLoadPhase::Protect,
        ),
        (
            FakeNativeAdapterOperation::Synchronize,
            NativeExecutableLoadPhase::Synchronize,
        ),
    ];
    for (index, (failure, phase)) in cases.into_iter().enumerate() {
        let mapping_id = native_executable_mapping_id(
            200u64.saturating_add(u64::try_from(index).unwrap_or(0)),
        )?;
        let mut adapter = FakeNativeExecutableAdapter::new(
            mapping_id,
            native_executable_address(0x20_000)?,
        )
        .with_failure(failure);
        let Err(error) = load_native_executable(&mut adapter, &image) else {
            return Err(String::from("configured adapter failure was ignored"));
        };
        let release_expected = failure != FakeNativeAdapterOperation::Allocate;
        if error.phase() != phase
            || error.adapter_error() != Some(&failure)
            || error.evidence_error().is_some()
            || error.lifecycle_error().is_some()
            || error.release_error().is_some()
            || error.release_request().is_some() != release_expected
            || adapter.operations != expected_failure_operations(failure)
            || adapter.release_requests.len() != usize::from(release_expected)
        {
            return Err(format!(
                "adapter failure cleanup drifted at {failure}"
            ));
        }
    }
    Ok(())
}

fn assert_native_loader_drift(
    drift: FakeNativeAdapterDrift,
    phase: NativeExecutableLoadPhase,
    lifecycle: Option<NativeExecutableLifecycleError>,
    evidence: Option<NativeExecutableOperationEvidenceError>,
) -> Result<(), String> {
    let image = direct_output_load_image(HostIsa::AArch64)?;
    let mapping_id = native_executable_mapping_id(300)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        mapping_id,
        native_executable_address(0x30_000)?,
    )
    .with_drift(drift);
    let Err(error) = load_native_executable(&mut adapter, &image) else {
        return Err(String::from(
            "configured platform evidence drift was ignored",
        ));
    };
    if error.phase() == phase
        && error.adapter_error().is_none()
        && error.lifecycle_error() == lifecycle
        && error.evidence_error() == evidence
        && error.release_error().is_none()
        && error.release_request().is_some()
        && adapter.operations.last()
            == Some(&FakeNativeAdapterOperation::Release)
        && adapter.release_requests.len() == 1
    {
        Ok(())
    } else {
        Err(format!("native loader drift admission changed: {drift:?}"))
    }
}

#[test]
fn native_executable_loader_rejects_platform_evidence_drift()
-> Result<(), String> {
    let lifecycle_cases = [
        (
            FakeNativeAdapterDrift::AllocationAlignment,
            NativeExecutableLoadPhase::Allocate,
            NativeExecutableLifecycleError::MappingAlignment,
        ),
        (
            FakeNativeAdapterDrift::AllocationCapacity,
            NativeExecutableLoadPhase::Allocate,
            NativeExecutableLifecycleError::MappingCapacity,
        ),
        (
            FakeNativeAdapterDrift::AllocationPermission,
            NativeExecutableLoadPhase::Allocate,
            NativeExecutableLifecycleError::Permissions,
        ),
        (
            FakeNativeAdapterDrift::CopyBytes,
            NativeExecutableLoadPhase::Copy,
            NativeExecutableLifecycleError::CodeImage,
        ),
        (
            FakeNativeAdapterDrift::ProtectMappingIdentity,
            NativeExecutableLoadPhase::Protect,
            NativeExecutableLifecycleError::MappingIdentity,
        ),
        (
            FakeNativeAdapterDrift::ProtectPermissions,
            NativeExecutableLoadPhase::Protect,
            NativeExecutableLifecycleError::Permissions,
        ),
        (
            FakeNativeAdapterDrift::SynchronizeMappingIdentity,
            NativeExecutableLoadPhase::Synchronize,
            NativeExecutableLifecycleError::MappingIdentity,
        ),
        (
            FakeNativeAdapterDrift::SynchronizeRange,
            NativeExecutableLoadPhase::Synchronize,
            NativeExecutableLifecycleError::SynchronizationRange,
        ),
    ];
    for (drift, phase, expected) in lifecycle_cases {
        assert_native_loader_drift(drift, phase, Some(expected), None)?;
    }
    assert_native_loader_drift(
        FakeNativeAdapterDrift::CopyMappingIdentity,
        NativeExecutableLoadPhase::Copy,
        None,
        Some(NativeExecutableOperationEvidenceError::CopyMappingIdentity),
    )?;
    assert_native_loader_drift(
        FakeNativeAdapterDrift::CopyStartAddress,
        NativeExecutableLoadPhase::Copy,
        None,
        Some(NativeExecutableOperationEvidenceError::CopyStartAddress),
    )
}

#[test]
fn native_executable_loader_retains_cleanup_failure() -> Result<(), String> {
    let image = direct_output_load_image(HostIsa::X86_64)?;
    let mapping_id = native_executable_mapping_id(400)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        mapping_id,
        native_executable_address(0x40_000)?,
    )
    .with_failure(FakeNativeAdapterOperation::Copy)
    .with_release_failures(1);
    let Err(error) = load_native_executable(&mut adapter, &image) else {
        return Err(String::from("copy and cleanup failures were ignored"));
    };
    if error.phase() == NativeExecutableLoadPhase::Copy
        && error.adapter_error() == Some(&FakeNativeAdapterOperation::Copy)
        && error.release_error() == Some(&FakeNativeAdapterOperation::Release)
        && error.release_request() == adapter.release_requests.first().copied()
        && adapter.operations
            == [
                FakeNativeAdapterOperation::Allocate,
                FakeNativeAdapterOperation::Copy,
                FakeNativeAdapterOperation::Release,
            ]
    {
        Ok(())
    } else {
        Err(String::from("loader cleanup failure evidence drifted"))
    }
}

#[test]
fn native_executable_release_failure_retries_exact_mapping()
-> Result<(), String> {
    let image = direct_output_load_image(HostIsa::X86_64)?;
    let mapping_id = native_executable_mapping_id(500)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        mapping_id,
        native_executable_address(0x50_000)?,
    );
    let ready = load_native_executable(&mut adapter, &image)
        .map_err(|error| error.to_string())?;
    let expected_key = ready.key().clone();
    let expected_release = ready.release_request();
    adapter.release_failures_remaining = 1;
    let Err(failure) = release_native_executable(&mut adapter, ready) else {
        return Err(String::from("configured release failure was ignored"));
    };
    if failure.error() != &FakeNativeAdapterOperation::Release
        || failure.executable().key() != &expected_key
        || failure.executable().release_request() != expected_release
    {
        return Err(String::from("release failure lost executable identity"));
    }
    failure
        .retry(&mut adapter)
        .map_err(|error| error.to_string())?;
    if adapter.release_requests == [expected_release, expected_release]
        && adapter.operations.ends_with(&[
            FakeNativeAdapterOperation::Release,
            FakeNativeAdapterOperation::Release,
        ])
    {
        Ok(())
    } else {
        Err(String::from("release retry changed exact mapping request"))
    }
}

fn prepared_verified_output_call<'artifact, 'buffers>(
    artifact: &'artifact execution_native::VerifiedDirectNativeArtifact,
    program: &RegionEffectProgram,
    buffers: NativeRegionBuffers<'buffers>,
) -> Result<PreparedVerifiedDirectInvocation<'artifact, 'buffers>, String> {
    PreparedVerifiedDirectInvocation::new(artifact, program, buffers)
        .map_err(|error| error.to_string())
}

fn repeated_release_request(adapter: &FakeNativeExecutableAdapter) -> bool {
    matches!(
        adapter.release_requests.as_slice(),
        [.., first, second] if first == second
    )
}

#[test]
fn native_executable_execution_applies_and_releases() -> Result<(), String> {
    let program = native_verified_output_program()?;
    let artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let expected = program
        .effects
        .first()
        .ok_or_else(|| String::from("verified output fixture has no effect"))?
        .after;
    let mapping_id = native_executable_mapping_id(600)?;
    let base_address = native_executable_address(0x60_000)?;
    let mut adapter =
        FakeNativeExecutableAdapter::new(mapping_id, base_address);
    let mut runner =
        FakeNativeExecutableRunner::new(FakeNativeRunnerBehavior::Applied);
    let mut memory = native_verified_output_memory();
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let prepared = prepared_verified_output_call(
        &artifact,
        &program,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    )?;
    let outcome = execute_verified_native(&mut adapter, &mut runner, prepared)
        .map_err(|error| error.to_string())?;
    if outcome == NativeRegionInvocationOutcome::Applied(expected)
        && memory[5] == 57
        && output == [0x10, 0xa8, 0]
        && runner.calls == 1
        && runner.entry_addresses == [base_address]
        && runner.mapping_ids == [mapping_id]
        && runner.state_pointers_non_null == [true]
        && adapter.operations
            == [
                FakeNativeAdapterOperation::Allocate,
                FakeNativeAdapterOperation::Copy,
                FakeNativeAdapterOperation::Protect,
                FakeNativeAdapterOperation::Synchronize,
                FakeNativeAdapterOperation::Release,
            ]
    {
        Ok(())
    } else {
        Err(String::from("native execution success transaction drifted"))
    }
}

#[test]
fn native_executable_execution_admits_guard_miss() -> Result<(), String> {
    let program = native_verified_output_program()?;
    let artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::AArch64,
    )
    .map_err(|error| error.to_string())?;
    let mapping_id = native_executable_mapping_id(601)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        mapping_id,
        native_executable_address(0x61_000)?,
    );
    let mut runner =
        FakeNativeExecutableRunner::new(FakeNativeRunnerBehavior::GuardMiss);
    let mut memory = native_verified_output_memory();
    let entry_memory = memory;
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let entry_output = output;
    let prepared = prepared_verified_output_call(
        &artifact,
        &program,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    )?;
    let outcome = execute_verified_native(&mut adapter, &mut runner, prepared)
        .map_err(|error| error.to_string())?;
    if outcome == NativeRegionInvocationOutcome::GuardMiss
        && memory == entry_memory
        && output == entry_output
        && runner.calls == 1
        && adapter.release_requests.len() == 1
    {
        Ok(())
    } else {
        Err(String::from("native guard miss transaction drifted"))
    }
}

#[test]
fn native_executable_execution_reports_load_failure_before_runner()
-> Result<(), String> {
    let program = native_verified_output_program()?;
    let artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(602)?,
        native_executable_address(0x62_000)?,
    )
    .with_failure(FakeNativeAdapterOperation::Allocate);
    let mut runner =
        FakeNativeExecutableRunner::new(FakeNativeRunnerBehavior::Applied);
    let mut memory = native_verified_output_memory();
    let entry_memory = memory;
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let entry_output = output;
    let prepared = prepared_verified_output_call(
        &artifact,
        &program,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    )?;
    let Err(error) =
        execute_verified_native(&mut adapter, &mut runner, prepared)
    else {
        return Err(String::from("configured load failure was ignored"));
    };
    let load_error = error
        .load_failure()
        .and_then(|failure| failure.adapter_error());
    if error.phase() == NativeExecutableExecutionPhase::Load
        && load_error == Some(&FakeNativeAdapterOperation::Allocate)
        && error.binding_error().is_none()
        && error.completion_error().is_none()
        && error.committed_outcome().is_none()
        && error.release_failure().is_none()
        && error.release_request().is_none()
        && error.runner_error().is_none()
        && runner.calls == 0
        && memory == entry_memory
        && output == entry_output
    {
        Ok(())
    } else {
        Err(String::from("native execution load failure drifted"))
    }
}

#[test]
fn native_executable_execution_restores_runner_failure_and_retries_release()
-> Result<(), String> {
    let program = native_verified_output_program()?;
    let artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(603)?,
        native_executable_address(0x63_000)?,
    )
    .with_release_failures(1);
    let mut runner = FakeNativeExecutableRunner::new(
        FakeNativeRunnerBehavior::FailureAfterMutation,
    );
    let mut memory = native_verified_output_memory();
    let entry_memory = memory;
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let entry_output = output;
    let prepared = prepared_verified_output_call(
        &artifact,
        &program,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    )?;
    let Err(error) =
        execute_verified_native(&mut adapter, &mut runner, prepared)
    else {
        return Err(String::from("configured runner failure was ignored"));
    };
    if error.phase() != NativeExecutableExecutionPhase::Run
        || error.runner_error() != Some(&FakeNativeRunnerError::Call)
        || error.release_failure().is_none()
        || error.release_request() != adapter.release_requests.first().copied()
        || memory != entry_memory
        || output != entry_output
    {
        return Err(String::from("runner failure rollback evidence drifted"));
    }
    let release_failure = (*error)
        .into_release_failure()
        .ok_or_else(|| String::from("runner cleanup retry state was lost"))?;
    release_failure
        .retry(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    if repeated_release_request(&adapter) {
        Ok(())
    } else {
        Err(String::from(
            "runner cleanup retry changed mapping identity",
        ))
    }
}

#[test]
fn native_executable_execution_restores_completion_drift() -> Result<(), String>
{
    let program = native_verified_output_program()?;
    let artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(604)?,
        native_executable_address(0x64_000)?,
    );
    let mut runner = FakeNativeExecutableRunner::new(
        FakeNativeRunnerBehavior::CompletionDrift,
    );
    let mut memory = native_verified_output_memory();
    let entry_memory = memory;
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let entry_output = output;
    let prepared = prepared_verified_output_call(
        &artifact,
        &program,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    )?;
    let Err(error) =
        execute_verified_native(&mut adapter, &mut runner, prepared)
    else {
        return Err(String::from("configured completion drift was ignored"));
    };
    let expected_completion = matches!(
        error.completion_error(),
        Some(VerifiedDirectInvocationError::Invocation(
            NativeRegionInvocationError::AppliedMemory { address: 5, .. }
        ))
    );
    if error.phase() == NativeExecutableExecutionPhase::Complete
        && expected_completion
        && error.runner_error().is_none()
        && error.release_failure().is_none()
        && error.release_request() == adapter.release_requests.first().copied()
        && memory == entry_memory
        && output == entry_output
    {
        Ok(())
    } else {
        Err(String::from("completion drift rollback evidence changed"))
    }
}

#[test]
fn native_executable_execution_retains_committed_outcome_on_release_failure()
-> Result<(), String> {
    let program = native_verified_output_program()?;
    let artifact = select_verified_direct_native(
        &program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::AArch64,
    )
    .map_err(|error| error.to_string())?;
    let expected = program
        .effects
        .first()
        .ok_or_else(|| String::from("verified output fixture has no effect"))?
        .after;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(605)?,
        native_executable_address(0x65_000)?,
    )
    .with_release_failures(1);
    let mut runner =
        FakeNativeExecutableRunner::new(FakeNativeRunnerBehavior::Applied);
    let mut memory = native_verified_output_memory();
    let input = [];
    let mut output = [0x10u8, 0, 0];
    let prepared = prepared_verified_output_call(
        &artifact,
        &program,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    )?;
    let Err(error) =
        execute_verified_native(&mut adapter, &mut runner, prepared)
    else {
        return Err(String::from(
            "configured final release failure was ignored",
        ));
    };
    if error.phase() != NativeExecutableExecutionPhase::Release
        || error.committed_outcome()
            != Some(NativeRegionInvocationOutcome::Applied(expected))
        || error.release_failure().is_none()
        || memory[5] != 57
        || output != [0x10, 0xa8, 0]
    {
        return Err(String::from("committed release failure evidence drifted"));
    }
    let release_failure = (*error).into_release_failure().ok_or_else(|| {
        String::from("committed executable retry state was lost")
    })?;
    release_failure
        .retry(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    if repeated_release_request(&adapter) {
        Ok(())
    } else {
        Err(String::from(
            "committed release retry changed mapping identity",
        ))
    }
}

#[test]
fn native_sequence_execution_applies_uncached_plan() -> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = select_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(700)?,
        native_executable_address(0x70_000)?,
    );
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = execute_verified_native_sequence(
        &mut adapter,
        &mut runner,
        &plan,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    )
    .map_err(|error| error.to_string())?;
    if outcome
        == (NativeSequenceExecutionOutcome::Applied {
            observation: plan.exit(),
            steps: 2,
        })
        && outcome.completed_steps() == 2
        && outcome.resume_index() == 2
        && outcome.observation() == plan.exit()
        && memory == fixture.final_memory
        && output == fixture.final_output
        && runner.calls == 2
        && adapter.release_requests.len() == 2
    {
        Ok(())
    } else {
        Err(String::from("uncached native sequence application drifted"))
    }
}

#[test]
fn native_sequence_execution_applies_cached_plan() -> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let mut cache = VerifiedDirectNativeCache::default();
    let plan = select_cached_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::AArch64),
        &mut cache,
    )
    .map_err(|error| error.to_string())?;
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(701)?,
        native_executable_address(0x71_000)?,
    );
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = execute_cached_verified_native_sequence(
        &mut adapter,
        &mut runner,
        &plan,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    )
    .map_err(|error| error.to_string())?;
    if outcome.completed_steps() == 2
        && outcome.observation() == plan.exit()
        && memory == fixture.final_memory
        && output == fixture.final_output
        && cache.len() == 2
        && runner.calls == 2
    {
        Ok(())
    } else {
        Err(String::from("cached native sequence application drifted"))
    }
}

#[test]
fn native_sequence_resumes_at_second_guard_miss() -> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = select_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let second_entry = fixture
        .programs
        .get(1)
        .and_then(|program| program.effects.first())
        .map(|effect| effect.before)
        .ok_or_else(|| String::from("second sequence entry missing"))?;
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(702)?,
        native_executable_address(0x72_000)?,
    );
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let outcome = execute_verified_native_sequence(
        &mut adapter,
        &mut runner,
        &plan,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    )
    .map_err(|error| error.to_string())?;
    if outcome
        == (NativeSequenceExecutionOutcome::GuardMiss {
            index: 1,
            observation: second_entry,
        })
        && outcome.completed_steps() == 1
        && outcome.resume_index() == 1
        && memory == fixture.first_memory
        && output == fixture.first_output
        && runner.calls == 2
        && adapter.release_requests.len() == 2
    {
        Ok(())
    } else {
        Err(String::from("native sequence guard-miss resume drifted"))
    }
}

#[test]
fn native_sequence_execution_restores_failed_second_step() -> Result<(), String>
{
    let fixture = direct_normative_sequence_fixture()?;
    let plan = select_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::AArch64,
    )
    .map_err(|error| error.to_string())?;
    let second_entry = fixture
        .programs
        .get(1)
        .and_then(|program| program.effects.first())
        .map(|effect| effect.before)
        .ok_or_else(|| String::from("second sequence entry missing"))?;
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(703)?,
        native_executable_address(0x73_000)?,
    );
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let Err(error) = execute_verified_native_sequence(
        &mut adapter,
        &mut runner,
        &plan,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    ) else {
        return Err(String::from("configured second-step failure was ignored"));
    };
    let runner_error = error
        .execution_failure()
        .and_then(|failure| failure.runner_error());
    if error.step_index() == 1
        && error.completed_steps() == 1
        && error.resume_index() == 1
        && error.observation() == second_entry
        && error.preparation_error().is_none()
        && runner_error == Some(&FakeNativeRunnerError::Call)
        && memory == fixture.first_memory
        && output == fixture.first_output
        && adapter.release_requests.len() == 2
    {
        Ok(())
    } else {
        Err(String::from("second-step rollback/resume evidence drifted"))
    }
}

#[test]
fn native_sequence_keeps_applied_progress_when_release_fails()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = select_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(704)?,
        native_executable_address(0x74_000)?,
    )
    .with_release_failure_at(2);
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let Err(error) = execute_verified_native_sequence(
        &mut adapter,
        &mut runner,
        &plan,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    ) else {
        return Err(String::from("second release failure was ignored"));
    };
    if error.completed_steps() != 2
        || error.resume_index() != 2
        || error.observation() != plan.exit()
        || memory != fixture.final_memory
        || output != fixture.final_output
    {
        return Err(String::from(
            "applied release failure lost sequence progress",
        ));
    }
    let execution = (*error)
        .into_execution_failure()
        .ok_or_else(|| String::from("sequence execution failure was lost"))?;
    if !matches!(
        execution.committed_outcome(),
        Some(NativeRegionInvocationOutcome::Applied(observation))
            if observation == plan.exit()
    ) {
        return Err(String::from("committed final sequence outcome was lost"));
    }
    let release = execution
        .into_release_failure()
        .ok_or_else(|| String::from("sequence release retry state was lost"))?;
    release
        .retry(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    if repeated_release_request(&adapter) {
        Ok(())
    } else {
        Err(String::from(
            "sequence release retry changed mapping request",
        ))
    }
}

#[test]
fn native_sequence_execution_preserves_guard_resume_on_release_failure()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = select_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::AArch64,
    )
    .map_err(|error| error.to_string())?;
    let second_entry = fixture
        .programs
        .get(1)
        .and_then(|program| program.effects.first())
        .map(|effect| effect.before)
        .ok_or_else(|| String::from("second sequence entry missing"))?;
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(705)?,
        native_executable_address(0x75_000)?,
    )
    .with_release_failure_at(2);
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let Err(error) = execute_verified_native_sequence(
        &mut adapter,
        &mut runner,
        &plan,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    ) else {
        return Err(String::from("guard-miss release failure was ignored"));
    };
    let committed = error.execution_failure().and_then(
        execution_native::NativeExecutableExecutionFailure::committed_outcome,
    );
    if error.step_index() == 1
        && error.completed_steps() == 1
        && error.resume_index() == 1
        && error.observation() == second_entry
        && committed == Some(NativeRegionInvocationOutcome::GuardMiss)
        && memory == fixture.first_memory
        && output == fixture.first_output
    {
        Ok(())
    } else {
        Err(String::from(
            "guard release failure lost exact resume evidence",
        ))
    }
}

fn assert_loaded_sequence_application(
    fixture: &NativeSequenceFixture,
    plan: &VerifiedDirectSequencePlan,
    sequence: &ReadyNativeExecutableSequence,
) -> Result<(), String> {
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = execute_loaded_verified_native_sequence(
        &mut runner,
        plan,
        sequence,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    )
    .map_err(|error| error.to_string())?;
    if outcome.completed_steps() == 2
        && memory == fixture.final_memory
        && output == fixture.final_output
        && runner.calls == 2
    {
        Ok(())
    } else {
        Err(String::from(
            "persistent sequence reuse changed execution evidence",
        ))
    }
}

#[test]
fn persistent_native_sequence_loads_reuses_and_releases() -> Result<(), String>
{
    let fixture = direct_normative_sequence_fixture()?;
    let plan = select_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(800)?,
        native_executable_address(0x80_000)?,
    );
    let sequence = load_verified_native_sequence(&mut adapter, &plan)
        .map_err(|error| error.to_string())?;
    let expected_release = sequence
        .executables()
        .iter()
        .rev()
        .map(ReadyNativeExecutable::release_request)
        .collect::<Vec<_>>();
    let mapping_ids = sequence
        .executables()
        .iter()
        .map(|executable| executable.mapping().mapping_id())
        .collect::<Vec<_>>();
    if sequence.len() != 2
        || sequence.is_empty()
        || mapping_ids.first() == mapping_ids.get(1)
        || adapter.operations.len() != 8
        || !adapter.release_requests.is_empty()
    {
        return Err(String::from("persistent sequence load evidence drifted"));
    }
    let operations_after_load = adapter.operations.len();
    for _iteration in [0usize, 1usize] {
        assert_loaded_sequence_application(&fixture, &plan, &sequence)?;
        if adapter.operations.len() != operations_after_load {
            return Err(String::from(
                "loaded execution performed memory-adapter operations",
            ));
        }
    }
    release_native_executable_sequence(&mut adapter, sequence)
        .map_err(|error| error.to_string())?;
    if adapter.release_requests == expected_release
        && adapter.operations.len() == operations_after_load.saturating_add(2)
    {
        Ok(())
    } else {
        Err(String::from("persistent sequence release order drifted"))
    }
}

#[test]
fn persistent_cached_sequence_preserves_second_guard_resume()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let mut cache = VerifiedDirectNativeCache::default();
    let plan = select_cached_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::AArch64),
        &mut cache,
    )
    .map_err(|error| error.to_string())?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(801)?,
        native_executable_address(0x81_000)?,
    );
    let sequence = load_cached_verified_native_sequence(&mut adapter, &plan)
        .map_err(|error| error.to_string())?;
    let operations_after_load = adapter.operations.len();
    let second_entry = plan
        .programs()
        .get(1)
        .and_then(|program| program.effects.first())
        .map(|effect| effect.before)
        .ok_or_else(|| String::from("persistent second entry missing"))?;
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let outcome = execute_loaded_cached_verified_native_sequence(
        &mut runner,
        &plan,
        &sequence,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    )
    .map_err(|error| error.to_string())?;
    if outcome
        != (NativeSequenceExecutionOutcome::GuardMiss {
            index: 1,
            observation: second_entry,
        })
        || memory != fixture.first_memory
        || output != fixture.first_output
        || adapter.operations.len() != operations_after_load
        || runner.calls != 2
    {
        return Err(String::from(
            "persistent cached guard-miss resume evidence drifted",
        ));
    }
    release_native_executable_sequence(&mut adapter, sequence)
        .map_err(|error| error.to_string())
}

#[test]
fn persistent_native_sequence_rolls_back_partial_load() -> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = select_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(802)?,
        native_executable_address(0x82_000)?,
    )
    .with_failure_at(FakeNativeAdapterOperation::Allocate, 2);
    let Err(error) = load_verified_native_sequence(&mut adapter, &plan) else {
        return Err(String::from("second sequence allocation failure ignored"));
    };
    let adapter_error = error
        .load_failure()
        .and_then(|failure| failure.adapter_error());
    if error.index() == 1
        && error.loaded_count() == 1
        && error.image_error().is_none()
        && error.cleanup_failure().is_none()
        && adapter_error == Some(&FakeNativeAdapterOperation::Allocate)
        && adapter.release_requests.len() == 1
        && adapter.operations.last()
            == Some(&FakeNativeAdapterOperation::Release)
    {
        Ok(())
    } else {
        Err(String::from("partial sequence load rollback drifted"))
    }
}

#[test]
fn persistent_native_sequence_retains_partial_cleanup_failure()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = select_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::AArch64,
    )
    .map_err(|error| error.to_string())?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(803)?,
        native_executable_address(0x83_000)?,
    )
    .with_failure_at(FakeNativeAdapterOperation::Allocate, 2)
    .with_release_failures(1);
    let Err(error) = load_verified_native_sequence(&mut adapter, &plan) else {
        return Err(String::from("partial load cleanup failure was ignored"));
    };
    let cleanup_evidence = error.cleanup_failure().ok_or_else(|| {
        String::from("partial load cleanup failure evidence was lost")
    })?;
    if error.index() != 1
        || error.loaded_count() != 1
        || cleanup_evidence.attempted_count() != 1
        || cleanup_evidence.failed_count() != 1
        || cleanup_evidence.released_count() != 0
    {
        return Err(String::from(
            "partial load cleanup aggregation evidence drifted",
        ));
    }
    let retry_cleanup = (*error).into_cleanup_failure().ok_or_else(|| {
        String::from("partial load cleanup retry ownership was lost")
    })?;
    retry_cleanup
        .retry(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    if repeated_release_request(&adapter) {
        Ok(())
    } else {
        Err(String::from(
            "partial load cleanup retry changed mapping request",
        ))
    }
}

#[test]
fn persistent_native_sequence_release_attempts_every_mapping()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = select_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(804)?,
        native_executable_address(0x84_000)?,
    );
    let sequence = load_verified_native_sequence(&mut adapter, &plan)
        .map_err(|error| error.to_string())?;
    let expected_release = sequence
        .executables()
        .iter()
        .rev()
        .map(ReadyNativeExecutable::release_request)
        .collect::<Vec<_>>();
    adapter.release_failure_at = Some(1);
    let Err(failure) =
        release_native_executable_sequence(&mut adapter, sequence)
    else {
        return Err(String::from("aggregate release failure was ignored"));
    };
    if failure.attempted_count() != 2
        || failure.failed_count() != 1
        || failure.released_count() != 1
        || adapter.release_requests != expected_release
    {
        return Err(String::from("aggregate release pass stopped early"));
    }
    (*failure)
        .retry(&mut adapter)
        .map_err(|retry| retry.to_string())?;
    if adapter.release_requests.first() == adapter.release_requests.last() {
        Ok(())
    } else {
        Err(String::from(
            "aggregate release retry changed failed mapping",
        ))
    }
}

#[test]
fn loaded_native_sequence_rejects_different_plan_before_runner()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let x86_plan = select_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let arm_plan = select_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::AArch64,
    )
    .map_err(|error| error.to_string())?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(805)?,
        native_executable_address(0x85_000)?,
    );
    let sequence = load_verified_native_sequence(&mut adapter, &x86_plan)
        .map_err(|error| error.to_string())?;
    let operations_after_load = adapter.operations.len();
    let mut memory = fixture.initial_memory.clone();
    let entry_memory = memory.clone();
    let mut output = fixture.initial_output.clone();
    let entry_output = output.clone();
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let Err(error) = execute_loaded_verified_native_sequence(
        &mut runner,
        &arm_plan,
        &sequence,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    ) else {
        return Err(String::from("cross-ISA loaded sequence was admitted"));
    };
    if error.admission_error()
        != Some(NativeLoadedSequenceAdmissionError::ExecutableIdentity {
            index: 0,
        })
        || error.completed_steps() != 0
        || error.resume_index() != 0
        || runner.calls != 0
        || memory != entry_memory
        || output != entry_output
        || adapter.operations.len() != operations_after_load
    {
        return Err(String::from(
            "loaded sequence prevalidation changed caller state",
        ));
    }
    release_native_executable_sequence(&mut adapter, sequence)
        .map_err(|release| release.to_string())
}

#[test]
fn loaded_native_sequence_restores_failed_second_step() -> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = select_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(806)?,
        native_executable_address(0x86_000)?,
    );
    let sequence = load_verified_native_sequence(&mut adapter, &plan)
        .map_err(|error| error.to_string())?;
    let operations_after_load = adapter.operations.len();
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let Err(error) = execute_loaded_verified_native_sequence(
        &mut runner,
        &plan,
        &sequence,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    ) else {
        return Err(String::from("loaded second-step failure was ignored"));
    };
    let runner_error = error
        .execution_failure()
        .and_then(|failure| failure.runner_error());
    if error.step_index() != 1
        || error.completed_steps() != 1
        || error.resume_index() != 1
        || runner_error != Some(&FakeNativeRunnerError::Call)
        || memory != fixture.first_memory
        || output != fixture.first_output
        || adapter.operations.len() != operations_after_load
    {
        return Err(String::from("loaded second-step rollback drifted"));
    }
    release_native_executable_sequence(&mut adapter, sequence)
        .map_err(|release| release.to_string())
}

fn selected_sequence_prefix(
    fixture: &NativeSequenceFixture,
    isa: HostIsa,
    steps: usize,
) -> Result<VerifiedDirectSequencePlan, String> {
    let programs = fixture
        .programs
        .get(..steps)
        .ok_or_else(|| String::from("sequence prefix exceeds fixture"))?;
    select_verified_direct_sequence(
        programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        isa,
    )
    .map_err(|error| error.to_string())
}

fn direct_sequence_mapped_bytes(
    plan: &VerifiedDirectSequencePlan,
) -> Result<usize, String> {
    plan.artifacts().iter().try_fold(0usize, |total, artifact| {
        let image = VerifiedDirectLoadImage::from_artifact_for_test(artifact)
            .map_err(|error| error.to_string())?;
        total
            .checked_add(image.allocation_len())
            .ok_or_else(|| String::from("sequence mapped-byte sum overflowed"))
    })
}

const fn executable_cache_usage_is_empty(
    cache: &NativeExecutableSequenceCache,
) -> bool {
    let usage = cache.usage();
    usage.entries() == 0 && usage.mappings() == 0 && usage.mapped_bytes() == 0
}

fn lease_acquire(
    cache: &mut NativeExecutableSequenceLeaseCache,
    adapter: &mut FakeNativeExecutableAdapter,
    plan: &VerifiedDirectSequencePlan,
) -> Result<NativeExecutableSequenceLease, String> {
    cache
        .ensure_plan(adapter, plan)
        .map(NativeExecutableSequenceLeaseCacheAcquisition::into_lease)
        .map_err(|failure| failure.to_string())
}

fn lease_fixture(
    limits: NativeExecutableSequenceCacheLimits,
    mapping_value: u64,
    base_value: usize,
) -> Result<LeaseCacheFixture, String> {
    Ok((
        NativeExecutableSequenceLeaseCache::with_limits(limits),
        FakeNativeExecutableAdapter::new(
            native_executable_mapping_id(mapping_value)?,
            native_executable_address(base_value)?,
        ),
    ))
}

fn ensure_executable_cache_plan(
    cache: &mut NativeExecutableSequenceCache,
    adapter: &mut FakeNativeExecutableAdapter,
    plan: &VerifiedDirectSequencePlan,
) -> Result<(), String> {
    cache
        .ensure_plan(adapter, plan)
        .map(|_entry| ())
        .map_err(|error| error.to_string())
}

fn nonzero_test_limit(
    value: usize,
    name: &str,
) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value).ok_or_else(|| format!("{name} missing"))
}

#[test]
fn executable_sequence_cache_inserts_hits_and_executes() -> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(900)?,
        native_executable_address(0x90_000)?,
    );
    let capacity = NonZeroUsize::new(2)
        .ok_or_else(|| String::from("cache capacity missing"))?;
    let mut cache = NativeExecutableSequenceCache::new(capacity);
    let first_mappings = {
        let entry = cache
            .ensure_plan(&mut adapter, &plan)
            .map_err(|error| error.to_string())?;
        if entry.disposition().is_hit()
            || entry.disposition().evicted_key().is_some()
            || entry.key().len() != 2
        {
            return Err(String::from("first loaded cache insertion drifted"));
        }
        entry
            .sequence()
            .executables()
            .iter()
            .map(|executable| executable.mapping().mapping_id())
            .collect::<Vec<_>>()
    };
    let operations_after_insert = adapter.operations.len();
    {
        let entry = cache
            .ensure_plan(&mut adapter, &plan)
            .map_err(|error| error.to_string())?;
        let hit_mappings = entry
            .sequence()
            .executables()
            .iter()
            .map(|executable| executable.mapping().mapping_id())
            .collect::<Vec<_>>();
        if entry.disposition() != &NativeExecutableSequenceCacheDisposition::Hit
            || hit_mappings != first_mappings
        {
            return Err(String::from("exact loaded cache hit drifted"));
        }
        assert_loaded_sequence_application(&fixture, &plan, entry.sequence())?;
    }
    if adapter.operations.len() != operations_after_insert
        || cache.len() != 1
        || !cache.contains_plan(&plan)
    {
        return Err(String::from("loaded cache hit touched adapter state"));
    }
    cache
        .release_all(&mut adapter)
        .map_err(|error| error.to_string())?;
    if cache.is_empty() && adapter.release_requests.len() == 2 {
        Ok(())
    } else {
        Err(String::from("loaded cache final release drifted"))
    }
}

#[test]
fn executable_sequence_cache_fifo_hit_does_not_refresh() -> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let third = selected_sequence_prefix(&fixture, HostIsa::AArch64, 2)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first);
    let second_key = NativeExecutableSequenceKey::from_plan(&second);
    let third_key = NativeExecutableSequenceKey::from_plan(&third);
    let capacity = NonZeroUsize::new(2)
        .ok_or_else(|| String::from("cache capacity missing"))?;
    let mut cache = NativeExecutableSequenceCache::new(capacity);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(901)?,
        native_executable_address(0x91_000)?,
    );
    ensure_executable_cache_plan(&mut cache, &mut adapter, &first)?;
    ensure_executable_cache_plan(&mut cache, &mut adapter, &second)?;
    let fifo_before_hit = cache.keys().cloned().collect::<Vec<_>>();
    let operations_before_hit = adapter.operations.len();
    {
        let hit = cache
            .ensure_plan(&mut adapter, &first)
            .map_err(|error| error.to_string())?;
        if !hit.disposition().is_hit() {
            return Err(String::from("FIFO reuse was not reported as hit"));
        }
    }
    if cache.keys().cloned().collect::<Vec<_>>() != fifo_before_hit
        || adapter.operations.len() != operations_before_hit
    {
        return Err(String::from(
            "cache hit refreshed FIFO or touched adapter",
        ));
    }
    {
        let inserted = cache
            .ensure_plan(&mut adapter, &third)
            .map_err(|error| error.to_string())?;
        if inserted.disposition().evicted_key() != Some(&first_key) {
            return Err(String::from("FIFO eviction removed the wrong key"));
        }
    }
    let final_keys = cache.keys().cloned().collect::<Vec<_>>();
    if final_keys != [second_key, third_key]
        || cache.contains_plan(&first)
        || !cache.contains_plan(&second)
        || !cache.contains_plan(&third)
    {
        return Err(String::from("FIFO cache state drifted after eviction"));
    }
    cache
        .release_all(&mut adapter)
        .map_err(|error| error.to_string())
}

#[test]
fn executable_sequence_cache_load_failure_preserves_entries()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::AArch64, 2)?;
    let second_key = NativeExecutableSequenceKey::from_plan(&second);
    let capacity = NonZeroUsize::new(1)
        .ok_or_else(|| String::from("cache capacity missing"))?;
    let mut cache = NativeExecutableSequenceCache::new(capacity);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(902)?,
        native_executable_address(0x92_000)?,
    );
    {
        let _entry = cache
            .ensure_plan(&mut adapter, &first)
            .map_err(|error| error.to_string())?;
    }
    let release_count = adapter.release_requests.len();
    let next_allocate = adapter.allocation_requests.len().saturating_add(1);
    adapter.failure_at =
        Some((FakeNativeAdapterOperation::Allocate, next_allocate));
    let Err(error) = cache.ensure_plan(&mut adapter, &second) else {
        return Err(String::from(
            "configured cache candidate load failure ignored",
        ));
    };
    if error.requested_key() != &second_key
        || error.load_failure().is_none()
        || error.evicted_key().is_some()
        || error.eviction_failure().is_some()
        || error.invariant_error().is_some()
        || error.candidate_cleanup_failure().is_some()
        || cache.len() != 1
        || !cache.contains_plan(&first)
        || cache.contains_plan(&second)
        || adapter.release_requests.len() != release_count
    {
        return Err(String::from(
            "failed candidate mutated loaded cache state",
        ));
    }
    adapter.failure_at = None;
    let operations_before_hit = adapter.operations.len();
    {
        let hit = cache
            .ensure_plan(&mut adapter, &first)
            .map_err(|failure| failure.to_string())?;
        if !hit.disposition().is_hit() {
            return Err(String::from("surviving cache entry was not reusable"));
        }
    }
    if adapter.operations.len() != operations_before_hit {
        return Err(String::from("surviving hit touched memory adapter"));
    }
    cache
        .release_all(&mut adapter)
        .map_err(|failure| failure.to_string())
}

#[test]
fn executable_sequence_cache_eviction_failure_retains_both_owners()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::AArch64, 2)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first);
    let second_key = NativeExecutableSequenceKey::from_plan(&second);
    let capacity = NonZeroUsize::new(1)
        .ok_or_else(|| String::from("cache capacity missing"))?;
    let mut cache = NativeExecutableSequenceCache::new(capacity);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(903)?,
        native_executable_address(0x93_000)?,
    );
    {
        let _entry = cache
            .ensure_plan(&mut adapter, &first)
            .map_err(|error| error.to_string())?;
    }
    adapter.release_failures_remaining = 3;
    let Err(error) = cache.ensure_plan(&mut adapter, &second) else {
        return Err(String::from("configured FIFO eviction failure ignored"));
    };
    let eviction = error.eviction_failure().ok_or_else(|| {
        String::from("FIFO eviction release ownership was lost")
    })?;
    let candidate = error
        .candidate_cleanup_failure()
        .ok_or_else(|| String::from("candidate cleanup ownership was lost"))?;
    if error.requested_key() != &second_key
        || error.evicted_key() != Some(&first_key)
        || error.load_failure().is_some()
        || error.invariant_error().is_some()
        || eviction.failed_count() != 2
        || candidate.failed_count() != 1
        || !cache.is_empty()
        || cache.contains_plan(&first)
        || cache.contains_plan(&second)
    {
        return Err(String::from(
            "failed eviction published invalid cache state",
        ));
    }
    let retained = (*error).into_release_failures();
    if retained.eviction_failure().is_none()
        || retained.candidate_failure().is_none()
    {
        return Err(String::from("failed eviction retry owners were lost"));
    }
    retained
        .retry(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    if adapter.release_requests.len() == 7 {
        Ok(())
    } else {
        Err(String::from("failed eviction retry count drifted"))
    }
}

#[test]
fn executable_sequence_cache_invalidation_retries_exact_mapping()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let mut artifact_cache = VerifiedDirectNativeCache::default();
    let plan = select_cached_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::AArch64),
        &mut artifact_cache,
    )
    .map_err(|error| error.to_string())?;
    let capacity = NonZeroUsize::new(1)
        .ok_or_else(|| String::from("cache capacity missing"))?;
    let mut cache = NativeExecutableSequenceCache::new(capacity);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(904)?,
        native_executable_address(0x94_000)?,
    );
    {
        let entry = cache
            .ensure_cached_plan(&mut adapter, &plan)
            .map_err(|error| error.to_string())?;
        if entry.key() != &NativeExecutableSequenceKey::from_cached_plan(&plan)
        {
            return Err(String::from("cached loaded sequence key drifted"));
        }
    }
    adapter.release_failure_at =
        Some(adapter.release_attempts.saturating_add(1));
    let Err(failure) = cache.invalidate_cached_plan(&mut adapter, &plan) else {
        return Err(String::from(
            "configured invalidation release failure ignored",
        ));
    };
    if failure.failed_count() != 1
        || failure.attempted_count() != 2
        || cache.contains_cached_plan(&plan)
        || !cache.is_empty()
    {
        return Err(String::from(
            "failed invalidation retained cache authority",
        ));
    }
    (*failure)
        .retry(&mut adapter)
        .map_err(|retry| retry.to_string())?;
    if cache
        .invalidate_cached_plan(&mut adapter, &plan)
        .map_err(|error| error.to_string())?
    {
        Err(String::from("missing invalidation reported removal"))
    } else {
        Ok(())
    }
}

#[test]
fn executable_sequence_cache_release_all_aggregates_failures()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::AArch64, 2)?;
    let capacity = NonZeroUsize::new(2)
        .ok_or_else(|| String::from("cache capacity missing"))?;
    let mut cache = NativeExecutableSequenceCache::new(capacity);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(905)?,
        native_executable_address(0x95_000)?,
    );
    ensure_executable_cache_plan(&mut cache, &mut adapter, &first)?;
    ensure_executable_cache_plan(&mut cache, &mut adapter, &second)?;
    adapter.release_failures_remaining = 2;
    let Err(failure) = cache.release_all(&mut adapter) else {
        return Err(String::from("configured cache release failures ignored"));
    };
    if failure.attempted_entries() != 2
        || failure.failed_entries() != 2
        || failure.released_entries() != 0
        || failure.retained_mappings() != 2
        || failure.failures().len() != 2
        || !cache.is_empty()
        || adapter.release_requests.len() != 3
    {
        return Err(String::from("cache release aggregation evidence drifted"));
    }
    (*failure)
        .retry(&mut adapter)
        .map_err(|retry| retry.to_string())?;
    if adapter.release_requests.len() == 5 {
        Ok(())
    } else {
        Err(String::from("cache release aggregate retry drifted"))
    }
}

#[test]
fn executable_sequence_cache_tracks_weighted_usage() -> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let mapped_bytes = direct_sequence_mapped_bytes(&plan)?;
    let entry_limit = nonzero_test_limit(2, "entry limit")?;
    let mapping_limit = nonzero_test_limit(3, "mapping limit")?;
    let doubled_bytes = mapped_bytes
        .checked_mul(2)
        .ok_or_else(|| String::from("mapped-byte limit overflowed"))?;
    let byte_limit = nonzero_test_limit(doubled_bytes, "mapped-byte limit")?;
    let limits = NativeExecutableSequenceCacheLimits::new(entry_limit)
        .with_mapped_byte_limit(byte_limit)
        .with_mapping_limit(mapping_limit);
    let mut cache = NativeExecutableSequenceCache::with_limits(limits);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(906)?,
        native_executable_address(0x96_000)?,
    );
    {
        let inserted = cache
            .ensure_plan(&mut adapter, &plan)
            .map_err(|error| error.to_string())?;
        if inserted.disposition().is_hit()
            || !inserted.disposition().evicted_keys().is_empty()
        {
            return Err(String::from("weighted insertion disposition drifted"));
        }
    }
    let inserted_usage = cache.usage();
    if cache.limits() != limits
        || inserted_usage.entries() != 1
        || inserted_usage.mappings() != 2
        || inserted_usage.mapped_bytes() != mapped_bytes
    {
        return Err(String::from("weighted insertion usage drifted"));
    }
    let operations_after_insert = adapter.operations.len();
    {
        let hit = cache
            .ensure_plan(&mut adapter, &plan)
            .map_err(|error| error.to_string())?;
        if !hit.disposition().is_hit() {
            return Err(String::from("weighted exact hit was not reused"));
        }
    }
    if cache.usage() != inserted_usage
        || adapter.operations.len() != operations_after_insert
    {
        return Err(String::from(
            "weighted hit changed usage or adapter state",
        ));
    }
    if !cache
        .invalidate_plan(&mut adapter, &plan)
        .map_err(|error| error.to_string())?
        || !executable_cache_usage_is_empty(&cache)
        || adapter.release_requests.len() != 2
    {
        return Err(String::from("weighted invalidation accounting drifted"));
    }
    Ok(())
}

#[test]
fn executable_sequence_cache_usage_overflow_is_transactional()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let base_value = 0x98_000usize;
    let first_mapped_len = usize::MAX
        .checked_sub(base_value)
        .ok_or_else(|| String::from("first mapped length underflowed"))?;
    let second_mapped_len = base_value
        .checked_add(1)
        .ok_or_else(|| String::from("second mapped length overflowed"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(9061)?,
        native_executable_address(base_value)?,
    )
    .with_mapped_len_overrides(vec![first_mapped_len, second_mapped_len]);
    let capacity = nonzero_test_limit(2, "entry limit")?;
    let mut cache = NativeExecutableSequenceCache::new(capacity);
    ensure_executable_cache_plan(&mut cache, &mut adapter, &first)?;
    let retained_usage = cache.usage();

    let Err(error) = cache.ensure_plan(&mut adapter, &second) else {
        return Err(String::from("cache usage overflow was admitted"));
    };
    if error.capacity_error()
        != Some(NativeExecutableSequenceCacheCapacityError::WeightOverflow)
        || error.candidate_cleanup_failure().is_some()
        || !error.evicted_keys().is_empty()
        || cache.usage() != retained_usage
        || cache.len() != 1
        || !cache.contains_plan(&first)
        || cache.contains_plan(&second)
        || adapter.release_requests.len() != 1
    {
        return Err(String::from(
            "cache usage overflow mutated retained authority",
        ));
    }
    cache
        .release_all(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    if adapter.release_requests.len() == 2 {
        Ok(())
    } else {
        Err(String::from("cache usage overflow cleanup drifted"))
    }
}

#[test]
fn executable_sequence_cache_rejects_mapping_oversize() -> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let entry_limit = nonzero_test_limit(3, "entry limit")?;
    let mapping_limit = nonzero_test_limit(1, "mapping limit")?;
    let limits = NativeExecutableSequenceCacheLimits::new(entry_limit)
        .with_mapping_limit(mapping_limit);
    let mut cache = NativeExecutableSequenceCache::with_limits(limits);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(907)?,
        native_executable_address(0x97_000)?,
    );
    let Err(error) = cache.ensure_plan(&mut adapter, &plan) else {
        return Err(String::from("oversized mapping candidate was admitted"));
    };
    let expected = NativeExecutableSequenceCacheCapacityError::Mappings {
        limit: mapping_limit,
        required: 2,
    };
    if error.capacity_error() != Some(expected)
        || error.candidate_cleanup_failure().is_some()
        || !error.evicted_keys().is_empty()
        || error.eviction_failure().is_some()
        || error.load_failure().is_some()
        || !cache.is_empty()
        || !executable_cache_usage_is_empty(&cache)
        || adapter.release_requests.len() != 2
    {
        return Err(String::from("mapping oversize rejection drifted"));
    }
    Ok(())
}

#[test]
fn executable_sequence_cache_rejects_byte_oversize() -> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = selected_sequence_prefix(&fixture, HostIsa::AArch64, 2)?;
    let mapped_bytes = direct_sequence_mapped_bytes(&plan)?;
    let entry_limit = nonzero_test_limit(3, "entry limit")?;
    let byte_limit = mapped_bytes
        .checked_sub(1)
        .and_then(NonZeroUsize::new)
        .ok_or_else(|| String::from("mapped-byte limit missing"))?;
    let limits = NativeExecutableSequenceCacheLimits::new(entry_limit)
        .with_mapped_byte_limit(byte_limit);
    let mut cache = NativeExecutableSequenceCache::with_limits(limits);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(908)?,
        native_executable_address(0x98_000)?,
    );
    let Err(error) = cache.ensure_plan(&mut adapter, &plan) else {
        return Err(String::from("oversized byte candidate was admitted"));
    };
    let expected = NativeExecutableSequenceCacheCapacityError::MappedBytes {
        limit: byte_limit,
        required: mapped_bytes,
    };
    if error.capacity_error() != Some(expected)
        || error.candidate_cleanup_failure().is_some()
        || !error.evicted_keys().is_empty()
        || error.eviction_failure().is_some()
        || error.load_failure().is_some()
        || !cache.is_empty()
        || !executable_cache_usage_is_empty(&cache)
        || adapter.release_requests.len() != 2
    {
        return Err(String::from("mapped-byte oversize rejection drifted"));
    }
    Ok(())
}

#[test]
fn executable_sequence_cache_evicts_multiple_for_mapping_limit()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let candidate = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first);
    let second_key = NativeExecutableSequenceKey::from_plan(&second);
    let candidate_key = NativeExecutableSequenceKey::from_plan(&candidate);
    let candidate_bytes = direct_sequence_mapped_bytes(&candidate)?;
    let entry_limit = nonzero_test_limit(3, "entry limit")?;
    let mapping_limit = nonzero_test_limit(2, "mapping limit")?;
    let limits = NativeExecutableSequenceCacheLimits::new(entry_limit)
        .with_mapping_limit(mapping_limit);
    let mut cache = NativeExecutableSequenceCache::with_limits(limits);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(909)?,
        native_executable_address(0x99_000)?,
    );
    ensure_executable_cache_plan(&mut cache, &mut adapter, &first)?;
    ensure_executable_cache_plan(&mut cache, &mut adapter, &second)?;
    if cache.usage().entries() != 2 || cache.usage().mappings() != 2 {
        return Err(String::from("mapping-limit setup usage drifted"));
    }
    let evicted = {
        let entry = cache
            .ensure_plan(&mut adapter, &candidate)
            .map_err(|error| error.to_string())?;
        entry.disposition().evicted_keys().to_vec()
    };
    if evicted != [first_key, second_key]
        || cache.keys().cloned().collect::<Vec<_>>() != [candidate_key]
        || cache.usage().entries() != 1
        || cache.usage().mappings() != 2
        || cache.usage().mapped_bytes() != candidate_bytes
        || adapter.release_requests.len() != 2
    {
        return Err(String::from("mapping-limit multi-eviction drifted"));
    }
    cache
        .release_all(&mut adapter)
        .map_err(|error| error.to_string())?;
    if executable_cache_usage_is_empty(&cache)
        && adapter.release_requests.len() == 4
    {
        Ok(())
    } else {
        Err(String::from("mapping-limit final cleanup drifted"))
    }
}

#[test]
fn executable_sequence_cache_evicts_multiple_for_byte_limit()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let x86_candidate = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let arm_candidate =
        selected_sequence_prefix(&fixture, HostIsa::AArch64, 2)?;
    let x86_bytes = direct_sequence_mapped_bytes(&x86_candidate)?;
    let arm_bytes = direct_sequence_mapped_bytes(&arm_candidate)?;
    let (candidate, candidate_bytes) = if x86_bytes >= arm_bytes {
        (x86_candidate, x86_bytes)
    } else {
        (arm_candidate, arm_bytes)
    };
    let first_key = NativeExecutableSequenceKey::from_plan(&first);
    let second_key = NativeExecutableSequenceKey::from_plan(&second);
    let candidate_key = NativeExecutableSequenceKey::from_plan(&candidate);
    let entry_limit = nonzero_test_limit(3, "entry limit")?;
    let byte_limit = nonzero_test_limit(candidate_bytes, "mapped-byte limit")?;
    let limits = NativeExecutableSequenceCacheLimits::new(entry_limit)
        .with_mapped_byte_limit(byte_limit);
    let mut cache = NativeExecutableSequenceCache::with_limits(limits);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(910)?,
        native_executable_address(0x9a_000)?,
    );
    {
        let _entry = cache
            .ensure_plan(&mut adapter, &first)
            .map_err(|error| error.to_string())?;
    }
    {
        let _entry = cache
            .ensure_plan(&mut adapter, &second)
            .map_err(|error| error.to_string())?;
    }
    let evicted = {
        let entry = cache
            .ensure_plan(&mut adapter, &candidate)
            .map_err(|error| error.to_string())?;
        entry.disposition().evicted_keys().to_vec()
    };
    if evicted != [first_key, second_key]
        || cache.keys().cloned().collect::<Vec<_>>() != [candidate_key]
        || cache.usage().entries() != 1
        || cache.usage().mappings() != 2
        || cache.usage().mapped_bytes() != candidate_bytes
        || adapter.release_requests.len() != 2
    {
        return Err(String::from("byte-limit multi-eviction drifted"));
    }
    cache
        .release_all(&mut adapter)
        .map_err(|error| error.to_string())?;
    if executable_cache_usage_is_empty(&cache)
        && adapter.release_requests.len() == 4
    {
        Ok(())
    } else {
        Err(String::from("byte-limit final cleanup drifted"))
    }
}

#[test]
fn executable_sequence_cache_retains_second_eviction_failure()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let candidate = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first);
    let second_key = NativeExecutableSequenceKey::from_plan(&second);
    let candidate_key = NativeExecutableSequenceKey::from_plan(&candidate);
    let entry_limit = nonzero_test_limit(3, "entry limit")?;
    let mapping_limit = nonzero_test_limit(2, "mapping limit")?;
    let limits = NativeExecutableSequenceCacheLimits::new(entry_limit)
        .with_mapping_limit(mapping_limit);
    let mut cache = NativeExecutableSequenceCache::with_limits(limits);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(911)?,
        native_executable_address(0x9b_000)?,
    );
    ensure_executable_cache_plan(&mut cache, &mut adapter, &first)?;
    ensure_executable_cache_plan(&mut cache, &mut adapter, &second)?;
    adapter.release_failure_at =
        Some(adapter.release_attempts.saturating_add(2));
    let Err(error) = cache.ensure_plan(&mut adapter, &candidate) else {
        return Err(String::from("second weighted eviction failure ignored"));
    };
    let expected_keys = [first_key, second_key];
    let eviction = error.eviction_failure().ok_or_else(|| {
        String::from("second weighted eviction ownership was lost")
    })?;
    if error.requested_key() != &candidate_key
        || error.evicted_keys() != expected_keys
        || error.capacity_error().is_some()
        || error.candidate_cleanup_failure().is_some()
        || error.load_failure().is_some()
        || eviction.attempted_count() != 1
        || eviction.failed_count() != 1
        || !cache.is_empty()
        || !executable_cache_usage_is_empty(&cache)
        || adapter.release_requests.len() != 4
    {
        return Err(String::from(
            "second weighted eviction failure evidence drifted",
        ));
    }
    let retained = (*error).into_release_failures();
    if retained.candidate_failure().is_some()
        || retained.eviction_failure().is_none()
    {
        return Err(String::from(
            "second weighted eviction retry ownership drifted",
        ));
    }
    retained
        .retry(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    if adapter.release_requests.len() == 5 {
        Ok(())
    } else {
        Err(String::from("second weighted eviction retry drifted"))
    }
}

#[test]
fn executable_sequence_cache_expands_limits_without_eviction()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let old_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(1, "entry limit")?,
    );
    let mut cache = NativeExecutableSequenceCache::with_limits(old_limits);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(912)?,
        native_executable_address(0x9c_000)?,
    );
    ensure_executable_cache_plan(&mut cache, &mut adapter, &plan)?;
    let usage = cache.usage();
    let byte_limit = nonzero_test_limit(
        usage.mapped_bytes().saturating_mul(2),
        "mapped-byte limit",
    )?;
    let new_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(3, "entry limit")?,
    )
    .with_mapped_byte_limit(byte_limit)
    .with_mapping_limit(nonzero_test_limit(2, "mapping limit")?);
    let operations = adapter.operations.len();
    let report = cache
        .reconfigure_limits(&mut adapter, new_limits)
        .map_err(|error| error.to_string())?;
    if !report.evicted_keys().is_empty()
        || report.limit_transition() != (old_limits, new_limits)
        || cache.limits() != new_limits
        || cache.usage() != usage
        || !cache.contains_plan(&plan)
        || adapter.operations.len() != operations
    {
        return Err(String::from("limit expansion changed cache state"));
    }
    cache
        .release_all(&mut adapter)
        .map_err(|error| error.to_string())
}

#[test]
fn executable_sequence_cache_shrinks_entry_limit_fifo() -> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let third = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first);
    let second_key = NativeExecutableSequenceKey::from_plan(&second);
    let third_key = NativeExecutableSequenceKey::from_plan(&third);
    let third_bytes = direct_sequence_mapped_bytes(&third)?;
    let old_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(3, "entry limit")?,
    );
    let new_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(1, "entry limit")?,
    );
    let mut cache = NativeExecutableSequenceCache::with_limits(old_limits);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(913)?,
        native_executable_address(0x9d_000)?,
    );
    ensure_executable_cache_plan(&mut cache, &mut adapter, &first)?;
    ensure_executable_cache_plan(&mut cache, &mut adapter, &second)?;
    ensure_executable_cache_plan(&mut cache, &mut adapter, &third)?;
    let report = cache
        .reconfigure_limits(&mut adapter, new_limits)
        .map_err(|error| error.to_string())?;
    if report.evicted_keys() != [first_key, second_key]
        || report.limit_transition() != (old_limits, new_limits)
        || cache.keys().cloned().collect::<Vec<_>>() != [third_key]
        || cache.usage().entries() != 1
        || cache.usage().mappings() != 2
        || cache.usage().mapped_bytes() != third_bytes
        || adapter.release_requests.len() != 2
    {
        return Err(String::from("entry-limit reconfiguration drifted"));
    }
    cache
        .release_all(&mut adapter)
        .map_err(|error| error.to_string())
}

#[test]
fn executable_sequence_cache_shrinks_mapping_limit_fifo() -> Result<(), String>
{
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let third = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let expected = [
        NativeExecutableSequenceKey::from_plan(&first),
        NativeExecutableSequenceKey::from_plan(&second),
    ];
    let old_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(3, "entry limit")?,
    );
    let new_limits =
        old_limits.with_mapping_limit(nonzero_test_limit(2, "mapping limit")?);
    let mut cache = NativeExecutableSequenceCache::with_limits(old_limits);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(914)?,
        native_executable_address(0x9e_000)?,
    );
    ensure_executable_cache_plan(&mut cache, &mut adapter, &first)?;
    ensure_executable_cache_plan(&mut cache, &mut adapter, &second)?;
    ensure_executable_cache_plan(&mut cache, &mut adapter, &third)?;
    let report = cache
        .reconfigure_limits(&mut adapter, new_limits)
        .map_err(|error| error.to_string())?;
    if report.evicted_keys() != expected
        || report.limit_transition() != (old_limits, new_limits)
        || cache.len() != 1
        || !cache.contains_plan(&third)
        || cache.usage().mappings() != 2
        || adapter.release_requests.len() != 2
    {
        return Err(String::from("mapping-limit reconfiguration drifted"));
    }
    cache
        .release_all(&mut adapter)
        .map_err(|error| error.to_string())
}

#[test]
fn executable_sequence_cache_shrinks_byte_limit_fifo() -> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let third = selected_sequence_prefix(&fixture, HostIsa::AArch64, 2)?;
    let expected = [
        NativeExecutableSequenceKey::from_plan(&first),
        NativeExecutableSequenceKey::from_plan(&second),
    ];
    let third_bytes = direct_sequence_mapped_bytes(&third)?;
    let old_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(3, "entry limit")?,
    );
    let new_limits = old_limits.with_mapped_byte_limit(nonzero_test_limit(
        third_bytes,
        "mapped-byte limit",
    )?);
    let mut cache = NativeExecutableSequenceCache::with_limits(old_limits);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(915)?,
        native_executable_address(0x9f_000)?,
    );
    ensure_executable_cache_plan(&mut cache, &mut adapter, &first)?;
    ensure_executable_cache_plan(&mut cache, &mut adapter, &second)?;
    ensure_executable_cache_plan(&mut cache, &mut adapter, &third)?;
    let report = cache
        .reconfigure_limits(&mut adapter, new_limits)
        .map_err(|error| error.to_string())?;
    if report.evicted_keys() != expected
        || report.limit_transition() != (old_limits, new_limits)
        || cache.len() != 1
        || !cache.contains_plan(&third)
        || cache.usage().mapped_bytes() != third_bytes
        || adapter.release_requests.len() != 2
    {
        return Err(String::from("byte-limit reconfiguration drifted"));
    }
    cache
        .release_all(&mut adapter)
        .map_err(|error| error.to_string())
}

#[test]
fn executable_sequence_cache_reconfiguration_retries_failed_eviction()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let third = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let expected = [
        NativeExecutableSequenceKey::from_plan(&first),
        NativeExecutableSequenceKey::from_plan(&second),
    ];
    let old_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(3, "entry limit")?,
    );
    let new_limits =
        old_limits.with_mapping_limit(nonzero_test_limit(2, "mapping limit")?);
    let mut cache = NativeExecutableSequenceCache::with_limits(old_limits);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(916)?,
        native_executable_address(0xa0_000)?,
    );
    ensure_executable_cache_plan(&mut cache, &mut adapter, &first)?;
    ensure_executable_cache_plan(&mut cache, &mut adapter, &second)?;
    ensure_executable_cache_plan(&mut cache, &mut adapter, &third)?;
    adapter.release_failure_at =
        Some(adapter.release_attempts.saturating_add(2));
    let Err(error) = cache.reconfigure_limits(&mut adapter, new_limits) else {
        return Err(String::from("configured reconfiguration failure ignored"));
    };
    if error.evicted_keys() != expected
        || error.limit_transition() != (old_limits, new_limits)
        || error.invariant_error().is_some()
        || error.release_failure().is_none()
        || cache.limits() != old_limits
        || cache.len() != 1
        || !cache.contains_plan(&third)
        || cache.usage().mappings() != 2
        || adapter.release_requests.len() != 2
    {
        return Err(String::from("failed reconfiguration evidence drifted"));
    }
    let release = (*error)
        .into_release_failure()
        .ok_or_else(|| String::from("reconfiguration release owner missing"))?;
    release
        .retry(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    let operations = adapter.operations.len();
    let report = cache
        .reconfigure_limits(&mut adapter, new_limits)
        .map_err(|failure| failure.to_string())?;
    if !report.evicted_keys().is_empty()
        || report.limit_transition() != (old_limits, new_limits)
        || cache.limits() != new_limits
        || adapter.operations.len() != operations
    {
        return Err(String::from("reconfiguration retry publication drifted"));
    }
    cache
        .release_all(&mut adapter)
        .map_err(|failure| failure.to_string())
}

#[test]
fn executable_sequence_lease_cache_shares_hits_across_threads()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let key = NativeExecutableSequenceKey::from_plan(&plan);
    let capacity = nonzero_test_limit(2, "lease cache capacity")?;
    let mut cache = NativeExecutableSequenceLeaseCache::new(capacity);
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(917)?,
        native_executable_address(0xa1_000)?,
    );
    let first = {
        let acquisition = cache
            .ensure_plan(&mut adapter, &plan)
            .map_err(|error| error.to_string())?;
        if acquisition.disposition().is_hit()
            || !acquisition.disposition().evicted_keys().is_empty()
        {
            return Err(String::from("first lease acquisition drifted"));
        }
        acquisition.into_lease()
    };
    let operations = adapter.operations.len();
    let second = {
        let acquisition = cache
            .ensure_plan(&mut adapter, &plan)
            .map_err(|error| error.to_string())?;
        if acquisition.disposition()
            != &NativeExecutableSequenceLeaseCacheDisposition::Hit
        {
            return Err(String::from("exact lease hit was not reused"));
        }
        acquisition.into_lease()
    };
    if !first.shares_resident_with(&second)
        || first.key() != &key
        || first.strong_owner_count() != 3
        || adapter.operations.len() != operations
    {
        return Err(String::from("shared lease identity drifted"));
    }
    let thread_lease = second.clone();
    let length = thread::spawn(move || thread_lease.sequence().len())
        .join()
        .map_err(|_panic| String::from("lease reader thread panicked"))?;
    if length != 2 || first.strong_owner_count() != 3 {
        return Err(String::from("cross-thread lease ownership drifted"));
    }
    drop(second);
    drop(first);
    let report = cache
        .release_all(&mut adapter)
        .map_err(|error| error.to_string())?;
    if report.released_keys() == [key]
        && report.retained_keys().is_empty()
        && cache.is_empty()
        && adapter.release_requests.len() == 2
    {
        Ok(())
    } else {
        Err(String::from("shared lease final release drifted"))
    }
}

#[test]
fn executable_sequence_lease_cache_blocks_weighted_resident()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first_plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let second_plan = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first_plan);
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        3,
        "entry limit",
    )?)
    .with_mapping_limit(nonzero_test_limit(2, "mapping limit")?);
    let (mut cache, mut adapter) = lease_fixture(limits, 918, 0xa2_000)?;
    let first_lease = cache
        .ensure_plan(&mut adapter, &first_plan)
        .map_err(|error| error.to_string())?
        .into_lease();
    let Err(error) = cache.ensure_plan(&mut adapter, &second_plan) else {
        return Err(String::from("leased resident exceeded mapping limit"));
    };
    let block = error
        .block()
        .ok_or_else(|| String::from("lease capacity blockage missing"))?;
    if error.evicted_keys() != [first_key.clone()]
        || error.retired_keys() != [first_key.clone()]
        || block.limits() != limits
        || block.retired_keys() != [first_key.clone()]
        || block.usage() != cache.usage()
        || cache.active_len() != 0
        || cache.retired_len() != 1
        || cache.usage().entries() != 1
        || cache.usage().mappings() != 2
        || adapter.release_requests.len() != 1
    {
        return Err(String::from("leased resident blockage evidence drifted"));
    }
    drop(first_lease);
    let report = cache
        .reconcile_retired(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    if report.released_keys() != [first_key]
        || !report.retained_keys().is_empty()
        || !cache.is_empty()
        || adapter.release_requests.len() != 3
    {
        return Err(String::from("leased resident reconciliation drifted"));
    }
    let second_lease = lease_acquire(&mut cache, &mut adapter, &second_plan)?;
    drop(second_lease);
    let final_report = cache
        .release_all(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    if final_report.retained_keys().is_empty()
        && adapter.release_requests.len() == 4
    {
        Ok(())
    } else {
        Err(String::from("weighted lease retry insertion drifted"))
    }
}

#[test]
fn executable_sequence_lease_cache_mixes_retirement_and_release()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first_plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second_plan = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let third_plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first_plan);
    let second_key = NativeExecutableSequenceKey::from_plan(&second_plan);
    let third_key = NativeExecutableSequenceKey::from_plan(&third_plan);
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        2,
        "lease cache capacity",
    )?);
    let (mut cache, mut adapter) = lease_fixture(limits, 919, 0xa3_000)?;
    let first_lease = lease_acquire(&mut cache, &mut adapter, &first_plan)?;
    let second_lease = lease_acquire(&mut cache, &mut adapter, &second_plan)?;
    drop(second_lease);
    let third_acquisition = cache
        .ensure_plan(&mut adapter, &third_plan)
        .map_err(|failure| failure.to_string())?;
    if third_acquisition.disposition().evicted_keys()
        != [first_key.clone(), second_key]
        || third_acquisition.disposition().retired_keys() != [first_key.clone()]
        || cache.keys().cloned().collect::<Vec<_>>() != [third_key]
        || cache.retired_keys().cloned().collect::<Vec<_>>()
            != [first_key.clone()]
        || cache.active_len() != 1
        || cache.retired_len() != 1
        || cache.resident_len() != 2
        || cache.usage().entries() != 2
        || cache.usage().mappings() != 3
        || adapter.release_requests.len() != 1
    {
        return Err(String::from("mixed lease eviction state drifted"));
    }
    let third_lease = third_acquisition.into_lease();
    drop(first_lease);
    let report = cache
        .reconcile_retired(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    if report.released_keys() != [first_key]
        || !report.retained_keys().is_empty()
        || cache.resident_len() != 1
        || adapter.release_requests.len() != 2
    {
        return Err(String::from("mixed lease retirement cleanup drifted"));
    }
    drop(third_lease);
    let final_report = cache
        .release_all(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    if final_report.retained_keys().is_empty()
        && cache.is_empty()
        && adapter.release_requests.len() == 4
    {
        Ok(())
    } else {
        Err(String::from("mixed lease final release drifted"))
    }
}

#[test]
fn executable_sequence_lease_cache_invalidation_waits_for_all_leases()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let key = NativeExecutableSequenceKey::from_plan(&plan);
    let mut cache = NativeExecutableSequenceLeaseCache::new(
        nonzero_test_limit(2, "lease cache capacity")?,
    );
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(920)?,
        native_executable_address(0xa4_000)?,
    );
    let first = cache
        .ensure_plan(&mut adapter, &plan)
        .map_err(|failure| failure.to_string())?
        .into_lease();
    let second = first.clone();
    let invalidation = cache
        .invalidate_plan(&mut adapter, &plan)
        .map_err(|failure| failure.to_string())?;
    if invalidation
        != (NativeExecutableSequenceLeaseCacheInvalidation::Retired {
            leases: 2,
        })
        || cache.contains_plan(&plan)
        || cache.active_len() != 0
        || cache.retired_len() != 1
        || !adapter.release_requests.is_empty()
    {
        return Err(String::from("leased invalidation did not retire exactly"));
    }
    let first_report = cache
        .return_lease(&mut adapter, first)
        .map_err(|failure| failure.to_string())?;
    if !first_report.released_keys().is_empty()
        || first_report.retained_keys() != [key.clone()]
        || cache.retired_len() != 1
        || !adapter.release_requests.is_empty()
    {
        return Err(String::from("first lease return released too early"));
    }
    let second_report = cache
        .return_lease(&mut adapter, second)
        .map_err(|failure| failure.to_string())?;
    if second_report.released_keys() != [key]
        || !second_report.retained_keys().is_empty()
        || !cache.is_empty()
        || adapter.release_requests.len() != 1
        || cache
            .invalidate_plan(&mut adapter, &plan)
            .map_err(|failure| failure.to_string())?
            != NativeExecutableSequenceLeaseCacheInvalidation::Missing
    {
        return Err(String::from("final lease return reconciliation drifted"));
    }
    Ok(())
}

#[test]
fn executable_sequence_lease_cache_release_all_retains_live_lease()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first_plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second_plan = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first_plan);
    let second_key = NativeExecutableSequenceKey::from_plan(&second_plan);
    let mut cache = NativeExecutableSequenceLeaseCache::new(
        nonzero_test_limit(2, "lease cache capacity")?,
    );
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(921)?,
        native_executable_address(0xa5_000)?,
    );
    let first_lease = lease_acquire(&mut cache, &mut adapter, &first_plan)?;
    let second_lease = lease_acquire(&mut cache, &mut adapter, &second_plan)?;
    drop(second_lease);
    let report = cache
        .release_all(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    if report.released_keys() != [second_key]
        || report.retained_keys() != [first_key.clone()]
        || cache.active_len() != 0
        || cache.retired_len() != 1
        || cache.usage().entries() != 1
        || adapter.release_requests.len() != 1
    {
        return Err(String::from("lease-aware release_all evidence drifted"));
    }
    drop(first_lease);
    let final_report = cache
        .reconcile_retired(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    if final_report.released_keys() == [first_key]
        && final_report.retained_keys().is_empty()
        && cache.is_empty()
        && adapter.release_requests.len() == 2
    {
        Ok(())
    } else {
        Err(String::from("lease-aware deferred release drifted"))
    }
}

#[test]
fn executable_sequence_lease_cache_retains_eviction_cleanup_failures()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first_plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second_plan = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first_plan);
    let second_key = NativeExecutableSequenceKey::from_plan(&second_plan);
    let mut cache = NativeExecutableSequenceLeaseCache::new(
        nonzero_test_limit(1, "lease cache capacity")?,
    );
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(922)?,
        native_executable_address(0xa6_000)?,
    );
    let first_lease = lease_acquire(&mut cache, &mut adapter, &first_plan)?;
    drop(first_lease);
    adapter.release_failures_remaining = 2;
    let Err(error) = cache.ensure_plan(&mut adapter, &second_plan) else {
        return Err(String::from("configured leased eviction failure ignored"));
    };
    if error.requested_key() != &second_key
        || error.evicted_keys() != [first_key.clone()]
        || !error.retired_keys().is_empty()
        || error.release_failure().is_none()
        || error.candidate_cleanup_failure().is_none()
        || error.block().is_some()
        || !cache.is_empty()
        || cache.usage().entries() != 0
        || adapter.release_requests.len() != 2
    {
        return Err(String::from("leased eviction failure evidence drifted"));
    }
    let report = (*error)
        .into_release_failures()
        .retry(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    if report.released_keys() == [first_key, second_key]
        && report.retained_keys().is_empty()
        && adapter.release_requests.len() == 4
    {
        Ok(())
    } else {
        Err(String::from("leased eviction cleanup retry drifted"))
    }
}

#[test]
fn executable_sequence_lease_cache_reconciliation_aggregates_failures()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first_plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second_plan = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first_plan);
    let second_key = NativeExecutableSequenceKey::from_plan(&second_plan);
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        2,
        "lease cache capacity",
    )?);
    let (mut cache, mut adapter) = lease_fixture(limits, 923, 0xa7_000)?;
    let first_lease = lease_acquire(&mut cache, &mut adapter, &first_plan)?;
    let second_lease = lease_acquire(&mut cache, &mut adapter, &second_plan)?;
    if cache
        .invalidate_plan(&mut adapter, &first_plan)
        .map_err(|failure| failure.to_string())?
        != (NativeExecutableSequenceLeaseCacheInvalidation::Retired {
            leases: 1,
        })
        || cache
            .invalidate_plan(&mut adapter, &second_plan)
            .map_err(|failure| failure.to_string())?
            != (NativeExecutableSequenceLeaseCacheInvalidation::Retired {
                leases: 1,
            })
    {
        return Err(String::from("aggregate reconciliation setup drifted"));
    }
    drop(first_lease);
    drop(second_lease);
    adapter.release_failures_remaining = 2;
    let Err(failure) = cache.reconcile_retired(&mut adapter) else {
        return Err(String::from("configured reconciliation failures ignored"));
    };
    let failed_keys = failure
        .failures()
        .iter()
        .map(|entry| entry.key().clone())
        .collect::<Vec<_>>();
    if failed_keys != [first_key.clone(), second_key.clone()]
        || !failure.released_keys().is_empty()
        || !failure.retained_keys().is_empty()
        || !cache.is_empty()
        || cache.usage().entries() != 0
        || adapter.release_requests.len() != 2
    {
        return Err(String::from("aggregate reconciliation evidence drifted"));
    }
    let report = (*failure)
        .retry(&mut adapter)
        .map_err(|retry| retry.to_string())?;
    if report.released_keys() == [first_key, second_key]
        && report.retained_keys().is_empty()
        && adapter.release_requests.len() == 4
    {
        Ok(())
    } else {
        Err(String::from("aggregate reconciliation retry drifted"))
    }
}

#[test]
fn executable_sequence_lease_cache_reconfigures_expansion_with_retired()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first);
    let second_key = NativeExecutableSequenceKey::from_plan(&second);
    let old_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(2, "entry limit")?,
    );
    let new_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(3, "entry limit")?,
    );
    let (mut cache, mut adapter) = lease_fixture(old_limits, 973, 0xe7_000)?;
    let first_lease = lease_acquire(&mut cache, &mut adapter, &first)?;
    let second_lease = lease_acquire(&mut cache, &mut adapter, &second)?;
    drop(second_lease);
    let invalidation = cache
        .invalidate_plan(&mut adapter, &first)
        .map_err(|failure| failure.to_string())?;
    let operations = adapter.operations.len();
    let report = cache
        .reconfigure_limits(&mut adapter, new_limits)
        .map_err(|failure| failure.to_string())?;
    if invalidation
        != (NativeExecutableSequenceLeaseCacheInvalidation::Retired {
            leases: 1,
        })
        || !report.evicted_keys().is_empty()
        || !report.retired_keys().is_empty()
        || report.limit_transition() != (old_limits, new_limits)
        || cache.keys().cloned().collect::<Vec<_>>() != [second_key]
        || cache.retired_keys().cloned().collect::<Vec<_>>() != [first_key]
        || cache.limits() != new_limits
        || cache.usage().entries() != 2
        || adapter.operations.len() != operations
    {
        return Err(String::from("leased expansion changed resident state"));
    }
    drop(first_lease);
    cache
        .release_all(&mut adapter)
        .map(|_report| ())
        .map_err(|failure| failure.to_string())
}

#[test]
fn executable_sequence_lease_cache_reconfigures_entry_fifo()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let third = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first);
    let second_key = NativeExecutableSequenceKey::from_plan(&second);
    let third_key = NativeExecutableSequenceKey::from_plan(&third);
    let old_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(3, "entry limit")?,
    );
    let new_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(1, "entry limit")?,
    );
    let (mut cache, mut adapter) = lease_fixture(old_limits, 974, 0xe8_000)?;
    drop(lease_acquire(&mut cache, &mut adapter, &first)?);
    drop(lease_acquire(&mut cache, &mut adapter, &second)?);
    drop(lease_acquire(&mut cache, &mut adapter, &third)?);
    let report = cache
        .reconfigure_limits(&mut adapter, new_limits)
        .map_err(|failure| failure.to_string())?;
    if report.evicted_keys() != [first_key, second_key]
        || !report.retired_keys().is_empty()
        || report.limit_transition() != (old_limits, new_limits)
        || cache.keys().cloned().collect::<Vec<_>>() != [third_key]
        || cache.active_len() != 1
        || cache.retired_len() != 0
        || cache.usage().entries() != 1
        || cache.usage().mappings() != 2
        || adapter.release_requests.len() != 2
    {
        return Err(String::from("leased entry shrink FIFO drifted"));
    }
    cache
        .release_all(&mut adapter)
        .map(|_report| ())
        .map_err(|failure| failure.to_string())
}

#[test]
fn executable_sequence_lease_cache_reconfiguration_blocks_live_entries()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first);
    let second_key = NativeExecutableSequenceKey::from_plan(&second);
    let old_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(2, "entry limit")?,
    );
    let new_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(1, "entry limit")?,
    );
    let (mut cache, mut adapter) = lease_fixture(old_limits, 975, 0xe9_000)?;
    let first_lease = lease_acquire(&mut cache, &mut adapter, &first)?;
    let second_lease = lease_acquire(&mut cache, &mut adapter, &second)?;
    let Err(failure) = cache.reconfigure_limits(&mut adapter, new_limits)
    else {
        return Err(String::from("live entry shrink unexpectedly published"));
    };
    let block = failure
        .block()
        .ok_or_else(|| String::from("entry shrink lease block missing"))?;
    if failure.evicted_keys() != [first_key.clone(), second_key.clone()]
        || failure.retired_keys() != [first_key.clone(), second_key.clone()]
        || failure.limit_transition() != (old_limits, new_limits)
        || block.limits() != new_limits
        || block.retired_keys() != [first_key, second_key]
        || block.usage() != cache.usage()
        || failure.release_failure().is_some()
        || cache.limits() != old_limits
        || cache.active_len() != 0
        || cache.retired_len() != 2
        || cache.usage().entries() != 2
        || !adapter.release_requests.is_empty()
    {
        return Err(String::from("live entry shrink blockage drifted"));
    }
    drop(first_lease);
    drop(second_lease);
    cache
        .reconcile_retired(&mut adapter)
        .map(|_report| ())
        .map_err(|release| release.to_string())
}

#[test]
fn executable_sequence_lease_cache_reconfiguration_publishes_after_return()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let key = NativeExecutableSequenceKey::from_plan(&plan);
    let old_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(1, "entry limit")?,
    );
    let new_limits =
        old_limits.with_mapping_limit(nonzero_test_limit(1, "mapping limit")?);
    let (mut cache, mut adapter) = lease_fixture(old_limits, 976, 0xea_000)?;
    let lease = lease_acquire(&mut cache, &mut adapter, &plan)?;
    let Err(failure) = cache.reconfigure_limits(&mut adapter, new_limits)
    else {
        return Err(String::from(
            "leased mapping shrink unexpectedly published",
        ));
    };
    if failure.evicted_keys() != [key.clone()]
        || failure.retired_keys() != [key.clone()]
        || failure.limit_transition() != (old_limits, new_limits)
        || failure.block().is_none()
        || cache.limits() != old_limits
        || cache.retired_len() != 1
        || cache.usage().mappings() != 2
    {
        return Err(String::from("leased mapping shrink evidence drifted"));
    }
    let reconciliation = cache
        .return_lease(&mut adapter, lease)
        .map_err(|release| release.to_string())?;
    let operations = adapter.operations.len();
    let report = cache
        .reconfigure_limits(&mut adapter, new_limits)
        .map_err(|retry| retry.to_string())?;
    if reconciliation.released_keys() != [key]
        || !reconciliation.retained_keys().is_empty()
        || !report.evicted_keys().is_empty()
        || !report.retired_keys().is_empty()
        || report.limit_transition() != (old_limits, new_limits)
        || cache.limits() != new_limits
        || !cache.is_empty()
        || adapter.operations.len() != operations
    {
        Err(String::from("post-return limit publication drifted"))
    } else {
        Ok(())
    }
}

#[test]
fn executable_sequence_lease_cache_reconfiguration_retries_release_failure()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::X86_64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first);
    let second_key = NativeExecutableSequenceKey::from_plan(&second);
    let old_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(2, "entry limit")?,
    );
    let new_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(1, "entry limit")?,
    );
    let (mut cache, mut adapter) = lease_fixture(old_limits, 977, 0xeb_000)?;
    drop(lease_acquire(&mut cache, &mut adapter, &first)?);
    drop(lease_acquire(&mut cache, &mut adapter, &second)?);
    adapter.release_failure_at =
        Some(adapter.release_attempts.saturating_add(1));
    let Err(failure) = cache.reconfigure_limits(&mut adapter, new_limits)
    else {
        return Err(String::from("configured leased shrink failure ignored"));
    };
    if failure.evicted_keys() != [first_key.clone()]
        || !failure.retired_keys().is_empty()
        || failure.limit_transition() != (old_limits, new_limits)
        || failure.block().is_some()
        || failure
            .release_failure()
            .map(NativeExecutableSequenceLeaseCacheEntryReleaseFailure::key)
            != Some(&first_key)
        || cache.limits() != old_limits
        || cache.keys().cloned().collect::<Vec<_>>() != [second_key]
        || cache.usage().entries() != 1
    {
        return Err(String::from("leased shrink release failure drifted"));
    }
    let keyed = (*failure)
        .into_release_failure()
        .ok_or_else(|| String::from("leased shrink release owner missing"))?;
    keyed
        .into_failure()
        .retry(&mut adapter)
        .map_err(|release| release.to_string())?;
    let operations = adapter.operations.len();
    let report = cache
        .reconfigure_limits(&mut adapter, new_limits)
        .map_err(|retry| retry.to_string())?;
    if !report.evicted_keys().is_empty()
        || report.limit_transition() != (old_limits, new_limits)
        || cache.limits() != new_limits
        || adapter.operations.len() != operations
    {
        return Err(String::from("leased shrink retry publication drifted"));
    }
    cache
        .release_all(&mut adapter)
        .map(|_report| ())
        .map_err(|release| release.to_string())
}

#[test]
fn executable_sequence_lease_cache_reconfigures_mapping_fifo()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&fixture, HostIsa::AArch64, 1)?;
    let second = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first);
    let second_key = NativeExecutableSequenceKey::from_plan(&second);
    let old_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(2, "entry limit")?,
    );
    let new_limits =
        old_limits.with_mapping_limit(nonzero_test_limit(2, "mapping limit")?);
    let (mut cache, mut adapter) = lease_fixture(old_limits, 978, 0xec_000)?;
    drop(lease_acquire(&mut cache, &mut adapter, &first)?);
    drop(lease_acquire(&mut cache, &mut adapter, &second)?);
    let report = cache
        .reconfigure_limits(&mut adapter, new_limits)
        .map_err(|failure| failure.to_string())?;
    if report.evicted_keys() != [first_key]
        || !report.retired_keys().is_empty()
        || report.limit_transition() != (old_limits, new_limits)
        || cache.keys().cloned().collect::<Vec<_>>() != [second_key]
        || cache.usage().entries() != 1
        || cache.usage().mappings() != 2
        || adapter.release_requests.len() != 1
    {
        return Err(String::from("leased mapping shrink FIFO drifted"));
    }
    cache
        .release_all(&mut adapter)
        .map(|_report| ())
        .map_err(|release| release.to_string())
}

#[test]
fn executable_sequence_lease_cache_reconfiguration_blocks_byte_resident()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = selected_sequence_prefix(&fixture, HostIsa::AArch64, 2)?;
    let key = NativeExecutableSequenceKey::from_plan(&plan);
    let mapped_bytes = direct_sequence_mapped_bytes(&plan)?;
    let byte_limit = mapped_bytes
        .checked_sub(1)
        .and_then(NonZeroUsize::new)
        .ok_or_else(|| String::from("leased byte shrink limit missing"))?;
    let old_limits = NativeExecutableSequenceCacheLimits::new(
        nonzero_test_limit(1, "entry limit")?,
    );
    let new_limits = old_limits.with_mapped_byte_limit(byte_limit);
    let (mut cache, mut adapter) = lease_fixture(old_limits, 979, 0xed_000)?;
    let lease = lease_acquire(&mut cache, &mut adapter, &plan)?;
    let Err(failure) = cache.reconfigure_limits(&mut adapter, new_limits)
    else {
        return Err(String::from("leased byte shrink unexpectedly published"));
    };
    let block = failure
        .block()
        .ok_or_else(|| String::from("leased byte shrink block missing"))?;
    if failure.evicted_keys() != [key.clone()]
        || failure.retired_keys() != [key.clone()]
        || block.limits() != new_limits
        || block.retired_keys() != [key.clone()]
        || block.usage().mapped_bytes() != mapped_bytes
        || cache.limits() != old_limits
        || cache.usage().mapped_bytes() != mapped_bytes
        || !adapter.release_requests.is_empty()
    {
        return Err(String::from("leased byte shrink blockage drifted"));
    }
    let report = cache
        .return_lease(&mut adapter, lease)
        .map_err(|release| release.to_string())?;
    if report.released_keys() == [key] && cache.is_empty() {
        Ok(())
    } else {
        Err(String::from("leased byte shrink cleanup drifted"))
    }
}

fn native_executable_adapter(
    mapping_value: u64,
    base_value: usize,
) -> Result<FakeNativeExecutableAdapter, String> {
    Ok(FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(mapping_value)?,
        native_executable_address(base_value)?,
    ))
}

fn second_sequence_entry(
    programs: &[RegionEffectProgram],
) -> Result<ProfileMachineObservation, String> {
    programs
        .get(1)
        .and_then(|program| program.effects.first())
        .map(|effect| effect.before)
        .ok_or_else(|| String::from("second continuation entry missing"))
}

fn assert_second_step_continuation(
    continuation: &NativeInterpreterContinuation,
    expected: &SecondStepContinuationExpectation<'_>,
) -> Result<(), String> {
    let remaining_key = expected
        .plan_key
        .suffix(1)
        .ok_or_else(|| String::from("second continuation key missing"))?;
    let remaining_programs = expected
        .programs
        .get(1..)
        .ok_or_else(|| String::from("second continuation suffix missing"))?;
    let observation = second_sequence_entry(expected.programs)?;
    if continuation.completed_steps() == 1
        && continuation.resume_index() == 1
        && continuation.remaining_steps() == remaining_programs.len()
        && continuation.observation() == observation
        && continuation.expected_exit() == expected.expected_exit
        && continuation.expected_outcome() == expected.expected_outcome
        && continuation.reason() == expected.reason
        && continuation.plan_key() == expected.plan_key
        && continuation.remaining_key() == &remaining_key
        && continuation.remaining_programs() == remaining_programs
    {
        Ok(())
    } else {
        Err(String::from("interpreter continuation suffix drifted"))
    }
}

#[test]
fn native_interpreter_continuation_tracks_uncached_guard_miss()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let plan_key = NativeExecutableSequenceKey::from_plan(&plan);
    let mut adapter = native_executable_adapter(930, 0xb0_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let outcome = execute_verified_native_sequence(
        &mut adapter,
        &mut runner,
        &plan,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    )
    .map_err(|failure| failure.to_string())?;
    let continuation =
        NativeInterpreterContinuation::from_outcome(&plan, outcome)
            .map_err(|error| error.to_string())?
            .ok_or_else(|| {
                String::from("guard miss produced no continuation")
            })?;
    assert_second_step_continuation(
        &continuation,
        &SecondStepContinuationExpectation {
            expected_exit: plan.exit(),
            expected_outcome: plan.outcome(),
            plan_key: &plan_key,
            programs: plan.programs(),
            reason: NativeInterpreterContinuationReason::GuardMiss,
        },
    )
}

#[test]
fn native_interpreter_continuation_tracks_cached_loaded_guard_miss()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let mut artifact_cache = VerifiedDirectNativeCache::default();
    let plan = select_cached_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::AArch64),
        &mut artifact_cache,
    )
    .map_err(|error| error.to_string())?;
    let plan_key = NativeExecutableSequenceKey::from_cached_plan(&plan);
    let mut adapter = native_executable_adapter(931, 0xb1_000)?;
    let sequence = load_cached_verified_native_sequence(&mut adapter, &plan)
        .map_err(|failure| failure.to_string())?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let outcome = execute_loaded_cached_verified_native_sequence(
        &mut runner,
        &plan,
        &sequence,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    )
    .map_err(|failure| failure.to_string())?;
    let continuation =
        NativeInterpreterContinuation::from_cached_outcome(&plan, outcome)
            .map_err(|error| error.to_string())?
            .ok_or_else(|| {
                String::from("cached guard miss produced no continuation")
            })?;
    assert_second_step_continuation(
        &continuation,
        &SecondStepContinuationExpectation {
            expected_exit: plan.exit(),
            expected_outcome: plan.outcome(),
            plan_key: &plan_key,
            programs: plan.programs(),
            reason: NativeInterpreterContinuationReason::GuardMiss,
        },
    )?;
    release_native_executable_sequence(&mut adapter, sequence)
        .map_err(|failure| failure.to_string())
}

#[test]
fn native_interpreter_continuation_rejects_forged_outcomes()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let bad_steps = NativeInterpreterContinuation::from_outcome(
        &plan,
        NativeSequenceExecutionOutcome::Applied {
            observation: plan.exit(),
            steps: 1,
        },
    );
    let bad_exit = NativeInterpreterContinuation::from_outcome(
        &plan,
        NativeSequenceExecutionOutcome::Applied {
            observation: plan.entry(),
            steps: 2,
        },
    );
    let bad_index = NativeInterpreterContinuation::from_outcome(
        &plan,
        NativeSequenceExecutionOutcome::GuardMiss {
            index: 2,
            observation: plan.exit(),
        },
    );
    let bad_observation = NativeInterpreterContinuation::from_outcome(
        &plan,
        NativeSequenceExecutionOutcome::GuardMiss {
            index: 1,
            observation: plan.entry(),
        },
    );
    if bad_steps
        == Err(NativeInterpreterContinuationError::AppliedSteps {
            expected: 2,
            observed: 1,
        })
        && bad_exit
            == Err(NativeInterpreterContinuationError::AppliedObservation)
        && bad_index
            == Err(NativeInterpreterContinuationError::ResumeIndex {
                observed: 2,
                steps: 2,
            })
        && bad_observation
            == Err(NativeInterpreterContinuationError::ResumeObservation {
                index: 1,
            })
    {
        Ok(())
    } else {
        Err(String::from("forged continuation outcome was admitted"))
    }
}

#[test]
fn native_interpreter_continuation_tracks_sequence_failure()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = selected_sequence_prefix(&fixture, HostIsa::AArch64, 2)?;
    let plan_key = NativeExecutableSequenceKey::from_plan(&plan);
    let mut adapter = native_executable_adapter(932, 0xb2_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let Err(failure) = execute_verified_native_sequence(
        &mut adapter,
        &mut runner,
        &plan,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    ) else {
        return Err(String::from(
            "configured continuation failure was ignored",
        ));
    };
    let continuation =
        NativeInterpreterContinuation::from_failure(&plan, &failure)
            .map_err(|error| error.to_string())?
            .ok_or_else(|| {
                String::from("sequence failure produced no continuation")
            })?;
    assert_second_step_continuation(
        &continuation,
        &SecondStepContinuationExpectation {
            expected_exit: plan.exit(),
            expected_outcome: plan.outcome(),
            plan_key: &plan_key,
            programs: plan.programs(),
            reason: NativeInterpreterContinuationReason::ExecutionFailure,
        },
    )
}

#[test]
fn native_interpreter_continuation_tracks_loaded_failure() -> Result<(), String>
{
    let fixture = direct_normative_sequence_fixture()?;
    let plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let plan_key = NativeExecutableSequenceKey::from_plan(&plan);
    let mut adapter = native_executable_adapter(933, 0xb3_000)?;
    let sequence = load_verified_native_sequence(&mut adapter, &plan)
        .map_err(|failure| failure.to_string())?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let Err(failure) = execute_loaded_verified_native_sequence(
        &mut runner,
        &plan,
        &sequence,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    ) else {
        return Err(String::from("configured loaded failure was ignored"));
    };
    let continuation =
        NativeInterpreterContinuation::from_loaded_failure(&plan, &failure)
            .map_err(|error| error.to_string())?
            .ok_or_else(|| {
                String::from("loaded failure produced no continuation")
            })?;
    assert_second_step_continuation(
        &continuation,
        &SecondStepContinuationExpectation {
            expected_exit: plan.exit(),
            expected_outcome: plan.outcome(),
            plan_key: &plan_key,
            programs: plan.programs(),
            reason: NativeInterpreterContinuationReason::ExecutionFailure,
        },
    )?;
    release_native_executable_sequence(&mut adapter, sequence)
        .map_err(|error| error.to_string())
}

#[test]
fn native_interpreter_continuation_tracks_cached_failure() -> Result<(), String>
{
    let fixture = direct_normative_sequence_fixture()?;
    let mut artifact_cache = VerifiedDirectNativeCache::default();
    let plan = select_cached_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        &mut artifact_cache,
    )
    .map_err(|error| error.to_string())?;
    let plan_key = NativeExecutableSequenceKey::from_cached_plan(&plan);
    let mut adapter = native_executable_adapter(934, 0xb4_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let Err(failure) = execute_cached_verified_native_sequence(
        &mut adapter,
        &mut runner,
        &plan,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    ) else {
        return Err(String::from("configured cached failure was ignored"));
    };
    let continuation =
        NativeInterpreterContinuation::from_cached_failure(&plan, &failure)
            .map_err(|error| error.to_string())?
            .ok_or_else(|| {
                String::from("cached failure produced no continuation")
            })?;
    assert_second_step_continuation(
        &continuation,
        &SecondStepContinuationExpectation {
            expected_exit: plan.exit(),
            expected_outcome: plan.outcome(),
            plan_key: &plan_key,
            programs: plan.programs(),
            reason: NativeInterpreterContinuationReason::ExecutionFailure,
        },
    )
}

#[test]
fn native_interpreter_continuation_tracks_cached_loaded_failure()
-> Result<(), String> {
    let fixture = direct_normative_sequence_fixture()?;
    let mut artifact_cache = VerifiedDirectNativeCache::default();
    let plan = select_cached_verified_direct_sequence(
        &fixture.programs,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::AArch64),
        &mut artifact_cache,
    )
    .map_err(|error| error.to_string())?;
    let plan_key = NativeExecutableSequenceKey::from_cached_plan(&plan);
    let mut adapter = native_executable_adapter(935, 0xb5_000)?;
    let sequence = load_cached_verified_native_sequence(&mut adapter, &plan)
        .map_err(|failure| failure.to_string())?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let Err(failure) = execute_loaded_cached_verified_native_sequence(
        &mut runner,
        &plan,
        &sequence,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    ) else {
        return Err(String::from("configured cached loaded failure ignored"));
    };
    let continuation =
        NativeInterpreterContinuation::from_cached_loaded_failure(
            &plan, &failure,
        )
        .map_err(|error| error.to_string())?
        .ok_or_else(|| {
            String::from("cached loaded failure has no continuation")
        })?;
    assert_second_step_continuation(
        &continuation,
        &SecondStepContinuationExpectation {
            expected_exit: plan.exit(),
            expected_outcome: plan.outcome(),
            plan_key: &plan_key,
            programs: plan.programs(),
            reason: NativeInterpreterContinuationReason::ExecutionFailure,
        },
    )?;
    release_native_executable_sequence(&mut adapter, sequence)
        .map_err(|error| error.to_string())
}

#[test]
fn native_interpreter_continuation_omits_completed_work() -> Result<(), String>
{
    let fixture = direct_normative_sequence_fixture()?;
    let plan = selected_sequence_prefix(&fixture, HostIsa::X86_64, 2)?;
    let complete = NativeSequenceExecutionOutcome::Applied {
        observation: plan.exit(),
        steps: plan.len(),
    };
    if NativeInterpreterContinuation::from_outcome(&plan, complete)
        .map_err(|error| error.to_string())?
        .is_some()
    {
        return Err(String::from(
            "completed outcome retained interpreter work",
        ));
    }
    let mut adapter =
        native_executable_adapter(936, 0xb6_000)?.with_release_failure_at(2);
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let Err(failure) = execute_verified_native_sequence(
        &mut adapter,
        &mut runner,
        &plan,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    ) else {
        return Err(String::from(
            "configured terminal cleanup failure ignored",
        ));
    };
    if NativeInterpreterContinuation::from_failure(&plan, &failure)
        .map_err(|error| error.to_string())?
        .is_some()
    {
        return Err(String::from("terminal cleanup retained semantic work"));
    }
    let execution = (*failure)
        .into_execution_failure()
        .ok_or_else(|| String::from("terminal execution failure missing"))?;
    let release = execution
        .into_release_failure()
        .ok_or_else(|| String::from("terminal release owner missing"))?;
    release
        .retry(&mut adapter)
        .map_err(|retry| retry.to_string())
}

fn native_handoff_fixture(
    isa: HostIsa,
    behaviors: Vec<FakeNativeRunnerBehavior>,
) -> Result<NativeHandoffFixture, String> {
    let fixture = direct_normative_sequence_fixture()?;
    let plan = selected_sequence_prefix(&fixture, isa, 2)?;
    let mut adapter = native_executable_adapter(940, 0xc0_000)?;
    let mut runner = FakeNativeSequenceRunner::new(behaviors);
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let outcome = execute_verified_native_sequence(
        &mut adapter,
        &mut runner,
        &plan,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    )
    .map_err(|failure| failure.to_string())?;
    let continuation =
        NativeInterpreterContinuation::from_outcome(&plan, outcome)
            .map_err(|error| error.to_string())?
            .ok_or_else(|| {
                String::from("native handoff fixture completed unexpectedly")
            })?;
    Ok(NativeHandoffFixture {
        continuation,
        input: fixture.input,
        memory,
        output,
        plan,
    })
}

const fn one_native_retry_policy() -> NativeContinuationRetryPolicy {
    NativeContinuationRetryPolicy::new(
        1,
        NativeContinuationRetryFallback::complete(),
    )
}

const fn linux_x86_64_retry_cycle_request(
    policy: NativeContinuationRetryPolicy,
    suspension: NativeContinuationScheduleSuspension,
    attempts: usize,
) -> NativeContinuationRetryCycleRequest {
    NativeContinuationRetryCycleRequest::new(
        policy,
        suspension,
        attempts,
        NativeContinuationRetryHost::new(
            safe_rust_profiled_capability(),
            HostOperatingSystem::Linux,
            HostIsa::X86_64,
        ),
    )
}

const fn complete_retry_policy(
    max_native_attempts: usize,
) -> NativeContinuationRetryPolicy {
    NativeContinuationRetryPolicy::new(
        max_native_attempts,
        NativeContinuationRetryFallback::complete(),
    )
}

const fn windows_cached_retry_cycle_request(
    policy: NativeContinuationRetryPolicy,
    suspension: NativeContinuationScheduleSuspension,
    attempts: usize,
    host_isa: HostIsa,
) -> NativeContinuationCachedRetryCycleRequest {
    NativeContinuationCachedRetryCycleRequest::new(
        policy,
        suspension,
        attempts,
        NativeContinuationRetryHost::new(
            safe_rust_profiled_capability(),
            HostOperatingSystem::Windows,
            host_isa,
        ),
    )
}

const fn windows_retry_cycle_request(
    policy: NativeContinuationRetryPolicy,
    suspension: NativeContinuationScheduleSuspension,
    attempts: usize,
    host_isa: HostIsa,
) -> NativeContinuationRetryCycleRequest {
    NativeContinuationRetryCycleRequest::new(
        policy,
        suspension,
        attempts,
        NativeContinuationRetryHost::new(
            safe_rust_profiled_capability(),
            HostOperatingSystem::Windows,
            host_isa,
        ),
    )
}

fn one_attempt_retry_route(
    suspension: NativeContinuationScheduleSuspension,
    runtime: &'static RuntimeCapability,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<NativeContinuationRetryRoute, String> {
    route_native_continuation_retry(NativeContinuationRetryRoutingRequest::new(
        one_native_retry_policy(),
        suspension,
        0,
        NativeContinuationRetryHost::new(runtime, host_os, host_isa),
    ))
    .map_err(|failure| failure.error().to_string())
}

fn native_schedule_fixture(
    isa: HostIsa,
    behaviors: Vec<FakeNativeRunnerBehavior>,
) -> Result<NativeScheduleFixture, String> {
    let NativeHandoffFixture {
        continuation,
        input,
        memory,
        output,
        plan,
    } = native_handoff_fixture(isa, behaviors)?;
    let retained_memory = memory.clone();
    let handoff = NativeInterpreterHandoff::from_buffers(
        continuation,
        memory,
        input,
        &output,
    )
    .map_err(|error| error.to_string())?;
    Ok(NativeScheduleFixture {
        handoff,
        memory: retained_memory,
        plan,
    })
}

fn native_retry_fixture(
    isa: HostIsa,
    interpreter_steps: usize,
) -> Result<NativeRetryFixture, String> {
    let fixture = native_schedule_fixture(isa, vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let full_plan = fixture.plan.clone();
    let first = if interpreter_steps == 0 {
        schedule_native_interpreter_handoff(
            fixture.handoff,
            NativeContinuationScheduleDecision::yield_to(
                NativeContinuationYieldTarget::NativeRetry,
            ),
        )
    } else {
        schedule_native_interpreter_handoff(
            fixture.handoff,
            NativeContinuationScheduleDecision::interpret(nonzero_test_limit(
                interpreter_steps,
                "retry prefix",
            )?),
        )
    }
    .map_err(|error| error.to_string())?;
    let NativeContinuationScheduleOutcome::Suspended(first_pause) = first
    else {
        return Err(String::from("retry fixture completed unexpectedly"));
    };
    let suspension = if interpreter_steps == 0 {
        first_pause
    } else {
        let second = first_pause
            .resume(NativeContinuationScheduleDecision::yield_to(
                NativeContinuationYieldTarget::NativeRetry,
            ))
            .map_err(|error| error.to_string())?;
        let NativeContinuationScheduleOutcome::Suspended(pause) = second else {
            return Err(String::from("retry yield completed unexpectedly"));
        };
        pause
    };
    let retry_plan = select_verified_direct_sequence(
        suspension.remaining_programs(),
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        isa,
    )
    .map_err(|error| error.to_string())?;
    Ok(NativeRetryFixture {
        full_plan,
        retry_plan,
        suspension,
    })
}

fn admitted_native_retry(
    isa: HostIsa,
    interpreter_steps: usize,
) -> Result<AdmittedNativeRetryFixture, String> {
    let fixture = native_retry_fixture(isa, interpreter_steps)?;
    let retry = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan.clone(),
    )
    .map_err(|failure| failure.error().to_string())?;
    Ok(AdmittedNativeRetryFixture {
        full_plan: fixture.full_plan,
        retry,
        retry_plan: fixture.retry_plan,
    })
}

fn cached_cycle_interpreter(
    outcome: NativeContinuationCachedRetryCycleOutcome<FakeNativeRunnerError>,
) -> Result<Box<NativeContinuationCachedRetryInterpreterOutcome>, String> {
    match outcome {
        NativeContinuationCachedRetryCycleOutcome::Interpreter(interpreter) => {
            Ok(interpreter)
        },
        NativeContinuationCachedRetryCycleOutcome::NativeCompletion(_)
        | NativeContinuationCachedRetryCycleOutcome::NativeFailure(_) => {
            Err(String::from("cached retry cycle did not route interpreter"))
        },
    }
}

fn cached_cycle_native_failure(
    outcome: NativeContinuationCachedRetryCycleOutcome<FakeNativeRunnerError>,
) -> Result<CachedRetryCycleNativeFailure, String> {
    match outcome {
        NativeContinuationCachedRetryCycleOutcome::NativeFailure(failure) => {
            Ok(failure)
        },
        NativeContinuationCachedRetryCycleOutcome::Interpreter(_)
        | NativeContinuationCachedRetryCycleOutcome::NativeCompletion(_) => {
            Err(String::from(
                "cached retry cycle did not retain native failure",
            ))
        },
    }
}

fn cached_cycle_completion(
    outcome: NativeContinuationCachedRetryCycleOutcome<FakeNativeRunnerError>,
) -> Result<Box<NativeContinuationCachedRetryCompletion>, String> {
    match outcome {
        NativeContinuationCachedRetryCycleOutcome::NativeCompletion(
            completion,
        ) => Ok(completion),
        NativeContinuationCachedRetryCycleOutcome::Interpreter(_)
        | NativeContinuationCachedRetryCycleOutcome::NativeFailure(_) => {
            Err(String::from("cached retry cycle did not complete native"))
        },
    }
}

fn cached_retry_failure_matches(
    failure: &NativeContinuationLeasedRetryExecutionFailure<
        FakeNativeRunnerError,
    >,
    expected_key: &NativeExecutableSequenceKey,
) -> bool {
    failure.lease().key() == expected_key
        && failure.failure().completed_steps() == 0
        && failure.failure().resume_index() == 0
        && !failure.cache_disposition().is_hit()
}

fn assert_cached_retry_telemetry<Source>(
    source: &Source,
    expected: &CachedRetryTelemetryExpectation,
) -> Result<(), String>
where
    Source: NativeContinuationCachedRetryTelemetrySource + ?Sized,
{
    let telemetry = source
        .cached_retry_telemetry()
        .map_err(|error| error.to_string())?;
    if telemetry.attempts() == expected.attempts
        && telemetry.completed_steps() == expected.completed_steps
        && telemetry.evicted_keys() == expected.evicted_keys
        && telemetry.hits() == expected.hits
        && telemetry.insertions() == expected.insertions
        && telemetry.retired_keys() == expected.retired_keys
    {
        Ok(())
    } else {
        Err(String::from("cached retry telemetry drifted"))
    }
}

fn assert_retirement_pressure_assessment(
    telemetry: NativeContinuationCachedRetryTelemetry,
) -> Result<(), String> {
    let thresholds =
        NativeContinuationCachedRetryTelemetryAssessmentThresholds::new(
            NativeContinuationCachedRetryTelemetryAssessmentMaximums::new(
                1, 1, 0,
            ),
            NativeContinuationCachedRetryTelemetryAssessmentMinimums::new(
                nonzero_test_limit(1, "telemetry assessment attempts")?,
                0,
                0,
            ),
        );
    let NativeContinuationCachedRetryTelemetryAssessment::Misses {
        telemetry: assessed,
        violations,
    } = assess_cached_retry_telemetry(telemetry, thresholds)
    else {
        return Err(String::from("retirement assessment category drifted"));
    };
    let evicted = violations.contains(
        NativeContinuationCachedRetryTelemetryAssessmentSignal::EvictedKeys,
    );
    let retired = violations.contains(
        NativeContinuationCachedRetryTelemetryAssessmentSignal::RetiredKeys,
    );
    let unexpected = [
        NativeContinuationCachedRetryTelemetryAssessmentSignal::CompletedSteps,
        NativeContinuationCachedRetryTelemetryAssessmentSignal::Hits,
        NativeContinuationCachedRetryTelemetryAssessmentSignal::Insertions,
    ]
    .into_iter()
    .any(|signal| violations.contains(signal));
    if assessed == telemetry && evicted && retired && !unexpected {
        Ok(())
    } else {
        Err(String::from("retirement assessment signals drifted"))
    }
}
fn assert_retirement_telemetry<Source>(source: &Source) -> Result<(), String>
where
    Source: NativeContinuationCachedRetryTelemetrySource + ?Sized,
{
    assert_cached_retry_telemetry(source, &CachedRetryTelemetryExpectation {
        attempts: 1,
        completed_steps: 2,
        evicted_keys: 2,
        hits: 0,
        insertions: 1,
        retired_keys: 1,
    })?;
    let telemetry = source
        .cached_retry_telemetry()
        .map_err(|error| error.to_string())?;
    assert_retirement_pressure_assessment(telemetry)
}

fn complete_retry_resumption(
    resumption: Box<NativeContinuationRetryResumption>,
) -> Result<NativeInterpreterHandoffCompletion, String> {
    let scheduled = schedule_native_interpreter_handoff(
        resumption.into_handoff(),
        NativeContinuationScheduleDecision::complete_interpreter(),
    )
    .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Completed(completion) = scheduled
    else {
        return Err(String::from("leased retry fallback suspended"));
    };
    Ok(completion)
}

fn retry_resumption(
    disposition: NativeContinuationRetryDisposition,
) -> Result<Box<NativeContinuationRetryResumption>, String> {
    match disposition {
        NativeContinuationRetryDisposition::Resumable(resumption) => {
            Ok(resumption)
        },
        NativeContinuationRetryDisposition::Completed(_) => {
            Err(String::from("retry disposition completed unexpectedly"))
        },
    }
}

fn retry_completion_matches(
    completion: &NativeInterpreterHandoffCompletion,
    expected_outcome: RunOutcome,
    expected: &NativeSequenceFixture,
) -> bool {
    completion.outcome() == expected_outcome
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
}

fn leased_native_retry_fixture(
    isa: HostIsa,
    interpreter_steps: usize,
    mapping_value: u64,
    base_value: usize,
) -> Result<LeasedNativeRetryFixture, String> {
    let fixture = native_retry_fixture(isa, interpreter_steps)?;
    let retry = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan.clone(),
    )
    .map_err(|failure| failure.error().to_string())?;
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        1,
        "leased retry capacity",
    )?);
    let (mut cache, mut adapter) =
        lease_fixture(limits, mapping_value, base_value)?;
    let acquisition = cache
        .ensure_plan(&mut adapter, &fixture.retry_plan)
        .map_err(|failure| failure.to_string())?;
    let leased = NativeContinuationLeasedRetry::new(retry, acquisition)
        .map_err(|_failure| String::from("leased retry binding failed"))?;
    Ok(LeasedNativeRetryFixture {
        adapter,
        cache,
        full_plan: fixture.full_plan,
        leased,
    })
}

fn release_leased_retry(
    cache: &mut NativeExecutableSequenceLeaseCache,
    adapter: &mut FakeNativeExecutableAdapter,
    lease: NativeExecutableSequenceLease,
) -> Result<(), String> {
    drop(lease);
    cache
        .release_all(adapter)
        .map(|_report| ())
        .map_err(|failure| failure.to_string())
}

fn profile_state_observation(
    state: &ProfileMachineState,
) -> ProfileMachineObservation {
    ProfileMachineObservation {
        input_consumed: state.io().input_consumed(),
        output_len: state.io().output().len(),
        registers: state.registers(),
        termination: state.io().termination(),
    }
}

fn distinct_second_live_in(
    plan: &VerifiedDirectSequencePlan,
) -> Result<MemoryLiveIn, String> {
    let [first, second] = plan.programs() else {
        return Err(String::from("handoff rollback plan length drifted"));
    };
    second
        .memory_live_ins
        .iter()
        .find(|candidate| {
            !first
                .memory_live_ins
                .iter()
                .any(|prior| prior.address == candidate.address)
        })
        .copied()
        .ok_or_else(|| String::from("late handoff live-in missing"))
}

fn run_one_profile_step(
    machine: &mut ProfileMachine,
    context: &str,
) -> Result<(), String> {
    let outcome = machine
        .run(1)
        .map_err(|error| format!("{context}: {error}"))?;
    if outcome == (RunOutcome::BudgetExhausted { steps: 1 }) {
        Ok(())
    } else {
        Err(format!("{context} outcome drifted: {outcome:?}"))
    }
}

#[test]
fn native_interpreter_handoff_completes_from_buffers() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let NativeHandoffFixture {
        continuation,
        input,
        memory,
        output,
        plan,
    } = native_handoff_fixture(HostIsa::X86_64, vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let retained = continuation.clone();
    let handoff = NativeInterpreterHandoff::from_buffers(
        continuation,
        memory,
        input,
        &output,
    )
    .map_err(|error| error.to_string())?;
    let completion = handoff.execute().map_err(|error| error.to_string())?;
    if completion.continuation() == &retained
        && completion.interpreter_outcome()
            == (RunOutcome::BudgetExhausted { steps: 1 })
        && completion.outcome() == plan.outcome()
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
        && profile_state_observation(completion.state()) == plan.exit()
    {
        Ok(())
    } else {
        Err(String::from(
            "buffer interpreter handoff completion drifted",
        ))
    }
}

#[test]
fn native_interpreter_handoff_completes_from_checkpoint() -> Result<(), String>
{
    let expected = direct_normative_sequence_fixture()?;
    let NativeHandoffFixture { continuation, plan, .. } =
        native_handoff_fixture(HostIsa::AArch64, vec![
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::GuardMiss,
        ])?;
    let mut machine =
        ProfileMachine::from_snapshot(direct_normative_sequence_state()?);
    run_one_profile_step(&mut machine, "handoff checkpoint prefix")?;
    let checkpoint = machine.snapshot_state();
    if profile_state_observation(&checkpoint) != continuation.observation() {
        return Err(String::from("handoff checkpoint prefix drifted"));
    }
    let completion =
        NativeInterpreterHandoff::from_checkpoint(continuation, checkpoint)
            .map_err(|error| error.to_string())?
            .execute()
            .map_err(|error| error.to_string())?;
    if completion.outcome() == plan.outcome()
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("checkpoint interpreter handoff drifted"))
    }
}

fn derived_v5_handoff_fixture(
    word_trits: u8,
) -> Result<DerivedV5HandoffFixture, String> {
    let verified =
        verify_initial_halt_profile_width(current_profile(), b"QP", word_trits)
            .map_err(|error| format!("v5 handoff verification: {error}"))?;
    let machine = ProfileMachine::from_verified_source(&verified, Vec::new())
        .map_err(|error| format!("v5 handoff machine: {error}"))?;
    let checkpoint = machine.snapshot_state();
    let mut replay = ProfileMachine::from_snapshot(checkpoint.clone());
    let mut trace_slot = None;
    let _outcome = replay
        .step_traced(&mut |trace| trace_slot = Some(*trace))
        .map_err(|error| format!("v5 handoff trace: {error}"))?;
    let trace = trace_slot.ok_or_else(|| String::from("v5 trace missing"))?;
    let program =
        ExecutionGeometryRegionEffectProgram::from_profile_step_trace(&trace)
            .map_err(|error| format!("v5 projection: {error:?}"))?;
    Ok((program, checkpoint, verified.geometry()))
}

fn derived_v5_initial_jump_data_fixture(
    word_trits: u8,
) -> Result<DerivedV5HandoffFixture, String> {
    let verified = verify_jump_rotate_halt_profile_width(
        current_profile(),
        b"(&O",
        word_trits,
    )
    .map_err(|error| format!("v5 initial jump-data verification: {error}"))?;
    let mut machine =
        ProfileMachine::from_verified_source(&verified, Vec::new()).map_err(
            |error| format!("v5 initial jump-data machine: {error}"),
        )?;
    let checkpoint = machine.snapshot_state();
    let mut trace_slot = None;
    let outcome = machine
        .step_traced(&mut |trace| trace_slot = Some(*trace))
        .map_err(|error| format!("v5 initial jump-data trace: {error}"))?;
    if outcome != StepOutcome::Continued {
        return Err(String::from(
            "v5 initial jump-data fixture did not advance",
        ));
    }
    let trace = trace_slot
        .ok_or_else(|| String::from("v5 initial jump-data trace missing"))?;
    let program =
        ExecutionGeometryRegionEffectProgram::from_profile_step_trace(&trace)
            .map_err(|error| {
            format!("v5 initial jump-data projection: {error:?}")
        })?;
    Ok((program, checkpoint, verified.geometry()))
}

fn derived_v5_no_operation_fixture(
    word_trits: u8,
) -> Result<DerivedV5HandoffFixture, String> {
    let verified = verify_noop_prefix_halt_profile_width(
        current_profile(),
        b"DP",
        word_trits,
    )
    .map_err(|error| format!("v5 no-operation verification: {error}"))?;
    let mut machine =
        ProfileMachine::from_verified_source(&verified, Vec::new())
            .map_err(|error| format!("v5 no-operation machine: {error}"))?;
    let checkpoint = machine.snapshot_state();
    let mut trace_slot = None;
    let outcome = machine
        .step_traced(&mut |trace| trace_slot = Some(*trace))
        .map_err(|error| format!("v5 no-operation trace: {error}"))?;
    if outcome != StepOutcome::Continued {
        return Err(String::from("v5 no-operation fixture did not advance"));
    }
    let trace = trace_slot
        .ok_or_else(|| String::from("v5 no-operation trace missing"))?;
    let program =
        ExecutionGeometryRegionEffectProgram::from_profile_step_trace(&trace)
            .map_err(|error| format!("v5 no-operation projection: {error:?}"))?;
    Ok((program, checkpoint, verified.geometry()))
}

fn derived_v5_rotate_fixture(
    word_trits: u8,
) -> Result<DerivedV5HandoffFixture, String> {
    let verified = verify_jump_rotate_halt_profile_width(
        current_profile(),
        b"(&O",
        word_trits,
    )
    .map_err(|error| format!("v5 rotate verification: {error}"))?;
    let mut machine =
        ProfileMachine::from_verified_source(&verified, Vec::new())
            .map_err(|error| format!("v5 rotate machine: {error}"))?;
    let first = machine
        .step()
        .map_err(|error| format!("v5 rotate jump: {error}"))?;
    if first != StepOutcome::Continued {
        return Err(String::from("v5 rotate fixture jump did not advance"));
    }
    let checkpoint = machine.snapshot_state();
    let mut trace_slot = None;
    let second = machine
        .step_traced(&mut |trace| trace_slot = Some(*trace))
        .map_err(|error| format!("v5 rotate trace: {error}"))?;
    if second != StepOutcome::Continued {
        return Err(String::from("v5 rotate fixture did not advance"));
    }
    let trace =
        trace_slot.ok_or_else(|| String::from("v5 rotate trace missing"))?;
    let program =
        ExecutionGeometryRegionEffectProgram::from_profile_step_trace(&trace)
            .map_err(|error| format!("v5 rotate projection: {error:?}"))?;
    Ok((program, checkpoint, verified.geometry()))
}

fn derived_v5_jump_rotate_halt_sequence_fixture(
    word_trits: u8,
) -> Result<DerivedV5SequenceFixture, String> {
    let verified = verify_jump_rotate_halt_profile_width(
        current_profile(),
        b"(&O",
        word_trits,
    )
    .map_err(|error| format!("v5 full-path verification: {error}"))?;
    let mut machine =
        ProfileMachine::from_verified_source(&verified, Vec::new())
            .map_err(|error| format!("v5 full-path machine: {error}"))?;
    let mut programs = Vec::new();
    let mut states = vec![machine.snapshot_state()];
    let mut traces = Vec::new();
    for _index in 0usize..3usize {
        let mut trace_slot = None;
        let _outcome = machine
            .step_traced(&mut |trace| trace_slot = Some(*trace))
            .map_err(|error| format!("v5 full-path trace: {error}"))?;
        let trace = trace_slot
            .ok_or_else(|| String::from("v5 full-path trace missing"))?;
        let program =
            ExecutionGeometryRegionEffectProgram::from_profile_step_trace(
                &trace,
            )
            .map_err(|error| format!("v5 full-path projection: {error:?}"))?;
        programs.push(program);
        states.push(machine.snapshot_state());
        traces.push(trace);
    }
    Ok(DerivedV5SequenceFixture {
        geometry: verified.geometry(),
        programs,
        states,
        traces,
    })
}

fn derived_v5_rotate_halt_sequence_fixture(
    word_trits: u8,
) -> Result<DerivedV5SequenceFixture, String> {
    let verified = verify_jump_rotate_halt_profile_width(
        current_profile(),
        b"(&O",
        word_trits,
    )
    .map_err(|error| format!("v5 rotate/halt verification: {error}"))?;
    let mut machine =
        ProfileMachine::from_verified_source(&verified, Vec::new())
            .map_err(|error| format!("v5 rotate/halt machine: {error}"))?;
    if machine
        .step()
        .map_err(|error| format!("v5 rotate/halt jump: {error}"))?
        != StepOutcome::Continued
    {
        return Err(String::from("v5 rotate/halt jump did not advance"));
    }
    let mut programs = Vec::new();
    let mut states = vec![machine.snapshot_state()];
    let mut traces = Vec::new();
    for _index in 0usize..2usize {
        let mut trace_slot = None;
        let _outcome = machine
            .step_traced(&mut |trace| trace_slot = Some(*trace))
            .map_err(|error| format!("v5 rotate/halt trace: {error}"))?;
        let trace = trace_slot
            .ok_or_else(|| String::from("v5 rotate/halt trace missing"))?;
        let program =
            ExecutionGeometryRegionEffectProgram::from_profile_step_trace(
                &trace,
            )
            .map_err(|error| format!("v5 rotate/halt projection: {error:?}"))?;
        programs.push(program);
        states.push(machine.snapshot_state());
        traces.push(trace);
    }
    Ok(DerivedV5SequenceFixture {
        geometry: verified.geometry(),
        programs,
        states,
        traces,
    })
}

fn derived_v5_noop_halt_sequence_fixture(
    word_trits: u8,
) -> Result<DerivedV5SequenceFixture, String> {
    let verified = verify_noop_prefix_halt_profile_width(
        current_profile(),
        b"DP",
        word_trits,
    )
    .map_err(|error| format!("v5 no-op/halt verification: {error}"))?;
    let mut machine =
        ProfileMachine::from_verified_source(&verified, Vec::new())
            .map_err(|error| format!("v5 no-op/halt machine: {error}"))?;
    let mut programs = Vec::new();
    let mut states = vec![machine.snapshot_state()];
    let mut traces = Vec::new();
    for _index in 0usize..2usize {
        let mut trace_slot = None;
        let _outcome = machine
            .step_traced(&mut |trace| trace_slot = Some(*trace))
            .map_err(|error| format!("v5 no-op/halt trace: {error}"))?;
        let trace = trace_slot
            .ok_or_else(|| String::from("v5 no-op/halt trace missing"))?;
        let program =
            ExecutionGeometryRegionEffectProgram::from_profile_step_trace(
                &trace,
            )
            .map_err(|error| format!("v5 no-op/halt projection: {error:?}"))?;
        programs.push(program);
        states.push(machine.snapshot_state());
        traces.push(trace);
    }
    Ok(DerivedV5SequenceFixture {
        geometry: verified.geometry(),
        programs,
        states,
        traces,
    })
}

fn assert_v5_initial_jump_data_artifact(
    isa: HostIsa,
    n10: &ExecutionGeometryRegionEffectProgram,
    n11: &ExecutionGeometryRegionEffectProgram,
) -> Result<(), String> {
    let n10_artifact = emit_direct_execution_geometry_initial_jump_data_coff(
        n10,
        direct_execution_geometry_initial_jump_data_target(isa),
    )
    .map_err(|error| {
        format!("v5 initial jump-data N10 {isa:?} emit: {error}")
    })?;
    let n11_artifact = emit_direct_execution_geometry_initial_jump_data_coff(
        n11,
        direct_execution_geometry_initial_jump_data_target(isa),
    )
    .map_err(|error| {
        format!("v5 initial jump-data N11 {isa:?} emit: {error}")
    })?;
    if n10_artifact.key() == n11_artifact.key()
        || n10_artifact.object() == n11_artifact.object()
    {
        return Err(String::from(
            "v5 initial jump-data geometry identity collapsed",
        ));
    }
    let verified =
        verify_direct_execution_geometry_initial_jump_data(&n10_artifact, n10)
            .map_err(|error| {
                format!("v5 initial jump-data N10 {isa:?} verify: {error}")
            })?;
    if verified.key() != n10_artifact.key()
        || verified.object() != n10_artifact.object()
        || verified.target_triple() != n10_artifact.target_triple()
    {
        return Err(String::from("v5 initial jump-data verification drifted"));
    }
    if verify_direct_execution_geometry_initial_jump_data(&n10_artifact, n11)
        != Err(DirectExecutionGeometryInitialJumpDataError::ProgramShape)
    {
        return Err(String::from(
            "v5 initial jump-data geometry mismatch admitted",
        ));
    }
    assert_tampered_direct_profile_metadata(&n10_artifact)
}

#[test]
fn direct_execution_geometry_initial_jump_data_admits_exact_v5_geometry()
-> Result<(), String> {
    let (n10, _n10_checkpoint, n10_geometry) =
        derived_v5_initial_jump_data_fixture(10)?;
    let (n11, _n11_checkpoint, _n11_geometry) =
        derived_v5_initial_jump_data_fixture(11)?;
    let [live_in] = n10.memory_live_ins() else {
        return Err(String::from(
            "v5 initial jump-data did not dedupe alias read",
        ));
    };
    let entry = n10.entry_observation().ok_or_else(|| {
        String::from("v5 initial jump-data entry observation missing")
    })?;
    let exit = n10.exit_observation().ok_or_else(|| {
        String::from("v5 initial jump-data exit observation missing")
    })?;
    if entry.registers.code_pointer != entry.registers.data_pointer
        || live_in.address != entry.registers.code_pointer
        || exit.registers.data_pointer != live_in.value.saturating_add(1)
        || n10.execution_geometry().memory_words()
            != n10_geometry.memory_words()
    {
        return Err(String::from(
            "v5 initial jump-data alias contract drifted",
        ));
    }
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        assert_v5_initial_jump_data_artifact(isa, &n10, &n11)?;
    }
    Ok(())
}

#[test]
fn direct_execution_geometry_no_operation_admits_exact_v5_geometry()
-> Result<(), String> {
    let (n10, _n10_checkpoint, _n10_geometry) =
        derived_v5_no_operation_fixture(10)?;
    let (n11, _n11_checkpoint, _n11_geometry) =
        derived_v5_no_operation_fixture(11)?;
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        let n10_artifact = emit_direct_execution_geometry_no_operation_coff(
            &n10,
            direct_execution_geometry_no_operation_target(isa),
        )
        .map_err(|error| format!("v5 no-op N10 {isa:?} emit: {error}"))?;
        let n11_artifact = emit_direct_execution_geometry_no_operation_coff(
            &n11,
            direct_execution_geometry_no_operation_target(isa),
        )
        .map_err(|error| format!("v5 no-op N11 {isa:?} emit: {error}"))?;
        if n10_artifact.key().ir().execution_geometry()
            != Some(n10.execution_geometry())
            || n10_artifact.key() == n11_artifact.key()
            || n10_artifact.object() == n11_artifact.object()
        {
            return Err(String::from("v5 no-op geometry identity collapsed"));
        }
        let verified =
            verify_direct_execution_geometry_no_operation(&n10_artifact, &n10)
                .map_err(|error| {
                    format!("v5 no-op N10 {isa:?} verify: {error}")
                })?;
        if verified.key() != n10_artifact.key()
            || verified.object() != n10_artifact.object()
            || verified.target_triple() != n10_artifact.target_triple()
        {
            return Err(String::from("v5 no-op verification drifted"));
        }
        if verify_direct_execution_geometry_no_operation(&n10_artifact, &n11)
            != Err(DirectExecutionGeometryNoOperationError::ProgramShape)
        {
            return Err(String::from("v5 no-op geometry mismatch admitted"));
        }
    }
    Ok(())
}

#[test]
fn direct_execution_geometry_rotate_admits_exact_v5_geometry()
-> Result<(), String> {
    let (n10, _n10_checkpoint, n10_geometry) = derived_v5_rotate_fixture(10)?;
    let (n11, _n11_checkpoint, _n11_geometry) = derived_v5_rotate_fixture(11)?;
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        let n10_artifact = emit_direct_execution_geometry_rotate_coff(
            &n10,
            direct_execution_geometry_rotate_target(isa),
        )
        .map_err(|error| format!("v5 rotate N10 {isa:?} emit: {error}"))?;
        let n11_artifact = emit_direct_execution_geometry_rotate_coff(
            &n11,
            direct_execution_geometry_rotate_target(isa),
        )
        .map_err(|error| format!("v5 rotate N11 {isa:?} emit: {error}"))?;
        if n10_artifact.key().ir().execution_geometry()
            != Some(n10.execution_geometry())
            || n10.execution_geometry().memory_words()
                != n10_geometry.memory_words()
            || n10_artifact.key() == n11_artifact.key()
            || n10_artifact.object() == n11_artifact.object()
        {
            return Err(String::from("v5 rotate geometry identity collapsed"));
        }
        let verified =
            verify_direct_execution_geometry_rotate(&n10_artifact, &n10)
                .map_err(|error| {
                    format!("v5 rotate N10 {isa:?} verify: {error}")
                })?;
        if verified.key() != n10_artifact.key()
            || verified.object() != n10_artifact.object()
            || verified.target_triple() != n10_artifact.target_triple()
        {
            return Err(String::from("v5 rotate verification drifted"));
        }
        if verify_direct_execution_geometry_rotate(&n10_artifact, &n11)
            != Err(DirectExecutionGeometryRotateError::ProgramShape)
        {
            return Err(String::from("v5 rotate geometry mismatch admitted"));
        }
        assert_tampered_direct_profile_metadata(&n10_artifact)?;
    }
    Ok(())
}

#[test]
fn direct_execution_geometry_initial_halt_admits_exact_v5_geometry()
-> Result<(), String> {
    let (n10, _n10_checkpoint, _n10_geometry) = derived_v5_handoff_fixture(10)?;
    let (n11, _n11_checkpoint, _n11_geometry) = derived_v5_handoff_fixture(11)?;
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        let n10_artifact = emit_direct_execution_geometry_initial_halt_coff(
            &n10,
            direct_execution_geometry_initial_halt_target(isa),
        )
        .map_err(|error| format!("v5 N10 {isa:?} emit: {error}"))?;
        let n11_artifact = emit_direct_execution_geometry_initial_halt_coff(
            &n11,
            direct_execution_geometry_initial_halt_target(isa),
        )
        .map_err(|error| format!("v5 N11 {isa:?} emit: {error}"))?;
        let mbpf_v5 = b"MBPF\x05\x00";
        if n10_artifact.key().ir().execution_geometry()
            != Some(n10.execution_geometry())
            || n10_artifact.key().ir().format_version()
                != EFFECT_IR_EXECUTION_GEOMETRY_VERSION
            || n10_artifact.object() == n11_artifact.object()
            || !n10_artifact
                .object()
                .windows(mbpf_v5.len())
                .any(|window| window == mbpf_v5)
        {
            return Err(String::from("v5 native object lost exact geometry"));
        }
        let verified =
            verify_direct_execution_geometry_initial_halt(&n10_artifact, &n10)
                .map_err(|error| format!("v5 N10 {isa:?} verify: {error}"))?;
        let image =
            VerifiedExecutionGeometryLoadImage::from_initial_halt(&verified)
                .map_err(|error| {
                    format!("v5 N10 {isa:?} load image: {error}")
                })?;
        if verified.object() != n10_artifact.object()
            || verified.key() != n10_artifact.key()
            || image.key() != verified.key()
            || image.host_isa() != isa
            || image.code().is_empty()
            || image.entry_code().is_empty()
            || image.allocation_len() != image.code().len()
            || image.target_triple() != verified.target_triple()
        {
            return Err(String::from(
                "v5 verified artifact/load image drifted",
            ));
        }
        if verify_direct_execution_geometry_initial_halt(&n10_artifact, &n11)
            != Err(DirectExecutionGeometryInitialHaltError::ProgramShape)
        {
            return Err(String::from(
                "v5 artifact admitted different geometry",
            ));
        }
        assert_tampered_direct_profile_metadata(&n10_artifact)?;
    }
    Ok(())
}

#[test]
fn execution_geometry_native_lifecycle_retains_v5_identity()
-> Result<(), String> {
    let (program, _checkpoint, _geometry) = derived_v5_handoff_fixture(10)?;
    let artifact = emit_direct_execution_geometry_initial_halt_coff(
        &program,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 lifecycle emit: {error}"))?;
    let verified =
        verify_direct_execution_geometry_initial_halt(&artifact, &program)
            .map_err(|error| format!("v5 lifecycle verify: {error}"))?;
    let image =
        VerifiedExecutionGeometryLoadImage::from_initial_halt(&verified)
            .map_err(|error| format!("v5 lifecycle image: {error}"))?;
    let mapping_id = NativeExecutableMappingId::new(91)
        .ok_or_else(|| String::from("v5 lifecycle mapping id invalid"))?;
    let base = NonZeroUsize::new(0x9000)
        .ok_or_else(|| String::from("v5 lifecycle base invalid"))?;
    let writable = NativeExecutableMappingReport::new(
        mapping_id,
        base,
        image.allocation_len(),
        NativeExecutablePermission::ReadWrite,
    );
    let staged = StagedExecutionGeometryNativeExecutable::stage(
        &image,
        writable,
        image.code(),
    )
    .map_err(|error| format!("v5 lifecycle stage: {error}"))?;
    let executable = staged
        .admit_read_execute(NativeExecutableMappingReport::new(
            mapping_id,
            base,
            image.allocation_len(),
            NativeExecutablePermission::ReadExecute,
        ))
        .map_err(|error| format!("v5 lifecycle protect: {error}"))?
        .admit_instruction_sync(NativeInstructionSyncReport::new(
            mapping_id,
            base,
            image.allocation_len(),
        ))
        .map_err(|error| format!("v5 lifecycle sync: {error}"))?;
    if executable.key() == verified.key()
        && executable.image() == &image
        && executable.mapping().mapping_id() == mapping_id
        && executable.entry_address() == base
        && executable.target() == verified.key().target()
        && executable.release_request().mapping_id() == mapping_id
    {
        Ok(())
    } else {
        Err(String::from("v5 lifecycle changed exact artifact identity"))
    }
}

#[test]
fn geometry_native_lifecycle_rejects_code_drift() -> Result<(), String> {
    let (program, _checkpoint, _geometry) = derived_v5_handoff_fixture(10)?;
    let artifact = emit_direct_execution_geometry_initial_halt_coff(
        &program,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 lifecycle drift emit: {error}"))?;
    let verified =
        verify_direct_execution_geometry_initial_halt(&artifact, &program)
            .map_err(|error| format!("v5 lifecycle drift verify: {error}"))?;
    let image =
        VerifiedExecutionGeometryLoadImage::from_initial_halt(&verified)
            .map_err(|error| format!("v5 lifecycle drift image: {error}"))?;
    let mapping_id = NativeExecutableMappingId::new(92)
        .ok_or_else(|| String::from("v5 lifecycle drift id invalid"))?;
    let base = NonZeroUsize::new(0xa000)
        .ok_or_else(|| String::from("v5 lifecycle drift base invalid"))?;
    let mapping = NativeExecutableMappingReport::new(
        mapping_id,
        base,
        image.allocation_len(),
        NativeExecutablePermission::ReadWrite,
    );
    let mut copied = image.code().to_vec();
    let first = copied
        .first_mut()
        .ok_or_else(|| String::from("v5 lifecycle code unexpectedly empty"))?;
    *first ^= 1;
    if StagedExecutionGeometryNativeExecutable::stage(&image, mapping, &copied)
        == Err(NativeExecutableLifecycleError::CodeImage)
    {
        Ok(())
    } else {
        Err(String::from("v5 lifecycle admitted copied-code drift"))
    }
}

#[test]
fn geometry_native_platform_loads_and_releases_exact_image()
-> Result<(), String> {
    let (program, _checkpoint, _geometry) = derived_v5_handoff_fixture(10)?;
    let artifact = emit_direct_execution_geometry_initial_halt_coff(
        &program,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 platform emit: {error}"))?;
    let verified =
        verify_direct_execution_geometry_initial_halt(&artifact, &program)
            .map_err(|error| format!("v5 platform verify: {error}"))?;
    let image =
        VerifiedExecutionGeometryLoadImage::from_initial_halt(&verified)
            .map_err(|error| format!("v5 platform image: {error}"))?;
    let mapping_id = native_executable_mapping_id(93)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        mapping_id,
        native_executable_address(0xb000)?,
    );
    let ready = load_execution_geometry_native_executable(&mut adapter, &image)
        .map_err(|error| format!("v5 platform load: {error}"))?;
    if ready.key() != verified.key()
        || ready.image() != &image
        || adapter.operations
            != [
                FakeNativeAdapterOperation::Allocate,
                FakeNativeAdapterOperation::Copy,
                FakeNativeAdapterOperation::Protect,
                FakeNativeAdapterOperation::Synchronize,
            ]
    {
        return Err(String::from("v5 platform load evidence drifted"));
    }
    let release = ready.release_request();
    release_execution_geometry_native_executable(&mut adapter, ready)
        .map_err(|error| format!("v5 platform release: {error}"))?;
    if adapter.release_requests == [release]
        && adapter.operations.last()
            == Some(&FakeNativeAdapterOperation::Release)
    {
        Ok(())
    } else {
        Err(String::from("v5 platform release evidence drifted"))
    }
}

#[test]
fn geometry_native_platform_cleans_up_copy_failure() -> Result<(), String> {
    let (program, _checkpoint, _geometry) = derived_v5_handoff_fixture(10)?;
    let artifact = emit_direct_execution_geometry_initial_halt_coff(
        &program,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 cleanup emit: {error}"))?;
    let verified =
        verify_direct_execution_geometry_initial_halt(&artifact, &program)
            .map_err(|error| format!("v5 cleanup verify: {error}"))?;
    let image =
        VerifiedExecutionGeometryLoadImage::from_initial_halt(&verified)
            .map_err(|error| format!("v5 cleanup image: {error}"))?;
    let mapping_id = native_executable_mapping_id(94)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        mapping_id,
        native_executable_address(0xc000)?,
    )
    .with_failure(FakeNativeAdapterOperation::Copy);
    let Err(error) =
        load_execution_geometry_native_executable(&mut adapter, &image)
    else {
        return Err(String::from("v5 copy failure was ignored"));
    };
    if error.phase() == NativeExecutableLoadPhase::Copy
        && error.adapter_error() == Some(&FakeNativeAdapterOperation::Copy)
        && error.release_error().is_none()
        && error.release_request() == adapter.release_requests.first().copied()
        && adapter.operations
            == [
                FakeNativeAdapterOperation::Allocate,
                FakeNativeAdapterOperation::Copy,
                FakeNativeAdapterOperation::Release,
            ]
    {
        Ok(())
    } else {
        Err(String::from("v5 copy failure cleanup evidence drifted"))
    }
}

#[test]
fn execution_geometry_native_admission_binds_opaque_checkpoint()
-> Result<(), String> {
    let (program, checkpoint, geometry) = derived_v5_handoff_fixture(10)?;
    let artifact = emit_direct_execution_geometry_initial_halt_coff(
        &program,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 admission emit: {error}"))?;
    let verified =
        verify_direct_execution_geometry_initial_halt(&artifact, &program)
            .map_err(|error| format!("v5 admission verify: {error}"))?;
    let expected_key = verified.key().clone();
    let expected_program = program.clone();
    let expected_checkpoint = checkpoint.clone();
    let admission = ExecutionGeometryNativeInitialHaltAdmission::new(
        program, checkpoint, verified,
    )
    .map_err(|error| format!("v5 checkpoint admission: {error}"))?;
    if admission.program() == &expected_program
        && admission.checkpoint() == &expected_checkpoint
        && admission.checkpoint().geometry() == geometry
        && admission.artifact().key() == &expected_key
        && admission.load_image().key() == &expected_key
    {
        Ok(())
    } else {
        Err(String::from("v5 checkpoint-native binding drifted"))
    }
}

#[test]
fn execution_geometry_native_admission_rejects_artifact_geometry_drift()
-> Result<(), String> {
    let (n10, n10_checkpoint, _n10_geometry) = derived_v5_handoff_fixture(10)?;
    let (n11, _n11_checkpoint, _n11_geometry) = derived_v5_handoff_fixture(11)?;
    let artifact = emit_direct_execution_geometry_initial_halt_coff(
        &n11,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 drift emit: {error}"))?;
    let verified =
        verify_direct_execution_geometry_initial_halt(&artifact, &n11)
            .map_err(|error| format!("v5 drift verify: {error}"))?;
    if ExecutionGeometryNativeInitialHaltAdmission::new(
        n10,
        n10_checkpoint,
        verified,
    ) == Err(
        ExecutionGeometryNativeInitialHaltAdmissionError::ArtifactIdentity,
    ) {
        Ok(())
    } else {
        Err(String::from(
            "v5 admission accepted artifact geometry drift",
        ))
    }
}

#[test]
fn execution_geometry_native_admission_rejects_checkpoint_geometry_drift()
-> Result<(), String> {
    let (n10, _n10_checkpoint, _n10_geometry) = derived_v5_handoff_fixture(10)?;
    let (_n11, n11_checkpoint, _n11_geometry) = derived_v5_handoff_fixture(11)?;
    let artifact = emit_direct_execution_geometry_initial_halt_coff(
        &n10,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 checkpoint drift emit: {error}"))?;
    let verified =
        verify_direct_execution_geometry_initial_halt(&artifact, &n10)
            .map_err(|error| format!("v5 checkpoint drift verify: {error}"))?;
    let expected = ExecutionGeometryNativeInitialHaltAdmissionError::Checkpoint(
        ExecutionGeometryHandoffAdmissionError::CheckpointGeometry,
    );
    if ExecutionGeometryNativeInitialHaltAdmission::new(
        n10,
        n11_checkpoint,
        verified,
    ) == Err(expected)
    {
        Ok(())
    } else {
        Err(String::from("v5 admission ignored opaque geometry drift"))
    }
}

fn full_lru_sequences() -> Result<FullGeometrySequenceTriple, String> {
    let n10 = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let n11 = derived_v5_jump_rotate_halt_sequence_fixture(11)?;
    let n12 = derived_v5_jump_rotate_halt_sequence_fixture(12)?;
    Ok((
        geometry_native_jump_rotate_halt_sequence(&n10)?,
        geometry_native_jump_rotate_halt_sequence(&n11)?,
        geometry_native_jump_rotate_halt_sequence(&n12)?,
    ))
}

fn full_lru_cache(capacity: usize) -> Result<FullLruCache, String> {
    Ok(FullLruCache::new(nonzero_test_limit(
        capacity,
        "v5 full LRU capacity",
    )?))
}

fn full_lru_cleanup_retains_all(
    cleanup: &FullGeometryTripleReleaseFailure<FakeNativeAdapterOperation>,
) -> bool {
    let Some(suffix) = cleanup.suffix_failure() else {
        return false;
    };
    cleanup.initial_jump_failure().is_some()
        && suffix.halt_failure().is_some()
        && suffix.rotate_failure().is_some()
}

fn full_lru_contains_only(
    cache: &FullLruCache,
    expected: &FullGeometrySequence,
    absent_a: &FullGeometrySequence,
    absent_b: &FullGeometrySequence,
) -> bool {
    cache.resident_count() == 1
        && cache.contains(expected)
        && !cache.contains(absent_a)
        && !cache.contains(absent_b)
}

fn geometry_native_jump_rotate_halt_evidence(
    jump_fixture: &DerivedV5SequenceFixture,
    suffix_fixture: &DerivedV5SequenceFixture,
) -> Result<FullGeometryEvidence, String> {
    let initial_jump = jump_fixture
        .programs
        .first()
        .cloned()
        .ok_or_else(|| String::from("v5 full-path jump missing"))?;
    let rotate = suffix_fixture
        .programs
        .get(1)
        .cloned()
        .ok_or_else(|| String::from("v5 full-path rotate missing"))?;
    let halt = suffix_fixture
        .programs
        .get(2)
        .cloned()
        .ok_or_else(|| String::from("v5 full-path halt missing"))?;
    let jump_object = emit_direct_execution_geometry_initial_jump_data_coff(
        &initial_jump,
        direct_execution_geometry_initial_jump_data_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 full-path jump emit: {error}"))?;
    let jump_artifact = verify_direct_execution_geometry_initial_jump_data(
        &jump_object,
        &initial_jump,
    )
    .map_err(|error| format!("v5 full-path jump verify: {error}"))?;
    let rotate_object = emit_direct_execution_geometry_rotate_coff(
        &rotate,
        direct_execution_geometry_rotate_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 full-path rotate emit: {error}"))?;
    let rotate_artifact =
        verify_direct_execution_geometry_rotate(&rotate_object, &rotate)
            .map_err(|error| format!("v5 full-path rotate verify: {error}"))?;
    let halt_object = emit_direct_execution_geometry_initial_halt_coff(
        &halt,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 full-path halt emit: {error}"))?;
    let halt_artifact =
        verify_direct_execution_geometry_initial_halt(&halt_object, &halt)
            .map_err(|error| format!("v5 full-path halt verify: {error}"))?;
    let suffix = ExecutionGeometryNativeRotateHaltEvidence::new(
        rotate,
        rotate_artifact,
        halt,
        halt_artifact,
    );
    Ok(FullGeometryEvidence::new(
        initial_jump,
        jump_artifact,
        suffix,
    ))
}

fn geometry_native_jump_rotate_halt_sequence(
    fixture: &DerivedV5SequenceFixture,
) -> Result<FullGeometrySequence, String> {
    let checkpoint = fixture
        .states
        .first()
        .cloned()
        .ok_or_else(|| String::from("v5 full-path checkpoint missing"))?;
    let evidence = geometry_native_jump_rotate_halt_evidence(fixture, fixture)?;
    FullGeometrySequence::new(evidence, checkpoint)
        .map_err(|error| error.to_string())
}

fn geometry_native_rotate_halt_sequence(
    fixture: &DerivedV5SequenceFixture,
) -> Result<ExecutionGeometryNativeRotateHaltSequence, String> {
    let rotate = fixture
        .programs
        .first()
        .cloned()
        .ok_or_else(|| String::from("v5 rotate/halt rotate missing"))?;
    let halt = fixture
        .programs
        .get(1)
        .cloned()
        .ok_or_else(|| String::from("v5 rotate/halt halt missing"))?;
    let checkpoint = fixture
        .states
        .first()
        .cloned()
        .ok_or_else(|| String::from("v5 rotate/halt checkpoint missing"))?;
    let rotate_object = emit_direct_execution_geometry_rotate_coff(
        &rotate,
        direct_execution_geometry_rotate_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 rotate/halt rotate emit: {error}"))?;
    let rotate_artifact =
        verify_direct_execution_geometry_rotate(&rotate_object, &rotate)
            .map_err(|error| {
                format!("v5 rotate/halt rotate verify: {error}")
            })?;
    let halt_object = emit_direct_execution_geometry_initial_halt_coff(
        &halt,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 rotate/halt halt emit: {error}"))?;
    let halt_artifact =
        verify_direct_execution_geometry_initial_halt(&halt_object, &halt)
            .map_err(|error| format!("v5 rotate/halt halt verify: {error}"))?;
    let evidence = ExecutionGeometryNativeRotateHaltEvidence::new(
        rotate,
        rotate_artifact,
        halt,
        halt_artifact,
    );
    ExecutionGeometryNativeRotateHaltSequence::new(evidence, checkpoint)
        .map_err(|error| error.to_string())
}

fn geometry_native_noop_halt_sequence(
    fixture: &DerivedV5SequenceFixture,
) -> Result<ExecutionGeometryNativeNoopHaltSequence, String> {
    let no_operation = fixture
        .programs
        .first()
        .cloned()
        .ok_or_else(|| String::from("v5 sequence no-operation missing"))?;
    let halt = fixture
        .programs
        .get(1)
        .cloned()
        .ok_or_else(|| String::from("v5 sequence halt missing"))?;
    let checkpoint = fixture
        .states
        .first()
        .cloned()
        .ok_or_else(|| String::from("v5 sequence checkpoint missing"))?;
    let no_operation_object = emit_direct_execution_geometry_no_operation_coff(
        &no_operation,
        direct_execution_geometry_no_operation_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 sequence no-operation emit: {error}"))?;
    let no_operation_artifact = verify_direct_execution_geometry_no_operation(
        &no_operation_object,
        &no_operation,
    )
    .map_err(|error| format!("v5 sequence no-operation verify: {error}"))?;
    let halt_object = emit_direct_execution_geometry_initial_halt_coff(
        &halt,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 sequence halt emit: {error}"))?;
    let halt_artifact =
        verify_direct_execution_geometry_initial_halt(&halt_object, &halt)
            .map_err(|error| format!("v5 sequence halt verify: {error}"))?;
    let evidence = ExecutionGeometryNativeNoopHaltEvidence::new(
        no_operation,
        no_operation_artifact,
        halt,
        halt_artifact,
    );
    ExecutionGeometryNativeNoopHaltSequence::new(evidence, checkpoint)
        .map_err(|error| error.to_string())
}

fn load_geometry_native_jump_rotate_halt_triple(
    adapter: &mut FakeNativeExecutableAdapter,
    sequence: &FullGeometrySequence,
) -> Result<GeometryNativeJumpRotateHaltReadyTriple, String> {
    let initial_jump = load_execution_geometry_native_executable(
        adapter,
        sequence.initial_jump().load_image(),
    )
    .map_err(|error| format!("v5 full prebind jump load: {error}"))?;
    let rotate = load_execution_geometry_native_executable(
        adapter,
        sequence.suffix().rotate().load_image(),
    )
    .map_err(|error| format!("v5 full prebind rotate load: {error}"))?;
    let halt = load_execution_geometry_native_executable(
        adapter,
        sequence.suffix().halt().load_image(),
    )
    .map_err(|error| format!("v5 full prebind halt load: {error}"))?;
    Ok((initial_jump, rotate, halt))
}

fn load_geometry_native_rotate_halt_pair(
    adapter: &mut FakeNativeExecutableAdapter,
    sequence: &ExecutionGeometryNativeRotateHaltSequence,
) -> Result<GeometryNativeRotateHaltReadyPair, String> {
    let rotate = load_execution_geometry_native_executable(
        adapter,
        sequence.rotate().load_image(),
    )
    .map_err(|error| format!("v5 reusable rotate load: {error}"))?;
    let halt = load_execution_geometry_native_executable(
        adapter,
        sequence.halt().load_image(),
    )
    .map_err(|error| format!("v5 reusable halt load: {error}"))?;
    Ok((rotate, halt))
}

fn load_geometry_native_noop_halt_pair(
    adapter: &mut FakeNativeExecutableAdapter,
    sequence: &ExecutionGeometryNativeNoopHaltSequence,
) -> Result<GeometryNativeNoopHaltReadyPair, String> {
    let no_operation = load_execution_geometry_native_executable(
        adapter,
        sequence.no_operation().load_image(),
    )
    .map_err(|error| format!("v5 reusable no-op load: {error}"))?;
    let halt = load_execution_geometry_native_executable(
        adapter,
        sequence.halt().load_image(),
    )
    .map_err(|error| format!("v5 reusable halt load: {error}"))?;
    Ok((no_operation, halt))
}

fn geometry_native_initial_jump_data_admission_fixture(
    word_trits: u8,
) -> Result<GeometryNativeInitialJumpDataAdmissionFixture, String> {
    let (program, checkpoint, geometry) =
        derived_v5_initial_jump_data_fixture(word_trits)?;
    let artifact = emit_direct_execution_geometry_initial_jump_data_coff(
        &program,
        direct_execution_geometry_initial_jump_data_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 initial jump admission emit: {error}"))?;
    let verified =
        verify_direct_execution_geometry_initial_jump_data(&artifact, &program)
            .map_err(|error| {
                format!("v5 initial jump admission verify: {error}")
            })?;
    let admission = InitialJumpAdmission::new(program, checkpoint, verified)
        .map_err(|error| format!("v5 initial jump admission: {error}"))?;
    Ok((admission, geometry))
}

fn geometry_native_initial_jump_data_runner_fixture(
    word_trits: u8,
    mapping_value: u64,
    base_value: usize,
) -> Result<GeometryNativeInitialJumpDataRunnerFixture, String> {
    let (admission, geometry) =
        geometry_native_initial_jump_data_admission_fixture(word_trits)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(mapping_value)?,
        native_executable_address(base_value)?,
    );
    let ready = load_execution_geometry_native_executable(
        &mut adapter,
        admission.load_image(),
    )
    .map_err(|error| format!("v5 initial jump runner load: {error}"))?;
    Ok(GeometryNativeInitialJumpDataRunnerFixture {
        adapter,
        admission,
        geometry,
        ready,
    })
}

fn geometry_native_no_operation_admission_fixture(
    word_trits: u8,
) -> Result<GeometryNativeNoOperationAdmissionFixture, String> {
    let (program, checkpoint, geometry) =
        derived_v5_no_operation_fixture(word_trits)?;
    let artifact = emit_direct_execution_geometry_no_operation_coff(
        &program,
        direct_execution_geometry_no_operation_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 no-op admission emit: {error}"))?;
    let verified =
        verify_direct_execution_geometry_no_operation(&artifact, &program)
            .map_err(|error| format!("v5 no-op admission verify: {error}"))?;
    let admission = ExecutionGeometryNativeNoOperationAdmission::new(
        program, checkpoint, verified,
    )
    .map_err(|error| format!("v5 no-op admission: {error}"))?;
    Ok((admission, geometry))
}

fn geometry_native_no_operation_runner_fixture(
    word_trits: u8,
    mapping_value: u64,
    base_value: usize,
) -> Result<GeometryNativeNoOperationRunnerFixture, String> {
    let (admission, geometry) =
        geometry_native_no_operation_admission_fixture(word_trits)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(mapping_value)?,
        native_executable_address(base_value)?,
    );
    let ready = load_execution_geometry_native_executable(
        &mut adapter,
        admission.load_image(),
    )
    .map_err(|error| format!("v5 no-op runner load: {error}"))?;
    Ok(GeometryNativeNoOperationRunnerFixture {
        adapter,
        admission,
        geometry,
        ready,
    })
}

fn geometry_native_rotate_admission_fixture(
    word_trits: u8,
) -> Result<GeometryNativeRotateAdmissionFixture, String> {
    let (program, checkpoint, geometry) =
        derived_v5_rotate_fixture(word_trits)?;
    let artifact = emit_direct_execution_geometry_rotate_coff(
        &program,
        direct_execution_geometry_rotate_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 rotate admission emit: {error}"))?;
    let verified = verify_direct_execution_geometry_rotate(&artifact, &program)
        .map_err(|error| format!("v5 rotate admission verify: {error}"))?;
    let admission = ExecutionGeometryNativeRotateAdmission::new(
        program, checkpoint, verified,
    )
    .map_err(|error| format!("v5 rotate admission: {error}"))?;
    Ok((admission, geometry))
}

fn geometry_native_rotate_runner_fixture(
    word_trits: u8,
    mapping_value: u64,
    base_value: usize,
) -> Result<GeometryNativeRotateRunnerFixture, String> {
    let (admission, geometry) =
        geometry_native_rotate_admission_fixture(word_trits)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(mapping_value)?,
        native_executable_address(base_value)?,
    );
    let ready = load_execution_geometry_native_executable(
        &mut adapter,
        admission.load_image(),
    )
    .map_err(|error| format!("v5 rotate runner load: {error}"))?;
    Ok(GeometryNativeRotateRunnerFixture {
        adapter,
        admission,
        geometry,
        ready,
    })
}

fn geometry_native_admission_fixture(
    word_trits: u8,
) -> Result<GeometryNativeAdmissionFixture, String> {
    let (program, checkpoint, geometry) =
        derived_v5_handoff_fixture(word_trits)?;
    let artifact = emit_direct_execution_geometry_initial_halt_coff(
        &program,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 transaction emit: {error}"))?;
    let verified =
        verify_direct_execution_geometry_initial_halt(&artifact, &program)
            .map_err(|error| format!("v5 transaction verify: {error}"))?;
    let admission = ExecutionGeometryNativeInitialHaltAdmission::new(
        program, checkpoint, verified,
    )
    .map_err(|error| format!("v5 transaction admission: {error}"))?;
    Ok((admission, geometry))
}

fn geometry_native_runner_fixture(
    word_trits: u8,
    mapping_value: u64,
    base_value: usize,
) -> Result<GeometryNativeRunnerFixture, String> {
    let (admission, geometry) = geometry_native_admission_fixture(word_trits)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(mapping_value)?,
        native_executable_address(base_value)?,
    );
    let ready = load_execution_geometry_native_executable(
        &mut adapter,
        admission.load_image(),
    )
    .map_err(|error| format!("v5 runner load: {error}"))?;
    Ok(GeometryNativeRunnerFixture {
        adapter,
        admission,
        geometry,
        ready,
    })
}

#[test]
fn geometry_native_rotate_halt_loaded_rejects_mixed_ready_before_execution()
-> Result<(), String> {
    let n10_fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_rotate_halt_sequence_fixture(11)?;
    let n10 = geometry_native_rotate_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_rotate_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(116)?,
        native_executable_address(0x2_2000)?,
    );
    let rotate = load_execution_geometry_native_executable(
        &mut adapter,
        n10.rotate().load_image(),
    )
    .map_err(|error| format!("v5 loaded N10 no-op: {error}"))?;
    let halt = load_execution_geometry_native_executable(
        &mut adapter,
        n11.halt().load_image(),
    )
    .map_err(|error| format!("v5 loaded N11 halt: {error}"))?;
    let rejected = matches!(
        n10.bind_executables(&rotate, &halt),
        Err(ExecutionGeometryNativeRotateHaltExecutableBindingError::Halt)
    );
    release_execution_geometry_native_executable(&mut adapter, rotate)
        .map_err(|error| format!("v5 loaded N10 no-op release: {error}"))?;
    release_execution_geometry_native_executable(&mut adapter, halt)
        .map_err(|error| format!("v5 loaded N11 halt release: {error}"))?;
    if rejected {
        Ok(())
    } else {
        Err(String::from("v5 mixed ready pair was prebound"))
    }
}

#[test]
fn geometry_native_rotate_halt_pair_load_failure_releases_prefix()
-> Result<(), String> {
    let fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_rotate_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(120)?,
        native_executable_address(0x2_6000)?,
    )
    .with_failure_at(FakeNativeAdapterOperation::Allocate, 2);
    let Err(failure) = sequence.load_pair(&mut adapter) else {
        return Err(String::from("v5 pair halt load failure was ignored"));
    };
    let ExecutionGeometryNativeRotateHaltPairLoadFailure::Halt {
        error,
        rotate_release_failure,
    } = *failure
    else {
        return Err(String::from("v5 pair load failure phase drifted"));
    };
    if error.phase() == NativeExecutableLoadPhase::Allocate
        && rotate_release_failure.is_none()
        && adapter.release_requests.len() == 1
        && adapter.operations.last()
            == Some(&FakeNativeAdapterOperation::Release)
    {
        Ok(())
    } else {
        Err(String::from("v5 pair partial load rollback drifted"))
    }
}

#[test]
fn geometry_native_rotate_halt_pair_reuses_owned_executables()
-> Result<(), String> {
    let fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_rotate_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 owned pair initial state missing"))?;
    let final_state = fixture
        .states
        .get(2)
        .ok_or_else(|| String::from("v5 owned pair final state missing"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(119)?,
        native_executable_address(0x2_5000)?,
    );
    let loaded = sequence
        .load_pair(&mut adapter)
        .map_err(|error| format!("v5 owned pair load: {error}"))?;
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    for _iteration in 0usize..2usize {
        let mut memory = initial.memory().to_vec();
        let input = initial.io().input().to_vec();
        let mut output = initial.io().output().to_vec();
        let outcome = loaded
            .execute(
                &mut runner,
                NativeRegionBuffers::new(&mut memory, &input, &mut output),
            )
            .map_err(|error| format!("v5 owned pair execute: {error}"))?;
        if outcome.state() != final_state || memory != final_state.memory() {
            return Err(String::from("v5 owned pair execution drifted"));
        }
    }
    if runner.calls != 4 || adapter.operations.len() != 8 {
        return Err(String::from("v5 owned pair remapped during reuse"));
    }
    loaded
        .release(&mut adapter)
        .map_err(|error| format!("v5 owned pair release: {error}"))?;
    if adapter.operations.len() == 10 {
        Ok(())
    } else {
        Err(String::from("v5 owned pair release count drifted"))
    }
}

#[test]
fn geometry_native_rotate_halt_loaded_reuses_two_ready_executables()
-> Result<(), String> {
    let fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_rotate_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 loaded initial state missing"))?;
    let final_state = fixture
        .states
        .get(2)
        .ok_or_else(|| String::from("v5 loaded final state missing"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(118)?,
        native_executable_address(0x2_4000)?,
    );
    let (rotate, halt) =
        load_geometry_native_rotate_halt_pair(&mut adapter, &sequence)?;
    {
        let bound = sequence
            .bind_executables(&rotate, &halt)
            .map_err(|error| format!("v5 reusable bind: {error}"))?;
        let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::Applied,
        ]);
        for _iteration in 0usize..2usize {
            let mut memory = initial.memory().to_vec();
            let input = initial.io().input().to_vec();
            let mut output = initial.io().output().to_vec();
            let outcome = bound
                .execute(
                    &mut runner,
                    NativeRegionBuffers::new(&mut memory, &input, &mut output),
                )
                .map_err(|error| format!("v5 reusable execute: {error}"))?;
            if outcome.state() != final_state || memory != final_state.memory()
            {
                return Err(String::from("v5 loaded reuse result drifted"));
            }
        }
        if runner.calls != 4 || adapter.operations.len() != 8 {
            return Err(String::from("v5 loaded reuse remapped executables"));
        }
    }
    release_execution_geometry_native_executable(&mut adapter, rotate)
        .map_err(|error| format!("v5 reusable no-op release: {error}"))?;
    release_execution_geometry_native_executable(&mut adapter, halt)
        .map_err(|error| format!("v5 reusable halt release: {error}"))?;
    if adapter.operations.len() == 10 {
        Ok(())
    } else {
        Err(String::from("v5 reusable releases drifted"))
    }
}

#[test]
fn geometry_native_rotate_halt_loaded_late_failure_retains_prefix()
-> Result<(), String> {
    let fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_rotate_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 loaded initial state missing"))?;
    let prefix = fixture
        .states
        .get(1)
        .ok_or_else(|| String::from("v5 loaded prefix state missing"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(117)?,
        native_executable_address(0x2_3000)?,
    );
    let rotate = load_execution_geometry_native_executable(
        &mut adapter,
        sequence.rotate().load_image(),
    )
    .map_err(|error| format!("v5 loaded late no-op: {error}"))?;
    let halt = load_execution_geometry_native_executable(
        &mut adapter,
        sequence.halt().load_image(),
    )
    .map_err(|error| format!("v5 loaded late halt: {error}"))?;
    {
        let bound = sequence
            .bind_executables(&rotate, &halt)
            .map_err(|error| format!("v5 loaded late bind: {error}"))?;
        let mut memory = initial.memory().to_vec();
        let input = initial.io().input().to_vec();
        let mut output = initial.io().output().to_vec();
        let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::FailureAfterMutation,
        ]);
        let Err(failure) = bound.execute(
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        ) else {
            return Err(String::from("v5 loaded late failure was ignored"));
        };
        if failure.index() != 1
            || failure.state() != prefix
            || memory != prefix.memory()
            || !matches!(failure.cause(), RHLoadedCause::HaltExecution(_error,))
            || adapter.operations.len() != 8
        {
            return Err(String::from("v5 loaded late failure lost prefix"));
        }
    }
    release_execution_geometry_native_executable(&mut adapter, rotate)
        .map_err(|error| format!("v5 loaded late no-op release: {error}"))?;
    release_execution_geometry_native_executable(&mut adapter, halt)
        .map_err(|error| format!("v5 loaded late halt release: {error}"))
}

#[test]
fn geometry_native_noop_halt_loaded_rejects_mixed_ready_before_execution()
-> Result<(), String> {
    let n10_fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_noop_halt_sequence_fixture(11)?;
    let n10 = geometry_native_noop_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_noop_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(116)?,
        native_executable_address(0x2_2000)?,
    );
    let no_operation = load_execution_geometry_native_executable(
        &mut adapter,
        n10.no_operation().load_image(),
    )
    .map_err(|error| format!("v5 loaded N10 no-op: {error}"))?;
    let halt = load_execution_geometry_native_executable(
        &mut adapter,
        n11.halt().load_image(),
    )
    .map_err(|error| format!("v5 loaded N11 halt: {error}"))?;
    let rejected = matches!(
        n10.bind_executables(&no_operation, &halt),
        Err(ExecutionGeometryNativeNoopHaltExecutableBindingError::Halt)
    );
    release_execution_geometry_native_executable(&mut adapter, no_operation)
        .map_err(|error| format!("v5 loaded N10 no-op release: {error}"))?;
    release_execution_geometry_native_executable(&mut adapter, halt)
        .map_err(|error| format!("v5 loaded N11 halt release: {error}"))?;
    if rejected {
        Ok(())
    } else {
        Err(String::from("v5 mixed ready pair was prebound"))
    }
}

#[test]
fn geometry_native_rotate_halt_cache_replace_blocks_live_lease()
-> Result<(), String> {
    let n10_fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_rotate_halt_sequence_fixture(11)?;
    let n10 = geometry_native_rotate_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_rotate_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(128)?,
        native_executable_address(0x2_e000)?,
    );
    let mut cache = GeometryNativeRotateHaltPairLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &n10)
        .map_err(|error| format!("v5 replace N10 acquire: {error}"))?
        .into_lease();
    let Err(failure) = cache.replace_if_unleased(&mut adapter, &n11) else {
        return Err(String::from("v5 replacement ignored live lease"));
    };
    if !matches!(
        *failure,
        GeometryNativeRotateHaltPairCacheAcquireFailure::Leased { leases: 1 }
    ) || adapter.operations.len() != 8
        || lease.sequence() != &n10
    {
        return Err(String::from("v5 live-lease replacement drifted"));
    }
    drop(lease);
    cache
        .release_if_unleased(&mut adapter)
        .map(|_release| ())
        .map_err(|error| format!("v5 replace blocked cleanup: {error}"))
}

#[test]
fn geometry_native_rotate_halt_cache_replace_publishes_identity()
-> Result<(), String> {
    let n10_fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_rotate_halt_sequence_fixture(11)?;
    let n10 = geometry_native_rotate_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_rotate_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(129)?,
        native_executable_address(0x2_f000)?,
    );
    let mut cache = GeometryNativeRotateHaltPairLeaseCache::new();
    let first = cache
        .ensure(&mut adapter, &n10)
        .map_err(|error| format!("v5 replace first acquire: {error}"))?
        .into_lease();
    drop(first);
    let replacement = cache
        .replace_if_unleased(&mut adapter, &n11)
        .map_err(|error| format!("v5 replace N11: {error}"))?;
    if replacement.disposition()
        != GeometryNativeRotateHaltPairCacheDisposition::Replaced
        || replacement.lease().sequence() != &n11
        || adapter.operations.len() != 18
    {
        return Err(String::from("v5 replacement publication drifted"));
    }
    drop(replacement);
    let released = cache
        .release_if_unleased(&mut adapter)
        .map_err(|error| format!("v5 replacement final cleanup: {error}"))?;
    if released == GeometryNativeRotateHaltPairCacheRelease::Released
        && adapter.operations.len() == 20
    {
        Ok(())
    } else {
        Err(String::from("v5 replacement final release drifted"))
    }
}

#[test]
fn geometry_native_rotate_halt_cache_replace_release_failure_empties()
-> Result<(), String> {
    let n10_fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_rotate_halt_sequence_fixture(11)?;
    let n10 = geometry_native_rotate_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_rotate_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(130)?,
        native_executable_address(0x3_0000)?,
    )
    .with_release_failures(2);
    let mut cache = GeometryNativeRotateHaltPairLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &n10)
        .map_err(|error| format!("v5 replace release acquire: {error}"))?
        .into_lease();
    drop(lease);
    let Err(failure) = cache.replace_if_unleased(&mut adapter, &n11) else {
        return Err(String::from("v5 replacement release failure ignored"));
    };
    let GeometryNativeRotateHaltPairCacheAcquireFailure::Release(cleanup) =
        *failure
    else {
        return Err(String::from("v5 replacement release cause drifted"));
    };
    if cache.has_resident()
        || cleanup.halt_failure().is_none()
        || cleanup.rotate_failure().is_none()
        || adapter.operations.len() != 10
    {
        return Err(String::from("v5 replacement release ownership drifted"));
    }
    cleanup
        .retry(&mut adapter)
        .map_err(|error| format!("v5 replacement release retry: {error}"))
}

#[test]
fn geometry_native_rotate_halt_cache_replace_load_failure_empties()
-> Result<(), String> {
    let n10_fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_rotate_halt_sequence_fixture(11)?;
    let n10 = geometry_native_rotate_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_rotate_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(131)?,
        native_executable_address(0x3_1000)?,
    )
    .with_failure_at(FakeNativeAdapterOperation::Allocate, 3);
    let mut cache = GeometryNativeRotateHaltPairLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &n10)
        .map_err(|error| format!("v5 replace load acquire: {error}"))?
        .into_lease();
    drop(lease);
    let Err(failure) = cache.replace_if_unleased(&mut adapter, &n11) else {
        return Err(String::from("v5 replacement load failure ignored"));
    };
    let load_failed = matches!(
        *failure,
        GeometryNativeRotateHaltPairCacheAcquireFailure::Load(error)
            if matches!(
                *error,
                ExecutionGeometryNativeRotateHaltPairLoadFailure::Rotate(_)
            )
    );
    if load_failed && !cache.has_resident() && adapter.operations.len() == 11 {
        Ok(())
    } else {
        Err(String::from(
            "v5 replacement load failure publication drifted",
        ))
    }
}

#[test]
fn geometry_native_rotate_halt_cache_insert_hit_reuses_resident()
-> Result<(), String> {
    let fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_rotate_halt_sequence(&fixture)?;
    let [initial, _prefix, final_state] = fixture.states.as_slice() else {
        return Err(String::from("v5 cache state sequence incomplete"));
    };
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(123)?,
        native_executable_address(0x2_9000)?,
    );
    let mut cache = GeometryNativeRotateHaltPairLeaseCache::new();
    let first = cache
        .ensure(&mut adapter, &sequence)
        .map_err(|error| format!("v5 cache insert: {error}"))?;
    let first_disposition = first.disposition();
    let first_lease = first.into_lease();
    let second = cache
        .ensure(&mut adapter, &sequence)
        .map_err(|error| format!("v5 cache hit: {error}"))?;
    let second_disposition = second.disposition();
    let second_lease = second.into_lease();
    if first_disposition
        != GeometryNativeRotateHaltPairCacheDisposition::Inserted
        || second_disposition
            != GeometryNativeRotateHaltPairCacheDisposition::Hit
        || !first_lease.shares_resident_with(&second_lease)
        || cache.resident_lease_count() != 2
        || adapter.operations.len() != 8
    {
        return Err(String::from("v5 cache resident reuse drifted"));
    }
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = first_lease
        .execute(
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| format!("v5 cache lease execute: {error}"))?;
    if outcome.state() != final_state || adapter.operations.len() != 8 {
        return Err(String::from("v5 cache lease execution remapped"));
    }
    drop((first_lease, second_lease));
    let released = cache
        .release_if_unleased(&mut adapter)
        .map_err(|error| format!("v5 cache final release: {error}"))?;
    if released != GeometryNativeRotateHaltPairCacheRelease::Released
        || cache.has_resident()
        || adapter.operations.len() != 10
    {
        return Err(String::from("v5 cache final release drifted"));
    }
    Ok(())
}

#[test]
fn geometry_native_rotate_halt_cache_live_lease_blocks_release()
-> Result<(), String> {
    let fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_rotate_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(124)?,
        native_executable_address(0x2_a000)?,
    );
    let mut cache = GeometryNativeRotateHaltPairLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &sequence)
        .map_err(|error| format!("v5 cache lease acquire: {error}"))?
        .into_lease();
    let blocked = cache
        .release_if_unleased(&mut adapter)
        .map_err(|error| format!("v5 cache blocked release: {error}"))?;
    if blocked
        != (GeometryNativeRotateHaltPairCacheRelease::Leased { leases: 1 })
        || adapter.operations.len() != 8
        || cache.resident_lease_count() != 1
    {
        return Err(String::from("v5 cache live lease did not block release"));
    }
    drop(lease);
    let released = cache
        .release_if_unleased(&mut adapter)
        .map_err(|error| format!("v5 cache unblocked release: {error}"))?;
    if released == GeometryNativeRotateHaltPairCacheRelease::Released
        && adapter.operations.len() == 10
    {
        Ok(())
    } else {
        Err(String::from("v5 cache unblocked release drifted"))
    }
}

#[test]
fn geometry_native_rotate_halt_cache_rejects_different_identity()
-> Result<(), String> {
    let n10_fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_rotate_halt_sequence_fixture(11)?;
    let n10 = geometry_native_rotate_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_rotate_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(125)?,
        native_executable_address(0x2_b000)?,
    );
    let mut cache = GeometryNativeRotateHaltPairLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &n10)
        .map_err(|error| format!("v5 cache N10 acquire: {error}"))?
        .into_lease();
    let Err(failure) = cache.ensure(&mut adapter, &n11) else {
        return Err(String::from("v5 cache mixed identity was admitted"));
    };
    if !matches!(
        *failure,
        GeometryNativeRotateHaltPairCacheAcquireFailure::IdentityOccupied
    ) || adapter.operations.len() != 8
        || lease.sequence() != &n10
    {
        return Err(String::from("v5 cache mixed identity handling drifted"));
    }
    drop(lease);
    cache
        .release_if_unleased(&mut adapter)
        .map(|_release| ())
        .map_err(|error| format!("v5 cache N10 cleanup: {error}"))
}

#[test]
fn geometry_native_rotate_halt_cache_load_failure_publishes_nothing()
-> Result<(), String> {
    let fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_rotate_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(126)?,
        native_executable_address(0x2_c000)?,
    )
    .with_failure_at(FakeNativeAdapterOperation::Allocate, 2);
    let mut cache = GeometryNativeRotateHaltPairLeaseCache::new();
    let Err(failure) = cache.ensure(&mut adapter, &sequence) else {
        return Err(String::from("v5 cache load failure was published"));
    };
    let load_failed = matches!(
        *failure,
        GeometryNativeRotateHaltPairCacheAcquireFailure::Load(error)
            if matches!(
                *error,
                ExecutionGeometryNativeRotateHaltPairLoadFailure::Halt { .. }
            )
    );
    let release = cache
        .release_if_unleased(&mut adapter)
        .map_err(|error| format!("v5 empty cache release: {error}"))?;
    if load_failed
        && !cache.has_resident()
        && release == GeometryNativeRotateHaltPairCacheRelease::Missing
    {
        Ok(())
    } else {
        Err(String::from("v5 cache failed load left resident authority"))
    }
}

#[test]
fn geometry_native_rotate_halt_cache_release_transfers_ownership()
-> Result<(), String> {
    let fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_rotate_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(127)?,
        native_executable_address(0x2_d000)?,
    )
    .with_release_failures(2);
    let mut cache = GeometryNativeRotateHaltPairLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &sequence)
        .map_err(|error| format!("v5 cache release acquire: {error}"))?
        .into_lease();
    drop(lease);
    let Err(failure) = cache.release_if_unleased(&mut adapter) else {
        return Err(String::from("v5 cache release failure was ignored"));
    };
    if cache.has_resident()
        || failure.halt_failure().is_none()
        || failure.rotate_failure().is_none()
    {
        return Err(String::from(
            "v5 cache cleanup ownership did not transfer",
        ));
    }
    failure
        .retry(&mut adapter)
        .map_err(|error| format!("v5 cache cleanup retry: {error}"))
}

#[test]
fn geometry_native_noop_halt_pair_cache_replace_blocks_live_lease()
-> Result<(), String> {
    let n10_fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_noop_halt_sequence_fixture(11)?;
    let n10 = geometry_native_noop_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_noop_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(128)?,
        native_executable_address(0x2_e000)?,
    );
    let mut cache = GeometryNativeNoopHaltPairLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &n10)
        .map_err(|error| format!("v5 replace N10 acquire: {error}"))?
        .into_lease();
    let Err(failure) = cache.replace_if_unleased(&mut adapter, &n11) else {
        return Err(String::from("v5 replacement ignored live lease"));
    };
    if !matches!(
        *failure,
        GeometryNativeNoopHaltPairCacheAcquireFailure::Leased { leases: 1 }
    ) || adapter.operations.len() != 8
        || lease.sequence() != &n10
    {
        return Err(String::from("v5 live-lease replacement drifted"));
    }
    drop(lease);
    cache
        .release_if_unleased(&mut adapter)
        .map(|_release| ())
        .map_err(|error| format!("v5 replace blocked cleanup: {error}"))
}

#[test]
fn geometry_native_noop_halt_pair_cache_replace_publishes_new_identity()
-> Result<(), String> {
    let n10_fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_noop_halt_sequence_fixture(11)?;
    let n10 = geometry_native_noop_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_noop_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(129)?,
        native_executable_address(0x2_f000)?,
    );
    let mut cache = GeometryNativeNoopHaltPairLeaseCache::new();
    let first = cache
        .ensure(&mut adapter, &n10)
        .map_err(|error| format!("v5 replace first acquire: {error}"))?
        .into_lease();
    drop(first);
    let replacement = cache
        .replace_if_unleased(&mut adapter, &n11)
        .map_err(|error| format!("v5 replace N11: {error}"))?;
    if replacement.disposition()
        != GeometryNativeNoopHaltPairCacheDisposition::Replaced
        || replacement.lease().sequence() != &n11
        || adapter.operations.len() != 18
    {
        return Err(String::from("v5 replacement publication drifted"));
    }
    drop(replacement);
    let released = cache
        .release_if_unleased(&mut adapter)
        .map_err(|error| format!("v5 replacement final cleanup: {error}"))?;
    if released == GeometryNativeNoopHaltPairCacheRelease::Released
        && adapter.operations.len() == 20
    {
        Ok(())
    } else {
        Err(String::from("v5 replacement final release drifted"))
    }
}

#[test]
fn geometry_native_noop_halt_pair_cache_replace_release_failure_empties_cache()
-> Result<(), String> {
    let n10_fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_noop_halt_sequence_fixture(11)?;
    let n10 = geometry_native_noop_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_noop_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(130)?,
        native_executable_address(0x3_0000)?,
    )
    .with_release_failures(2);
    let mut cache = GeometryNativeNoopHaltPairLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &n10)
        .map_err(|error| format!("v5 replace release acquire: {error}"))?
        .into_lease();
    drop(lease);
    let Err(failure) = cache.replace_if_unleased(&mut adapter, &n11) else {
        return Err(String::from("v5 replacement release failure ignored"));
    };
    let GeometryNativeNoopHaltPairCacheAcquireFailure::Release(cleanup) =
        *failure
    else {
        return Err(String::from("v5 replacement release cause drifted"));
    };
    if cache.has_resident()
        || cleanup.halt_failure().is_none()
        || cleanup.no_operation_failure().is_none()
        || adapter.operations.len() != 10
    {
        return Err(String::from("v5 replacement release ownership drifted"));
    }
    cleanup
        .retry(&mut adapter)
        .map_err(|error| format!("v5 replacement release retry: {error}"))
}

#[test]
fn geometry_native_noop_halt_pair_cache_replace_load_failure_leaves_empty()
-> Result<(), String> {
    let n10_fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_noop_halt_sequence_fixture(11)?;
    let n10 = geometry_native_noop_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_noop_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(131)?,
        native_executable_address(0x3_1000)?,
    )
    .with_failure_at(FakeNativeAdapterOperation::Allocate, 3);
    let mut cache = GeometryNativeNoopHaltPairLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &n10)
        .map_err(|error| format!("v5 replace load acquire: {error}"))?
        .into_lease();
    drop(lease);
    let Err(failure) = cache.replace_if_unleased(&mut adapter, &n11) else {
        return Err(String::from("v5 replacement load failure ignored"));
    };
    let load_failed = matches!(
        *failure,
        GeometryNativeNoopHaltPairCacheAcquireFailure::Load(error)
            if matches!(
                *error,
                ExecutionGeometryNativeNoopHaltPairLoadFailure::NoOperation(_)
            )
    );
    if load_failed && !cache.has_resident() && adapter.operations.len() == 11 {
        Ok(())
    } else {
        Err(String::from(
            "v5 replacement load failure publication drifted",
        ))
    }
}

#[test]
fn geometry_native_noop_halt_pair_cache_insert_hit_reuses_resident()
-> Result<(), String> {
    let fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let sequence = geometry_native_noop_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 cache initial state missing"))?;
    let final_state = fixture
        .states
        .get(2)
        .ok_or_else(|| String::from("v5 cache final state missing"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(123)?,
        native_executable_address(0x2_9000)?,
    );
    let mut cache = GeometryNativeNoopHaltPairLeaseCache::new();
    let first = cache
        .ensure(&mut adapter, &sequence)
        .map_err(|error| format!("v5 cache insert: {error}"))?;
    let first_disposition = first.disposition();
    let first_lease = first.into_lease();
    let second = cache
        .ensure(&mut adapter, &sequence)
        .map_err(|error| format!("v5 cache hit: {error}"))?;
    let second_disposition = second.disposition();
    let second_lease = second.into_lease();
    if first_disposition != GeometryNativeNoopHaltPairCacheDisposition::Inserted
        || second_disposition != GeometryNativeNoopHaltPairCacheDisposition::Hit
        || !first_lease.shares_resident_with(&second_lease)
        || cache.resident_lease_count() != 2
        || adapter.operations.len() != 8
    {
        return Err(String::from("v5 cache resident reuse drifted"));
    }
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = first_lease
        .execute(
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| format!("v5 cache lease execute: {error}"))?;
    if outcome.state() != final_state || adapter.operations.len() != 8 {
        return Err(String::from("v5 cache lease execution remapped"));
    }
    drop((first_lease, second_lease));
    let released = cache
        .release_if_unleased(&mut adapter)
        .map_err(|error| format!("v5 cache final release: {error}"))?;
    if released != GeometryNativeNoopHaltPairCacheRelease::Released
        || cache.has_resident()
        || adapter.operations.len() != 10
    {
        return Err(String::from("v5 cache final release drifted"));
    }
    Ok(())
}

#[test]
fn geometry_native_noop_halt_pair_cache_live_lease_blocks_release()
-> Result<(), String> {
    let fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let sequence = geometry_native_noop_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(124)?,
        native_executable_address(0x2_a000)?,
    );
    let mut cache = GeometryNativeNoopHaltPairLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &sequence)
        .map_err(|error| format!("v5 cache lease acquire: {error}"))?
        .into_lease();
    let blocked = cache
        .release_if_unleased(&mut adapter)
        .map_err(|error| format!("v5 cache blocked release: {error}"))?;
    if blocked != (GeometryNativeNoopHaltPairCacheRelease::Leased { leases: 1 })
        || adapter.operations.len() != 8
        || cache.resident_lease_count() != 1
    {
        return Err(String::from("v5 cache live lease did not block release"));
    }
    drop(lease);
    let released = cache
        .release_if_unleased(&mut adapter)
        .map_err(|error| format!("v5 cache unblocked release: {error}"))?;
    if released == GeometryNativeNoopHaltPairCacheRelease::Released
        && adapter.operations.len() == 10
    {
        Ok(())
    } else {
        Err(String::from("v5 cache unblocked release drifted"))
    }
}

#[test]
fn geometry_native_noop_halt_pair_cache_rejects_different_identity()
-> Result<(), String> {
    let n10_fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_noop_halt_sequence_fixture(11)?;
    let n10 = geometry_native_noop_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_noop_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(125)?,
        native_executable_address(0x2_b000)?,
    );
    let mut cache = GeometryNativeNoopHaltPairLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &n10)
        .map_err(|error| format!("v5 cache N10 acquire: {error}"))?
        .into_lease();
    let Err(failure) = cache.ensure(&mut adapter, &n11) else {
        return Err(String::from("v5 cache mixed identity was admitted"));
    };
    if !matches!(
        *failure,
        GeometryNativeNoopHaltPairCacheAcquireFailure::IdentityOccupied
    ) || adapter.operations.len() != 8
        || lease.sequence() != &n10
    {
        return Err(String::from("v5 cache mixed identity handling drifted"));
    }
    drop(lease);
    cache
        .release_if_unleased(&mut adapter)
        .map(|_release| ())
        .map_err(|error| format!("v5 cache N10 cleanup: {error}"))
}

#[test]
fn geometry_native_noop_halt_pair_cache_load_failure_publishes_nothing()
-> Result<(), String> {
    let fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let sequence = geometry_native_noop_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(126)?,
        native_executable_address(0x2_c000)?,
    )
    .with_failure_at(FakeNativeAdapterOperation::Allocate, 2);
    let mut cache = GeometryNativeNoopHaltPairLeaseCache::new();
    let Err(failure) = cache.ensure(&mut adapter, &sequence) else {
        return Err(String::from("v5 cache load failure was published"));
    };
    let load_failed = matches!(
        *failure,
        GeometryNativeNoopHaltPairCacheAcquireFailure::Load(error)
            if matches!(
                *error,
                ExecutionGeometryNativeNoopHaltPairLoadFailure::Halt { .. }
            )
    );
    let release = cache
        .release_if_unleased(&mut adapter)
        .map_err(|error| format!("v5 empty cache release: {error}"))?;
    if load_failed
        && !cache.has_resident()
        && release == GeometryNativeNoopHaltPairCacheRelease::Missing
    {
        Ok(())
    } else {
        Err(String::from("v5 cache failed load left resident authority"))
    }
}

#[test]
fn geometry_native_noop_halt_pair_cache_release_failure_transfers_ownership()
-> Result<(), String> {
    let fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let sequence = geometry_native_noop_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(127)?,
        native_executable_address(0x2_d000)?,
    )
    .with_release_failures(2);
    let mut cache = GeometryNativeNoopHaltPairLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &sequence)
        .map_err(|error| format!("v5 cache release acquire: {error}"))?
        .into_lease();
    drop(lease);
    let Err(failure) = cache.release_if_unleased(&mut adapter) else {
        return Err(String::from("v5 cache release failure was ignored"));
    };
    if cache.has_resident()
        || failure.halt_failure().is_none()
        || failure.no_operation_failure().is_none()
    {
        return Err(String::from(
            "v5 cache cleanup ownership did not transfer",
        ));
    }
    failure
        .retry(&mut adapter)
        .map_err(|error| format!("v5 cache cleanup retry: {error}"))
}

#[test]
fn geometry_native_noop_halt_pair_load_failure_releases_prefix()
-> Result<(), String> {
    let fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let sequence = geometry_native_noop_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(120)?,
        native_executable_address(0x2_6000)?,
    )
    .with_failure_at(FakeNativeAdapterOperation::Allocate, 2);
    let Err(failure) = sequence.load_pair(&mut adapter) else {
        return Err(String::from("v5 pair halt load failure was ignored"));
    };
    let ExecutionGeometryNativeNoopHaltPairLoadFailure::Halt {
        error,
        no_operation_release_failure,
    } = *failure
    else {
        return Err(String::from("v5 pair load failure phase drifted"));
    };
    if error.phase() == NativeExecutableLoadPhase::Allocate
        && no_operation_release_failure.is_none()
        && adapter.release_requests.len() == 1
        && adapter.operations.last()
            == Some(&FakeNativeAdapterOperation::Release)
    {
        Ok(())
    } else {
        Err(String::from("v5 pair partial load rollback drifted"))
    }
}

#[test]
fn geometry_native_rotate_halt_pair_load_failure_retains_cleanup_retry()
-> Result<(), String> {
    let fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_rotate_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(121)?,
        native_executable_address(0x2_7000)?,
    )
    .with_failure_at(FakeNativeAdapterOperation::Allocate, 2)
    .with_release_failures(1);
    let Err(failure) = sequence.load_pair(&mut adapter) else {
        return Err(String::from("v5 pair cleanup failure was ignored"));
    };
    let ExecutionGeometryNativeRotateHaltPairLoadFailure::Halt {
        error,
        rotate_release_failure: Some(cleanup),
    } = *failure
    else {
        return Err(String::from("v5 pair cleanup ownership was lost"));
    };
    if error.phase() != NativeExecutableLoadPhase::Allocate
        || cleanup.executable().key() != sequence.rotate().artifact().key()
    {
        return Err(String::from("v5 pair cleanup retry identity drifted"));
    }
    cleanup
        .retry(&mut adapter)
        .map_err(|retry_error| format!("v5 pair cleanup retry: {retry_error}"))
}

#[test]
fn geometry_native_rotate_halt_pair_release_retries_both_mappings()
-> Result<(), String> {
    let fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_rotate_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(122)?,
        native_executable_address(0x2_8000)?,
    )
    .with_release_failures(2);
    let loaded = sequence
        .load_pair(&mut adapter)
        .map_err(|error| format!("v5 pair owned load: {error}"))?;
    let Err(failure) = loaded.release(&mut adapter) else {
        return Err(String::from("v5 pair release failures were ignored"));
    };
    let halt_key_matches = failure.halt_failure().is_some_and(|error| {
        error.executable().key() == sequence.halt().artifact().key()
    });
    let rotate_key_matches = failure.rotate_failure().is_some_and(|error| {
        error.executable().key() == sequence.rotate().artifact().key()
    });
    if !halt_key_matches || !rotate_key_matches {
        return Err(String::from("v5 pair release retry ownership drifted"));
    }
    failure
        .retry(&mut adapter)
        .map_err(|error| format!("v5 pair release retry: {error}"))?;
    if adapter.release_requests.len() == 4 {
        Ok(())
    } else {
        Err(String::from("v5 pair release retry attempts drifted"))
    }
}

#[test]
fn geometry_native_noop_halt_pair_load_failure_retains_cleanup_retry()
-> Result<(), String> {
    let fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let sequence = geometry_native_noop_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(121)?,
        native_executable_address(0x2_7000)?,
    )
    .with_failure_at(FakeNativeAdapterOperation::Allocate, 2)
    .with_release_failures(1);
    let Err(failure) = sequence.load_pair(&mut adapter) else {
        return Err(String::from("v5 pair cleanup failure was ignored"));
    };
    let ExecutionGeometryNativeNoopHaltPairLoadFailure::Halt {
        error,
        no_operation_release_failure: Some(cleanup),
    } = *failure
    else {
        return Err(String::from("v5 pair cleanup ownership was lost"));
    };
    if error.phase() != NativeExecutableLoadPhase::Allocate
        || cleanup.executable().key()
            != sequence.no_operation().artifact().key()
    {
        return Err(String::from("v5 pair cleanup retry identity drifted"));
    }
    cleanup
        .retry(&mut adapter)
        .map_err(|retry_error| format!("v5 pair cleanup retry: {retry_error}"))
}

#[test]
fn geometry_native_noop_halt_pair_release_retries_both_mappings()
-> Result<(), String> {
    let fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let sequence = geometry_native_noop_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(122)?,
        native_executable_address(0x2_8000)?,
    )
    .with_release_failures(2);
    let loaded = sequence
        .load_pair(&mut adapter)
        .map_err(|error| format!("v5 pair owned load: {error}"))?;
    let Err(failure) = loaded.release(&mut adapter) else {
        return Err(String::from("v5 pair release failures were ignored"));
    };
    let halt_key_matches = failure.halt_failure().is_some_and(|error| {
        error.executable().key() == sequence.halt().artifact().key()
    });
    let no_operation_key_matches =
        failure.no_operation_failure().is_some_and(|error| {
            error.executable().key() == sequence.no_operation().artifact().key()
        });
    if !halt_key_matches || !no_operation_key_matches {
        return Err(String::from("v5 pair release retry ownership drifted"));
    }
    failure
        .retry(&mut adapter)
        .map_err(|error| format!("v5 pair release retry: {error}"))?;
    if adapter.release_requests.len() == 4 {
        Ok(())
    } else {
        Err(String::from("v5 pair release retry attempts drifted"))
    }
}

#[test]
fn geometry_native_noop_halt_pair_reuses_owned_executables()
-> Result<(), String> {
    let fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let sequence = geometry_native_noop_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 owned pair initial state missing"))?;
    let final_state = fixture
        .states
        .get(2)
        .ok_or_else(|| String::from("v5 owned pair final state missing"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(119)?,
        native_executable_address(0x2_5000)?,
    );
    let loaded = sequence
        .load_pair(&mut adapter)
        .map_err(|error| format!("v5 owned pair load: {error}"))?;
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    for _iteration in 0usize..2usize {
        let mut memory = initial.memory().to_vec();
        let input = initial.io().input().to_vec();
        let mut output = initial.io().output().to_vec();
        let outcome = loaded
            .execute(
                &mut runner,
                NativeRegionBuffers::new(&mut memory, &input, &mut output),
            )
            .map_err(|error| format!("v5 owned pair execute: {error}"))?;
        if outcome.state() != final_state || memory != final_state.memory() {
            return Err(String::from("v5 owned pair execution drifted"));
        }
    }
    if runner.calls != 4 || adapter.operations.len() != 8 {
        return Err(String::from("v5 owned pair remapped during reuse"));
    }
    loaded
        .release(&mut adapter)
        .map_err(|error| format!("v5 owned pair release: {error}"))?;
    if adapter.operations.len() == 10 {
        Ok(())
    } else {
        Err(String::from("v5 owned pair release count drifted"))
    }
}

#[test]
fn geometry_native_noop_halt_loaded_reuses_two_ready_executables()
-> Result<(), String> {
    let fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let sequence = geometry_native_noop_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 loaded initial state missing"))?;
    let final_state = fixture
        .states
        .get(2)
        .ok_or_else(|| String::from("v5 loaded final state missing"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(118)?,
        native_executable_address(0x2_4000)?,
    );
    let (no_operation, halt) =
        load_geometry_native_noop_halt_pair(&mut adapter, &sequence)?;
    {
        let bound = sequence
            .bind_executables(&no_operation, &halt)
            .map_err(|error| format!("v5 reusable bind: {error}"))?;
        let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::Applied,
        ]);
        for _iteration in 0usize..2usize {
            let mut memory = initial.memory().to_vec();
            let input = initial.io().input().to_vec();
            let mut output = initial.io().output().to_vec();
            let outcome = bound
                .execute(
                    &mut runner,
                    NativeRegionBuffers::new(&mut memory, &input, &mut output),
                )
                .map_err(|error| format!("v5 reusable execute: {error}"))?;
            if outcome.state() != final_state || memory != final_state.memory()
            {
                return Err(String::from("v5 loaded reuse result drifted"));
            }
        }
        if runner.calls != 4 || adapter.operations.len() != 8 {
            return Err(String::from("v5 loaded reuse remapped executables"));
        }
    }
    release_execution_geometry_native_executable(&mut adapter, no_operation)
        .map_err(|error| format!("v5 reusable no-op release: {error}"))?;
    release_execution_geometry_native_executable(&mut adapter, halt)
        .map_err(|error| format!("v5 reusable halt release: {error}"))?;
    if adapter.operations.len() == 10 {
        Ok(())
    } else {
        Err(String::from("v5 reusable releases drifted"))
    }
}

#[test]
fn geometry_native_noop_halt_loaded_late_failure_retains_prefix()
-> Result<(), String> {
    let fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let sequence = geometry_native_noop_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 loaded initial state missing"))?;
    let prefix = fixture
        .states
        .get(1)
        .ok_or_else(|| String::from("v5 loaded prefix state missing"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(117)?,
        native_executable_address(0x2_3000)?,
    );
    let no_operation = load_execution_geometry_native_executable(
        &mut adapter,
        sequence.no_operation().load_image(),
    )
    .map_err(|error| format!("v5 loaded late no-op: {error}"))?;
    let halt = load_execution_geometry_native_executable(
        &mut adapter,
        sequence.halt().load_image(),
    )
    .map_err(|error| format!("v5 loaded late halt: {error}"))?;
    {
        let bound = sequence
            .bind_executables(&no_operation, &halt)
            .map_err(|error| format!("v5 loaded late bind: {error}"))?;
        let mut memory = initial.memory().to_vec();
        let input = initial.io().input().to_vec();
        let mut output = initial.io().output().to_vec();
        let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::FailureAfterMutation,
        ]);
        let Err(failure) = bound.execute(
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        ) else {
            return Err(String::from("v5 loaded late failure was ignored"));
        };
        if failure.index() != 1
            || failure.state() != prefix
            || memory != prefix.memory()
            || !matches!(
                failure.cause(),
                LoadedNoopHaltCause::HaltExecution(_error,)
            )
            || adapter.operations.len() != 8
        {
            return Err(String::from("v5 loaded late failure lost prefix"));
        }
    }
    release_execution_geometry_native_executable(&mut adapter, no_operation)
        .map_err(|error| format!("v5 loaded late no-op release: {error}"))?;
    release_execution_geometry_native_executable(&mut adapter, halt)
        .map_err(|error| format!("v5 loaded late halt release: {error}"))
}

#[test]
fn geometry_native_jump_rotate_halt_owned_reuses_three_executables()
-> Result<(), String> {
    let fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_jump_rotate_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 owned triple initial state missing"))?;
    let final_state = fixture
        .states
        .get(3)
        .ok_or_else(|| String::from("v5 owned triple final state missing"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(139)?,
        native_executable_address(0x3_9000)?,
    );
    let loaded = sequence
        .load_triple(&mut adapter)
        .map_err(|error| format!("v5 owned triple load: {error}"))?;
    if adapter.operations.len() != 12 || loaded.sequence() != &sequence {
        return Err(String::from("v5 owned triple load identity drifted"));
    }
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    for _iteration in 0usize..2usize {
        let mut memory = initial.memory().to_vec();
        let input = initial.io().input().to_vec();
        let mut output = initial.io().output().to_vec();
        let outcome = loaded
            .execute(
                &mut runner,
                NativeRegionBuffers::new(&mut memory, &input, &mut output),
            )
            .map_err(|error| format!("v5 owned triple execute: {error}"))?;
        if outcome != FullGeometryOutcome::Completed(final_state.clone())
            || memory != final_state.memory()
            || output != final_state.io().output()
            || adapter.operations.len() != 12
        {
            return Err(String::from("v5 owned triple execution remapped"));
        }
    }
    if runner.calls != 6 {
        return Err(String::from("v5 owned triple runner count drifted"));
    }
    loaded
        .release(&mut adapter)
        .map_err(|error| format!("v5 owned triple release: {error}"))?;
    if adapter.operations.len() == 15 {
        Ok(())
    } else {
        Err(String::from("v5 owned triple release count drifted"))
    }
}

#[test]
fn geometry_native_jump_rotate_halt_jump_load_failure_releases_suffix()
-> Result<(), String> {
    let fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_jump_rotate_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(140)?,
        native_executable_address(0x3_a000)?,
    )
    .with_failure_at(FakeNativeAdapterOperation::Allocate, 3);
    let Err(failure) = sequence.load_triple(&mut adapter) else {
        return Err(String::from("v5 owned jump load failure was ignored"));
    };
    let FullGeometryTripleLoadFailure::InitialJump {
        error,
        suffix_release_failure,
    } = *failure
    else {
        return Err(String::from("v5 owned jump load failure phase drifted"));
    };
    if error.phase() == NativeExecutableLoadPhase::Allocate
        && suffix_release_failure.is_none()
        && adapter.release_requests.len() == 2
        && adapter.operations.len() == 11
    {
        Ok(())
    } else {
        Err(String::from("v5 owned jump load rollback drifted"))
    }
}

#[test]
fn geometry_native_jump_rotate_halt_jump_load_retains_suffix_cleanup()
-> Result<(), String> {
    let fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_jump_rotate_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(141)?,
        native_executable_address(0x3_b000)?,
    )
    .with_failure_at(FakeNativeAdapterOperation::Allocate, 3)
    .with_release_failures(2);
    let Err(failure) = sequence.load_triple(&mut adapter) else {
        return Err(String::from("v5 owned cleanup failure was ignored"));
    };
    let FullGeometryTripleLoadFailure::InitialJump {
        error,
        suffix_release_failure: Some(cleanup),
    } = *failure
    else {
        return Err(String::from("v5 owned cleanup ownership was lost"));
    };
    if error.phase() != NativeExecutableLoadPhase::Allocate
        || cleanup.halt_failure().is_none()
        || cleanup.rotate_failure().is_none()
        || adapter.operations.len() != 11
    {
        return Err(String::from("v5 owned suffix cleanup evidence drifted"));
    }
    cleanup.retry(&mut adapter).map_err(|retry_error| {
        format!("v5 owned suffix cleanup retry: {retry_error}")
    })?;
    if adapter.operations.len() == 13 {
        Ok(())
    } else {
        Err(String::from("v5 owned suffix cleanup retry drifted"))
    }
}

#[test]
fn geometry_native_jump_rotate_halt_release_retries_all_three()
-> Result<(), String> {
    let fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_jump_rotate_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(142)?,
        native_executable_address(0x3_c000)?,
    )
    .with_release_failures(3);
    let loaded = sequence
        .load_triple(&mut adapter)
        .map_err(|error| format!("v5 owned release load: {error}"))?;
    let Err(failure) = loaded.release(&mut adapter) else {
        return Err(String::from("v5 owned triple release failure ignored"));
    };
    let suffix_failure = failure.suffix_failure().ok_or_else(|| {
        String::from("v5 owned suffix release failure missing")
    })?;
    if failure.initial_jump_failure().is_none()
        || suffix_failure.halt_failure().is_none()
        || suffix_failure.rotate_failure().is_none()
        || adapter.release_requests.len() != 3
        || adapter.operations.len() != 15
    {
        return Err(String::from("v5 owned triple release ownership drifted"));
    }
    (*failure)
        .retry(&mut adapter)
        .map_err(|error| format!("v5 owned triple release retry: {error}"))?;
    if adapter.operations.len() == 18 {
        Ok(())
    } else {
        Err(String::from("v5 owned triple release retry drifted"))
    }
}

#[test]
fn geometry_native_jump_rotate_halt_lru_hit_executes_without_remap()
-> Result<(), String> {
    let fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_jump_rotate_halt_sequence(&fixture)?;
    let [initial, _jump, _rotate, final_state] = fixture.states.as_slice()
    else {
        return Err(String::from("v5 LRU state sequence incomplete"));
    };
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(152)?,
        native_executable_address(0x4_6000)?,
    );
    let mut cache = full_lru_cache(2)?;
    let inserted = cache
        .ensure(&mut adapter, &sequence)
        .map_err(|error| format!("v5 LRU insert: {error}"))?;
    drop(inserted);
    let hit = cache
        .ensure(&mut adapter, &sequence)
        .map_err(|error| format!("v5 LRU hit: {error}"))?;
    if hit.disposition() != FullLruDisposition::Hit
        || adapter.operations.len() != 12
    {
        return Err(String::from("v5 LRU hit remapped resident"));
    }
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = hit
        .lease()
        .execute(
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| format!("v5 LRU hit execute: {error}"))?;
    if outcome.state() != final_state
        || memory != final_state.memory()
        || adapter.operations.len() != 12
    {
        return Err(String::from("v5 LRU hit execution drifted"));
    }
    drop(hit);
    cache
        .release_if_unleased(&mut adapter, &sequence)
        .map(|_release| ())
        .map_err(|error| format!("v5 LRU hit cleanup: {error}"))
}

#[test]
fn geometry_native_jump_rotate_halt_lru_hit_refreshes_eviction()
-> Result<(), String> {
    let (s10, s11, s12) = full_lru_sequences()?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(153)?,
        native_executable_address(0x4_7000)?,
    );
    let mut cache = full_lru_cache(2)?;
    drop(
        cache
            .ensure(&mut adapter, &s10)
            .map_err(|error| error.to_string())?,
    );
    drop(
        cache
            .ensure(&mut adapter, &s11)
            .map_err(|error| error.to_string())?,
    );
    let hit = cache
        .ensure(&mut adapter, &s10)
        .map_err(|error| error.to_string())?;
    if hit.disposition() != FullLruDisposition::Hit {
        return Err(String::from("v5 LRU recency hit was not reported"));
    }
    drop(hit);
    let replacement = cache
        .ensure(&mut adapter, &s12)
        .map_err(|error| format!("v5 LRU eviction: {error}"))?;
    if replacement.disposition() != FullLruDisposition::Evicted
        || !cache.contains(&s10)
        || cache.contains(&s11)
        || !cache.contains(&s12)
        || cache.resident_count() != 2
        || adapter.operations.len() != 39
    {
        return Err(String::from("v5 LRU hit did not refresh eviction order"));
    }
    drop(replacement);
    cache
        .release_if_unleased(&mut adapter, &s10)
        .map(|_release| ())
        .map_err(|error| format!("v5 LRU N10 cleanup: {error}"))?;
    cache
        .release_if_unleased(&mut adapter, &s12)
        .map(|_release| ())
        .map_err(|error| format!("v5 LRU N12 cleanup: {error}"))
}

#[test]
fn geometry_native_jump_rotate_halt_lru_skips_leased_victim()
-> Result<(), String> {
    let (s10, s11, s12) = full_lru_sequences()?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(154)?,
        native_executable_address(0x4_8000)?,
    );
    let mut cache = full_lru_cache(2)?;
    let n10_lease = cache
        .ensure(&mut adapter, &s10)
        .map_err(|error| format!("v5 LRU leased N10: {error}"))?
        .into_lease();
    drop(
        cache
            .ensure(&mut adapter, &s11)
            .map_err(|error| error.to_string())?,
    );
    let n12_lease = cache
        .ensure(&mut adapter, &s12)
        .map_err(|error| format!("v5 LRU skip lease: {error}"))?
        .into_lease();
    if !cache.contains(&s10)
        || cache.contains(&s11)
        || !cache.contains(&s12)
        || cache.resident_lease_count(&s10) != 1
        || n10_lease.sequence() != &s10
        || adapter.operations.len() != 39
    {
        return Err(String::from("v5 LRU eviction crossed live lease"));
    }
    drop((n10_lease, n12_lease));
    cache
        .release_if_unleased(&mut adapter, &s10)
        .map(|_release| ())
        .map_err(|error| format!("v5 LRU leased N10 cleanup: {error}"))?;
    cache
        .release_if_unleased(&mut adapter, &s12)
        .map(|_release| ())
        .map_err(|error| format!("v5 LRU leased N12 cleanup: {error}"))
}

#[test]
fn geometry_native_jump_rotate_halt_lru_saturates_when_all_leased()
-> Result<(), String> {
    let (s10, s11, s12) = full_lru_sequences()?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(155)?,
        native_executable_address(0x4_9000)?,
    );
    let mut cache = full_lru_cache(2)?;
    let lease10 = cache
        .ensure(&mut adapter, &s10)
        .map_err(|error| error.to_string())?;
    let lease11 = cache
        .ensure(&mut adapter, &s11)
        .map_err(|error| error.to_string())?;
    let Err(failure) = cache.ensure(&mut adapter, &s12) else {
        return Err(String::from("v5 LRU all-leased saturation was ignored"));
    };
    if !matches!(*failure, FullLruFailure::Saturated {
        leased_residents: 2,
        residents: 2,
    }) || adapter.operations.len() != 24
        || !cache.contains(&s10)
        || !cache.contains(&s11)
        || cache.contains(&s12)
    {
        return Err(String::from("v5 LRU saturation performed eviction work"));
    }
    drop((lease10, lease11));
    cache
        .release_if_unleased(&mut adapter, &s10)
        .map(|_release| ())
        .map_err(|error| format!("v5 LRU saturated N10 cleanup: {error}"))?;
    cache
        .release_if_unleased(&mut adapter, &s11)
        .map(|_release| ())
        .map_err(|error| format!("v5 LRU saturated N11 cleanup: {error}"))
}

#[test]
fn geometry_native_jump_rotate_halt_lru_eviction_release_failure_isolated()
-> Result<(), String> {
    let (s10, s11, s12) = full_lru_sequences()?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(156)?,
        native_executable_address(0x4_a000)?,
    )
    .with_release_failures(3);
    let mut cache = full_lru_cache(2)?;
    drop(
        cache
            .ensure(&mut adapter, &s10)
            .map_err(|error| error.to_string())?,
    );
    drop(
        cache
            .ensure(&mut adapter, &s11)
            .map_err(|error| error.to_string())?,
    );
    let Err(failure) = cache.ensure(&mut adapter, &s12) else {
        return Err(String::from("v5 LRU eviction release failure ignored"));
    };
    let FullLruFailure::EvictionRelease(cleanup) = *failure else {
        return Err(String::from("v5 LRU eviction release cause drifted"));
    };
    if !full_lru_cleanup_retains_all(&cleanup)
        || !full_lru_contains_only(&cache, &s11, &s10, &s12)
        || adapter.operations.len() != 27
    {
        return Err(String::from("v5 LRU release failure damaged survivors"));
    }
    cleanup
        .retry(&mut adapter)
        .map_err(|error| format!("v5 LRU victim cleanup retry: {error}"))?;
    cache
        .release_if_unleased(&mut adapter, &s11)
        .map(|_release| ())
        .map_err(|error| format!("v5 LRU survivor cleanup: {error}"))
}

#[test]
fn geometry_native_jump_rotate_halt_lru_load_failure_leaves_vacancy()
-> Result<(), String> {
    let (s10, s11, s12) = full_lru_sequences()?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(157)?,
        native_executable_address(0x4_b000)?,
    )
    .with_failure_at(FakeNativeAdapterOperation::Allocate, 7);
    let mut cache = full_lru_cache(2)?;
    drop(
        cache
            .ensure(&mut adapter, &s10)
            .map_err(|error| error.to_string())?,
    );
    drop(
        cache
            .ensure(&mut adapter, &s11)
            .map_err(|error| error.to_string())?,
    );
    let Err(failure) = cache.ensure(&mut adapter, &s12) else {
        return Err(String::from("v5 LRU post-eviction load failure ignored"));
    };
    let load_failed = matches!(
        *failure,
        FullLruFailure::Load(error)
            if matches!(
                &*error,
                FullGeometryTripleLoadFailure::Suffix(_error)
            )
    );
    if !load_failed
        || cache.contains(&s10)
        || !cache.contains(&s11)
        || cache.contains(&s12)
        || cache.resident_count() != 1
        || adapter.operations.len() != 28
    {
        return Err(String::from("v5 LRU failed load restored stale victim"));
    }
    let inserted = cache
        .ensure(&mut adapter, &s12)
        .map_err(|error| format!("v5 LRU vacancy refill: {error}"))?;
    if inserted.disposition() != FullLruDisposition::Inserted
        || cache.resident_count() != 2
        || adapter.operations.len() != 40
    {
        return Err(String::from("v5 LRU vacancy was not reusable"));
    }
    drop(inserted);
    cache
        .release_if_unleased(&mut adapter, &s11)
        .map(|_release| ())
        .map_err(|error| format!("v5 LRU load survivor cleanup: {error}"))?;
    cache
        .release_if_unleased(&mut adapter, &s12)
        .map(|_release| ())
        .map_err(|error| format!("v5 LRU load refill cleanup: {error}"))
}

#[test]
fn geometry_native_jump_rotate_halt_lru_release_targets_identity()
-> Result<(), String> {
    let n10 = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let n11 = derived_v5_jump_rotate_halt_sequence_fixture(11)?;
    let s10 = geometry_native_jump_rotate_halt_sequence(&n10)?;
    let s11 = geometry_native_jump_rotate_halt_sequence(&n11)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(158)?,
        native_executable_address(0x4_c000)?,
    );
    let mut cache = full_lru_cache(2)?;
    let lease10 = cache
        .ensure(&mut adapter, &s10)
        .map_err(|error| format!("v5 LRU release N10 acquire: {error}"))?
        .into_lease();
    drop(
        cache
            .ensure(&mut adapter, &s11)
            .map_err(|error| error.to_string())?,
    );
    let blocked = cache
        .release_if_unleased(&mut adapter, &s10)
        .map_err(|error| format!("v5 LRU release N10 blocked: {error}"))?;
    let released11 = cache
        .release_if_unleased(&mut adapter, &s11)
        .map_err(|error| format!("v5 LRU release N11: {error}"))?;
    if blocked != (FullLruRelease::Leased { leases: 1 })
        || released11 != FullLruRelease::Released
        || !cache.contains(&s10)
        || cache.contains(&s11)
        || cache.resident_count() != 1
        || adapter.operations.len() != 27
    {
        return Err(String::from("v5 LRU targeted release crossed identity"));
    }
    drop(lease10);
    let released10 = cache
        .release_if_unleased(&mut adapter, &s10)
        .map_err(|error| format!("v5 LRU release N10 final: {error}"))?;
    if released10 == FullLruRelease::Released
        && cache.resident_count() == 0
        && adapter.operations.len() == 30
    {
        Ok(())
    } else {
        Err(String::from("v5 LRU final targeted release drifted"))
    }
}

#[test]
fn geometry_native_jump_rotate_halt_cache_insert_hit_reuses_resident()
-> Result<(), String> {
    let fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_jump_rotate_halt_sequence(&fixture)?;
    let [initial, _jump, _rotate, final_state] = fixture.states.as_slice()
    else {
        return Err(String::from("v5 full cache state sequence incomplete"));
    };
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(143)?,
        native_executable_address(0x3_d000)?,
    );
    let mut cache = FullLeaseCache::new();
    let first = cache
        .ensure(&mut adapter, &sequence)
        .map_err(|error| format!("v5 full cache insert: {error}"))?;
    let first_disposition = first.disposition();
    let first_lease = first.into_lease();
    let second = cache
        .ensure(&mut adapter, &sequence)
        .map_err(|error| format!("v5 full cache hit: {error}"))?;
    let second_disposition = second.disposition();
    let second_lease = second.into_lease();
    if first_disposition != FullCacheDisposition::Inserted
        || second_disposition != FullCacheDisposition::Hit
        || !first_lease.shares_resident_with(&second_lease)
        || cache.resident_lease_count() != 2
        || adapter.operations.len() != 12
    {
        return Err(String::from("v5 full cache resident reuse drifted"));
    }
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = first_lease
        .execute(
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| format!("v5 full cache lease execute: {error}"))?;
    if outcome.state() != final_state
        || memory != final_state.memory()
        || adapter.operations.len() != 12
    {
        return Err(String::from("v5 full cache lease execution remapped"));
    }
    drop((first_lease, second_lease));
    let released = cache
        .release_if_unleased(&mut adapter)
        .map_err(|error| format!("v5 full cache final release: {error}"))?;
    if released != FullCacheRelease::Released
        || cache.has_resident()
        || adapter.operations.len() != 15
    {
        return Err(String::from("v5 full cache final release drifted"));
    }
    Ok(())
}

#[test]
fn geometry_native_jump_rotate_halt_cache_live_lease_blocks_release()
-> Result<(), String> {
    let fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_jump_rotate_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(144)?,
        native_executable_address(0x3_e000)?,
    );
    let mut cache = FullLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &sequence)
        .map_err(|error| format!("v5 full cache lease acquire: {error}"))?
        .into_lease();
    let blocked = cache
        .release_if_unleased(&mut adapter)
        .map_err(|error| format!("v5 full cache blocked release: {error}"))?;
    if blocked != (FullCacheRelease::Leased { leases: 1 })
        || adapter.operations.len() != 12
        || cache.resident_lease_count() != 1
    {
        return Err(String::from("v5 full cache live lease did not block"));
    }
    drop(lease);
    let released = cache
        .release_if_unleased(&mut adapter)
        .map_err(|error| format!("v5 full cache unblocked release: {error}"))?;
    if released == FullCacheRelease::Released && adapter.operations.len() == 15
    {
        Ok(())
    } else {
        Err(String::from("v5 full cache unblocked release drifted"))
    }
}

#[test]
fn geometry_native_jump_rotate_halt_cache_rejects_different_identity()
-> Result<(), String> {
    let n10_fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_jump_rotate_halt_sequence_fixture(11)?;
    let n10 = geometry_native_jump_rotate_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_jump_rotate_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(145)?,
        native_executable_address(0x3_f000)?,
    );
    let mut cache = FullLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &n10)
        .map_err(|error| format!("v5 full cache N10 acquire: {error}"))?
        .into_lease();
    let Err(failure) = cache.ensure(&mut adapter, &n11) else {
        return Err(String::from("v5 full cache mixed identity admitted"));
    };
    if !matches!(*failure, FullCacheFailure::IdentityOccupied)
        || adapter.operations.len() != 12
        || lease.sequence() != &n10
    {
        return Err(String::from("v5 full cache mixed identity drifted"));
    }
    drop(lease);
    cache
        .release_if_unleased(&mut adapter)
        .map(|_release| ())
        .map_err(|error| format!("v5 full cache N10 cleanup: {error}"))
}

#[test]
fn geometry_native_jump_rotate_halt_cache_load_failure_publishes_nothing()
-> Result<(), String> {
    let fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_jump_rotate_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(146)?,
        native_executable_address(0x4_0000)?,
    )
    .with_failure_at(FakeNativeAdapterOperation::Allocate, 3);
    let mut cache = FullLeaseCache::new();
    let Err(failure) = cache.ensure(&mut adapter, &sequence) else {
        return Err(String::from("v5 full cache failed load was published"));
    };
    let load_failed = matches!(
        *failure,
        FullCacheFailure::Load(error)
            if matches!(
                *error,
                FullGeometryTripleLoadFailure::InitialJump { .. }
            )
    );
    let release = cache
        .release_if_unleased(&mut adapter)
        .map_err(|error| format!("v5 full empty cache release: {error}"))?;
    if load_failed
        && !cache.has_resident()
        && release == FullCacheRelease::Missing
        && adapter.operations.len() == 11
    {
        Ok(())
    } else {
        Err(String::from(
            "v5 full cache partial load published authority",
        ))
    }
}

#[test]
fn geometry_native_jump_rotate_halt_cache_release_transfers_ownership()
-> Result<(), String> {
    let fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_jump_rotate_halt_sequence(&fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(147)?,
        native_executable_address(0x4_1000)?,
    )
    .with_release_failures(3);
    let mut cache = FullLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &sequence)
        .map_err(|error| format!("v5 full cache release acquire: {error}"))?
        .into_lease();
    drop(lease);
    let Err(failure) = cache.release_if_unleased(&mut adapter) else {
        return Err(String::from("v5 full cache release failure ignored"));
    };
    let suffix = failure.suffix_failure().ok_or_else(|| {
        String::from("v5 full cache suffix cleanup ownership missing")
    })?;
    if cache.has_resident()
        || failure.initial_jump_failure().is_none()
        || suffix.halt_failure().is_none()
        || suffix.rotate_failure().is_none()
        || adapter.operations.len() != 15
    {
        return Err(String::from("v5 full cache cleanup transfer drifted"));
    }
    failure
        .retry(&mut adapter)
        .map_err(|error| format!("v5 full cache cleanup retry: {error}"))
}

#[test]
fn geometry_native_jump_rotate_halt_cache_replace_blocks_live_lease()
-> Result<(), String> {
    let n10_fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_jump_rotate_halt_sequence_fixture(11)?;
    let n10 = geometry_native_jump_rotate_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_jump_rotate_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(148)?,
        native_executable_address(0x4_2000)?,
    );
    let mut cache = FullLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &n10)
        .map_err(|error| format!("v5 full replace N10 acquire: {error}"))?
        .into_lease();
    let Err(failure) = cache.replace_if_unleased(&mut adapter, &n11) else {
        return Err(String::from("v5 full replacement ignored live lease"));
    };
    if !matches!(*failure, FullCacheFailure::Leased { leases: 1 })
        || adapter.operations.len() != 12
        || lease.sequence() != &n10
    {
        return Err(String::from("v5 full live-lease replacement drifted"));
    }
    drop(lease);
    cache
        .release_if_unleased(&mut adapter)
        .map(|_release| ())
        .map_err(|error| format!("v5 full replace blocked cleanup: {error}"))
}

#[test]
fn geometry_native_jump_rotate_halt_cache_replace_publishes_identity()
-> Result<(), String> {
    let n10_fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_jump_rotate_halt_sequence_fixture(11)?;
    let n10 = geometry_native_jump_rotate_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_jump_rotate_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(149)?,
        native_executable_address(0x4_3000)?,
    );
    let mut cache = FullLeaseCache::new();
    let first = cache
        .ensure(&mut adapter, &n10)
        .map_err(|error| format!("v5 full replace first acquire: {error}"))?
        .into_lease();
    drop(first);
    let replacement = cache
        .replace_if_unleased(&mut adapter, &n11)
        .map_err(|error| format!("v5 full replace N11: {error}"))?;
    if replacement.disposition() != FullCacheDisposition::Replaced
        || replacement.lease().sequence() != &n11
        || adapter.operations.len() != 27
    {
        return Err(String::from("v5 full replacement publication drifted"));
    }
    drop(replacement);
    let released = cache
        .release_if_unleased(&mut adapter)
        .map_err(|error| format!("v5 full replacement cleanup: {error}"))?;
    if released == FullCacheRelease::Released && adapter.operations.len() == 30
    {
        Ok(())
    } else {
        Err(String::from("v5 full replacement final release drifted"))
    }
}

#[test]
fn geometry_native_jump_rotate_halt_cache_replace_release_failure_empties()
-> Result<(), String> {
    let n10_fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_jump_rotate_halt_sequence_fixture(11)?;
    let n10 = geometry_native_jump_rotate_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_jump_rotate_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(150)?,
        native_executable_address(0x4_4000)?,
    )
    .with_release_failures(3);
    let mut cache = FullLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &n10)
        .map_err(|error| format!("v5 full replace release acquire: {error}"))?
        .into_lease();
    drop(lease);
    let Err(failure) = cache.replace_if_unleased(&mut adapter, &n11) else {
        return Err(String::from(
            "v5 full replacement release failure ignored",
        ));
    };
    let FullCacheFailure::Release(cleanup) = *failure else {
        return Err(String::from("v5 full replacement release cause drifted"));
    };
    let suffix = cleanup.suffix_failure().ok_or_else(|| {
        String::from("v5 full replacement suffix cleanup missing")
    })?;
    if cache.has_resident()
        || cleanup.initial_jump_failure().is_none()
        || suffix.halt_failure().is_none()
        || suffix.rotate_failure().is_none()
        || adapter.operations.len() != 15
    {
        return Err(String::from("v5 full replacement cleanup drifted"));
    }
    cleanup
        .retry(&mut adapter)
        .map_err(|error| format!("v5 full replacement release retry: {error}"))
}

#[test]
fn geometry_native_jump_rotate_halt_cache_replace_load_failure_empties()
-> Result<(), String> {
    let n10_fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_jump_rotate_halt_sequence_fixture(11)?;
    let n10 = geometry_native_jump_rotate_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_jump_rotate_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(151)?,
        native_executable_address(0x4_5000)?,
    )
    .with_failure_at(FakeNativeAdapterOperation::Allocate, 4);
    let mut cache = FullLeaseCache::new();
    let lease = cache
        .ensure(&mut adapter, &n10)
        .map_err(|error| format!("v5 full replace load acquire: {error}"))?
        .into_lease();
    drop(lease);
    let Err(failure) = cache.replace_if_unleased(&mut adapter, &n11) else {
        return Err(String::from("v5 full replacement load failure ignored"));
    };
    let load_failed = matches!(
        *failure,
        FullCacheFailure::Load(error)
            if matches!(
                &*error,
                FullGeometryTripleLoadFailure::Suffix(_error)
            )
    );
    if load_failed && !cache.has_resident() && adapter.operations.len() == 16 {
        Ok(())
    } else {
        Err(String::from("v5 full replacement load publication drifted"))
    }
}

#[test]
fn geometry_native_jump_rotate_halt_prebind_rejects_mixed_jump()
-> Result<(), String> {
    let n10_fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let n11_fixture = derived_v5_jump_rotate_halt_sequence_fixture(11)?;
    let n10 = geometry_native_jump_rotate_halt_sequence(&n10_fixture)?;
    let n11 = geometry_native_jump_rotate_halt_sequence(&n11_fixture)?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(136)?,
        native_executable_address(0x3_6000)?,
    );
    let jump = load_execution_geometry_native_executable(
        &mut adapter,
        n11.initial_jump().load_image(),
    )
    .map_err(|error| format!("v5 mixed prebind jump load: {error}"))?;
    let rotate = load_execution_geometry_native_executable(
        &mut adapter,
        n10.suffix().rotate().load_image(),
    )
    .map_err(|error| format!("v5 mixed prebind rotate load: {error}"))?;
    let halt = load_execution_geometry_native_executable(
        &mut adapter,
        n10.suffix().halt().load_image(),
    )
    .map_err(|error| format!("v5 mixed prebind halt load: {error}"))?;
    let rejected = matches!(
        n10.bind_executables(&jump, &rotate, &halt),
        Err(FullGeometryBindingError::InitialJump)
    );
    release_execution_geometry_native_executable(&mut adapter, jump)
        .map_err(|error| format!("v5 mixed prebind jump release: {error}"))?;
    release_execution_geometry_native_executable(&mut adapter, rotate)
        .map_err(|error| format!("v5 mixed prebind rotate release: {error}"))?;
    release_execution_geometry_native_executable(&mut adapter, halt)
        .map_err(|error| format!("v5 mixed prebind halt release: {error}"))?;
    if rejected && adapter.operations.len() == 15 {
        Ok(())
    } else {
        Err(String::from("v5 mixed prebound jump was admitted"))
    }
}

#[test]
fn geometry_native_jump_rotate_halt_prebound_late_failure_retains_rotate()
-> Result<(), String> {
    let fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_jump_rotate_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 prebound initial state missing"))?;
    let rotate_state = fixture
        .states
        .get(2)
        .ok_or_else(|| String::from("v5 prebound rotate state missing"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(137)?,
        native_executable_address(0x3_7000)?,
    );
    let (jump, rotate, halt) =
        load_geometry_native_jump_rotate_halt_triple(&mut adapter, &sequence)?;
    {
        let bound = sequence
            .bind_executables(&jump, &rotate, &halt)
            .map_err(|error| format!("v5 full prebind bind: {error}"))?;
        let mut memory = initial.memory().to_vec();
        let input = initial.io().input().to_vec();
        let mut output = initial.io().output().to_vec();
        let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::FailureAfterMutation,
        ]);
        let Err(failure) = bound.execute(
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        ) else {
            return Err(String::from("v5 prebound late failure was ignored"));
        };
        let suffix_halt_failure = matches!(
            failure.cause(),
            FullGeometryLoadedFailureCause::Suffix(suffix)
                if matches!(
                    suffix.cause(),
                    RHLoadedCause::HaltExecution(_error)
                )
        );
        if failure.index() != 2
            || failure.state() != rotate_state
            || memory != rotate_state.memory()
            || runner.calls != 3
            || adapter.operations.len() != 12
            || !suffix_halt_failure
        {
            return Err(String::from("v5 prebound late failure lost rotate"));
        }
    }
    release_execution_geometry_native_executable(&mut adapter, jump)
        .map_err(|error| format!("v5 prebound jump release: {error}"))?;
    release_execution_geometry_native_executable(&mut adapter, rotate)
        .map_err(|error| format!("v5 prebound rotate release: {error}"))?;
    release_execution_geometry_native_executable(&mut adapter, halt)
        .map_err(|error| format!("v5 prebound halt release: {error}"))
}

#[test]
fn geometry_native_jump_rotate_halt_prebound_reuses_three_executables()
-> Result<(), String> {
    let fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_jump_rotate_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 prebound initial state missing"))?;
    let final_state = fixture
        .states
        .get(3)
        .ok_or_else(|| String::from("v5 prebound final state missing"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(138)?,
        native_executable_address(0x3_8000)?,
    );
    let (jump, rotate, halt) =
        load_geometry_native_jump_rotate_halt_triple(&mut adapter, &sequence)?;
    {
        let bound = sequence
            .bind_executables(&jump, &rotate, &halt)
            .map_err(|error| format!("v5 full prebind bind: {error}"))?;
        let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::Applied,
        ]);
        for _iteration in 0usize..2usize {
            let mut memory = initial.memory().to_vec();
            let input = initial.io().input().to_vec();
            let mut output = initial.io().output().to_vec();
            let outcome = bound
                .execute(
                    &mut runner,
                    NativeRegionBuffers::new(&mut memory, &input, &mut output),
                )
                .map_err(|error| format!("v5 full prebind execute: {error}"))?;
            if outcome != FullGeometryOutcome::Completed(final_state.clone())
                || memory != final_state.memory()
                || output != final_state.io().output()
            {
                return Err(String::from("v5 prebound reuse state drifted"));
            }
        }
        if runner.calls != 6 || adapter.operations.len() != 12 {
            return Err(String::from("v5 prebound reuse remapped triple"));
        }
    }
    release_execution_geometry_native_executable(&mut adapter, jump)
        .map_err(|error| format!("v5 prebound jump release: {error}"))?;
    release_execution_geometry_native_executable(&mut adapter, rotate)
        .map_err(|error| format!("v5 prebound rotate release: {error}"))?;
    release_execution_geometry_native_executable(&mut adapter, halt)
        .map_err(|error| format!("v5 prebound halt release: {error}"))?;
    if adapter.operations.len() == 15 {
        Ok(())
    } else {
        Err(String::from("v5 prebound triple release drifted"))
    }
}

#[test]
fn geometry_native_jump_rotate_halt_applies_three_steps() -> Result<(), String>
{
    let fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_jump_rotate_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 full-path initial state missing"))?;
    let final_state = fixture
        .states
        .get(3)
        .ok_or_else(|| String::from("v5 full-path final state missing"))?;
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(132)?,
        native_executable_address(0x3_2000)?,
    );
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = sequence
        .execute_transactionally(
            &mut adapter,
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| error.to_string())?;
    if outcome != FullGeometryOutcome::Completed(final_state.clone())
        || outcome.state().geometry() != fixture.geometry
        || memory != final_state.memory()
        || output != final_state.io().output()
        || runner.calls != 3
        || adapter.operations.len() != 15
    {
        Err(String::from("v5 full-path completion drifted"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_jump_rotate_halt_guard_miss_stops_at_jump()
-> Result<(), String> {
    let fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_jump_rotate_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 full-path initial state missing"))?;
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(133)?,
        native_executable_address(0x3_3000)?,
    );
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::GuardMiss,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = sequence
        .execute_transactionally(
            &mut adapter,
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| error.to_string())?;
    if outcome
        != (FullGeometryOutcome::GuardMiss {
            index: 0,
            state: initial.clone(),
        })
        || runner.calls != 1
        || memory != initial.memory()
        || adapter.operations.len() != 5
    {
        Err(String::from("v5 full-path jump miss executed suffix"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_jump_rotate_halt_rejects_mixed_geometry()
-> Result<(), String> {
    let n10 = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let n11 = derived_v5_jump_rotate_halt_sequence_fixture(11)?;
    let checkpoint =
        n10.states.first().cloned().ok_or_else(|| {
            String::from("v5 mixed full-path checkpoint missing")
        })?;
    let evidence = geometry_native_jump_rotate_halt_evidence(&n10, &n11)?;
    if matches!(
        FullGeometrySequence::new(evidence, checkpoint),
        Err(FullGeometryAdmissionError::Suffix(_error))
    ) {
        Ok(())
    } else {
        Err(String::from("v5 mixed full-path geometry was admitted"))
    }
}

#[test]
fn geometry_native_jump_rotate_halt_rotate_miss_retains_jump()
-> Result<(), String> {
    let fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_jump_rotate_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 full-path initial state missing"))?;
    let jump_state = fixture
        .states
        .get(1)
        .ok_or_else(|| String::from("v5 full-path jump state missing"))?;
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(134)?,
        native_executable_address(0x3_4000)?,
    );
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::GuardMiss,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = sequence
        .execute_transactionally(
            &mut adapter,
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| error.to_string())?;
    if outcome
        != (FullGeometryOutcome::GuardMiss {
            index: 1,
            state: jump_state.clone(),
        })
        || runner.calls != 2
        || memory != jump_state.memory()
        || adapter.operations.len() != 10
    {
        Err(String::from("v5 full-path rotate miss lost jump prefix"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_jump_rotate_halt_late_failure_retains_rotate()
-> Result<(), String> {
    let fixture = derived_v5_jump_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_jump_rotate_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 full-path initial state missing"))?;
    let rotate_state = fixture
        .states
        .get(2)
        .ok_or_else(|| String::from("v5 full-path rotate state missing"))?;
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(135)?,
        native_executable_address(0x3_5000)?,
    );
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let Err(failure) = sequence.execute_transactionally(
        &mut adapter,
        &mut runner,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    ) else {
        return Err(String::from("v5 full-path late failure was ignored"));
    };
    let suffix_halt_failure = matches!(
        failure.cause(),
        FullGeometryFailureCause::Suffix(suffix)
            if matches!(
                suffix.cause(),
                ExecutionGeometryNativeRotateHaltFailureCause::Halt(_error)
            )
    );
    if failure.index() != 2
        || failure.state() != rotate_state
        || memory != rotate_state.memory()
        || runner.calls != 3
        || adapter.operations.len() != 15
        || !suffix_halt_failure
    {
        Err(String::from("v5 full-path late failure lost rotate prefix"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_rotate_halt_applies_two_steps() -> Result<(), String> {
    let fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_rotate_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 sequence initial state missing"))?;
    let final_state = fixture
        .states
        .get(2)
        .ok_or_else(|| String::from("v5 sequence final state missing"))?;
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(112)?,
        native_executable_address(0x1_e000)?,
    );
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = sequence
        .execute_transactionally(
            &mut adapter,
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| error.to_string())?;
    if outcome
        != ExecutionGeometryNativeRotateHaltOutcome::Completed(
            final_state.clone(),
        )
        || outcome.state().geometry() != fixture.geometry
        || memory != final_state.memory()
        || output != final_state.io().output()
        || runner.calls != 2
        || adapter.operations.len() != 10
    {
        Err(String::from("v5 rotate/halt completion drifted"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_rotate_halt_sequence_guard_miss_stops_first_suffix()
-> Result<(), String> {
    let fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_rotate_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 sequence initial state missing"))?;
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(113)?,
        native_executable_address(0x1_f000)?,
    );
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::GuardMiss,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = sequence
        .execute_transactionally(
            &mut adapter,
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| error.to_string())?;
    if outcome
        != (ExecutionGeometryNativeRotateHaltOutcome::GuardMiss {
            index: 0,
            state: initial.clone(),
        })
        || runner.calls != 1
        || memory != initial.memory()
        || adapter.operations.len() != 5
    {
        Err(String::from("v5 first guard miss executed suffix"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_rotate_halt_sequence_guard_miss_retains_prefix()
-> Result<(), String> {
    let fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_rotate_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 sequence initial state missing"))?;
    let prefix = fixture
        .states
        .get(1)
        .ok_or_else(|| String::from("v5 sequence prefix state missing"))?;
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(114)?,
        native_executable_address(0x2_0000)?,
    );
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let outcome = sequence
        .execute_transactionally(
            &mut adapter,
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| error.to_string())?;
    if outcome
        != (ExecutionGeometryNativeRotateHaltOutcome::GuardMiss {
            index: 1,
            state: prefix.clone(),
        })
        || runner.calls != 2
        || memory != prefix.memory()
    {
        Err(String::from("v5 second guard miss lost committed prefix"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_rotate_halt_sequence_late_failure_retains_prefix()
-> Result<(), String> {
    let fixture = derived_v5_rotate_halt_sequence_fixture(10)?;
    let sequence = geometry_native_rotate_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 sequence initial state missing"))?;
    let prefix = fixture
        .states
        .get(1)
        .ok_or_else(|| String::from("v5 sequence prefix state missing"))?;
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(115)?,
        native_executable_address(0x2_1000)?,
    );
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let Err(failure) = sequence.execute_transactionally(
        &mut adapter,
        &mut runner,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    ) else {
        return Err(String::from("v5 late sequence failure was ignored"));
    };
    if failure.index() != 1
        || failure.state() != prefix
        || memory != prefix.memory()
        || !matches!(
            failure.cause(),
            ExecutionGeometryNativeRotateHaltFailureCause::Halt(_error)
        )
    {
        Err(String::from("v5 late failure lost committed prefix"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_rotate_halt_sequence_rejects_mixed_geometry()
-> Result<(), String> {
    let n10 = derived_v5_rotate_halt_sequence_fixture(10)?;
    let n11 = derived_v5_rotate_halt_sequence_fixture(11)?;
    let rotate = n10
        .programs
        .first()
        .cloned()
        .ok_or_else(|| String::from("v5 N10 rotate missing"))?;
    let checkpoint = n10
        .states
        .first()
        .cloned()
        .ok_or_else(|| String::from("v5 N10 checkpoint missing"))?;
    let halt = n11
        .programs
        .get(1)
        .cloned()
        .ok_or_else(|| String::from("v5 N11 halt missing"))?;
    let rotate_object = emit_direct_execution_geometry_rotate_coff(
        &rotate,
        direct_execution_geometry_rotate_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 mixed rotate emit: {error}"))?;
    let rotate_artifact =
        verify_direct_execution_geometry_rotate(&rotate_object, &rotate)
            .map_err(|error| format!("v5 mixed rotate verify: {error}"))?;
    let halt_object = emit_direct_execution_geometry_initial_halt_coff(
        &halt,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 mixed halt emit: {error}"))?;
    let halt_artifact =
        verify_direct_execution_geometry_initial_halt(&halt_object, &halt)
            .map_err(|error| format!("v5 mixed halt verify: {error}"))?;
    let evidence = ExecutionGeometryNativeRotateHaltEvidence::new(
        rotate,
        rotate_artifact,
        halt,
        halt_artifact,
    );
    if matches!(
        ExecutionGeometryNativeRotateHaltSequence::new(evidence, checkpoint),
        Err(ExecutionGeometryNativeRotateHaltAdmissionError::Halt(
            _error
        ))
    ) {
        Ok(())
    } else {
        Err(String::from("v5 mixed sequence geometry was admitted"))
    }
}

#[test]
fn geometry_native_noop_halt_sequence_applies_two_steps() -> Result<(), String>
{
    let fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let sequence = geometry_native_noop_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 sequence initial state missing"))?;
    let final_state = fixture
        .states
        .get(2)
        .ok_or_else(|| String::from("v5 sequence final state missing"))?;
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(112)?,
        native_executable_address(0x1_e000)?,
    );
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = sequence
        .execute_transactionally(
            &mut adapter,
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| error.to_string())?;
    if outcome
        != ExecutionGeometryNativeNoopHaltOutcome::Completed(
            final_state.clone(),
        )
        || outcome.state().geometry() != fixture.geometry
        || memory != final_state.memory()
        || output != final_state.io().output()
        || runner.calls != 2
        || adapter.operations.len() != 10
    {
        Err(String::from("v5 no-op/halt completion drifted"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_noop_halt_sequence_guard_miss_stops_first_suffix()
-> Result<(), String> {
    let fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let sequence = geometry_native_noop_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 sequence initial state missing"))?;
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(113)?,
        native_executable_address(0x1_f000)?,
    );
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::GuardMiss,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = sequence
        .execute_transactionally(
            &mut adapter,
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| error.to_string())?;
    if outcome
        != (ExecutionGeometryNativeNoopHaltOutcome::GuardMiss {
            index: 0,
            state: initial.clone(),
        })
        || runner.calls != 1
        || memory != initial.memory()
        || adapter.operations.len() != 5
    {
        Err(String::from("v5 first guard miss executed suffix"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_noop_halt_sequence_guard_miss_retains_prefix()
-> Result<(), String> {
    let fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let sequence = geometry_native_noop_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 sequence initial state missing"))?;
    let prefix = fixture
        .states
        .get(1)
        .ok_or_else(|| String::from("v5 sequence prefix state missing"))?;
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(114)?,
        native_executable_address(0x2_0000)?,
    );
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let outcome = sequence
        .execute_transactionally(
            &mut adapter,
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| error.to_string())?;
    if outcome
        != (ExecutionGeometryNativeNoopHaltOutcome::GuardMiss {
            index: 1,
            state: prefix.clone(),
        })
        || runner.calls != 2
        || memory != prefix.memory()
    {
        Err(String::from("v5 second guard miss lost committed prefix"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_noop_halt_sequence_late_failure_retains_prefix()
-> Result<(), String> {
    let fixture = derived_v5_noop_halt_sequence_fixture(10)?;
    let sequence = geometry_native_noop_halt_sequence(&fixture)?;
    let initial = fixture
        .states
        .first()
        .ok_or_else(|| String::from("v5 sequence initial state missing"))?;
    let prefix = fixture
        .states
        .get(1)
        .ok_or_else(|| String::from("v5 sequence prefix state missing"))?;
    let mut memory = initial.memory().to_vec();
    let input = initial.io().input().to_vec();
    let mut output = initial.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(115)?,
        native_executable_address(0x2_1000)?,
    );
    let mut runner = FakeExecutionGeometrySequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let Err(failure) = sequence.execute_transactionally(
        &mut adapter,
        &mut runner,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    ) else {
        return Err(String::from("v5 late sequence failure was ignored"));
    };
    if failure.index() != 1
        || failure.state() != prefix
        || memory != prefix.memory()
        || !matches!(
            failure.cause(),
            ExecutionGeometryNativeNoopHaltFailureCause::Halt(_error)
        )
    {
        Err(String::from("v5 late failure lost committed prefix"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_noop_halt_sequence_rejects_mixed_geometry()
-> Result<(), String> {
    let n10 = derived_v5_noop_halt_sequence_fixture(10)?;
    let n11 = derived_v5_noop_halt_sequence_fixture(11)?;
    let no_operation = n10
        .programs
        .first()
        .cloned()
        .ok_or_else(|| String::from("v5 N10 no-operation missing"))?;
    let checkpoint = n10
        .states
        .first()
        .cloned()
        .ok_or_else(|| String::from("v5 N10 checkpoint missing"))?;
    let halt = n11
        .programs
        .get(1)
        .cloned()
        .ok_or_else(|| String::from("v5 N11 halt missing"))?;
    let no_operation_object = emit_direct_execution_geometry_no_operation_coff(
        &no_operation,
        direct_execution_geometry_no_operation_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 mixed no-operation emit: {error}"))?;
    let no_operation_artifact = verify_direct_execution_geometry_no_operation(
        &no_operation_object,
        &no_operation,
    )
    .map_err(|error| format!("v5 mixed no-operation verify: {error}"))?;
    let halt_object = emit_direct_execution_geometry_initial_halt_coff(
        &halt,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 mixed halt emit: {error}"))?;
    let halt_artifact =
        verify_direct_execution_geometry_initial_halt(&halt_object, &halt)
            .map_err(|error| format!("v5 mixed halt verify: {error}"))?;
    let evidence = ExecutionGeometryNativeNoopHaltEvidence::new(
        no_operation,
        no_operation_artifact,
        halt,
        halt_artifact,
    );
    if matches!(
        ExecutionGeometryNativeNoopHaltSequence::new(evidence, checkpoint),
        Err(ExecutionGeometryNativeNoopHaltAdmissionError::Halt(_error))
    ) {
        Ok(())
    } else {
        Err(String::from("v5 mixed sequence geometry was admitted"))
    }
}

#[test]
fn geometry_native_initial_jump_binding_rejects_geometry() -> Result<(), String>
{
    let (admission, _geometry) =
        geometry_native_initial_jump_data_admission_fixture(10)?;
    let (n11, _checkpoint, _n11_geometry) =
        derived_v5_initial_jump_data_fixture(11)?;
    let n11_artifact = emit_direct_execution_geometry_initial_jump_data_coff(
        &n11,
        direct_execution_geometry_initial_jump_data_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 initial jump N11 bind emit: {error}"))?;
    let n11_verified =
        verify_direct_execution_geometry_initial_jump_data(&n11_artifact, &n11)
            .map_err(|error| {
                format!("v5 initial jump N11 bind verify: {error}")
            })?;
    let n11_image = VerifiedExecutionGeometryLoadImage::from_initial_jump_data(
        &n11_verified,
    )
    .map_err(|error| format!("v5 initial jump N11 bind image: {error}"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(105)?,
        native_executable_address(0x1_7000)?,
    );
    let n11_ready =
        load_execution_geometry_native_executable(&mut adapter, &n11_image)
            .map_err(|error| {
                format!("v5 initial jump N11 bind load: {error}")
            })?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 initial jump bind prepare: {error}"))?;
    if !matches!(
        prepared.bind_executable(&n11_ready),
        Err(InitialJumpBindingError::ExecutableIdentity)
    ) || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from(
            "v5 initial jump geometry bind rollback drifted",
        ));
    }
    release_execution_geometry_native_executable(&mut adapter, n11_ready)
        .map_err(|error| format!("v5 initial jump N11 bind release: {error}"))
}

#[test]
fn geometry_native_initial_jump_applies_normative_state() -> Result<(), String>
{
    let GeometryNativeInitialJumpDataRunnerFixture {
        mut adapter,
        admission,
        geometry,
        ready,
    } = geometry_native_initial_jump_data_runner_fixture(10, 106, 0x1_8000)?;
    let checkpoint = admission.checkpoint().clone();
    let expected = admission.expected_state().clone();
    if expected == checkpoint || expected.geometry() != geometry {
        return Err(String::from(
            "v5 initial jump normative replay did not advance",
        ));
    }
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 initial jump runner prepare: {error}"))?;
    let bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 initial jump runner bind: {error}"))?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::Applied,
    );
    let completion = bound
        .execute(&mut runner)
        .map_err(|error| format!("v5 initial jump runner execute: {error}"))?;
    if completion.state() != &expected
        || memory != expected.memory()
        || output != expected.io().output()
        || runner.calls != 1
        || runner.entry_addresses != [ready.entry_address()]
        || runner.mapping_ids != [ready.mapping().mapping_id()]
    {
        return Err(String::from(
            "v5 initial jump applied state drifted from replay",
        ));
    }
    release_execution_geometry_native_executable(&mut adapter, ready)
        .map_err(|error| format!("v5 initial jump runner release: {error}"))
}

#[test]
fn geometry_native_initial_jump_rejects_memory_drift() -> Result<(), String> {
    let (admission, _geometry) =
        geometry_native_initial_jump_data_admission_fixture(10)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let first = memory.first_mut().ok_or_else(|| {
        String::from("v5 initial jump checkpoint memory missing")
    })?;
    *first = first.saturating_add(1);
    let result = admission.prepare(NativeRegionBuffers::new(
        &mut memory,
        &input,
        &mut output,
    ));
    if matches!(result, Err(InitialJumpPreparationError::Memory)) {
        Ok(())
    } else {
        Err(String::from("v5 initial jump memory drift was admitted"))
    }
}

#[test]
fn geometry_native_initial_jump_completion_drift_rolls_back()
-> Result<(), String> {
    let GeometryNativeInitialJumpDataRunnerFixture {
        mut adapter,
        admission,
        geometry: _geometry,
        ready,
    } = geometry_native_initial_jump_data_runner_fixture(10, 109, 0x1_b000)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 initial jump drift prepare: {error}"))?;
    let bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 initial jump drift bind: {error}"))?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::CompletionDrift,
    );
    let Err(execution_error) = bound.execute(&mut runner) else {
        return Err(String::from(
            "v5 initial jump completion drift was admitted",
        ));
    };
    let completion_drift = matches!(
        *execution_error,
        InitialJumpExecutionError::Completion(
            InitialJumpCompletionError::Invocation(
                NativeRegionInvocationError::AppliedMemory { address: 0, .. },
            ),
        )
    );
    if !completion_drift
        || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from(
            "v5 initial jump completion rollback drifted",
        ));
    }
    release_execution_geometry_native_executable(&mut adapter, ready)
        .map_err(|error| format!("v5 initial jump drift release: {error}"))
}

#[test]
fn geometry_native_initial_jump_runner_failure_rollback() -> Result<(), String>
{
    let GeometryNativeInitialJumpDataRunnerFixture {
        mut adapter,
        admission,
        geometry: _geometry,
        ready,
    } = geometry_native_initial_jump_data_runner_fixture(10, 107, 0x1_9000)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| {
            format!("v5 initial jump failed runner prepare: {error}")
        })?;
    let bound = prepared.bind_executable(&ready).map_err(|error| {
        format!("v5 initial jump failed runner bind: {error}")
    })?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::FailureAfterMutation,
    );
    let Err(execution_error) = bound.execute(&mut runner) else {
        return Err(String::from("v5 initial jump runner failure was ignored"));
    };
    if !matches!(
        *execution_error,
        InitialJumpExecutionError::Runner(runner_error)
            if *runner_error == FakeNativeRunnerError::Call
    ) || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from("v5 initial jump runner rollback drifted"));
    }
    release_execution_geometry_native_executable(&mut adapter, ready).map_err(
        |error| format!("v5 initial jump failed runner release: {error}"),
    )
}

#[test]
fn geometry_native_initial_jump_guard_miss_preserves_checkpoint()
-> Result<(), String> {
    let GeometryNativeInitialJumpDataRunnerFixture {
        mut adapter,
        admission,
        geometry: _geometry,
        ready,
    } = geometry_native_initial_jump_data_runner_fixture(10, 108, 0x1_a000)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 initial jump miss prepare: {error}"))?;
    let bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 initial jump miss bind: {error}"))?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::GuardMiss,
    );
    let completion = bound
        .execute(&mut runner)
        .map_err(|error| format!("v5 initial jump miss execute: {error}"))?;
    if completion.outcome() != NativeRegionInvocationOutcome::GuardMiss
        || completion.state() != &checkpoint
        || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from(
            "v5 initial jump guard miss changed checkpoint",
        ));
    }
    release_execution_geometry_native_executable(&mut adapter, ready)
        .map_err(|error| format!("v5 initial jump miss release: {error}"))
}

#[test]
fn geometry_native_rotate_binding_rejects_different_geometry()
-> Result<(), String> {
    let (admission, _geometry) = geometry_native_rotate_admission_fixture(10)?;
    let (n11, _checkpoint, _n11_geometry) = derived_v5_rotate_fixture(11)?;
    let n11_artifact = emit_direct_execution_geometry_rotate_coff(
        &n11,
        direct_execution_geometry_rotate_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 rotate N11 bind emit: {error}"))?;
    let n11_verified =
        verify_direct_execution_geometry_rotate(&n11_artifact, &n11)
            .map_err(|error| format!("v5 rotate N11 bind verify: {error}"))?;
    let n11_image =
        VerifiedExecutionGeometryLoadImage::from_rotate(&n11_verified)
            .map_err(|error| format!("v5 rotate N11 bind image: {error}"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(105)?,
        native_executable_address(0x1_7000)?,
    );
    let n11_ready =
        load_execution_geometry_native_executable(&mut adapter, &n11_image)
            .map_err(|error| format!("v5 rotate N11 bind load: {error}"))?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 rotate bind prepare: {error}"))?;
    if !matches!(
        prepared.bind_executable(&n11_ready),
        Err(ExecutionGeometryNativeRotateBindingError::ExecutableIdentity)
    ) || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from("v5 rotate geometry bind did not roll back"));
    }
    release_execution_geometry_native_executable(&mut adapter, n11_ready)
        .map_err(|error| format!("v5 rotate N11 bind release: {error}"))
}

#[test]
fn geometry_native_rotate_runner_applies_normative_state() -> Result<(), String>
{
    let GeometryNativeRotateRunnerFixture {
        mut adapter,
        admission,
        geometry,
        ready,
    } = geometry_native_rotate_runner_fixture(10, 106, 0x1_8000)?;
    let checkpoint = admission.checkpoint().clone();
    let expected = admission.expected_state().clone();
    if expected == checkpoint || expected.geometry() != geometry {
        return Err(String::from("v5 rotate normative replay did not advance"));
    }
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 rotate runner prepare: {error}"))?;
    let bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 rotate runner bind: {error}"))?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::Applied,
    );
    let completion = bound
        .execute(&mut runner)
        .map_err(|error| format!("v5 rotate runner execute: {error}"))?;
    if completion.state() != &expected
        || memory != expected.memory()
        || output != expected.io().output()
        || runner.calls != 1
        || runner.entry_addresses != [ready.entry_address()]
        || runner.mapping_ids != [ready.mapping().mapping_id()]
    {
        return Err(String::from(
            "v5 rotate applied state drifted from replay",
        ));
    }
    release_execution_geometry_native_executable(&mut adapter, ready)
        .map_err(|error| format!("v5 rotate runner release: {error}"))
}

#[test]
fn geometry_native_rotate_preparation_rejects_memory_drift()
-> Result<(), String> {
    let (admission, _geometry) = geometry_native_rotate_admission_fixture(10)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let first = memory
        .first_mut()
        .ok_or_else(|| String::from("v5 rotate checkpoint memory missing"))?;
    *first = first.saturating_add(1);
    let result = admission.prepare(NativeRegionBuffers::new(
        &mut memory,
        &input,
        &mut output,
    ));
    if matches!(
        result,
        Err(ExecutionGeometryNativeRotatePreparationError::Memory)
    ) {
        Ok(())
    } else {
        Err(String::from("v5 rotate memory drift was admitted"))
    }
}

#[test]
fn geometry_native_rotate_runner_completion_drift_restores_checkpoint()
-> Result<(), String> {
    let GeometryNativeRotateRunnerFixture {
        mut adapter,
        admission,
        geometry: _geometry,
        ready,
    } = geometry_native_rotate_runner_fixture(10, 109, 0x1_b000)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 rotate drift prepare: {error}"))?;
    let bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 rotate drift bind: {error}"))?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::CompletionDrift,
    );
    let Err(execution_error) = bound.execute(&mut runner) else {
        return Err(String::from("v5 rotate completion drift was admitted"));
    };
    let completion_drift = matches!(
        *execution_error,
        ExecutionGeometryNativeRotateExecutionError::Completion(
            ExecutionGeometryNativeRotateCompletionError::Invocation(
                NativeRegionInvocationError::AppliedMemory { address: 0, .. },
            ),
        )
    );
    if !completion_drift
        || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from("v5 rotate completion rollback drifted"));
    }
    release_execution_geometry_native_executable(&mut adapter, ready)
        .map_err(|error| format!("v5 rotate drift release: {error}"))
}

#[test]
fn geometry_native_rotate_runner_failure_restores_checkpoint()
-> Result<(), String> {
    let GeometryNativeRotateRunnerFixture {
        mut adapter,
        admission,
        geometry: _geometry,
        ready,
    } = geometry_native_rotate_runner_fixture(10, 107, 0x1_9000)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 rotate failed runner prepare: {error}"))?;
    let bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 rotate failed runner bind: {error}"))?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::FailureAfterMutation,
    );
    let Err(execution_error) = bound.execute(&mut runner) else {
        return Err(String::from("v5 rotate runner failure was ignored"));
    };
    if !matches!(
        *execution_error,
        ExecutionGeometryNativeRotateExecutionError::Runner(runner_error)
            if *runner_error == FakeNativeRunnerError::Call
    ) || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from("v5 rotate runner rollback drifted"));
    }
    release_execution_geometry_native_executable(&mut adapter, ready)
        .map_err(|error| format!("v5 rotate failed runner release: {error}"))
}

#[test]
fn geometry_native_rotate_runner_guard_miss_preserves_checkpoint()
-> Result<(), String> {
    let GeometryNativeRotateRunnerFixture {
        mut adapter,
        admission,
        geometry: _geometry,
        ready,
    } = geometry_native_rotate_runner_fixture(10, 108, 0x1_a000)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 rotate miss prepare: {error}"))?;
    let bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 rotate miss bind: {error}"))?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::GuardMiss,
    );
    let completion = bound
        .execute(&mut runner)
        .map_err(|error| format!("v5 rotate miss execute: {error}"))?;
    if completion.outcome() != NativeRegionInvocationOutcome::GuardMiss
        || completion.state() != &checkpoint
        || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from("v5 rotate guard miss changed checkpoint"));
    }
    release_execution_geometry_native_executable(&mut adapter, ready)
        .map_err(|error| format!("v5 rotate miss release: {error}"))
}

#[test]
fn geometry_native_no_operation_binding_rejects_different_geometry()
-> Result<(), String> {
    let (admission, _geometry) =
        geometry_native_no_operation_admission_fixture(10)?;
    let (n11, _checkpoint, _n11_geometry) =
        derived_v5_no_operation_fixture(11)?;
    let n11_artifact = emit_direct_execution_geometry_no_operation_coff(
        &n11,
        direct_execution_geometry_no_operation_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 no-op N11 bind emit: {error}"))?;
    let n11_verified =
        verify_direct_execution_geometry_no_operation(&n11_artifact, &n11)
            .map_err(|error| format!("v5 no-op N11 bind verify: {error}"))?;
    let n11_image =
        VerifiedExecutionGeometryLoadImage::from_no_operation(&n11_verified)
            .map_err(|error| format!("v5 no-op N11 bind image: {error}"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(105)?,
        native_executable_address(0x1_7000)?,
    );
    let n11_ready =
        load_execution_geometry_native_executable(&mut adapter, &n11_image)
            .map_err(|error| format!("v5 no-op N11 bind load: {error}"))?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 no-op bind prepare: {error}"))?;
    if !matches!(
        prepared.bind_executable(&n11_ready),
        Err(ExecutionGeometryNativeNoOperationBindingError::ExecutableIdentity)
    ) || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from("v5 no-op geometry bind did not roll back"));
    }
    release_execution_geometry_native_executable(&mut adapter, n11_ready)
        .map_err(|error| format!("v5 no-op N11 bind release: {error}"))
}

#[test]
fn geometry_native_no_operation_runner_applies_normative_state()
-> Result<(), String> {
    let GeometryNativeNoOperationRunnerFixture {
        mut adapter,
        admission,
        geometry,
        ready,
    } = geometry_native_no_operation_runner_fixture(10, 106, 0x1_8000)?;
    let checkpoint = admission.checkpoint().clone();
    let expected = admission.expected_state().clone();
    if expected == checkpoint || expected.geometry() != geometry {
        return Err(String::from("v5 no-op normative replay did not advance"));
    }
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 no-op runner prepare: {error}"))?;
    let bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 no-op runner bind: {error}"))?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::Applied,
    );
    let completion = bound
        .execute(&mut runner)
        .map_err(|error| format!("v5 no-op runner execute: {error}"))?;
    if completion.state() != &expected
        || memory != expected.memory()
        || output != expected.io().output()
        || runner.calls != 1
        || runner.entry_addresses != [ready.entry_address()]
        || runner.mapping_ids != [ready.mapping().mapping_id()]
    {
        return Err(String::from("v5 no-op applied state drifted from replay"));
    }
    release_execution_geometry_native_executable(&mut adapter, ready)
        .map_err(|error| format!("v5 no-op runner release: {error}"))
}

#[test]
fn geometry_native_no_operation_preparation_rejects_memory_drift()
-> Result<(), String> {
    let (admission, _geometry) =
        geometry_native_no_operation_admission_fixture(10)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let first = memory
        .first_mut()
        .ok_or_else(|| String::from("v5 no-op checkpoint memory missing"))?;
    *first = first.saturating_add(1);
    let result = admission.prepare(NativeRegionBuffers::new(
        &mut memory,
        &input,
        &mut output,
    ));
    if matches!(
        result,
        Err(ExecutionGeometryNativeNoOperationPreparationError::Memory)
    ) {
        Ok(())
    } else {
        Err(String::from("v5 no-op memory drift was admitted"))
    }
}

#[test]
fn geometry_native_no_operation_runner_completion_drift_restores_checkpoint()
-> Result<(), String> {
    let GeometryNativeNoOperationRunnerFixture {
        mut adapter,
        admission,
        geometry: _geometry,
        ready,
    } = geometry_native_no_operation_runner_fixture(10, 109, 0x1_b000)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 no-op drift prepare: {error}"))?;
    let bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 no-op drift bind: {error}"))?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::CompletionDrift,
    );
    let Err(execution_error) = bound.execute(&mut runner) else {
        return Err(String::from("v5 no-op completion drift was admitted"));
    };
    let completion_drift = matches!(
        *execution_error,
        ExecutionGeometryNativeNoOperationExecutionError::Completion(
            ExecutionGeometryNativeNoOperationCompletionError::Invocation(
                NativeRegionInvocationError::AppliedMemory { address: 0, .. },
            ),
        )
    );
    if !completion_drift
        || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from("v5 no-op completion rollback drifted"));
    }
    release_execution_geometry_native_executable(&mut adapter, ready)
        .map_err(|error| format!("v5 no-op drift release: {error}"))
}

#[test]
fn geometry_native_no_operation_runner_failure_restores_checkpoint()
-> Result<(), String> {
    let GeometryNativeNoOperationRunnerFixture {
        mut adapter,
        admission,
        geometry: _geometry,
        ready,
    } = geometry_native_no_operation_runner_fixture(10, 107, 0x1_9000)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 no-op failed runner prepare: {error}"))?;
    let bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 no-op failed runner bind: {error}"))?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::FailureAfterMutation,
    );
    let Err(execution_error) = bound.execute(&mut runner) else {
        return Err(String::from("v5 no-op runner failure was ignored"));
    };
    if !matches!(
        *execution_error,
        ExecutionGeometryNativeNoOperationExecutionError::Runner(runner_error)
            if *runner_error == FakeNativeRunnerError::Call
    ) || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from("v5 no-op runner rollback drifted"));
    }
    release_execution_geometry_native_executable(&mut adapter, ready)
        .map_err(|error| format!("v5 no-op failed runner release: {error}"))
}

#[test]
fn geometry_native_no_operation_runner_guard_miss_preserves_checkpoint()
-> Result<(), String> {
    let GeometryNativeNoOperationRunnerFixture {
        mut adapter,
        admission,
        geometry: _geometry,
        ready,
    } = geometry_native_no_operation_runner_fixture(10, 108, 0x1_a000)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 no-op miss prepare: {error}"))?;
    let bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 no-op miss bind: {error}"))?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::GuardMiss,
    );
    let completion = bound
        .execute(&mut runner)
        .map_err(|error| format!("v5 no-op miss execute: {error}"))?;
    if completion.outcome() != NativeRegionInvocationOutcome::GuardMiss
        || completion.state() != &checkpoint
        || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from("v5 no-op guard miss changed checkpoint"));
    }
    release_execution_geometry_native_executable(&mut adapter, ready)
        .map_err(|error| format!("v5 no-op miss release: {error}"))
}

#[test]
fn geometry_native_binding_matches_checkpoint_owned_executable()
-> Result<(), String> {
    let (program, checkpoint, geometry) = derived_v5_handoff_fixture(10)?;
    let artifact = emit_direct_execution_geometry_initial_halt_coff(
        &program,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 bind emit: {error}"))?;
    let verified =
        verify_direct_execution_geometry_initial_halt(&artifact, &program)
            .map_err(|error| format!("v5 bind verify: {error}"))?;
    let admission = ExecutionGeometryNativeInitialHaltAdmission::new(
        program, checkpoint, verified,
    )
    .map_err(|error| format!("v5 bind admission: {error}"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(95)?,
        native_executable_address(0xd000)?,
    );
    let ready = load_execution_geometry_native_executable(
        &mut adapter,
        admission.load_image(),
    )
    .map_err(|error| format!("v5 bind load: {error}"))?;
    let mut memory = admission.checkpoint().memory().to_vec();
    let input = admission.checkpoint().io().input().to_vec();
    let mut output = admission.checkpoint().io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 bind prepare: {error}"))?;
    let mut bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 executable bind: {error}"))?;
    let artifact_identity_matches =
        bound.executable().key() == admission.artifact().key();
    let entry_matches = bound.entry_address() == ready.entry_address();
    if !artifact_identity_matches || !entry_matches {
        return Err(String::from("v5 bound executable identity drifted"));
    }
    bound.apply_expected_for_test();
    let completion = bound
        .complete(NativeRegionStatus::Applied.code())
        .map_err(|error| format!("v5 bound completion: {error}"))?;
    if completion.state().geometry() != geometry {
        return Err(String::from("v5 bound completion lost opaque geometry"));
    }
    release_execution_geometry_native_executable(&mut adapter, ready)
        .map_err(|error| format!("v5 bound release: {error}"))
}

#[test]
fn geometry_native_binding_rejects_different_geometry_executable()
-> Result<(), String> {
    let (n10, n10_checkpoint, _n10_geometry) = derived_v5_handoff_fixture(10)?;
    let (n11, _n11_checkpoint, _n11_geometry) = derived_v5_handoff_fixture(11)?;
    let n10_artifact = emit_direct_execution_geometry_initial_halt_coff(
        &n10,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 bind N10 emit: {error}"))?;
    let n10_verified =
        verify_direct_execution_geometry_initial_halt(&n10_artifact, &n10)
            .map_err(|error| format!("v5 bind N10 verify: {error}"))?;
    let admission = ExecutionGeometryNativeInitialHaltAdmission::new(
        n10,
        n10_checkpoint.clone(),
        n10_verified,
    )
    .map_err(|error| format!("v5 bind N10 admission: {error}"))?;
    let n11_artifact = emit_direct_execution_geometry_initial_halt_coff(
        &n11,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 bind N11 emit: {error}"))?;
    let n11_verified =
        verify_direct_execution_geometry_initial_halt(&n11_artifact, &n11)
            .map_err(|error| format!("v5 bind N11 verify: {error}"))?;
    let n11_image =
        VerifiedExecutionGeometryLoadImage::from_initial_halt(&n11_verified)
            .map_err(|error| format!("v5 bind N11 image: {error}"))?;
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(96)?,
        native_executable_address(0xe000)?,
    );
    let n11_ready =
        load_execution_geometry_native_executable(&mut adapter, &n11_image)
            .map_err(|error| format!("v5 bind N11 load: {error}"))?;
    let mut memory = n10_checkpoint.memory().to_vec();
    let input = n10_checkpoint.io().input().to_vec();
    let mut output = n10_checkpoint.io().output().to_vec();
    let expected_memory = memory.clone();
    let expected_output = output.clone();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 bind mismatch prepare: {error}"))?;
    if !matches!(
        prepared.bind_executable(&n11_ready),
        Err(ExecutionGeometryNativeInitialHaltBindingError::ExecutableIdentity)
    ) || memory != expected_memory
        || output != expected_output
    {
        return Err(String::from(
            "v5 executable drift did not fail atomically",
        ));
    }
    release_execution_geometry_native_executable(&mut adapter, n11_ready)
        .map_err(|error| format!("v5 bind N11 release: {error}"))
}

#[test]
fn geometry_native_runner_applies_bound_halt() -> Result<(), String> {
    let GeometryNativeRunnerFixture {
        mut adapter,
        admission,
        geometry,
        ready,
    } = geometry_native_runner_fixture(10, 97, 0xf000)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 runner prepare: {error}"))?;
    let bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 runner bind: {error}"))?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::Applied,
    );
    let completion = bound
        .execute(&mut runner)
        .map_err(|error| format!("v5 runner execute: {error}"))?;
    let evidence_matches = runner.calls == 1
        && runner.entry_addresses == [ready.entry_address()]
        && runner.mapping_ids == [ready.mapping().mapping_id()]
        && runner.state_pointers_non_null == [true];
    let state_matches = completion.state().geometry() == geometry
        && completion.state().memory() == checkpoint.memory()
        && completion.state().io().termination()
            == Some(Termination::HaltInstruction)
        && matches!(
            completion.outcome(),
            NativeRegionInvocationOutcome::Applied(observation)
                if observation.termination
                    == Some(Termination::HaltInstruction)
        );
    if !evidence_matches || !state_matches || memory != checkpoint.memory() {
        return Err(String::from("v5 runner applied halt evidence drifted"));
    }
    release_execution_geometry_native_executable(&mut adapter, ready)
        .map_err(|error| format!("v5 runner applied release: {error}"))
}

#[test]
fn geometry_native_runner_completion_drift_restores_buffers()
-> Result<(), String> {
    let GeometryNativeRunnerFixture {
        mut adapter,
        admission,
        geometry: _geometry,
        ready,
    } = geometry_native_runner_fixture(10, 98, 0x1_0000)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 drift runner prepare: {error}"))?;
    let bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 drift runner bind: {error}"))?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::CompletionDrift,
    );
    let Err(execution_error) = bound.execute(&mut runner) else {
        return Err(String::from("v5 completion drift was admitted"));
    };
    let completion_drift = matches!(
        *execution_error,
        ExecutionGeometryNativeInitialHaltExecutionError::Completion(
            ExecutionGeometryNativeInitialHaltCompletionError::Invocation(
                NativeRegionInvocationError::AppliedMemory { address: 0, .. },
            ),
        )
    );
    if !completion_drift
        || runner.calls != 1
        || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from("v5 completion drift rollback failed"));
    }
    release_execution_geometry_native_executable(&mut adapter, ready).map_err(
        |release_error| format!("v5 drift runner release: {release_error}"),
    )
}

#[test]
fn geometry_native_runner_failure_restores_buffers() -> Result<(), String> {
    let GeometryNativeRunnerFixture {
        mut adapter,
        admission,
        geometry: _geometry,
        ready,
    } = geometry_native_runner_fixture(10, 99, 0x1_1000)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 failed runner prepare: {error}"))?;
    let bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 failed runner bind: {error}"))?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::FailureAfterMutation,
    );
    let Err(execution_error) = bound.execute(&mut runner) else {
        return Err(String::from("v5 runner failure was ignored"));
    };
    let runner_failed = matches!(
        *execution_error,
        ExecutionGeometryNativeInitialHaltExecutionError::Runner(runner_error)
            if *runner_error == FakeNativeRunnerError::Call
    );
    if !runner_failed
        || runner.calls != 1
        || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from("v5 runner failure rollback drifted"));
    }
    release_execution_geometry_native_executable(&mut adapter, ready).map_err(
        |release_error| format!("v5 failed runner release: {release_error}"),
    )
}

#[test]
fn geometry_native_runner_guard_miss_preserves_state() -> Result<(), String> {
    let GeometryNativeRunnerFixture {
        mut adapter,
        admission,
        geometry: _geometry,
        ready,
    } = geometry_native_runner_fixture(10, 100, 0x1_2000)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 miss runner prepare: {error}"))?;
    let bound = prepared
        .bind_executable(&ready)
        .map_err(|error| format!("v5 miss runner bind: {error}"))?;
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::GuardMiss,
    );
    let completion = bound
        .execute(&mut runner)
        .map_err(|error| format!("v5 miss runner execute: {error}"))?;
    if completion.outcome() != NativeRegionInvocationOutcome::GuardMiss
        || completion.state() != &checkpoint
        || runner.calls != 1
        || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from("v5 runner guard miss changed checkpoint"));
    }
    release_execution_geometry_native_executable(&mut adapter, ready)
        .map_err(|error| format!("v5 miss runner release: {error}"))
}

#[test]
fn geometry_native_initial_jump_transaction_applies_and_releases()
-> Result<(), String> {
    let (admission, geometry) =
        geometry_native_initial_jump_data_admission_fixture(10)?;
    let checkpoint = admission.checkpoint().clone();
    let expected = admission.expected_state().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(110)?,
        native_executable_address(0x1_c000)?,
    );
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::Applied,
    );
    let completion = admission
        .execute_transactionally(
            &mut adapter,
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| format!("v5 initial jump transaction: {error}"))?;
    if completion.state() != &expected
        || completion.state().geometry() != geometry
        || memory != expected.memory()
        || output != expected.io().output()
        || adapter.operations
            != [
                FakeNativeAdapterOperation::Allocate,
                FakeNativeAdapterOperation::Copy,
                FakeNativeAdapterOperation::Protect,
                FakeNativeAdapterOperation::Synchronize,
                FakeNativeAdapterOperation::Release,
            ]
    {
        Err(String::from("v5 initial jump transaction evidence drifted"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_initial_jump_retains_committed_release_retry()
-> Result<(), String> {
    let (admission, _geometry) =
        geometry_native_initial_jump_data_admission_fixture(10)?;
    let checkpoint = admission.checkpoint().clone();
    let expected = admission.expected_state().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(111)?,
        native_executable_address(0x1_d000)?,
    )
    .with_release_failures(1);
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::Applied,
    );
    let Err(failure) = admission.execute_transactionally(
        &mut adapter,
        &mut runner,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    ) else {
        return Err(String::from(
            "v5 initial jump release failure was ignored",
        ));
    };
    let InitialJumpTransactionFailure::Release {
        completion,
        release_failure,
    } = *failure
    else {
        return Err(String::from("v5 initial jump cleanup ownership was lost"));
    };
    if completion.state() != &expected
        || release_failure.executable().key() != admission.artifact().key()
        || memory != expected.memory()
        || output != expected.io().output()
    {
        return Err(String::from("v5 initial jump committed cleanup drifted"));
    }
    release_failure.retry(&mut adapter).map_err(|error| {
        format!("v5 initial jump committed cleanup retry: {error}")
    })
}

#[test]
fn geometry_native_rotate_transaction_applies_and_releases()
-> Result<(), String> {
    let (admission, geometry) = geometry_native_rotate_admission_fixture(10)?;
    let checkpoint = admission.checkpoint().clone();
    let expected = admission.expected_state().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(110)?,
        native_executable_address(0x1_c000)?,
    );
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::Applied,
    );
    let completion = admission
        .execute_transactionally(
            &mut adapter,
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| format!("v5 rotate transaction: {error}"))?;
    if completion.state() != &expected
        || completion.state().geometry() != geometry
        || memory != expected.memory()
        || output != expected.io().output()
        || adapter.operations
            != [
                FakeNativeAdapterOperation::Allocate,
                FakeNativeAdapterOperation::Copy,
                FakeNativeAdapterOperation::Protect,
                FakeNativeAdapterOperation::Synchronize,
                FakeNativeAdapterOperation::Release,
            ]
    {
        Err(String::from("v5 rotate transaction evidence drifted"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_rotate_transaction_retains_committed_release_retry()
-> Result<(), String> {
    let (admission, _geometry) = geometry_native_rotate_admission_fixture(10)?;
    let checkpoint = admission.checkpoint().clone();
    let expected = admission.expected_state().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(111)?,
        native_executable_address(0x1_d000)?,
    )
    .with_release_failures(1);
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::Applied,
    );
    let Err(failure) = admission.execute_transactionally(
        &mut adapter,
        &mut runner,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    ) else {
        return Err(String::from("v5 rotate release failure was ignored"));
    };
    let ExecutionGeometryNativeRotateTransactionFailure::Release {
        completion,
        release_failure,
    } = *failure
    else {
        return Err(String::from("v5 rotate cleanup ownership was lost"));
    };
    if completion.state() != &expected
        || release_failure.executable().key() != admission.artifact().key()
        || memory != expected.memory()
        || output != expected.io().output()
    {
        return Err(String::from("v5 rotate committed cleanup drifted"));
    }
    release_failure
        .retry(&mut adapter)
        .map_err(|error| format!("v5 rotate committed cleanup retry: {error}"))
}

#[test]
fn geometry_native_no_operation_transaction_applies_and_releases()
-> Result<(), String> {
    let (admission, geometry) =
        geometry_native_no_operation_admission_fixture(10)?;
    let checkpoint = admission.checkpoint().clone();
    let expected = admission.expected_state().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(110)?,
        native_executable_address(0x1_c000)?,
    );
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::Applied,
    );
    let completion = admission
        .execute_transactionally(
            &mut adapter,
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| format!("v5 no-op transaction: {error}"))?;
    if completion.state() != &expected
        || completion.state().geometry() != geometry
        || memory != expected.memory()
        || output != expected.io().output()
        || adapter.operations
            != [
                FakeNativeAdapterOperation::Allocate,
                FakeNativeAdapterOperation::Copy,
                FakeNativeAdapterOperation::Protect,
                FakeNativeAdapterOperation::Synchronize,
                FakeNativeAdapterOperation::Release,
            ]
    {
        Err(String::from("v5 no-op transaction evidence drifted"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_no_operation_transaction_retains_committed_release_retry()
-> Result<(), String> {
    let (admission, _geometry) =
        geometry_native_no_operation_admission_fixture(10)?;
    let checkpoint = admission.checkpoint().clone();
    let expected = admission.expected_state().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(111)?,
        native_executable_address(0x1_d000)?,
    )
    .with_release_failures(1);
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::Applied,
    );
    let Err(failure) = admission.execute_transactionally(
        &mut adapter,
        &mut runner,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    ) else {
        return Err(String::from("v5 no-op release failure was ignored"));
    };
    let ExecutionGeometryNativeNoOperationTransactionFailure::Release {
        completion,
        release_failure,
    } = *failure
    else {
        return Err(String::from("v5 no-op cleanup ownership was lost"));
    };
    if completion.state() != &expected
        || release_failure.executable().key() != admission.artifact().key()
        || memory != expected.memory()
        || output != expected.io().output()
    {
        return Err(String::from("v5 no-op committed cleanup drifted"));
    }
    release_failure
        .retry(&mut adapter)
        .map_err(|error| format!("v5 no-op committed cleanup retry: {error}"))
}

#[test]
fn geometry_native_transaction_applies_and_releases() -> Result<(), String> {
    let (admission, geometry) = geometry_native_admission_fixture(10)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(101)?,
        native_executable_address(0x1_3000)?,
    );
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::Applied,
    );
    let completion = admission
        .execute_transactionally(
            &mut adapter,
            &mut runner,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        )
        .map_err(|error| format!("v5 transaction execute: {error}"))?;
    if completion.state().geometry() != geometry
        || completion.state().io().termination()
            != Some(Termination::HaltInstruction)
        || runner.calls != 1
        || memory != checkpoint.memory()
        || output != checkpoint.io().output()
        || adapter.operations
            != [
                FakeNativeAdapterOperation::Allocate,
                FakeNativeAdapterOperation::Copy,
                FakeNativeAdapterOperation::Protect,
                FakeNativeAdapterOperation::Synchronize,
                FakeNativeAdapterOperation::Release,
            ]
    {
        Err(String::from("v5 transaction completion evidence drifted"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_transaction_load_failure_skips_runner() -> Result<(), String>
{
    let (admission, _geometry) = geometry_native_admission_fixture(10)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(102)?,
        native_executable_address(0x1_4000)?,
    )
    .with_failure(FakeNativeAdapterOperation::Copy);
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::Applied,
    );
    let Err(failure) = admission.execute_transactionally(
        &mut adapter,
        &mut runner,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    ) else {
        return Err(String::from("v5 transaction load failure ignored"));
    };
    let load_failed = matches!(
        *failure,
        ExecutionGeometryNativeInitialHaltTransactionFailure::Load(error)
            if error.phase() == NativeExecutableLoadPhase::Copy
    );
    if !load_failed
        || runner.calls != 0
        || memory != checkpoint.memory()
        || output != checkpoint.io().output()
        || adapter.operations
            != [
                FakeNativeAdapterOperation::Allocate,
                FakeNativeAdapterOperation::Copy,
                FakeNativeAdapterOperation::Release,
            ]
    {
        Err(String::from("v5 transaction load rollback drifted"))
    } else {
        Ok(())
    }
}

#[test]
fn geometry_native_transaction_retains_runner_cleanup_retry()
-> Result<(), String> {
    let (admission, _geometry) = geometry_native_admission_fixture(10)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(103)?,
        native_executable_address(0x1_5000)?,
    )
    .with_release_failures(1);
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::FailureAfterMutation,
    );
    let Err(failure) = admission.execute_transactionally(
        &mut adapter,
        &mut runner,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    ) else {
        return Err(String::from("v5 transaction runner failure ignored"));
    };
    let ExecutionGeometryNativeInitialHaltTransactionFailure::Execution {
        error: execution_error,
        release_failure: Some(release_failure),
    } = *failure
    else {
        return Err(String::from("v5 runner cleanup ownership was lost"));
    };
    if !matches!(
        *execution_error,
        ExecutionGeometryNativeInitialHaltExecutionError::Runner(runner_error)
            if *runner_error == FakeNativeRunnerError::Call
    ) || release_failure.executable().key() != admission.artifact().key()
        || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from("v5 runner failure cleanup evidence drifted"));
    }
    release_failure
        .retry(&mut adapter)
        .map_err(|error| format!("v5 runner cleanup retry: {error}"))
}

#[test]
fn geometry_native_transaction_retains_committed_release_retry()
-> Result<(), String> {
    let (admission, geometry) = geometry_native_admission_fixture(10)?;
    let checkpoint = admission.checkpoint().clone();
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let mut adapter = FakeNativeExecutableAdapter::new(
        native_executable_mapping_id(104)?,
        native_executable_address(0x1_6000)?,
    )
    .with_release_failures(1);
    let mut runner = FakeExecutionGeometryNativeRunner::new(
        FakeNativeRunnerBehavior::Applied,
    );
    let Err(failure) = admission.execute_transactionally(
        &mut adapter,
        &mut runner,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    ) else {
        return Err(String::from("v5 transaction release failure ignored"));
    };
    let ExecutionGeometryNativeInitialHaltTransactionFailure::Release {
        completion,
        release_failure,
    } = *failure
    else {
        return Err(String::from("v5 committed cleanup ownership was lost"));
    };
    if completion.state().geometry() != geometry
        || completion.state().io().termination()
            != Some(Termination::HaltInstruction)
        || release_failure.executable().key() != admission.artifact().key()
        || memory != checkpoint.memory()
        || output != checkpoint.io().output()
    {
        return Err(String::from("v5 committed release evidence drifted"));
    }
    release_failure
        .retry(&mut adapter)
        .map_err(|error| format!("v5 committed release retry: {error}"))
}

#[test]
fn execution_geometry_native_preparation_admits_exact_halt_result()
-> Result<(), String> {
    let (program, checkpoint, geometry) = derived_v5_handoff_fixture(10)?;
    let artifact = emit_direct_execution_geometry_initial_halt_coff(
        &program,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 prepare emit: {error}"))?;
    let verified =
        verify_direct_execution_geometry_initial_halt(&artifact, &program)
            .map_err(|error| format!("v5 prepare verify: {error}"))?;
    let admission = ExecutionGeometryNativeInitialHaltAdmission::new(
        program, checkpoint, verified,
    )
    .map_err(|error| format!("v5 prepare admission: {error}"))?;
    let mut memory = admission.checkpoint().memory().to_vec();
    let input = admission.checkpoint().io().input().to_vec();
    let mut output = admission.checkpoint().io().output().to_vec();
    let mut prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 ABI preparation: {error}"))?;
    prepared.apply_expected_for_test();
    let completion = prepared
        .complete(NativeRegionStatus::Applied.code())
        .map_err(|error| format!("v5 ABI completion: {error}"))?;
    if completion.state().geometry() == geometry
        && completion.state().memory() == memory
        && completion.state().io().input() == input
        && completion.state().io().output() == output
        && completion.state().io().termination()
            == Some(Termination::HaltInstruction)
        && matches!(
            completion.outcome(),
            NativeRegionInvocationOutcome::Applied(observation)
                if observation.termination
                    == Some(Termination::HaltInstruction)
        )
    {
        Ok(())
    } else {
        Err(String::from("v5 prepared halt lost checkpoint authority"))
    }
}

#[test]
fn execution_geometry_native_preparation_guard_miss_preserves_checkpoint()
-> Result<(), String> {
    let (program, checkpoint, _geometry) = derived_v5_handoff_fixture(10)?;
    let artifact = emit_direct_execution_geometry_initial_halt_coff(
        &program,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 miss emit: {error}"))?;
    let verified =
        verify_direct_execution_geometry_initial_halt(&artifact, &program)
            .map_err(|error| format!("v5 miss verify: {error}"))?;
    let admission = ExecutionGeometryNativeInitialHaltAdmission::new(
        program,
        checkpoint.clone(),
        verified,
    )
    .map_err(|error| format!("v5 miss admission: {error}"))?;
    let mut memory = checkpoint.memory().to_vec();
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let prepared = admission
        .prepare(NativeRegionBuffers::new(&mut memory, &input, &mut output))
        .map_err(|error| format!("v5 miss prepare: {error}"))?;
    let completion = prepared
        .complete(NativeRegionStatus::GuardMiss.code())
        .map_err(|error| format!("v5 miss completion: {error}"))?;
    if completion.outcome() == NativeRegionInvocationOutcome::GuardMiss
        && completion.state() == &checkpoint
        && memory == checkpoint.memory()
        && output == checkpoint.io().output()
    {
        Ok(())
    } else {
        Err(String::from("v5 guard miss changed admitted checkpoint"))
    }
}

#[test]
fn execution_geometry_native_preparation_rejects_buffer_drift()
-> Result<(), String> {
    let (program, checkpoint, _geometry) = derived_v5_handoff_fixture(10)?;
    let artifact = emit_direct_execution_geometry_initial_halt_coff(
        &program,
        direct_execution_geometry_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| format!("v5 buffer emit: {error}"))?;
    let verified =
        verify_direct_execution_geometry_initial_halt(&artifact, &program)
            .map_err(|error| format!("v5 buffer verify: {error}"))?;
    let admission = ExecutionGeometryNativeInitialHaltAdmission::new(
        program,
        checkpoint.clone(),
        verified,
    )
    .map_err(|error| format!("v5 buffer admission: {error}"))?;
    let input = checkpoint.io().input().to_vec();
    let mut output = checkpoint.io().output().to_vec();
    let mut memory_drift = checkpoint.memory().to_vec();
    let first = memory_drift.first_mut().ok_or_else(|| {
        String::from("v5 checkpoint memory unexpectedly empty")
    })?;
    *first ^= 1;
    if !matches!(
        admission.prepare(NativeRegionBuffers::new(
            &mut memory_drift,
            &input,
            &mut output,
        )),
        Err(ExecutionGeometryNativeInitialHaltPreparationError::Memory)
    ) {
        return Err(String::from("v5 preparation accepted memory drift"));
    }
    let mut input_drift_memory = checkpoint.memory().to_vec();
    let mut input_drift = input;
    input_drift.push(0x55);
    if !matches!(
        admission.prepare(NativeRegionBuffers::new(
            &mut input_drift_memory,
            &input_drift,
            &mut output,
        )),
        Err(ExecutionGeometryNativeInitialHaltPreparationError::Input)
    ) {
        return Err(String::from("v5 preparation accepted input drift"));
    }
    Ok(())
}

#[test]
fn explicit_geometry_handoff_preserves_opaque_checkpoint_geometry()
-> Result<(), String> {
    let (program, checkpoint, geometry) = derived_v5_handoff_fixture(10)?;
    let expected = program.clone();
    let completion =
        ExecutionGeometryInterpreterHandoff::new(program, checkpoint)
            .map_err(|error| error.to_string())?
            .execute()
            .map_err(|error| error.to_string())?;
    if completion.outcome()
        == StepOutcome::Terminated(Termination::HaltInstruction)
        && completion.program() == &expected
        && completion.state().geometry() == geometry
        && completion.state().profile() == current_profile()
    {
        Ok(())
    } else {
        Err(String::from("v5 handoff lost derived geometry authority"))
    }
}

#[test]
fn explicit_geometry_handoff_rejects_checkpoint_geometry_drift()
-> Result<(), String> {
    let (program, _n10, _geometry) = derived_v5_handoff_fixture(10)?;
    let (_n11_program, n11, _n11_geometry) = derived_v5_handoff_fixture(11)?;
    if ExecutionGeometryInterpreterHandoff::new(program, n11)
        == Err(ExecutionGeometryHandoffAdmissionError::CheckpointGeometry)
    {
        Ok(())
    } else {
        Err(String::from(
            "v5 handoff admitted different opaque geometry",
        ))
    }
}

#[test]
fn explicit_geometry_handoff_revalidates_untrusted_effects_normatively()
-> Result<(), String> {
    let verified =
        verify_initial_halt_profile_width(current_profile(), b"QP", 10)
            .map_err(|error| format!("forged v5 verification: {error}"))?;
    let machine = ProfileMachine::from_verified_source(&verified, Vec::new())
        .map_err(|error| format!("forged v5 machine: {error}"))?;
    let checkpoint = machine.snapshot_state();
    let mut replay = ProfileMachine::from_snapshot(checkpoint.clone());
    let mut trace_slot = None;
    let _outcome = replay
        .step_traced(&mut |trace| trace_slot = Some(*trace))
        .map_err(|error| format!("forged v5 trace: {error}"))?;
    let mut trace =
        trace_slot.ok_or_else(|| String::from("forged trace missing"))?;
    trace.output = Some(0x55);
    let forged =
        ExecutionGeometryRegionEffectProgram::from_profile_step_trace(&trace)
            .map_err(|error| format!("forged v5 projection: {error:?}"))?;
    let replay_result =
        ExecutionGeometryInterpreterHandoff::new(forged, checkpoint.clone())
            .map_err(|error| error.to_string())?
            .execute();
    let Err(failure) = replay_result else {
        return Err(String::from("forged v5 effect passed normative replay"));
    };
    if failure.cause()
        == ExecutionGeometryHandoffExecutionCause::ProgramMismatch
        && failure.state() == &checkpoint
    {
        Ok(())
    } else {
        Err(String::from("v5 replay did not fail closed to entry state"))
    }
}

fn derived_v5_input_halt_sequence_fixture(
    word_trits: u8,
    input: Vec<u8>,
) -> Result<DerivedV5SequenceFixture, String> {
    let verified = verify_input_then_halt_profile_width(
        current_profile(),
        b"uP",
        word_trits,
    )
    .map_err(|error| format!("v5 continuation verification: {error}"))?;
    let mut machine = ProfileMachine::from_verified_source(&verified, input)
        .map_err(|error| format!("v5 continuation machine: {error}"))?;
    let mut programs = Vec::new();
    let mut states = vec![machine.snapshot_state()];
    let mut traces = Vec::new();
    for _index in 0usize..2usize {
        let mut trace_slot = None;
        let _outcome = machine
            .step_traced(&mut |trace| trace_slot = Some(*trace))
            .map_err(|error| format!("v5 continuation trace: {error}"))?;
        let trace = trace_slot
            .ok_or_else(|| String::from("v5 continuation trace missing"))?;
        let program =
            ExecutionGeometryRegionEffectProgram::from_profile_step_trace(
                &trace,
            )
            .map_err(|error| {
                format!("v5 continuation projection: {error:?}")
            })?;
        programs.push(program);
        states.push(machine.snapshot_state());
        traces.push(trace);
    }
    Ok(DerivedV5SequenceFixture {
        geometry: verified.geometry(),
        programs,
        states,
        traces,
    })
}

fn derived_v5_fixture_program(
    fixture: &DerivedV5SequenceFixture,
    index: usize,
) -> Result<&ExecutionGeometryRegionEffectProgram, String> {
    fixture
        .programs
        .get(index)
        .ok_or_else(|| format!("v5 fixture program {index} missing"))
}

fn derived_v5_fixture_state(
    fixture: &DerivedV5SequenceFixture,
    index: usize,
) -> Result<&ProfileMachineState, String> {
    fixture
        .states
        .get(index)
        .ok_or_else(|| format!("v5 fixture state {index} missing"))
}

fn derived_v5_fixture_trace(
    fixture: &DerivedV5SequenceFixture,
    index: usize,
) -> Result<ProfileStepTrace, String> {
    fixture
        .traces
        .get(index)
        .copied()
        .ok_or_else(|| format!("v5 fixture trace {index} missing"))
}

fn admit_v5_continuation_fixture(
    fixture: &DerivedV5SequenceFixture,
) -> Result<ExecutionGeometryInterpreterContinuation, String> {
    let initial = derived_v5_fixture_state(fixture, 0)?;
    let final_program = derived_v5_fixture_program(fixture, 1)?;
    let continuation = ExecutionGeometryInterpreterContinuation::new(
        fixture.programs.clone(),
        initial.clone(),
    )
    .map_err(|error| error.to_string())?;
    let expected_exit = final_program
        .exit_observation()
        .ok_or_else(|| String::from("v5 continuation exit missing"))?;
    let expected_outcome = RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 2,
    };
    if continuation.completed_steps() == 0
        && continuation.remaining_steps() == 2
        && continuation.expected_exit() == expected_exit
        && continuation.expected_outcome() == expected_outcome
        && continuation.state().geometry() == fixture.geometry
    {
        Ok(continuation)
    } else {
        Err(String::from("v5 continuation admission drifted"))
    }
}

fn suspend_v5_continuation_fixture(
    continuation: ExecutionGeometryInterpreterContinuation,
    fixture: &DerivedV5SequenceFixture,
) -> Result<ExecutionGeometryInterpreterContinuation, String> {
    let zero_outcome = continuation
        .clone()
        .execute_with_budget(0)
        .map_err(|error| error.to_string())?;
    let ExecutionGeometryContinuationBudgetOutcome::Suspended(zero_suspension) =
        zero_outcome
    else {
        return Err(String::from("zero v5 budget completed work"));
    };
    if zero_suspension != continuation {
        return Err(String::from("zero v5 budget changed continuation"));
    }
    let slice = continuation
        .execute_with_budget(1)
        .map_err(|error| error.to_string())?;
    let ExecutionGeometryContinuationBudgetOutcome::Suspended(suspended) =
        slice
    else {
        return Err(String::from("one-step v5 budget completed sequence"));
    };
    let expected_state = derived_v5_fixture_state(fixture, 1)?;
    let expected_suffix = fixture
        .programs
        .get(1..)
        .ok_or_else(|| String::from("v5 fixture suffix missing"))?;
    if suspended.completed_steps() == 1
        && suspended.resume_index() == 1
        && suspended.remaining_steps() == 1
        && suspended.remaining_programs() == expected_suffix
        && suspended.state() == expected_state
        && suspended.state().geometry() == fixture.geometry
    {
        Ok(suspended)
    } else {
        Err(String::from("v5 suspension lost exact suffix state"))
    }
}

#[test]
fn explicit_geometry_continuation_rejects_mixed_opaque_geometry()
-> Result<(), String> {
    let n10 = derived_v5_input_halt_sequence_fixture(10, vec![0xa5])?;
    let n11 = derived_v5_input_halt_sequence_fixture(11, vec![0xa5])?;
    let first = derived_v5_fixture_program(&n10, 0)?.clone();
    let second = derived_v5_fixture_program(&n11, 1)?.clone();
    let initial = derived_v5_fixture_state(&n10, 0)?.clone();
    let observed = ExecutionGeometryInterpreterContinuation::new(
        vec![first, second],
        initial,
    );
    if observed
        == Err(ExecutionGeometryContinuationAdmissionError::GeometryDrift {
            index: 1,
        })
    {
        Ok(())
    } else {
        Err(String::from("v5 continuation admitted mixed geometry"))
    }
}

#[test]
fn explicit_geometry_continuation_suspends_and_resumes_opaque_geometry()
-> Result<(), String> {
    for input in [vec![0xa5], Vec::new()] {
        let fixture = derived_v5_input_halt_sequence_fixture(10, input)?;
        let continuation = admit_v5_continuation_fixture(&fixture)?;
        let suspended =
            suspend_v5_continuation_fixture(continuation, &fixture)?;
        let completion =
            suspended.execute().map_err(|error| error.to_string())?;
        let expected_state = derived_v5_fixture_state(&fixture, 2)?;
        let expected_outcome = RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 2,
        };
        if completion.outcome() != expected_outcome
            || completion.programs() != fixture.programs
            || completion.state() != expected_state
            || completion.state().geometry() != fixture.geometry
        {
            return Err(String::from("v5 continuation resume drifted"));
        }
    }
    Ok(())
}

#[test]
fn explicit_geometry_continuation_stops_at_forged_later_step()
-> Result<(), String> {
    let fixture = derived_v5_input_halt_sequence_fixture(10, vec![0xa5])?;
    let mut forged_trace = derived_v5_fixture_trace(&fixture, 1)?;
    forged_trace.output = Some(0x55);
    let forged = ExecutionGeometryRegionEffectProgram::from_profile_step_trace(
        &forged_trace,
    )
    .map_err(|error| format!("forged continuation projection: {error:?}"))?;
    let first = derived_v5_fixture_program(&fixture, 0)?.clone();
    let initial = derived_v5_fixture_state(&fixture, 0)?.clone();
    let continuation = ExecutionGeometryInterpreterContinuation::new(
        vec![first, forged],
        initial,
    )
    .map_err(|error| error.to_string())?;
    let Err(failure) = continuation.execute() else {
        return Err(String::from("forged later v5 step replayed"));
    };
    let expected_state = derived_v5_fixture_state(&fixture, 1)?;
    if failure.index() == 1
        && failure.cause()
            == ExecutionGeometryContinuationExecutionCause::Step(
                ExecutionGeometryHandoffExecutionCause::ProgramMismatch,
            )
        && failure.state() == expected_state
        && failure.programs().len() == 2
    {
        Ok(())
    } else {
        Err(String::from("v5 later-step failure lost admitted prefix"))
    }
}

#[test]
fn native_interpreter_handoff_rejects_derived_checkpoint_geometry()
-> Result<(), String> {
    let profile = target_profile(FIXTURE_PROFILE_ID)
        .ok_or_else(|| String::from("initial-halt profile missing"))?;
    let mut program = direct_initial_halt_program();
    program.profile_fingerprint = String::from(profile.fingerprint());
    program.profile_requirement =
        TargetProfileRequirement::from_descriptor(profile);
    let programs = [program];
    let plan = select_verified_direct_sequence(
        &programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let continuation = NativeInterpreterContinuation::from_outcome(
        &plan,
        NativeSequenceExecutionOutcome::GuardMiss {
            index: 0,
            observation: plan.entry(),
        },
    )
    .map_err(|error| error.to_string())?
    .ok_or_else(|| String::from("initial-halt guard miss lost continuation"))?;
    let verified = verify_minimum_initial_halt_profile_width(profile, b"QP")
        .map_err(|error| format!("derived handoff geometry: {error}"))?;
    let geometry = verified.geometry();
    let memory_len = usize::try_from(geometry.memory_words())
        .map_err(|error| format!("derived handoff memory length: {error}"))?;
    let checkpoint = ProfileMachineState::new_with_geometry(
        geometry,
        vec![0u32; memory_len],
        plan.entry().registers,
        ProfileMachineIoState::new(Vec::new(), 0, Vec::new(), None)
            .map_err(|error| error.to_string())?,
    )
    .map_err(|error| format!("derived handoff state: {error}"))?;
    if NativeInterpreterHandoff::from_checkpoint(continuation, checkpoint)
        == Err(NativeInterpreterHandoffAdmissionError::CheckpointGeometry)
    {
        Ok(())
    } else {
        Err(String::from("derived checkpoint geometry was admitted"))
    }
}

#[test]
fn native_interpreter_handoff_rejects_checkpoint_drift() -> Result<(), String> {
    let NativeHandoffFixture { continuation, .. } =
        native_handoff_fixture(HostIsa::X86_64, vec![
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::GuardMiss,
        ])?;
    let historical = ProfileMachine::from_source(
        historical_profile(),
        b"(=%`qL",
        Vec::new(),
    )
    .map_err(|error| format!("historical handoff state: {error}"))?
    .snapshot_state();
    let profile_error = NativeInterpreterHandoff::from_checkpoint(
        continuation.clone(),
        historical,
    );
    let mut machine =
        ProfileMachine::from_snapshot(direct_normative_sequence_state()?);
    run_one_profile_step(&mut machine, "observation drift prefix")?;
    let state = machine.snapshot_state();
    let io = ProfileMachineIoState::new(
        state.io().input().to_vec(),
        state.io().input_consumed(),
        vec![0x55],
        state.io().termination(),
    )
    .map_err(|error| error.to_string())?;
    let drifted = ProfileMachineState::new(
        current_profile(),
        state.memory().to_vec(),
        state.registers(),
        io,
    )
    .map_err(|error| error.to_string())?;
    let observation_error =
        NativeInterpreterHandoff::from_checkpoint(continuation, drifted);
    if profile_error
        == Err(NativeInterpreterHandoffAdmissionError::CheckpointProfile)
        && observation_error
            == Err(
                NativeInterpreterHandoffAdmissionError::CheckpointObservation,
            )
    {
        Ok(())
    } else {
        Err(String::from("checkpoint drift was admitted"))
    }
}

#[test]
fn native_interpreter_handoff_rejects_initial_live_in_drift()
-> Result<(), String> {
    let NativeHandoffFixture {
        continuation,
        input,
        mut memory,
        output,
        ..
    } = native_handoff_fixture(HostIsa::AArch64, vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let live_in = continuation
        .remaining_programs()
        .first()
        .and_then(|program| program.memory_live_ins.first())
        .copied()
        .ok_or_else(|| String::from("handoff live-in fixture missing"))?;
    let index = usize::try_from(live_in.address)
        .map_err(|error| format!("handoff live-in index: {error}"))?;
    let observed = live_in.value.saturating_add(1);
    *memory
        .get_mut(index)
        .ok_or_else(|| String::from("handoff live-in address missing"))? =
        observed;
    let result = NativeInterpreterHandoff::from_buffers(
        continuation,
        memory,
        input,
        &output,
    );
    if result
        == Err(NativeInterpreterHandoffAdmissionError::LiveIn {
            address: live_in.address,
            expected: live_in.value,
            observed,
        })
    {
        Ok(())
    } else {
        Err(String::from("initial handoff live-in drift was admitted"))
    }
}

#[test]
fn native_interpreter_handoff_rolls_back_late_live_in_drift()
-> Result<(), String> {
    let NativeHandoffFixture {
        continuation,
        input,
        mut memory,
        output,
        plan,
    } = native_handoff_fixture(HostIsa::X86_64, vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let live_in = distinct_second_live_in(&plan)?;
    let second = plan
        .programs()
        .get(1)
        .ok_or_else(|| String::from("late handoff second program missing"))?;
    let index = usize::try_from(live_in.address)
        .map_err(|error| format!("late handoff live-in index: {error}"))?;
    let observed = live_in.value.saturating_sub(1);
    *memory
        .get_mut(index)
        .ok_or_else(|| String::from("late handoff memory address missing"))? =
        observed;
    let handoff = NativeInterpreterHandoff::from_buffers(
        continuation,
        memory,
        input,
        &output,
    )
    .map_err(|error| error.to_string())?;
    let Err(failure) = handoff.execute() else {
        return Err(String::from("late handoff live-in drift was ignored"));
    };
    let expected_observation = second
        .effects
        .first()
        .map(|effect| effect.before)
        .ok_or_else(|| String::from("late handoff observation missing"))?;
    if failure.cause()
        == (NativeInterpreterHandoffExecutionCause::LiveIn {
            address: live_in.address,
            expected: live_in.value,
            observed,
        })
        && failure.interpreter_steps() == 1
        && failure.resume_index() == 1
        && profile_state_observation(failure.state()) == expected_observation
        && failure.state().io().output().is_empty()
        && failure.state().memory().get(index).copied() == Some(observed)
    {
        Ok(())
    } else {
        Err(String::from("late handoff rollback evidence drifted"))
    }
}

#[test]
fn native_interpreter_handoff_budget_zero_suspends_exactly()
-> Result<(), String> {
    let NativeHandoffFixture {
        continuation,
        input,
        memory,
        output,
        plan,
    } = native_handoff_fixture(HostIsa::X86_64, vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let retained = continuation.clone();
    let outcome = NativeInterpreterHandoff::from_buffers(
        continuation,
        memory.clone(),
        input,
        &output,
    )
    .map_err(|error| error.to_string())?
    .execute_with_budget(0)
    .map_err(|error| error.to_string())?;
    let NativeInterpreterHandoffBudgetOutcome::Suspended(suspension) = outcome
    else {
        return Err(String::from("zero budget completed interpreter work"));
    };
    if suspension.continuation() == &retained
        && suspension.interpreter_steps() == 0
        && suspension.resume_index() == 0
        && suspension.remaining_steps() == plan.len()
        && suspension.remaining_key() == retained.remaining_key()
        && suspension.remaining_programs() == plan.programs()
        && suspension.state().memory() == memory
        && suspension.state().io().output().is_empty()
        && profile_state_observation(suspension.state()) == plan.entry()
    {
        Ok(())
    } else {
        Err(String::from("zero-budget suspension evidence drifted"))
    }
}

#[test]
fn native_interpreter_handoff_budget_suspends_then_completes()
-> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let NativeHandoffFixture {
        continuation,
        input,
        memory,
        output,
        plan,
    } = native_handoff_fixture(HostIsa::AArch64, vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let remaining_key = NativeExecutableSequenceKey::from_plan(&plan)
        .suffix(1)
        .ok_or_else(|| String::from("budget suffix key missing"))?;
    let remaining_programs = plan
        .programs()
        .get(1..)
        .ok_or_else(|| String::from("budget program suffix missing"))?;
    let outcome = NativeInterpreterHandoff::from_buffers(
        continuation,
        memory,
        input,
        &output,
    )
    .map_err(|error| error.to_string())?
    .execute_with_budget(1)
    .map_err(|error| error.to_string())?;
    let NativeInterpreterHandoffBudgetOutcome::Suspended(suspension) = outcome
    else {
        return Err(String::from("one-step budget did not suspend"));
    };
    if suspension.interpreter_steps() != 1
        || suspension.resume_index() != 1
        || suspension.remaining_steps() != 1
        || suspension.remaining_key() != &remaining_key
        || suspension.remaining_programs() != remaining_programs
        || suspension.state().memory() != expected.first_memory
    {
        return Err(String::from("one-step suspension evidence drifted"));
    }
    let completion = suspension
        .into_handoff()
        .execute()
        .map_err(|error| error.to_string())?;
    if completion.outcome() == plan.outcome()
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("resumed budget completion drifted"))
    }
}

#[test]
fn native_interpreter_handoff_budget_overshoot_completes() -> Result<(), String>
{
    let expected = direct_normative_sequence_fixture()?;
    let NativeHandoffFixture {
        continuation,
        input,
        memory,
        output,
        plan,
    } = native_handoff_fixture(HostIsa::X86_64, vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let outcome = NativeInterpreterHandoff::from_buffers(
        continuation,
        memory,
        input,
        &output,
    )
    .map_err(|error| error.to_string())?
    .execute_with_budget(7)
    .map_err(|error| error.to_string())?;
    let NativeInterpreterHandoffBudgetOutcome::Completed(completion) = outcome
    else {
        return Err(String::from("oversized budget suspended unexpectedly"));
    };
    if completion.interpreter_outcome()
        == (RunOutcome::BudgetExhausted { steps: 1 })
        && completion.outcome() == plan.outcome()
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("oversized budget completion drifted"))
    }
}

#[test]
fn native_interpreter_handoff_budgeted_resume_rolls_back_drift()
-> Result<(), String> {
    let NativeHandoffFixture {
        continuation,
        input,
        mut memory,
        output,
        plan,
    } = native_handoff_fixture(HostIsa::AArch64, vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let live_in = distinct_second_live_in(&plan)?;
    let index = usize::try_from(live_in.address)
        .map_err(|error| format!("budgeted drift index: {error}"))?;
    let observed = live_in.value.saturating_sub(1);
    *memory
        .get_mut(index)
        .ok_or_else(|| String::from("budgeted drift address missing"))? =
        observed;
    let first = NativeInterpreterHandoff::from_buffers(
        continuation,
        memory,
        input,
        &output,
    )
    .map_err(|error| error.to_string())?
    .execute_with_budget(1)
    .map_err(|error| error.to_string())?;
    let NativeInterpreterHandoffBudgetOutcome::Suspended(suspension) = first
    else {
        return Err(String::from("budgeted drift did not suspend first"));
    };
    let Err(failure) = suspension.into_handoff().execute_with_budget(1) else {
        return Err(String::from("budgeted resumed drift was ignored"));
    };
    if failure.cause()
        == (NativeInterpreterHandoffExecutionCause::LiveIn {
            address: live_in.address,
            expected: live_in.value,
            observed,
        })
        && failure.interpreter_steps() == 1
        && failure.resume_index() == 1
        && failure.state().memory().get(index).copied() == Some(observed)
    {
        Ok(())
    } else {
        Err(String::from("budgeted resumed rollback drifted"))
    }
}

#[test]
fn native_interpreter_handoff_budget_zero_preserves_progress()
-> Result<(), String> {
    let NativeHandoffFixture {
        continuation,
        input,
        memory,
        output,
        plan,
    } = native_handoff_fixture(HostIsa::X86_64, vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let first = NativeInterpreterHandoff::from_buffers(
        continuation,
        memory,
        input,
        &output,
    )
    .map_err(|error| error.to_string())?
    .execute_with_budget(1)
    .map_err(|error| error.to_string())?;
    let NativeInterpreterHandoffBudgetOutcome::Suspended(first_pause) = first
    else {
        return Err(String::from("progress fixture did not suspend"));
    };
    let first_state = first_pause.state().clone();
    let first_key = first_pause.remaining_key().clone();
    let second = first_pause
        .into_handoff()
        .execute_with_budget(0)
        .map_err(|error| error.to_string())?;
    let NativeInterpreterHandoffBudgetOutcome::Suspended(second_pause) = second
    else {
        return Err(String::from("zero resumed budget completed work"));
    };
    if second_pause.interpreter_steps() == 1
        && second_pause.resume_index() == 1
        && second_pause.remaining_steps() == 1
        && second_pause.remaining_key() == &first_key
        && second_pause.remaining_programs()
            == plan.programs().get(1..).unwrap_or(&[])
        && second_pause.state() == &first_state
    {
        Ok(())
    } else {
        Err(String::from(
            "zero resumed budget lost accumulated progress",
        ))
    }
}

#[test]
fn native_continuation_scheduler_yields_to_caller_without_execution()
-> Result<(), String> {
    let fixture = native_schedule_fixture(HostIsa::X86_64, vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let key = NativeExecutableSequenceKey::from_plan(&fixture.plan);
    let outcome = schedule_native_interpreter_handoff(
        fixture.handoff,
        NativeContinuationScheduleDecision::yield_to(
            NativeContinuationYieldTarget::Caller,
        ),
    )
    .map_err(|error| error.to_string())?;
    let NativeContinuationScheduleOutcome::Suspended(pause) = outcome else {
        return Err(String::from("caller yield completed work"));
    };
    if pause.reason() == NativeContinuationScheduleStopReason::CallerYield
        && pause.interpreter_steps() == 0
        && pause.resume_index() == 0
        && pause.remaining_steps() == fixture.plan.len()
        && pause.remaining_key() == &key
        && pause.remaining_programs() == fixture.plan.programs()
        && pause.state().memory() == fixture.memory
        && profile_state_observation(pause.state()) == fixture.plan.entry()
    {
        Ok(())
    } else {
        Err(String::from("caller yield evidence drifted"))
    }
}

#[test]
fn native_continuation_scheduler_yields_native_retry_after_progress()
-> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_schedule_fixture(HostIsa::AArch64, vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let first = schedule_native_interpreter_handoff(
        fixture.handoff,
        NativeContinuationScheduleDecision::interpret(nonzero_test_limit(
            1,
            "scheduler slice",
        )?),
    )
    .map_err(|error| error.to_string())?;
    let NativeContinuationScheduleOutcome::Suspended(pause) = first else {
        return Err(String::from("scheduler slice did not suspend"));
    };
    let second = pause
        .resume(NativeContinuationScheduleDecision::yield_to(
            NativeContinuationYieldTarget::NativeRetry,
        ))
        .map_err(|error| error.to_string())?;
    let NativeContinuationScheduleOutcome::Suspended(retry) = second else {
        return Err(String::from("native retry yield completed work"));
    };
    if retry.reason() == NativeContinuationScheduleStopReason::NativeRetry
        && retry.interpreter_steps() == 1
        && retry.resume_index() == 1
        && retry.remaining_steps() == 1
        && retry.state().memory() == expected.first_memory
    {
        Ok(())
    } else {
        Err(String::from("native retry yield evidence drifted"))
    }
}

#[test]
fn native_continuation_scheduler_slices_then_completes() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_schedule_fixture(HostIsa::X86_64, vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let first = schedule_native_interpreter_handoff(
        fixture.handoff,
        NativeContinuationScheduleDecision::interpret(nonzero_test_limit(
            1,
            "scheduler slice",
        )?),
    )
    .map_err(|error| error.to_string())?;
    let NativeContinuationScheduleOutcome::Suspended(pause) = first else {
        return Err(String::from("scheduler slice completed unexpectedly"));
    };
    if pause.reason() != NativeContinuationScheduleStopReason::BudgetExhausted {
        return Err(String::from("scheduler slice reason drifted"));
    }
    let second = pause
        .resume(NativeContinuationScheduleDecision::complete_interpreter())
        .map_err(|error| error.to_string())?;
    let NativeContinuationScheduleOutcome::Completed(completion) = second
    else {
        return Err(String::from("scheduler completion remained suspended"));
    };
    if completion.outcome() == fixture.plan.outcome()
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("scheduled completion drifted"))
    }
}

#[test]
fn native_continuation_scheduler_completes_directly() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_schedule_fixture(HostIsa::AArch64, vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let outcome = schedule_native_interpreter_handoff(
        fixture.handoff,
        NativeContinuationScheduleDecision::complete_interpreter(),
    )
    .map_err(|error| error.to_string())?;
    let NativeContinuationScheduleOutcome::Completed(completion) = outcome
    else {
        return Err(String::from("direct scheduler completion suspended"));
    };
    if completion.outcome() == fixture.plan.outcome()
        && completion.interpreter_outcome()
            == (RunOutcome::BudgetExhausted { steps: 1 })
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("direct scheduler completion drifted"))
    }
}

#[test]
fn native_continuation_scheduler_propagates_drift() -> Result<(), String> {
    let NativeHandoffFixture {
        continuation,
        input,
        mut memory,
        output,
        plan,
    } = native_handoff_fixture(HostIsa::X86_64, vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let live_in = distinct_second_live_in(&plan)?;
    let index = usize::try_from(live_in.address)
        .map_err(|error| format!("scheduler drift index: {error}"))?;
    let observed = live_in.value.saturating_sub(1);
    *memory
        .get_mut(index)
        .ok_or_else(|| String::from("scheduler drift address missing"))? =
        observed;
    let handoff = NativeInterpreterHandoff::from_buffers(
        continuation,
        memory,
        input,
        &output,
    )
    .map_err(|error| error.to_string())?;
    let first = schedule_native_interpreter_handoff(
        handoff,
        NativeContinuationScheduleDecision::interpret(nonzero_test_limit(
            1,
            "scheduler drift slice",
        )?),
    )
    .map_err(|error| error.to_string())?;
    let NativeContinuationScheduleOutcome::Suspended(pause) = first else {
        return Err(String::from("scheduler drift did not suspend"));
    };
    let Err(failure) = pause
        .resume(NativeContinuationScheduleDecision::complete_interpreter())
    else {
        return Err(String::from("scheduler resumed drift was ignored"));
    };
    if failure.cause()
        == (NativeInterpreterHandoffExecutionCause::LiveIn {
            address: live_in.address,
            expected: live_in.value,
            observed,
        })
        && failure.interpreter_steps() == 1
        && failure.resume_index() == 1
        && failure.state().memory().get(index).copied() == Some(observed)
    {
        Ok(())
    } else {
        Err(String::from("scheduler resumed failure evidence drifted"))
    }
}

#[test]
fn native_retry_admits_exact_initial_suffix() -> Result<(), String> {
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let expected_key = fixture.suspension.remaining_key().clone();
    let admitted = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan,
    )
    .map_err(|failure| failure.error().to_string())?;
    if admitted.plan().programs() == admitted.suspension().remaining_programs()
        && NativeExecutableSequenceKey::from_plan(admitted.plan())
            == expected_key
        && admitted.plan().entry()
            == profile_state_observation(admitted.state())
        && admitted.suspension().reason()
            == NativeContinuationScheduleStopReason::NativeRetry
    {
        Ok(())
    } else {
        Err(String::from("exact initial retry admission drifted"))
    }
}

#[test]
fn native_retry_admits_suffix_after_interpreter_progress() -> Result<(), String>
{
    let fixture = native_retry_fixture(HostIsa::AArch64, 1)?;
    let admitted = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan,
    )
    .map_err(|failure| failure.error().to_string())?;
    if admitted.plan().len() == 1
        && admitted.suspension().interpreter_steps() == 1
        && admitted.suspension().resume_index() == 1
        && admitted.plan().programs()
            == admitted.suspension().remaining_programs()
        && admitted.plan().entry()
            == profile_state_observation(admitted.state())
    {
        Ok(())
    } else {
        Err(String::from("progressed retry admission drifted"))
    }
}

#[test]
fn native_retry_rejects_caller_yield_and_restores_owners() -> Result<(), String>
{
    let fixture = native_schedule_fixture(HostIsa::X86_64, vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let expected_plan = fixture.plan.clone();
    let outcome = schedule_native_interpreter_handoff(
        fixture.handoff,
        NativeContinuationScheduleDecision::yield_to(
            NativeContinuationYieldTarget::Caller,
        ),
    )
    .map_err(|error| error.to_string())?;
    let NativeContinuationScheduleOutcome::Suspended(pause) = outcome else {
        return Err(String::from("caller-yield retry fixture completed"));
    };
    let Err(failure) = NativeContinuationNativeRetry::new(pause, fixture.plan)
    else {
        return Err(String::from("caller yield admitted as native retry"));
    };
    if failure.error()
        != (NativeContinuationRetryAdmissionError::ScheduleReason {
            observed: NativeContinuationScheduleStopReason::CallerYield,
        })
    {
        return Err(String::from("caller-yield rejection reason drifted"));
    }
    let (restored_pause, plan) = failure.into_parts();
    if plan == expected_plan
        && restored_pause.reason()
            == NativeContinuationScheduleStopReason::CallerYield
        && restored_pause.interpreter_steps() == 0
    {
        Ok(())
    } else {
        Err(String::from("caller-yield rejection lost ownership"))
    }
}

#[test]
fn native_retry_rejects_full_plan_after_progress_and_restores_owners()
-> Result<(), String> {
    let fixture = native_retry_fixture(HostIsa::AArch64, 1)?;
    let expected_plan = fixture.full_plan.clone();
    let Err(failure) = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.full_plan,
    ) else {
        return Err(String::from("full plan admitted for retry suffix"));
    };
    if failure.error() != NativeContinuationRetryAdmissionError::PlanPrograms {
        return Err(String::from("retry suffix rejection reason drifted"));
    }
    let (pause, plan) = failure.into_parts();
    if plan == expected_plan
        && pause.reason() == NativeContinuationScheduleStopReason::NativeRetry
        && pause.interpreter_steps() == 1
        && pause.remaining_steps() == 1
    {
        Ok(())
    } else {
        Err(String::from("retry suffix rejection lost ownership"))
    }
}

#[test]
fn native_retry_rejects_cross_isa_key() -> Result<(), String> {
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let cross_isa = select_verified_direct_sequence(
        fixture.suspension.remaining_programs(),
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::AArch64,
    )
    .map_err(|error| error.to_string())?;
    let expected_plan = cross_isa.clone();
    let Err(failure) =
        NativeContinuationNativeRetry::new(fixture.suspension, cross_isa)
    else {
        return Err(String::from("cross-ISA retry key was admitted"));
    };
    if failure.error() != NativeContinuationRetryAdmissionError::PlanKey {
        return Err(String::from("cross-ISA retry rejection reason drifted"));
    }
    let (pause, plan) = failure.into_parts();
    if plan == expected_plan
        && pause.reason() == NativeContinuationScheduleStopReason::NativeRetry
        && pause.interpreter_steps() == 0
        && pause.remaining_steps() == fixture.full_plan.len()
    {
        Ok(())
    } else {
        Err(String::from("cross-ISA retry rejection lost ownership"))
    }
}

#[test]
fn native_interpreter_continuation_advances_mixed_tier_suffix()
-> Result<(), String> {
    let NativeHandoffFixture { continuation, plan, .. } =
        native_handoff_fixture(HostIsa::X86_64, vec![
            FakeNativeRunnerBehavior::GuardMiss,
        ])?;
    let second_entry = plan
        .programs()
        .get(1)
        .and_then(|program| program.effects.first())
        .map(|effect| effect.before)
        .ok_or_else(|| String::from("advanced continuation entry missing"))?;
    let expected_key = continuation
        .remaining_key()
        .suffix(1)
        .ok_or_else(|| String::from("advanced continuation key missing"))?;
    let advanced = continuation
        .advance(
            1,
            second_entry,
            NativeInterpreterContinuationReason::GuardMiss,
        )
        .map_err(|error| error.to_string())?
        .ok_or_else(|| String::from("partial continuation completed"))?;
    if advanced.completed_steps() == 1
        && advanced.resume_index() == 1
        && advanced.observation() == second_entry
        && advanced.reason() == NativeInterpreterContinuationReason::GuardMiss
        && advanced.remaining_steps() == 1
        && advanced.remaining_key() == &expected_key
        && advanced.remaining_programs()
            == plan.programs().get(1..).unwrap_or(&[])
        && advanced.expected_exit() == plan.exit()
        && advanced.expected_outcome() == plan.outcome()
    {
        Ok(())
    } else {
        Err(String::from("mixed-tier continuation advance drifted"))
    }
}

#[test]
fn native_interpreter_continuation_advance_completes_suffix()
-> Result<(), String> {
    let NativeHandoffFixture { continuation, plan, .. } =
        native_handoff_fixture(HostIsa::AArch64, vec![
            FakeNativeRunnerBehavior::Applied,
            FakeNativeRunnerBehavior::GuardMiss,
        ])?;
    if continuation.completed_steps() != 1
        || continuation.remaining_steps() != 1
    {
        return Err(String::from("completion continuation fixture drifted"));
    }
    let completed = continuation
        .advance(
            1,
            plan.exit(),
            NativeInterpreterContinuationReason::GuardMiss,
        )
        .map_err(|error| error.to_string())?;
    if completed.is_none() {
        Ok(())
    } else {
        Err(String::from("completed continuation retained a suffix"))
    }
}

#[test]
fn native_interpreter_continuation_advance_rejects_drift() -> Result<(), String>
{
    let NativeHandoffFixture { continuation, plan, .. } =
        native_handoff_fixture(HostIsa::X86_64, vec![
            FakeNativeRunnerBehavior::GuardMiss,
        ])?;
    let overshoot = continuation.advance(
        plan.len().saturating_add(1),
        plan.exit(),
        NativeInterpreterContinuationReason::ExecutionFailure,
    );
    let observation_drift = continuation.advance(
        1,
        plan.entry(),
        NativeInterpreterContinuationReason::ExecutionFailure,
    );
    if overshoot
        == Err(NativeInterpreterContinuationError::ResumeIndex {
            observed: plan.len().saturating_add(1),
            steps: plan.len(),
        })
        && observation_drift
            == Err(NativeInterpreterContinuationError::ResumeObservation {
                index: 1,
            })
    {
        Ok(())
    } else {
        Err(String::from("continuation advance drift was admitted"))
    }
}

#[test]
fn native_retry_execution_applies_initial_suffix() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let admitted = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan,
    )
    .map_err(|failure| failure.error().to_string())?;
    let mut adapter = native_executable_adapter(950, 0xd0_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let execution = admitted
        .execute(&mut adapter, &mut runner)
        .map_err(|failure| failure.failure().to_string())?;
    if execution.outcome()
        != (NativeSequenceExecutionOutcome::Applied {
            observation: execution.plan().exit(),
            steps: execution.plan().len(),
        })
        || execution.transfer().memory() != expected.final_memory
        || execution.transfer().output() != expected.final_output
        || execution.transfer().observation() != execution.plan().exit()
        || adapter.release_requests.len() != execution.plan().len()
    {
        return Err(String::from("initial native retry execution drifted"));
    }
    let checkpoint = execution
        .into_parts()
        .3
        .into_checkpoint()
        .map_err(|error| error.to_string())?;
    if checkpoint.memory() == expected.final_memory
        && checkpoint.io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("initial retry checkpoint drifted"))
    }
}

#[test]
fn native_retry_execution_applies_progressed_suffix() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::AArch64, 1)?;
    let admitted = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan,
    )
    .map_err(|failure| failure.error().to_string())?;
    let mut adapter = native_executable_adapter(951, 0xd1_000)?;
    let mut runner =
        FakeNativeSequenceRunner::new(vec![FakeNativeRunnerBehavior::Applied]);
    let execution = admitted
        .execute(&mut adapter, &mut runner)
        .map_err(|failure| failure.failure().to_string())?;
    if execution.outcome().completed_steps() == 1
        && execution.suspension().interpreter_steps() == 1
        && execution.transfer().memory() == expected.final_memory
        && execution.transfer().output() == expected.final_output
        && execution.transfer().observation() == execution.plan().exit()
    {
        Ok(())
    } else {
        Err(String::from("progressed native retry execution drifted"))
    }
}

#[test]
fn native_retry_execution_preserves_guard_miss() -> Result<(), String> {
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let entry = fixture.suspension.state().clone();
    let admitted = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan,
    )
    .map_err(|failure| failure.error().to_string())?;
    let mut adapter = native_executable_adapter(952, 0xd2_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let execution = admitted
        .execute(&mut adapter, &mut runner)
        .map_err(|failure| failure.failure().to_string())?;
    if execution.outcome()
        != (NativeSequenceExecutionOutcome::GuardMiss {
            index: 0,
            observation: execution.plan().entry(),
        })
        || execution.transfer().memory() != entry.memory()
        || execution.transfer().observation() != execution.plan().entry()
    {
        return Err(String::from("retry guard miss mutated state"));
    }
    let checkpoint = execution
        .into_parts()
        .3
        .into_checkpoint()
        .map_err(|error| error.to_string())?;
    if checkpoint == entry {
        Ok(())
    } else {
        Err(String::from("retry guard checkpoint drifted"))
    }
}

#[test]
fn native_retry_execution_retains_runner_rollback() -> Result<(), String> {
    let fixture = native_retry_fixture(HostIsa::AArch64, 0)?;
    let entry = fixture.suspension.state().clone();
    let admitted = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan,
    )
    .map_err(|failure| failure.error().to_string())?;
    let mut adapter = native_executable_adapter(953, 0xd3_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let Err(failure) = admitted.execute(&mut adapter, &mut runner) else {
        return Err(String::from("configured retry runner failure ignored"));
    };
    if failure.failure().completed_steps() != 0
        || failure.failure().resume_index() != 0
        || failure.transfer().memory() != entry.memory()
        || failure.transfer().observation() != failure.plan().entry()
    {
        return Err(String::from("retry runner rollback evidence drifted"));
    }
    let checkpoint = failure
        .into_parts()
        .3
        .into_checkpoint()
        .map_err(|error| error.to_string())?;
    if checkpoint == entry {
        Ok(())
    } else {
        Err(String::from("retry runner rollback checkpoint drifted"))
    }
}

#[test]
fn native_retry_execution_retains_committed_cleanup_failure()
-> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 1)?;
    let admitted = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan,
    )
    .map_err(|failure| failure.error().to_string())?;
    let mut adapter =
        native_executable_adapter(954, 0xd4_000)?.with_release_failure_at(1);
    let mut runner =
        FakeNativeSequenceRunner::new(vec![FakeNativeRunnerBehavior::Applied]);
    let Err(failure) = admitted.execute(&mut adapter, &mut runner) else {
        return Err(String::from("configured retry cleanup failure ignored"));
    };
    if failure.failure().completed_steps() != 1
        || failure.failure().resume_index() != 1
        || failure.transfer().memory() != expected.final_memory
        || failure.transfer().output() != expected.final_output
        || failure.transfer().observation() != failure.plan().exit()
    {
        return Err(String::from("retry cleanup failure lost committed state"));
    }
    let (_, _, sequence_failure, transfer) = (*failure).into_parts();
    let checkpoint = transfer
        .into_checkpoint()
        .map_err(|error| error.to_string())?;
    let execution = (*sequence_failure)
        .into_execution_failure()
        .ok_or_else(|| String::from("retry cleanup owner missing"))?;
    let release = execution
        .into_release_failure()
        .ok_or_else(|| String::from("retry release failure missing"))?;
    release
        .retry(&mut adapter)
        .map_err(|error| error.to_string())?;
    if checkpoint.memory() == expected.final_memory
        && checkpoint.io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("retry cleanup checkpoint drifted"))
    }
}

#[test]
fn native_retry_rebase_completes_initial_suffix() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let expected_outcome = fixture.full_plan.outcome();
    let admitted = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan,
    )
    .map_err(|failure| failure.error().to_string())?;
    let mut adapter = native_executable_adapter(955, 0xd5_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let disposition = admitted
        .execute(&mut adapter, &mut runner)
        .map_err(|failure| failure.failure().to_string())?
        .rebase()
        .map_err(|failure| failure.error().to_string())?;
    let NativeContinuationRetryDisposition::Completed(completion) = disposition
    else {
        return Err(String::from("initial retry rebase remained resumable"));
    };
    if completion.interpreter_steps() == 0
        && completion.retry_steps() == 2
        && completion.outcome() == expected_outcome
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("initial retry completion rebase drifted"))
    }
}

#[test]
fn native_retry_rebase_completes_after_interpreter_progress()
-> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::AArch64, 1)?;
    let expected_outcome = fixture.full_plan.outcome();
    let admitted = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan,
    )
    .map_err(|failure| failure.error().to_string())?;
    let mut adapter = native_executable_adapter(956, 0xd6_000)?;
    let mut runner =
        FakeNativeSequenceRunner::new(vec![FakeNativeRunnerBehavior::Applied]);
    let disposition = admitted
        .execute(&mut adapter, &mut runner)
        .map_err(|failure| failure.failure().to_string())?
        .rebase()
        .map_err(|failure| failure.error().to_string())?;
    let NativeContinuationRetryDisposition::Completed(completion) = disposition
    else {
        return Err(String::from("progressed retry rebase remained resumable"));
    };
    if completion.interpreter_steps() == 1
        && completion.retry_steps() == 1
        && completion.outcome() == expected_outcome
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("progressed retry completion rebase drifted"))
    }
}

#[test]
fn native_retry_rebase_resumes_after_progressed_guard() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 1)?;
    let expected_outcome = fixture.full_plan.outcome();
    let admitted = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan,
    )
    .map_err(|failure| failure.error().to_string())?;
    let mut adapter = native_executable_adapter(957, 0xd7_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let disposition = admitted
        .execute(&mut adapter, &mut runner)
        .map_err(|failure| failure.failure().to_string())?
        .rebase()
        .map_err(|failure| failure.error().to_string())?;
    let NativeContinuationRetryDisposition::Resumable(resumption) = disposition
    else {
        return Err(String::from("retry guard rebase completed unexpectedly"));
    };
    if resumption.interpreter_steps() != 1
        || resumption.retry_steps() != 0
        || resumption.resume_index() != 1
    {
        return Err(String::from("retry guard rebase progress drifted"));
    }
    let outcome = schedule_native_interpreter_handoff(
        resumption.into_handoff(),
        NativeContinuationScheduleDecision::complete_interpreter(),
    )
    .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Completed(completion) = outcome
    else {
        return Err(String::from("rebased retry handoff remained suspended"));
    };
    if completion.outcome() == expected_outcome
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("rebased retry handoff completion drifted"))
    }
}

#[test]
fn native_retry_failure_rebase_resumes_before_progress() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::AArch64, 0)?;
    let expected_outcome = fixture.full_plan.outcome();
    let admitted = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan,
    )
    .map_err(|failure| failure.error().to_string())?;
    let mut adapter = native_executable_adapter(958, 0xd8_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let Err(execution_failure) = admitted.execute(&mut adapter, &mut runner)
    else {
        return Err(String::from("retry failure fixture completed"));
    };
    let rebased = execution_failure
        .rebase()
        .map_err(|failure| failure.error().to_string())?;
    let (disposition, sequence_failure) = rebased.into_parts();
    if sequence_failure.completed_steps() != 0
        || sequence_failure.resume_index() != 0
    {
        return Err(String::from("retry failure progress drifted"));
    }
    let NativeContinuationRetryDisposition::Resumable(resumption) = disposition
    else {
        return Err(String::from("zero-progress retry failure completed"));
    };
    if resumption.interpreter_steps() != 0
        || resumption.retry_steps() != 0
        || resumption.resume_index() != 0
    {
        return Err(String::from("zero-progress failure rebase drifted"));
    }
    let outcome = schedule_native_interpreter_handoff(
        resumption.into_handoff(),
        NativeContinuationScheduleDecision::complete_interpreter(),
    )
    .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Completed(completion) = outcome
    else {
        return Err(String::from("failure-rebased handoff suspended"));
    };
    if completion.outcome() == expected_outcome
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("failure-rebased completion drifted"))
    }
}

#[test]
fn native_retry_failure_rebase_resumes_after_retry_progress()
-> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let expected_outcome = fixture.full_plan.outcome();
    let admitted = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan,
    )
    .map_err(|failure| failure.error().to_string())?;
    let mut adapter = native_executable_adapter(959, 0xd9_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let Err(execution_failure) = admitted.execute(&mut adapter, &mut runner)
    else {
        return Err(String::from("progressed retry failure completed"));
    };
    let rebased = execution_failure
        .rebase()
        .map_err(|failure| failure.error().to_string())?;
    let (disposition, sequence_failure) = rebased.into_parts();
    if sequence_failure.completed_steps() != 1
        || sequence_failure.resume_index() != 1
    {
        return Err(String::from("progressed retry failure evidence drifted"));
    }
    let NativeContinuationRetryDisposition::Resumable(resumption) = disposition
    else {
        return Err(String::from("progressed retry failure completed"));
    };
    if resumption.interpreter_steps() != 0
        || resumption.retry_steps() != 1
        || resumption.resume_index() != 1
    {
        return Err(String::from("progressed failure rebase drifted"));
    }
    let outcome = schedule_native_interpreter_handoff(
        resumption.into_handoff(),
        NativeContinuationScheduleDecision::complete_interpreter(),
    )
    .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Completed(completion) = outcome
    else {
        return Err(String::from("progressed failure handoff suspended"));
    };
    if completion.outcome() == expected_outcome
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("progressed failure completion drifted"))
    }
}

#[test]
fn native_retry_failure_rebase_completes_with_cleanup_owner()
-> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::AArch64, 1)?;
    let expected_outcome = fixture.full_plan.outcome();
    let admitted = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan,
    )
    .map_err(|failure| failure.error().to_string())?;
    let mut adapter =
        native_executable_adapter(960, 0xda_000)?.with_release_failure_at(1);
    let mut runner =
        FakeNativeSequenceRunner::new(vec![FakeNativeRunnerBehavior::Applied]);
    let Err(execution_failure) = admitted.execute(&mut adapter, &mut runner)
    else {
        return Err(String::from("cleanup retry failure completed cleanly"));
    };
    let rebased = execution_failure
        .rebase()
        .map_err(|failure| failure.error().to_string())?;
    let (disposition, sequence_failure) = rebased.into_parts();
    let NativeContinuationRetryDisposition::Completed(completion) = disposition
    else {
        return Err(String::from("cleanup retry failure remained resumable"));
    };
    if completion.interpreter_steps() != 1
        || completion.retry_steps() != 1
        || completion.outcome() != expected_outcome
        || completion.state().memory() != expected.final_memory
        || completion.state().io().output() != expected.final_output
    {
        return Err(String::from("cleanup failure completion rebase drifted"));
    }
    let execution = (*sequence_failure)
        .into_execution_failure()
        .ok_or_else(|| String::from("rebased cleanup owner missing"))?;
    let release = execution
        .into_release_failure()
        .ok_or_else(|| String::from("rebased release owner missing"))?;
    release
        .retry(&mut adapter)
        .map_err(|failure| failure.to_string())
}

#[test]
fn native_retry_planner_selects_exact_windows_retry() -> Result<(), String> {
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let outcome = plan_native_continuation_retry(
        fixture.suspension,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|failure| failure.error().to_string())?;
    let NativeContinuationRetryPlanningOutcome::Native(retry) = outcome else {
        return Err(String::from("Windows retry planning fell back"));
    };
    if retry.plan().programs() == fixture.full_plan.programs()
        && retry.plan().entry() == fixture.full_plan.entry()
        && retry.plan().exit() == fixture.full_plan.exit()
        && retry.suspension().reason()
            == NativeContinuationScheduleStopReason::NativeRetry
    {
        Ok(())
    } else {
        Err(String::from("Windows retry planning identity drifted"))
    }
}

#[test]
fn native_retry_planner_falls_back_for_target_format() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    for (isa, interpreter_steps) in
        [(HostIsa::X86_64, 0usize), (HostIsa::AArch64, 1usize)]
    {
        let fixture = native_retry_fixture(isa, interpreter_steps)?;
        let expected_outcome = fixture.full_plan.outcome();
        let outcome = plan_native_continuation_retry(
            fixture.suspension,
            safe_rust_profiled_capability(),
            HostOperatingSystem::Linux,
            isa,
        )
        .map_err(|failure| failure.error().to_string())?;
        let NativeContinuationRetryPlanningOutcome::Interpreter(handoff) =
            outcome
        else {
            return Err(String::from(
                "unsupported format planned native retry",
            ));
        };
        let completion =
            handoff.execute().map_err(|failure| failure.to_string())?;
        if completion.outcome() != expected_outcome
            || completion.state().memory() != expected.final_memory
            || completion.state().io().output() != expected.final_output
        {
            return Err(String::from("target-format fallback drifted"));
        }
    }
    Ok(())
}

#[test]
fn native_retry_planner_preserves_hard_profile_failure() -> Result<(), String> {
    let fixture = native_retry_fixture(HostIsa::X86_64, 1)?;
    let expected_profile_diagnostic = match select_verified_direct_sequence(
        fixture.suspension.remaining_programs(),
        safe_rust_classic_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    ) {
        Err(DirectSequenceError::Step { error, index: 0 })
            if matches!(error.as_ref(), DirectSelectionError::Profile(_)) =>
        {
            error.to_string()
        },
        result => {
            return Err(format!(
                "direct profile preflight fixture changed: {result:?}"
            ));
        },
    };
    let expected_state = fixture.suspension.state().clone();
    let expected_steps = fixture.suspension.interpreter_steps();
    let Err(failure) = plan_native_continuation_retry(
        fixture.suspension,
        safe_rust_classic_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    ) else {
        return Err(String::from("profile-incompatible retry was routed"));
    };
    if failure.error()
        != (NativeContinuationRetryPlanningError::Step {
            cause: NativeContinuationRetryStepPlanningError::Profile,
            index: 0,
        })
    {
        return Err(String::from("hard retry planning error drifted"));
    }
    if !expected_profile_diagnostic.starts_with("MALBOLGE-PROFILE-001 ")
        || failure.profile_diagnostic()
            != Some(expected_profile_diagnostic.as_str())
        || failure.to_string() != expected_profile_diagnostic
    {
        return Err(String::from(
            "retry planner lost exact MALBOLGE-PROFILE-001 diagnostic",
        ));
    }
    let suspension = (*failure).into_suspension();
    if suspension.interpreter_steps() == expected_steps
        && suspension.state() == &expected_state
        && suspension.reason()
            == NativeContinuationScheduleStopReason::NativeRetry
    {
        Ok(())
    } else {
        Err(String::from("hard planning failure lost suspension"))
    }
}

#[test]
fn native_retry_planner_rejects_non_retry_reason() -> Result<(), String> {
    let fixture = native_schedule_fixture(HostIsa::AArch64, vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let outcome = schedule_native_interpreter_handoff(
        fixture.handoff,
        NativeContinuationScheduleDecision::yield_to(
            NativeContinuationYieldTarget::Caller,
        ),
    )
    .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Suspended(suspension) = outcome
    else {
        return Err(String::from("caller yield completed before planning"));
    };
    let expected_state = suspension.state().clone();
    let Err(failure) = plan_native_continuation_retry(
        suspension,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::AArch64,
    ) else {
        return Err(String::from("caller yield entered retry planning"));
    };
    if failure.error()
        != (NativeContinuationRetryPlanningError::ScheduleReason {
            observed: NativeContinuationScheduleStopReason::CallerYield,
        })
    {
        return Err(String::from("non-retry planning rejection drifted"));
    }
    let recovered = (*failure).into_suspension();
    if recovered.reason() == NativeContinuationScheduleStopReason::CallerYield
        && recovered.state() == &expected_state
    {
        Ok(())
    } else {
        Err(String::from("non-retry planning lost suspension"))
    }
}

#[test]
fn native_retry_policy_selects_exact_attempt_numbers() -> Result<(), String> {
    let policy = NativeContinuationRetryPolicy::new(
        2,
        NativeContinuationRetryFallback::complete(),
    );
    for (attempts, expected_next) in [(0usize, 1usize), (1usize, 2usize)] {
        let fixture = native_retry_fixture(HostIsa::X86_64, attempts)?;
        let expected_state = fixture.suspension.state().clone();
        let outcome = policy
            .route(fixture.suspension, attempts)
            .map_err(|failure| failure.error().to_string())?;
        let NativeContinuationRetryPolicyOutcome::NativeRetry(route) = outcome
        else {
            return Err(String::from("available retry budget fell back"));
        };
        if route.attempts() != attempts || route.next_attempt() != expected_next
        {
            return Err(String::from("retry attempt numbering drifted"));
        }
        let suspension = route.into_suspension();
        if suspension.state() != &expected_state
            || suspension.reason()
                != NativeContinuationScheduleStopReason::NativeRetry
        {
            return Err(String::from("retry policy lost suspension ownership"));
        }
    }
    Ok(())
}

#[test]
fn native_retry_policy_completes_after_attempt_limit() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::AArch64, 1)?;
    let expected_outcome = fixture.full_plan.outcome();
    let policy = NativeContinuationRetryPolicy::new(
        2,
        NativeContinuationRetryFallback::complete(),
    );
    let outcome = policy
        .route(fixture.suspension, 2)
        .map_err(|failure| failure.error().to_string())?;
    let NativeContinuationRetryPolicyOutcome::Interpreter(route) = outcome
    else {
        return Err(String::from("exhausted retry budget selected native"));
    };
    if route.attempts() != 2
        || route.decision()
            != NativeContinuationScheduleDecision::complete_interpreter()
    {
        return Err(String::from("complete retry fallback route drifted"));
    }
    let (handoff, decision) = route.into_parts();
    let scheduled = schedule_native_interpreter_handoff(handoff, decision)
        .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Completed(completion) = scheduled
    else {
        return Err(String::from("complete retry fallback suspended"));
    };
    if completion.outcome() == expected_outcome
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("complete retry fallback execution drifted"))
    }
}

#[test]
fn native_retry_policy_slices_after_zero_limit() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let policy = NativeContinuationRetryPolicy::new(
        0,
        NativeContinuationRetryFallback::sliced(nonzero_test_limit(
            1,
            "retry policy slice",
        )?),
    );
    let outcome = policy
        .route(fixture.suspension, 0)
        .map_err(|failure| failure.error().to_string())?;
    let NativeContinuationRetryPolicyOutcome::Interpreter(route) = outcome
    else {
        return Err(String::from("zero retry limit selected native"));
    };
    let (handoff, decision) = route.into_parts();
    let first = schedule_native_interpreter_handoff(handoff, decision)
        .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Suspended(pause) = first else {
        return Err(String::from("sliced retry fallback completed early"));
    };
    if pause.reason() != NativeContinuationScheduleStopReason::BudgetExhausted
        || pause.interpreter_steps() != 1
        || pause.resume_index() != 1
    {
        return Err(String::from("sliced retry fallback evidence drifted"));
    }
    let second = pause
        .resume(NativeContinuationScheduleDecision::complete_interpreter())
        .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Completed(completion) = second
    else {
        return Err(String::from("sliced retry fallback did not resume"));
    };
    if completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("sliced retry fallback completion drifted"))
    }
}

#[test]
fn native_retry_policy_rejects_non_retry_reason() -> Result<(), String> {
    let fixture = native_schedule_fixture(HostIsa::AArch64, vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let yielded = schedule_native_interpreter_handoff(
        fixture.handoff,
        NativeContinuationScheduleDecision::yield_to(
            NativeContinuationYieldTarget::Caller,
        ),
    )
    .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Suspended(suspension) = yielded
    else {
        return Err(String::from("caller yield completed before retry policy"));
    };
    let expected_state = suspension.state().clone();
    let policy = one_native_retry_policy();
    let Err(failure) = policy.route(suspension, 0) else {
        return Err(String::from("caller yield entered retry policy"));
    };
    if failure.error()
        != (NativeContinuationRetryPolicyError::ScheduleReason {
            observed: NativeContinuationScheduleStopReason::CallerYield,
        })
    {
        return Err(String::from("retry policy reason rejection drifted"));
    }
    let recovered = (*failure).into_suspension();
    if recovered.state() == &expected_state
        && recovered.reason()
            == NativeContinuationScheduleStopReason::CallerYield
    {
        Ok(())
    } else {
        Err(String::from("retry policy rejection lost suspension"))
    }
}

#[test]
fn native_retry_router_selects_bounded_windows_attempt() -> Result<(), String> {
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let expected_state = fixture.suspension.state().clone();
    let policy = NativeContinuationRetryPolicy::new(
        2,
        NativeContinuationRetryFallback::complete(),
    );
    let routing = route_native_continuation_retry(
        NativeContinuationRetryRoutingRequest::new(
            policy,
            fixture.suspension,
            0,
            NativeContinuationRetryHost::new(
                safe_rust_profiled_capability(),
                HostOperatingSystem::Windows,
                HostIsa::X86_64,
            ),
        ),
    )
    .map_err(|failure| failure.error().to_string())?;
    let NativeContinuationRetryRoute::Native(native_route) = routing else {
        return Err(String::from("bounded Windows retry routed interpreter"));
    };
    if native_route.attempt() == 1
        && native_route.retry().plan().programs()
            == fixture.full_plan.programs()
        && native_route.retry().suspension().state() == &expected_state
    {
        Ok(())
    } else {
        Err(String::from("bounded Windows retry route drifted"))
    }
}

#[test]
fn native_retry_router_exhaustion_bypasses_hard_planner() -> Result<(), String>
{
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::AArch64, 1)?;
    let expected_outcome = fixture.full_plan.outcome();
    let policy = one_native_retry_policy();
    let routing = route_native_continuation_retry(
        NativeContinuationRetryRoutingRequest::new(
            policy,
            fixture.suspension,
            1,
            NativeContinuationRetryHost::new(
                safe_rust_classic_capability(),
                HostOperatingSystem::Windows,
                HostIsa::AArch64,
            ),
        ),
    )
    .map_err(|failure| failure.error().to_string())?;
    let NativeContinuationRetryRoute::Interpreter(interpreter_route) = routing
    else {
        return Err(String::from("exhausted retry route entered planner"));
    };
    if interpreter_route.attempts() != 1
        || interpreter_route.decision()
            != NativeContinuationScheduleDecision::complete_interpreter()
    {
        return Err(String::from("exhausted retry route evidence drifted"));
    }
    let (handoff, decision) = interpreter_route.into_parts();
    let outcome = schedule_native_interpreter_handoff(handoff, decision)
        .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Completed(completion) = outcome
    else {
        return Err(String::from("exhausted retry fallback suspended"));
    };
    if completion.outcome() == expected_outcome
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("exhausted retry fallback drifted"))
    }
}

#[test]
fn native_retry_router_uses_policy_for_target_format() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let policy = NativeContinuationRetryPolicy::new(
        2,
        NativeContinuationRetryFallback::sliced(nonzero_test_limit(
            1,
            "retry router slice",
        )?),
    );
    let routing = route_native_continuation_retry(
        NativeContinuationRetryRoutingRequest::new(
            policy,
            fixture.suspension,
            0,
            NativeContinuationRetryHost::new(
                safe_rust_profiled_capability(),
                HostOperatingSystem::Linux,
                HostIsa::X86_64,
            ),
        ),
    )
    .map_err(|failure| failure.error().to_string())?;
    let NativeContinuationRetryRoute::Interpreter(interpreter_route) = routing
    else {
        return Err(String::from("target format retry route remained native"));
    };
    if interpreter_route.attempts() != 0 {
        return Err(String::from("target format fallback counted attempt"));
    }
    let (handoff, decision) = interpreter_route.into_parts();
    let first = schedule_native_interpreter_handoff(handoff, decision)
        .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Suspended(pause) = first else {
        return Err(String::from("target format sliced fallback completed"));
    };
    if pause.interpreter_steps() != 1
        || pause.reason()
            != NativeContinuationScheduleStopReason::BudgetExhausted
    {
        return Err(String::from("target format fallback slice drifted"));
    }
    let second = pause
        .resume(NativeContinuationScheduleDecision::complete_interpreter())
        .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Completed(completion) = second
    else {
        return Err(String::from("target format fallback did not complete"));
    };
    if completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("target format routed completion drifted"))
    }
}

fn expected_retry_profile_diagnostic(
    suspension: &NativeContinuationScheduleSuspension,
) -> Result<String, String> {
    match select_verified_direct_sequence(
        suspension.remaining_programs(),
        safe_rust_classic_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    ) {
        Err(DirectSequenceError::Step { error, index: 0 })
            if matches!(error.as_ref(), DirectSelectionError::Profile(_)) =>
        {
            Ok(error.to_string())
        },
        result => Err(format!(
            "router profile preflight fixture changed: {result:?}"
        )),
    }
}

#[test]
fn native_retry_router_preserves_hard_planning_failure() -> Result<(), String> {
    let fixture = native_retry_fixture(HostIsa::X86_64, 1)?;
    let expected_profile_diagnostic =
        expected_retry_profile_diagnostic(&fixture.suspension)?;
    let expected_state = fixture.suspension.state().clone();
    let policy = NativeContinuationRetryPolicy::new(
        2,
        NativeContinuationRetryFallback::complete(),
    );
    let Err(failure) = route_native_continuation_retry(
        NativeContinuationRetryRoutingRequest::new(
            policy,
            fixture.suspension,
            0,
            NativeContinuationRetryHost::new(
                safe_rust_classic_capability(),
                HostOperatingSystem::Windows,
                HostIsa::X86_64,
            ),
        ),
    ) else {
        return Err(String::from("hard router planning failure was hidden"));
    };
    if failure.error()
        != (NativeContinuationRetryRoutingError::Planning(
            NativeContinuationRetryPlanningError::Step {
                cause: NativeContinuationRetryStepPlanningError::Profile,
                index: 0,
            },
        ))
    {
        return Err(String::from("hard router planning error drifted"));
    }
    if failure.profile_diagnostic()
        != Some(expected_profile_diagnostic.as_str())
        || failure.to_string() != expected_profile_diagnostic
    {
        return Err(String::from(
            "retry router lost exact MALBOLGE-PROFILE-001 diagnostic",
        ));
    }
    let recovered = (*failure).into_suspension();
    if recovered.state() == &expected_state
        && recovered.reason()
            == NativeContinuationScheduleStopReason::NativeRetry
    {
        Ok(())
    } else {
        Err(String::from("hard router failure lost suspension"))
    }
}

#[test]
fn native_retry_router_preserves_policy_rejection() -> Result<(), String> {
    let fixture = native_schedule_fixture(HostIsa::AArch64, vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ])?;
    let yielded = schedule_native_interpreter_handoff(
        fixture.handoff,
        NativeContinuationScheduleDecision::yield_to(
            NativeContinuationYieldTarget::Caller,
        ),
    )
    .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Suspended(suspension) = yielded
    else {
        return Err(String::from("caller yield completed before retry router"));
    };
    let expected_state = suspension.state().clone();
    let policy = NativeContinuationRetryPolicy::new(
        2,
        NativeContinuationRetryFallback::complete(),
    );
    let Err(failure) = route_native_continuation_retry(
        NativeContinuationRetryRoutingRequest::new(
            policy,
            suspension,
            0,
            NativeContinuationRetryHost::new(
                safe_rust_profiled_capability(),
                HostOperatingSystem::Windows,
                HostIsa::AArch64,
            ),
        ),
    ) else {
        return Err(String::from("caller yield entered retry router"));
    };
    if failure.error()
        != (NativeContinuationRetryRoutingError::Policy(
            NativeContinuationRetryPolicyError::ScheduleReason {
                observed: NativeContinuationScheduleStopReason::CallerYield,
            },
        ))
    {
        return Err(String::from("retry router policy error drifted"));
    }
    let recovered = (*failure).into_suspension();
    if recovered.state() == &expected_state
        && recovered.reason()
            == NativeContinuationScheduleStopReason::CallerYield
    {
        Ok(())
    } else {
        Err(String::from("retry router policy failure lost suspension"))
    }
}

#[test]
fn native_retry_turn_executes_interpreter_route() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let expected_outcome = fixture.full_plan.outcome();
    let policy = NativeContinuationRetryPolicy::new(
        0,
        NativeContinuationRetryFallback::complete(),
    );
    let route = route_native_continuation_retry(
        NativeContinuationRetryRoutingRequest::new(
            policy,
            fixture.suspension,
            0,
            NativeContinuationRetryHost::new(
                safe_rust_classic_capability(),
                HostOperatingSystem::Windows,
                HostIsa::X86_64,
            ),
        ),
    )
    .map_err(|failure| failure.error().to_string())?;
    let mut adapter = native_executable_adapter(961, 0xdb_000)?;
    let mut runner = FakeNativeSequenceRunner::new(Vec::new());
    let outcome = execute_native_continuation_retry_turn(
        route,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| format!("interpreter retry turn failed: {failure:?}"))?;
    let NativeContinuationRetryTurnOutcome::Interpreter(turn) = outcome else {
        return Err(String::from("interpreter retry route executed native"));
    };
    if turn.attempts() != 0 {
        return Err(String::from("interpreter retry turn counted attempt"));
    }
    let NativeContinuationScheduleOutcome::Completed(completion) =
        turn.outcome()
    else {
        return Err(String::from("interpreter retry turn suspended"));
    };
    if completion.outcome() == expected_outcome
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
        && adapter.allocation_requests.is_empty()
        && runner.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("interpreter retry turn evidence drifted"))
    }
}

#[test]
fn native_retry_turn_executes_native_completion() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::AArch64, 0)?;
    let expected_outcome = fixture.full_plan.outcome();
    let route = one_attempt_retry_route(
        fixture.suspension,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::AArch64,
    )?;
    let mut adapter = native_executable_adapter(962, 0xdc_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = execute_native_continuation_retry_turn(
        route,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| format!("native completion turn failed: {failure:?}"))?;
    let NativeContinuationRetryTurnOutcome::NativeSuccess(turn) = outcome
    else {
        return Err(String::from("native completion turn did not succeed"));
    };
    if turn.attempt() != 1 {
        return Err(String::from("native completion attempt drifted"));
    }
    let NativeContinuationRetryDisposition::Completed(completion) =
        turn.disposition()
    else {
        return Err(String::from("native completion remained resumable"));
    };
    if completion.outcome() == expected_outcome
        && completion.retry_steps() == 2
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("native completion turn evidence drifted"))
    }
}

#[test]
fn native_retry_turn_rebases_native_guard() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 1)?;
    let expected_outcome = fixture.full_plan.outcome();
    let route = one_attempt_retry_route(
        fixture.suspension,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )?;
    let mut adapter = native_executable_adapter(963, 0xdd_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let outcome = execute_native_continuation_retry_turn(
        route,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| format!("native guard turn failed: {failure:?}"))?;
    let NativeContinuationRetryTurnOutcome::NativeSuccess(turn) = outcome
    else {
        return Err(String::from("native guard turn became failure"));
    };
    let (attempt, disposition) = turn.into_parts();
    let NativeContinuationRetryDisposition::Resumable(resumption) = disposition
    else {
        return Err(String::from("native guard turn completed"));
    };
    if attempt != 1
        || resumption.interpreter_steps() != 1
        || resumption.retry_steps() != 0
        || resumption.resume_index() != 1
    {
        return Err(String::from("native guard turn progress drifted"));
    }
    let scheduled = schedule_native_interpreter_handoff(
        resumption.into_handoff(),
        NativeContinuationScheduleDecision::complete_interpreter(),
    )
    .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Completed(completion) = scheduled
    else {
        return Err(String::from("native guard fallback suspended"));
    };
    if completion.outcome() == expected_outcome
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("native guard fallback drifted"))
    }
}

#[test]
fn native_retry_turn_splits_runner_failure() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::AArch64, 0)?;
    let expected_outcome = fixture.full_plan.outcome();
    let route = one_attempt_retry_route(
        fixture.suspension,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::AArch64,
    )?;
    let mut adapter = native_executable_adapter(964, 0xde_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let outcome = execute_native_continuation_retry_turn(
        route,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| {
        format!("native failure turn rebase failed: {failure:?}")
    })?;
    let NativeContinuationRetryTurnOutcome::NativeFailure(turn) = outcome
    else {
        return Err(String::from("native runner failure did not split owners"));
    };
    let (attempt, disposition, sequence_failure) = turn.into_parts();
    if attempt != 1
        || sequence_failure.completed_steps() != 0
        || sequence_failure.resume_index() != 0
    {
        return Err(String::from("native failure turn evidence drifted"));
    }
    let NativeContinuationRetryDisposition::Resumable(resumption) = disposition
    else {
        return Err(String::from("zero-progress native failure completed"));
    };
    let scheduled = schedule_native_interpreter_handoff(
        resumption.into_handoff(),
        NativeContinuationScheduleDecision::complete_interpreter(),
    )
    .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Completed(completion) = scheduled
    else {
        return Err(String::from("native failure fallback suspended"));
    };
    if completion.outcome() == expected_outcome
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("native failure fallback drifted"))
    }
}

#[test]
fn native_retry_turn_splits_cleanup_completion() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 1)?;
    let expected_outcome = fixture.full_plan.outcome();
    let route = one_attempt_retry_route(
        fixture.suspension,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )?;
    let mut adapter =
        native_executable_adapter(965, 0xdf_000)?.with_release_failure_at(1);
    let mut runner =
        FakeNativeSequenceRunner::new(vec![FakeNativeRunnerBehavior::Applied]);
    let outcome = execute_native_continuation_retry_turn(
        route,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| format!("cleanup turn rebase failed: {failure:?}"))?;
    let NativeContinuationRetryTurnOutcome::NativeFailure(turn) = outcome
    else {
        return Err(String::from("cleanup failure did not split owners"));
    };
    let (attempt, disposition, sequence_failure) = turn.into_parts();
    if attempt != 1 {
        return Err(String::from("cleanup failure attempt drifted"));
    }
    let NativeContinuationRetryDisposition::Completed(completion) = disposition
    else {
        return Err(String::from("cleanup failure lost semantic completion"));
    };
    if completion.outcome() != expected_outcome
        || completion.state().memory() != expected.final_memory
        || completion.state().io().output() != expected.final_output
    {
        return Err(String::from("cleanup failure completion drifted"));
    }
    let execution = (*sequence_failure)
        .into_execution_failure()
        .ok_or_else(|| String::from("turn cleanup execution owner missing"))?;
    let release = execution
        .into_release_failure()
        .ok_or_else(|| String::from("turn cleanup release owner missing"))?;
    release
        .retry(&mut adapter)
        .map_err(|failure| failure.to_string())
}

#[test]
fn native_retry_cycle_falls_back_at_zero_limit() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let expected_outcome = fixture.full_plan.outcome();
    let policy = NativeContinuationRetryPolicy::new(
        0,
        NativeContinuationRetryFallback::complete(),
    );
    let request = windows_retry_cycle_request(
        policy,
        fixture.suspension,
        0,
        HostIsa::X86_64,
    );
    let mut adapter = native_executable_adapter(966, 0xe0_000)?;
    let mut runner = FakeNativeSequenceRunner::new(Vec::new());
    let outcome = execute_native_continuation_retry_cycle(
        request,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| format!("zero-limit retry cycle: {failure:?}"))?;
    let NativeContinuationRetryCycleOutcome::Interpreter(turn) = outcome else {
        return Err(String::from("zero-limit retry cycle executed native"));
    };
    if turn.attempts() != 0 {
        return Err(String::from("zero-limit cycle counted native attempt"));
    }
    let NativeContinuationScheduleOutcome::Completed(completion) =
        turn.outcome()
    else {
        return Err(String::from("zero-limit retry cycle suspended"));
    };
    if completion.outcome() == expected_outcome
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
        && adapter.allocation_requests.is_empty()
        && runner.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("zero-limit retry cycle evidence drifted"))
    }
}

#[test]
fn native_retry_cycle_guards_until_bounded_fallback() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::AArch64, 0)?;
    let expected_outcome = fixture.full_plan.outcome();
    let policy = NativeContinuationRetryPolicy::new(
        2,
        NativeContinuationRetryFallback::complete(),
    );
    let request = windows_retry_cycle_request(
        policy,
        fixture.suspension,
        0,
        HostIsa::AArch64,
    );
    let mut adapter = native_executable_adapter(967, 0xe1_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::GuardMiss,
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let outcome = execute_native_continuation_retry_cycle(
        request,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| format!("bounded guard cycle: {failure:?}"))?;
    let NativeContinuationRetryCycleOutcome::Interpreter(turn) = outcome else {
        return Err(String::from("bounded guards did not fall back"));
    };
    if turn.attempts() != 2 || runner.calls != 2 {
        return Err(String::from("bounded guard attempt evidence drifted"));
    }
    let NativeContinuationScheduleOutcome::Completed(completion) =
        turn.outcome()
    else {
        return Err(String::from("bounded guard fallback suspended"));
    };
    if completion.outcome() == expected_outcome
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("bounded guard fallback completion drifted"))
    }
}

#[test]
fn native_retry_cycle_guard_then_native_completion() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let expected_outcome = fixture.full_plan.outcome();
    let policy = NativeContinuationRetryPolicy::new(
        2,
        NativeContinuationRetryFallback::complete(),
    );
    let request = windows_retry_cycle_request(
        policy,
        fixture.suspension,
        0,
        HostIsa::X86_64,
    );
    let mut adapter = native_executable_adapter(968, 0xe2_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::GuardMiss,
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = execute_native_continuation_retry_cycle(
        request,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| format!("guard-completion retry cycle: {failure:?}"))?;
    let NativeContinuationRetryCycleOutcome::NativeCompletion(completion) =
        outcome
    else {
        return Err(String::from(
            "guard-completion cycle did not complete native",
        ));
    };
    if completion.attempts() == 2
        && completion.completion().outcome() == expected_outcome
        && completion.completion().retry_steps() == 2
        && completion.completion().state().memory() == expected.final_memory
        && completion.completion().state().io().output()
            == expected.final_output
        && runner.calls == 3
    {
        Ok(())
    } else {
        Err(String::from("guard-completion cycle evidence drifted"))
    }
}

#[test]
fn native_retry_cycle_stops_on_runner_failure() -> Result<(), String> {
    let fixture = native_retry_fixture(HostIsa::AArch64, 0)?;
    let policy = NativeContinuationRetryPolicy::new(
        3,
        NativeContinuationRetryFallback::complete(),
    );
    let request = windows_retry_cycle_request(
        policy,
        fixture.suspension,
        0,
        HostIsa::AArch64,
    );
    let mut adapter = native_executable_adapter(969, 0xe3_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::FailureAfterMutation,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = execute_native_continuation_retry_cycle(
        request,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| format!("runner-failure retry cycle: {failure:?}"))?;
    let NativeContinuationRetryCycleOutcome::NativeFailure(turn) = outcome
    else {
        return Err(String::from("runner-failure cycle retried or completed"));
    };
    if turn.attempt() != 1
        || turn.failure().completed_steps() != 0
        || turn.failure().resume_index() != 0
        || runner.calls != 1
    {
        return Err(String::from("runner-failure cycle evidence drifted"));
    }
    let NativeContinuationRetryDisposition::Resumable(resumption) =
        turn.disposition()
    else {
        return Err(String::from("runner-failure cycle lost fallback"));
    };
    if resumption.resume_index() == 0 && resumption.retry_steps() == 0 {
        Ok(())
    } else {
        Err(String::from("runner-failure fallback progress drifted"))
    }
}

#[test]
fn native_retry_cycle_uses_format_fallback_without_attempt()
-> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let expected_outcome = fixture.full_plan.outcome();
    let policy = NativeContinuationRetryPolicy::new(
        3,
        NativeContinuationRetryFallback::sliced(nonzero_test_limit(
            1,
            "cycle format fallback",
        )?),
    );
    let request =
        linux_x86_64_retry_cycle_request(policy, fixture.suspension, 0);
    let mut adapter = native_executable_adapter(970, 0xe4_000)?;
    let mut runner = FakeNativeSequenceRunner::new(Vec::new());
    let outcome = execute_native_continuation_retry_cycle(
        request,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| format!("format-fallback cycle: {failure:?}"))?;
    let NativeContinuationRetryCycleOutcome::Interpreter(turn) = outcome else {
        return Err(String::from("format fallback cycle executed native"));
    };
    if turn.attempts() != 0
        || !adapter.allocation_requests.is_empty()
        || runner.calls != 0
    {
        return Err(String::from("format fallback cycle counted native work"));
    }
    let NativeContinuationScheduleOutcome::Suspended(pause) =
        turn.into_outcome()
    else {
        return Err(String::from("format fallback slice completed early"));
    };
    if pause.interpreter_steps() != 1
        || pause.reason()
            != NativeContinuationScheduleStopReason::BudgetExhausted
    {
        return Err(String::from("format fallback cycle slice drifted"));
    }
    let scheduled = pause
        .resume(NativeContinuationScheduleDecision::complete_interpreter())
        .map_err(|failure| failure.to_string())?;
    let NativeContinuationScheduleOutcome::Completed(completion) = scheduled
    else {
        return Err(String::from("format fallback cycle did not complete"));
    };
    if completion.outcome() == expected_outcome
        && completion.state().memory() == expected.final_memory
        && completion.state().io().output() == expected.final_output
    {
        Ok(())
    } else {
        Err(String::from("format fallback cycle completion drifted"))
    }
}

#[test]
fn native_retry_cycle_stops_on_cleanup_failure() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::AArch64, 1)?;
    let expected_outcome = fixture.full_plan.outcome();
    let policy = NativeContinuationRetryPolicy::new(
        3,
        NativeContinuationRetryFallback::complete(),
    );
    let request = windows_retry_cycle_request(
        policy,
        fixture.suspension,
        0,
        HostIsa::AArch64,
    );
    let mut adapter =
        native_executable_adapter(971, 0xe5_000)?.with_release_failure_at(1);
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = execute_native_continuation_retry_cycle(
        request,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| format!("cleanup-failure cycle: {failure:?}"))?;
    let NativeContinuationRetryCycleOutcome::NativeFailure(turn) = outcome
    else {
        return Err(String::from("cleanup failure cycle retried or fell back"));
    };
    if turn.attempt() != 1 || runner.calls != 1 {
        return Err(String::from("cleanup failure cycle retried native work"));
    }
    let (attempt, disposition, sequence_failure) = turn.into_parts();
    let NativeContinuationRetryDisposition::Completed(completion) = disposition
    else {
        return Err(String::from("cleanup failure cycle lost completion"));
    };
    if attempt != 1
        || completion.outcome() != expected_outcome
        || completion.state().memory() != expected.final_memory
        || completion.state().io().output() != expected.final_output
    {
        return Err(String::from("cleanup failure cycle completion drifted"));
    }
    let execution = (*sequence_failure)
        .into_execution_failure()
        .ok_or_else(|| String::from("cycle cleanup execution owner missing"))?;
    let release = execution
        .into_release_failure()
        .ok_or_else(|| String::from("cycle cleanup release owner missing"))?;
    release
        .retry(&mut adapter)
        .map_err(|failure| failure.to_string())
}

#[test]
fn native_retry_cycle_preserves_hard_routing_failure() -> Result<(), String> {
    let fixture = native_retry_fixture(HostIsa::X86_64, 1)?;
    let expected_state = fixture.suspension.state().clone();
    let policy = NativeContinuationRetryPolicy::new(
        3,
        NativeContinuationRetryFallback::complete(),
    );
    let request = NativeContinuationRetryCycleRequest::new(
        policy,
        fixture.suspension,
        0,
        NativeContinuationRetryHost::new(
            safe_rust_classic_capability(),
            HostOperatingSystem::Windows,
            HostIsa::X86_64,
        ),
    );
    let mut adapter = native_executable_adapter(972, 0xe6_000)?;
    let mut runner = FakeNativeSequenceRunner::new(Vec::new());
    let Err(failure) = execute_native_continuation_retry_cycle(
        request,
        &mut adapter,
        &mut runner,
    ) else {
        return Err(String::from("hard cycle routing failure was hidden"));
    };
    let retry_cycle::NativeContinuationRetryCycleFailure::Routing(
        routing_failure,
    ) = *failure
    else {
        return Err(String::from("hard cycle failure phase drifted"));
    };
    if routing_failure.error()
        != (NativeContinuationRetryRoutingError::Planning(
            NativeContinuationRetryPlanningError::Step {
                cause: NativeContinuationRetryStepPlanningError::Profile,
                index: 0,
            },
        ))
        || routing_failure
            .profile_diagnostic()
            .is_none_or(|diagnostic| {
                !diagnostic.starts_with("MALBOLGE-PROFILE-001 ")
            })
        || !adapter.allocation_requests.is_empty()
        || runner.calls != 0
    {
        return Err(String::from("hard cycle routing evidence drifted"));
    }
    let recovered = (*routing_failure).into_suspension();
    if recovered.state() == &expected_state
        && recovered.reason()
            == NativeContinuationScheduleStopReason::NativeRetry
    {
        Ok(())
    } else {
        Err(String::from("hard cycle routing lost suspension"))
    }
}

#[test]
fn leased_native_retry_completes_inserted_sequence() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::AArch64, 0)?;
    let expected_outcome = fixture.full_plan.outcome();
    let retry = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan.clone(),
    )
    .map_err(|failure| failure.error().to_string())?;
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        1,
        "leased retry capacity",
    )?);
    let (mut cache, mut adapter) = lease_fixture(limits, 980, 0xee_000)?;
    let acquisition = cache
        .ensure_plan(&mut adapter, &fixture.retry_plan)
        .map_err(|failure| failure.to_string())?;
    let operations = adapter.operations.len();
    let leased = NativeContinuationLeasedRetry::new(retry, acquisition)
        .map_err(|_failure| String::from("exact leased retry was rejected"))?;
    if leased.cache_disposition().is_hit()
        || leased.plan() != &fixture.retry_plan
    {
        return Err(String::from("inserted leased retry evidence drifted"));
    }
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let execution = leased
        .execute(&mut runner)
        .map_err(|_failure| String::from("inserted leased retry failed"))?;
    if execution.cache_disposition().is_hit()
        || execution.plan() != &fixture.retry_plan
        || adapter.operations.len() != operations
    {
        return Err(String::from("inserted leased execution touched adapter"));
    }
    let rebased = execution
        .rebase()
        .map_err(|failure| failure.error().to_string())?;
    let (disposition, cache_disposition, lease) = rebased.into_parts();
    let NativeContinuationRetryDisposition::Completed(completion) = disposition
    else {
        return Err(String::from("inserted leased retry remained resumable"));
    };
    if cache_disposition.is_hit()
        || completion.outcome() != expected_outcome
        || completion.retry_steps() != 2
        || completion.state().memory() != expected.final_memory
        || completion.state().io().output() != expected.final_output
    {
        return Err(String::from("inserted leased completion drifted"));
    }
    drop(lease);
    cache
        .release_all(&mut adapter)
        .map(|_report| ())
        .map_err(|failure| failure.to_string())
}

#[test]
fn leased_native_retry_reuses_hit_without_adapter_work() -> Result<(), String> {
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let retry = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan.clone(),
    )
    .map_err(|failure| failure.error().to_string())?;
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        1,
        "leased retry capacity",
    )?);
    let (mut cache, mut adapter) = lease_fixture(limits, 981, 0xef_000)?;
    let resident = cache
        .ensure_plan(&mut adapter, &fixture.retry_plan)
        .map_err(|failure| failure.to_string())?
        .into_lease();
    let operations = adapter.operations.len();
    let acquisition = cache
        .ensure_plan(&mut adapter, &fixture.retry_plan)
        .map_err(|failure| failure.to_string())?;
    if !acquisition.disposition().is_hit()
        || !acquisition.lease().shares_resident_with(&resident)
        || adapter.operations.len() != operations
    {
        return Err(String::from("leased retry cache hit drifted"));
    }
    let leased = NativeContinuationLeasedRetry::new(retry, acquisition)
        .map_err(|_failure| String::from("cache-hit retry binding failed"))?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let execution = leased
        .execute(&mut runner)
        .map_err(|_failure| String::from("cache-hit retry execution failed"))?;
    if !execution.cache_disposition().is_hit()
        || !execution.lease().shares_resident_with(&resident)
        || adapter.operations.len() != operations
        || runner.calls != 1
    {
        return Err(String::from("cache-hit retry execution drifted"));
    }
    drop(execution);
    drop(resident);
    cache
        .release_all(&mut adapter)
        .map(|_report| ())
        .map_err(|failure| failure.to_string())
}

#[test]
fn leased_native_retry_rebases_guard_with_live_lease() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let LeasedNativeRetryFixture {
        mut adapter,
        mut cache,
        full_plan,
        leased,
    } = leased_native_retry_fixture(HostIsa::X86_64, 1, 982, 0xf0_000)?;
    let operations = adapter.operations.len();
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let rebased = leased
        .execute(&mut runner)
        .map_err(|_failure| String::from("leased guard execution failed"))?
        .rebase()
        .map_err(|failure| failure.error().to_string())?;
    if adapter.operations.len() != operations
        || rebased.lease().key().is_empty()
    {
        return Err(String::from("leased guard touched adapter or lost lease"));
    }
    let (disposition, _cache_disposition, lease) = rebased.into_parts();
    let NativeContinuationRetryDisposition::Resumable(resumption) = disposition
    else {
        return Err(String::from("leased guard retry completed"));
    };
    if resumption.interpreter_steps() != 1
        || resumption.retry_steps() != 0
        || resumption.resume_index() != 1
    {
        return Err(String::from("leased guard progress drifted"));
    }
    let completion = complete_retry_resumption(resumption)?;
    if completion.outcome() != full_plan.outcome()
        || completion.state().memory() != expected.final_memory
        || completion.state().io().output() != expected.final_output
    {
        return Err(String::from("leased guard fallback drifted"));
    }
    release_leased_retry(&mut cache, &mut adapter, lease)
}

#[test]
fn leased_native_retry_rebases_runner_failure() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let LeasedNativeRetryFixture {
        mut adapter,
        mut cache,
        full_plan,
        leased,
    } = leased_native_retry_fixture(HostIsa::AArch64, 0, 983, 0xf1_000)?;
    let operations = adapter.operations.len();
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let Err(execution_failure) = leased.execute(&mut runner) else {
        return Err(String::from("leased runner failure was ignored"));
    };
    if execution_failure.failure().completed_steps() != 0
        || execution_failure.failure().resume_index() != 0
        || adapter.operations.len() != operations
    {
        return Err(String::from("leased runner failure evidence drifted"));
    }
    let rebased = execution_failure
        .rebase()
        .map_err(|rebase_failure| rebase_failure.error().to_string())?;
    let (disposition, loaded_failure, _cache_disposition, lease) =
        rebased.into_parts();
    if loaded_failure.completed_steps() != 0
        || loaded_failure.resume_index() != 0
    {
        return Err(String::from("rebased loaded failure drifted"));
    }
    let NativeContinuationRetryDisposition::Resumable(resumption) = disposition
    else {
        return Err(String::from("zero-progress loaded failure completed"));
    };
    let completion = complete_retry_resumption(resumption)?;
    if completion.outcome() != full_plan.outcome()
        || completion.state().memory() != expected.final_memory
        || completion.state().io().output() != expected.final_output
    {
        return Err(String::from("leased failure fallback drifted"));
    }
    release_leased_retry(&mut cache, &mut adapter, lease)
}

#[test]
fn leased_native_retry_rejects_different_lease_key() -> Result<(), String> {
    let fixture = native_retry_fixture(HostIsa::X86_64, 1)?;
    let wrong_plan = select_verified_direct_sequence(
        fixture.retry_plan.programs(),
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::AArch64,
    )
    .map_err(|error| error.to_string())?;
    let wrong_key = NativeExecutableSequenceKey::from_plan(&wrong_plan);
    let retry = NativeContinuationNativeRetry::new(
        fixture.suspension,
        fixture.retry_plan.clone(),
    )
    .map_err(|failure| failure.error().to_string())?;
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        1,
        "leased retry capacity",
    )?);
    let (mut cache, mut adapter) = lease_fixture(limits, 984, 0xf2_000)?;
    let acquisition = cache
        .ensure_plan(&mut adapter, &wrong_plan)
        .map_err(|failure| failure.to_string())?;
    let Err(failure) = NativeContinuationLeasedRetry::new(retry, acquisition)
    else {
        return Err(String::from("different leased retry key was admitted"));
    };
    if failure.error() != NativeContinuationLeasedRetryAdmissionError::LeaseKey
    {
        return Err(String::from("leased retry key rejection drifted"));
    }
    let (recovered_retry, recovered_acquisition) = (*failure).into_parts();
    if recovered_retry.plan() != &fixture.retry_plan
        || recovered_acquisition.lease().key() != &wrong_key
    {
        return Err(String::from("leased retry rejection lost owners"));
    }
    drop(recovered_acquisition.into_lease());
    cache
        .release_all(&mut adapter)
        .map(|_report| ())
        .map_err(|release| release.to_string())
}

#[test]
fn cached_native_retry_completes_inserted_sequence() -> Result<(), String> {
    let fixture = admitted_native_retry(HostIsa::AArch64, 0)?;
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        1,
        "cached retry capacity",
    )?);
    let (mut cache, mut adapter) = lease_fixture(limits, 985, 0xf3_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let execution = execute_cached_native_retry(
        &mut cache,
        &mut adapter,
        &mut runner,
        fixture.retry,
    )
    .map_err(|_failure| String::from("cached retry insertion failed"))?;
    if execution.cache_disposition().is_hit()
        || execution.plan() != &fixture.retry_plan
        || runner.calls != 2
    {
        return Err(String::from("cached retry insertion evidence drifted"));
    }
    let rebased = execution
        .rebase()
        .map_err(|failure| failure.error().to_string())?;
    let (disposition, cache_disposition, lease) = rebased.into_parts();
    let NativeContinuationRetryDisposition::Completed(completion) = disposition
    else {
        return Err(String::from("cached inserted retry remained resumable"));
    };
    if cache_disposition.is_hit()
        || completion.outcome() != fixture.full_plan.outcome()
        || completion.retry_steps() != fixture.retry_plan.len()
        || profile_state_observation(completion.state())
            != fixture.full_plan.exit()
    {
        return Err(String::from("cached inserted completion drifted"));
    }
    release_leased_retry(&mut cache, &mut adapter, lease)
}

#[test]
fn cached_native_retry_reuses_hit_without_adapter_work() -> Result<(), String> {
    let fixture = admitted_native_retry(HostIsa::X86_64, 0)?;
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        1,
        "cached retry capacity",
    )?);
    let (mut cache, mut adapter) = lease_fixture(limits, 986, 0xf4_000)?;
    drop(
        cache
            .ensure_plan(&mut adapter, &fixture.retry_plan)
            .map_err(|failure| failure.to_string())?
            .into_lease(),
    );
    let operations = adapter.operations.len();
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let execution = execute_cached_native_retry(
        &mut cache,
        &mut adapter,
        &mut runner,
        fixture.retry,
    )
    .map_err(|_failure| String::from("cached retry hit failed"))?;
    if !execution.cache_disposition().is_hit()
        || adapter.operations.len() != operations
        || runner.calls != 1
    {
        return Err(String::from("cached retry hit touched adapter"));
    }
    drop(execution);
    cache
        .release_all(&mut adapter)
        .map(|_report| ())
        .map_err(|failure| failure.to_string())
}

#[test]
fn cached_native_retry_preserves_acquisition_failure() -> Result<(), String> {
    let fixture = admitted_native_retry(HostIsa::AArch64, 0)?;
    let expected_key =
        NativeExecutableSequenceKey::from_plan(&fixture.retry_plan);
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        1,
        "cached retry capacity",
    )?);
    let mut cache = NativeExecutableSequenceLeaseCache::with_limits(limits);
    let mut adapter = native_executable_adapter(987, 0xf5_000)?
        .with_failure(FakeNativeAdapterOperation::Allocate);
    let mut runner = FakeNativeSequenceRunner::new(Vec::new());
    let Err(failure) = execute_cached_native_retry(
        &mut cache,
        &mut adapter,
        &mut runner,
        fixture.retry,
    ) else {
        return Err(String::from("cached retry load failure was ignored"));
    };
    let acquisition_evidence = failure
        .acquisition()
        .ok_or_else(|| String::from("cached acquisition owner missing"))?;
    if acquisition_evidence.failure().requested_key() != &expected_key
        || acquisition_evidence.failure().load_failure().is_none()
        || acquisition_evidence.retry().plan() != &fixture.retry_plan
        || runner.calls != 0
        || !cache.is_empty()
    {
        return Err(String::from("cached acquisition failure drifted"));
    }
    let NativeContinuationCachedRetryFailure::Acquisition(acquisition_owner) =
        *failure
    else {
        return Err(String::from("cached load failure category changed"));
    };
    let (retry, cache_failure) = (*acquisition_owner).into_parts();
    if retry.plan() == &fixture.retry_plan
        && cache_failure.requested_key() == &expected_key
    {
        Ok(())
    } else {
        Err(String::from("cached acquisition failure lost owners"))
    }
}

#[test]
fn cached_native_retry_retires_live_fifo_victim() -> Result<(), String> {
    let source = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&source, HostIsa::AArch64, 1)?;
    let second = selected_sequence_prefix(&source, HostIsa::X86_64, 1)?;
    let first_key = NativeExecutableSequenceKey::from_plan(&first);
    let second_key = NativeExecutableSequenceKey::from_plan(&second);
    let fixture = admitted_native_retry(HostIsa::AArch64, 0)?;
    let candidate_key =
        NativeExecutableSequenceKey::from_plan(&fixture.retry_plan);
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        2,
        "cached retry capacity",
    )?);
    let (mut cache, mut adapter) = lease_fixture(limits, 988, 0xf6_000)?;
    let first_lease = cache
        .ensure_plan(&mut adapter, &first)
        .map_err(|failure| failure.to_string())?
        .into_lease();
    drop(
        cache
            .ensure_plan(&mut adapter, &second)
            .map_err(|failure| failure.to_string())?
            .into_lease(),
    );
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let execution = execute_cached_native_retry(
        &mut cache,
        &mut adapter,
        &mut runner,
        fixture.retry,
    )
    .map_err(|_failure| String::from("cached retry replacement failed"))?;
    if execution.cache_disposition().evicted_keys()
        != [first_key.clone(), second_key]
        || execution.cache_disposition().retired_keys() != [first_key.clone()]
        || cache.keys().cloned().collect::<Vec<_>>() != [candidate_key.clone()]
        || cache.retired_keys().cloned().collect::<Vec<_>>()
            != [first_key.clone()]
        || adapter.release_requests.len() != 1
    {
        return Err(String::from("cached retry FIFO retirement drifted"));
    }
    drop(execution);
    let drained = cache
        .release_all(&mut adapter)
        .map_err(|failure| failure.to_string())?;
    if drained.released_keys() != [candidate_key]
        || drained.retained_keys() != [first_key]
    {
        return Err(String::from("cached retry drain evidence drifted"));
    }
    cache
        .return_lease(&mut adapter, first_lease)
        .map(|_report| ())
        .map_err(|failure| failure.to_string())
}

#[test]
fn cached_native_retry_preserves_runner_failure_lease() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = admitted_native_retry(HostIsa::X86_64, 0)?;
    let expected_key =
        NativeExecutableSequenceKey::from_plan(&fixture.retry_plan);
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        1,
        "cached retry capacity",
    )?);
    let (mut cache, mut adapter) = lease_fixture(limits, 989, 0xf7_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let failure = execute_cached_native_retry(
        &mut cache,
        &mut adapter,
        &mut runner,
        fixture.retry,
    )
    .err()
    .ok_or_else(|| String::from("cached retry runner failure was ignored"))?;
    let execution_failure = (*failure).into_execution().ok_or_else(|| {
        String::from("cached execution failure owner missing")
    })?;
    if !cached_retry_failure_matches(&execution_failure, &expected_key) {
        return Err(String::from("cached runner failure evidence drifted"));
    }
    let rebased = execution_failure
        .rebase()
        .map_err(|rebase_failure| rebase_failure.error().to_string())?;
    let (disposition, loaded_failure, _cache_disposition, lease) =
        rebased.into_parts();
    if loaded_failure.completed_steps() != 0
        || loaded_failure.resume_index() != 0
    {
        return Err(String::from("cached loaded failure drifted"));
    }
    let completion = complete_retry_resumption(retry_resumption(disposition)?)?;
    if !retry_completion_matches(
        &completion,
        fixture.full_plan.outcome(),
        &expected,
    ) {
        return Err(String::from("cached runner fallback drifted"));
    }
    release_leased_retry(&mut cache, &mut adapter, lease)
}

#[test]
fn cached_retry_cycle_reuses_unchanged_guard_suffix() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::AArch64, 0)?;
    let request = windows_cached_retry_cycle_request(
        complete_retry_policy(3),
        fixture.suspension,
        0,
        HostIsa::AArch64,
    );
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        1,
        "cached cycle capacity",
    )?);
    let (mut cache, mut adapter) = lease_fixture(limits, 990, 0xf8_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::GuardMiss,
        FakeNativeRunnerBehavior::GuardMiss,
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = execute_cached_native_retry_cycle(
        request,
        &mut cache,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| format!("cached guard cycle failed: {failure:?}"))?;
    let completion = cached_cycle_completion(outcome)?;
    assert_cached_retry_telemetry(
        completion.as_ref(),
        &CachedRetryTelemetryExpectation {
            attempts: 3,
            completed_steps: 2,
            evicted_keys: 0,
            hits: 2,
            insertions: 1,
            retired_keys: 0,
        },
    )?;
    let attempt_numbers = completion
        .native_attempts()
        .iter()
        .map(NativeContinuationCachedRetryAttempt::attempt)
        .collect::<Vec<_>>();
    if completion.attempts() != 3
        || attempt_numbers != [1, 2, 3]
        || completion.native_steps() != 2
        || runner.calls != 4
        || cache.active_len() != 1
        || completion.completion().outcome() != fixture.full_plan.outcome()
        || completion.completion().state().memory() != expected.final_memory
        || completion.completion().state().io().output()
            != expected.final_output
    {
        return Err(String::from("cached guard reuse evidence drifted"));
    }
    cache
        .release_all(&mut adapter)
        .map(|_report| ())
        .map_err(|failure| failure.to_string())
}

#[test]
fn cached_retry_cycle_inserts_progressed_suffix() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let request = windows_cached_retry_cycle_request(
        NativeContinuationRetryPolicy::new(
            2,
            NativeContinuationRetryFallback::complete(),
        ),
        fixture.suspension,
        0,
        HostIsa::X86_64,
    );
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        2,
        "cached cycle capacity",
    )?);
    let (mut cache, mut adapter) = lease_fixture(limits, 991, 0xf9_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::GuardMiss,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = execute_cached_native_retry_cycle(
        request,
        &mut cache,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| format!("cached progress cycle failed: {failure:?}"))?;
    let completion = cached_cycle_completion(outcome)?;
    assert_cached_retry_telemetry(
        completion.native_attempts(),
        &CachedRetryTelemetryExpectation {
            attempts: 2,
            completed_steps: 2,
            evicted_keys: 0,
            hits: 0,
            insertions: 2,
            retired_keys: 0,
        },
    )?;
    if completion.attempts() != 2
        || completion.native_steps() != 2
        || completion.completion().retry_steps() != 1
        || completion.completion().outcome() != fixture.full_plan.outcome()
        || completion.completion().state().memory() != expected.final_memory
        || completion.completion().state().io().output()
            != expected.final_output
        || cache.active_len() != 2
        || runner.calls != 3
    {
        return Err(String::from("cached progressed suffix evidence drifted"));
    }
    cache
        .release_all(&mut adapter)
        .map(|_report| ())
        .map_err(|failure| failure.to_string())
}

#[test]
fn cached_retry_telemetry_counts_eviction_and_retirement() -> Result<(), String>
{
    let source = direct_normative_sequence_fixture()?;
    let first = selected_sequence_prefix(&source, HostIsa::AArch64, 1)?;
    let second = selected_sequence_prefix(&source, HostIsa::X86_64, 1)?;
    let fixture = native_retry_fixture(HostIsa::AArch64, 0)?;
    let request = windows_cached_retry_cycle_request(
        complete_retry_policy(1),
        fixture.suspension,
        0,
        HostIsa::AArch64,
    );
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        2,
        "cached telemetry capacity",
    )?);
    let (mut cache, mut adapter) = lease_fixture(limits, 997, 0xff_000)?;
    let first_lease = cache
        .ensure_plan(&mut adapter, &first)
        .map_err(|failure| failure.to_string())?
        .into_lease();
    drop(
        cache
            .ensure_plan(&mut adapter, &second)
            .map_err(|failure| failure.to_string())?
            .into_lease(),
    );
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::Applied,
    ]);
    let outcome = execute_cached_native_retry_cycle(
        request,
        &mut cache,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| format!("cached telemetry cycle failed: {failure:?}"))?;
    let completion = cached_cycle_completion(outcome)?;
    assert_retirement_telemetry(completion.as_ref())?;
    drop(completion);
    cache
        .release_all(&mut adapter)
        .map(|_report| ())
        .map_err(|failure| failure.to_string())?;
    cache
        .return_lease(&mut adapter, first_lease)
        .map(|_report| ())
        .map_err(|failure| failure.to_string())
}

#[test]
fn cached_retry_cycle_falls_back_without_cache_work() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let request = windows_cached_retry_cycle_request(
        NativeContinuationRetryPolicy::new(
            0,
            NativeContinuationRetryFallback::complete(),
        ),
        fixture.suspension,
        0,
        HostIsa::X86_64,
    );
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        1,
        "cached cycle capacity",
    )?);
    let (mut cache, mut adapter) = lease_fixture(limits, 992, 0xfa_000)?;
    let mut runner = FakeNativeSequenceRunner::new(Vec::new());
    let outcome = execute_cached_native_retry_cycle(
        request,
        &mut cache,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| format!("cached fallback cycle failed: {failure:?}"))?;
    let interpreter = cached_cycle_interpreter(outcome)?;
    let NativeContinuationScheduleOutcome::Completed(completion) =
        interpreter.outcome()
    else {
        return Err(String::from("cached zero-limit fallback suspended"));
    };
    if interpreter.attempts() != 0
        || !interpreter.native_attempts().is_empty()
        || runner.calls != 0
        || !cache.is_empty()
        || !adapter.operations.is_empty()
        || completion.outcome() != fixture.full_plan.outcome()
        || completion.state().memory() != expected.final_memory
        || completion.state().io().output() != expected.final_output
    {
        Err(String::from("cached zero-limit fallback drifted"))
    } else {
        Ok(())
    }
}

#[test]
fn cached_retry_cycle_preserves_acquisition_failure() -> Result<(), String> {
    let fixture = native_retry_fixture(HostIsa::AArch64, 0)?;
    let expected_key =
        NativeExecutableSequenceKey::from_plan(&fixture.retry_plan);
    let request = windows_cached_retry_cycle_request(
        NativeContinuationRetryPolicy::new(
            2,
            NativeContinuationRetryFallback::complete(),
        ),
        fixture.suspension,
        0,
        HostIsa::AArch64,
    );
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        1,
        "cached cycle capacity",
    )?);
    let mut cache = NativeExecutableSequenceLeaseCache::with_limits(limits);
    let mut adapter = native_executable_adapter(993, 0xfb_000)?
        .with_failure(FakeNativeAdapterOperation::Allocate);
    let mut runner = FakeNativeSequenceRunner::new(Vec::new());
    let failure = execute_cached_native_retry_cycle(
        request,
        &mut cache,
        &mut adapter,
        &mut runner,
    )
    .err()
    .ok_or_else(|| String::from("cached cycle load failure was ignored"))?;
    let NativeContinuationCachedRetryCycleFailure::Cached(cached_failure) =
        failure.as_ref()
    else {
        return Err(String::from("cached cycle load failure category drifted"));
    };
    let acquisition =
        cached_failure.failure().acquisition().ok_or_else(|| {
            String::from("cached cycle acquisition owner missing")
        })?;
    if cached_failure.attempt() == 1
        && cached_failure.prior_attempts().is_empty()
        && acquisition.failure().requested_key() == &expected_key
        && acquisition.failure().load_failure().is_some()
        && acquisition.retry().plan() == &fixture.retry_plan
        && runner.calls == 0
        && cache.is_empty()
    {
        Ok(())
    } else {
        Err(String::from("cached cycle acquisition failure drifted"))
    }
}

#[test]
fn cached_retry_cycle_preserves_late_acquisition_history() -> Result<(), String>
{
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let expected_key =
        NativeExecutableSequenceKey::from_plan(&fixture.retry_plan)
            .suffix(1)
            .ok_or_else(|| {
                String::from("cached late failure suffix missing")
            })?;
    let request = windows_cached_retry_cycle_request(
        complete_retry_policy(3),
        fixture.suspension,
        0,
        HostIsa::X86_64,
    );
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        2,
        "cached cycle capacity",
    )?);
    let mut cache = NativeExecutableSequenceLeaseCache::with_limits(limits);
    let mut adapter = native_executable_adapter(995, 0xfd_000)?
        .with_failure_at(FakeNativeAdapterOperation::Allocate, 3);
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::Applied,
        FakeNativeRunnerBehavior::GuardMiss,
    ]);
    let failure = execute_cached_native_retry_cycle(
        request,
        &mut cache,
        &mut adapter,
        &mut runner,
    )
    .err()
    .ok_or_else(|| String::from("cached late load failure was ignored"))?;
    let NativeContinuationCachedRetryCycleFailure::Cached(cached_failure) =
        failure.as_ref()
    else {
        return Err(String::from("cached late load failure category drifted"));
    };
    let acquisition = cached_failure
        .failure()
        .acquisition()
        .ok_or_else(|| String::from("cached late acquisition owner missing"))?;
    let prior = cached_failure.prior_attempts();
    let first = prior
        .first()
        .ok_or_else(|| String::from("cached prior attempt missing"))?;
    if cached_failure.attempt() == 2
        && prior.len() == 1
        && first.attempt() == 1
        && first.completed_steps() == 1
        && !first.disposition().is_hit()
        && acquisition.failure().requested_key() == &expected_key
        && NativeExecutableSequenceKey::from_plan(acquisition.retry().plan())
            == expected_key
        && runner.calls == 2
        && cache.active_len() == 1
    {
        Ok(())
    } else {
        Err(String::from("cached late acquisition history drifted"))
    }
}

#[test]
fn cached_retry_cycle_preserves_initial_routing_failure() -> Result<(), String>
{
    let fixture = native_retry_fixture(HostIsa::AArch64, 0)?;
    let request = NativeContinuationCachedRetryCycleRequest::new(
        NativeContinuationRetryPolicy::new(
            2,
            NativeContinuationRetryFallback::complete(),
        ),
        fixture.suspension,
        0,
        NativeContinuationRetryHost::new(
            safe_rust_classic_capability(),
            HostOperatingSystem::Windows,
            HostIsa::AArch64,
        ),
    );
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        1,
        "cached cycle capacity",
    )?);
    let (mut cache, mut adapter) = lease_fixture(limits, 996, 0xfe_000)?;
    let mut runner = FakeNativeSequenceRunner::new(Vec::new());
    let failure = execute_cached_native_retry_cycle(
        request,
        &mut cache,
        &mut adapter,
        &mut runner,
    )
    .err()
    .ok_or_else(|| String::from("cached routing failure was ignored"))?;
    let NativeContinuationCachedRetryCycleFailure::Routing(routing_failure) =
        failure.as_ref()
    else {
        return Err(String::from("cached routing failure category drifted"));
    };
    let profile_diagnostic =
        routing_failure.profile_diagnostic().ok_or_else(|| {
            String::from("cached routing lost profile diagnostic")
        })?;
    if routing_failure.prior_attempts().is_empty()
        && profile_diagnostic.starts_with("MALBOLGE-PROFILE-001 ")
        && routing_failure.failure().to_string() == profile_diagnostic
        && routing_failure.to_string() == profile_diagnostic
        && runner.calls == 0
        && cache.is_empty()
        && adapter.operations.is_empty()
    {
        Ok(())
    } else {
        Err(String::from("cached routing failure history drifted"))
    }
}

#[test]
fn cached_retry_cycle_stops_with_runner_failure_lease() -> Result<(), String> {
    let expected = direct_normative_sequence_fixture()?;
    let fixture = native_retry_fixture(HostIsa::X86_64, 0)?;
    let expected_key =
        NativeExecutableSequenceKey::from_plan(&fixture.retry_plan);
    let request = windows_cached_retry_cycle_request(
        NativeContinuationRetryPolicy::new(
            3,
            NativeContinuationRetryFallback::complete(),
        ),
        fixture.suspension,
        0,
        HostIsa::X86_64,
    );
    let limits = NativeExecutableSequenceCacheLimits::new(nonzero_test_limit(
        1,
        "cached cycle capacity",
    )?);
    let (mut cache, mut adapter) = lease_fixture(limits, 994, 0xfc_000)?;
    let mut runner = FakeNativeSequenceRunner::new(vec![
        FakeNativeRunnerBehavior::FailureAfterMutation,
    ]);
    let outcome = execute_cached_native_retry_cycle(
        request,
        &mut cache,
        &mut adapter,
        &mut runner,
    )
    .map_err(|failure| format!("cached runner cycle failed: {failure:?}"))?;
    let native_failure = cached_cycle_native_failure(outcome)?;
    if native_failure.attempt() != 1
        || !native_failure.prior_attempts().is_empty()
        || native_failure.failure().lease().key() != &expected_key
        || runner.calls != 1
    {
        return Err(String::from("cached cycle runner failure drifted"));
    }
    let (_attempt, prior_attempts, failure) = (*native_failure).into_parts();
    let (disposition, loaded_failure, cache_disposition, lease) =
        failure.into_parts();
    if !prior_attempts.is_empty()
        || loaded_failure.completed_steps() != 0
        || loaded_failure.resume_index() != 0
        || cache_disposition.is_hit()
    {
        return Err(String::from("cached cycle loaded failure drifted"));
    }
    let completion = complete_retry_resumption(retry_resumption(disposition)?)?;
    if !retry_completion_matches(
        &completion,
        fixture.full_plan.outcome(),
        &expected,
    ) {
        return Err(String::from("cached cycle runner fallback drifted"));
    }
    release_leased_retry(&mut cache, &mut adapter, lease)
}

#[test]
fn cached_retry_telemetry_empty_slice_is_zero() {
    assert_eq!(
        summarize_cached_retry_attempts(&[]),
        Ok(NativeContinuationCachedRetryTelemetry::default()),
    );
}

#[test]
fn cached_retry_telemetry_reports_exact_step_overflow_attempt() {
    let attempts = [
        NativeContinuationCachedRetryAttempt::from_test_evidence(
            1,
            usize::MAX,
            NativeExecutableSequenceLeaseCacheDisposition::Hit,
        ),
        NativeContinuationCachedRetryAttempt::from_test_evidence(
            2,
            1,
            NativeExecutableSequenceLeaseCacheDisposition::Hit,
        ),
    ];
    assert_eq!(
        summarize_cached_retry_attempts(&attempts),
        Err(
            cached_cycle::NativeContinuationCachedRetryTelemetryError::
                CompletedSteps { attempt: 2 },
        ),
    );
}

fn cached_retry_window_telemetry(
    attempt: usize,
    completed_steps: usize,
    disposition: NativeExecutableSequenceLeaseCacheDisposition,
) -> Result<NativeContinuationCachedRetryTelemetry, String> {
    summarize_cached_retry_attempts(&[
        NativeContinuationCachedRetryAttempt::from_test_evidence(
            attempt,
            completed_steps,
            disposition,
        ),
    ])
    .map_err(|error| error.to_string())
}

#[test]
fn cached_retry_telemetry_window_starts_empty() -> Result<(), String> {
    let capacity = nonzero_test_limit(2, "telemetry window capacity")?;
    let window = NativeContinuationCachedRetryTelemetryWindow::new(capacity);
    if window.capacity() == capacity
        && window.evictions() == 0
        && window.is_empty()
        && window.last_sequence().is_none()
        && window.observations().next().is_none()
        && window.totals() == NativeContinuationCachedRetryTelemetry::default()
    {
        Ok(())
    } else {
        Err(String::from("empty telemetry window drifted"))
    }
}

#[test]
fn cached_retry_telemetry_window_aggregates_exactly() -> Result<(), String> {
    let capacity = nonzero_test_limit(2, "telemetry window capacity")?;
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(capacity);
    let hit = cached_retry_window_telemetry(
        1,
        2,
        NativeExecutableSequenceLeaseCacheDisposition::Hit,
    )?;
    let insertion = cached_retry_window_telemetry(
        1,
        3,
        NativeExecutableSequenceLeaseCacheDisposition::Inserted {
            evicted: Vec::new(),
            retired: Vec::new(),
        },
    )?;
    let first = window.append(hit).map_err(|error| error.to_string())?;
    let second = window
        .append(insertion)
        .map_err(|error| error.to_string())?;
    let totals = window.totals();
    let sequences = window
        .observations()
        .map(|observation| observation.sequence())
        .collect::<Vec<_>>();
    if first.observation().sequence() == 1
        && first.evicted().is_none()
        && second.observation().sequence() == 2
        && second.evicted().is_none()
        && second.totals() == totals
        && totals.attempts() == 2
        && totals.completed_steps() == 5
        && totals.hits() == 1
        && totals.insertions() == 1
        && totals.evicted_keys() == 0
        && totals.retired_keys() == 0
        && sequences == [1, 2]
        && window.evictions() == 0
    {
        Ok(())
    } else {
        Err(String::from("telemetry window aggregation drifted"))
    }
}

#[test]
fn cached_retry_telemetry_window_evicts_oldest_exactly() -> Result<(), String> {
    let capacity = nonzero_test_limit(2, "telemetry window capacity")?;
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(capacity);
    let hit_one = cached_retry_window_telemetry(
        1,
        1,
        NativeExecutableSequenceLeaseCacheDisposition::Hit,
    )?;
    let insertion = cached_retry_window_telemetry(
        1,
        2,
        NativeExecutableSequenceLeaseCacheDisposition::Inserted {
            evicted: Vec::new(),
            retired: Vec::new(),
        },
    )?;
    let hit_four = cached_retry_window_telemetry(
        1,
        4,
        NativeExecutableSequenceLeaseCacheDisposition::Hit,
    )?;
    let _first = window.append(hit_one).map_err(|error| error.to_string())?;
    let _second = window
        .append(insertion)
        .map_err(|error| error.to_string())?;
    let third = window.append(hit_four).map_err(|error| error.to_string())?;
    let evicted = third
        .evicted()
        .ok_or_else(|| String::from("telemetry FIFO did not evict"))?;
    let sequences = window
        .observations()
        .map(|observation| observation.sequence())
        .collect::<Vec<_>>();
    let totals = window.totals();
    if evicted.sequence() == 1
        && evicted.telemetry() == hit_one
        && third.observation().sequence() == 3
        && third.evictions() == 1
        && sequences == [2, 3]
        && totals.attempts() == 2
        && totals.completed_steps() == 6
        && totals.hits() == 1
        && totals.insertions() == 1
        && window.last_sequence() == Some(3)
    {
        Ok(())
    } else {
        Err(String::from("telemetry FIFO eviction drifted"))
    }
}

#[test]
fn cached_retry_telemetry_window_rejects_overflow_transactionally()
-> Result<(), String> {
    let capacity = nonzero_test_limit(2, "telemetry window capacity")?;
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(capacity);
    let maximum = cached_retry_window_telemetry(
        1,
        usize::MAX,
        NativeExecutableSequenceLeaseCacheDisposition::Hit,
    )?;
    let one = cached_retry_window_telemetry(
        1,
        1,
        NativeExecutableSequenceLeaseCacheDisposition::Hit,
    )?;
    let _first = window.append(maximum).map_err(|error| error.to_string())?;
    let failure = window
        .append(one)
        .err()
        .ok_or_else(|| String::from("telemetry overflow was admitted"))?;
    let expected =
        NativeContinuationCachedRetryTelemetryWindowError::AggregateOverflow {
            sequence: 2,
            counter:
                NativeContinuationCachedRetryTelemetryWindowCounter::
                    CompletedSteps,
        };
    if failure == expected
        && window.len() == 1
        && window.last_sequence() == Some(1)
        && window.evictions() == 0
        && window.totals() == maximum
        && window
            .observations()
            .next()
            .is_some_and(|observation| observation.sequence() == 1)
    {
        Ok(())
    } else {
        Err(String::from("telemetry overflow mutated the window"))
    }
}

#[test]
fn cached_retry_telemetry_window_rejects_sequence_exhaustion()
-> Result<(), String> {
    let capacity = nonzero_test_limit(1, "telemetry window capacity")?;
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(capacity);
    window.force_counters_for_test(0, u64::MAX);
    let failure = window
        .append(NativeContinuationCachedRetryTelemetry::default())
        .err()
        .ok_or_else(|| {
            String::from("telemetry sequence exhaustion was ignored")
        })?;
    if failure
        == NativeContinuationCachedRetryTelemetryWindowError::SequenceExhausted
        && window.is_empty()
        && window.last_sequence() == Some(u64::MAX)
        && window.evictions() == 0
        && window.totals() == NativeContinuationCachedRetryTelemetry::default()
    {
        Ok(())
    } else {
        Err(String::from("telemetry sequence exhaustion mutated state"))
    }
}

#[test]
fn cached_retry_telemetry_window_rejects_eviction_count_overflow()
-> Result<(), String> {
    let capacity = nonzero_test_limit(1, "telemetry window capacity")?;
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(capacity);
    let first = cached_retry_window_telemetry(
        1,
        2,
        NativeExecutableSequenceLeaseCacheDisposition::Hit,
    )?;
    let second = cached_retry_window_telemetry(
        1,
        3,
        NativeExecutableSequenceLeaseCacheDisposition::Hit,
    )?;
    let _append = window.append(first).map_err(|error| error.to_string())?;
    window.force_counters_for_test(u64::MAX, 1);
    let failure = window.append(second).err().ok_or_else(|| {
        String::from("telemetry eviction overflow was ignored")
    })?;
    let expected =
        NativeContinuationCachedRetryTelemetryWindowError::
            EvictionCountOverflow { sequence: 2 };
    if failure == expected
        && window.len() == 1
        && window.last_sequence() == Some(1)
        && window.evictions() == u64::MAX
        && window.totals() == first
        && window
            .observations()
            .next()
            .is_some_and(|observation| observation.telemetry() == first)
    {
        Ok(())
    } else {
        Err(String::from("telemetry eviction overflow mutated state"))
    }
}

#[test]
fn cached_retry_telemetry_assessment_requires_attempt_gate()
-> Result<(), String> {
    let telemetry = cached_retry_window_telemetry(
        1,
        10,
        NativeExecutableSequenceLeaseCacheDisposition::Hit,
    )?;
    let required = nonzero_test_limit(2, "telemetry assessment attempts")?;
    let thresholds =
        NativeContinuationCachedRetryTelemetryAssessmentThresholds::new(
            NativeContinuationCachedRetryTelemetryAssessmentMaximums::new(
                usize::MAX,
                usize::MAX,
                usize::MAX,
            ),
            NativeContinuationCachedRetryTelemetryAssessmentMinimums::new(
                required, 0, 0,
            ),
        );
    let assessment = assess_cached_retry_telemetry(telemetry, thresholds);
    let NativeContinuationCachedRetryTelemetryAssessment::Insufficient {
        observed_attempts,
        required_attempts,
    } = assessment
    else {
        return Err(String::from("telemetry attempt gate category drifted"));
    };
    if observed_attempts == 1 && required_attempts == required {
        Ok(())
    } else {
        Err(String::from("telemetry attempt gate drifted"))
    }
}

#[test]
fn cached_retry_telemetry_assessment_meets_inclusive_thresholds()
-> Result<(), String> {
    let attempts = [
        NativeContinuationCachedRetryAttempt::from_test_evidence(
            1,
            1,
            NativeExecutableSequenceLeaseCacheDisposition::Hit,
        ),
        NativeContinuationCachedRetryAttempt::from_test_evidence(
            2,
            2,
            NativeExecutableSequenceLeaseCacheDisposition::Inserted {
                evicted: Vec::new(),
                retired: Vec::new(),
            },
        ),
    ];
    let telemetry = summarize_cached_retry_attempts(&attempts)
        .map_err(|error| error.to_string())?;
    let required = nonzero_test_limit(2, "telemetry assessment attempts")?;
    let maximums =
        NativeContinuationCachedRetryTelemetryAssessmentMaximums::new(0, 1, 0);
    let minimums =
        NativeContinuationCachedRetryTelemetryAssessmentMinimums::new(
            required, 3, 1,
        );
    let thresholds =
        NativeContinuationCachedRetryTelemetryAssessmentThresholds::new(
            maximums, minimums,
        );
    let assessment = assess_cached_retry_telemetry(telemetry, thresholds);
    let NativeContinuationCachedRetryTelemetryAssessment::Meets {
        telemetry: assessed,
    } = assessment
    else {
        return Err(String::from("inclusive assessment category drifted"));
    };
    if assessed == telemetry
        && thresholds.maximums() == maximums
        && thresholds.minimums() == minimums
        && maximums.evicted_keys() == 0
        && maximums.insertions() == 1
        && maximums.retired_keys() == 0
        && minimums.attempts() == required
        && minimums.completed_steps() == 3
        && minimums.hits() == 1
    {
        Ok(())
    } else {
        Err(String::from("inclusive telemetry assessment drifted"))
    }
}

#[test]
fn cached_retry_telemetry_assessment_retains_all_missed_signals()
-> Result<(), String> {
    let attempts = [
        NativeContinuationCachedRetryAttempt::from_test_evidence(
            1,
            1,
            NativeExecutableSequenceLeaseCacheDisposition::Hit,
        ),
        NativeContinuationCachedRetryAttempt::from_test_evidence(
            2,
            2,
            NativeExecutableSequenceLeaseCacheDisposition::Inserted {
                evicted: Vec::new(),
                retired: Vec::new(),
            },
        ),
    ];
    let telemetry = summarize_cached_retry_attempts(&attempts)
        .map_err(|error| error.to_string())?;
    let thresholds =
        NativeContinuationCachedRetryTelemetryAssessmentThresholds::new(
            NativeContinuationCachedRetryTelemetryAssessmentMaximums::new(
                0, 0, 0,
            ),
            NativeContinuationCachedRetryTelemetryAssessmentMinimums::new(
                nonzero_test_limit(2, "telemetry assessment attempts")?,
                4,
                2,
            ),
        );
    let NativeContinuationCachedRetryTelemetryAssessment::Misses {
        telemetry: assessed,
        violations,
    } = assess_cached_retry_telemetry(telemetry, thresholds)
    else {
        return Err(String::from("telemetry misses were not retained"));
    };
    if assessed == telemetry
        && violations.contains(
            NativeContinuationCachedRetryTelemetryAssessmentSignal::
                CompletedSteps,
        )
        && violations.contains(
            NativeContinuationCachedRetryTelemetryAssessmentSignal::Hits,
        )
        && violations.contains(
            NativeContinuationCachedRetryTelemetryAssessmentSignal::Insertions,
        )
        && !violations.contains(
            NativeContinuationCachedRetryTelemetryAssessmentSignal::EvictedKeys,
        )
        && !violations.contains(
            NativeContinuationCachedRetryTelemetryAssessmentSignal::RetiredKeys,
        )
        && !violations.is_empty()
    {
        Ok(())
    } else {
        Err(String::from("telemetry miss signals drifted"))
    }
}

#[test]
fn cached_retry_telemetry_assessment_uses_window_totals() -> Result<(), String>
{
    let capacity = nonzero_test_limit(2, "telemetry window capacity")?;
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(capacity);
    let hit = cached_retry_window_telemetry(
        1,
        2,
        NativeExecutableSequenceLeaseCacheDisposition::Hit,
    )?;
    let insertion = cached_retry_window_telemetry(
        1,
        3,
        NativeExecutableSequenceLeaseCacheDisposition::Inserted {
            evicted: Vec::new(),
            retired: Vec::new(),
        },
    )?;
    let _first = window.append(hit).map_err(|error| error.to_string())?;
    let _second = window
        .append(insertion)
        .map_err(|error| error.to_string())?;
    let thresholds =
        NativeContinuationCachedRetryTelemetryAssessmentThresholds::new(
            NativeContinuationCachedRetryTelemetryAssessmentMaximums::new(
                0, 1, 0,
            ),
            NativeContinuationCachedRetryTelemetryAssessmentMinimums::new(
                nonzero_test_limit(2, "telemetry assessment attempts")?,
                5,
                1,
            ),
        );
    let assessment = assess_cached_retry_telemetry(window.totals(), thresholds);
    let NativeContinuationCachedRetryTelemetryAssessment::Meets { telemetry } =
        assessment
    else {
        return Err(String::from("window assessment category drifted"));
    };
    if telemetry == window.totals() {
        Ok(())
    } else {
        Err(String::from("window telemetry assessment drifted"))
    }
}

fn cached_retry_telemetry_snapshot_fixture()
-> Result<NativeContinuationCachedRetryTelemetryWindow, String> {
    let capacity = nonzero_test_limit(2, "telemetry snapshot capacity")?;
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(capacity);
    let summaries = [
        cached_retry_window_telemetry(
            1,
            1,
            NativeExecutableSequenceLeaseCacheDisposition::Hit,
        )?,
        cached_retry_window_telemetry(
            1,
            2,
            NativeExecutableSequenceLeaseCacheDisposition::Inserted {
                evicted: Vec::new(),
                retired: Vec::new(),
            },
        )?,
        cached_retry_window_telemetry(
            1,
            4,
            NativeExecutableSequenceLeaseCacheDisposition::Hit,
        )?,
    ];
    for summary in summaries {
        let _append =
            window.append(summary).map_err(|error| error.to_string())?;
    }
    Ok(window)
}

fn cached_retry_latency_histogram()
-> Result<NativeContinuationCachedRetryLatencyHistogram, String> {
    NativeContinuationCachedRetryLatencyHistogram::new(vec![0, 10, 100])
        .map_err(|error| error.to_string())
}

#[test]
fn cached_retry_latency_rejects_invalid_bounds() -> Result<(), String> {
    let empty = NativeContinuationCachedRetryLatencyHistogram::new(Vec::new())
        .err()
        .ok_or_else(|| String::from("empty latency bounds were admitted"))?;
    let duplicate =
        NativeContinuationCachedRetryLatencyHistogram::new(vec![1, 1])
            .err()
            .ok_or_else(|| {
                String::from("duplicate latency bounds were admitted")
            })?;
    let descending =
        NativeContinuationCachedRetryLatencyHistogram::new(vec![2, 1])
            .err()
            .ok_or_else(|| {
                String::from("descending latency bounds were admitted")
            })?;
    let expected_duplicate =
        NativeContinuationCachedRetryLatencyHistogramError::
            BoundsNotIncreasing {
                index: 1,
                previous: 1,
                observed: 1,
            };
    let expected_descending =
        NativeContinuationCachedRetryLatencyHistogramError::
            BoundsNotIncreasing {
                index: 1,
                previous: 2,
                observed: 1,
            };
    if empty == NativeContinuationCachedRetryLatencyHistogramError::BoundsEmpty
        && duplicate == expected_duplicate
        && descending == expected_descending
    {
        Ok(())
    } else {
        Err(String::from("latency bound rejection drifted"))
    }
}

#[test]
fn cached_retry_latency_records_inclusive_buckets() -> Result<(), String> {
    let mut histogram = cached_retry_latency_histogram()?;
    let samples = [0, 1, 10, 11, 100, 101];
    let mut records = Vec::new();
    for nanoseconds in samples {
        records.push(
            histogram
                .record(NativeContinuationCachedRetryLatencySample::new(
                    nanoseconds,
                ))
                .map_err(|error| error.to_string())?,
        );
    }
    let first = records
        .first()
        .copied()
        .ok_or_else(|| String::from("latency records were empty"))?;
    let last = records
        .last()
        .copied()
        .ok_or_else(|| String::from("latency records were empty"))?;
    if histogram.upper_bounds() == [0, 10, 100]
        && histogram.bucket_counts() == [1, 2, 2]
        && histogram.above_maximum() == 1
        && histogram.samples() == 6
        && histogram.total_nanoseconds() == 223
        && histogram.minimum_nanoseconds() == Some(0)
        && histogram.maximum_nanoseconds() == Some(101)
        && !histogram.is_empty()
        && first.bucket() == Some(0)
        && first.samples() == 1
        && first.total_nanoseconds() == 0
        && first.minimum_nanoseconds() == 0
        && first.maximum_nanoseconds() == 0
        && last.bucket().is_none()
        && last.samples() == 6
        && last.total_nanoseconds() == 223
        && last.minimum_nanoseconds() == 0
        && last.maximum_nanoseconds() == 101
        && NativeContinuationCachedRetryLatencySample::new(101).nanoseconds()
            == 101
    {
        Ok(())
    } else {
        Err(String::from("inclusive latency histogram drifted"))
    }
}

#[test]
fn cached_retry_latency_sample_overflow_is_transactional() -> Result<(), String>
{
    let mut histogram = cached_retry_latency_histogram()?;
    histogram.force_totals_for_test(usize::MAX, 0);
    let before = histogram.clone();
    let failure = histogram
        .record(NativeContinuationCachedRetryLatencySample::new(1))
        .err()
        .ok_or_else(|| String::from("latency sample overflow was admitted"))?;
    if failure
        == NativeContinuationCachedRetryLatencyHistogramError::
            SampleCountOverflow
        && histogram == before
    {
        Ok(())
    } else {
        Err(String::from("latency sample overflow mutated state"))
    }
}

#[test]
fn cached_retry_latency_total_overflow_is_transactional() -> Result<(), String>
{
    let mut histogram = cached_retry_latency_histogram()?;
    histogram.force_totals_for_test(0, u128::MAX);
    let before = histogram.clone();
    let failure = histogram
        .record(NativeContinuationCachedRetryLatencySample::new(1))
        .err()
        .ok_or_else(|| String::from("latency total overflow was admitted"))?;
    if failure
        == NativeContinuationCachedRetryLatencyHistogramError::
            TotalNanosecondsOverflow
        && histogram == before
    {
        Ok(())
    } else {
        Err(String::from("latency total overflow mutated state"))
    }
}

#[test]
fn cached_retry_latency_bucket_overflow_is_transactional() -> Result<(), String>
{
    let mut histogram = cached_retry_latency_histogram()?;
    if !histogram.force_bucket_for_test(1, usize::MAX) {
        return Err(String::from("latency test bucket did not exist"));
    }
    let before = histogram.clone();
    let failure = histogram
        .record(NativeContinuationCachedRetryLatencySample::new(10))
        .err()
        .ok_or_else(|| String::from("latency bucket overflow was admitted"))?;
    let expected =
        NativeContinuationCachedRetryLatencyHistogramError::
            BucketCountOverflow { bucket: Some(1) };
    if failure == expected && histogram == before {
        Ok(())
    } else {
        Err(String::from("latency bucket overflow mutated state"))
    }
}

#[test]
fn cached_retry_latency_overflow_bin_is_transactional() -> Result<(), String> {
    let mut histogram = cached_retry_latency_histogram()?;
    histogram.force_above_maximum_for_test(usize::MAX);
    let before = histogram.clone();
    let failure = histogram
        .record(NativeContinuationCachedRetryLatencySample::new(101))
        .err()
        .ok_or_else(|| {
            String::from("latency overflow-bin overflow was admitted")
        })?;
    let expected =
        NativeContinuationCachedRetryLatencyHistogramError::
            BucketCountOverflow { bucket: None };
    if failure == expected && histogram == before {
        Ok(())
    } else {
        Err(String::from("latency overflow bin mutated state"))
    }
}

#[test]
fn cached_retry_latency_merge_combines_exact_schema() -> Result<(), String> {
    let mut target = cached_retry_latency_histogram()?;
    for nanoseconds in [1, 10] {
        let _record = target
            .record(NativeContinuationCachedRetryLatencySample::new(
                nanoseconds,
            ))
            .map_err(|error| error.to_string())?;
    }
    let mut source = cached_retry_latency_histogram()?;
    for nanoseconds in [0, 11, 101] {
        let _record = source
            .record(NativeContinuationCachedRetryLatencySample::new(
                nanoseconds,
            ))
            .map_err(|error| error.to_string())?;
    }
    let record = target
        .merge(&source)
        .map_err(|error| format!("latency merge failed: {error:?}"))?;
    if target.bucket_counts() == [1, 2, 1]
        && target.above_maximum() == 1
        && target.samples() == 5
        && target.total_nanoseconds() == 123
        && target.minimum_nanoseconds() == Some(0)
        && target.maximum_nanoseconds() == Some(101)
        && record.added_samples() == 3
        && record.above_maximum() == 1
        && record.samples() == 5
        && record.total_nanoseconds() == 123
        && record.minimum_nanoseconds() == Some(0)
        && record.maximum_nanoseconds() == Some(101)
    {
        Ok(())
    } else {
        Err(String::from("exact latency merge drifted"))
    }
}

#[test]
fn cached_retry_latency_merge_empty_source_is_noop() -> Result<(), String> {
    let mut target = cached_retry_populated_latency_histogram()?;
    let source = cached_retry_latency_histogram()?;
    let before = target.clone();
    let record = target
        .merge(&source)
        .map_err(|error| format!("empty latency merge failed: {error:?}"))?;
    if target == before
        && record.added_samples() == 0
        && record.samples() == before.samples()
        && record.total_nanoseconds() == before.total_nanoseconds()
    {
        Ok(())
    } else {
        Err(String::from("empty latency merge was not a no-op"))
    }
}

#[test]
fn cached_retry_latency_merge_rejects_schema_mismatch() -> Result<(), String> {
    let mut target = cached_retry_latency_histogram()?;
    let before = target.clone();
    let short = NativeContinuationCachedRetryLatencyHistogram::new(vec![0, 10])
        .map_err(|error| error.to_string())?;
    let length_failure = target
        .merge(&short)
        .err()
        .ok_or_else(|| String::from("short latency schema was merged"))?;
    let mismatched =
        NativeContinuationCachedRetryLatencyHistogram::new(vec![0, 11, 100])
            .map_err(|error| error.to_string())?;
    let bound_failure = target
        .merge(&mismatched)
        .err()
        .ok_or_else(|| String::from("different latency schema was merged"))?;
    let expected_length =
        NativeContinuationCachedRetryLatencyMergeError::BoundsLength {
            target: 3,
            source: 2,
        };
    let expected_bound =
        NativeContinuationCachedRetryLatencyMergeError::BoundMismatch {
            index: 1,
            target: 10,
            source: 11,
        };
    if length_failure == expected_length
        && bound_failure == expected_bound
        && target == before
    {
        Ok(())
    } else {
        Err(String::from("latency schema rejection drifted"))
    }
}

#[test]
fn cached_retry_latency_merge_bucket_overflow_is_transactional()
-> Result<(), String> {
    let mut target = cached_retry_latency_histogram()?;
    if !target.force_bucket_for_test(1, usize::MAX) {
        return Err(String::from("latency merge test bucket did not exist"));
    }
    let mut source = cached_retry_latency_histogram()?;
    let _record = source
        .record(NativeContinuationCachedRetryLatencySample::new(10))
        .map_err(|error| error.to_string())?;
    let before = target.clone();
    let failure = target
        .merge(&source)
        .err()
        .ok_or_else(|| String::from("latency bucket overflow was merged"))?;
    let expected =
        NativeContinuationCachedRetryLatencyMergeError::BucketCountOverflow {
            bucket: 1,
        };
    if failure == expected && target == before {
        Ok(())
    } else {
        Err(String::from("latency merge bucket overflow mutated state"))
    }
}

#[test]
fn cached_retry_latency_merge_above_overflow_is_transactional()
-> Result<(), String> {
    let mut target = cached_retry_latency_histogram()?;
    target.force_above_maximum_for_test(usize::MAX);
    let mut source = cached_retry_latency_histogram()?;
    let _record = source
        .record(NativeContinuationCachedRetryLatencySample::new(101))
        .map_err(|error| error.to_string())?;
    let before = target.clone();
    let failure = target
        .merge(&source)
        .err()
        .ok_or_else(|| String::from("latency overflow bin was merged"))?;
    if failure
        == NativeContinuationCachedRetryLatencyMergeError::AboveMaximumOverflow
        && target == before
    {
        Ok(())
    } else {
        Err(String::from("latency merge overflow bin mutated state"))
    }
}

#[test]
fn cached_retry_latency_merge_sample_overflow_is_transactional()
-> Result<(), String> {
    let mut target = cached_retry_latency_histogram()?;
    target.force_totals_for_test(usize::MAX, 0);
    let mut source = cached_retry_latency_histogram()?;
    let _record = source
        .record(NativeContinuationCachedRetryLatencySample::new(1))
        .map_err(|error| error.to_string())?;
    let before = target.clone();
    let failure = target
        .merge(&source)
        .err()
        .ok_or_else(|| String::from("latency sample overflow was merged"))?;
    if failure
        == NativeContinuationCachedRetryLatencyMergeError::SampleCountOverflow
        && target == before
    {
        Ok(())
    } else {
        Err(String::from("latency merge sample overflow mutated state"))
    }
}

#[test]
fn cached_retry_latency_merge_total_overflow_is_transactional()
-> Result<(), String> {
    let mut target = cached_retry_latency_histogram()?;
    target.force_totals_for_test(0, u128::MAX);
    let mut source = cached_retry_latency_histogram()?;
    let _record = source
        .record(NativeContinuationCachedRetryLatencySample::new(1))
        .map_err(|error| error.to_string())?;
    let before = target.clone();
    let failure = target
        .merge(&source)
        .err()
        .ok_or_else(|| String::from("latency total overflow was merged"))?;
    if failure
        == NativeContinuationCachedRetryLatencyMergeError::
            TotalNanosecondsOverflow
        && target == before
    {
        Ok(())
    } else {
        Err(String::from("latency merge total overflow mutated state"))
    }
}

fn cached_retry_populated_latency_histogram()
-> Result<NativeContinuationCachedRetryLatencyHistogram, String> {
    let mut histogram = cached_retry_latency_histogram()?;
    for nanoseconds in [0, 1, 10, 11, 100, 101] {
        let _record = histogram
            .record(NativeContinuationCachedRetryLatencySample::new(
                nanoseconds,
            ))
            .map_err(|error| error.to_string())?;
    }
    Ok(histogram)
}

fn cached_retry_latency_snapshot_failure(
    snapshot: NativeContinuationCachedRetryLatencyHistogramSnapshot,
) -> Result<NativeContinuationCachedRetryLatencySnapshotError, String> {
    NativeContinuationCachedRetryLatencyHistogram::from_snapshot(snapshot)
        .err()
        .ok_or_else(|| String::from("forged latency snapshot was admitted"))
}

#[test]
fn cached_retry_latency_snapshot_roundtrips_exactly() -> Result<(), String> {
    let histogram = cached_retry_populated_latency_histogram()?;
    let snapshot = histogram.snapshot();
    let restored =
        NativeContinuationCachedRetryLatencyHistogram::from_snapshot(
            snapshot.clone(),
        )
        .map_err(|error| format!("latency snapshot rejected: {error:?}"))?;
    let counts = snapshot.counts();
    let range = snapshot.range();
    let parts = snapshot.clone().into_parts();
    if restored == histogram
        && snapshot.upper_bounds() == [0, 10, 100]
        && counts.bucket_counts() == [1, 2, 2]
        && counts.above_maximum() == 1
        && counts.samples() == 6
        && range.minimum_nanoseconds() == Some(0)
        && range.maximum_nanoseconds() == Some(101)
        && range.total_nanoseconds() == 223
        && parts.0 == vec![0, 10, 100]
        && parts.1 == *counts
        && parts.2 == range
    {
        Ok(())
    } else {
        Err(String::from("latency snapshot roundtrip drifted"))
    }
}

#[test]
fn cached_retry_latency_snapshot_roundtrips_empty() -> Result<(), String> {
    let histogram = cached_retry_latency_histogram()?;
    let snapshot = histogram.snapshot();
    let restored =
        NativeContinuationCachedRetryLatencyHistogram::from_snapshot(
            snapshot.clone(),
        )
        .map_err(|error| {
            format!("empty latency snapshot rejected: {error:?}")
        })?;
    if restored == histogram
        && snapshot.counts().samples() == 0
        && snapshot.range().minimum_nanoseconds().is_none()
        && snapshot.range().maximum_nanoseconds().is_none()
        && snapshot.range().total_nanoseconds() == 0
    {
        Ok(())
    } else {
        Err(String::from("empty latency snapshot roundtrip drifted"))
    }
}

#[test]
fn cached_retry_latency_snapshot_rejects_bucket_count() -> Result<(), String> {
    let snapshot = NativeContinuationCachedRetryLatencyHistogramSnapshot::new(
        vec![0, 10, 100],
        NativeContinuationCachedRetryLatencySnapshotCounts::new(
            vec![1, 2],
            1,
            4,
        ),
        NativeContinuationCachedRetryLatencySnapshotRange::new(
            Some(0),
            Some(101),
            112,
        ),
    );
    let expected =
        NativeContinuationCachedRetryLatencySnapshotError::BucketCount {
            expected: 3,
            observed: 2,
        };
    if cached_retry_latency_snapshot_failure(snapshot)? == expected {
        Ok(())
    } else {
        Err(String::from("latency snapshot bucket count drifted"))
    }
}

#[test]
fn cached_retry_latency_snapshot_rejects_sample_count() -> Result<(), String> {
    let snapshot = NativeContinuationCachedRetryLatencyHistogramSnapshot::new(
        vec![0, 10, 100],
        NativeContinuationCachedRetryLatencySnapshotCounts::new(
            vec![1, 2, 2],
            1,
            7,
        ),
        NativeContinuationCachedRetryLatencySnapshotRange::new(
            Some(0),
            Some(101),
            223,
        ),
    );
    let expected =
        NativeContinuationCachedRetryLatencySnapshotError::SampleCount {
            expected: 6,
            observed: 7,
        };
    if cached_retry_latency_snapshot_failure(snapshot)? == expected {
        Ok(())
    } else {
        Err(String::from("latency snapshot sample count drifted"))
    }
}

#[test]
fn cached_retry_latency_snapshot_rejects_empty_state() -> Result<(), String> {
    let snapshot = NativeContinuationCachedRetryLatencyHistogramSnapshot::new(
        vec![10],
        NativeContinuationCachedRetryLatencySnapshotCounts::new(vec![0], 0, 0),
        NativeContinuationCachedRetryLatencySnapshotRange::new(
            Some(0),
            None,
            0,
        ),
    );
    if cached_retry_latency_snapshot_failure(snapshot)?
        == NativeContinuationCachedRetryLatencySnapshotError::EmptyState
    {
        Ok(())
    } else {
        Err(String::from("latency snapshot empty-state drifted"))
    }
}

#[test]
fn cached_retry_latency_snapshot_rejects_extrema() -> Result<(), String> {
    let counts = NativeContinuationCachedRetryLatencySnapshotCounts::new(
        vec![0, 1, 0],
        0,
        1,
    );
    let missing = NativeContinuationCachedRetryLatencyHistogramSnapshot::new(
        vec![0, 10, 100],
        counts.clone(),
        NativeContinuationCachedRetryLatencySnapshotRange::new(None, None, 5),
    );
    let order = NativeContinuationCachedRetryLatencyHistogramSnapshot::new(
        vec![0, 10, 100],
        counts.clone(),
        NativeContinuationCachedRetryLatencySnapshotRange::new(
            Some(9),
            Some(5),
            5,
        ),
    );
    let outside = NativeContinuationCachedRetryLatencyHistogramSnapshot::new(
        vec![0, 10, 100],
        counts,
        NativeContinuationCachedRetryLatencySnapshotRange::new(
            Some(0),
            Some(5),
            5,
        ),
    );
    let expected_order =
        NativeContinuationCachedRetryLatencySnapshotError::ExtremaOrder {
            maximum: 5,
            minimum: 9,
        };
    let expected_range =
        NativeContinuationCachedRetryLatencySnapshotError::ExtremaRange {
            bucket: Some(1),
            lower: 1,
            observed: 0,
            upper: 10,
        };
    if cached_retry_latency_snapshot_failure(missing)?
        == NativeContinuationCachedRetryLatencySnapshotError::ExtremaMissing
        && cached_retry_latency_snapshot_failure(order)? == expected_order
        && cached_retry_latency_snapshot_failure(outside)? == expected_range
    {
        Ok(())
    } else {
        Err(String::from("latency snapshot extrema rejection drifted"))
    }
}

#[test]
fn cached_retry_latency_snapshot_rejects_total_range() -> Result<(), String> {
    let snapshot = NativeContinuationCachedRetryLatencyHistogramSnapshot::new(
        vec![0, 10, 100],
        NativeContinuationCachedRetryLatencySnapshotCounts::new(
            vec![0, 1, 0],
            0,
            1,
        ),
        NativeContinuationCachedRetryLatencySnapshotRange::new(
            Some(1),
            Some(10),
            11,
        ),
    );
    let expected =
        NativeContinuationCachedRetryLatencySnapshotError::TotalRange {
            minimum: 1,
            maximum: 10,
            observed: 11,
        };
    if cached_retry_latency_snapshot_failure(snapshot)? == expected {
        Ok(())
    } else {
        Err(String::from("latency snapshot total range drifted"))
    }
}

#[test]
fn cached_retry_latency_snapshot_rejects_impossible_overflow_bin()
-> Result<(), String> {
    let snapshot = NativeContinuationCachedRetryLatencyHistogramSnapshot::new(
        vec![u64::MAX],
        NativeContinuationCachedRetryLatencySnapshotCounts::new(vec![0], 1, 1),
        NativeContinuationCachedRetryLatencySnapshotRange::new(
            Some(u64::MAX),
            Some(u64::MAX),
            u128::from(u64::MAX),
        ),
    );
    let expected =
        NativeContinuationCachedRetryLatencySnapshotError::CalculationOverflow {
            bucket: None,
        };
    if cached_retry_latency_snapshot_failure(snapshot)? == expected {
        Ok(())
    } else {
        Err(String::from("impossible latency overflow bin was admitted"))
    }
}

fn cached_retry_latency_codec_failure(
    bytes: &[u8],
) -> Result<NativeContinuationCachedRetryLatencyCodecError, String> {
    decode_cached_retry_latency_snapshot(bytes)
        .err()
        .ok_or_else(|| String::from("forged latency codec bytes were admitted"))
}

fn cached_retry_latency_codec_snapshot_error(
    error: NativeContinuationCachedRetryLatencyCodecError,
) -> Option<Box<NativeContinuationCachedRetryLatencySnapshotError>> {
    match error {
        NativeContinuationCachedRetryLatencyCodecError::Snapshot(cause) => {
            Some(cause)
        },
        NativeContinuationCachedRetryLatencyCodecError::AbsentExtremaValue {
            ..
        }
        | NativeContinuationCachedRetryLatencyCodecError::EncodingRange {
            ..
        }
        | NativeContinuationCachedRetryLatencyCodecError::Flag { .. }
        | NativeContinuationCachedRetryLatencyCodecError::Length { .. }
        | NativeContinuationCachedRetryLatencyCodecError::LengthOverflow
        | NativeContinuationCachedRetryLatencyCodecError::Magic
        | NativeContinuationCachedRetryLatencyCodecError::Representation {
            ..
        }
        | NativeContinuationCachedRetryLatencyCodecError::Reserved { .. }
        | NativeContinuationCachedRetryLatencyCodecError::Version {
            ..
        } => None,
    }
}

fn cached_retry_latency_codec_fixture()
-> Result<CachedRetryLatencyCodecFixture, String> {
    let snapshot = cached_retry_populated_latency_histogram()?.snapshot();
    let bytes = encode_cached_retry_latency_snapshot(&snapshot)
        .map_err(|error| error.to_string())?;
    Ok((snapshot, bytes))
}

#[test]
fn cached_retry_latency_codec_roundtrips_canonical_bytes() -> Result<(), String>
{
    let (snapshot, bytes) = cached_retry_latency_codec_fixture()?;
    let prefix = bytes
        .get(..12)
        .ok_or_else(|| String::from("latency codec prefix was truncated"))?;
    let decoded = decode_cached_retry_latency_snapshot(&bytes)
        .map_err(|error| error.to_string())?;
    let reencoded = encode_cached_retry_latency_snapshot(&decoded)
        .map_err(|error| error.to_string())?;
    if bytes.len() == 120
        && prefix == b"MBLATN01\x01\x00\x00\x00"
        && decoded == snapshot
        && reencoded == bytes
    {
        Ok(())
    } else {
        Err(String::from("canonical latency codec roundtrip drifted"))
    }
}

#[test]
fn cached_retry_latency_codec_roundtrips_empty() -> Result<(), String> {
    let snapshot = cached_retry_latency_histogram()?.snapshot();
    let bytes = encode_cached_retry_latency_snapshot(&snapshot)
        .map_err(|error| error.to_string())?;
    let decoded = decode_cached_retry_latency_snapshot(&bytes)
        .map_err(|error| error.to_string())?;
    if bytes.len() == 120 && decoded == snapshot {
        Ok(())
    } else {
        Err(String::from("empty latency codec roundtrip drifted"))
    }
}

#[test]
fn cached_retry_latency_codec_rejects_magic() -> Result<(), String> {
    let (_snapshot, mut bytes) = cached_retry_latency_codec_fixture()?;
    let first = bytes
        .first_mut()
        .ok_or_else(|| String::from("latency codec fixture was empty"))?;
    *first = first.wrapping_add(1);
    if cached_retry_latency_codec_failure(&bytes)?
        == NativeContinuationCachedRetryLatencyCodecError::Magic
    {
        Ok(())
    } else {
        Err(String::from("latency codec magic rejection drifted"))
    }
}

#[test]
fn cached_retry_latency_codec_rejects_version_and_reserved()
-> Result<(), String> {
    let (_snapshot, bytes) = cached_retry_latency_codec_fixture()?;
    let mut version = bytes.clone();
    replace_cached_retry_codec_bytes(&mut version, 8, 2u16.to_le_bytes())?;
    let version_failure = cached_retry_latency_codec_failure(&version)?;
    let mut reserved = bytes;
    replace_cached_retry_codec_bytes(&mut reserved, 10, 1u16.to_le_bytes())?;
    let reserved_failure = cached_retry_latency_codec_failure(&reserved)?;
    let expected_version =
        NativeContinuationCachedRetryLatencyCodecError::Version { observed: 2 };
    let expected_reserved =
        NativeContinuationCachedRetryLatencyCodecError::Reserved {
            observed: 1,
        };
    if version_failure == expected_version
        && reserved_failure == expected_reserved
    {
        Ok(())
    } else {
        Err(String::from("latency codec header rejection drifted"))
    }
}

#[test]
fn cached_retry_latency_codec_rejects_flags_and_absent_values()
-> Result<(), String> {
    let (_snapshot, bytes) = cached_retry_latency_codec_fixture()?;
    let mut flag = bytes;
    replace_cached_retry_codec_bytes(&mut flag, 36, [2u8])?;
    let flag_failure = cached_retry_latency_codec_failure(&flag)?;
    let empty = cached_retry_latency_histogram()?.snapshot();
    let mut absent = encode_cached_retry_latency_snapshot(&empty)
        .map_err(|error| error.to_string())?;
    replace_cached_retry_codec_bytes(&mut absent, 40, 1u64.to_le_bytes())?;
    let absent_failure = cached_retry_latency_codec_failure(&absent)?;
    let expected_flag = NativeContinuationCachedRetryLatencyCodecError::Flag {
        maximum: false,
        observed: 2,
    };
    let expected_absent =
        NativeContinuationCachedRetryLatencyCodecError::AbsentExtremaValue {
            maximum: false,
            observed: 1,
        };
    if flag_failure == expected_flag && absent_failure == expected_absent {
        Ok(())
    } else {
        Err(String::from("latency codec extrema framing drifted"))
    }
}

#[test]
fn cached_retry_latency_codec_rejects_short_and_trailing_bytes()
-> Result<(), String> {
    let (_snapshot, bytes) = cached_retry_latency_codec_fixture()?;
    let short = bytes
        .get(..71)
        .ok_or_else(|| String::from("latency codec fixture was too short"))?;
    let short_failure = cached_retry_latency_codec_failure(short)?;
    let mut trailing = bytes;
    trailing.push(0);
    let trailing_failure = cached_retry_latency_codec_failure(&trailing)?;
    let expected_short =
        NativeContinuationCachedRetryLatencyCodecError::Length {
            expected: 72,
            observed: 71,
        };
    let expected_trailing =
        NativeContinuationCachedRetryLatencyCodecError::Length {
            expected: 120,
            observed: 121,
        };
    if short_failure == expected_short && trailing_failure == expected_trailing
    {
        Ok(())
    } else {
        Err(String::from("latency codec length rejection drifted"))
    }
}

#[test]
fn cached_retry_latency_codec_rejects_count_overflow() -> Result<(), String> {
    let (_snapshot, mut bytes) = cached_retry_latency_codec_fixture()?;
    replace_cached_retry_codec_bytes(&mut bytes, 12, u64::MAX.to_le_bytes())?;
    if cached_retry_latency_codec_failure(&bytes)?
        == NativeContinuationCachedRetryLatencyCodecError::LengthOverflow
    {
        Ok(())
    } else {
        Err(String::from("latency codec count overflow drifted"))
    }
}

#[test]
fn cached_retry_latency_codec_rejects_semantic_drift() -> Result<(), String> {
    let (_snapshot, bytes) = cached_retry_latency_codec_fixture()?;
    let mut total = bytes.clone();
    replace_cached_retry_codec_bytes(&mut total, 56, 0u128.to_le_bytes())?;
    let total_failure = cached_retry_latency_codec_failure(&total)?;
    let mut bounds = bytes;
    replace_cached_retry_codec_bytes(&mut bounds, 88, 0u64.to_le_bytes())?;
    let bound_failure = cached_retry_latency_codec_failure(&bounds)?;
    let total_matches = cached_retry_latency_codec_snapshot_error(
        total_failure,
    )
    .is_some_and(|error| {
        matches!(
            *error,
            NativeContinuationCachedRetryLatencySnapshotError::TotalRange {
                minimum: 125,
                observed: 0,
                ..
            }
        )
    });
    let bound_matches = cached_retry_latency_codec_snapshot_error(
        bound_failure,
    )
    .is_some_and(|error| {
        matches!(
            *error,
            NativeContinuationCachedRetryLatencySnapshotError::Bounds(
                NativeContinuationCachedRetryLatencyHistogramError::
                    BoundsNotIncreasing {
                        index: 1,
                        previous: 0,
                        observed: 0,
                    },
            )
        )
    });
    if total_matches && bound_matches {
        Ok(())
    } else {
        Err(String::from("latency codec semantic rejection drifted"))
    }
}

#[test]
fn cached_retry_latency_codec_rejects_invalid_snapshot_on_encode()
-> Result<(), String> {
    let snapshot = cached_retry_populated_latency_histogram()?.snapshot();
    let (bounds, counts, range) = snapshot.into_parts();
    let forged_counts = NativeContinuationCachedRetryLatencySnapshotCounts::new(
        counts.bucket_counts().to_vec(),
        counts.above_maximum(),
        counts.samples().saturating_add(1),
    );
    let forged = NativeContinuationCachedRetryLatencyHistogramSnapshot::new(
        bounds,
        forged_counts,
        range,
    );
    let failure = encode_cached_retry_latency_snapshot(&forged)
        .err()
        .ok_or_else(|| String::from("invalid latency snapshot was encoded"))?;
    let matches = cached_retry_latency_codec_snapshot_error(failure)
        .is_some_and(|error| {
            matches!(
                *error,
                NativeContinuationCachedRetryLatencySnapshotError::SampleCount {
                    expected: 6,
                    observed: 7,
                }
            )
        });
    if matches {
        Ok(())
    } else {
        Err(String::from("latency codec encoder validation drifted"))
    }
}

fn cached_retry_codec_failure(
    bytes: &[u8],
) -> Result<NativeContinuationCachedRetryTelemetryCodecError, String> {
    decode_cached_retry_telemetry_snapshot(bytes)
        .err()
        .ok_or_else(|| {
            String::from("forged telemetry codec bytes were admitted")
        })
}

fn cached_retry_codec_fixture() -> Result<CachedRetryCodecFixture, String> {
    let snapshot = cached_retry_telemetry_snapshot_fixture()?.snapshot();
    let bytes = encode_cached_retry_telemetry_snapshot(&snapshot)
        .map_err(|error| error.to_string())?;
    Ok((snapshot, bytes))
}

fn replace_cached_retry_codec_bytes<const N: usize>(
    bytes: &mut [u8],
    offset: usize,
    value: [u8; N],
) -> Result<(), String> {
    let end = offset
        .checked_add(N)
        .ok_or_else(|| String::from("codec test offset overflow"))?;
    let target = bytes
        .get_mut(offset..end)
        .ok_or_else(|| String::from("codec test offset out of range"))?;
    target.copy_from_slice(&value);
    Ok(())
}

#[test]
fn cached_retry_telemetry_codec_roundtrips_canonical_bytes()
-> Result<(), String> {
    let (snapshot, bytes) = cached_retry_codec_fixture()?;
    let prefix = bytes
        .get(..12)
        .ok_or_else(|| String::from("codec prefix was truncated"))?;
    let expected_prefix = b"MBTELM01\x01\x00\x00\x00";
    let decoded = decode_cached_retry_telemetry_snapshot(&bytes)
        .map_err(|error| error.to_string())?;
    let reencoded = encode_cached_retry_telemetry_snapshot(&decoded)
        .map_err(|error| error.to_string())?;
    if bytes.len() == 204
        && prefix == expected_prefix
        && decoded == snapshot
        && reencoded == bytes
    {
        Ok(())
    } else {
        Err(String::from("canonical telemetry codec roundtrip drifted"))
    }
}

#[test]
fn cached_retry_codec_roundtrips_empty_snapshot() -> Result<(), String> {
    let capacity = nonzero_test_limit(3, "empty codec capacity")?;
    let snapshot =
        NativeContinuationCachedRetryTelemetryWindow::new(capacity).snapshot();
    let bytes = encode_cached_retry_telemetry_snapshot(&snapshot)
        .map_err(|error| error.to_string())?;
    let decoded = decode_cached_retry_telemetry_snapshot(&bytes)
        .map_err(|error| error.to_string())?;
    if bytes.len() == 92 && decoded == snapshot {
        Ok(())
    } else {
        Err(String::from("empty telemetry codec roundtrip drifted"))
    }
}

#[test]
fn cached_retry_telemetry_codec_rejects_magic() -> Result<(), String> {
    let (_snapshot, mut bytes) = cached_retry_codec_fixture()?;
    let first = bytes
        .first_mut()
        .ok_or_else(|| String::from("codec fixture was empty"))?;
    *first = first.wrapping_add(1);
    if cached_retry_codec_failure(&bytes)?
        == NativeContinuationCachedRetryTelemetryCodecError::Magic
    {
        Ok(())
    } else {
        Err(String::from("telemetry codec magic rejection drifted"))
    }
}

#[test]
fn cached_retry_telemetry_codec_rejects_version_and_reserved()
-> Result<(), String> {
    let (_snapshot, bytes) = cached_retry_codec_fixture()?;
    let mut version = bytes.clone();
    replace_cached_retry_codec_bytes(&mut version, 8, 2u16.to_le_bytes())?;
    let version_failure = cached_retry_codec_failure(&version)?;
    let mut reserved = bytes;
    replace_cached_retry_codec_bytes(&mut reserved, 10, 1u16.to_le_bytes())?;
    let reserved_failure = cached_retry_codec_failure(&reserved)?;
    if version_failure
        == (NativeContinuationCachedRetryTelemetryCodecError::Version {
            observed: 2,
        })
        && reserved_failure
            == (NativeContinuationCachedRetryTelemetryCodecError::Reserved {
                observed: 1,
            })
    {
        Ok(())
    } else {
        Err(String::from("telemetry codec header rejection drifted"))
    }
}

#[test]
fn cached_retry_telemetry_codec_rejects_short_and_trailing_bytes()
-> Result<(), String> {
    let (_snapshot, bytes) = cached_retry_codec_fixture()?;
    let short = bytes
        .get(..91)
        .ok_or_else(|| String::from("codec fixture was too short"))?;
    let short_failure = cached_retry_codec_failure(short)?;
    let mut trailing = bytes;
    trailing.push(0);
    let trailing_failure = cached_retry_codec_failure(&trailing)?;
    let expected_short =
        NativeContinuationCachedRetryTelemetryCodecError::Length {
            expected: 92,
            observed: 91,
        };
    let expected_trailing =
        NativeContinuationCachedRetryTelemetryCodecError::Length {
            expected: 204,
            observed: 205,
        };
    if short_failure == expected_short && trailing_failure == expected_trailing
    {
        Ok(())
    } else {
        Err(String::from("telemetry codec length rejection drifted"))
    }
}

#[test]
fn cached_retry_telemetry_codec_rejects_zero_capacity() -> Result<(), String> {
    let (_snapshot, mut bytes) = cached_retry_codec_fixture()?;
    replace_cached_retry_codec_bytes(&mut bytes, 12, 0u64.to_le_bytes())?;
    if cached_retry_codec_failure(&bytes)?
        == NativeContinuationCachedRetryTelemetryCodecError::CapacityZero
    {
        Ok(())
    } else {
        Err(String::from("telemetry codec zero capacity drifted"))
    }
}

#[test]
fn cached_retry_telemetry_codec_rejects_count_overflow() -> Result<(), String> {
    let (_snapshot, mut bytes) = cached_retry_codec_fixture()?;
    replace_cached_retry_codec_bytes(&mut bytes, 36, u64::MAX.to_le_bytes())?;
    if cached_retry_codec_failure(&bytes)?
        == NativeContinuationCachedRetryTelemetryCodecError::LengthOverflow
    {
        Ok(())
    } else {
        Err(String::from("telemetry codec count overflow drifted"))
    }
}

#[test]
fn cached_retry_telemetry_codec_rejects_total_drift() -> Result<(), String> {
    let (_snapshot, mut bytes) = cached_retry_codec_fixture()?;
    replace_cached_retry_codec_bytes(&mut bytes, 52, 8u64.to_le_bytes())?;
    let failure = cached_retry_codec_failure(&bytes)?;
    let expected = NativeContinuationCachedRetryTelemetryCodecError::Snapshot(
        NativeContinuationCachedRetryTelemetrySnapshotError::Totals,
    );
    if failure == expected {
        Ok(())
    } else {
        Err(String::from("telemetry codec total rejection drifted"))
    }
}

#[test]
fn cached_retry_telemetry_codec_rejects_sequence_drift() -> Result<(), String> {
    let (_snapshot, mut bytes) = cached_retry_codec_fixture()?;
    replace_cached_retry_codec_bytes(&mut bytes, 92, 1u64.to_le_bytes())?;
    let failure = cached_retry_codec_failure(&bytes)?;
    let snapshot_error =
        NativeContinuationCachedRetryTelemetrySnapshotError::FirstSequence {
            expected: 2,
            observed: 1,
        };
    let expected = NativeContinuationCachedRetryTelemetryCodecError::Snapshot(
        snapshot_error,
    );
    if failure == expected {
        Ok(())
    } else {
        Err(String::from("telemetry codec sequence rejection drifted"))
    }
}

#[test]
fn cached_retry_telemetry_codec_rejects_invalid_snapshot_on_encode()
-> Result<(), String> {
    let snapshot = cached_retry_telemetry_snapshot_fixture()?.snapshot();
    let (capacity, _metadata, observations, totals) = snapshot.into_parts();
    let forged = NativeContinuationCachedRetryTelemetryWindowSnapshot::new(
        capacity,
        NativeContinuationCachedRetryTelemetrySnapshotMetadata::new(0, 3),
        observations,
        totals,
    );
    let failure = encode_cached_retry_telemetry_snapshot(&forged)
        .err()
        .ok_or_else(|| String::from("invalid snapshot was encoded"))?;
    let snapshot_error =
        NativeContinuationCachedRetryTelemetrySnapshotError::EvictionCount {
            expected: 1,
            observed: 0,
        };
    let expected = NativeContinuationCachedRetryTelemetryCodecError::Snapshot(
        snapshot_error,
    );
    if failure == expected {
        Ok(())
    } else {
        Err(String::from("telemetry codec encoder validation drifted"))
    }
}

#[test]
fn cached_retry_telemetry_snapshot_roundtrips_exact_window()
-> Result<(), String> {
    let window = cached_retry_telemetry_snapshot_fixture()?;
    let snapshot = window.snapshot();
    let restored = NativeContinuationCachedRetryTelemetryWindow::from_snapshot(
        snapshot.clone(),
    )
    .map_err(|error| format!("snapshot roundtrip failed: {error:?}"))?;
    if snapshot.capacity() == window.capacity()
        && snapshot.metadata().evictions() == 1
        && snapshot.metadata().last_sequence() == 3
        && snapshot.observations().len() == 2
        && snapshot.totals() == window.totals()
        && restored.snapshot() == snapshot
    {
        Ok(())
    } else {
        Err(String::from("telemetry snapshot roundtrip drifted"))
    }
}

#[test]
fn cached_retry_snapshot_rejects_retained_count() -> Result<(), String> {
    let snapshot = cached_retry_telemetry_snapshot_fixture()?.snapshot();
    let (capacity, metadata, mut observations, totals) = snapshot.into_parts();
    let duplicate = observations
        .first()
        .copied()
        .ok_or_else(|| String::from("snapshot fixture was empty"))?;
    observations.push(duplicate);
    let forged = NativeContinuationCachedRetryTelemetryWindowSnapshot::new(
        capacity,
        metadata,
        observations,
        totals,
    );
    let failure =
        NativeContinuationCachedRetryTelemetryWindow::from_snapshot(forged)
            .err()
            .ok_or_else(|| String::from("oversized snapshot was admitted"))?;
    let expected =
        NativeContinuationCachedRetryTelemetrySnapshotError::RetainedCount {
            expected: 2,
            observed: 3,
        };
    if failure == expected {
        Ok(())
    } else {
        Err(String::from("snapshot retained-count rejection drifted"))
    }
}

fn cached_retry_snapshot_failure(
    snapshot: NativeContinuationCachedRetryTelemetryWindowSnapshot,
) -> Result<NativeContinuationCachedRetryTelemetrySnapshotError, String> {
    NativeContinuationCachedRetryTelemetryWindow::from_snapshot(snapshot)
        .err()
        .ok_or_else(|| String::from("forged telemetry snapshot was admitted"))
}

#[test]
fn cached_retry_snapshot_rejects_first_sequence() -> Result<(), String> {
    let snapshot = cached_retry_telemetry_snapshot_fixture()?.snapshot();
    let (capacity, metadata, mut observations, totals) = snapshot.into_parts();
    observations.swap(0, 1);
    let forged = NativeContinuationCachedRetryTelemetryWindowSnapshot::new(
        capacity,
        metadata,
        observations,
        totals,
    );
    let failure = cached_retry_snapshot_failure(forged)?;
    let expected =
        NativeContinuationCachedRetryTelemetrySnapshotError::FirstSequence {
            expected: 2,
            observed: 3,
        };
    if failure == expected {
        Ok(())
    } else {
        Err(String::from("snapshot first-sequence rejection drifted"))
    }
}

#[test]
fn cached_retry_telemetry_snapshot_rejects_eviction_metadata()
-> Result<(), String> {
    let snapshot = cached_retry_telemetry_snapshot_fixture()?.snapshot();
    let (capacity, _metadata, observations, totals) = snapshot.into_parts();
    let forged = NativeContinuationCachedRetryTelemetryWindowSnapshot::new(
        capacity,
        NativeContinuationCachedRetryTelemetrySnapshotMetadata::new(0, 3),
        observations,
        totals,
    );
    let failure = cached_retry_snapshot_failure(forged)?;
    let expected =
        NativeContinuationCachedRetryTelemetrySnapshotError::EvictionCount {
            expected: 1,
            observed: 0,
        };
    if failure == expected {
        Ok(())
    } else {
        Err(String::from("snapshot eviction rejection drifted"))
    }
}

#[test]
fn cached_retry_telemetry_snapshot_rejects_total_drift() -> Result<(), String> {
    let snapshot = cached_retry_telemetry_snapshot_fixture()?.snapshot();
    let (capacity, metadata, observations, _totals) = snapshot.into_parts();
    let forged = NativeContinuationCachedRetryTelemetryWindowSnapshot::new(
        capacity,
        metadata,
        observations,
        NativeContinuationCachedRetryTelemetry::default(),
    );
    let failure = cached_retry_snapshot_failure(forged)?;
    if failure == NativeContinuationCachedRetryTelemetrySnapshotError::Totals {
        Ok(())
    } else {
        Err(String::from("snapshot totals rejection drifted"))
    }
}

#[test]
fn cached_retry_telemetry_snapshot_roundtrips_empty_window()
-> Result<(), String> {
    let capacity = nonzero_test_limit(2, "telemetry snapshot capacity")?;
    let window = NativeContinuationCachedRetryTelemetryWindow::new(capacity);
    let snapshot = window.snapshot();
    let restored = NativeContinuationCachedRetryTelemetryWindow::from_snapshot(
        snapshot.clone(),
    )
    .map_err(|error| format!("empty snapshot failed: {error:?}"))?;
    if snapshot.metadata()
        == NativeContinuationCachedRetryTelemetrySnapshotMetadata::default()
        && snapshot.observations().is_empty()
        && snapshot.totals()
            == NativeContinuationCachedRetryTelemetry::default()
        && restored.snapshot() == snapshot
    {
        Ok(())
    } else {
        Err(String::from("empty telemetry snapshot drifted"))
    }
}

#[test]
fn cached_retry_telemetry_window_reconfigures_expansion() -> Result<(), String>
{
    let mut window = cached_retry_telemetry_snapshot_fixture()?;
    let original_totals = window.totals();
    let same = window
        .reconfigure_capacity(window.capacity())
        .map_err(|error| error.to_string())?;
    let expanded_capacity =
        nonzero_test_limit(4, "telemetry expanded capacity")?;
    let expanded = window
        .reconfigure_capacity(expanded_capacity)
        .map_err(|error| error.to_string())?;
    let next = cached_retry_window_telemetry(
        1,
        5,
        NativeExecutableSequenceLeaseCacheDisposition::Hit,
    )?;
    let appended = window.append(next).map_err(|error| error.to_string())?;
    if same.previous_capacity() == same.current_capacity()
        && same.removed().is_empty()
        && same.totals() == original_totals
        && expanded.previous_capacity().get() == 2
        && expanded.current_capacity() == expanded_capacity
        && expanded.evictions() == 1
        && expanded.removed().is_empty()
        && expanded.totals() == original_totals
        && appended.evicted().is_none()
        && appended.observation().sequence() == 4
        && window.len() == 3
        && window.evictions() == 1
        && NativeContinuationCachedRetryTelemetryWindow::from_snapshot(
            window.snapshot(),
        )
        .is_ok()
    {
        Ok(())
    } else {
        Err(String::from("telemetry capacity expansion drifted"))
    }
}

#[test]
fn cached_retry_telemetry_window_reconfigures_shrink_and_continuation()
-> Result<(), String> {
    let mut window = cached_retry_telemetry_snapshot_fixture()?;
    let capacity = nonzero_test_limit(1, "telemetry shrunk capacity")?;
    let shrunk = window
        .reconfigure_capacity(capacity)
        .map_err(|error| error.to_string())?;
    let removed = shrunk
        .removed()
        .first()
        .copied()
        .ok_or_else(|| String::from("telemetry shrink removed nothing"))?;
    let retained = window
        .observations()
        .next()
        .copied()
        .ok_or_else(|| String::from("telemetry shrink retained nothing"))?;
    let next = cached_retry_window_telemetry(
        1,
        5,
        NativeExecutableSequenceLeaseCacheDisposition::Hit,
    )?;
    let appended = window.append(next).map_err(|error| error.to_string())?;
    if shrunk.previous_capacity().get() == 2
        && shrunk.current_capacity() == capacity
        && removed.sequence() == 2
        && retained.sequence() == 3
        && shrunk.evictions() == 2
        && shrunk.totals() == retained.telemetry()
        && appended.evicted() == Some(retained)
        && appended.observation().sequence() == 4
        && appended.evictions() == 3
        && window.snapshot().metadata().evictions() == 3
        && window.snapshot().metadata().last_sequence() == 4
        && NativeContinuationCachedRetryTelemetryWindow::from_snapshot(
            window.snapshot(),
        )
        .is_ok()
    {
        Ok(())
    } else {
        Err(String::from("telemetry capacity shrink drifted"))
    }
}

#[test]
fn cached_retry_telemetry_window_reconfiguration_overflow_is_transactional()
-> Result<(), String> {
    let mut window = cached_retry_telemetry_snapshot_fixture()?;
    let original_capacity = window.capacity();
    let original_totals = window.totals();
    let original_observations =
        window.observations().copied().collect::<Vec<_>>();
    window.force_counters_for_test(u64::MAX, 3);
    let capacity = nonzero_test_limit(1, "telemetry shrunk capacity")?;
    let failure =
        window.reconfigure_capacity(capacity).err().ok_or_else(|| {
            String::from("telemetry shrink overflow was admitted")
        })?;
    let expected =
        CachedRetryTelemetryWindowError::EvictionCountOverflow { sequence: 3 };
    if failure == expected
        && window.capacity() == original_capacity
        && window.evictions() == u64::MAX
        && window.last_sequence() == Some(3)
        && window.totals() == original_totals
        && window.observations().copied().collect::<Vec<_>>()
            == original_observations
    {
        Ok(())
    } else {
        Err(String::from("telemetry shrink overflow mutated state"))
    }
}

#[test]
fn cached_retry_snapshot_rejects_empty_metadata() -> Result<(), String> {
    let capacity = nonzero_test_limit(1, "telemetry snapshot capacity")?;
    let forged = NativeContinuationCachedRetryTelemetryWindowSnapshot::new(
        capacity,
        NativeContinuationCachedRetryTelemetrySnapshotMetadata::new(1, 1),
        Vec::new(),
        NativeContinuationCachedRetryTelemetry::default(),
    );
    let failure = cached_retry_snapshot_failure(forged)?;
    let expected =
        NativeContinuationCachedRetryTelemetrySnapshotError::EmptyMetadata {
            evictions: 1,
            last_sequence: 1,
        };
    if failure == expected {
        Ok(())
    } else {
        Err(String::from("snapshot empty-metadata rejection drifted"))
    }
}

#[test]
fn cached_retry_snapshot_rejects_internal_sequence_gap() -> Result<(), String> {
    let capacity = nonzero_test_limit(2, "telemetry snapshot capacity")?;
    let summary = NativeContinuationCachedRetryTelemetry::default();
    let observations = vec![
        NativeContinuationCachedRetryTelemetryObservation::new(1, summary),
        NativeContinuationCachedRetryTelemetryObservation::new(3, summary),
    ];
    let forged = NativeContinuationCachedRetryTelemetryWindowSnapshot::new(
        capacity,
        NativeContinuationCachedRetryTelemetrySnapshotMetadata::new(0, 2),
        observations,
        summary,
    );
    let failure = cached_retry_snapshot_failure(forged)?;
    let expected =
        NativeContinuationCachedRetryTelemetrySnapshotError::SequenceGap {
            index: 1,
            expected: 2,
            observed: 3,
        };
    if failure == expected {
        Ok(())
    } else {
        Err(String::from("snapshot sequence-gap rejection drifted"))
    }
}

#[test]
fn cached_retry_snapshot_rejects_aggregate_overflow() -> Result<(), String> {
    let capacity = nonzero_test_limit(2, "telemetry snapshot capacity")?;
    let maximum = cached_retry_window_telemetry(
        1,
        usize::MAX,
        NativeExecutableSequenceLeaseCacheDisposition::Hit,
    )?;
    let one = cached_retry_window_telemetry(
        1,
        1,
        NativeExecutableSequenceLeaseCacheDisposition::Hit,
    )?;
    let observations = vec![
        NativeContinuationCachedRetryTelemetryObservation::new(1, maximum),
        NativeContinuationCachedRetryTelemetryObservation::new(2, one),
    ];
    let forged = NativeContinuationCachedRetryTelemetryWindowSnapshot::new(
        capacity,
        NativeContinuationCachedRetryTelemetrySnapshotMetadata::new(0, 2),
        observations,
        NativeContinuationCachedRetryTelemetry::default(),
    );
    let failure = cached_retry_snapshot_failure(forged)?;
    let aggregate = CachedRetryTelemetryWindowError::AggregateOverflow {
        sequence: 2,
        counter:
            NativeContinuationCachedRetryTelemetryWindowCounter::CompletedSteps,
    };
    let expected =
        NativeContinuationCachedRetryTelemetrySnapshotError::Aggregate(
            aggregate,
        );
    if failure == expected {
        Ok(())
    } else {
        Err(String::from("snapshot aggregate rejection drifted"))
    }
}
