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
//   - Atomic pre-publication staging for one ordered fused cache batch.
// - Must-Not:
//   - Execute resident code, alter cache limits, or hide post-publication
//     cleanup ownership.
// - Allows:
//   - Inputs: exact verified fused artifacts, lease cache, and memory adapter.
//   - Outputs: ordered dispositions/leases or rollback/cleanup evidence.
//   - Side effects: staged executable load and explicit cleanup through
//     adapter.
// - Split-When:
//   - Semantic sequence admission or asynchronous cache mutation gains policy.
// - Merge-When:
//   - The fused lease cache owns complete batch publication internally.
// - Summary:
//   - Stages every miss before mutating active or retired cache authority.
// - Description:
//   - Pre-publication failure leaves cache queues and usage unchanged.
// - Usage:
//   - Acquire a verified artifact batch, then bind returned leases separately.
// - Defaults:
//   - Destructive FIFO release begins only after the whole batch can publish.
//

//! Transactional batch acquisition for fused executable leases.

use std::collections::VecDeque;
use std::fmt::{Display, Formatter, Result as FormatResult};
use std::sync::Arc;

use super::super::direct::VerifiedDirectFusedSequenceObjectArtifact;
use super::super::executable_cache_capacity::{
    NativeExecutableSequenceCacheCapacityError,
    NativeExecutableSequenceCacheUsage, NativeExecutableSequenceWeight,
};
use super::super::fused_resident::{
    DirectFusedNativeExecutableOwner, DirectFusedNativeOwnerLoadFailure,
};
use super::super::platform::NativeExecutableMemoryAdapter;
use super::{
    CacheCandidate, CacheValue, DirectFusedNativeLease,
    DirectFusedNativeLeaseCache, DirectFusedNativeLeaseCacheAcquisition,
    DirectFusedNativeLeaseCacheBlock, DirectFusedNativeLeaseCacheDisposition,
    DirectFusedNativeLeaseCacheEntryReleaseFailure,
    DirectFusedNativeLeaseCacheReleaseFailure,
};
use crate::execution_cache::NativeArtifactKey;

/// Ordered dispositions and exact leases consumed from one batch.
pub type DirectFusedNativeLeaseCacheBatchParts = (
    Vec<DirectFusedNativeLeaseCacheDisposition>,
    Vec<DirectFusedNativeLease>,
);

/// Committed batch plus retryable post-publication cleanup ownership.
pub type DirectFusedNativeLeaseCacheBatchCommittedCleanup<E> = (
    DirectFusedNativeLeaseCacheBatchAcquisition,
    DirectFusedNativeLeaseCacheReleaseFailure<E>,
);
type BatchFailure<Adapter> = DirectFusedNativeLeaseCacheBatchFailure<
    <Adapter as NativeExecutableMemoryAdapter>::Error,
>;
type BatchAdapterResult<Adapter, T> = Result<T, Box<BatchFailure<Adapter>>>;
type BatchCauseResult<Adapter> = Result<
    (),
    BatchFailureCause<<Adapter as NativeExecutableMemoryAdapter>::Error>,
>;
type PreflightResult<E> = Result<PublishPlan, BatchFailureCause<E>>;
type CleanupResult<E> =
    Result<(), Box<DirectFusedNativeLeaseCacheReleaseFailure<E>>>;
type PublishedResident =
    (NativeArtifactKey, Arc<DirectFusedNativeExecutableOwner>);
type TransferredResident =
    (NativeArtifactKey, DirectFusedNativeExecutableOwner);

#[derive(Debug)]
enum BatchFailureCause<E> {
    Blocked(Box<DirectFusedNativeLeaseCacheBlock>),
    Capacity(NativeExecutableSequenceCacheCapacityError),
    Cleanup(Box<DirectFusedNativeLeaseCacheReleaseFailure<E>>),
    Identity,
    Invariant,
    Load(Box<DirectFusedNativeOwnerLoadFailure<E>>),
}

#[derive(Debug)]
enum BatchRequestSource {
    Active(Box<DirectFusedNativeLease>),
    Staged { first: bool, index: usize },
}

