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
//   - Source-authenticated frame, operation and phi-copy address relocation.
// - Must-Not:
//   - Infer a physical source length, execute guest writes or publish a target.
// - Allows:
//   - Inputs: canonical typed source, final code length and proposed frame
//     base.
//   - Outputs: absolute N15 data addresses with preserved typed source
//     identity.
//   - Side effects: none.
// - Split-When:
//   - Real guest opcodes and mutable control relocation join physical linking.
// - Merge-When:
//   - An independently verified full guest code/data linker owns relocation.
// - Summary:
//   - Computes exact disjoint data addresses for all checksum operations.
// - Description:
//   - The proposed final code length is an external obligation, not verified
//     code; the results cannot be executed without physical target linking.
// - Usage:
//   - Relocate only source-locked canonical bytes, never caller-forged plans.
// - Defaults:
//   - Reject code/data overlap and the first address past target memory.
//
//! Checked guest data relocation, not executable Malbolge code generation.

use std::collections::{BTreeMap, BTreeSet};

use super::phi_edge_transfers::PrelinkCfgPlan;
use super::state_storage::{
    GuestCellCopy, GuestFramePlacement, GuestStateFrame, GuestStorageValue,
    placed_cell, validate_frame_placement,
};
use super::ternary::TernaryCfgScalarKind;
use super::typed::{Instruction, SourceSpan, Terminator};
use super::{TypedCfgAdapterError, prepare_canonical_dynamic_cfg};

/// One exact literal word requiring physical guest materialization.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestPlacedLiteralCell {
    /// Absolute N15 guest-memory address, not a code instruction.
    pub address: u32,
    /// Exact 15-trit value the future guest instruction must write.
    pub word: u32,
}

/// One exact source SSA scalar with a checked contiguous N15 word interval.
///
/// This preserves 32-bit signed/unsigned values across *two* guest words;
/// an instruction encoder must not silently truncate these to one word.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestPlacedOperand {
    /// First absolute N15 word address of this canonical typed SSA value.
    pub address: u32,
    /// Original scalar type, including signedness and Boolean distinction.
    pub type_kind: TernaryCfgScalarKind,
    /// Canonical source-function SSA value identity.
    pub value: u32,
    /// Exact number of N15 words required by this value.
    pub words: u32,
}

impl GuestPlacedOperand {
    /// Returns an exact word address or refuses an out-of-range index.
    #[must_use]
    pub fn cell_address(self, index: u32) -> Option<u32> {
        (index < self.words)
            .then(|| self.address.checked_add(index))
            .flatten()
    }
}

/// One instruction's typed runtime work and physically located operands.
///
/// These are not target instructions; the physical linker must implement
/// the preserved operation, including its full-width reads and writes.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestPlacedInstruction {
    /// Exact literal write obligations, in canonical instruction order.
    pub constant_cells: Vec<GuestPlacedLiteralCell>,
    /// Authenticated typed instruction, not a host-computed result.
    pub instruction: Instruction,
    /// Exact source-ordered, width-preserving input operands.
    pub reads: Vec<GuestPlacedOperand>,
    /// Original source coordinates for diagnostics and translation evidence.
    pub span: SourceSpan,
    /// Full-width destination SSA scalar, absent for output effects.
    pub write: Option<GuestPlacedOperand>,
}

/// One source CFG edge with addressed, two-phase phi-write obligations.
///
/// The successor is a symbolic block ID, never an executable code address.
/// The target linker must first execute every snapshot and then every commit
/// *only* when this particular edge is reached by guest control.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestPlacedControlEdge {
    /// Execute these writes after all snapshots, never interleaved with them.
    pub commits: Vec<GuestPlacedCellCopy>,
    /// Read all originals into disjoint temporary cells first.
    pub snapshots: Vec<GuestPlacedCellCopy>,
    /// Original target block identity; no physical jump address is assigned.
    pub successor: u32,
}

/// A source-authenticated control terminator with edge-local phi writes.
///
/// This is an operand-placement handoff, not a real guest jump or branch.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum GuestPlacedControl {
    /// Both possible successors; the host has not selected a branch arm.
    Branch {
        /// Unselected false edge and its own two-phase phi copies.
        when_false: GuestPlacedControlEdge,
        /// Unselected true edge and its own two-phase phi copies.
        when_true: GuestPlacedControlEdge,
    },
    /// One unconditional successor, optionally carrying phi copies.
    Jump {
        /// The exact source successor and its addressed writes.
        edge: GuestPlacedControlEdge,
    },
    /// Terminate the source function; no target instructions are emitted.
    Return,
}

