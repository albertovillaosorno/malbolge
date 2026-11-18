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
//   - Relocatable guest state cells and parallel phi-edge copy scheduling.
// - Must-Not:
//   - Assign absolute guest addresses, mutate state on the host, or publish
//     source code without verified physical code/data layout.
// - Allows:
//   - Inputs: source-authenticated typed SSA and validated ternary phi edges.
//   - Outputs: bounded nonaliasing frame offsets and two-phase cell copies.
//   - Side effects: none.
// - Split-When:
//   - Target linker owns exact code/data relocation and guest write encoding.
// - Merge-When:
//   - A general verified guest-frame planner replaces this limited scalar ABI.
// - Summary:
//   - Gives mutable checksum locals disjoint target-word reservations while
//     protecting parallel phi assignments from copy-order clobbering.
// - Description:
//   - Signed EOF is preserved in two 15-trit cells, not narrowed to u8.
// - Usage:
//   - Called only after canonical typed CFG and phi-edge admission.
// - Defaults:
//   - No guest memory is allocated or executable instructions emitted here.
//

//! Frame-relative guest word reservations; not an executable Malbolge image.

use std::collections::{BTreeMap, BTreeSet};

use super::TypedCfgAdapterError;
use super::phi_edge_transfers::PhiEdgeTransfers;
use super::ternary::TernaryCfgScalarKind;
use super::typed::{Function, Instruction, Module, TypeDef, TypeId};

/// Number of distinct words in the admitted current 15-trit profile.
pub const CURRENT_WORD_COUNT: u32 = 14_348_907;

/// One value's disjoint, frame-relative storage interval.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestStorageValue {
    /// Offset in target words from a future linker-assigned frame base.
    pub offset: u32,
    /// The admitted typed scalar category.
    pub type_kind: TernaryCfgScalarKind,
    /// Canonical function-local SSA identity.
    pub value: u32,
    /// One word for Boolean/byte; two for a full C32 scalar.
    pub words: u32,
}

/// One complete future data frame with a disjoint phi snapshot bank.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestStateFrame {
    /// Canonical function identity.
    pub function: u32,
    /// The first offset not owned by any SSA value.
    pub scratch_offset: u32,
    /// Maximal phi-edge source footprint, for lossless parallel copies.
    pub scratch_words: u32,
    /// Frame-relative total (not an absolute Malbolge address).
    pub total_words: u32,
    /// Distinct SSA value reservations in canonical definition order.
    pub values: Vec<GuestStorageValue>,
}

/// One frame-relative, single-cell copy to be realized in guest instructions.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestCellCopy {
    /// Cell that will receive the source's exact 15-trit word.
    pub destination: u32,
    /// Cell to read before writing the destination.
    pub source: u32,
}

/// One reached edge's lossless two-phase phi copies.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestCellEdge {
    /// Copy all scratch words into destinations after the complete snapshot.
    pub commits: Vec<GuestCellCopy>,
    /// Canonical function identity.
    pub function: u32,
    /// Predecessor block identity.
    pub predecessor: u32,
    /// Copy every source into disjoint scratch before modifying any phi
    /// result.
    pub snapshots: Vec<GuestCellCopy>,
    /// Successor block identity.
    pub successor: u32,
}

/// Split an exact C32 bit pattern into two current-profile 15-trit words.
/// The high word is restricted to the unused upper six trits of the C32 value.
#[must_use]
pub fn encode_i32_cells(bits: u32) -> [u32; 2] {
    [
        bits.checked_rem(CURRENT_WORD_COUNT).unwrap_or_default(),
        bits.checked_div(CURRENT_WORD_COUNT).unwrap_or_default(),
    ]
}

/// Decode only the canonical 32-bit subset of two 15-trit guest words.
/// Return `None` for malformed cells or values outside the C32 domain.
#[must_use]
pub fn decode_i32_cells(cells: [u32; 2]) -> Option<u32> {
    if cells.iter().any(|word| *word >= CURRENT_WORD_COUNT) {
        return None;
    }
    let bits = u64::from(cells[1])
        .checked_mul(u64::from(CURRENT_WORD_COUNT))?
        .checked_add(u64::from(cells[0]))?;
    u32::try_from(bits).ok()
}