#[derive(Debug)]
struct PlannedVictim {
    key: NativeArtifactKey,
    retire: bool,
}

#[derive(Debug)]
struct PreparedBatch {
    candidates: Vec<StagedCandidate>,
    plans: Vec<PublishPlan>,
    sources: Vec<BatchRequestSource>,
}

#[derive(Debug)]
struct PreflightState {
    active: VecDeque<SimulatedActive>,
    retired_keys: Vec<NativeArtifactKey>,
    usage: NativeExecutableSequenceCacheUsage,
}

#[derive(Debug)]
struct PublishPlan {
    retired: Vec<NativeArtifactKey>,
    usage_after: NativeExecutableSequenceCacheUsage,
    victims: Vec<PlannedVictim>,
}

#[derive(Debug)]
struct SimulatedActive {
    key: NativeArtifactKey,
    protected: bool,
    weight: NativeExecutableSequenceWeight,
}

#[derive(Clone, Copy)]
struct StageRequest<'artifact> {
    artifact: &'artifact VerifiedDirectFusedSequenceObjectArtifact,
    index: usize,
}

#[derive(Debug)]
struct StagedBatch {
    candidates: Vec<StagedCandidate>,
    sources: Vec<BatchRequestSource>,
}

#[derive(Debug)]
struct StagedCandidate {
    candidate: CacheCandidate,
    request_index: usize,
}

/// Ordered fused cache batch after one atomic publication decision.
#[derive(Debug)]
pub struct DirectFusedNativeLeaseCacheBatchAcquisition {
    acquisitions: Vec<DirectFusedNativeLeaseCacheAcquisition>,
}

/// Transactional fused cache batch failure with exact cleanup ownership.
#[derive(Debug)]
pub struct DirectFusedNativeLeaseCacheBatchFailure<E> {
    cause: BatchFailureCause<E>,
    committed: Option<DirectFusedNativeLeaseCacheBatchAcquisition>,
    index: usize,
    published: bool,
    rollback_cleanup: Option<Box<DirectFusedNativeLeaseCacheReleaseFailure<E>>>,
}

/// Result of one ordered transactional fused cache batch acquisition.
pub type DirectFusedNativeLeaseCacheBatchResult<E> = Result<
    DirectFusedNativeLeaseCacheBatchAcquisition,
    Box<DirectFusedNativeLeaseCacheBatchFailure<E>>,
>;

impl DirectFusedNativeLeaseCacheBatchAcquisition {
    /// Returns exact per-request insertion/hit evidence in request order.
    #[must_use]
    pub fn dispositions(&self) -> Vec<DirectFusedNativeLeaseCacheDisposition> {
        self.acquisitions
            .iter()
            .map(|item| item.disposition().clone())
            .collect()
    }

    /// Consumes this batch into ordered dispositions and exact leases.
    #[must_use]
    pub fn into_parts(self) -> DirectFusedNativeLeaseCacheBatchParts {
        self.acquisitions
            .into_iter()
            .map(|item| (item.disposition, item.lease))
            .unzip()
    }

    /// Returns whether this batch contains no requested leases.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.acquisitions.is_empty()
    }

    /// Returns the number of exact requested leases retained by this batch.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.acquisitions.len()
    }
}

impl<E> DirectFusedNativeLeaseCacheBatchFailure<E> {
    /// Returns capacity blockage when live residency prevents publication.
    #[must_use]
    pub const fn block(&self) -> Option<&DirectFusedNativeLeaseCacheBlock> {
        match &self.cause {
            BatchFailureCause::Blocked(block) => Some(block),
            BatchFailureCause::Capacity(_)
            | BatchFailureCause::Cleanup(_)
            | BatchFailureCause::Identity
            | BatchFailureCause::Invariant
            | BatchFailureCause::Load(_) => None,
        }
    }

    /// Reports whether cache publication began before this failure.
    #[must_use]
    pub const fn cache_committed(&self) -> bool {
        self.published
    }

