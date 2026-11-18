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

use std::collections::BTreeMap;

use super::phi_edge_transfers::PrelinkCfgPlan;
use super::state_storage::{
    GuestCellCopy, GuestFramePlacement, GuestStateFrame, GuestStorageValue,
    placed_cell, validate_frame_placement,
};
use super::{TypedCfgAdapterError, prepare_canonical_dynamic_cfg};

/// One exact literal word requiring physical guest materialization.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestPlacedLiteralCell {
    /// Absolute N15 guest-memory address, not a code instruction.
    pub address: u32,
    /// Exact 15-trit value the future guest instruction must write.
    pub word: u32,
}

/// One instruction's absolute operand addresses (no instruction encoding).
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestPlacedInstruction {
    /// Exact literal write obligations, in canonical instruction order.
    pub constant_cells: Vec<GuestPlacedLiteralCell>,
    /// Absolute first addresses of typed input slots, in operand order.
    pub reads: Vec<u32>,
    /// Absolute first address of the result slot, when applicable.
    pub write: Option<u32>,
}

/// One original block's absolute operand and control-cell locations.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestPlacedBlock {
    /// Canonical source block identity.
    pub block: u32,
    /// Absolute address containing the branch Boolean, if any.
    pub condition: Option<u32>,
    /// Canonical source function identity.
    pub function: u32,
    /// Relocated operations in exact source-authenticated order.
    pub instructions: Vec<GuestPlacedInstruction>,
    /// Absolute address of the return value, if any.
    pub return_value: Option<u32>,
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
) -> Result<u32, TypedCfgAdapterError> {
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
    placed_cell(placement, frame, slot.offset)
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

fn place_operations(
    blocks: &[super::state_operations::GuestOperationBlock],
    by_function: &FramePlacements<'_>,
) -> Result<Vec<GuestPlacedBlock>, TypedCfgAdapterError> {
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
        operation_blocks.push(GuestPlacedBlock {
            block: block.block,
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
    let operation_blocks =
        place_operations(&prelink.operation_blocks, &by_function)?;
    let phi_edges = place_edges(&prelink.cell_edges, &by_function)?;
    Ok(GuestRelocatedCfgPlan {
        operation_blocks,
        phi_edges,
        prelink,
        state_placements,
    })
}
