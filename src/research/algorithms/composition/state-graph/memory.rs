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
//   - Persistent profile-memory research representation over exact trace
//   - deltas.
// - Must-Not:
//   - Replace runtime memory, skip before-value validation, or claim production
//   - cost.
// - Allows:
//   - Inputs: validated `ProfileMachineState` roots and `ProfileMemoryDelta`
//   - steps.
//   - Outputs: shared-root memory views, exact reads, and oracle
//   - materialization.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when compaction/indexing strategies need independent evidence.
// - Merge-When:
//   - Merge when a production state graph adopts the proved persistent model.
// - Summary:
//   - Represents large profile memories as one root plus at-most-two-cell
//   - patches.
// - Description:
//   - Every patch checks trace `before` values against the current persistent
//   - view.
// - Usage:
//   - Research baseline consumed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Materialization is an oracle operation, not the expected per-step path.
//

//! Persistent large-memory research representation driven by exact VM deltas.

use std::sync::Arc;

use malbolge::{ProfileMachineState, ProfileMemoryDelta, ProfileMemoryWrite};

/// One immutable persistent profile-memory view.
#[derive(Clone, Debug)]
pub struct PersistentProfileMemory {
    base: Arc<[u32]>,
    depth: usize,
    tail: Option<Arc<PatchNode>>,
}

/// Failure while validating or reconstructing a persistent memory view.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PersistentMemoryError {
    /// A trace patch address lies outside the root memory domain.
    AddressOutOfRange {
        /// Invalid profile-width address.
        address: u32,
    },
    /// A trace patch does not match the memory value it claims to replace.
    BeforeValueMismatch {
        /// Profile-width address being patched.
        address: u32,
        /// Value required by the trace record.
        expected: u32,
        /// Value observed through the persistent view.
        observed: u32,
    },
    /// Host indexing could not represent an otherwise admitted profile address.
    IndexInvariant,
}

#[derive(Clone, Debug)]
struct PatchNode {
    delta: ProfileMemoryDelta,
    parent: Option<Arc<Self>>,
}

impl PersistentProfileMemory {
    /// Applies one exact trace delta and returns a new shared-root memory view.
    ///
    /// Empty deltas reuse the current view without increasing patch depth.
    ///
    /// # Errors
    ///
    /// Returns [`PersistentMemoryError`] when an address is invalid or a trace
    /// `before` value does not match the current persistent memory view.
    pub fn apply(
        &self,
        delta: ProfileMemoryDelta,
    ) -> Result<Self, PersistentMemoryError> {
        self.validate_delta(delta)?;
        if delta.changed_cells() == 0 {
            return Ok(self.clone());
        }
        Ok(Self {
            base: Arc::clone(&self.base),
            depth: self.depth.saturating_add(1),
            tail: Some(Arc::new(PatchNode {
                delta,
                parent: self.tail.clone(),
            })),
        })
    }

    /// Creates a persistent memory root from one validated profile checkpoint.
    #[must_use]
    pub fn from_state(state: &ProfileMachineState) -> Self {
        Self {
            base: Arc::from(state.memory()),
            depth: 0,
            tail: None,
        }
    }

    /// Materializes the exact complete memory image for oracle comparison.
    ///
    /// # Errors
    ///
    /// Returns [`PersistentMemoryError`] if a stored address cannot index the
    /// root memory. Valid deltas created through [`Self::apply`] cannot
    /// mismatch.
    pub fn materialize(&self) -> Result<Vec<u32>, PersistentMemoryError> {
        let mut memory = self.base.to_vec();
        let mut deltas = Vec::with_capacity(self.depth);
        let mut node = self.tail.as_ref().map(Arc::clone);
        while let Some(current) = node {
            deltas.push(current.delta);
            node = current.parent.as_ref().map(Arc::clone);
        }
        for delta in deltas.into_iter().rev() {
            apply_materialized_delta(&mut memory, delta)?;
        }
        Ok(memory)
    }

    /// Returns the number of non-empty immutable patches after the root.
    #[must_use]
    pub const fn patch_depth(&self) -> usize {
        self.depth
    }

    /// Reads one profile-width address from the newest patch or shared root.
    ///
    /// # Errors
    ///
    /// Returns [`PersistentMemoryError::AddressOutOfRange`] outside the root
    /// memory domain or [`PersistentMemoryError::IndexInvariant`] when host
    /// indexing cannot represent the admitted address.
    pub fn read(&self, address: u32) -> Result<u32, PersistentMemoryError> {
        let index = usize::try_from(address)
            .map_err(|_error| PersistentMemoryError::IndexInvariant)?;
        if index >= self.base.len() {
            return Err(PersistentMemoryError::AddressOutOfRange { address });
        }
        let mut node = self.tail.as_deref();
        while let Some(current) = node {
            if let Some(value) = delta_value(current.delta, address) {
                return Ok(value);
            }
            node = current.parent.as_deref();
        }
        self.base
            .get(index)
            .copied()
            .ok_or(PersistentMemoryError::IndexInvariant)
    }

    fn validate_delta(
        &self,
        delta: ProfileMemoryDelta,
    ) -> Result<(), PersistentMemoryError> {
        for write in [delta.data, delta.encryption].into_iter().flatten() {
            validate_write(self, write)?;
        }
        Ok(())
    }
}

fn apply_materialized_delta(
    memory: &mut [u32],
    delta: ProfileMemoryDelta,
) -> Result<(), PersistentMemoryError> {
    for write in [delta.data, delta.encryption].into_iter().flatten() {
        let index = usize::try_from(write.address)
            .map_err(|_error| PersistentMemoryError::IndexInvariant)?;
        let slot = memory.get_mut(index).ok_or(
            PersistentMemoryError::AddressOutOfRange { address: write.address },
        )?;
        *slot = write.after;
    }
    Ok(())
}

const fn delta_value(delta: ProfileMemoryDelta, address: u32) -> Option<u32> {
    if let Some(write) = delta.encryption
        && write.address == address
    {
        return Some(write.after);
    }
    if let Some(write) = delta.data
        && write.address == address
    {
        return Some(write.after);
    }
    None
}

fn validate_write(
    memory: &PersistentProfileMemory,
    write: ProfileMemoryWrite,
) -> Result<(), PersistentMemoryError> {
    let observed = memory.read(write.address)?;
    if observed == write.before {
        Ok(())
    } else {
        Err(PersistentMemoryError::BeforeValueMismatch {
            address: write.address,
            expected: write.before,
            observed,
        })
    }
}