    /// Returns candidate capacity rejection before cache publication.
    #[must_use]
    pub const fn capacity_error(
        &self,
    ) -> Option<NativeExecutableSequenceCacheCapacityError> {
        match self.cause {
            BatchFailureCause::Capacity(error) => Some(error),
            BatchFailureCause::Blocked(_)
            | BatchFailureCause::Cleanup(_)
            | BatchFailureCause::Identity
            | BatchFailureCause::Invariant
            | BatchFailureCause::Load(_) => None,
        }
    }

    /// Returns the zero-based request whose preparation/publication failed.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Consumes topology cleanup failure into acquisitions and retry ownership.
    #[must_use]
    pub fn into_committed_cleanup(
        self,
    ) -> Option<DirectFusedNativeLeaseCacheBatchCommittedCleanup<E>> {
        let BatchFailureCause::Cleanup(cleanup) = self.cause else {
            return None;
        };
        self.committed.map(|committed| (committed, *cleanup))
    }

    /// Consumes this failure into retryable pre-publication rollback cleanup.
    #[must_use]
    pub fn into_rollback_cleanup(
        self,
    ) -> Option<DirectFusedNativeLeaseCacheReleaseFailure<E>> {
        self.rollback_cleanup.map(|failure| *failure)
    }

    /// Reports whether a request key disagreed with active/staged identity.
    #[must_use]
    pub const fn is_identity_failure(&self) -> bool {
        matches!(self.cause, BatchFailureCause::Identity)
    }

    /// Returns exact owner-load failure before cache authority changed.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&DirectFusedNativeOwnerLoadFailure<E>> {
        match &self.cause {
            BatchFailureCause::Load(failure) => Some(failure),
            BatchFailureCause::Blocked(_)
            | BatchFailureCause::Capacity(_)
            | BatchFailureCause::Cleanup(_)
            | BatchFailureCause::Identity
            | BatchFailureCause::Invariant => None,
        }
    }

    /// Returns post-publication FIFO cleanup failure, when present.
    #[must_use]
    pub const fn publication_cleanup_failure(
        &self,
    ) -> Option<&DirectFusedNativeLeaseCacheReleaseFailure<E>> {
        match &self.cause {
            BatchFailureCause::Cleanup(failure) => Some(failure),
            BatchFailureCause::Blocked(_)
            | BatchFailureCause::Capacity(_)
            | BatchFailureCause::Identity
            | BatchFailureCause::Invariant
            | BatchFailureCause::Load(_) => None,
        }
    }

    /// Returns retryable cleanup retained while rolling back staged misses.
    #[must_use]
    pub fn rollback_cleanup_failure(
        &self,
    ) -> Option<&DirectFusedNativeLeaseCacheReleaseFailure<E>> {
        self.rollback_cleanup.as_deref()
    }
}

impl<E: Display> Display for DirectFusedNativeLeaseCacheBatchFailure<E> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "fused cache batch failed at {}: ", self.index)?;
        match &self.cause {
            BatchFailureCause::Blocked(_) => {
                f.write_str("live residency blocks transactional publication")
            },
            BatchFailureCause::Capacity(error) => Display::fmt(error, f),
            BatchFailureCause::Cleanup(error) => write!(
                f,
                "publication committed but FIFO cleanup failed: {error}",
            ),
            BatchFailureCause::Identity => {
                f.write_str("exact fused artifact identity drifted")
            },
            BatchFailureCause::Invariant => {
                f.write_str("transactional publication invariant drifted")
            },
            BatchFailureCause::Load(error) => write!(f, "load: {error}"),
        }?;
        if self.rollback_cleanup.is_some() {
            f.write_str("; staged rollback cleanup also failed")?;
        }
        Ok(())
    }
}

pub(super) fn acquire_batch_transactionally<Adapter>(
    cache: &mut DirectFusedNativeLeaseCache,
    adapter: &mut Adapter,
    artifacts: &[VerifiedDirectFusedSequenceObjectArtifact],
) -> DirectFusedNativeLeaseCacheBatchResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let staged_batch = stage_requests(cache, adapter, artifacts)?;
    let prepared = preflight_publication(cache, adapter, staged_batch)?;
    publish_staged(cache, adapter, prepared)
}

