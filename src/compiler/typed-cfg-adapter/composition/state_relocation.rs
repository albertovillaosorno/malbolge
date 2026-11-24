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
use super::typed::{
    BinaryOp, CastOp, CompareOp, Instruction, SourceSpan, Terminator,
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

/// One proposed physical phi-copy write within a source-specific edge pad.
///
/// `copy_index` numbers snapshots first, then commits. Copy operands and
/// widths are always rederived from canonical source, never caller-supplied.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCodePhiCopyAnchor {
    /// Absolute code address at which the required p/* must execute.
    pub code_address: u32,
    /// Zero-based source-derived snapshot/commit write ordinal.
    pub copy_index: u32,
    /// Canonical source-function identity.
    pub function: u32,
    /// Source control arm owning this private phi pad.
    pub kind: GuestCodeEdgeKind,
    /// Source CFG predecessor.
    pub predecessor: u32,
    /// Source CFG successor.
    pub successor: u32,
}

/// The first instruction of a source-owned phi pad, possibly before its first
/// snapshot, leaving space for actual guest operand and pointer setup.
/// This is an address reservation, not an opcode or transfer proof.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCodePhiEntryAnchor {
    /// Proposed entry of this predecessor-specific landing pad.
    pub code_address: u32,
    /// Canonical source function identity.
    pub function: u32,
    /// Canonical edge arm or unconditional jump.
    pub kind: GuestCodeEdgeKind,
    /// Canonical predecessor entering the pad.
    pub predecessor: u32,
    /// Canonical successor reached after all phi effects.
    pub successor: u32,
}

/// One proposed successor-transfer instruction at the end of a phi pad.
///
/// The last source-authenticated snapshot/commit may be followed by real
/// pointer setup before the guest `i` transfers to the shared successor.
/// This exact edge-specific cell is only a reservation, not an opcode proof.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCodePhiExitAnchor {
    /// Proposed final code cell executing the successor transfer.
    pub code_address: u32,
    /// Canonical source-function identity.
    pub function: u32,
    /// Branch-arm or unconditional edge identity.
    pub kind: GuestCodeEdgeKind,
    /// Source predecessor whose phi snapshots and commits must finish first.
    pub predecessor: u32,
    /// Canonical shared successor block reached by this transfer.
    pub successor: u32,
}

/// Complete source-checked sparse phi binding request.
///
/// The caller supplies only address proposals. Copy operands, two-phase
/// order and edge identities must still match the canonical source.
#[derive(Clone, Copy, Debug)]
pub struct GuestCodePhiCopyPlacement<'source> {
    /// Exact source-authenticated canonical typed wire.
    pub canonical: &'source [u8],
    /// Complete reserved physical code source length.
    pub source_cells: u32,
    /// First word of the source SSA frame reservations.
    pub frame_base: u32,
    /// Disjoint source block and edge-pad interval proposals.
    pub proposals: GuestCodeProposals<'source>,
    /// Source-identified operation first-effect proposals.
    pub operation_anchors: &'source [GuestCodeOperationAnchor],
    /// Source-identified individual operation effect proposals.
    pub effect_anchors: &'source [GuestCodeEffectAnchor],
    /// Source-identified individual snapshot and commit effect proposals.
    pub phi_anchors: &'source [GuestCodePhiCopyAnchor],
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

/// A nonconstant typed computation that still requires real guest execution.
///
/// These are exact source operations and placed words, not computed results
/// or accepted Malbolge opcodes. In particular, signedness, overflow and
/// truncation must be realized in the eventual guest instruction sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GuestCodeComputation {
    /// Two source operands of the same scalar kind, one result.
    Binary {
        /// Exact typed source operation, including arithmetic/bitwise kind.
        operation: BinaryOp,
        /// Original ordered left operand.
        left: GuestPlacedOperand,
        /// Original ordered right operand.
        right: GuestPlacedOperand,
        /// Full-width SSA result requiring target writes.
        result: GuestPlacedOperand,
    },
    /// One typed integer conversion (including truncation/extension).
    Cast {
        /// Exact typed source conversion operation.
        operation: CastOp,
        /// Full-width cast destination.
        result: GuestPlacedOperand,
        /// Original source value, not a host-evaluated constant.
        source: GuestPlacedOperand,
    },
    /// Typed equality/order semantics with a one-word Boolean result.
    Compare {
        /// Exact signed or unsigned comparison kind.
        operation: CompareOp,
        /// Original ordered left operand.
        left: GuestPlacedOperand,
        /// Original ordered right operand.
        right: GuestPlacedOperand,
        /// One-word Boolean SSA destination.
        result: GuestPlacedOperand,
    },
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
    /// Exact arithmetic/compare/cast obligation, absent for I/O or literals.
    pub computation: Option<GuestCodeComputation>,
    /// First reserved code cell (inclusive).
    pub start: u32,
    /// First code cell following this operation's minimum reservation.
    pub end_exclusive: u32,
    /// Canonical source function identity.
    pub function: u32,
    /// Source-order index into the relocated block's instructions.
    pub ordinal: u32,
}

/// A source-identified instruction whose first required physical effect has
/// a fixed proposed code position. The region before an anchor may contain
/// unverified operand setup; it is never treated as an encoded instruction.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCodeOperationAnchor {
    /// Canonical source block containing the operation.
    pub block: u32,
    /// Proposed location of the first required physical effect.
    pub code_address: u32,
    /// Canonical source function identity.
    pub function: u32,
    /// Source-ordered instruction index within the block.
    pub ordinal: u32,
}

/// One source-CFG block's proposed physical control-suffix address.
///
/// This is a reservation for an independently verified jump, branch or halt,
/// not evidence that any guest control opcode has been encoded or executed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCodeControlAnchor {
    /// Canonical source block identity.
    pub block: u32,
    /// Exact proposed control step, after every operation effect in the block.
    pub code_address: u32,
    /// Canonical source function identity.
    pub function: u32,
}

/// One individually located effect inside a source-authenticated operation.
///
/// Unlike an operation's first-effect anchor, this may leave setup cells
/// between the input and its frame writes, or between two C32 word writes.
/// The index selects an effect derived from the typed instruction, not a
/// caller-provided opcode or destination. The physical order may differ
/// only for two separately anchored constant-integer word stores: both
/// literal words must be explicitly proposed, and their writes have no
/// intervening source-visible operation. Input and computed-result effects
/// always preserve their canonical order.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCodeEffectAnchor {
    /// Canonical source block containing the instruction.
    pub block: u32,
    /// Proposed physical instruction address performing this effect.
    pub code_address: u32,
    /// Zero-based effect order within its canonical source instruction.
    pub effect_index: u32,
    /// Canonical source function containing the block.
    pub function: u32,
    /// Zero-based instruction index inside the source block.
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

/// An exact entry instruction for a canonical source function.
///
/// Unlike an operation anchor, this reserves the physical function entry
/// *before* any setup needed for its first typed operation. It does not
/// establish that an executable Malbolge instruction reaches that address.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCodeFunctionEntryAnchor {
    /// Canonical source entry block, not an arbitrary reachable block.
    pub block: u32,
    /// Proposed first guest code address of the function entry.
    pub code_address: u32,
    /// Canonical source function identity.
    pub function: u32,
}

/// Complete sparse code-placement request with optional function entries.
///
/// Every address is a proposal. Original typed source rederives all operation,
/// control, phi and entry identities before accepting the reservation.
#[derive(Clone, Copy, Debug)]
pub struct GuestCodeFunctionEntryPlacement<'source> {
    /// Exact canonical typed source wire.
    pub canonical: &'source [u8],
    /// Anchored locations of each source block's terminating control.
    pub control_anchors: &'source [GuestCodeControlAnchor],
    /// Source-identified per-operation physical write and I/O sites.
    pub effect_anchors: &'source [GuestCodeEffectAnchor],
    /// First word of the disjoint SSA data frame.
    pub frame_base: u32,
    /// Exact canonical function-entry positions, when known.
    pub function_entries: &'source [GuestCodeFunctionEntryAnchor],
    /// Physical operation first-effect sites.
    pub operation_anchors: &'source [GuestCodeOperationAnchor],
    /// Snapshot/commit site proposals for predecessor-specific phi edges.
    pub phi_anchors: &'source [GuestCodePhiCopyAnchor],
    /// Optional physical entry sites before the first phi snapshot.
    pub phi_entries: &'source [GuestCodePhiEntryAnchor],
    /// Optional physical transfer sites after the last phi commit.
    pub phi_exits: &'source [GuestCodePhiExitAnchor],
    /// Physical source-cell count (not a verified target byte image).
    pub source_cells: u32,
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
type PhiSiteAnchors = BTreeMap<EdgeKey, BTreeMap<u32, u32>>;
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