#[derive(Clone, Copy)]
struct ScalarLayout {
    kind: TernaryCfgScalarKind,
    words: u32,
}

fn scalar_layout(
    module: &Module,
    id: TypeId,
) -> Result<ScalarLayout, TypedCfgAdapterError> {
    let definition = module
        .types()
        .iter()
        .find(|entry| entry.id() == id)
        .map(super::typed::TypeEntry::definition);
    let (words, kind) = match definition {
        Some(TypeDef::Bool) => (1, TernaryCfgScalarKind::Bool),
        Some(TypeDef::I32) => (2, TernaryCfgScalarKind::I32),
        Some(TypeDef::U32) => (2, TernaryCfgScalarKind::U32),
        Some(TypeDef::U8) => (1, TernaryCfgScalarKind::U8),
        _ => return Err(TypedCfgAdapterError::UnsupportedTypedIr),
    };
    Ok(ScalarLayout { kind, words })
}

struct FrameBuilder<'a> {
    module: &'a Module,
    values: Vec<GuestStorageValue>,
    seen: BTreeSet<u32>,
    offset: u32,
}

impl FrameBuilder<'_> {
    fn reserve(
        &mut self,
        result: u32,
        type_id: TypeId,
    ) -> Result<(), TypedCfgAdapterError> {
        if !self.seen.insert(result) {
            return Err(TypedCfgAdapterError::GuestStateAllocation);
        }
        let layout = scalar_layout(self.module, type_id)?;
        let next = self
            .offset
            .checked_add(layout.words)
            .filter(|next| *next <= CURRENT_WORD_COUNT)
            .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
        self.values.push(GuestStorageValue {
            offset: self.offset,
            type_kind: layout.kind,
            value: result,
            words: layout.words,
        });
        self.offset = next;
        Ok(())
    }
}

fn instruction_definition(
    instruction: &Instruction,
) -> Result<Option<(u32, TypeId)>, TypedCfgAdapterError> {
    let (result, type_id) = match instruction {
        Instruction::Binary { result, type_id, .. }
        | Instruction::ByteInput { result, type_id }
        | Instruction::Getchar { result, type_id }
        | Instruction::Cast { result, type_id, .. }
        | Instruction::Compare { result, type_id, .. }
        | Instruction::ConstantInteger { result, type_id, .. } => {
            (result.value(), *type_id)
        },
        Instruction::ByteOutput { .. } => return Ok(None),
        Instruction::AddressOffset { .. }
        | Instruction::AutomaticAllocate { .. }
        | Instruction::Call { .. }
        | Instruction::FunctionAddress { .. }
        | Instruction::Load { .. }
        | Instruction::Store { .. } => {
            return Err(TypedCfgAdapterError::UnsupportedTypedIr);
        },
    };
    Ok(Some((result, type_id)))
}

fn reserve_function_values<'a>(
    module: &'a Module,
    function: &Function,
) -> Result<FrameBuilder<'a>, TypedCfgAdapterError> {
    let mut builder = FrameBuilder {
        module,
        values: Vec::new(),
        seen: BTreeSet::new(),
        offset: 0,
    };
    for block in function.blocks() {
        for phi in block.phis() {
            builder.reserve(phi.result().value(), phi.type_id())?;
        }
        for located in block.instructions() {
            if let Some((result, type_id)) =
                instruction_definition(located.instruction())?
            {
                builder.reserve(result, type_id)?;
            }
        }
    }
    Ok(builder)
}

