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
//   - Process-local and durable publication of exact agreed adaptive dispatch-
//     policy arbitrations, including productivity-gated agreement.
// - Must-Not:
//   - Assess telemetry, adapt signals, reinterpret arbitration, infer
//     precedence, bypass revision ownership, or replace canonical durable CAS.
// - Allows:
//   - Inputs: one exact two- or three-signal arbitration plus local expected
//     revision or durable expected state and byte bound.
//   - Outputs: withheld evidence, exact owner/CAS conflict or commit, and typed
//     failure retaining the arbitration.
//   - Side effects: local owner mutation or durable CAS only for agreed policy
//     authority.
// - Split-When:
//   - Additional publication destinations or distributed consensus gain
//     authority.
// - Merge-When:
//   - One product orchestrator owns arbitration through publication atomically.
// - Summary:
//   - Publishes agreement-only multi-signal dispatch policy authority.
// - Description:
//   - Deferred or conflicting evidence never mutates local or durable state.
// - Usage:
//   - Arbitrate validated adaptations first, then publish exact agreement.
// - Defaults:
//   - No implicit precedence; absent arbitration policy is withheld.
//

//! Agreement-only publication of mixed dispatch-policy adaptation evidence.
//!
//! Three-signal productivity authority reuses the same owner and durable CAS;
//! it does not add storage framing or precedence semantics.

use std::num::NonZeroUsize;

use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::{
    continuation_dispatch_policy_mixed_evidence as mixed,
    continuation_dispatch_policy_owner as owner,
    continuation_dispatch_policy_state_cas as cas,
};

type Arbitration = mixed::NativeContinuationDispatchPolicyAdaptationArbitration;
type ThreeSignalArbitration =
    mixed::NativeContinuationDispatchPolicyThreeSignalArbitration;
type DispatchOwner = owner::NativeContinuationDispatchPolicyOwner;
type DispatchRevision = owner::NativeContinuationDispatchPolicyRevision;
type DispatchState = owner::NativeContinuationDispatchPolicyState;
type OwnerError = owner::NativeContinuationDispatchPolicyOwnerError;
type OwnerUpdate = owner::NativeContinuationDispatchPolicyOwnerUpdate;

/// Failure before one process-local three-signal publication produced an
/// outcome.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyThreeSignalFailure {
    arbitration: ThreeSignalArbitration,
    error: OwnerError,
}

/// Exact process-local publication result for one three-signal arbitration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyThreeSignalPublication {
    /// Agreed policy encountered stale process-local revision evidence.
    Conflict {
        /// Exact three-signal arbitration whose policy was rejected.
        arbitration: ThreeSignalArbitration,
        /// Exact current active process-local state.
        current: DispatchState,
        /// Caller-supplied stale expected revision.
        expected: DispatchRevision,
    },
    /// Agreed three-signal policy replaced active process-local state.
    Published {
        /// Exact three-signal arbitration authorizing publication.
        arbitration: ThreeSignalArbitration,
        /// Exact active state after publication.
        current: DispatchState,
        /// Exact active state before publication.
        previous: DispatchState,
    },
    /// Three-signal arbitration exposed no policy authority.
    Withheld {
        /// Exact deferred or conflicting three-signal evidence.
        arbitration: ThreeSignalArbitration,
        /// Exact unchanged active process-local state.
        current: DispatchState,
    },
}

/// Failure before one durable three-signal publication produced an outcome.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyThreeSignalDurableFailure<StoreError>
{
    arbitration: ThreeSignalArbitration,
    error: cas::NativeContinuationDispatchPolicyStateCasError<StoreError>,
}

/// Exact durable publication result for one three-signal arbitration.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyThreeSignalDurablePublication<
    DurabilityError,
> {
    /// Agreed policy attempted the existing typed durable active-state CAS.
    Ready {
        /// Exact three-signal arbitration authorizing the CAS attempt.
        arbitration: ThreeSignalArbitration,
        /// Exact durable/conflict evidence from the existing CAS.
        publication:
            cas::NativeContinuationDispatchPolicyStateCas<DurabilityError>,
    },
    /// Three-signal arbitration exposed no policy authority.
    Withheld {
        /// Exact deferred or conflicting three-signal evidence.
        arbitration: ThreeSignalArbitration,
        /// Caller-supplied expected state retained without validation.
        expected: Option<DispatchState>,
    },
}

type ThreeSignalDurablePublication<DurabilityError> =
    NativeContinuationDispatchPolicyThreeSignalDurablePublication<
        DurabilityError,
    >;

/// Durable three-signal publication result specialized to one store.
pub type NativeContinuationDispatchPolicyThreeSignalDurableStoreResult<Store> =
    Result<
        ThreeSignalDurablePublication<
            <Store as DurableBlobStore>::DurabilityError,
        >,
        Box<
            NativeContinuationDispatchPolicyThreeSignalDurableFailure<
                <Store as BlobStore>::Error,
            >,
        >,
    >;