fn minimum_operation_cells_by_width(
    instruction: &Instruction,
    destination_words: u32,
    literal_writes: usize,
) -> Option<u32> {
    let literal_writes = u32::try_from(literal_writes).ok()?;
    let input_steps = u32::from(matches!(
        instruction,
        Instruction::Getchar { .. } | Instruction::ByteInput { .. }
    ));
    Some(
        destination_words
            .checked_add(input_steps)?
            .max(literal_writes)
            .max(1),
    )
}

fn minimum_operation_cells(
    instruction: &GuestPlacedInstruction,
) -> Option<u32> {
    minimum_operation_cells_by_width(
        &instruction.instruction,
        instruction.write.map_or(0, |destination| destination.words),
        instruction.constant_cells.len(),
    )
}

// Proposed instruction effects must preserve the original SSA read order and
// result, even for computed values whose word writes are not yet executable.
// Constants are the only operations allowed to supply literal word effects.
fn validate_code_operation_operands(
    instruction: &GuestPlacedInstruction,
) -> Result<(), GuestCodePlacementError> {
    let refusal = GuestCodePlacementError::InvalidCodePlacement;
    let (read_values, write_value) =
        super::state_operations::operand_values(&instruction.instruction)
            .map_err(|_| refusal)?;
    if read_values.len() != instruction.reads.len()
        || read_values
            .iter()
            .zip(&instruction.reads)
            .any(|(expected, actual)| expected.value() != actual.value)
        || write_value.map(super::typed::ValueId::value)
            != instruction.write.map(|slot| slot.value)
        || (!matches!(
            instruction.instruction,
            Instruction::ConstantInteger { .. }
        ) && !instruction.constant_cells.is_empty())
    {
        return Err(refusal);
    }
    let valid = |slot: &GuestPlacedOperand| {
        let expected_words = match slot.type_kind {
            TernaryCfgScalarKind::I32 | TernaryCfgScalarKind::U32 => 2,
            TernaryCfgScalarKind::Bool
            | TernaryCfgScalarKind::I8
            | TernaryCfgScalarKind::I16
            | TernaryCfgScalarKind::U8
            | TernaryCfgScalarKind::U16 => 1,
        };
        slot.words == expected_words
            && slot
                .address
                .checked_add(expected_words)
                .is_some_and(|end| end <= CURRENT_WORD_COUNT)
    };
    if instruction.reads.iter().any(|slot| !valid(slot))
        || instruction.write.is_some_and(|slot| !valid(&slot))
    {
        return Err(refusal);
    }
    let translated = |slot: GuestPlacedOperand| GuestStorageValue {
        offset: slot.address,
        type_kind: slot.type_kind,
        value: slot.value,
        words: slot.words,
    };
    let reads = instruction
        .reads
        .iter()
        .copied()
        .map(translated)
        .collect::<Vec<_>>();
    super::state_operations::validate_operation_operands(
        &instruction.instruction,
        &reads,
        instruction.write.map(translated),
    )
    .map_err(|_| refusal)
}

fn required_operation_effects(
    instruction: &GuestPlacedInstruction,
) -> Result<Vec<GuestCodeOperationEffect>, GuestCodePlacementError> {
    validate_code_operation_operands(instruction)?;
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
            || source.address >= CURRENT_WORD_COUNT
            || instruction.write.is_some()
            || !instruction.constant_cells.is_empty()
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
        effects.push(GuestCodeOperationEffect::Output { source: *source });
    }
    if let Some(destination) = instruction.write {
        if destination.words == 0
            || destination
                .address
                .checked_add(destination.words)
                .is_none_or(|end| end > CURRENT_WORD_COUNT)
            || instruction
                .constant_cells
                .iter()
                .any(|cell| cell.word >= CURRENT_WORD_COUNT)
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
        if let Instruction::ConstantInteger { result, .. } =
            &instruction.instruction
        {
            if destination.value != result.value() {
                return Err(GuestCodePlacementError::InvalidCodePlacement);
            }
            let source_slot = GuestStorageValue {
                offset: destination.address,
                type_kind: destination.type_kind,
                value: destination.value,
                words: destination.words,
            };
            let expected = super::state_operations::literal_cells(
                &instruction.instruction,
                Some(source_slot),
            )
            .map_err(|_| GuestCodePlacementError::InvalidCodePlacement)?;
            let expected_cells = expected
                .iter()
                .map(|cell| (cell.destination, cell.word))
                .collect::<Vec<_>>();
            let actual_cells = instruction
                .constant_cells
                .iter()
                .map(|cell| (cell.address, cell.word))
                .collect::<Vec<_>>();
            if expected_cells != actual_cells {
                return Err(GuestCodePlacementError::InvalidCodePlacement);
            }
        }
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

// Called only after source-locked operand validation. The computation is
// descriptive: it cannot be executed or pre-evaluated in this compiler stage.
fn bound_computation(
    instruction: &GuestPlacedInstruction,
) -> Option<GuestCodeComputation> {
    match (
        &instruction.instruction,
        instruction.reads.as_slice(),
        instruction.write,
    ) {
        (
            Instruction::Binary { operation, .. },
            [left, right],
            Some(result),
        ) => Some(GuestCodeComputation::Binary {
            operation: *operation,
            left: *left,
            right: *right,
            result,
        }),
        (
            Instruction::Compare { operation, .. },
            [left, right],
            Some(result),
        ) => Some(GuestCodeComputation::Compare {
            operation: *operation,
            left: *left,
            right: *right,
            result,
        }),
        (Instruction::Cast { operation, .. }, [source], Some(result)) => {
            Some(GuestCodeComputation::Cast {
                operation: *operation,
                result,
                source: *source,
            })
        },
        _ => None,
    }
}

// An explicitly anchored, two-word source literal may be written high-first.
// No source-visible effect occurs between its two independent constant stores.
// Runtime input and computed results retain canonical physical effect order.
fn scheduled_operation_effects(
    instruction: &GuestPlacedInstruction,
    key: (u32, u32, u32),
    anchors: &BTreeMap<(u32, u32, u32, u32), u32>,
) -> Result<Vec<(u32, GuestCodeOperationEffect)>, GuestCodePlacementError> {
    let mut effects = required_operation_effects(instruction)?
        .into_iter()
        .enumerate()
        .map(|(index, effect)| {
            u32::try_from(index)
                .map(|index| (index, effect))
                .map_err(|_| GuestCodePlacementError::InvalidCodePlacement)
        })
        .collect::<Result<Vec<_>, _>>()?;
    if matches!(instruction.instruction, Instruction::ConstantInteger { .. })
        && effects.len() == 2
    {
        let low = anchors.get(&(key.0, key.1, key.2, 0));
        let high = anchors.get(&(key.0, key.1, key.2, 1));
        if matches!((low, high), (Some(low), Some(high)) if high < low) {
            effects.reverse();
        }
    }
    Ok(effects)
}

fn bind_operation_sites(
    block: &GuestPlacedBlock,
    placement: GuestCodeBlockPlacement,
    anchors: &BTreeMap<(u32, u32, u32), u32>,
    effect_anchors: &BTreeMap<(u32, u32, u32, u32), u32>,
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
        let ordinal = u32::try_from(index)
            .map_err(|_| GuestCodePlacementError::InvalidCodePlacement)?;
        let key = (block.function, block.block, ordinal);
        let effects =
            scheduled_operation_effects(instruction, key, effect_anchors)?;
        let first_index = effects
            .first()
            .map(|(effect_index, _)| *effect_index)
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        let start = anchors
            .get(&key)
            .copied()
            .or_else(|| {
                effect_anchors
                    .get(&(key.0, key.1, key.2, first_index))
                    .copied()
            })
            .unwrap_or(next_address);
        for (position, (effect_index, effect)) in
            effects.into_iter().enumerate()
        {
            let code_address = effect_anchors
                .get(&(key.0, key.1, key.2, effect_index))
                .copied()
                .unwrap_or(if position == 0 {
                    start
                } else {
                    next_address
                });
            if (position == 0 && code_address != start)
                || code_address < next_address
            {
                return Err(GuestCodePlacementError::InvalidCodePlacement);
            }
            next_address = code_address
                .checked_add(1)
                .filter(|end| *end <= placement.control_start)
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
            computation: bound_computation(instruction),
            end_exclusive: next_address,
            function: block.function,
            ordinal,
            start,
        });
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
    bind_source_locked_cfg_code_targets_with_operation_anchors(
        canonical,
        source_cells,
        frame_base,
        proposals,
        &[],
    )
}