fn phi_scratch_words(
    function: &Function,
    edges: &[PhiEdgeTransfers],
    values: &[GuestStorageValue],
) -> Result<u32, TypedCfgAdapterError> {
    let mut max_words = 0u32;
    for edge in edges
        .iter()
        .filter(|edge| edge.function == function.id().value())
    {
        let mut needed = 0u32;
        for assignment in &edge.simultaneous {
            let result = values
                .iter()
                .find(|slot| slot.value == assignment.result)
                .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
            let source = values
                .iter()
                .find(|slot| slot.value == assignment.source)
                .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
            if result.words != source.words
                || result.type_kind != assignment.type_kind
                || source.type_kind != assignment.type_kind
            {
                return Err(TypedCfgAdapterError::GuestStateAllocation);
            }
            needed = needed
                .checked_add(result.words)
                .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
        }
        max_words = max_words.max(needed);
    }
    Ok(max_words)
}

/// Reserve disjoint frame-relative 15-trit words for every SSA definition.
/// Dynamic CFG admission has already rejected pointers, globals and calls.
pub(super) fn plan_frame(
    module: &Module,
    function: &Function,
    edges: &[PhiEdgeTransfers],
) -> Result<GuestStateFrame, TypedCfgAdapterError> {
    let builder = reserve_function_values(module, function)?;
    let scratch_words = phi_scratch_words(function, edges, &builder.values)?;
    let total_words = builder
        .offset
        .checked_add(scratch_words)
        .filter(|total| *total <= CURRENT_WORD_COUNT)
        .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
    Ok(GuestStateFrame {
        function: function.id().value(),
        scratch_offset: builder.offset,
        scratch_words,
        total_words,
        values: builder.values,
    })
}

/// Schedule one fully validated parallel phi edge as two disjoint passes.
///
/// # Errors
///
/// Refuses unknown or mistyped slots, duplicate destinations, overlaps and
/// scratch overflow. Never chooses an input-derived successor on the host.
fn validated_slots(
    frame: &GuestStateFrame,
) -> Result<BTreeMap<u32, &GuestStorageValue>, TypedCfgAdapterError> {
    if frame.scratch_offset.checked_add(frame.scratch_words)
        != Some(frame.total_words)
        || frame.total_words > CURRENT_WORD_COUNT
    {
        return Err(TypedCfgAdapterError::GuestStateAllocation);
    }
    let mut intervals = frame.values.iter().collect::<Vec<_>>();
    intervals.sort_unstable_by_key(|slot| slot.offset);
    let mut next = 0u32;
    for slot in intervals {
        let expected = match slot.type_kind {
            TernaryCfgScalarKind::Bool | TernaryCfgScalarKind::U8 => 1,
            TernaryCfgScalarKind::I32 | TernaryCfgScalarKind::U32 => 2,
        };
        if slot.offset != next || slot.words != expected {
            return Err(TypedCfgAdapterError::GuestStateAllocation);
        }
        next = next
            .checked_add(slot.words)
            .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
    }
    if next != frame.scratch_offset {
        return Err(TypedCfgAdapterError::GuestStateAllocation);
    }
    let slots = frame
        .values
        .iter()
        .map(|slot| (slot.value, slot))
        .collect::<BTreeMap<_, _>>();
    if slots.len() != frame.values.len() {
        return Err(TypedCfgAdapterError::GuestStateAllocation);
    }
    Ok(slots)
}

fn snapshot_assignment(
    frame: &GuestStateFrame,
    source: &GuestStorageValue,
    destination: &GuestStorageValue,
    scratch: u32,
    snapshots: &mut Vec<GuestCellCopy>,
    commits: &mut Vec<GuestCellCopy>,
) -> Result<u32, TypedCfgAdapterError> {
    let next = scratch
        .checked_add(source.words)
        .filter(|value| *value <= frame.total_words)
        .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
    for word in 0..source.words {
        let from = source
            .offset
            .checked_add(word)
            .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
        let to = destination
            .offset
            .checked_add(word)
            .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
        let temp = scratch
            .checked_add(word)
            .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
        if from >= frame.scratch_offset
            || to >= frame.scratch_offset
            || temp >= frame.total_words
        {
            return Err(TypedCfgAdapterError::GuestStateAllocation);
        }
        snapshots.push(GuestCellCopy {
            destination: temp,
            source: from,
        });
        commits.push(GuestCellCopy {
            destination: to,
            source: temp,
        });
    }
    Ok(next)
}