fn stage_requests<Adapter>(
    cache: &DirectFusedNativeLeaseCache,
    adapter: &mut Adapter,
    artifacts: &[VerifiedDirectFusedSequenceObjectArtifact],
) -> BatchAdapterResult<Adapter, StagedBatch>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut batch = StagedBatch {
        candidates: Vec::new(),
        sources: Vec::with_capacity(artifacts.len()),
    };
    for (request_index, artifact) in artifacts.iter().enumerate() {
        let request = StageRequest {
            artifact,
            index: request_index,
        };
        if let Err(cause) = stage_request(cache, adapter, request, &mut batch) {
            let candidates = batch
                .candidates
                .into_iter()
                .map(|item| item.candidate)
                .collect();
            return Err(Box::new(rollback_failure(
                adapter,
                candidates,
                request_index,
                cause,
            )));
        }
    }
    Ok(batch)
}

fn stage_request<Adapter>(
    cache: &DirectFusedNativeLeaseCache,
    adapter: &mut Adapter,
    request: StageRequest<'_>,
    batch: &mut StagedBatch,
) -> BatchCauseResult<Adapter>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let artifact = request.artifact;
    let key = artifact.key();
    if let Some(entry) = cache.active.iter().find(|entry| entry.key == *key) {
        if entry.resident.artifact() != artifact {
            return Err(BatchFailureCause::Identity);
        }
        batch.sources.push(BatchRequestSource::Active(Box::new(
            DirectFusedNativeLease {
                key: entry.key.clone(),
                resident: Arc::clone(&entry.resident),
            },
        )));
        return Ok(());
    }
    if let Some((index, candidate)) = batch
        .candidates
        .iter()
        .enumerate()
        .find(|(_, item)| item.candidate.key == *key)
    {
        if candidate.candidate.owner.artifact() != artifact {
            return Err(BatchFailureCause::Identity);
        }
        batch
            .sources
            .push(BatchRequestSource::Staged { first: false, index });
        return Ok(());
    }
    stage_new_candidate(cache, adapter, request, batch)
}

fn stage_new_candidate<Adapter>(
    cache: &DirectFusedNativeLeaseCache,
    adapter: &mut Adapter,
    request: StageRequest<'_>,
    batch: &mut StagedBatch,
) -> BatchCauseResult<Adapter>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let artifact = request.artifact;
    let owner = DirectFusedNativeExecutableOwner::load(adapter, artifact)
        .map_err(BatchFailureCause::Load)?;
    let resident_weight = owner.resident_weight();
    let weight = NativeExecutableSequenceWeight::from_parts(
        resident_weight.mapped_bytes(),
        resident_weight.mappings(),
    );
    if let Some(error) = cache.limits.candidate_error(weight) {
        batch.candidates.push(StagedCandidate {
            candidate: CacheCandidate {
                key: artifact.key().clone(),
                owner,
                weight,
            },
            request_index: request.index,
        });
        return Err(BatchFailureCause::Capacity(error));
    }
    let index = batch.candidates.len();
    batch.candidates.push(StagedCandidate {
        candidate: CacheCandidate {
            key: artifact.key().clone(),
            owner,
            weight,
        },
        request_index: request.index,
    });
    batch
        .sources
        .push(BatchRequestSource::Staged { first: true, index });
    Ok(())
}

fn preflight_publication<Adapter>(
    cache: &DirectFusedNativeLeaseCache,
    adapter: &mut Adapter,
    batch: StagedBatch,
) -> BatchAdapterResult<Adapter, PreparedBatch>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut state = preflight_state(cache);
    let metadata = batch
        .candidates
        .iter()
        .map(|item| {
            (
                item.request_index,
                item.candidate.key.clone(),
                item.candidate.weight,
            )
        })
        .collect::<Vec<_>>();
    let mut plans = Vec::with_capacity(metadata.len());
    for (request_index, key, weight) in metadata {
        match preflight_candidate(cache, &mut state, key, weight) {
            Ok(plan) => plans.push(plan),
            Err(cause) => {
                let candidates = batch
                    .candidates
                    .into_iter()
                    .map(|item| item.candidate)
                    .collect();
                return Err(Box::new(rollback_failure(
                    adapter,
                    candidates,
                    request_index,
                    cause,
                )));
            },
        }
    }
    Ok(PreparedBatch {
        candidates: batch.candidates,
        plans,
        sources: batch.sources,
    })
}