/// Bind canonical source operations to proposed physical effect locations.
///
/// A source operation may need preparatory guest code before its first
/// effective input, output, computation or data write. Each supplied anchor
/// identifies a source instruction and its *first required effect*, not an
/// arbitrary N15 instruction or a completed source operation. The checked
/// effect cells remain consecutive within that instruction and ordered
/// relative to other operations in its block, except that explicitly pinned
/// independent two-word constant writes can run high-first. Unanchored
/// operations retain
/// their earliest nonoverlapping minimum placements, and all code/control/phi
/// intervals retain their original source-owned reservations.
///
/// No operation execution, operands, jumps, signed EOF normalization or
/// self-modification is proved. The physical linker must independently check
/// the proposed effects against the normative guest VM before publication.
///
/// # Errors
///
/// Rejects unknown or duplicated source identities, an anchor before a prior
/// effect, insufficient instruction capacity, out-of-block positions, source
/// tampering or code/data/phi overlaps.
pub fn bind_source_locked_cfg_code_targets_with_operation_anchors(
    canonical: &[u8],
    source_cells: u32,
    frame_base: u32,
    proposals: GuestCodeProposals<'_>,
    anchors: &[GuestCodeOperationAnchor],
) -> Result<GuestAddressedCfgPlan, GuestCodePlacementError> {
    bind_source_locked_cfg_code_targets_with_effect_anchors(
        canonical,
        source_cells,
        frame_base,
        proposals,
        anchors,
        &[],
    )
}

