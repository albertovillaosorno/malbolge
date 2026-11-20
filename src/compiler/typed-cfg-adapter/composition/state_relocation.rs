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
    CURRENT_WORD_COUNT, GuestCellCopy, GuestFramePlacement, GuestStateFrame,
    GuestStorageValue, encode_i32_cells, placed_cell, validate_frame_placement,
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

/// One proposed contiguous instruction interval for a source CFG block.
///
/// The interval is code *space*, not verified instruction bytes. A backend
/// must independently prove its source, decode and mutation footprint.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCodeBlockPlacement {
    /// Canonical function identity.
    pub function: u32,
    /// Canonical block identity.
    pub block: u32,
    /// First proposed physical instruction address (inclusive).
    pub start: u32,
    /// First guest source address following this block (exclusive).
    pub end_exclusive: u32,
    /// Proposed first instruction of the terminating control sequence.
    /// The interval must contain it, but no actual opcode is verified.
    pub control_start: u32,
}

/// Which source control outcome must execute one physical edge.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub enum GuestCodeEdgeKind {
    /// Unconditional source jump.
    Jump,
    /// Branch outcome when its checked Boolean is false.
    WhenFalse,
    /// Branch outcome when its checked Boolean is true.
    WhenTrue,
}

/// One proposed predecessor-specific code landing pad with phi writes.
///
/// The future linker must implement both copy phases in this pad, then
/// transfer control to the shared successor block. This reservation does not
/// contain executable bytes or a physical proof.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCodeEdgePadPlacement {
    /// First source address after this reserved landing pad (exclusive).
    pub end_exclusive: u32,
    /// Canonical source function identity.
    pub function: u32,
    /// Exact source branch arm or unconditional jump identity.
    pub kind: GuestCodeEdgeKind,
    /// Canonical predecessor whose live values are to be copied.
    pub predecessor: u32,
    /// First proposed source address of this edge-specific landing pad.
    pub start: u32,
    /// Canonical successor reached only after completing the phi copies.
    pub successor: u32,
}

/// Caller-proposed code blocks and predecessor-specific phi landing pads.
///
/// Neither set contains verified guest instructions or executable transfers.
#[derive(Clone, Copy, Debug)]
pub struct GuestCodeProposals<'source> {
    /// Proposed CFG block intervals in the physical source image.
    pub code_blocks: &'source [GuestCodeBlockPlacement],
    /// Proposed edge-specific phi-write intervals in the same image.
    pub edge_pads: &'source [GuestCodeEdgePadPlacement],
}

/// A specific code cell obligated to perform one source-locked phi copy.
///
/// This is not an encoded Malbolge instruction: actual byte mutation and
/// read/write semantics must still be proved by the physical linker.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCodeCellCopySite {
    /// One distinct proposed code cell inside the owning edge pad.
    pub code_address: u32,
    /// Original relocated source and destination cells for this write.
    pub copy: GuestPlacedCellCopy,
}

/// One proposed physical target with its *edge-local* parallel copies.
///
/// Neither the target address nor the copies are guest instructions yet.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestCodeControlEdge {
    /// Code-cell obligations for commits, strictly after all snapshots.
    pub commit_sites: Vec<GuestCodeCellCopySite>,
    /// Physical scratch-to-phi assignments, after all snapshots.
    pub commits: Vec<GuestPlacedCellCopy>,
    /// Original typed branch Boolean, absent on unconditional jumps.
    pub condition: Option<GuestPlacedOperand>,
    /// Proposed first code position implementing this predecessor's control.
    pub control_address: u32,
    /// Physical entry to the phi pad, or directly to the successor if none.
    /// This is the proposed address the predecessor must branch to.
    pub entry_address: u32,
    /// Canonical function containing the predecessor and successor.
    pub function: u32,
    /// Exact source control arm, not host-selected.
    pub kind: GuestCodeEdgeKind,
    /// Last cell of this edge's phi pad, reserved for the successor jump.
    /// None for phi-free edges that enter their successor directly.
    /// This is a proposed location, not an executed or encoded jump.
    pub pad_exit_address: Option<u32>,
    /// Canonical predecessor block identity.
    pub predecessor: u32,
    /// Ordered code-cell obligations for snapshots before any commits.
    pub snapshot_sites: Vec<GuestCodeCellCopySite>,
    /// Copies of all original phi sources into scratch first.
    pub snapshots: Vec<GuestPlacedCellCopy>,
    /// Canonical successor block identity.
    pub successor: u32,
    /// Physical source-cell entry of the successor block.
    pub target_address: u32,
}