fn preflight_candidate<E>(
    cache: &DirectFusedNativeLeaseCache,
    state: &mut PreflightState,
    key: NativeArtifactKey,
    weight: NativeExecutableSequenceWeight,
) -> PreflightResult<E> {
    let mut victims = Vec::new();
    let mut retired = Vec::new();
    while cache.limits.projected_exceeds(state.usage, weight) {
        let Some(victim) = state.active.pop_front() else {
            return Err(BatchFailureCause::Blocked(Box::new(
                DirectFusedNativeLeaseCacheBlock {
                    limits: cache.limits,
                    retired_keys: state.retired_keys.clone(),
                    usage: state.usage,
                },
            )));
        };
        if victim.protected {
            retired.push(victim.key.clone());
            state.retired_keys.push(victim.key.clone());
        } else {
            state.usage.remove(victim.weight);
        }
        victims.push(PlannedVictim {
            key: victim.key,
            retire: victim.protected,
        });
    }
    state
        .usage
        .add(weight)
        .map_err(BatchFailureCause::Capacity)?;
    state.active.push_back(SimulatedActive {
        key,
        protected: true,
        weight,
    });
    Ok(PublishPlan {
        retired,
        usage_after: state.usage,
        victims,
    })
}

fn preflight_state(cache: &DirectFusedNativeLeaseCache) -> PreflightState {
    PreflightState {
        active: cache
            .active
            .iter()
            .map(|entry| SimulatedActive {
                key: entry.key.clone(),
                protected: Arc::strong_count(&entry.resident) > 1,
                weight: entry.weight,
            })
            .collect(),
        retired_keys: cache
            .retired
            .iter()
            .map(|entry| entry.key.clone())
            .collect(),
        usage: cache.usage,
    }
}

fn publish_staged<Adapter>(
    cache: &mut DirectFusedNativeLeaseCache,
    adapter: &mut Adapter,
    prepared: PreparedBatch,
) -> DirectFusedNativeLeaseCacheBatchResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let request_count = prepared.sources.len();
    let mut transferred = Vec::new();
    let mut published = Vec::with_capacity(prepared.candidates.len());
    for (staged, plan) in prepared.candidates.into_iter().zip(&prepared.plans) {
        if !apply_victims(cache, plan, &mut transferred) {
            return Err(Box::new(invariant_failure(request_count)));
        }
        cache.usage = plan.usage_after;
        let candidate = staged.candidate;
        let resident = Arc::new(candidate.owner);
        cache.active.push_back(CacheValue {
            key: candidate.key.clone(),
            resident: Arc::clone(&resident),
            weight: candidate.weight,
        });
        published.push((candidate.key, resident));
    }
    let Some(acquisitions) =
        build_acquisitions(prepared.sources, &published, &prepared.plans)
    else {
        return Err(Box::new(invariant_failure(request_count)));
    };
    finish_publication(adapter, acquisitions, transferred, request_count)
}

fn apply_victims(
    cache: &mut DirectFusedNativeLeaseCache,
    plan: &PublishPlan,
    transferred: &mut Vec<TransferredResident>,
) -> bool {
    for victim_plan in &plan.victims {
        let Some(victim) = cache.active.pop_front() else {
            return false;
        };
        if victim.key != victim_plan.key {
            cache.active.push_front(victim);
            return false;
        }
        if victim_plan.retire {
            cache.retired.push_back(victim);
            continue;
        }
        let key = victim.key;
        let weight = victim.weight;
        match Arc::try_unwrap(victim.resident) {
            Ok(owner) => transferred.push((key, owner)),
            Err(resident) => {
                cache
                    .active
                    .push_front(CacheValue { key, resident, weight });
                return false;
            },
        }
    }
    true
}

