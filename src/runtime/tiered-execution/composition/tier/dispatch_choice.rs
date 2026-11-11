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
//   - Process-local and durable publication of exact two-, three-, or
//     four-signal precedence-selected dispatch-policy authority.
// - Must-Not:
//   - Assess telemetry, arbitrate signals, choose precedence, reinterpret
//     selection evidence, bypass revision ownership, or replace durable CAS.
// - Allows:
//   - Inputs: one exact two-, three-, or four-signal precedence selection plus
//     local expected revision or durable expected state and byte bound.
//   - Outputs: withheld evidence, exact owner/CAS conflict or commit, and typed
//     failure retaining the selection.
//   - Side effects: local owner mutation or durable CAS only when selection
//     exposes policy authority.
// - Split-When:
//   - Additional publication destinations or durable precedence policy gains
//     independent authority.
// - Merge-When:
//   - One product orchestrator owns precedence selection through publication.
// - Summary:
//   - Publishes exact caller-selected mixed-evidence policy authority.
// - Description:
//   - Deferred or withheld selection never mutates local or durable state.
// - Usage:
//   - Select precedence first, then publish that exact selection evidence.
// - Defaults:
//   - Selection without policy authority is withheld without storage work.
//

//! Publication of exact caller-selected dispatch-policy precedence evidence.
//!
//! Three- and four-signal selections reuse the same owner and durable CAS
//! without adding persistence framing or precedence inference.

use std::num::NonZeroUsize;

use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::{
    continuation_dispatch_policy_owner as owner,
    continuation_dispatch_policy_precedence as precedence,
    continuation_dispatch_policy_state_cas as cas,
};

type DispatchOwner = owner::NativeContinuationDispatchPolicyOwner;
type DispatchRevision = owner::NativeContinuationDispatchPolicyRevision;
type DispatchState = owner::NativeContinuationDispatchPolicyState;
type OwnerError = owner::NativeContinuationDispatchPolicyOwnerError;
type OwnerUpdate = owner::NativeContinuationDispatchPolicyOwnerUpdate;
type Selection =
    precedence::NativeContinuationDispatchPolicyPrecedenceSelection;
type FourSignalSelection =
    precedence::NativeContinuationDispatchPolicyFourSignalPrecedenceSelection;
type ThreeSignalSelection =
    precedence::NativeContinuationDispatchPolicyThreeSignalPrecedenceSelection;

/// Failure before one process-local four-signal precedence publication.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyFourSignalFailure {
    error: OwnerError,
    selection: FourSignalSelection,
}

/// Exact process-local publication for one four-signal precedence selection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyFourSignalPublication {
    /// Selected policy encountered stale process-local revision evidence.
    Conflict {
        /// Exact four-signal precedence selection whose policy was rejected.
        selection: FourSignalSelection,
        /// Exact current active process-local state.
        current: DispatchState,
        /// Caller-supplied stale expected revision.
        expected: DispatchRevision,
    },
    /// Selected policy replaced the active process-local state.
    Published {
        /// Exact four-signal precedence selection authorizing publication.
        selection: FourSignalSelection,
        /// Exact active state after publication.
        current: DispatchState,
        /// Exact active state before publication.
        previous: DispatchState,
    },
    /// Selection exposed no policy authority; owner was not mutated.
    Withheld {
        /// Exact deferred, unavailable, or withheld selection evidence.
        selection: FourSignalSelection,
        /// Exact unchanged active process-local state.
        current: DispatchState,
    },
}

/// Failure before one durable four-signal precedence publication.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyFourSignalDurableFailure<StoreError>
{
    error: cas::NativeContinuationDispatchPolicyStateCasError<StoreError>,
    selection: FourSignalSelection,
}

/// Exact durable publication for one four-signal precedence selection.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyFourSignalDurablePublication<
    DurabilityError,
> {
    /// Policy authority attempted the existing typed durable active-state CAS.
    Ready {
        /// Exact four-signal precedence selection authorizing the CAS attempt.
        selection: FourSignalSelection,
        /// Exact durable/conflict evidence from the existing CAS.
        publication:
            cas::NativeContinuationDispatchPolicyStateCas<DurabilityError>,
    },
    /// Selection exposed no policy authority; storage was not touched.
    Withheld {
        /// Exact deferred, unavailable, or withheld selection evidence.
        selection: FourSignalSelection,
        /// Caller-supplied expected state retained without validation.
        expected: Option<DispatchState>,
    },
}

type FourSignalDurablePublication<DurabilityError> =
    NativeContinuationDispatchPolicyFourSignalDurablePublication<
        DurabilityError,
    >;

/// Durable four-signal precedence result specialized to one store.
pub type NativeContinuationDispatchPolicyFourSignalDurableStoreResult<Store> =
    Result<
        FourSignalDurablePublication<
            <Store as DurableBlobStore>::DurabilityError,
        >,
        Box<
            NativeContinuationDispatchPolicyFourSignalDurableFailure<
                <Store as BlobStore>::Error,
            >,
        >,
    >;

