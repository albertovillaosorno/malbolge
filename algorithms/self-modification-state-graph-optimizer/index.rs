// File:
//   - index.rs
// Path:
//   - algorithms/self-modification-state-graph-optimizer/index.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Bounded-read persistent overlay research for current profile memory.
// - Must-Not:
//   - Replace runtime memory or claim support beyond the 24-bit research bound.
// - Allows:
//   - Inputs: validated profile checkpoints and exact profile memory deltas.
//   - Outputs: shared-root indexed reads, patches, and oracle materialization.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when a generalized profile-width radix needs independent ownership.
// - Merge-When:
//   - Merge when production state graphs adopt the proved indexed
//     representation.
// - Summary:
//   - Adds a four-level 64-way persistent override index above one shared root.
// - Description:
//   - Reads have bounded radix depth independent of patch-history length.
// - Usage:
//   - Research candidate composed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Every trace `before` value is validated before any overlay update
//     commits.
//
// Related documents:
// - math/algorithms/self-modification-state-graph-optimizer.tex
// - algorithms/self-modification-state-graph-optimizer/memory.rs
//
// Large file:
//   - false

//! Four-level persistent radix overlay for current profile memory research.

use std::array::from_fn;
use std::sync::Arc;

use malbolge::{ProfileMachineState, ProfileMemoryDelta, ProfileMemoryWrite};

const RADIX_CAPACITY: usize = 16_777_216;
const RADIX_FANOUT: usize = 64;
const RADIX_LEVELS: u8 = 4;
const RADIX_MASK: u32 = 63;
const RADIX_SHIFT: u32 = 6;

type RadixChildren = [Option<Arc<RadixNode>>; RADIX_FANOUT];
type RadixValues = [Option<u32>; RADIX_FANOUT];

/// Failure while applying or reading the bounded persistent index.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IndexedMemoryError {
    /// One address lies outside the validated root memory domain.
    AddressOutOfRange {
        /// Rejected profile-width address.
        address: u32,
    },
    /// A trace patch does not match the value it claims to replace.
    BeforeValueMismatch {
        /// Profile-width address being patched.
        address: u32,
        /// Value required by the trace record.
        expected: u32,
        /// Value observed through the indexed view.
        observed: u32,
    },
    /// Internal radix shape or host-index conversion violated an invariant.
    IndexInvariant,
    /// The checkpoint exceeds the admitted 24-bit research index capacity.
    UnsupportedMemoryLength {
        /// Maximum memory words admitted by this research candidate.
        maximum: usize,
        /// Memory words carried by the supplied checkpoint.
        observed: usize,
    },
}

/// Persistent current-profile memory with one full root and sparse overrides.
#[derive(Clone, Debug)]
pub struct IndexedProfileMemory {
    base: Arc<[u32]>,
    overlay: Option<Arc<RadixNode>>,
    patches: usize,
}

#[derive(Clone, Debug)]
enum RadixNode {
    Branch(Box<RadixChildren>),
    Leaf(Box<RadixValues>),
}

impl IndexedProfileMemory {
    /// Applies one exact trace delta to a new persistent radix root.
    ///
    /// # Errors
    ///
    /// Returns [`IndexedMemoryError`] when an address is invalid, a trace
    /// `before` value mismatches, or an internal radix invariant fails.
    pub fn apply(
        &self,
        delta: ProfileMemoryDelta,
    ) -> Result<Self, IndexedMemoryError> {
        for write in [delta.data, delta.encryption].into_iter().flatten() {
            validate_write(self, write)?;
        }
        if delta.changed_cells() == 0 {
            return Ok(self.clone());
        }
        let mut overlay = self.overlay.clone();
        for write in [delta.data, delta.encryption].into_iter().flatten() {
            overlay = Some(update_node(
                overlay.as_ref(),
                write.address,
                write.after,
                RADIX_LEVELS.saturating_sub(1),
            )?);
        }
        Ok(Self {
            base: Arc::clone(&self.base),
            overlay,
            patches: self.patches.saturating_add(1),
        })
    }

    /// Constructs the bounded radix candidate over one validated checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`IndexedMemoryError::UnsupportedMemoryLength`] above 24 bits.
    pub fn from_state(
        state: &ProfileMachineState,
    ) -> Result<Self, IndexedMemoryError> {
        if state.memory().len() > RADIX_CAPACITY {
            return Err(IndexedMemoryError::UnsupportedMemoryLength {
                maximum: RADIX_CAPACITY,
                observed: state.memory().len(),
            });
        }
        Ok(Self {
            base: Arc::from(state.memory()),
            overlay: None,
            patches: 0,
        })
    }

    /// Materializes the exact complete memory image for oracle comparison.
    ///
    /// # Errors
    ///
    /// Returns [`IndexedMemoryError`] if stored radix structure violates the
    /// admitted shape or points outside the validated base memory.
    pub fn materialize(&self) -> Result<Vec<u32>, IndexedMemoryError> {
        let mut memory = self.base.to_vec();
        if let Some(root) = self.overlay.as_ref() {
            materialize_node(
                root,
                RADIX_LEVELS.saturating_sub(1),
                0,
                &mut memory,
            )?;
        }
        Ok(memory)
    }

    /// Returns the number of non-empty semantic deltas applied to this view.
    #[must_use]
    pub const fn patch_count(&self) -> usize {
        self.patches
    }

