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
//   - Hardware-neutral optional batch execution attempts with CPU fallback.
// - Must-Not:
//   - Name CUDA/ROCm APIs or make optional backend failure guest-visible.
// - Allows:
//   - Inputs: validated classic/profile machine views and bounded step budgets.
//   - Outputs: completed checkpoints or deterministic scalar fallback results.
//   - Side effects: backend-defined host work over immutable request views.
// - Split-When:
//   - Split when asynchronous backend submission requires a separate lifecycle.
// - Merge-When:
//   - Merge when optional backend routing becomes identical to CPU scheduling.
// - Summary:
//   - Routes prepared VM batches through replaceable best-effort backends.
// - Description:
//   - Keeps original CPU states untouched until a backend completion is valid.
// - Usage:
//   - Used by product batch callers that opt into replaceable acceleration.
// - Defaults:
//   - Sequential safe-Rust execution remains the mandatory semantic fallback.
//

//! Hardware-neutral best-effort batch execution with deterministic CPU
//! fallback.

use super::{
    BatchRequest, BatchResult, BuiltProfileRequest, BuiltRequest,
    ProfileBatchRequest, ProfileBatchResult, execute_built,
    execute_profile_built,
};
use crate::{
    ExecutionMachine, MachineState, ProfileMachine, ProfileMachineState,
    RunOutcome, Termination,
};

/// Actual execution origin recorded for one product-routed batch item.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BatchExecutionOrigin {
    /// A complete optional-backend checkpoint was accepted.
    Backend,
    /// Safe Rust rejected source/profile admission before backend submission.
    SafeRustAdmissionRejection,
    /// The request was valid but executed by safe Rust after backend fallback.
    SafeRustFallback,
}

/// Input-ordered execution-origin evidence for one routed batch call.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BatchExecutionReport {
    origins: Vec<BatchExecutionOrigin>,
}

impl BatchExecutionReport {
    /// Returns the number of requests rejected before backend submission.
    #[must_use]
    pub fn admission_rejection_count(&self) -> usize {
        self.origins
            .iter()
            .filter(|origin| {
                **origin == BatchExecutionOrigin::SafeRustAdmissionRejection
            })
            .count()
    }

    /// Returns the number of items completed by the optional backend.
    #[must_use]
    pub fn backend_count(&self) -> usize {
        self.origins
            .iter()
            .filter(|origin| **origin == BatchExecutionOrigin::Backend)
            .count()
    }

    /// Returns the number of valid items executed by safe-Rust fallback.
    #[must_use]
    pub fn fallback_count(&self) -> usize {
        self.origins
            .iter()
            .filter(|origin| **origin == BatchExecutionOrigin::SafeRustFallback)
            .count()
    }

    const fn new(origins: Vec<BatchExecutionOrigin>) -> Self {
        Self { origins }
    }

    /// Returns one execution origin for every input item, in exact input order.
    #[must_use]
    pub fn origins(&self) -> &[BatchExecutionOrigin] {
        &self.origins
    }
}

/// Immutable view of one prepared classic request offered to a backend.
#[derive(Clone, Copy, Debug)]
pub struct BatchBackendRequest<'machine> {
    machine: &'machine ExecutionMachine,
    step_budget: usize,
}

impl<'machine> BatchBackendRequest<'machine> {
    /// Returns the complete immutable classic machine offered to the backend.
    #[must_use]
    pub const fn machine(&self) -> &'machine ExecutionMachine {
        self.machine
    }

    /// Returns the exact semantic step budget for this request.
    #[must_use]
    pub const fn step_budget(&self) -> usize {
        self.step_budget
    }
}

/// One successful classic completion returned by an optional backend.
#[derive(Clone, Debug)]
pub struct BatchBackendCompletion {
    outcome: RunOutcome,
    state: MachineState,
}

impl BatchBackendCompletion {
    /// Constructs a backend completion from one complete classic checkpoint.
    #[must_use]
    pub const fn new(state: MachineState, outcome: RunOutcome) -> Self {
        Self { outcome, state }
    }
}

/// Replaceable best-effort backend for already validated classic requests.
pub trait BatchExecutionBackend {
    /// Attempts an input-ordered batch without mutating the offered CPU states.
    ///
    /// Returning `None` means the whole backend attempt was unavailable or
    /// failed operationally. Within a returned vector, `None` defers that one
    /// request to the CPU fallback. A wrong result count is also ignored and
    /// the complete prepared subset runs on CPU.
    fn execute(
        &mut self,
        requests: &[BatchBackendRequest<'_>],
    ) -> Option<Vec<Option<BatchBackendCompletion>>>;
}

/// Immutable view of one prepared profile request offered to a backend.
#[derive(Clone, Copy, Debug)]
pub struct ProfileBatchBackendRequest<'machine> {
    machine: &'machine ProfileMachine,
    step_budget: usize,
}

