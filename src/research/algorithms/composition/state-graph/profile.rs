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
//   - Collision-safe exact identity for validated profile-machine checkpoints.
// - Must-Not:
//   - Revalidate checkpoint fields or claim sparse/current-state reductions.
// - Allows:
//   - Inputs: validated `ProfileMachineState` values.
//   - Outputs: exact node IDs and deduplication statistics.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when a proved scalable reduced-state representation is admitted.
// - Merge-When:
//   - Merge when production native tiers own identical checkpoint identity.
// - Summary:
//   - Extends the exact graph baseline to canonical scalable checkpoints.
// - Description:
//   - Hash collisions always fall back to complete checkpoint equality.
// - Usage:
//   - Research baseline consumed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Stores complete checkpoints; no memory-size optimization is claimed.
//

//! Collision-safe exact graph identity for validated profile checkpoints.

use std::collections::BTreeMap;

use malbolge::{ProfileMachineState, Termination};

const FNV_OFFSET: u64 = 14_695_981_039_346_656_037;
const FNV_PRIME: u64 = 1_099_511_628_211;

type ProfileDigestFunction = fn(&ProfileMachineState) -> u64;

/// Stable node identifier inside one exact profile-state graph.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProfileNodeId(u32);

/// Exact profile checkpoint graph with collision-confirmed identity.
#[derive(Clone, Debug)]
pub struct ProfileStateGraph {
    buckets: BTreeMap<u64, Vec<ProfileNodeId>>,
    deduplicated_observations: usize,
    digest: ProfileDigestFunction,
    nodes: Vec<ProfileMachineState>,
    observations: usize,
}

/// Failure while indexing an exact profile checkpoint.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProfileStateGraphError {
    /// Unique checkpoint count exceeded the stable identifier domain.
    NodeIdentityOverflow,
}

impl ProfileNodeId {
    /// Returns the stable zero-based node index.
    #[must_use]
    pub const fn value(self) -> u32 {
        self.0
    }
}

impl ProfileStateGraph {
    /// Returns how many observations reused an exact checkpoint.
    #[must_use]
    pub const fn deduplicated_observations(&self) -> usize {
        self.deduplicated_observations
    }

    fn existing_node(
        &self,
        digest: u64,
        state: &ProfileMachineState,
    ) -> Result<Option<ProfileNodeId>, ProfileStateGraphError> {
        let Some(candidates) = self.buckets.get(&digest) else {
            return Ok(None);
        };
        for candidate in candidates {
            let index =
                usize::try_from(candidate.value()).map_err(|_error| {
                    ProfileStateGraphError::NodeIdentityOverflow
                })?;
            if self.nodes.get(index) == Some(state) {
                return Ok(Some(*candidate));
            }
        }
        Ok(None)
    }

    /// Creates the default graph using a deterministic complete-state digest.
    #[must_use]
    pub fn new() -> Self {
        Self::with_digest(profile_state_digest)
    }

    /// Returns the number of exact unique checkpoints.
    #[must_use]
    pub const fn node_count(&self) -> usize {
        self.nodes.len()
    }

    /// Returns the total number of checkpoint observations offered to the
    /// graph.
    #[must_use]
    pub const fn observations(&self) -> usize {
        self.observations
    }

    /// Records one validated checkpoint using collision-confirmed equality.
    ///
    /// # Errors
    ///
    /// Returns [`ProfileStateGraphError::NodeIdentityOverflow`] when the stable
    /// zero-based node identifier domain is exhausted.
    pub fn observe(
        &mut self,
        state: ProfileMachineState,
    ) -> Result<ProfileNodeId, ProfileStateGraphError> {
        self.observations = self.observations.saturating_add(1);
        let digest = (self.digest)(&state);
        if let Some(candidate) = self.existing_node(digest, &state)? {
            self.deduplicated_observations =
                self.deduplicated_observations.saturating_add(1);
            return Ok(candidate);
        }
        let raw_id = u32::try_from(self.nodes.len())
            .map_err(|_error| ProfileStateGraphError::NodeIdentityOverflow)?;
        let node_id = ProfileNodeId(raw_id);
        self.nodes.push(state);
        self.buckets.entry(digest).or_default().push(node_id);
        Ok(node_id)
    }

    /// Creates a graph with an explicit digest for adversarial collision tests.
    #[must_use]
    pub fn with_digest(digest: ProfileDigestFunction) -> Self {
        Self {
            buckets: BTreeMap::new(),
            deduplicated_observations: 0,
            digest,
            nodes: Vec::new(),
            observations: 0,
        }
    }
}

impl Default for ProfileStateGraph {
    fn default() -> Self {
        Self::new()
    }
}

/// Digest function deliberately mapping every profile checkpoint to one bucket.
#[must_use]
pub const fn constant_profile_collision_digest(
    _state: &ProfileMachineState,
) -> u64 {
    0
}

fn hash_byte(hash: u64, value: u8) -> u64 {
    (hash ^ u64::from(value)).wrapping_mul(FNV_PRIME)
}

fn hash_bytes(mut hash: u64, values: &[u8]) -> u64 {
    for value in values {
        hash = hash_byte(hash, *value);
    }
    hash
}

fn hash_termination(hash: u64, termination: Option<Termination>) -> u64 {
    let tag = match termination {
        None => 0,
        Some(Termination::HaltInstruction) => 1,
        Some(Termination::NonGraphicalCell) => 2,
    };
    hash_byte(hash, tag)
}

fn profile_state_digest(state: &ProfileMachineState) -> u64 {
    let mut hash = FNV_OFFSET;
    hash = hash_bytes(hash, state.profile().fingerprint().as_bytes());
    let io = state.io();
    hash = hash_bytes(hash, io.input());
    hash = hash_bytes(hash, &io.input_consumed().to_le_bytes());
    hash = hash_bytes(hash, io.output());
    hash = hash_termination(hash, io.termination());
    let registers = state.registers();
    hash = hash_bytes(hash, &registers.accumulator.to_le_bytes());
    hash = hash_bytes(hash, &registers.code_pointer.to_le_bytes());
    hash = hash_bytes(hash, &registers.data_pointer.to_le_bytes());
    for word in state.memory() {
        hash = hash_bytes(hash, &word.to_le_bytes());
    }
    hash
}
