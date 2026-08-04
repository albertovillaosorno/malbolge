// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
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

#[path = "../src/runtime/tiered-execution/application/scheduler.rs"]
pub mod continuation_scheduler;
#[path = "../src/runtime/tiered-execution/adapter-outbound/cache/main.rs"]
pub mod execution_cache;
#[path = "../src/runtime/tiered-execution/domain/ir/main.rs"]
pub mod execution_ir;
#[path = "../src/runtime/tiered-execution/adapter-outbound/native/main.rs"]
pub mod execution_native;
#[path = "../src/runtime/tiered-execution/application/interpreter_handoff.rs"]
pub mod interpreter_handoff;
#[path = "../src/runtime/tiered-execution/application/native_retry.rs"]
pub mod native_retry;
#[path = "../src/runtime/tiered-execution/application/retry_planner.rs"]
pub mod retry_planner;
#[path = "../src/runtime/tiered-execution/application/retry_policy.rs"]
pub mod retry_policy;

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::fs::{create_dir_all, read, remove_dir_all, write};
use std::num::NonZeroUsize;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::str::from_utf8;
use std::sync::Arc;
use std::thread;

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
use execution_ir::{
    EFFECT_IR_VERSION, EffectOp, MemoryLiveIn, RegionEffectProgram,
    StepProgramProjectionError, TargetProfileRequirement,
};
use execution_native::{
    CLANG_C23_BOOTSTRAP_BACKEND_ID, CLANG_C23_BOOTSTRAP_BACKEND_REVISION,
    CachedPreflightedExecutionTier, CoffAdmissionError,
    DIRECT_CRAZY_BACKEND_ID, DIRECT_CRAZY_BACKEND_REVISION,
    DIRECT_DEOPT_BACKEND_ID, DIRECT_DEOPT_BACKEND_REVISION,
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
    DirectHaltFetchError, DirectHaltRegistersError, DirectHost,
    DirectInitialHaltError, DirectInputError, DirectJumpCodeError,
    DirectJumpDataError, DirectNativeKind, DirectNoOperationError,
    DirectNonGraphicalError, DirectOutputError, DirectRotateError,
    DirectSelectionError, DirectSequenceError, NATIVE_REGION_ABI_REVISION,
    NATIVE_REGION_ACCUMULATOR_OFFSET, NATIVE_REGION_CODE_POINTER_OFFSET,
    NATIVE_REGION_DATA_POINTER_OFFSET, NATIVE_REGION_INPUT_CONSUMED_OFFSET,
    NATIVE_REGION_INPUT_LEN_OFFSET, NATIVE_REGION_INPUT_OFFSET,
    NATIVE_REGION_MEMORY_OFFSET, NATIVE_REGION_MEMORY_WORDS_OFFSET,
    NATIVE_REGION_OUTPUT_CAPACITY_OFFSET, NATIVE_REGION_OUTPUT_LEN_OFFSET,
    NATIVE_REGION_OUTPUT_OFFSET, NATIVE_REGION_STATE_SIZE,
    NATIVE_REGION_TERMINATION_OFFSET, NativeArtifactError,
    NativeExecutableAllocationRequest, NativeExecutableCodeCopyReport,
    NativeExecutableExecutionPhase, NativeExecutableInvocationBindingError,
    NativeExecutableLifecycleError, NativeExecutableLoadPhase,
    NativeExecutableMappingId, NativeExecutableMappingReport,
    NativeExecutableMemoryAdapter, NativeExecutableOperationEvidenceError,
    NativeExecutablePermission, NativeExecutableReleaseRequest,
    NativeExecutableRunner, NativeExecutableSequenceCache,
    NativeExecutableSequenceCacheCapacityError,
    NativeExecutableSequenceCacheDisposition,
    NativeExecutableSequenceCacheLimits, NativeExecutableSequenceKey,
    NativeExecutableSequenceLease, NativeExecutableSequenceLeaseCache,
    NativeExecutableSequenceLeaseCacheAcquisition,
    NativeExecutableSequenceLeaseCacheDisposition,
    NativeExecutableSequenceLeaseCacheInvalidation,
    NativeInstructionSyncReport, NativeInstructionSyncRequest,
    NativeInterpreterContinuation, NativeInterpreterContinuationError,
    NativeInterpreterContinuationReason, NativeLoadedSequenceAdmissionError,
    NativeRegionBuffers, NativeRegionCallFrame, NativeRegionCallFrameError,
    NativeRegionInvocationError, NativeRegionInvocationOutcome,
    NativeRegionMutationSurface, NativeRegionStatus,
    NativeSequenceExecutionOutcome, NativeTerminationTag,
    PreflightedExecutionTier, PreparedNativeExecutableInvocation,
    PreparedNativeRegionInvocation, PreparedVerifiedDirectInvocation,
    ReadyNativeExecutable, ReadyNativeExecutableSequence,
    StagedNativeExecutable, UntrustedNativeObjectArtifact,
    VerifiedDirectInvocationError, VerifiedDirectLoadError,
    VerifiedDirectLoadImage, VerifiedDirectNativeCache,
    VerifiedDirectSequencePlan, emit_direct_crazy_coff, emit_direct_deopt_coff,
    emit_direct_halt_fetch_coff, emit_direct_halt_registers_coff,
    emit_direct_initial_halt_coff, emit_direct_input_coff,
    emit_direct_jump_code_coff, emit_direct_jump_data_coff,
    emit_direct_no_operation_coff, emit_direct_non_graphical_coff,
    emit_direct_output_coff, emit_direct_rotate_coff,
    execute_cached_verified_native_sequence,
    execute_loaded_cached_verified_native_sequence,
    execute_loaded_verified_native_sequence, execute_verified_native,
    execute_verified_native_sequence, load_cached_verified_native_sequence,
    load_native_executable, load_verified_native_sequence, lower_clang_c23,
    release_native_executable, release_native_executable_sequence,
    select_cached_preflighted_execution_tier,
    select_cached_verified_direct_sequence, select_preflighted_execution_tier,
    select_verified_direct_native, select_verified_direct_sequence,
    structurally_admit_coff, verify_direct_crazy, verify_direct_deopt_stub,
    verify_direct_halt_fetch, verify_direct_halt_registers,
    verify_direct_initial_halt, verify_direct_input, verify_direct_jump_code,
    verify_direct_jump_data, verify_direct_no_operation,
    verify_direct_non_graphical, verify_direct_output, verify_direct_rotate,
};
use interpreter_handoff::{
    NativeInterpreterHandoff, NativeInterpreterHandoffAdmissionError,
    NativeInterpreterHandoffBudgetOutcome,
    NativeInterpreterHandoffExecutionCause,
};
use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileMachineIoState,
    ProfileMachineObservation, ProfileMachineState, ProfileMemoryDelta,
    ProfileMemoryRead, ProfileMemoryWrite, ProfileRegisters,
    ProfileRequirementErrorKind, ProfileStepTrace, RunOutcome, Termination,
    TraceInput, current_profile, decode_profile_instruction,
    historical_profile, preflight_profile, preflight_runtime_requirement,
    safe_rust_classic_capability, safe_rust_profiled_capability,
};
use native_retry::{
    NativeContinuationNativeRetry, NativeContinuationRetryAdmissionError,
    NativeContinuationRetryDisposition,
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
                request.byte_len()
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
    let mut bytes = Vec::new();
    bytes.extend_from_slice(b"MBPF");
    bytes.extend_from_slice(&3u16.to_le_bytes());
    bytes.extend_from_slice(&0u16.to_le_bytes());
    push_bytes(&mut bytes, program.profile_id.as_bytes())?;
    push_bytes(&mut bytes, program.profile_fingerprint.as_bytes())?;
    push_bytes(&mut bytes, program.profile_requirement.version.as_bytes())?;
    bytes.extend_from_slice(&feature_count.to_le_bytes());
    for feature in &program.profile_requirement.features {
        push_bytes(&mut bytes, feature.as_bytes())?;
    }
    bytes.push(program.profile_requirement.word_trits);
    bytes.extend_from_slice(
        &program.profile_requirement.memory_words.to_le_bytes(),
    );
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

fn current_profile_requirement() -> TargetProfileRequirement {
    TargetProfileRequirement::from_descriptor(current_profile())
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
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
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
    renamed.profile_id = String::from("malbolge-2026.2-alias");
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
    let current = current_profile();
    let Err(canonical) = preflight_profile(
        current,
        current.memory_words(),
        safe_rust_classic_capability(),
    ) else {
        return Err(String::from(
            "classic runtime unexpectedly admitted current profile",
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
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
        step_budget: 2,
    }
}

fn profile_invalid_native_program() -> RegionEffectProgram {
    let mut program = native_program();
    program.profile_requirement.memory_words = 1;
    program
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
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
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
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
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
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
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
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
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
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
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
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
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
                    after: 57,
                    before: 94,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 5, value: 94 }],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-input-byte-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
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
                    after: 57,
                    before: 94,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 5, value: 94 }],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-input-eof-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
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
                    after: 68,
                    before: 112,
                }),
            },
            output: Some(0xa8),
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 5, value: 112 }],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-output-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
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
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
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
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
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
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
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