/// One source-ordered typed operation's minimum physical code reservation.
///
/// These cells are only a lower-bound placement. They contain no verified
/// opcode, so arithmetic, operand loading, pointer motion and encryption may
/// require additional code that is not represented by this reservation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCodeOperationSite {
    /// Canonical typed block identity.
    pub block: u32,
    /// First reserved code cell (inclusive).
    pub start: u32,
    /// First code cell following this operation's minimum reservation.
    pub end_exclusive: u32,
    /// Canonical source function identity.
    pub function: u32,
    /// Source-order index into the relocated block's instructions.
    pub ordinal: u32,
}

/// Exact interpretation owed by one physically executed guest input.
///
/// A signed C23 `getchar` has two *different* EOF representations: the raw
/// current-profile VM sentinel and the source C `int` value (-1). The target
/// linker must realize that conversion in guest instructions before both
/// destination cells are written. No host-side input substitution is allowed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GuestCodeInputSemantics {
    /// One unsigned byte input; no C23 signed EOF conversion is implied.
    ByteU8,
    /// Convert all 256 successful bytes and raw VM EOF to C23 `int` words.
    SignedC23 {
        /// The target-profile's physical input accumulator on true EOF.
        raw_eof_word: u32,
        /// Canonical full-width two-word representation of C23 EOF (-1).
        c23_eof_cells: [u32; 2],
    },
}

/// A required physical effect of one typed operation, not an opcode.
///
/// Actual address-sensitive code may need more instructions for pointer
/// setup, signed EOF conversion, arithmetic or self-modification. An effect
/// site must never be treated as proof that an opcode performs its effect.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GuestCodeOperationEffect {
    /// Real input, with its source-bound destination and conversion contract.
    Input {
        /// Full-width typed result; physical input alone does not write it.
        destination: GuestPlacedOperand,
        /// Required raw byte or signed C23 interpretation after the read.
        semantics: GuestCodeInputSemantics,
    },
    /// One output of the addressed byte operand.
    Output {
        /// Source SSA byte cell for the required output effect.
        source: GuestPlacedOperand,
    },
    /// One addressed guest data word that must be written.
    Store {
        /// Exact destination cell of the write.
        destination: u32,
        /// Exact literal word for constants, or runtime-computed otherwise.
        literal: Option<u32>,
    },
    /// One otherwise effect-free computation's minimum instruction cell.
    Compute,
}

/// An exact source operation's typed effect bound to reserved code space.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCodeOperationEffectSite {
    /// Canonical block identity.
    pub block: u32,
    /// First proposed code cell for this one required effect.
    pub code_address: u32,
    /// The semantic obligation at this site, not a proven instruction.
    pub effect: GuestCodeOperationEffect,
    /// Canonical source function identity.
    pub function: u32,
    /// Instruction ordinal within its source block.
    pub ordinal: u32,
}

/// A source-authenticated function's proposed physical code entry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCodeFunctionEntry {
    /// Canonical entry block identity, not inferred from code order.
    pub block: u32,
    /// Proposed start of this function's entry block.
    pub address: u32,
    /// Canonical function identity.
    pub function: u32,
}

/// One source return's proposed physical control entry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCodeReturnSite {
    /// Canonical block ending in Return.
    pub block: u32,
    /// First proposed code cell of this block's return sequence.
    pub address: u32,
    /// Canonical function identity.
    pub function: u32,
    /// Optional addressed scalar returned by the function.
    pub value: Option<GuestPlacedOperand>,
}