/// One original block's absolute operand and control-cell locations.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestPlacedBlock {
    /// Canonical source block identity.
    pub block: u32,
    /// Absolute address containing the branch Boolean, if any.
    pub condition: Option<GuestPlacedOperand>,
    /// Symbolic control with source-authenticated, edge-local phi obligations.
    pub control: GuestPlacedControl,
    /// Canonical source function identity.
    pub function: u32,
    /// Relocated operations in exact source-authenticated order.
    pub instructions: Vec<GuestPlacedInstruction>,
    /// Absolute address of the return value, if any.
    pub return_value: Option<GuestPlacedOperand>,
}

/// One precise guest memory copy to be implemented by future instructions.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestPlacedCellCopy {
    /// Absolute N15 destination memory cell.
    pub destination: u32,
    /// Absolute N15 source memory cell.
    pub source: u32,
}

/// Physically addressed two-phase phi copies for one symbolic CFG edge.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestPlacedPhiEdge {
    /// Commit scratch copies only after every snapshot has completed.
    pub commits: Vec<GuestPlacedCellCopy>,
    /// Canonical source function identity.
    pub function: u32,
    /// Original predecessor; no host edge selection occurs.
    pub predecessor: u32,
    /// Copy sources to scratch before any phi destination changes.
    pub snapshots: Vec<GuestPlacedCellCopy>,
    /// Original successor receiving phi values.
    pub successor: u32,
}

/// Authenticated prelink CFG plus physically located *data* obligations.
///
/// No physical instruction addresses, guest writes, arithmetic or control
/// jumps have been linked; this is not a target program or a VM state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestRelocatedCfgPlan {
    /// Data operand and control-cell addresses in original block order.
    pub operation_blocks: Vec<GuestPlacedBlock>,
    /// Addressed two-phase copies for each source CFG phi edge.
    pub phi_edges: Vec<GuestPlacedPhiEdge>,
    /// Canonical typed/ternary CFG from the exact supplied source bytes.
    pub prelink: PrelinkCfgPlan,
    /// Disjoint source-length-checked N15 data reservations.
    pub state_placements: Vec<GuestFramePlacement>,
}

type FramePlacements<'frame> =
    BTreeMap<u32, (&'frame GuestStateFrame, GuestFramePlacement)>;
type PlacedFrames<'frame> = (Vec<GuestFramePlacement>, FramePlacements<'frame>);

fn locate_slot(
    frame: &GuestStateFrame,
    placement: GuestFramePlacement,
    slot: GuestStorageValue,
) -> Result<GuestPlacedOperand, TypedCfgAdapterError> {
    // A width-carrying operand must be identical to its canonical SSA slot.
    if !frame.values.contains(&slot) || slot.words == 0 {
        return Err(TypedCfgAdapterError::GuestStateAllocation);
    }
    let last_offset = slot
        .words
        .checked_sub(1)
        .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
    let last = slot
        .offset
        .checked_add(last_offset)
        .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
    let _end = placed_cell(placement, frame, last)?;
    Ok(GuestPlacedOperand {
        address: placed_cell(placement, frame, slot.offset)?,
        type_kind: slot.type_kind,
        value: slot.value,
        words: slot.words,
    })
}

fn locate_copy(
    frame: &GuestStateFrame,
    placement: GuestFramePlacement,
    copy: GuestCellCopy,
) -> Result<GuestPlacedCellCopy, TypedCfgAdapterError> {
    Ok(GuestPlacedCellCopy {
        destination: placed_cell(placement, frame, copy.destination)?,
        source: placed_cell(placement, frame, copy.source)?,
    })
}

fn place_frames(
    frames: &[GuestStateFrame],
    source_cells: u32,
    frame_base: u32,
) -> Result<PlacedFrames<'_>, TypedCfgAdapterError> {
    let mut state_placements = Vec::with_capacity(frames.len());
    let mut by_function = FramePlacements::new();
    let mut next = frame_base;
    for frame in frames {
        let placed = validate_frame_placement(frame, source_cells, next)?;
        if by_function
            .insert(frame.function, (frame, placed))
            .is_some()
        {
            return Err(TypedCfgAdapterError::GuestStateAllocation);
        }
        next = placed.end_exclusive;
        state_placements.push(placed);
    }
    Ok((state_placements, by_function))
}