/// Failure before one process-local three-signal precedence publication.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyThreeSignalFailure {
    error: OwnerError,
    selection: ThreeSignalSelection,
}

/// Exact process-local publication for one three-signal precedence selection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyThreeSignalPublication {
    /// Selected policy encountered stale process-local revision evidence.
    Conflict {
        /// Exact three-signal precedence selection whose policy was rejected.
        selection: ThreeSignalSelection,
        /// Exact current active process-local state.
        current: DispatchState,
        /// Caller-supplied stale expected revision.
        expected: DispatchRevision,
    },
    /// Selected policy replaced the active process-local state.
    Published {
        /// Exact three-signal precedence selection authorizing publication.
        selection: ThreeSignalSelection,
        /// Exact active state after publication.
        current: DispatchState,
        /// Exact active state before publication.
        previous: DispatchState,
    },
    /// Selection exposed no policy authority; owner was not mutated.
    Withheld {
        /// Exact deferred, unavailable, or withheld selection evidence.
        selection: ThreeSignalSelection,
        /// Exact unchanged active process-local state.
        current: DispatchState,
    },
}

/// Failure before one durable three-signal precedence publication.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyThreeSignalDurableFailure<StoreError>
{
    error: cas::NativeContinuationDispatchPolicyStateCasError<StoreError>,
    selection: ThreeSignalSelection,
}

/// Exact durable publication for one three-signal precedence selection.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyThreeSignalDurablePublication<
    DurabilityError,
> {
    /// Policy authority attempted the existing typed durable active-state CAS.
    Ready {
        /// Exact three-signal precedence selection authorizing the CAS
        /// attempt.
        selection: ThreeSignalSelection,
        /// Exact durable/conflict evidence from the existing CAS.
        publication:
            cas::NativeContinuationDispatchPolicyStateCas<DurabilityError>,
    },
    /// Selection exposed no policy authority; storage was not touched.
    Withheld {
        /// Exact deferred, unavailable, or withheld selection evidence.
        selection: ThreeSignalSelection,
        /// Caller-supplied expected state retained without validation.
        expected: Option<DispatchState>,
    },
}

type ThreeSignalDurablePublication<DurabilityError> =
    NativeContinuationDispatchPolicyThreeSignalDurablePublication<
        DurabilityError,
    >;

/// Durable three-signal precedence result specialized to one store.
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

/// Failure before one process-local precedence publication produced an outcome.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyPrecedenceFailure {
    error: OwnerError,
    selection: Selection,
}

/// Exact process-local publication result for one precedence selection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyPrecedencePublication {
    /// Selected policy encountered stale process-local revision evidence.
    Conflict {
        /// Exact precedence selection whose policy was rejected.
        selection: Selection,
        /// Exact current active process-local state.
        current: DispatchState,
        /// Caller-supplied stale expected revision.
        expected: DispatchRevision,
    },
    /// Selected policy replaced the active process-local state.
    Published {
        /// Exact precedence selection that authorized publication.
        selection: Selection,
        /// Exact active state after publication.
        current: DispatchState,
        /// Exact active state before publication.
        previous: DispatchState,
    },
    /// Selection exposed no policy authority; owner was not mutated.
    Withheld {
        /// Exact deferred or withheld precedence selection.
        selection: Selection,
        /// Exact unchanged active process-local state.
        current: DispatchState,
    },
}

/// Failure before one durable precedence publication produced an outcome.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationDispatchPolicyPrecedenceDurableFailure<StoreError>
{
    error: cas::NativeContinuationDispatchPolicyStateCasError<StoreError>,
    selection: Selection,
}

/// Exact durable publication result for one precedence selection.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationDispatchPolicyPrecedenceDurablePublication<
    DurabilityError,
> {
    /// Policy authority attempted the existing typed durable active-state CAS.
    Ready {
        /// Exact precedence selection that authorized the CAS attempt.
        selection: Selection,
        /// Exact durable/conflict publication evidence from the existing CAS.
        publication:
            cas::NativeContinuationDispatchPolicyStateCas<DurabilityError>,
    },
    /// Selection exposed no policy authority; storage was not touched.
    Withheld {
        /// Exact deferred or withheld precedence selection.
        selection: Selection,
        /// Caller-supplied expected state retained without validation.
        expected: Option<DispatchState>,
    },
}

type DurablePublication<DurabilityError> =
    NativeContinuationDispatchPolicyPrecedenceDurablePublication<
        DurabilityError,
    >;