/// Addressed code-edge obligations attached to an authenticated data plan.
///
/// The code intervals are supplied *proposals*. No opcode, physical jump,
/// branch, phi copy or termination has been emitted or accepted by the VM.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestAddressedCfgPlan {
    /// Nonoverlapping proposed block code intervals in canonical block order.
    pub code_blocks: Vec<GuestCodeBlockPlacement>,
    /// Each source branch arm or jump gets an unselected entry and copies.
    pub control_edges: Vec<GuestCodeControlEdge>,
    /// Phi pads, each reserving its exit jump, disjoint from all blocks.
    pub edge_pads: Vec<GuestCodeEdgePadPlacement>,
    /// Entry address for each canonical source function, never first by guess.
    pub function_entries: Vec<GuestCodeFunctionEntry>,
    /// Addressed input, output and per-word store obligations, not opcodes.
    pub operation_effect_sites: Vec<GuestCodeOperationEffectSite>,
    /// Source-ordered minimum physical instruction reservations, not opcodes.
    pub operation_sites: Vec<GuestCodeOperationSite>,
    /// Every return's separate physical control site and optional scalar.
    pub return_sites: Vec<GuestCodeReturnSite>,
    /// The unchanged authenticated operation and data relocation obligations.
    pub relocated: GuestRelocatedCfgPlan,
}

/// Exact refusal boundary for a proposed physical CFG code placement.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GuestCodePlacementError {
    /// A proposed code interval or source block identity is invalid.
    InvalidCodePlacement,
    /// Original canonical typed CFG or data relocation refused.
    TypedCfg(TypedCfgAdapterError),
}

type FramePlacements<'frame> =
    BTreeMap<u32, (&'frame GuestStateFrame, GuestFramePlacement)>;
type PlacedFrames<'frame> = (Vec<GuestFramePlacement>, FramePlacements<'frame>);
type BlockPlacements = BTreeMap<(u32, u32), GuestCodeBlockPlacement>;
type EdgeKey = (u32, u32, GuestCodeEdgeKind, u32);
type EdgePadPlacements = BTreeMap<EdgeKey, GuestCodeEdgePadPlacement>;
type ValidatedCodeProposals = (BlockPlacements, EdgePadPlacements);

struct CodeEdgeIndex<'index> {
    pads: &'index EdgePadPlacements,
    starts: &'index BlockPlacements,
    used_pads: &'index mut Vec<GuestCodeEdgePadPlacement>,
}

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

fn minimum_operation_cells(
    instruction: &GuestPlacedInstruction,
) -> Option<u32> {
    let literal_writes =
        u32::try_from(instruction.constant_cells.len()).ok()?;
    let destination_writes =
        instruction.write.map_or(0, |destination| destination.words);
    let input_steps = u32::from(matches!(
        instruction.instruction,
        Instruction::Getchar { .. } | Instruction::ByteInput { .. }
    ));
    Some(
        destination_writes
            .checked_add(input_steps)?
            .max(literal_writes)
            .max(1),
    )
}