fn placed_control_edge(
    function: u32,
    predecessor: u32,
    successor: u32,
    by_edge: &BTreeMap<(u32, u32, u32), &GuestPlacedPhiEdge>,
    phi_targets: &BTreeSet<(u32, u32)>,
    consumed: &mut BTreeSet<(u32, u32, u32)>,
) -> Result<GuestPlacedControlEdge, TypedCfgAdapterError> {
    let key = (function, predecessor, successor);
    let phi = by_edge.get(&key).copied();
    if phi.is_none() && phi_targets.contains(&(function, successor)) {
        return Err(TypedCfgAdapterError::GuestStateAllocation);
    }
    if phi.is_some() {
        _ = consumed.insert(key);
    }
    Ok(GuestPlacedControlEdge {
        commits: phi.map_or_else(Vec::new, |edge| edge.commits.clone()),
        snapshots: phi.map_or_else(Vec::new, |edge| edge.snapshots.clone()),
        successor,
    })
}

fn place_operations(
    blocks: &[super::state_operations::GuestOperationBlock],
    by_function: &FramePlacements<'_>,
    phi_edges: &[GuestPlacedPhiEdge],
    phi_targets: &BTreeSet<(u32, u32)>,
) -> Result<Vec<GuestPlacedBlock>, TypedCfgAdapterError> {
    let mut by_edge = BTreeMap::new();
    for edge in phi_edges {
        if by_edge
            .insert((edge.function, edge.predecessor, edge.successor), edge)
            .is_some()
        {
            return Err(TypedCfgAdapterError::GuestStateAllocation);
        }
    }
    let mut consumed = BTreeSet::new();
    let mut operation_blocks = Vec::with_capacity(blocks.len());
    for block in blocks {
        let &(frame, placement) = by_function
            .get(&block.function)
            .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
        let instructions = block
            .instructions
            .iter()
            .map(|binding| {
                Ok(GuestPlacedInstruction {
                    instruction: binding.instruction.clone(),
                    span: binding.span,
                    constant_cells: binding
                        .constant_cells
                        .iter()
                        .map(|cell| {
                            Ok(GuestPlacedLiteralCell {
                                address: placed_cell(
                                    placement,
                                    frame,
                                    cell.destination,
                                )?,
                                word: cell.word,
                            })
                        })
                        .collect::<Result<Vec<_>, TypedCfgAdapterError>>()?,
                    reads: binding
                        .reads
                        .iter()
                        .map(|slot| locate_slot(frame, placement, *slot))
                        .collect::<Result<Vec<_>, _>>()?,
                    write: binding
                        .write
                        .map(|slot| locate_slot(frame, placement, slot))
                        .transpose()?,
                })
            })
            .collect::<Result<Vec<_>, TypedCfgAdapterError>>()?;
        let mut edge = |target| {
            placed_control_edge(
                block.function,
                block.block,
                target,
                &by_edge,
                &phi_targets,
                &mut consumed,
            )
        };
        let control = match &block.control.terminator {
            Terminator::Jump { target } => GuestPlacedControl::Jump {
                edge: edge(target.value())?,
            },
            Terminator::Branch {
                false_target,
                true_target,
                ..
            } => GuestPlacedControl::Branch {
                when_false: edge(false_target.value())?,
                when_true: edge(true_target.value())?,
            },
            Terminator::Return { .. } => GuestPlacedControl::Return,
            Terminator::Switch { .. } => {
                return Err(TypedCfgAdapterError::UnsupportedTypedIr);
            },
        };
        operation_blocks.push(GuestPlacedBlock {
            block: block.block,
            control,
            condition: block
                .control
                .condition
                .map(|slot| locate_slot(frame, placement, slot))
                .transpose()?,
            function: block.function,
            instructions,
            return_value: block
                .control
                .return_value
                .map(|slot| locate_slot(frame, placement, slot))
                .transpose()?,
        });
    }
    if consumed.len() != by_edge.len() {
        return Err(TypedCfgAdapterError::GuestStateAllocation);
    }
    Ok(operation_blocks)
}