/// Bind source-typed individual effects to sparse physical code addresses.
///
/// Within each canonical instruction, required effects stay in their exact
/// source-derived order except a pair of independent two-word literal stores
/// that are both explicitly pinned, whose order may be reversed. Unanchored
/// effects follow the preceding physical effect in the earliest available
/// cell. Arbitrary setup gaps are permitted before or between them, but
/// cannot overlap later operations, source control or phi pads. Operation
/// anchors identify the first *physical* effect and must agree with any
/// separate anchor naming that effect's canonical index.
///
/// These are checked **proposals**, not verified VM transitions. In
/// particular a signed C23 input remains unimplemented unless real `/` and
/// both full-width guest writes execute with correct values and dependence.
///
/// # Errors
///
/// Refuses foreign, duplicated, inconsistent, out-of-order or out-of-block
/// effect addresses, along with all ordinary source relocation errors.
pub fn bind_source_locked_cfg_code_targets_with_effect_anchors(
    canonical: &[u8],
    source_cells: u32,
    frame_base: u32,
    proposals: GuestCodeProposals<'_>,
    anchors: &[GuestCodeOperationAnchor],
    effect_anchors: &[GuestCodeEffectAnchor],
) -> Result<GuestAddressedCfgPlan, GuestCodePlacementError> {
    let mut anchored = BTreeMap::new();
    for anchor in anchors {
        if anchored
            .insert(
                (anchor.function, anchor.block, anchor.ordinal),
                anchor.code_address,
            )
            .is_some()
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
    }
    let mut unmatched = anchored.clone();
    let mut anchored_effects = BTreeMap::new();
    for anchor in effect_anchors {
        if anchored_effects
            .insert(
                (
                    anchor.function,
                    anchor.block,
                    anchor.ordinal,
                    anchor.effect_index,
                ),
                anchor.code_address,
            )
            .is_some()
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
    }
    let mut unmatched_effects = anchored_effects.clone();
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
        let (sites, effects) = bind_operation_sites(
            block,
            placement,
            &anchored,
            &anchored_effects,
        )?;
        // Match canonical indices even when literal words execute high-first.
        for (ordinal, instruction) in block.instructions.iter().enumerate() {
            let ordinal = u32::try_from(ordinal)
                .map_err(|_| GuestCodePlacementError::InvalidCodePlacement)?;
            for index in 0..required_operation_effects(instruction)?.len() {
                let index = u32::try_from(index).map_err(|_| {
                    GuestCodePlacementError::InvalidCodePlacement
                })?;
                let _matched = unmatched_effects.remove(&(
                    block.function,
                    block.block,
                    ordinal,
                    index,
                ));
            }
        }
        for site in &sites {
            let _matched =
                unmatched.remove(&(site.function, site.block, site.ordinal));
        }
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
    if edge_pads.len() != pads.len()
        || !unmatched.is_empty()
        || !unmatched_effects.is_empty()
    {
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

fn source_phi_site_anchors(
    anchors: &[GuestCodePhiCopyAnchor],
) -> Result<PhiSiteAnchors, GuestCodePlacementError> {
    let mut by_edge = PhiSiteAnchors::new();
    for anchor in anchors {
        let sites = by_edge
            .entry((
                anchor.function,
                anchor.predecessor,
                anchor.kind,
                anchor.successor,
            ))
            .or_default();
        if sites
            .insert(anchor.copy_index, anchor.code_address)
            .is_some()
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
    }
    Ok(by_edge)
}

fn place_source_phi_edge_effects(
    edge: &mut GuestCodeControlEdge,
    mut anchors: BTreeMap<u32, u32>,
) -> Result<(), GuestCodePlacementError> {
    let exit = edge
        .pad_exit_address
        .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
    let total = edge
        .snapshots
        .len()
        .checked_add(edge.commits.len())
        .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
    if anchors.len() != total || total == 0 {
        return Err(GuestCodePlacementError::InvalidCodePlacement);
    }
    let mut previous = None;
    let mut placed = Vec::with_capacity(total);
    for (ordinal, copy) in
        edge.snapshots.iter().chain(&edge.commits).enumerate()
    {
        let index = u32::try_from(ordinal)
            .map_err(|_error| GuestCodePlacementError::InvalidCodePlacement)?;
        let address = anchors
            .remove(&index)
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        if !(edge.entry_address..exit).contains(&address)
            || previous.is_some_and(|prior| prior >= address)
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
        previous = Some(address);
        placed.push(GuestCodeCellCopySite {
            code_address: address,
            copy: *copy,
        });
    }
    if !anchors.is_empty() {
        return Err(GuestCodePlacementError::InvalidCodePlacement);
    }
    edge.commit_sites = placed.split_off(edge.snapshots.len());
    edge.snapshot_sites = placed;
    Ok(())
}

/// Bind sparse, source-identified physical phi-copy effect addresses.
///
/// The ordinary operation/effect anchors and disjoint source pad placement
/// remain mandatory. Each edge with explicit phi anchors must name **every**
/// snapshot and commit in source order; unanchored edges retain the compact
/// right-aligned copy suffix. Setup cells before and between physical copies
/// are reserved but do not acquire invented opcode semantics. The final pad
/// cell stays reserved for an independently verified successor transfer.
///
/// Copy values, destinations, widths and phases come only from the canonical
/// typed source. This binds proposed code cells, not executable copy proof.
///
/// # Errors
///
/// Rejects incomplete, duplicate, foreign, unordered, overlapping, off-pad
/// or exit-cell anchors, in addition to ordinary source placement errors.
pub fn bind_source_locked_cfg_code_targets_with_phi_copy_anchors(
    request: GuestCodePhiCopyPlacement<'_>,
) -> Result<GuestAddressedCfgPlan, GuestCodePlacementError> {
    let mut plan = bind_source_locked_cfg_code_targets_with_effect_anchors(
        request.canonical,
        request.source_cells,
        request.frame_base,
        request.proposals,
        request.operation_anchors,
        request.effect_anchors,
    )?;
    let mut by_edge = source_phi_site_anchors(request.phi_anchors)?;
    for edge in &mut plan.control_edges {
        if let Some(sites) = by_edge.remove(&(
            edge.function,
            edge.predecessor,
            edge.kind,
            edge.successor,
        )) {
            place_source_phi_edge_effects(edge, sites)?;
        }
    }
    if !by_edge.is_empty() {
        return Err(GuestCodePlacementError::InvalidCodePlacement);
    }
    Ok(plan)
}

// This is a lower-bound source reservation, not a candidate encoding. Even a
// single Malbolge copy or input can require more code for pointer routing,
// operand preparation, conditional control and self-encryption. Keeping the
// calculation separate from physical emission avoids authoring imaginary
// opcode bytes to fill a mathematically possible but unlinked interval.
fn reserve_minimum_code_cells(
    next: &mut u32,
    cells: u32,
    source_cells: u32,
) -> Result<(u32, u32), GuestCodePlacementError> {
    let start = *next;
    let end_exclusive = start
        .checked_add(cells)
        .filter(|end| cells > 0 && *end <= source_cells)
        .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
    *next = end_exclusive;
    Ok((start, end_exclusive))
}

fn reserve_minimum_phi_pad(
    edge: &GuestPlacedControlEdge,
    function: u32,
    predecessor: u32,
    kind: GuestCodeEdgeKind,
    next: &mut u32,
    source_cells: u32,
    pads: &mut Vec<GuestCodeEdgePadPlacement>,
) -> Result<(), GuestCodePlacementError> {
    if edge.snapshots.is_empty() && edge.commits.is_empty() {
        return Ok(());
    }
    let copies = edge
        .snapshots
        .len()
        .checked_add(edge.commits.len())
        .and_then(|len| u32::try_from(len).ok())
        .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
    let minimum = copies
        .checked_add(1)
        .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
    let (start, end_exclusive) =
        reserve_minimum_code_cells(next, minimum, source_cells)?;
    pads.push(GuestCodeEdgePadPlacement {
        end_exclusive,
        function,
        kind,
        predecessor,
        start,
        successor: edge.successor,
    });
    Ok(())
}

/// Count the strict *minimum* physical instruction-cell obligations of a
/// source-authenticated typed CFG before any source length or frame base is
/// proposed. Every SSA instruction and terminator consumes at least one
/// cell, full-width guest writes consume their actual word widths, and each
/// phi-bearing control arm requires all snapshots and commits plus its jump.
/// Branch arms with the same target are counted separately: each outcome
/// owns a distinct physical landing pad when phi writes are required.
///
/// No source layout, target instruction, C input conversion or runtime path
/// is inferred from this count. Physical realizations will generally need
/// more cells for pointer routing, materialization and self-encryption.
///
/// # Errors
///
/// Refuses invalid or unsupported canonical typed IR and impossible checked
/// cell-count arithmetic. This function never publishes target code.
pub fn source_locked_cfg_minimum_code_cells(
    canonical: &[u8],
) -> Result<u32, GuestCodePlacementError> {
    let prelink = prepare_canonical_dynamic_cfg(canonical)
        .map_err(GuestCodePlacementError::TypedCfg)?;
    let mut cells = 0u32;
    for block in &prelink.operation_blocks {
        for operation in &block.instructions {
            let needed = minimum_operation_cells_by_width(
                &operation.instruction,
                operation.write.map_or(0, |destination| destination.words),
                operation.constant_cells.len(),
            )
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            cells = cells
                .checked_add(needed)
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        }
        // An unconditional jump, two-way branch selector, or return needs
        // its own physical control step after all of the block's operations.
        cells = cells
            .checked_add(1)
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        let mut edge_cost = |successor| {
            if let Some(edge) = prelink.cell_edges.iter().find(|edge| {
                edge.function == block.function
                    && edge.predecessor == block.block
                    && edge.successor == successor
            }) {
                let copies = edge
                    .snapshots
                    .len()
                    .checked_add(edge.commits.len())
                    .and_then(|len| u32::try_from(len).ok())
                    .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
                cells = cells
                    .checked_add(copies)
                    .and_then(|cells| cells.checked_add(1))
                    .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            }
            Ok::<(), GuestCodePlacementError>(())
        };
        match &block.control.terminator {
            Terminator::Jump { target } => edge_cost(target.value())?,
            Terminator::Branch {
                false_target,
                true_target,
                ..
            } => {
                edge_cost(false_target.value())?;
                edge_cost(true_target.value())?;
            },
            Terminator::Return { .. } => {},
            Terminator::Switch { .. } => {
                return Err(GuestCodePlacementError::TypedCfg(
                    TypedCfgAdapterError::UnsupportedTypedIr,
                ));
            },
        }
    }
    Ok(cells)
}

/// Automatically reserve the *minimum* disjoint code and phi landing-pad
/// intervals required by one canonical, source-authenticated typed CFG.
///
/// This removes caller-authored block and predecessor-pad coordinates from
/// the first physical planning attempt. All operations, control arms, return
/// sites and two-phase phi transfers are re-derived from the exact typed
/// source; the resulting plan is independently rebound by
/// [`bind_source_locked_cfg_code_targets`]. No Malbolge source bytes, pointer
/// paths, runtime arithmetic, signed EOF normalization or jumps are produced.
/// A real linker must expand these necessary lower bounds and verify its
/// encoded source under the normative VM before publishing any C artifact.
///
/// # Errors
///
/// Rejects corrupted canonical source, aliased/out-of-range frame placement,
/// code position overflow and a source too short for the minimum instruction
/// and edge-pad obligations. All refusal paths create no guest artifact.
pub fn plan_source_locked_cfg_minimum_code_targets(
    canonical: &[u8],
    source_cells: u32,
    frame_base: u32,
    code_base: u32,
) -> Result<GuestAddressedCfgPlan, GuestCodePlacementError> {
    let relocated =
        relocate_source_locked_cfg(canonical, source_cells, frame_base)
            .map_err(GuestCodePlacementError::TypedCfg)?;
    let minimum = source_locked_cfg_minimum_code_cells(canonical)?;
    let expected_end = code_base
        .checked_add(minimum)
        .filter(|end| *end <= source_cells)
        .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
    let mut next = code_base;
    let mut code_blocks = Vec::with_capacity(relocated.operation_blocks.len());
    for block in &relocated.operation_blocks {
        let minimum_operations = block
            .instructions
            .iter()
            .try_fold(0u32, |cells, instruction| {
                cells.checked_add(minimum_operation_cells(instruction)?)
            })
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        let control_start = next
            .checked_add(minimum_operations)
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        let (start, end_exclusive) = reserve_minimum_code_cells(
            &mut next,
            minimum_operations
                .checked_add(1)
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?,
            source_cells,
        )?;
        code_blocks.push(GuestCodeBlockPlacement {
            block: block.block,
            control_start,
            end_exclusive,
            function: block.function,
            start,
        });
    }
    let mut edge_pads = Vec::new();
    for block in &relocated.operation_blocks {
        let mut reserve = |kind, edge: &GuestPlacedControlEdge| {
            reserve_minimum_phi_pad(
                edge,
                block.function,
                block.block,
                kind,
                &mut next,
                source_cells,
                &mut edge_pads,
            )
        };
        match &block.control {
            GuestPlacedControl::Branch { when_false, when_true } => {
                reserve(GuestCodeEdgeKind::WhenFalse, when_false)?;
                reserve(GuestCodeEdgeKind::WhenTrue, when_true)?;
            },
            GuestPlacedControl::Jump { edge } => {
                reserve(GuestCodeEdgeKind::Jump, edge)?;
            },
            GuestPlacedControl::Return => {},
        }
    }
    if next != expected_end {
        return Err(GuestCodePlacementError::InvalidCodePlacement);
    }
    bind_source_locked_cfg_code_targets(
        canonical,
        source_cells,
        frame_base,
        GuestCodeProposals {
            code_blocks: &code_blocks,
            edge_pads: &edge_pads,
        },
    )
}

/// One proposed instruction address for an actual source-typed input effect.
/// The future physical linker must still prove that this position executes
/// the correct `/` under the target VM and normalizes C23 EOF correctly.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCodeInputAnchor {
    /// Canonical source block containing the signed/byte input operation.
    pub block: u32,
    /// Proposed exact physical instruction position of the input read.
    pub code_address: u32,
    /// Canonical source function identity.
    pub function: u32,
    /// Source operation ordinal; constants and computations cannot anchor.
    pub ordinal: u32,
}

fn first_fit_code_span(
    reserved: &[(u32, u32)],
    cells: u32,
    source_cells: u32,
) -> Result<(u32, u32), GuestCodePlacementError> {
    if cells == 0 {
        return Err(GuestCodePlacementError::InvalidCodePlacement);
    }
    let mut sorted = reserved.to_vec();
    sorted.sort_unstable();
    let mut start = 0u32;
    for (occupied_start, occupied_end) in sorted {
        if start
            .checked_add(cells)
            .is_some_and(|end| end <= occupied_start)
        {
            return Ok((start, start + cells));
        }
        start = start.max(occupied_end);
    }
    let end = start
        .checked_add(cells)
        .filter(|end| *end <= source_cells)
        .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
    Ok((start, end))
}

fn first_fit_phi_pad(
    edge: &GuestPlacedControlEdge,
    function: u32,
    predecessor: u32,
    kind: GuestCodeEdgeKind,
    reserved: &mut Vec<(u32, u32)>,
    source_cells: u32,
    pads: &mut Vec<GuestCodeEdgePadPlacement>,
) -> Result<(), GuestCodePlacementError> {
    if edge.snapshots.is_empty() && edge.commits.is_empty() {
        return Ok(());
    }
    let writes = edge
        .snapshots
        .len()
        .checked_add(edge.commits.len())
        .and_then(|count| u32::try_from(count).ok())
        .and_then(|count| count.checked_add(1))
        .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
    let (start, end_exclusive) =
        first_fit_code_span(reserved, writes, source_cells)?;
    reserved.push((start, end_exclusive));
    pads.push(GuestCodeEdgePadPlacement {
        end_exclusive,
        function,
        kind,
        predecessor,
        start,
        successor: edge.successor,
    });
    Ok(())
}

// Checked extent of one source-ordered snapshot/commit list, including
// optional physical setup before the first copy and after the last commit.
// The caller authenticates the edge identity separately against the typed CFG.
fn sparse_phi_pad_span(
    sites: &BTreeMap<u32, u32>,
    total: usize,
    entry: Option<u32>,
    exit: Option<u32>,
    source_cells: u32,
) -> Result<(u32, u32), GuestCodePlacementError> {
    let refused = GuestCodePlacementError::InvalidCodePlacement;
    if total == 0 || sites.len() != total {
        return Err(refused);
    }
    let mut previous = None;
    for ordinal in 0..total {
        let index = u32::try_from(ordinal).map_err(|_| refused)?;
        let address = *sites.get(&index).ok_or(refused)?;
        if previous.is_some_and(|prior| prior >= address) {
            return Err(refused);
        }
        previous = Some(address);
    }
    let first = *sites.get(&0).ok_or(refused)?;
    let last = previous.ok_or(refused)?;
    let start = match entry {
        Some(site) if site <= first => site,
        Some(_) => return Err(refused),
        None => first,
    };
    let transfer = match exit {
        Some(site) if site > last => site,
        Some(_) => return Err(refused),
        None => last.checked_add(1).ok_or(refused)?,
    };
    let end_exclusive = transfer
        .checked_add(1)
        .filter(|end| *end <= source_cells)
        .ok_or(refused)?;
    Ok((start, end_exclusive))
}

// Source-locked sparse copies and edge-specific successor transfers reserve
// their whole phi pad before first-fit placement of unrelated code. A pinned
// exit may leave setup cells after the final commit; the independent binder
// still rechecks exact source copies and the reserved transfer suffix.
fn reserve_source_phi_pads(
    blocks: &[GuestPlacedBlock],
    anchors: &[GuestCodePhiCopyAnchor],
    entries: &[GuestCodePhiEntryAnchor],
    exits: &[GuestCodePhiExitAnchor],
    source_cells: u32,
) -> Result<EdgePadPlacements, GuestCodePlacementError> {
    let mut by_edge = source_phi_site_anchors(anchors)?;
    let mut entry_by_edge = BTreeMap::new();
    for entry in entries {
        let key = (
            entry.function,
            entry.predecessor,
            entry.kind,
            entry.successor,
        );
        if entry_by_edge.insert(key, entry.code_address).is_some() {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
    }
    let mut exit_by_edge = BTreeMap::new();
    for exit in exits {
        let key = (exit.function, exit.predecessor, exit.kind, exit.successor);
        if exit_by_edge.insert(key, exit.code_address).is_some() {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
    }
    let mut pinned = EdgePadPlacements::new();
    for block in blocks {
        let mut reserve = |kind, edge: &GuestPlacedControlEdge| {
            let key = (block.function, block.block, kind, edge.successor);
            let site_list = by_edge.remove(&key);
            let entry = entry_by_edge.remove(&key);
            let exit = exit_by_edge.remove(&key);
            let Some(sites) = site_list else {
                // Entry/exit proposals without source copies are not pads.
                return (entry.is_none() && exit.is_none())
                    .then_some(())
                    .ok_or(GuestCodePlacementError::InvalidCodePlacement);
            };
            let total = edge
                .snapshots
                .len()
                .checked_add(edge.commits.len())
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            let (start, end_exclusive) =
                sparse_phi_pad_span(&sites, total, entry, exit, source_cells)?;
            let pad = GuestCodeEdgePadPlacement {
                end_exclusive,
                function: block.function,
                kind,
                predecessor: block.block,
                start,
                successor: edge.successor,
            };
            if pinned.insert(key, pad).is_some() {
                return Err(GuestCodePlacementError::InvalidCodePlacement);
            }
            Ok(())
        };
        match &block.control {
            GuestPlacedControl::Branch { when_false, when_true } => {
                reserve(GuestCodeEdgeKind::WhenFalse, when_false)?;
                reserve(GuestCodeEdgeKind::WhenTrue, when_true)?;
            },
            GuestPlacedControl::Jump { edge } => {
                reserve(GuestCodeEdgeKind::Jump, edge)?;
            },
            GuestPlacedControl::Return => {},
        }
    }
    if !by_edge.is_empty()
        || !entry_by_edge.is_empty()
        || !exit_by_edge.is_empty()
    {
        return Err(GuestCodePlacementError::InvalidCodePlacement);
    }
    Ok(pinned)
}

/// Reserve exact source-typed input code sites inside otherwise minimal,
/// disjoint code blocks and predecessor-specific phi landing pads.
///
/// This allows a future physical linker to *propose* addresses observed in a
/// real guest input prefix without requiring that all source-C blocks execute
/// in canonical numeric order. Anchors are checked against actual source
/// input operations and their preceding minimum write obligations. Two
/// source-typed reads in the same block may have intervening physical setup
/// cells; the earliest admitted first anchor fixes the block's start, while
/// subsequent anchors enlarge its reservation and remain at their exact
/// positions. No setup code or SSA store is executed by the planner.
/// Remaining blocks/pads are first-fit packed in deterministic source order;
/// no target code, runtime control, EOF conversion or guest output is built.
/// A physical VM witness and true operation/copy instruction encoding remain
/// mandatory before the result can be used for artifact publication.
///
/// # Errors
///
/// Refuses non-input/duplicate/foreign anchors, conflicting fixed blocks,
/// source-capacity exhaustion, invalid frames, and corrupted typed source.
pub fn plan_source_locked_cfg_with_input_anchors(
    canonical: &[u8],
    source_cells: u32,
    frame_base: u32,
    anchors: &[GuestCodeInputAnchor],
) -> Result<GuestAddressedCfgPlan, GuestCodePlacementError> {
    plan_source_locked_cfg_with_input_and_effect_anchors(
        canonical,
        source_cells,
        frame_base,
        anchors,
        &[],
    )
}

/// Reserve source-typed input reads and their separate physical word effects.
///
/// A signed C23 input has a real `/` and two independently addressed result
/// stores; setup instructions may separate all three. Every effect identity
/// is derived from the canonical source operation, and its fixed position
/// must remain in its source block after the associated input anchor.
/// All other blocks and predecessor phi pads are packed with deterministic
/// minimum reservations. This is a placement *proposal*: no guest opcodes,
/// signed conversion, value writes, or CFG runtime effects are emitted.
///
/// # Errors
///
/// Rejects unknown, duplicate, conflicting or out-of-order source effects;
/// effects without a pinned source input block; and insufficient guest code
/// space or incompatible frame relocation.
pub fn plan_source_locked_cfg_with_input_and_effect_anchors(
    canonical: &[u8],
    source_cells: u32,
    frame_base: u32,
    anchors: &[GuestCodeInputAnchor],
    effect_anchors: &[GuestCodeEffectAnchor],
) -> Result<GuestAddressedCfgPlan, GuestCodePlacementError> {
    let operations = anchors
        .iter()
        .map(|anchor| GuestCodeOperationAnchor {
            block: anchor.block,
            code_address: anchor.code_address,
            function: anchor.function,
            ordinal: anchor.ordinal,
        })
        .collect::<Vec<_>>();
    plan_source_locked_cfg_with_general_effect_anchors(
        &GuestCodeFunctionEntryPlacement {
            canonical,
            source_cells,
            frame_base,
            operation_anchors: &operations,
            effect_anchors,
            control_anchors: &[],
            phi_anchors: &[],
            phi_entries: &[],
            phi_exits: &[],
            function_entries: &[],
        },
        true,
    )
}

/// Automatically reserve source-locked, sparsely anchored operations from
/// **any** typed CFG block, including literals before the first real input
/// and arithmetic in blocks without input. The earliest anchored operation
/// or individual effect fixes that block's minimum canonical prefix, while
/// later effect anchors may leave setup cells between source-ordered effects.
/// Other source blocks and predecessor-specific phi pads remain disjoint.
///
/// All source instructions, write widths and control edges are independently
/// rebound from canonical typed IR. These are only proposed code positions;
/// no guest opcodes, source arithmetic, signed EOF conversion or branch
/// transfers execute here.
///
/// # Errors
///
/// Refuses missing, duplicate, out-of-order or foreign source operation
/// identities, overlapping code/phi reservations and invalid frame geometry.
pub fn plan_source_locked_cfg_with_operation_and_effect_anchors(
    canonical: &[u8],
    source_cells: u32,
    frame_base: u32,
    anchors: &[GuestCodeOperationAnchor],
    effect_anchors: &[GuestCodeEffectAnchor],
) -> Result<GuestAddressedCfgPlan, GuestCodePlacementError> {
    plan_source_locked_cfg_with_general_effect_anchors(
        &GuestCodeFunctionEntryPlacement {
            canonical,
            source_cells,
            frame_base,
            operation_anchors: anchors,
            effect_anchors,
            control_anchors: &[],
            phi_anchors: &[],
            phi_entries: &[],
            phi_exits: &[],
            function_entries: &[],
        },
        false,
    )
}

/// Plan sparse source-typed operation effects and their block control sites.
///
/// A control-only anchor fixes the source block's minimum operation prefix
/// immediately before its proposed physical control instruction. A block
/// with earlier operation anchors instead reserves all intervening setup
/// cells before its exact control position. All reservations remain disjoint
/// from other blocks, source phi pads and the relocated state frame.
///
/// The control is not encoded or run here: an independent target verifier
/// must prove the real branch/halt transition and its data dependence.
///
/// # Errors
///
/// Refuses duplicated, foreign, reordered or overlapping control addresses,
/// alongside the ordinary source operation and frame placement errors.
pub fn plan_source_locked_cfg_with_operation_effect_and_control_anchors(
    canonical: &[u8],
    source_cells: u32,
    frame_base: u32,
    anchors: &[GuestCodeOperationAnchor],
    effect_anchors: &[GuestCodeEffectAnchor],
    controls: &[GuestCodeControlAnchor],
) -> Result<GuestAddressedCfgPlan, GuestCodePlacementError> {
    plan_source_locked_cfg_with_general_effect_anchors(
        &GuestCodeFunctionEntryPlacement {
            canonical,
            source_cells,
            frame_base,
            operation_anchors: anchors,
            effect_anchors,
            control_anchors: controls,
            phi_anchors: &[],
            phi_entries: &[],
            phi_exits: &[],
            function_entries: &[],
        },
        false,
    )
}

/// Automatically reserve exact source-typed operation, control and sparse
/// predecessor-specific phi-copy sites without caller-authored block pads.
/// Every anchored phi edge requires its complete source-derived snapshot and
/// commit list. Unanchored edges retain minimum first-fit pads, and fixed
/// pads are protected from unanchored block placement.
///
/// No proposed opcode, copy or control transfer is trusted without the
/// independent target VM/layout checker; this is still a code-space plan.
///
/// # Errors
///
/// Refuses incomplete, duplicate, non-monotone or foreign phi-copy anchors,
/// code/pad collisions and ordinary typed CFG placement errors.
pub fn plan_source_locked_cfg_with_operation_effect_control_and_phi_anchors(
    canonical: &[u8],
    source_cells: u32,
    frame_base: u32,
    anchors: &[GuestCodeOperationAnchor],
    effect_anchors: &[GuestCodeEffectAnchor],
    controls: &[GuestCodeControlAnchor],
    phi_anchors: &[GuestCodePhiCopyAnchor],
) -> Result<GuestAddressedCfgPlan, GuestCodePlacementError> {
    plan_source_locked_cfg_with_general_effect_anchors(
        &GuestCodeFunctionEntryPlacement {
            canonical,
            source_cells,
            frame_base,
            operation_anchors: anchors,
            effect_anchors,
            control_anchors: controls,
            phi_anchors,
            phi_entries: &[],
            phi_exits: &[],
            function_entries: &[],
        },
        false,
    )
}

/// Reserve an exact source-identified successor transfer after sparse phi
/// copies, allowing real pointer-setup code between the last commit and `i`.
///
/// Every anchored exit must identify a fully anchored, source-derived phi
/// edge. Its address must follow all writes, fit source memory and stay
/// disjoint from source blocks and all other predecessor-specific phi pads.
/// Copies, typed effects and the transfer location remain *proposals*;
/// actual Malbolge guest execution and EOF loop linkage are not inferred.
///
/// # Errors
///
/// Refuses a missing/foreign/duplicated phi edge, transfer before or on a
/// copy, source-capacity exhaustion, overlaps or invalid source identities.
#[expect(
    clippy::too_many_arguments,
    reason = "one source-locked placement API retains each anchor category"
)]
pub fn plan_source_locked_cfg_with_phi_exit_anchors(
    canonical: &[u8],
    source_cells: u32,
    frame_base: u32,
    anchors: &[GuestCodeOperationAnchor],
    effect_anchors: &[GuestCodeEffectAnchor],
    controls: &[GuestCodeControlAnchor],
    phi_anchors: &[GuestCodePhiCopyAnchor],
    exits: &[GuestCodePhiExitAnchor],
) -> Result<GuestAddressedCfgPlan, GuestCodePlacementError> {
    plan_source_locked_cfg_with_general_effect_anchors(
        &GuestCodeFunctionEntryPlacement {
            canonical,
            source_cells,
            frame_base,
            operation_anchors: anchors,
            effect_anchors,
            control_anchors: controls,
            phi_anchors,
            phi_entries: &[],
            phi_exits: exits,
            function_entries: &[],
        },
        false,
    )
}

/// Reserve predecessor-owned phi-pad entry and successor-transfer sites
/// around exact source-authenticated snapshot and commit effect addresses.
/// Pre-snapshot and post-commit guest setup is allowed but never inferred.
/// This produces *only* a disjoint reservation; the real physical linker
/// still owes code bytes, control transfers and a normative VM trace.
///
/// # Errors
///
/// Refuses missing or foreign phi effects, unordered boundary addresses,
/// duplicate edge identities, collisions and capacity exhaustion.
#[expect(
    clippy::too_many_arguments,
    reason = "each canonical anchor class is an independent placement input"
)]
pub fn plan_source_locked_cfg_with_phi_boundary_anchors(
    canonical: &[u8],
    source_cells: u32,
    frame_base: u32,
    anchors: &[GuestCodeOperationAnchor],
    effect_anchors: &[GuestCodeEffectAnchor],
    controls: &[GuestCodeControlAnchor],
    phi_anchors: &[GuestCodePhiCopyAnchor],
    entries: &[GuestCodePhiEntryAnchor],
    exits: &[GuestCodePhiExitAnchor],
) -> Result<GuestAddressedCfgPlan, GuestCodePlacementError> {
    plan_source_locked_cfg_with_general_effect_anchors(
        &GuestCodeFunctionEntryPlacement {
            canonical,
            source_cells,
            frame_base,
            operation_anchors: anchors,
            effect_anchors,
            control_anchors: controls,
            phi_anchors,
            phi_entries: entries,
            phi_exits: exits,
            function_entries: &[],
        },
        false,
    )
}