fn required_operation_effects(
    instruction: &GuestPlacedInstruction,
) -> Result<Vec<GuestCodeOperationEffect>, GuestCodePlacementError> {
    let mut effects = Vec::new();
    let input_semantics = match &instruction.instruction {
        Instruction::Getchar { result, .. } => Some((
            GuestCodeInputSemantics::SignedC23 {
                raw_eof_word: CURRENT_WORD_COUNT.saturating_sub(1),
                c23_eof_cells: encode_i32_cells(u32::MAX),
            },
            result.value(),
        )),
        Instruction::ByteInput { result, .. } => {
            Some((GuestCodeInputSemantics::ByteU8, result.value()))
        },
        _ => None,
    };
    if let Some((semantics, result)) = input_semantics {
        let destination = instruction
            .write
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        let correctly_typed = match semantics {
            GuestCodeInputSemantics::SignedC23 { .. } => {
                destination.type_kind == TernaryCfgScalarKind::I32
                    && destination.words == 2
            },
            GuestCodeInputSemantics::ByteU8 => {
                destination.type_kind == TernaryCfgScalarKind::U8
                    && destination.words == 1
            },
        };
        if !correctly_typed
            || destination.value != result
            || !instruction.reads.is_empty()
            || !instruction.constant_cells.is_empty()
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
        effects
            .push(GuestCodeOperationEffect::Input { destination, semantics });
    }
    if let Instruction::ByteOutput { value } = &instruction.instruction {
        let [source] = instruction.reads.as_slice() else {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        };
        if source.value != value.value()
            || source.type_kind != TernaryCfgScalarKind::U8
            || source.words != 1
            || instruction.write.is_some()
            || !instruction.constant_cells.is_empty()
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
        effects.push(GuestCodeOperationEffect::Output { source: *source });
    }
    if let Some(destination) = instruction.write {
        let literal_by_address = instruction
            .constant_cells
            .iter()
            .map(|cell| (cell.address, cell.word))
            .collect::<BTreeMap<_, _>>();
        if literal_by_address.len() != instruction.constant_cells.len() {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
        for offset in 0..destination.words {
            let address = destination
                .cell_address(offset)
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            effects.push(GuestCodeOperationEffect::Store {
                destination: address,
                literal: literal_by_address.get(&address).copied(),
            });
        }
        if !literal_by_address.is_empty()
            && (literal_by_address.len()
                != usize::try_from(destination.words).map_err(|_| {
                    GuestCodePlacementError::InvalidCodePlacement
                })?
                || (0..destination.words).any(|offset| {
                    destination.cell_address(offset).is_none_or(|cell| {
                        !literal_by_address.contains_key(&cell)
                    })
                }))
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
    } else if !instruction.constant_cells.is_empty() {
        return Err(GuestCodePlacementError::InvalidCodePlacement);
    }
    if effects.is_empty() {
        effects.push(GuestCodeOperationEffect::Compute);
    }
    if u32::try_from(effects.len()).ok() != minimum_operation_cells(instruction)
    {
        return Err(GuestCodePlacementError::InvalidCodePlacement);
    }
    Ok(effects)
}

fn bind_operation_sites(
    block: &GuestPlacedBlock,
    placement: GuestCodeBlockPlacement,
) -> Result<
    (
        Vec<GuestCodeOperationSite>,
        Vec<GuestCodeOperationEffectSite>,
    ),
    GuestCodePlacementError,
> {
    let mut next_address = placement.start;
    let mut sites = Vec::with_capacity(block.instructions.len());
    let mut effect_sites = Vec::new();
    for (index, instruction) in block.instructions.iter().enumerate() {
        let effects = required_operation_effects(instruction)?;
        let length = u32::try_from(effects.len())
            .map_err(|_| GuestCodePlacementError::InvalidCodePlacement)?;
        let end_exclusive = next_address
            .checked_add(length)
            .filter(|end| *end <= placement.control_start)
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        let ordinal = u32::try_from(index)
            .map_err(|_| GuestCodePlacementError::InvalidCodePlacement)?;
        for (effect_index, effect) in effects.into_iter().enumerate() {
            let code_address = next_address
                .checked_add(u32::try_from(effect_index).map_err(|_| {
                    GuestCodePlacementError::InvalidCodePlacement
                })?)
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            effect_sites.push(GuestCodeOperationEffectSite {
                block: block.block,
                code_address,
                effect,
                function: block.function,
                ordinal,
            });
        }
        sites.push(GuestCodeOperationSite {
            block: block.block,
            end_exclusive,
            function: block.function,
            ordinal,
            start: next_address,
        });
        next_address = end_exclusive;
    }
    Ok((sites, effect_sites))
}

fn validate_code_proposals(
    proposals: GuestCodeProposals<'_>,
    source_cells: u32,
    blocks: &[GuestPlacedBlock],
) -> Result<ValidatedCodeProposals, GuestCodePlacementError> {
    let GuestCodeProposals {
        code_blocks: proposed,
        edge_pads: proposed_pads,
    } = proposals;
    let mut starts = BTreeMap::new();
    for block in proposed {
        if block.start >= block.end_exclusive
            || block.control_start < block.start
            || block.control_start >= block.end_exclusive
            || block.end_exclusive > source_cells
            || starts
                .insert((block.function, block.block), *block)
                .is_some()
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
    }
    if starts.len() != blocks.len()
        || blocks
            .iter()
            .any(|block| !starts.contains_key(&(block.function, block.block)))
    {
        return Err(GuestCodePlacementError::InvalidCodePlacement);
    }
    // Every frame-backed result has a distinct physical word per slot; an
    // instruction writes at most one guest data cell. Getchar/byte input also
    // requires a separate real `/` instruction, which only changes A, not
    // those frame cells. Constants require every addressed literal write.
    // This is a necessary capacity bound, not a claim that C32 arithmetic
    // or control flow can actually fit in the proposed source interval.
    for source_block in blocks {
        let placement = starts
            .get(&(source_block.function, source_block.block))
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        let required = source_block
            .instructions
            .iter()
            .try_fold(0u32, |count, instruction| {
                count.checked_add(minimum_operation_cells(instruction)?)
            })
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        if placement.control_start - placement.start < required {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
    }
    let mut pads = BTreeMap::new();
    for pad in proposed_pads {
        if pad.start >= pad.end_exclusive
            || pad.end_exclusive > source_cells
            || pads
                .insert(
                    (pad.function, pad.predecessor, pad.kind, pad.successor),
                    *pad,
                )
                .is_some()
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
    }
    // Both source blocks and predecessor-owned phi pads occupy *physical*
    // source cells. They may not alias even if their CFG identities differ.
    let mut intervals = proposed
        .iter()
        .map(|block| (block.start, block.end_exclusive))
        .chain(
            proposed_pads
                .iter()
                .map(|pad| (pad.start, pad.end_exclusive)),
        )
        .collect::<Vec<_>>();
    intervals.sort_unstable();
    if intervals
        .windows(2)
        .any(|window| matches!(window, [left, right] if left.1 > right.0))
    {
        return Err(GuestCodePlacementError::InvalidCodePlacement);
    }
    Ok((starts, pads))
}

fn proposed_code_edge(
    key: (u32, u32, GuestCodeEdgeKind),
    edge: &GuestPlacedControlEdge,
    control_address: u32,
    condition: Option<GuestPlacedOperand>,
    index: &mut CodeEdgeIndex<'_>,
) -> Result<GuestCodeControlEdge, GuestCodePlacementError> {
    let (function, predecessor, kind) = key;
    let target_address = index
        .starts
        .get(&(function, edge.successor))
        .map(|block| block.start)
        .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
    let pad = index
        .pads
        .get(&(function, predecessor, kind, edge.successor))
        .copied();
    let copies_needed = !edge.snapshots.is_empty() || !edge.commits.is_empty();
    // A branch may not enter a shared successor before the edge-local phi
    // snapshots and commits; a pad without phi writes is also unexplained.
    if copies_needed != pad.is_some() {
        return Err(GuestCodePlacementError::InvalidCodePlacement);
    }
    if let Some(placement) = pad {
        // The pad reserves a separate physical operation for each memory
        // copy and one final code-pointer transfer to the successor.
        // A p/* write only advances C; it cannot also perform an i jump.
        // This is a necessary reservation, not an opcode or mutation proof.
        let required_cells = edge
            .snapshots
            .len()
            .checked_add(edge.commits.len())
            .and_then(|writes| writes.checked_add(1))
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        let reserved_cells =
            usize::try_from(placement.end_exclusive - placement.start)
                .map_err(|_| GuestCodePlacementError::InvalidCodePlacement)?;
        if reserved_cells < required_cells {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
        index.used_pads.push(placement);
    }
    // Right-align the ordered copy suffix immediately before the reserved
    // successor transfer. Earlier pad cells are only unverified setup space,
    // not proved instructions or safe no-ops; no gaps may interrupt the
    // snapshot-before-commit sequence or delay its final jump.
    let (snapshot_sites, commit_sites) = if let Some(placement) = pad {
        let copy_count = edge
            .snapshots
            .len()
            .checked_add(edge.commits.len())
            .and_then(|count| u32::try_from(count).ok())
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        let pad_exit = placement
            .end_exclusive
            .checked_sub(1)
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        let mut next_address = pad_exit
            .checked_sub(copy_count)
            .filter(|start| *start >= placement.start)
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        let mut assign_site = |copy: &GuestPlacedCellCopy| {
            let code_address = next_address;
            next_address = next_address
                .checked_add(1)
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            Ok(GuestCodeCellCopySite {
                code_address,
                copy: *copy,
            })
        };
        let snapshots = edge
            .snapshots
            .iter()
            .map(&mut assign_site)
            .collect::<Result<Vec<_>, _>>()?;
        let commits = edge
            .commits
            .iter()
            .map(&mut assign_site)
            .collect::<Result<Vec<_>, _>>()?;
        if next_address != pad_exit {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
        (snapshots, commits)
    } else {
        (Vec::new(), Vec::new())
    };
    Ok(GuestCodeControlEdge {
        commit_sites,
        commits: edge.commits.clone(),
        condition,
        control_address,
        entry_address: pad.map_or(target_address, |placement| placement.start),
        function,
        kind,
        pad_exit_address: pad.map(|placement| placement.end_exclusive - 1),
        predecessor,
        snapshot_sites,
        snapshots: edge.snapshots.clone(),
        successor: edge.successor,
        target_address,
    })
}

/// Attach proposed physical code entries to source control edges.
///
/// An edge carrying phi writes first enters its predecessor-specific pad;
/// other edges enter the successor directly. The pad must snapshot every
/// source, commit the writes, then jump to its successor. These are not
/// verified target bytes or executable guest copies.
///
/// Both sets of supplied intervals are untrusted. This verifies that every
/// source block and required phi pad has exactly one disjoint, nonempty,
/// source-contained reservation, without host selection of any branch arm.
/// The physical linker must later prove opcode decode, execution order,
/// state updates, jumps and self-modification independently.
///
/// # Errors
///
/// Refuses invalid typed source/data placement, missing or extra intervals,
/// inconsistent edge identity, duplicates, overlap or source exhaustion.
pub fn bind_source_locked_cfg_code_targets(
    canonical: &[u8],
    source_cells: u32,
    frame_base: u32,
    proposals: GuestCodeProposals<'_>,
) -> Result<GuestAddressedCfgPlan, GuestCodePlacementError> {
    let GuestCodeProposals {
        code_blocks: proposed,
        edge_pads: proposed_pads,
    } = proposals;
    let relocated =
        relocate_source_locked_cfg(canonical, source_cells, frame_base)
            .map_err(GuestCodePlacementError::TypedCfg)?;
    let (starts, pads) = validate_code_proposals(
        proposals,
        source_cells,
        &relocated.operation_blocks,
    )?;
    let function_entries = relocated
        .prelink
        .cfg
        .functions
        .iter()
        .map(|function| {
            starts
                .get(&(function.id, function.entry))
                .map(|entry| GuestCodeFunctionEntry {
                    block: function.entry,
                    address: entry.start,
                    function: function.id,
                })
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)
        })
        .collect::<Result<Vec<_>, _>>()?;
    let mut code_blocks = Vec::with_capacity(proposed.len());
    let mut control_edges = Vec::new();
    let mut edge_pads = Vec::with_capacity(proposed_pads.len());
    let mut operation_sites = Vec::new();
    let mut operation_effect_sites = Vec::new();
    let mut return_sites = Vec::new();
    for block in &relocated.operation_blocks {
        let placement = starts
            .get(&(block.function, block.block))
            .copied()
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        code_blocks.push(placement);
        let (sites, effects) = bind_operation_sites(block, placement)?;
        operation_sites.extend(sites);
        operation_effect_sites.extend(effects);
        let mut bind = |kind, edge: &GuestPlacedControlEdge| {
            let mut index = CodeEdgeIndex {
                pads: &pads,
                starts: &starts,
                used_pads: &mut edge_pads,
            };
            control_edges.push(proposed_code_edge(
                (block.function, block.block, kind),
                edge,
                placement.control_start,
                (kind != GuestCodeEdgeKind::Jump)
                    .then_some(block.condition)
                    .flatten(),
                &mut index,
            )?);
            Ok::<(), GuestCodePlacementError>(())
        };
        match &block.control {
            GuestPlacedControl::Branch { when_false, when_true } => {
                bind(GuestCodeEdgeKind::WhenFalse, when_false)?;
                bind(GuestCodeEdgeKind::WhenTrue, when_true)?;
            },
            GuestPlacedControl::Jump { edge } => {
                bind(GuestCodeEdgeKind::Jump, edge)?;
            },
            GuestPlacedControl::Return => {
                return_sites.push(GuestCodeReturnSite {
                    block: block.block,
                    address: placement.control_start,
                    function: block.function,
                    value: block.return_value,
                });
            },
        }
    }
    if edge_pads.len() != pads.len() {
        return Err(GuestCodePlacementError::InvalidCodePlacement);
    }
    Ok(GuestAddressedCfgPlan {
        code_blocks,
        control_edges,
        edge_pads,
        function_entries,
        operation_effect_sites,
        operation_sites,
        return_sites,
        relocated,
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
    fn physical_io_effects_refuse_forged_width_kind_and_result_identity() {
        use super::super::ternary::TernaryCfgScalarKind;
        use super::super::typed::{
            Instruction, SourcePosition, SourceSpan, TypeId, ValueId,
        };
        use super::{
            GuestCodeInputSemantics, GuestCodeOperationEffect,
            GuestCodePlacementError, GuestPlacedInstruction,
            GuestPlacedOperand, required_operation_effects,
        };

        let destination = GuestPlacedOperand {
            address: 4096,
            type_kind: TernaryCfgScalarKind::I32,
            value: 7,
            words: 2,
        };
        let source = SourcePosition::new(0, 1, 1);
        let mut instruction = GuestPlacedInstruction {
            constant_cells: Vec::new(),
            instruction: Instruction::Getchar {
                result: ValueId::new(7),
                type_id: TypeId::new(0),
            },
            reads: Vec::new(),
            span: SourceSpan::new(source, source),
            write: Some(destination),
        };
        assert_eq!(
            required_operation_effects(&instruction),
            Ok(vec![
                GuestCodeOperationEffect::Input {
                    destination,
                    semantics: GuestCodeInputSemantics::SignedC23 {
                        raw_eof_word: 14_348_906,
                        c23_eof_cells: [4_644_102, 299],
                    },
                },
                GuestCodeOperationEffect::Store {
                    destination: 4096,
                    literal: None,
                },
                GuestCodeOperationEffect::Store {
                    destination: 4097,
                    literal: None,
                },
            ])
        );
        let refusal = Err(GuestCodePlacementError::InvalidCodePlacement);
        instruction.write =
            Some(GuestPlacedOperand { value: 8, ..destination });
        assert_eq!(required_operation_effects(&instruction), refusal);
        instruction.write =
            Some(GuestPlacedOperand { words: 1, ..destination });
        assert_eq!(required_operation_effects(&instruction), refusal);
        instruction.write = Some(GuestPlacedOperand {
            type_kind: TernaryCfgScalarKind::U8,
            ..destination
        });
        assert_eq!(required_operation_effects(&instruction), refusal);
        instruction.write = None;
        assert_eq!(required_operation_effects(&instruction), refusal);

        let byte = GuestPlacedOperand {
            address: 4100,
            type_kind: TernaryCfgScalarKind::U8,
            value: 9,
            words: 1,
        };
        instruction.instruction = Instruction::ByteInput {
            result: ValueId::new(9),
            type_id: TypeId::new(1),
        };
        instruction.write = Some(byte);
        assert_eq!(
            required_operation_effects(&instruction),
            Ok(vec![
                GuestCodeOperationEffect::Input {
                    destination: byte,
                    semantics: GuestCodeInputSemantics::ByteU8,
                },
                GuestCodeOperationEffect::Store {
                    destination: 4100,
                    literal: None,
                },
            ])
        );
        instruction.write = Some(GuestPlacedOperand { value: 10, ..byte });
        assert_eq!(required_operation_effects(&instruction), refusal);
        instruction.write = Some(destination);
        assert_eq!(required_operation_effects(&instruction), refusal);
        instruction.write = Some(byte);
        instruction.reads.push(byte);
        assert_eq!(required_operation_effects(&instruction), refusal);

        // This is the checksum's final effect: output must read the exact
        // canonical U8 value, not a different SSA slot or truncated C32 word.
        instruction.instruction =
            Instruction::ByteOutput { value: ValueId::new(9) };
        instruction.write = None;
        assert_eq!(
            required_operation_effects(&instruction),
            Ok(vec![GuestCodeOperationEffect::Output { source: byte }])
        );
        instruction.reads = vec![GuestPlacedOperand { value: 10, ..byte }];
        assert_eq!(required_operation_effects(&instruction), refusal);
        instruction.reads = vec![GuestPlacedOperand { words: 2, ..byte }];
        assert_eq!(required_operation_effects(&instruction), refusal);
        instruction.reads = vec![GuestPlacedOperand {
            type_kind: TernaryCfgScalarKind::I32,
            ..byte
        }];
        assert_eq!(required_operation_effects(&instruction), refusal);
        instruction.reads = Vec::new();
        assert_eq!(required_operation_effects(&instruction), refusal);
        instruction.reads.push(byte);
        instruction.write = Some(byte);
        assert_eq!(required_operation_effects(&instruction), refusal);
    }

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