fn place_edges(
    edges: &[super::state_storage::GuestCellEdge],
    by_function: &FramePlacements<'_>,
) -> Result<Vec<GuestPlacedPhiEdge>, TypedCfgAdapterError> {
    let mut phi_edges = Vec::with_capacity(edges.len());
    for edge in edges {
        let &(frame, placement) = by_function
            .get(&edge.function)
            .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
        phi_edges.push(GuestPlacedPhiEdge {
            commits: edge
                .commits
                .iter()
                .map(|copy| locate_copy(frame, placement, *copy))
                .collect::<Result<Vec<_>, _>>()?,
            function: edge.function,
            predecessor: edge.predecessor,
            snapshots: edge
                .snapshots
                .iter()
                .map(|copy| locate_copy(frame, placement, *copy))
                .collect::<Result<Vec<_>, _>>()?,
            successor: edge.successor,
        });
    }
    Ok(phi_edges)
}

/// Re-derive the original typed CFG before assigning disjoint absolute
/// operand, Boolean control, literal write and parallel phi-copy addresses.
///
/// # Errors
///
/// Refuses invalid source-authenticated typed IR, any code/data collision,
/// exhausted target memory or a malformed cell-range computation. The caller
/// must later prove that `source_cells` equals its *final* physical code size;
/// no target bytes are produced or validated here.
pub fn relocate_source_locked_cfg(
    canonical: &[u8],
    source_cells: u32,
    frame_base: u32,
) -> Result<GuestRelocatedCfgPlan, TypedCfgAdapterError> {
    let prelink = prepare_canonical_dynamic_cfg(canonical)?;
    if prelink.state_frames.is_empty() {
        return Err(TypedCfgAdapterError::GuestStateAllocation);
    }
    let (state_placements, by_function) =
        place_frames(&prelink.state_frames, source_cells, frame_base)?;
    let phi_edges = place_edges(&prelink.cell_edges, &by_function)?;
    // Derive the required phi-bearing successors independently of the
    // relocated copies. Losing a transfer must not silently turn a phi edge
    // into an ordinary empty-copy jump.
    let phi_targets = prelink
        .cfg
        .functions
        .iter()
        .flat_map(|function| {
            function
                .blocks
                .iter()
                .filter(|block| !block.phis.is_empty())
                .map(|block| (function.id, block.id))
        })
        .collect::<BTreeSet<_>>();
    let operation_blocks = place_operations(
        &prelink.operation_blocks,
        &by_function,
        &phi_edges,
        &phi_targets,
    )?;
    Ok(GuestRelocatedCfgPlan {
        operation_blocks,
        phi_edges,
        prelink,
        state_placements,
    })
}

#[cfg(test)]
mod tests {
    use std::collections::{BTreeMap, BTreeSet};

    use super::super::state_operations::{
        GuestControlBinding, GuestOperationBlock,
    };
    use super::super::typed::{BlockId, Terminator};
    use super::{
        FramePlacements, GuestFramePlacement, GuestPlacedPhiEdge,
        GuestStateFrame, TypedCfgAdapterError, place_operations,
    };

    #[test]
    fn rejects_orphan_duplicate_and_missing_control_phi_bindings() {
        let frame = GuestStateFrame {
            function: 0,
            scratch_offset: 0,
            scratch_words: 0,
            total_words: 0,
            values: Vec::new(),
        };
        let placement = GuestFramePlacement {
            base: 91,
            end_exclusive: 91,
            source_cells: 91,
        };
        let by_function: FramePlacements<'_> =
            BTreeMap::from([(0, (&frame, placement))]);
        let blocks = vec![GuestOperationBlock {
            block: 0,
            control: GuestControlBinding {
                condition: None,
                return_value: None,
                terminator: Terminator::Jump { target: BlockId::new(1) },
            },
            function: 0,
            instructions: Vec::new(),
        }];
        let edge = GuestPlacedPhiEdge {
            commits: Vec::new(),
            function: 0,
            predecessor: 0,
            snapshots: Vec::new(),
            successor: 1,
        };
        let phi_targets = BTreeSet::from([(0, 1)]);
        assert!(
            place_operations(
                &blocks,
                &by_function,
                &[edge.clone()],
                &phi_targets,
            )
            .is_ok()
        );
        let refusal = Err(TypedCfgAdapterError::GuestStateAllocation);
        assert_eq!(
            place_operations(&blocks, &by_function, &[], &phi_targets),
            refusal,
        );
        assert_eq!(
            place_operations(
                &blocks,
                &by_function,
                &[edge.clone(), edge.clone()],
                &phi_targets,
            ),
            refusal,
        );
        let orphan = GuestPlacedPhiEdge { predecessor: 2, ..edge };
        assert_eq!(
            place_operations(
                &blocks,
                &by_function,
                &[orphan].as_slice(),
                &phi_targets
            ),
            refusal,
        );
    }
}