fn build_acquisitions(
    sources: Vec<BatchRequestSource>,
    published: &[PublishedResident],
    plans: &[PublishPlan],
) -> Option<Vec<DirectFusedNativeLeaseCacheAcquisition>> {
    sources
        .into_iter()
        .map(|source| match source {
            BatchRequestSource::Active(lease) => {
                Some(DirectFusedNativeLeaseCacheAcquisition {
                    disposition: DirectFusedNativeLeaseCacheDisposition::Hit,
                    lease: *lease,
                })
            },
            BatchRequestSource::Staged { first, index } => {
                staged_acquisition(first, index, published, plans)
            },
        })
        .collect()
}

fn staged_acquisition(
    first: bool,
    index: usize,
    published: &[PublishedResident],
    plans: &[PublishPlan],
) -> Option<DirectFusedNativeLeaseCacheAcquisition> {
    let (key, resident) = published.get(index)?;
    let plan = plans.get(index)?;
    let disposition = if first {
        DirectFusedNativeLeaseCacheDisposition::Inserted {
            evicted: plan
                .victims
                .iter()
                .map(|victim| victim.key.clone())
                .collect(),
            retired: plan.retired.clone(),
        }
    } else {
        DirectFusedNativeLeaseCacheDisposition::Hit
    };
    Some(DirectFusedNativeLeaseCacheAcquisition {
        disposition,
        lease: DirectFusedNativeLease {
            key: key.clone(),
            resident: Arc::clone(resident),
        },
    })
}

fn finish_publication<Adapter>(
    adapter: &mut Adapter,
    acquisitions: Vec<DirectFusedNativeLeaseCacheAcquisition>,
    transferred: Vec<TransferredResident>,
    request_count: usize,
) -> DirectFusedNativeLeaseCacheBatchResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let committed =
        DirectFusedNativeLeaseCacheBatchAcquisition { acquisitions };
    match release_transferred(adapter, transferred) {
        Ok(()) => Ok(committed),
        Err(failure) => {
            Err(Box::new(DirectFusedNativeLeaseCacheBatchFailure {
                cause: BatchFailureCause::Cleanup(failure),
                committed: Some(committed),
                index: request_count,
                published: true,
                rollback_cleanup: None,
            }))
        },
    }
}

fn release_transferred<Adapter>(
    adapter: &mut Adapter,
    transferred: Vec<TransferredResident>,
) -> CleanupResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut failures = Vec::new();
    let mut released_keys = Vec::new();
    for (key, owner) in transferred {
        match owner.release(adapter) {
            Ok(()) => released_keys.push(key),
            Err(failure) => {
                failures.push(DirectFusedNativeLeaseCacheEntryReleaseFailure {
                    failure: *failure,
                    key,
                });
            },
        }
    }
    if failures.is_empty() {
        Ok(())
    } else {
        Err(Box::new(DirectFusedNativeLeaseCacheReleaseFailure {
            failures,
            released_keys,
            retained_keys: Vec::new(),
        }))
    }
}

fn rollback_failure<Adapter>(
    adapter: &mut Adapter,
    staged: Vec<CacheCandidate>,
    index: usize,
    cause: BatchFailureCause<Adapter::Error>,
) -> BatchFailure<Adapter>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let rollback_cleanup = cleanup_staged(adapter, staged).err();
    DirectFusedNativeLeaseCacheBatchFailure {
        cause,
        committed: None,
        index,
        published: false,
        rollback_cleanup,
    }
}

fn cleanup_staged<Adapter>(
    adapter: &mut Adapter,
    staged: Vec<CacheCandidate>,
) -> CleanupResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let transferred = staged
        .into_iter()
        .rev()
        .map(|candidate| (candidate.key, candidate.owner))
        .collect();
    release_transferred(adapter, transferred)
}

const fn invariant_failure<E>(
    index: usize,
) -> DirectFusedNativeLeaseCacheBatchFailure<E> {
    DirectFusedNativeLeaseCacheBatchFailure {
        cause: BatchFailureCause::Invariant,
        committed: None,
        index,
        published: true,
        rollback_cleanup: None,
    }
}