/// Failure before one process-local arbitration publication produced an
/// outcome.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyArbitrationFailure {
    arbitration: Arbitration,
    error: OwnerError,
}

/// Exact process-local publication result for one adaptive arbitration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyArbitrationPublication {
    /// Agreed policy encountered stale process-local revision evidence.
    Conflict {
        /// Exact arbitration whose agreed policy was rejected.
        arbitration: Arbitration,
        /// Exact current active process-local state.
        current: DispatchState,
        /// Caller-supplied stale expected revision.
        expected: DispatchRevision,
    },
    /// Agreed policy replaced the active process-local state.
    Published {
        /// Exact arbitration whose agreement authorized publication.
        arbitration: Arbitration,
        /// Exact active state after publication.
        current: DispatchState,
        /// Exact active state before publication.
        previous: DispatchState,
    },
    /// Arbitration exposed no policy authority; owner was not mutated.
    Withheld {
        /// Exact deferred or conflicting arbitration evidence.
        arbitration: Arbitration,
        /// Exact unchanged active process-local state.
        current: DispatchState,
    },
}

/// Failure before one durable arbitration publication produced an outcome.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyArbitrationDurableFailure<StoreError>
{
    arbitration: Arbitration,
    error: cas::NativeContinuationDispatchPolicyStateCasError<StoreError>,
}

/// Exact durable publication result for one adaptive arbitration.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyArbitrationDurablePublication<
    DurabilityError,
> {
    /// Agreed policy attempted the existing typed durable active-state CAS.
    Ready {
        /// Exact arbitration whose agreement authorized the CAS attempt.
        arbitration: Arbitration,
        /// Exact durable/conflict publication evidence from the existing CAS.
        publication:
            cas::NativeContinuationDispatchPolicyStateCas<DurabilityError>,
    },
    /// Arbitration exposed no policy authority; storage was not touched.
    Withheld {
        /// Exact deferred or conflicting arbitration evidence.
        arbitration: Arbitration,
        /// Caller-supplied expected state retained without validation.
        expected: Option<DispatchState>,
    },
}

type DurablePublication<DurabilityError> =
    NativeContinuationDispatchPolicyArbitrationDurablePublication<
        DurabilityError,
    >;

/// Durable arbitration publication result specialized to one store.
pub type NativeContinuationDispatchPolicyArbitrationDurableStoreResult<Store> =
    Result<
        DurablePublication<<Store as DurableBlobStore>::DurabilityError>,
        Box<
            NativeContinuationDispatchPolicyArbitrationDurableFailure<
                <Store as BlobStore>::Error,
            >,
        >,
    >;

impl NativeContinuationDispatchPolicyThreeSignalFailure {
    /// Returns the exact arbitration whose agreed policy was not published.
    #[must_use]
    pub const fn arbitration(&self) -> ThreeSignalArbitration {
        self.arbitration
    }

    /// Returns exact process-local owner rejection evidence.
    #[must_use]
    pub const fn error(&self) -> OwnerError {
        self.error
    }
}

impl<StoreError>
    NativeContinuationDispatchPolicyThreeSignalDurableFailure<StoreError>
{
    /// Returns the exact arbitration whose agreed policy was not published.
    #[must_use]
    pub const fn arbitration(&self) -> ThreeSignalArbitration {
        self.arbitration
    }

    /// Returns exact typed durable active-state CAS failure evidence.
    #[must_use]
    pub const fn error(
        &self,
    ) -> &cas::NativeContinuationDispatchPolicyStateCasError<StoreError> {
        &self.error
    }
}

impl NativeContinuationDispatchPolicyArbitrationFailure {
    /// Returns the exact arbitration whose agreed policy was not published.
    #[must_use]
    pub const fn arbitration(&self) -> Arbitration {
        self.arbitration
    }

    /// Returns exact process-local owner rejection evidence.
    #[must_use]
    pub const fn error(&self) -> OwnerError {
        self.error
    }
}

impl<StoreError>
    NativeContinuationDispatchPolicyArbitrationDurableFailure<StoreError>
{
    /// Returns the exact arbitration whose agreed policy was not published.
    #[must_use]
    pub const fn arbitration(&self) -> Arbitration {
        self.arbitration
    }

    /// Returns exact typed durable active-state CAS failure evidence.
    #[must_use]
    pub const fn error(
        &self,
    ) -> &cas::NativeContinuationDispatchPolicyStateCasError<StoreError> {
        &self.error
    }
}

/// Publishes one agreed arbitration through process-local revision ownership.
///
/// # Errors
///
/// Returns revision exhaustion while retaining the complete arbitration.
pub fn publish_native_continuation_dispatch_policy_arbitration(
    owner: &mut DispatchOwner,
    expected: DispatchRevision,
    arbitration: &Arbitration,
) -> Result<
    NativeContinuationDispatchPolicyArbitrationPublication,
    Box<NativeContinuationDispatchPolicyArbitrationFailure>,
