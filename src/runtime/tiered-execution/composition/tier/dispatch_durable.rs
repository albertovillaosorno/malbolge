// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Durable publication of one exact adaptive dispatch-policy selection
//     through the existing revisioned active-state CAS.
// - Must-Not:
//   - Assess telemetry, infer policy, bypass canonical state framing, choose
//     storage paths, or reinterpret revision and durability evidence.
// - Allows:
//   - Inputs: one adaptation, optional expected active state, byte bound, and
//     conditional durable store.
//   - Outputs: deferred evidence, exact conflict, durable commit, committed
//     sync failure, or typed CAS failure retaining the adaptation.
//   - Side effects: delegated durable state CAS only for sufficient evidence.
// - Split-When:
//   - Multi-evidence arbitration or distributed publication gains authority.
// - Merge-When:
//   - One durable dispatch orchestrator owns selection and publication
//     atomically.
// - Summary:
//   - Binds sufficient adaptive evidence to durable revisioned policy state.
// - Description:
//   - Deferral is storage-free; ready evidence preserves exact CAS semantics.
// - Usage:
//   - Supply the last observed active state and one exact adaptation.
// - Defaults:
//   - Insufficient evidence never initializes or mutates durable active state.
//

//! Durable publication of one exact adaptive synchronous dispatch policy.

use std::num::NonZeroUsize;

use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::{
    continuation_dispatch_policy as dispatch_policy,
    continuation_dispatch_policy_adaptation as adaptation,
    continuation_dispatch_policy_owner as policy_owner,
    continuation_dispatch_policy_state_cas as cas,
};

type DispatchAdaptation =
    adaptation::NativeContinuationDispatchPolicyAdaptation;
type DispatchPolicy = dispatch_policy::NativeContinuationDispatchPolicy;
type DispatchState = policy_owner::NativeContinuationDispatchPolicyState;
type StateCas<DurabilityError> =
    cas::NativeContinuationDispatchPolicyStateCas<DurabilityError>;

/// Failure before one adaptive durable publication produced an outcome.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyAdaptationDurableFailure<StoreError>
{
    adaptation: DispatchAdaptation,
    error: cas::NativeContinuationDispatchPolicyStateCasError<StoreError>,
}

/// Exact outcome of one adaptive durable active-policy publication attempt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyAdaptationDurablePublication<
    DurabilityError,
> {
    /// Durable state differed from the caller-supplied expected state.
    Conflict {
        /// Exact adaptation whose selected policy was rejected.
        adaptation: DispatchAdaptation,
        /// Exact current durable state, or `None` when missing.
        current: Option<DispatchState>,
        /// Exact caller-supplied expected durable state.
        expected: Option<DispatchState>,
    },
    /// Evidence was insufficient; no storage operation occurred.
    Deferred {
        /// Exact deferred adaptation evidence.
        adaptation: DispatchAdaptation,
        /// Caller-supplied expected state retained without validation.
        expected: Option<DispatchState>,
    },
    /// Selected policy committed and durability confirmation completed.
    Durable {
        /// Exact adaptation that selected the committed policy.
        adaptation: DispatchAdaptation,
        /// Exact canonical state byte count committed by the store.
        bytes: usize,
        /// Exact active state published by this operation.
        current: DispatchState,
        /// Exact prior state, or `None` for revision-zero initialization.
        previous: Option<DispatchState>,
    },
    /// Selected policy committed, then durability confirmation failed.
    Published {
        /// Exact adaptation that selected the committed policy.
        adaptation: DispatchAdaptation,
        /// Exact canonical state byte count committed by the store.
        bytes: usize,
        /// Exact active state published by this operation.
        current: DispatchState,
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact prior state, or `None` for revision-zero initialization.
        previous: Option<DispatchState>,
    },
}

type DurablePublication<DurabilityError> =
    NativeContinuationDispatchPolicyAdaptationDurablePublication<
        DurabilityError,
    >;

/// Durable adaptive publication result specialized to one store.
pub type NativeContinuationDispatchPolicyAdaptationDurableStoreResult<Store> =
    Result<
        DurablePublication<<Store as DurableBlobStore>::DurabilityError>,
        Box<
            NativeContinuationDispatchPolicyAdaptationDurableFailure<
                <Store as BlobStore>::Error,
            >,
        >,
    >;

impl<StoreError>
    NativeContinuationDispatchPolicyAdaptationDurableFailure<StoreError>
{
    /// Returns the exact adaptation whose selected policy was not published.
    #[must_use]
    pub const fn adaptation(&self) -> DispatchAdaptation {
        self.adaptation
    }

    /// Returns exact typed durable active-state CAS failure evidence.
    #[must_use]
    pub const fn error(
        &self,
    ) -> &cas::NativeContinuationDispatchPolicyStateCasError<StoreError> {
        &self.error
    }
}

/// Publishes one sufficient adaptation through the existing durable state CAS.
///
/// # Errors
///
/// Returns typed CAS rejection while retaining the complete adaptation.
pub fn publish_native_continuation_dispatch_policy_adaptation_durably<Store>(
    store: &mut Store,
    expected: Option<DispatchState>,
    adaptation: DispatchAdaptation,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationDispatchPolicyAdaptationDurableStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let Some(candidate) = adaptation.policy() else {
        return Ok(DurablePublication::Deferred { adaptation, expected });
    };
    let outcome =
        compare_state_durably(store, expected, candidate, maximum_bytes)
            .map_err(|error| {
                Box::new(
                    NativeContinuationDispatchPolicyAdaptationDurableFailure {
                        adaptation,
                        error,
                    },
                )
            })?;
    Ok(match outcome {
        StateCas::Conflict {
            current,
            expected: observed_expected,
            ..
        } => DurablePublication::Conflict {
            adaptation,
            current,
            expected: observed_expected,
        },
        StateCas::Durable { bytes, current, previous } => {
            DurablePublication::Durable {
                adaptation,
                bytes,
                current,
                previous,
            }
        },
        StateCas::Published {
            bytes,
            current,
            durability_error,
            previous,
        } => DurablePublication::Published {
            adaptation,
            bytes,
            current,
            durability_error,
            previous,
        },
    })
}
fn compare_state_durably<Store>(
    store: &mut Store,
    expected: Option<DispatchState>,
    candidate: DispatchPolicy,
    maximum_bytes: NonZeroUsize,
) -> cas::NativeContinuationDispatchPolicyStateCasStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    cas::compare_and_swap_native_continuation_dispatch_policy_state_durably(
        store,
        expected,
        candidate,
        maximum_bytes,
    )
}