/// Durable precedence publication result specialized to one store.
pub type NativeContinuationDispatchPolicyPrecedenceDurableStoreResult<Store> =
    Result<
        DurablePublication<<Store as DurableBlobStore>::DurabilityError>,
        Box<
            NativeContinuationDispatchPolicyPrecedenceDurableFailure<
                <Store as BlobStore>::Error,
            >,
        >,
    >;

impl NativeContinuationDispatchPolicyFourSignalFailure {
    /// Returns exact process-local owner rejection evidence.
    #[must_use]
    pub const fn error(&self) -> OwnerError {
        self.error
    }

    /// Returns the exact selection whose policy was not published.
    #[must_use]
    pub const fn selection(&self) -> FourSignalSelection {
        self.selection
    }
}

impl<StoreError>
    NativeContinuationDispatchPolicyFourSignalDurableFailure<StoreError>
{
    /// Returns exact typed durable active-state CAS failure evidence.
    #[must_use]
    pub const fn error(
        &self,
    ) -> &cas::NativeContinuationDispatchPolicyStateCasError<StoreError> {
        &self.error
    }

    /// Returns the exact selection whose policy was not published.
    #[must_use]
    pub const fn selection(&self) -> FourSignalSelection {
        self.selection
    }
}

impl NativeContinuationDispatchPolicyThreeSignalFailure {
    /// Returns exact process-local owner rejection evidence.
    #[must_use]
    pub const fn error(&self) -> OwnerError {
        self.error
    }

    /// Returns the exact selection whose policy was not published.
    #[must_use]
    pub const fn selection(&self) -> ThreeSignalSelection {
        self.selection
    }
}

impl<StoreError>
    NativeContinuationDispatchPolicyThreeSignalDurableFailure<StoreError>
{
    /// Returns exact typed durable active-state CAS failure evidence.
    #[must_use]
    pub const fn error(
        &self,
    ) -> &cas::NativeContinuationDispatchPolicyStateCasError<StoreError> {
        &self.error
    }

    /// Returns the exact selection whose policy was not published.
    #[must_use]
    pub const fn selection(&self) -> ThreeSignalSelection {
        self.selection
    }
}

impl NativeContinuationDispatchPolicyPrecedenceFailure {
    /// Returns exact process-local owner rejection evidence.
    #[must_use]
    pub const fn error(&self) -> OwnerError {
        self.error
    }

    /// Returns the exact selection whose policy was not published.
    #[must_use]
    pub const fn selection(&self) -> Selection {
        self.selection
    }
}

impl<StoreError>
    NativeContinuationDispatchPolicyPrecedenceDurableFailure<StoreError>
{
    /// Returns exact typed durable active-state CAS failure evidence.
    #[must_use]
    pub const fn error(
        &self,
    ) -> &cas::NativeContinuationDispatchPolicyStateCasError<StoreError> {
        &self.error
    }

    /// Returns the exact selection whose policy was not published.
    #[must_use]
    pub const fn selection(&self) -> Selection {
        self.selection
    }
}

/// Publishes one four-signal precedence selection through revision ownership.
///
/// # Errors
///
/// Returns revision exhaustion while retaining the complete selection evidence.
pub fn publish_native_continuation_dispatch_policy_four_signal_choice(
    owner: &mut DispatchOwner,
    expected: DispatchRevision,
    selection: &FourSignalSelection,
) -> Result<
    NativeContinuationDispatchPolicyFourSignalPublication,
    Box<NativeContinuationDispatchPolicyFourSignalFailure>,
> {
    let evidence = *selection;
    let Some(candidate) = evidence.policy() else {
        return Ok(
            NativeContinuationDispatchPolicyFourSignalPublication::Withheld {
                selection: evidence,
                current: owner.state(),
            },
        );
    };
    let update =
        owner
            .compare_and_swap(expected, candidate)
            .map_err(|error| {
                Box::new(NativeContinuationDispatchPolicyFourSignalFailure {
                    error,
                    selection: evidence,
                })
            })?;
    Ok(match update {
        OwnerUpdate::Conflict {
            current,
            expected: observed_expected,
            ..
        } => NativeContinuationDispatchPolicyFourSignalPublication::Conflict {
            selection: evidence,
            current,
            expected: observed_expected,
        },
        OwnerUpdate::Published { current, previous } => {
            NativeContinuationDispatchPolicyFourSignalPublication::Published {
                selection: evidence,
                current,
                previous,
            }
        },
    })
}

/// Publishes one four-signal precedence selection through durable state CAS.
///
/// # Errors
///
/// Returns typed CAS failure only for selected policy authority while retaining
/// the complete selection. Evidence without policy performs no storage work.
pub fn publish_native_continuation_dispatch_policy_four_signal_choice_durably<
    Store,