    /// Reads one address through at most four radix chunks before the root.
    ///
    /// # Errors
    ///
    /// Returns [`IndexedMemoryError::AddressOutOfRange`] outside the base
    /// memory or [`IndexedMemoryError::IndexInvariant`] for malformed radix
    /// structure.
    pub fn read(&self, address: u32) -> Result<u32, IndexedMemoryError> {
        let index = checked_base_index(&self.base, address)?;
        if let Some(root) = self.overlay.as_ref()
            && let Some(value) =
                lookup_node(root, address, RADIX_LEVELS.saturating_sub(1))?
        {
            return Ok(value);
        }
        self.base
            .get(index)
            .copied()
            .ok_or(IndexedMemoryError::IndexInvariant)
    }
}

fn checked_base_index(
    base: &[u32],
    address: u32,
) -> Result<usize, IndexedMemoryError> {
    let index = usize::try_from(address)
        .map_err(|_error| IndexedMemoryError::IndexInvariant)?;
    if index < base.len() {
        Ok(index)
    } else {
        Err(IndexedMemoryError::AddressOutOfRange { address })
    }
}

fn empty_children() -> Box<RadixChildren> {
    Box::new(from_fn(|_index| None))
}

fn lookup_node(
    node: &RadixNode,
    address: u32,
    level: u8,
) -> Result<Option<u32>, IndexedMemoryError> {
    let index = radix_index(address, level)?;
    if level == 0 {
        return match node {
            RadixNode::Leaf(values) => Ok(values.get(index).copied().flatten()),
            RadixNode::Branch(_children) => {
                Err(IndexedMemoryError::IndexInvariant)
            },
        };
    }
    match node {
        RadixNode::Branch(children) => match children.get(index) {
            Some(Some(child)) => {
                lookup_node(child, address, level.saturating_sub(1))
            },
            Some(None) => Ok(None),
            None => Err(IndexedMemoryError::IndexInvariant),
        },
        RadixNode::Leaf(_values) => Err(IndexedMemoryError::IndexInvariant),
    }
}

fn materialize_leaf(
    values: &RadixValues,
    prefix: u32,
    memory: &mut [u32],
) -> Result<(), IndexedMemoryError> {
    for (index, word) in values
        .iter()
        .enumerate()
        .filter_map(|(index, value)| value.map(|word| (index, word)))
    {
        let low = u32::try_from(index)
            .map_err(|_error| IndexedMemoryError::IndexInvariant)?;
        let address = prefix | low;
        let slot = checked_base_index(memory, address)?;
        let target = memory
            .get_mut(slot)
            .ok_or(IndexedMemoryError::IndexInvariant)?;
        *target = word;
    }
    Ok(())
}

fn materialize_node(
    node: &RadixNode,
    level: u8,
    prefix: u32,
    memory: &mut [u32],
) -> Result<(), IndexedMemoryError> {
    if level == 0 {
        return match node {
            RadixNode::Leaf(values) => materialize_leaf(values, prefix, memory),
            RadixNode::Branch(_children) => {
                Err(IndexedMemoryError::IndexInvariant)
            },
        };
    }
    match node {
        RadixNode::Branch(children) => {
            let shift = u32::from(level).saturating_mul(RADIX_SHIFT);
            for (index, child) in children.iter().enumerate() {
                if let Some(next) = child {
                    let chunk = u32::try_from(index)
                        .map_err(|_error| IndexedMemoryError::IndexInvariant)?;
                    let next_prefix = prefix | (chunk << shift);
                    materialize_node(
                        next,
                        level.saturating_sub(1),
                        next_prefix,
                        memory,
                    )?;
                }
            }
            Ok(())
        },
        RadixNode::Leaf(_values) => Err(IndexedMemoryError::IndexInvariant),
    }
}

fn radix_index(address: u32, level: u8) -> Result<usize, IndexedMemoryError> {
    let shift = u32::from(level).saturating_mul(RADIX_SHIFT);
    let chunk = address.checked_shr(shift).unwrap_or(0) & RADIX_MASK;
    usize::try_from(chunk).map_err(|_error| IndexedMemoryError::IndexInvariant)
}

fn update_node(
    current: Option<&Arc<RadixNode>>,
    address: u32,
    value: u32,
    level: u8,
) -> Result<Arc<RadixNode>, IndexedMemoryError> {
    let index = radix_index(address, level)?;
    if level == 0 {
        let mut values = match current.map(Arc::as_ref) {
            Some(RadixNode::Leaf(existing)) => existing.clone(),
            Some(RadixNode::Branch(_children)) => {
                return Err(IndexedMemoryError::IndexInvariant);
            },
            None => Box::new([None; RADIX_FANOUT]),
        };
        let slot = values
            .get_mut(index)
            .ok_or(IndexedMemoryError::IndexInvariant)?;
        *slot = Some(value);
        return Ok(Arc::new(RadixNode::Leaf(values)));
    }
    let mut children = match current.map(Arc::as_ref) {
        Some(RadixNode::Branch(existing)) => existing.clone(),
        Some(RadixNode::Leaf(_values)) => {
            return Err(IndexedMemoryError::IndexInvariant);
        },
        None => empty_children(),
    };
    let previous = children
        .get(index)
        .ok_or(IndexedMemoryError::IndexInvariant)?;
    let updated = update_node(
        previous.as_ref(),
        address,
        value,
        level.saturating_sub(1),
    )?;
    let slot = children
        .get_mut(index)
        .ok_or(IndexedMemoryError::IndexInvariant)?;
    *slot = Some(updated);
    Ok(Arc::new(RadixNode::Branch(children)))
}

fn validate_write(
    memory: &IndexedProfileMemory,
    write: ProfileMemoryWrite,
) -> Result<(), IndexedMemoryError> {
    let observed = memory.read(write.address)?;
    if observed == write.before {
        Ok(())
    } else {
        Err(IndexedMemoryError::BeforeValueMismatch {
            address: write.address,
            expected: write.before,
            observed,
        })
    }
}