impl<'machine> ProfileBatchBackendRequest<'machine> {
    /// Returns the complete immutable profile machine offered to the backend.
    #[must_use]
    pub const fn machine(&self) -> &'machine ProfileMachine {
        self.machine
    }

    /// Returns the exact semantic step budget for this request.
    #[must_use]
    pub const fn step_budget(&self) -> usize {
        self.step_budget
    }
}

/// One successful profile completion returned by an optional backend.
#[derive(Clone, Debug)]
pub struct ProfileBatchBackendCompletion {
    outcome: RunOutcome,
    state: ProfileMachineState,
}

impl ProfileBatchBackendCompletion {
    /// Constructs a backend completion from one validated profile checkpoint.
    #[must_use]
    pub const fn new(state: ProfileMachineState, outcome: RunOutcome) -> Self {
        Self { outcome, state }
    }
}

/// Replaceable best-effort backend for already validated profile requests.
pub trait ProfileBatchExecutionBackend {
    /// Attempts an input-ordered batch without mutating the offered CPU states.
    ///
    /// Returning `None` means the whole backend attempt was unavailable or
    /// failed operationally. Per-item `None` values defer to safe Rust. A wrong
    /// result count is ignored and the complete prepared subset runs on CPU.
    fn execute(
        &mut self,
        requests: &[ProfileBatchBackendRequest<'_>],
    ) -> Option<Vec<Option<ProfileBatchBackendCompletion>>>;
}

#[derive(Debug)]
enum ClassicSlot {
    Prepared(BuiltRequest),
    Rejected(BatchResult),
}

#[derive(Debug)]
enum ProfileSlot {
    Prepared(BuiltProfileRequest),
    Rejected(ProfileBatchResult),
}

/// Executes classic requests through an optional backend with safe-Rust
/// fallback.
///
/// Source/profile admission remains CPU-owned. Backend unavailability,
/// malformed result shape, per-item deferral, or inconsistent completion
/// metadata changes performance only; the original prepared machine then
/// executes on safe Rust.
#[must_use]
pub fn execute_batch_with_backend(
    requests: Vec<BatchRequest>,
    backend: &mut dyn BatchExecutionBackend,
) -> Vec<BatchResult> {
    execute_batch_with_backend_report(requests, backend).0
}

/// Executes classic requests and returns exact per-item backend/fallback
/// origin.
#[must_use]
pub fn execute_batch_with_backend_report(
    requests: Vec<BatchRequest>,
    backend: &mut dyn BatchExecutionBackend,
) -> (Vec<BatchResult>, BatchExecutionReport) {
    let slots = prepare_classic(requests);
    let views = classic_views(&slots);
    let attempts = if views.is_empty() {
        None
    } else {
        valid_classic_attempts(backend.execute(&views), views.len())
    };
    collect_classic(slots, attempts)
}

/// Executes profile requests through an optional backend with safe-Rust
/// fallback.
///
/// Canonical profile admission remains CPU-owned. Backend unavailability,
/// malformed result shape, per-item deferral, profile drift, or inconsistent
/// completion metadata falls back to the original safe-Rust machine.
#[must_use]
pub fn execute_profile_batch_with_backend(
    requests: Vec<ProfileBatchRequest>,
    backend: &mut dyn ProfileBatchExecutionBackend,
) -> Vec<ProfileBatchResult> {
    execute_profile_batch_with_backend_report(requests, backend).0
}

/// Executes profile requests and returns exact per-item backend/fallback
/// origin.
#[must_use]
pub fn execute_profile_batch_with_backend_report(
    requests: Vec<ProfileBatchRequest>,
    backend: &mut dyn ProfileBatchExecutionBackend,
) -> (Vec<ProfileBatchResult>, BatchExecutionReport) {
    let slots = prepare_profile(requests);
    let views = profile_views(&slots);
    let attempts = if views.is_empty() {
        None
    } else {
        valid_profile_attempts(backend.execute(&views), views.len())
    };
    collect_profile(slots, attempts)
}

fn prepare_classic(requests: Vec<BatchRequest>) -> Vec<ClassicSlot> {
    requests
        .into_iter()
        .map(|request| match request.build() {
            Ok(built) => ClassicSlot::Prepared(built),
            Err(error) => ClassicSlot::Rejected(BatchResult::Rejected {
                error,
                machine: None,
            }),
        })
        .collect()
}

fn classic_views(slots: &[ClassicSlot]) -> Vec<BatchBackendRequest<'_>> {
    slots
        .iter()
        .filter_map(|slot| match slot {
            ClassicSlot::Prepared(request) => Some(BatchBackendRequest {
                machine: &request.machine,
                step_budget: request.step_budget,
            }),
            ClassicSlot::Rejected(_) => None,
        })
        .collect()
}

fn valid_classic_attempts(
    attempts: Option<Vec<Option<BatchBackendCompletion>>>,
    expected: usize,
) -> Option<Vec<Option<BatchBackendCompletion>>> {
    attempts.filter(|items| items.len() == expected)
}