>(
    store: &mut Store,
    expected: Option<DispatchState>,
    selection: &FourSignalSelection,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationDispatchPolicyFourSignalDurableStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let evidence = *selection;
    let Some(candidate) = evidence.policy() else {
        return Ok(FourSignalDurablePublication::Withheld {
            selection: evidence,
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
                NativeContinuationDispatchPolicyFourSignalDurableFailure {
                    error,
                    selection: evidence,
                },
            )
        })?;
    Ok(FourSignalDurablePublication::Ready {
        selection: evidence,
        publication,
    })
}

/// Publishes one precedence selection through process-local revision ownership.
///
/// # Errors
///
/// Returns revision exhaustion while retaining the complete selection.
pub fn publish_native_continuation_dispatch_policy_precedence(
    owner: &mut DispatchOwner,
    expected: DispatchRevision,
    selection: &Selection,
) -> Result<
    NativeContinuationDispatchPolicyPrecedencePublication,
    Box<NativeContinuationDispatchPolicyPrecedenceFailure>,
> {
    let evidence = *selection;
    let Some(candidate) = evidence.policy() else {
        return Ok(
            NativeContinuationDispatchPolicyPrecedencePublication::Withheld {
                selection: evidence,
                current: owner.state(),
            },
        );
    };
    let update =
        owner
            .compare_and_swap(expected, candidate)
            .map_err(|error| {
                Box::new(NativeContinuationDispatchPolicyPrecedenceFailure {
                    error,
                    selection: evidence,
                })
            })?;
    Ok(match update {
        OwnerUpdate::Conflict {
            current,
            expected: observed_expected,
            ..
        } => NativeContinuationDispatchPolicyPrecedencePublication::Conflict {
            selection: evidence,
            current,
            expected: observed_expected,
        },
        OwnerUpdate::Published { current, previous } => {
            NativeContinuationDispatchPolicyPrecedencePublication::Published {
                selection: evidence,
                current,
                previous,
            }
        },
    })
}

/// Publishes one precedence selection through the existing durable state CAS.
///
/// # Errors
///
/// Returns typed CAS failure only for selected policy authority while retaining
/// the complete selection. Withheld evidence performs no storage operation.
pub fn publish_native_continuation_dispatch_policy_precedence_durably<Store>(
    store: &mut Store,
    expected: Option<DispatchState>,
    selection: &Selection,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationDispatchPolicyPrecedenceDurableStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let evidence = *selection;
    let Some(candidate) = evidence.policy() else {
        return Ok(DurablePublication::Withheld {
            selection: evidence,
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
            Box::new(NativeContinuationDispatchPolicyPrecedenceDurableFailure {
                error,
                selection: evidence,
            })
        })?;
    Ok(DurablePublication::Ready {
        selection: evidence,
        publication,
    })
}
/// Publishes one three-signal precedence selection through revision ownership.
///
/// # Errors
///
/// Returns revision exhaustion while retaining the complete selection evidence.
pub fn publish_native_continuation_dispatch_policy_three_signal_choice(
    owner: &mut DispatchOwner,
    expected: DispatchRevision,
    selection: &ThreeSignalSelection,
) -> Result<
    NativeContinuationDispatchPolicyThreeSignalPublication,
    Box<NativeContinuationDispatchPolicyThreeSignalFailure>,
> {
    let evidence = *selection;
    let Some(candidate) = evidence.policy() else {
        return Ok(
            NativeContinuationDispatchPolicyThreeSignalPublication::Withheld {
                selection: evidence,
                current: owner.state(),
            },
        );
    };
    let update =
        owner
            .compare_and_swap(expected, candidate)
            .map_err(|error| {
                Box::new(NativeContinuationDispatchPolicyThreeSignalFailure {
                    error,
                    selection: evidence,
                })
            })?;
    Ok(match update {
        OwnerUpdate::Conflict {
            current,
            expected: observed_expected,
            ..
        } => NativeContinuationDispatchPolicyThreeSignalPublication::Conflict {
            selection: evidence,
            current,
            expected: observed_expected,
        },
        OwnerUpdate::Published { current, previous } => {
            NativeContinuationDispatchPolicyThreeSignalPublication::Published {
                selection: evidence,
                current,
                previous,
            }
        },
    })
}

/// Publishes one three-signal precedence selection through durable state CAS.
///
/// # Errors
///
/// Returns typed CAS failure only for selected policy authority while retaining
/// the complete selection. Evidence without policy performs no storage work.
pub fn publish_native_continuation_dispatch_policy_three_signal_choice_durably<
    Store,
>(
    store: &mut Store,
    expected: Option<DispatchState>,
    selection: &ThreeSignalSelection,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationDispatchPolicyThreeSignalDurableStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let evidence = *selection;
    let Some(candidate) = evidence.policy() else {
        return Ok(ThreeSignalDurablePublication::Withheld {
            selection: evidence,
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
                    error,
                    selection: evidence,
                },
            )
        })?;
    Ok(ThreeSignalDurablePublication::Ready {
        selection: evidence,
        publication,
    })
}