#[test]
fn tier_planner_preserves_profile_errors_before_fallback() -> Result<(), String>
{
    let current = direct_initial_halt_program();
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
        "MALBOLGE-PROFILE-002 profile=malbolge-2026.2 version=2026.2 ",
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
    let current = current_profile();
    let Err(canonical) = preflight_profile(
        current,
        current.memory_words(),
        safe_rust_classic_capability(),
    ) else {
        return Err(String::from("canonical current profile was admitted"));
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
        .value = 112;
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
    renamed_program.profile_id = String::from("malbolge-2026.2-alias");
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
    if !source.contains("/* Profile ID: malbolge-2026.2 */") {
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
fn native_bootstrap_compiles_real_x86_64_and_aarch64_coff_objects()
-> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let clang = root.join(".dependencies/llvm/22.1.8/bin/clang.exe");
    if !clang.is_file() {
        return Err(format!("pinned Clang missing: {}", clang.display()));
    }
    let temporary = native_test_directory(root);
    if temporary.exists() {
        remove_dir_all(&temporary)
            .map_err(|error| format!("native temp cleanup: {error}"))?;
    }
    create_dir_all(&temporary)
        .map_err(|error| format!("native temp create: {error}"))?;

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
        check_compiled_coff_case(&clang, &temporary, &program, case)?;
    }
    remove_dir_all(&temporary)
        .map_err(|error| format!("native temp final cleanup: {error}"))?;
    Ok(())
}

fn check_compiled_coff_case(
    clang: &Path,
    temporary: &Path,
    program: &RegionEffectProgram,
    case: CoffCompileCase,
) -> Result<(), String> {
    let candidate = lower_clang_c23(program, native_target(case.isa))
        .map_err(|error| error.to_string())?;
    let stem = match case.isa {
        HostIsa::X86_64 => "x86_64",
        HostIsa::AArch64 => "aarch64",
    };
    let source_path = temporary.join(format!("{stem}.c"));
    let object_path = temporary.join(format!("{stem}.obj"));
    write(&source_path, candidate.source().as_bytes())
        .map_err(|error| format!("native source write: {error}"))?;
    compile_native_object(
        clang,
        candidate.target_triple(),
        &source_path,
        &object_path,
    )?;
    let object = read(&object_path)
        .map_err(|error| format!("native object read: {error}"))?;
    let artifact =
        UntrustedNativeObjectArtifact::from_compiler_output(&candidate, object)
            .map_err(|error| error.to_string())?;
    if artifact.key() != candidate.key()
        || artifact.target_triple() != candidate.target_triple()
    {
        return Err(String::from("native object lost source identity"));
    }
    if artifact.object().get(..2) != Some(case.expected_machine.as_slice()) {
        return Err(format!("unexpected COFF machine for {stem}"));
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
        check_rejected_coff_mutations(&candidate, &artifact)?;
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

fn native_test_directory(root: &Path) -> PathBuf {
    root.join(".temp/native-bootstrap-tests")
}

fn compile_native_object(
    clang: &Path,
    target: &str,
    source: &Path,
    object: &Path,
) -> Result<(), String> {
    let output = Command::new(clang)
        .args([
            "-std=c23",
            "-ffreestanding",
            "-nostdinc",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-O2",
            "-c",
            "-target",
            target,
        ])
        .arg(source)
        .arg("-o")
        .arg(object)
        .output()
        .map_err(|error| format!("native Clang launch failed: {error}"))?;
    if output.status.success() {
        return Ok(());
    }
    Err(format!(
        "native Clang failed: {}",
        String::from_utf8_lossy(&output.stderr)
    ))
}

fn direct_normative_sequence_state() -> Result<ProfileMachineState, String> {
    let base =
        ProfileMachine::from_source(current_profile(), b"(=%`qL", Vec::new())
            .map_err(|error| format!("direct sequence base load: {error}"))?;
    let mut memory = base.snapshot_state().memory().to_vec();
    *memory
        .get_mut(5)
        .ok_or_else(|| String::from("direct sequence code cell 5 missing"))? =
        34;
    let output_cell = (33u32..=126u32)
        .find(|cell| decode_profile_instruction(*cell, 6) == Some(b'/'))
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
        || second_trace.decoded != Some(b'/')
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
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
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
    memory[5] = 112;
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
        && memory[5] == 68
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
                expected: 112,
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
        && memory[5] == 68
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
        && memory[5] == 68
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
        || memory[5] != 68
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
    let policy = NativeContinuationRetryPolicy::new(
        1,
        NativeContinuationRetryFallback::complete(),
    );
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