fn collect_classic(
    slots: Vec<ClassicSlot>,
    attempts: Option<Vec<Option<BatchBackendCompletion>>>,
) -> (Vec<BatchResult>, BatchExecutionReport) {
    let mut attempt_iter = attempts.into_iter().flatten();
    let mut results = Vec::with_capacity(slots.len());
    let mut origins = Vec::with_capacity(slots.len());
    for slot in slots {
        match slot {
            ClassicSlot::Rejected(result) => {
                results.push(result);
                origins.push(BatchExecutionOrigin::SafeRustAdmissionRejection);
            },
            ClassicSlot::Prepared(request) => {
                let completion = attempt_iter.next().flatten();
                let (result, origin) = accept_classic(request, completion);
                results.push(result);
                origins.push(origin);
            },
        }
    }
    (results, BatchExecutionReport::new(origins))
}

fn accept_classic(
    request: BuiltRequest,
    maybe_completion: Option<BatchBackendCompletion>,
) -> (BatchResult, BatchExecutionOrigin) {
    let Some(completion) = maybe_completion else {
        return (
            execute_built(request),
            BatchExecutionOrigin::SafeRustFallback,
        );
    };
    if !outcome_matches_state(
        completion.outcome,
        completion.state.io().termination(),
        request.step_budget,
    ) {
        return (
            execute_built(request),
            BatchExecutionOrigin::SafeRustFallback,
        );
    }
    let mode = request.machine.mode();
    let profile = request.machine.profile();
    let Ok(machine) =
        ExecutionMachine::from_snapshot(completion.state, mode, profile)
    else {
        return (
            execute_built(request),
            BatchExecutionOrigin::SafeRustFallback,
        );
    };
    (
        BatchResult::Completed {
            machine,
            outcome: completion.outcome,
        },
        BatchExecutionOrigin::Backend,
    )
}

fn prepare_profile(requests: Vec<ProfileBatchRequest>) -> Vec<ProfileSlot> {
    requests
        .into_iter()
        .map(|request| match request.build() {
            Ok(built) => ProfileSlot::Prepared(built),
            Err(error) => ProfileSlot::Rejected(ProfileBatchResult::Rejected {
                error,
                machine: None,
            }),
        })
        .collect()
}

fn profile_views(slots: &[ProfileSlot]) -> Vec<ProfileBatchBackendRequest<'_>> {
    slots
        .iter()
        .filter_map(|slot| match slot {
            ProfileSlot::Prepared(request) => {
                Some(ProfileBatchBackendRequest {
                    machine: &request.machine,
                    step_budget: request.step_budget,
                })
            },
            ProfileSlot::Rejected(_) => None,
        })
        .collect()
}

fn valid_profile_attempts(
    attempts: Option<Vec<Option<ProfileBatchBackendCompletion>>>,
    expected: usize,
) -> Option<Vec<Option<ProfileBatchBackendCompletion>>> {
    attempts.filter(|items| items.len() == expected)
}

fn collect_profile(
    slots: Vec<ProfileSlot>,
    attempts: Option<Vec<Option<ProfileBatchBackendCompletion>>>,
) -> (Vec<ProfileBatchResult>, BatchExecutionReport) {
    let mut attempt_iter = attempts.into_iter().flatten();
    let mut results = Vec::with_capacity(slots.len());
    let mut origins = Vec::with_capacity(slots.len());
    for slot in slots {
        match slot {
            ProfileSlot::Rejected(result) => {
                results.push(result);
                origins.push(BatchExecutionOrigin::SafeRustAdmissionRejection);
            },
            ProfileSlot::Prepared(request) => {
                let completion = attempt_iter.next().flatten();
                let (result, origin) = accept_profile(request, completion);
                results.push(result);
                origins.push(origin);
            },
        }
    }
    (results, BatchExecutionReport::new(origins))
}

fn accept_profile(
    request: BuiltProfileRequest,
    maybe_completion: Option<ProfileBatchBackendCompletion>,
) -> (ProfileBatchResult, BatchExecutionOrigin) {
    let Some(completion) = maybe_completion else {
        return (
            execute_profile_built(request),
            BatchExecutionOrigin::SafeRustFallback,
        );
    };
    if completion.state.profile() != request.machine.profile()
        || !outcome_matches_state(
            completion.outcome,
            completion.state.io().termination(),
            request.step_budget,
        )
    {
        return (
            execute_profile_built(request),
            BatchExecutionOrigin::SafeRustFallback,
        );
    }
    (
        ProfileBatchResult::Completed {
            machine: ProfileMachine::from_snapshot(completion.state),
            outcome: completion.outcome,
        },
        BatchExecutionOrigin::Backend,
    )
}

fn outcome_matches_state(
    outcome: RunOutcome,
    termination: Option<Termination>,
    step_budget: usize,
) -> bool {
    match outcome {
        RunOutcome::BudgetExhausted { steps } => {
            steps == step_budget && termination.is_none()
        },
        RunOutcome::Terminated { reason, steps } => {
            steps <= step_budget && termination == Some(reason)
        },
    }
}