/// Reserve source-checked function entries ahead of sparse typed effects.
///
/// The entry must name the canonical function's actual entry block, not an
/// arbitrary block elsewhere in its CFG. Earlier setup cells stay inside
/// that block; anchored effects cannot move backwards to fit the entry.
///
/// This is a physical code *reservation* only. It does not prove reachability,
/// decoded guest opcodes, C23 arithmetic, branch behavior or EOF termination.
///
/// # Errors
///
/// Refuses foreign, duplicate, non-entry, late or overlapping function entry
/// anchors and all previously checked sparse operation/phi placement errors.
pub fn plan_source_locked_cfg_with_function_entry_anchors(
    request: &GuestCodeFunctionEntryPlacement<'_>,
) -> Result<GuestAddressedCfgPlan, GuestCodePlacementError> {
    plan_source_locked_cfg_with_general_effect_anchors(request, false)
}

fn plan_source_locked_cfg_with_general_effect_anchors(
    request: &GuestCodeFunctionEntryPlacement<'_>,
    inputs_only: bool,
) -> Result<GuestAddressedCfgPlan, GuestCodePlacementError> {
    let GuestCodeFunctionEntryPlacement {
        canonical,
        source_cells,
        frame_base,
        operation_anchors: anchors,
        effect_anchors,
        control_anchors: controls,
        phi_anchors,
        phi_entries: entries,
        phi_exits: exits,
        function_entries,
    } = *request;
    let relocated =
        relocate_source_locked_cfg(canonical, source_cells, frame_base)
            .map_err(GuestCodePlacementError::TypedCfg)?;
    // Real physical source sites may be sparse, but every anchored
    // instruction must remain ordered within its canonical basic block.
    let mut operation_sites = BTreeMap::<(u32, u32), BTreeMap<u32, u32>>::new();
    for anchor in anchors {
        let block = relocated
            .operation_blocks
            .iter()
            .find(|block| {
                (block.function, block.block) == (anchor.function, anchor.block)
            })
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        let ordinal = usize::try_from(anchor.ordinal)
            .map_err(|_| GuestCodePlacementError::InvalidCodePlacement)?;
        let operation = block
            .instructions
            .get(ordinal)
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        if (inputs_only
            && !matches!(
                operation.instruction,
                Instruction::Getchar { .. } | Instruction::ByteInput { .. }
            ))
            || operation_sites
                .entry((anchor.function, anchor.block))
                .or_default()
                .insert(anchor.ordinal, anchor.code_address)
                .is_some()
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
    }
    let mut anchored_effects = BTreeMap::new();
    for anchor in effect_anchors {
        if (inputs_only
            && !operation_sites.contains_key(&(anchor.function, anchor.block)))
            || anchored_effects
                .insert(
                    (
                        anchor.function,
                        anchor.block,
                        anchor.ordinal,
                        anchor.effect_index,
                    ),
                    anchor.code_address,
                )
                .is_some()
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
    }
    let mut control_sites = BTreeMap::<(u32, u32), u32>::new();
    for anchor in controls {
        let key = (anchor.function, anchor.block);
        if !relocated
            .operation_blocks
            .iter()
            .any(|block| (block.function, block.block) == key)
            || control_sites.insert(key, anchor.code_address).is_some()
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
    }
    let mut function_sites = BTreeMap::new();
    for entry in function_entries {
        let key = (entry.function, entry.block);
        if !relocated.prelink.cfg.functions.iter().any(|function| {
            function.id == entry.function && function.entry == entry.block
        }) || function_sites.insert(key, entry.code_address).is_some()
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
    }
    let mut fixed = BTreeMap::<(u32, u32), GuestCodeBlockPlacement>::new();
    for block in &relocated.operation_blocks {
        let key = (block.function, block.block);
        let sites = operation_sites.get(&key);
        let control_site = control_sites.get(&key).copied();
        let function_entry = function_sites.get(&key).copied();
        // A reached source-word store may be known before its preceding
        // input or computation opcode has been located. Recover the minimum
        // canonical prefix from whichever source-ordered effect was anchored
        // first, whether or not its operation has an explicit start site.
        let first_operation = sites.and_then(|sites| {
            sites
                .iter()
                .next()
                .map(|(&ordinal, &address)| (ordinal, 0u32, address))
        });
        let mut first_effect = None;
        for (&(function, id, ordinal, index), &address) in &anchored_effects {
            if (function, id) != key {
                continue;
            }
            let instruction = block
                .instructions
                .get(usize::try_from(ordinal).map_err(|_| {
                    GuestCodePlacementError::InvalidCodePlacement
                })?)
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            let schedule = scheduled_operation_effects(
                instruction,
                (function, id, ordinal),
                &anchored_effects,
            )?;
            let position = schedule
                .iter()
                .position(|(effect_index, _)| *effect_index == index)
                .and_then(|position| u32::try_from(position).ok())
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            if first_effect.is_none_or(|(best_ordinal, best_position, _)| {
                (ordinal, position) < (best_ordinal, best_position)
            }) {
                first_effect = Some((ordinal, position, address));
            }
        }
        let first_site = first_operation
            .into_iter()
            .chain(first_effect)
            .min_by_key(|&(ordinal, index, _)| (ordinal, index));
        if first_site.is_none()
            && control_site.is_none()
            && function_entry.is_none()
        {
            continue;
        }
        let start = if let Some(address) = function_entry {
            address
        } else if let Some((ordinal, effect_index, address)) = first_site {
            let ordinal = usize::try_from(ordinal)
                .map_err(|_| GuestCodePlacementError::InvalidCodePlacement)?;
            let earlier = block
                .instructions
                .get(..ordinal)
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            let prefix = earlier
                .iter()
                .try_fold(0u32, |cells, instruction| {
                    cells.checked_add(minimum_operation_cells(instruction)?)
                })
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            let operation = block
                .instructions
                .get(ordinal)
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            if effect_index
                >= minimum_operation_cells(operation)
                    .ok_or(GuestCodePlacementError::InvalidCodePlacement)?
            {
                return Err(GuestCodePlacementError::InvalidCodePlacement);
            }
            address
                .checked_sub(
                    prefix
                        .checked_add(effect_index)
                        .ok_or(GuestCodePlacementError::InvalidCodePlacement)?,
                )
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?
        } else {
            let minimum = block
                .instructions
                .iter()
                .try_fold(0u32, |cells, instruction| {
                    cells.checked_add(minimum_operation_cells(instruction)?)
                })
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            control_site
                .and_then(|address| address.checked_sub(minimum))
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?
        };
        let mut next = start;
        for (ordinal, instruction) in block.instructions.iter().enumerate() {
            let ordinal = u32::try_from(ordinal)
                .map_err(|_| GuestCodePlacementError::InvalidCodePlacement)?;
            let effects = scheduled_operation_effects(
                instruction,
                (block.function, block.block, ordinal),
                &anchored_effects,
            )?;
            for (position, (effect_index, _)) in effects.iter().enumerate() {
                let from_operation = (position == 0)
                    .then(|| sites.and_then(|sites| sites.get(&ordinal)))
                    .flatten()
                    .copied();
                let from_effect = anchored_effects
                    .get(&(block.function, block.block, ordinal, *effect_index))
                    .copied();
                if from_operation.is_some()
                    && from_effect.is_some()
                    && from_operation != from_effect
                {
                    return Err(GuestCodePlacementError::InvalidCodePlacement);
                }
                if let Some(site) = from_operation.or(from_effect) {
                    if site < next {
                        return Err(
                            GuestCodePlacementError::InvalidCodePlacement,
                        );
                    }
                    next = site;
                }
                next = next
                    .checked_add(1)
                    .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            }
        }
        let control_start = control_site.unwrap_or(next);
        if control_start < next {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
        let end_exclusive = control_start
            .checked_add(1)
            .filter(|end| *end <= source_cells)
            .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
        if fixed
            .insert((block.function, block.block), GuestCodeBlockPlacement {
                block: block.block,
                control_start,
                end_exclusive,
                function: block.function,
                start,
            })
            .is_some()
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
    }
    let mut reserved = Vec::<(u32, u32)>::new();
    for block in fixed.values() {
        if reserved.iter().any(|&(start, end)| {
            block.start < end && start < block.end_exclusive
        }) {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
        reserved.push((block.start, block.end_exclusive));
    }
    let pinned_pads = reserve_source_phi_pads(
        &relocated.operation_blocks,
        phi_anchors,
        entries,
        exits,
        source_cells,
    )?;
    for pad in pinned_pads.values() {
        if reserved
            .iter()
            .any(|&(start, end)| pad.start < end && start < pad.end_exclusive)
        {
            return Err(GuestCodePlacementError::InvalidCodePlacement);
        }
        reserved.push((pad.start, pad.end_exclusive));
    }
    let mut blocks = Vec::with_capacity(relocated.operation_blocks.len());
    for block in &relocated.operation_blocks {
        let key = (block.function, block.block);
        let placed = if let Some(&placed) = fixed.get(&key) {
            placed
        } else {
            let operations = block
                .instructions
                .iter()
                .try_fold(0u32, |cells, instruction| {
                    cells.checked_add(minimum_operation_cells(instruction)?)
                })
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            let width = operations
                .checked_add(1)
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            let (start, end_exclusive) =
                first_fit_code_span(&reserved, width, source_cells)?;
            let control_start = start
                .checked_add(operations)
                .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
            let placement = GuestCodeBlockPlacement {
                block: block.block,
                control_start,
                end_exclusive,
                function: block.function,
                start,
            };
            reserved.push((start, end_exclusive));
            placement
        };
        blocks.push(placed);
    }
    let mut pads = Vec::new();
    for block in &relocated.operation_blocks {
        let mut reserve = |kind, edge: &GuestPlacedControlEdge| {
            let key = (block.function, block.block, kind, edge.successor);
            if let Some(&pad) = pinned_pads.get(&key) {
                pads.push(pad);
                Ok(())
            } else {
                first_fit_phi_pad(
                    edge,
                    block.function,
                    block.block,
                    kind,
                    &mut reserved,
                    source_cells,
                    &mut pads,
                )
            }
        };
        match &block.control {
            GuestPlacedControl::Branch { when_false, when_true } => {
                reserve(GuestCodeEdgeKind::WhenFalse, when_false)?;
                reserve(GuestCodeEdgeKind::WhenTrue, when_true)?;
            },
            GuestPlacedControl::Jump { edge } => {
                reserve(GuestCodeEdgeKind::Jump, edge)?;
            },
            GuestPlacedControl::Return => {},
        }
    }
    let used = reserved
        .iter()
        .try_fold(0u32, |sum, &(start, end)| {
            sum.checked_add(end.checked_sub(start)?)
        })
        .ok_or(GuestCodePlacementError::InvalidCodePlacement)?;
    if used < source_locked_cfg_minimum_code_cells(canonical)? {
        return Err(GuestCodePlacementError::InvalidCodePlacement);
    }
    bind_source_locked_cfg_code_targets_with_phi_copy_anchors(
        GuestCodePhiCopyPlacement {
            canonical,
            source_cells,
            frame_base,
            proposals: GuestCodeProposals {
                code_blocks: &blocks,
                edge_pads: &pads,
            },
            operation_anchors: anchors,
            effect_anchors,
            phi_anchors,
        },
    )
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
        instruction.reads = vec![GuestPlacedOperand {
            address: super::CURRENT_WORD_COUNT,
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
    fn literal_effects_refuse_non_guest_words_and_invalid_write_width() {
        use super::super::ternary::TernaryCfgScalarKind;
        use super::super::typed::{
            Instruction, IntegerConstant, SourcePosition, SourceSpan, TypeId,
            ValueId,
        };
        use super::{
            CURRENT_WORD_COUNT, GuestCodeOperationEffect,
            GuestCodePlacementError, GuestPlacedInstruction,
            GuestPlacedLiteralCell, GuestPlacedOperand,
            required_operation_effects,
        };

        let first = CURRENT_WORD_COUNT.saturating_sub(2);
        let operand = GuestPlacedOperand {
            address: first,
            type_kind: TernaryCfgScalarKind::U32,
            value: 31,
            words: 2,
        };
        let source = SourcePosition::new(0, 1, 1);
        let mut instruction = GuestPlacedInstruction {
            constant_cells: vec![
                GuestPlacedLiteralCell { address: first, word: 0 },
                GuestPlacedLiteralCell {
                    address: first + 1,
                    word: 0,
                },
            ],
            instruction: Instruction::ConstantInteger {
                constant: IntegerConstant::new(32, vec![0, 0, 0, 0]),
                result: ValueId::new(31),
                type_id: TypeId::new(1),
            },
            reads: Vec::new(),
            span: SourceSpan::new(source, source),
            write: Some(operand),
        };
        assert_eq!(
            required_operation_effects(&instruction),
            Ok(vec![
                GuestCodeOperationEffect::Store {
                    destination: first,
                    literal: Some(0),
                },
                GuestCodeOperationEffect::Store {
                    destination: first + 1,
                    literal: Some(0),
                },
            ])
        );
        let refusal = Err(GuestCodePlacementError::InvalidCodePlacement);
        instruction.constant_cells[1].word = 299;
        assert_eq!(required_operation_effects(&instruction), refusal);
        instruction.constant_cells[1].word = CURRENT_WORD_COUNT;
        assert_eq!(required_operation_effects(&instruction), refusal);
        instruction.constant_cells[1].word = 0;
        instruction.write = Some(GuestPlacedOperand { value: 32, ..operand });
        assert_eq!(required_operation_effects(&instruction), refusal);
        instruction.write = Some(GuestPlacedOperand {
            address: CURRENT_WORD_COUNT - 1,
            ..operand
        });
        assert_eq!(required_operation_effects(&instruction), refusal);
        instruction.constant_cells.clear();
        instruction.write = Some(GuestPlacedOperand { words: 0, ..operand });
        assert_eq!(required_operation_effects(&instruction), refusal);
    }

    #[test]
    fn computed_operation_effects_refuse_forged_literals_and_operand_bindings()
    {
        use super::super::ternary::TernaryCfgScalarKind;
        use super::super::typed::{
            BinaryOp, CastOp, CompareOp, Instruction, SourcePosition,
            SourceSpan, TypeId, ValueId,
        };
        use super::{
            GuestCodePlacementError, GuestPlacedInstruction,
            GuestPlacedLiteralCell, GuestPlacedOperand,
            required_operation_effects,
        };

        let at = |address, value, type_kind, words| GuestPlacedOperand {
            address,
            type_kind,
            value,
            words,
        };
        let left = at(4100, 1, TernaryCfgScalarKind::U32, 2);
        let right = at(4102, 2, TernaryCfgScalarKind::U32, 2);
        let result = at(4104, 3, TernaryCfgScalarKind::U32, 2);
        let source = SourcePosition::new(0, 1, 1);
        let mut placed = GuestPlacedInstruction {
            constant_cells: Vec::new(),
            instruction: Instruction::Binary {
                left: ValueId::new(1),
                operation: BinaryOp::Xor,
                result: ValueId::new(3),
                right: ValueId::new(2),
                type_id: TypeId::new(1),
            },
            reads: vec![left, right],
            span: SourceSpan::new(source, source),
            write: Some(result),
        };
        assert!(required_operation_effects(&placed).is_ok());
        let refusal = Err(GuestCodePlacementError::InvalidCodePlacement);
        placed.constant_cells = vec![
            GuestPlacedLiteralCell { address: 4104, word: 0 },
            GuestPlacedLiteralCell { address: 4105, word: 0 },
        ];
        assert_eq!(required_operation_effects(&placed), refusal);
        placed.constant_cells.clear();
        placed.reads.swap(0, 1);
        assert_eq!(required_operation_effects(&placed), refusal);
        placed.reads = vec![left, at(4102, 9, TernaryCfgScalarKind::U32, 2)];
        assert_eq!(required_operation_effects(&placed), refusal);
        placed.reads = vec![left, right];
        placed.write = Some(at(4104, 9, TernaryCfgScalarKind::U32, 2));
        assert_eq!(required_operation_effects(&placed), refusal);
        placed.write = Some(result);
        placed.reads[0].words = 1;
        assert_eq!(required_operation_effects(&placed), refusal);

        let comparison = at(4106, 4, TernaryCfgScalarKind::Bool, 1);
        placed.reads = vec![left, right];
        placed.write = Some(comparison);
        placed.instruction = Instruction::Compare {
            left: ValueId::new(1),
            operation: CompareOp::Equal,
            result: ValueId::new(4),
            right: ValueId::new(2),
            type_id: TypeId::new(2),
        };
        assert!(required_operation_effects(&placed).is_ok());
        placed
            .constant_cells
            .push(GuestPlacedLiteralCell { address: 4106, word: 1 });
        assert_eq!(required_operation_effects(&placed), refusal);
        placed.constant_cells.clear();
        placed.reads[0].words = 1;
        assert_eq!(required_operation_effects(&placed), refusal);

        let converted = at(4107, 5, TernaryCfgScalarKind::U8, 1);
        placed.instruction = Instruction::Cast {
            operation: CastOp::Truncate,
            result: ValueId::new(5),
            type_id: TypeId::new(3),
            value: ValueId::new(1),
        };
        placed.reads = vec![left];
        placed.write = Some(converted);
        assert!(required_operation_effects(&placed).is_ok());
        placed.reads.clear();
        assert_eq!(required_operation_effects(&placed), refusal);
        placed.reads.push(left);
        placed
            .constant_cells
            .push(GuestPlacedLiteralCell { address: 4107, word: 0 });
        assert_eq!(required_operation_effects(&placed), refusal);
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