/// Schedule all phi sources into scratch, then copy to destinations.
///
/// # Errors
///
/// Rejects malformed frames, missing value slots, mismatched types, duplicate
/// destination identities, and insufficient scratch; emits no guest code.
pub fn plan_cell_edge(
    frame: &GuestStateFrame,
    edge: &PhiEdgeTransfers,
) -> Result<GuestCellEdge, TypedCfgAdapterError> {
    if frame.function != edge.function {
        return Err(TypedCfgAdapterError::GuestStateAllocation);
    }
    // Validate every public interval before assigning any cell copy.
    let slots = validated_slots(frame)?;
    let mut snapshots = Vec::new();
    let mut commits = Vec::new();
    let mut scratch = frame.scratch_offset;
    let mut written = BTreeSet::new();
    for assignment in &edge.simultaneous {
        let source = slots
            .get(&assignment.source)
            .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
        let destination = slots
            .get(&assignment.result)
            .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
        if !written.insert(assignment.result)
            || source.words != destination.words
            || source.type_kind != assignment.type_kind
            || destination.type_kind != assignment.type_kind
        {
            return Err(TypedCfgAdapterError::GuestStateAllocation);
        }
        scratch = snapshot_assignment(
            frame,
            source,
            destination,
            scratch,
            &mut snapshots,
            &mut commits,
        )?;
    }
    Ok(GuestCellEdge {
        commits,
        function: edge.function,
        predecessor: edge.predecessor,
        snapshots,
        successor: edge.successor,
    })
}

/// An optional absolute reservation after an independent code-size witness.
/// This does not allocate physical guest memory or initialize the cells.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestFramePlacement {
    /// Proposed first guest-memory word reserved for this frame.
    pub base: u32,
    /// First word beyond the reservation; no modulo wrap is allowed.
    pub end_exclusive: u32,
    /// Full source-code length against which nonaliasing is checked.
    pub source_cells: u32,
}

/// Verify a proposed N15 frame range is disjoint from the entire source.
///
/// This requires the *final* encoded source length, not a provisional opcode
/// count. No guest word is written or read by this check.
///
/// # Errors
///
/// Refuses invalid graphical-source lengths, incomplete frames, intersecting
/// code/data ranges, end-of-memory overflow and any wraparound.
pub fn validate_frame_placement(
    frame: &GuestStateFrame,
    source_cells: u32,
    base: u32,
) -> Result<GuestFramePlacement, TypedCfgAdapterError> {
    let _validated = validated_slots(frame)?;
    if source_cells < 2
        || source_cells >= CURRENT_WORD_COUNT
        || base < source_cells
    {
        return Err(TypedCfgAdapterError::GuestStateAllocation);
    }
    let end_exclusive = base
        .checked_add(frame.total_words)
        .filter(|end| *end <= CURRENT_WORD_COUNT)
        .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
    Ok(GuestFramePlacement {
        base,
        end_exclusive,
        source_cells,
    })
}

/// Safely relocate a frame-relative cell with a validated absolute reservation.
///
/// # Errors
///
/// Refuses any cell outside the actual reservation; no modulo wrap or
/// presumed guest code/data alias is allowed.
pub fn placed_cell(
    placement: GuestFramePlacement,
    frame: &GuestStateFrame,
    relative: u32,
) -> Result<u32, TypedCfgAdapterError> {
    let _validated = validated_slots(frame)?;
    if relative >= frame.total_words
        || Some(placement.end_exclusive)
            != placement.base.checked_add(frame.total_words)
        || placement.source_cells < 2
        || placement.base < placement.source_cells
        || placement.end_exclusive > CURRENT_WORD_COUNT
    {
        return Err(TypedCfgAdapterError::GuestStateAllocation);
    }
    placement
        .base
        .checked_add(relative)
        .filter(|address| *address < placement.end_exclusive)
        .ok_or(TypedCfgAdapterError::GuestStateAllocation)
}