> {
    let evidence = *arbitration;
    let Some(candidate) = evidence.policy() else {
        return Ok(
            NativeContinuationDispatchPolicyArbitrationPublication::Withheld {
                arbitration: evidence,
                current: owner.state(),
            },
        );
    };
    let update =
        owner
            .compare_and_swap(expected, candidate)
            .map_err(|error| {
                Box::new(NativeContinuationDispatchPolicyArbitrationFailure {
                    arbitration: evidence,
                    error,
                })
            })?;
    Ok(match update {
        OwnerUpdate::Conflict {
            current,
            expected: observed_expected,
            ..
        } => NativeContinuationDispatchPolicyArbitrationPublication::Conflict {
            arbitration: evidence,
            current,
            expected: observed_expected,
        },
        OwnerUpdate::Published { current, previous } => {
            NativeContinuationDispatchPolicyArbitrationPublication::Published {
                arbitration: evidence,
                current,
                previous,
            }
        },
    })
}

/// Publishes one agreed arbitration through the existing durable state CAS.
///
/// # Errors
///
/// Returns typed CAS failure only for agreed policy authority while retaining
/// the complete arbitration. Withheld evidence performs no storage operation.
pub fn publish_native_continuation_dispatch_policy_arbitration_durably<Store>(
    store: &mut Store,
    expected: Option<DispatchState>,
    arbitration: &Arbitration,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationDispatchPolicyArbitrationDurableStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let evidence = *arbitration;
    let Some(candidate) = evidence.policy() else {
        return Ok(DurablePublication::Withheld {
            arbitration: evidence,
            expected,
        });
    };
    let publication =
        cas::compare_and_swap_native_continuation_dispatch_policy_state_durably(
            store,
            expected,
            candidate,
            maximum_bytes,
        )
        .map_err(|error| {
            Box::new(
                NativeContinuationDispatchPolicyArbitrationDurableFailure {
                    arbitration: evidence,
                    error,
                },
            )
        })?;
    Ok(DurablePublication::Ready {
        arbitration: evidence,
        publication,
    })
}

/// Publishes one agreed three-signal arbitration through local revision
/// ownership.
///
/// # Errors
///
/// Returns revision exhaustion while retaining complete three-signal evidence.
pub fn publish_native_continuation_dispatch_policy_three_signal(
    owner: &mut DispatchOwner,
    expected: DispatchRevision,
    arbitration: &ThreeSignalArbitration,
) -> Result<
    NativeContinuationDispatchPolicyThreeSignalPublication,
    Box<NativeContinuationDispatchPolicyThreeSignalFailure>,
> {
    let evidence = *arbitration;
    let Some(candidate) = evidence.policy() else {
        return Ok(
            NativeContinuationDispatchPolicyThreeSignalPublication::Withheld {
                arbitration: evidence,
                current: owner.state(),
            },
        );
    };
    let update =
        owner
            .compare_and_swap(expected, candidate)
            .map_err(|error| {
                Box::new(NativeContinuationDispatchPolicyThreeSignalFailure {
                    arbitration: evidence,
                    error,
                })
            })?;
    Ok(match update {
        OwnerUpdate::Conflict {
            current,
            expected: observed_expected,
            ..
        } => NativeContinuationDispatchPolicyThreeSignalPublication::Conflict {
            arbitration: evidence,
            current,
            expected: observed_expected,
        },
        OwnerUpdate::Published { current, previous } => {
            NativeContinuationDispatchPolicyThreeSignalPublication::Published {
                arbitration: evidence,
                current,
                previous,
            }
        },
    })
}

/// Publishes one agreed three-signal arbitration through durable state CAS.
///
/// # Errors
///
/// Returns typed CAS failure only for agreed policy authority while retaining
/// complete three-signal evidence. Withheld evidence performs no storage work.
pub fn publish_native_continuation_dispatch_policy_three_signal_durably<Store>(
    store: &mut Store,
    expected: Option<DispatchState>,
    arbitration: &ThreeSignalArbitration,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationDispatchPolicyThreeSignalDurableStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let evidence = *arbitration;
    let Some(candidate) = evidence.policy() else {
        return Ok(ThreeSignalDurablePublication::Withheld {
            arbitration: evidence,
            expected,
        });
    };
    let publication =
        cas::compare_and_swap_native_continuation_dispatch_policy_state_durably(
            store,
            expected,
            candidate,
            maximum_bytes,
        )
        .map_err(|error| {
            Box::new(
                NativeContinuationDispatchPolicyThreeSignalDurableFailure {
                    arbitration: evidence,
                    error,
                },
            )
        })?;
    Ok(ThreeSignalDurablePublication::Ready {
        arbitration: evidence,
        publication,
    })
}
