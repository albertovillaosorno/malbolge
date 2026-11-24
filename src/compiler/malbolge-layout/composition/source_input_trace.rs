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
//   - Normative VM evidence for source-typed physical input code sites.
// - Must-Not:
//   - Assert C23 conversion, frame stores, phi copies, branch parity or publish
//     executable C from an input-only trace.
// - Allows:
//   - Inputs: source-authenticated typed IR, proposed input addresses, actual
//     graphical target source, finite byte stream and strict VM step ceiling.
//   - Outputs: reached input steps and their exact raw guest accumulator words.
//   - Side effects: isolated current-profile VM execution only.
// - Split-When:
//   - A full translation validator verifies every source operation and edge.
// - Merge-When:
//   - The source-linked guest backend supplies complete VM trace certificates.
// - Summary:
//   - Proves real / operations occurred at the source-locked candidate sites.

//! Source-locked input-site evidence from the actual current-profile VM.
//!
//! This verifies only physical input opcodes and their raw accumulator results.
//! In particular a reached C23 getchar site still owes its two-word signed
//! normalization and all following source operations. The candidate code is
//! never published or considered to implement its source CFG.

use std::collections::{BTreeMap, BTreeSet, VecDeque};

use malbolge::{
    ProfileMachine, ProfileStepTrace, RunOutcome, Termination, TraceInput,
    current_profile,
};

use super::typed_cfg_adapter::lower_canonical_dynamic_cfg;
use super::typed_cfg_adapter::state_relocation::{
    GuestCodeEffectAnchor, GuestCodeInputAnchor, GuestCodeInputSemantics,
    GuestCodeOperationAnchor, GuestCodeOperationEffect, GuestCodeProposals,
    GuestPlacedOperand,
    bind_source_locked_cfg_code_targets_with_effect_anchors,
    plan_source_locked_cfg_with_input_anchors,
};
use super::typed_cfg_adapter::state_storage::encode_i32_cells;
use super::typed_cfg_adapter::ternary::{
    TernaryCfgFunction, TernaryCfgTerminator, TernaryOperation,
};

/// Physical probe code is intentionally small and entirely graphical.
pub const MAX_SOURCE_INPUT_TRACE_CELLS: usize = 4096;
/// Finite physical prefix ceiling; this is not an unbounded C execution gate.
pub const MAX_SOURCE_INPUT_TRACE_STEPS: usize = 512;
const MAX_SOURCE_INPUT_CFG_SEARCH_STATES: usize = 16_384;

/// A failure to associate a real input transition with authenticated source.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SourceInputTraceError {
    /// Current-profile VM refused to load or execute this physical program.
    InvalidGuestExecution,
    /// Real transition does not carry the expected signed/raw input word.
    InvalidInputTransition,
    /// Invalid/too-large source or input, or zero/excessive step budget.
    InvalidProbeBound,
    /// Canonical typed source, frame or anchored interval was rejected.
    InvalidSourcePlacement,
    /// A source input effect is not assigned exactly one distinct code site.
    MissingSourceAnchor,
    /// Source-input path search exhausted its finite state budget.
    SourceInputSearchLimit,
    /// No source CFG walk can produce the observed input-site prefix.
    SourceInputUnreachable,
    /// No fully source-known output path matches the real guest bytes.
    SourceOutputNotProven,
    /// A reached input never received all real data writes for its source SSA.
    MissingInputResultStore,
    /// Guest data writes did not reproduce the full C23 or byte input value.
    InputResultMismatch,
    /// Matching stores have no guest data or control dependence on the input.
    InputResultUnrelatedToInput,
    /// Physical execution did not terminate within the declared ceiling.
    StepBudgetExhausted,
    /// An executed input instruction had no authenticated source input site.
    UnexpectedGuestInput,
    /// A physical output opcode was not at a source-placed output effect.
    UnexpectedGuestOutput,
    /// Real input-dependent frame write ran at the wrong source effect site.
    UnexpectedGuestStoreSite,
    /// Guest made extra/missing writes, even at an authorized source site.
    UnattributedGuestStore,
    /// Physical execution terminated without the source-required halt.
    UnexpectedGuestTermination,
    /// A skipped source input site is mandatory on every possible return path.
    UnreachedSourceInput,
    /// Requested source branch is not a unique bound conditional/landing.
    InvalidBranchBinding,
    /// Real guest landing disagrees with a source-known branch direction.
    SourceBranchMismatch,
}

/// An actual input step and its *raw* profile accumulator, before C23 casting.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourceInputSiteObservation {
    /// Authenticated source block that owns this proposed read.
    pub block: u32,
    /// Physical code address executed by the normative VM.
    pub code_address: u32,
    /// Source SSA destination that still needs signed/byte guest stores.
    pub destination: GuestPlacedOperand,
    /// Canonical function identity (block IDs are function-local).
    pub function: u32,
    /// Actual byte or true EOF selected by the guest.
    pub input: TraceInput,
    /// Source operation index within its block.
    pub ordinal: u32,
    /// Physical VM accumulator after the input instruction.
    pub raw_accumulator: u32,
    /// Target interpretation still required after this raw read.
    pub semantics: GuestCodeInputSemantics,
    /// Zero-based normative VM trace index, including any jumps.
    pub trace_index: usize,
}

/// One actual I/O event in the physical VM's trace order.
///
/// Input indexes refer to [`SourceInputPrefixProof::observations`] and
/// therefore retain real input bytes, source code addresses and step indices.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SourceInputIoEvent {
    /// A verified source-anchored physical input instruction.
    Input {
        /// Index of the corresponding observed physical source read.
        observation_index: u16,
    },
    /// A real output instruction emitted one byte.
    Output(u8),
}

/// One reached output's source-authenticated physical effect identity.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourceOutputSiteObservation {
    /// Canonical source block containing the output operation.
    pub block: u32,
    /// Normative VM's actual emitted byte.
    pub byte: u8,
    /// Exact physical code cell of the reached output instruction.
    pub code_address: u32,
    /// Canonical source function containing the output operation.
    pub function: u32,
    /// Source operation ordinal within its block.
    pub ordinal: u32,
    /// Normative VM step at which this output occurred.
    pub trace_index: usize,
}

/// An input-only physical-prefix witness, never complete C translation proof.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceInputPrefixProof {
    /// Number of actual bytes consumed; EOF reads do not advance this.
    pub bytes_consumed: usize,
    /// Physical VM output, which need not match the source-C program.
    pub guest_output: Vec<u8>,
    /// Real VM input/output effects in their actual execution order.
    pub io_events: Vec<SourceInputIoEvent>,
    /// Reached output sites when explicit source effect anchors were required.
    /// Empty for an unanchored probe or a guest with no output.
    pub output_sites: Vec<SourceOutputSiteObservation>,
    /// Input effects in guest execution order, not host CFG path selection.
    pub observations: Vec<SourceInputSiteObservation>,
    /// Actual bounded physical VM termination.
    pub outcome: RunOutcome,
}

/// One exact source conditional is bound to a physical guest indirect arm.
///
/// `after_inputs` is the number of observed source input operations before
/// this branch (possibly zero), distinguishing source loop iterations.
/// A source-unknown condition cannot authenticate a guest destination.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourceBranchLanding {
    /// Number of reached input observations before the branch.
    pub after_inputs: usize,
    /// Canonical source basic block containing the conditional terminator.
    pub block: u32,
    /// Physical destination for the source false successor.
    pub false_landing: u32,
    /// Canonical function containing the conditional terminator.
    pub function: u32,
    /// Physical destination for the source true successor.
    pub true_landing: u32,
}

/// Source-locked C23 input sites and physical execution input for one probe.
#[derive(Clone, Copy, Debug)]
pub struct SourceInputProbe<'source> {
    /// All source-typed input effects must be anchored exactly once.
    pub anchors: &'source [GuestCodeInputAnchor],
    /// Canonical MCTI source-locked compiler representation.
    pub canonical: &'source [u8],
    /// Guest state frame, disjoint from code and valid in the N15 domain.
    pub frame_base: u32,
    /// Actual binary stream supplied to the normative VM.
    pub input: &'source [u8],
    /// Physical, printable Malbolge source bytes.
    pub physical_source: &'source [u8],
    /// Positive finite guest instruction ceiling, at most 512.
    pub step_budget: usize,
}

#[derive(Clone, Copy)]
struct SourceOutputSite {
    block: u32,
    function: u32,
    ordinal: u32,
}

#[derive(Clone, Copy)]
struct SourceInputSite {
    block: u32,
    destination: GuestPlacedOperand,
    function: u32,
    ordinal: u32,
    semantics: GuestCodeInputSemantics,
}

// Only source-known scalar values may constrain branch reachability. Unknown
// arithmetic or data never selects a branch; this is an independent source
// path check, not target execution or guest branch/control verification.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
struct SourceInputWalkState {
    block: u32,
    // None: target branch not reached; Some(false): not source-proven.
    branch_match: Option<bool>,
    consumed: usize,
    io_count: usize,
    known: BTreeMap<u32, u32>,
    operation: usize,
    output_count: usize,
}

impl SourceInputWalkState {
    fn entry(block: u32) -> Self {
        Self {
            block,
            branch_match: None,
            consumed: 0,
            io_count: 0,
            known: BTreeMap::new(),
            operation: 0,
            output_count: 0,
        }
    }
}

#[derive(Clone, Copy)]
struct SourceBranchObligation {
    after_inputs: usize,
    io_before_transfer: Option<usize>,
    block: u32,
    expected_true: bool,
}

type KnownSourceOperator = fn(u32, u32) -> u32;
type KnownSignedSourceOperator = fn(i32, i32) -> Option<i32>;
type KnownSourceScalar = (u32, Option<u32>);
type SourceInputSites = BTreeMap<u32, SourceInputSite>;

/// Source-placed input and output code effects, never complete VM operations.
struct SourceIoSites {
    inputs: SourceInputSites,
    outputs: BTreeMap<u32, SourceOutputSite>,
}
#[derive(Clone, Copy)]
struct SourceOutputExpectations<'expected> {
    expected_output: Option<&'expected [u8]>,
    expected_io: Option<&'expected [SourceInputIoEvent]>,
    expected_sites: Option<&'expected [SourceOutputSiteObservation]>,
    function: u32,
}

type ExplicitOperationPlacement<'source> = (
    GuestCodeProposals<'source>,
    &'source [GuestCodeOperationAnchor],
    &'source [GuestCodeEffectAnchor],
);

fn authenticate_io_sites(
    probe: SourceInputProbe<'_>,
    explicit: Option<ExplicitOperationPlacement<'_>>,
) -> Result<SourceIoSites, SourceInputTraceError> {
    if probe.physical_source.len() < 2
        || probe.physical_source.len() > MAX_SOURCE_INPUT_TRACE_CELLS
        || !probe
            .physical_source
            .iter()
            .all(|byte| (33..=126).contains(byte))
        || probe.step_budget == 0
        || probe.step_budget > MAX_SOURCE_INPUT_TRACE_STEPS
        || probe.input.len() > MAX_SOURCE_INPUT_TRACE_STEPS
    {
        return Err(SourceInputTraceError::InvalidProbeBound);
    }
    let source_cells = u32::try_from(probe.physical_source.len())
        .map_err(|_error| SourceInputTraceError::InvalidProbeBound)?;
    let plan = if let Some((proposals, anchors, effect_anchors)) = explicit {
        if probe.anchors.iter().any(|read| {
            !anchors.iter().any(|anchor| {
                (
                    anchor.function,
                    anchor.block,
                    anchor.ordinal,
                    anchor.code_address,
                ) == (
                    read.function,
                    read.block,
                    read.ordinal,
                    read.code_address,
                )
            })
        }) {
            return Err(SourceInputTraceError::InvalidSourcePlacement);
        }
        bind_source_locked_cfg_code_targets_with_effect_anchors(
            probe.canonical,
            source_cells,
            probe.frame_base,
            proposals,
            anchors,
            effect_anchors,
        )
    } else {
        plan_source_locked_cfg_with_input_anchors(
            probe.canonical,
            source_cells,
            probe.frame_base,
            probe.anchors,
        )
    }
    .map_err(|_error| SourceInputTraceError::InvalidSourcePlacement)?;
    let mut sites = SourceInputSites::new();
    let mut outputs = BTreeMap::new();
    for effect_site in plan.operation_effect_sites {
        match effect_site.effect {
            GuestCodeOperationEffect::Output { .. } => {
                if outputs
                    .insert(effect_site.code_address, SourceOutputSite {
                        block: effect_site.block,
                        function: effect_site.function,
                        ordinal: effect_site.ordinal,
                    })
                    .is_some()
                {
                    return Err(SourceInputTraceError::InvalidSourcePlacement);
                }
            },
            GuestCodeOperationEffect::Input { destination, semantics } => {
                if sites
                    .insert(effect_site.code_address, SourceInputSite {
                        block: effect_site.block,
                        destination,
                        function: effect_site.function,
                        ordinal: effect_site.ordinal,
                        semantics,
                    })
                    .is_some()
                {
                    return Err(SourceInputTraceError::MissingSourceAnchor);
                }
            },
            GuestCodeOperationEffect::Store { .. }
            | GuestCodeOperationEffect::Compute => {},
        }
    }

    if sites.is_empty()
        || sites.len() != probe.anchors.len()
        || probe.anchors.iter().any(|anchor| {
            sites.get(&anchor.code_address).is_none_or(|site| {
                (site.function, site.block, site.ordinal)
                    != (anchor.function, anchor.block, anchor.ordinal)
            })
        })
    {
        return Err(SourceInputTraceError::MissingSourceAnchor);
    }
    Ok(SourceIoSites { inputs: sites, outputs })
}

fn observe_input_step(
    step: &ProfileStepTrace,
    trace_index: usize,
    sites: &SourceInputSites,
    observations: &mut Vec<SourceInputSiteObservation>,
) -> Result<(), SourceInputTraceError> {
    let Some(input) = step.input else {
        return Ok(());
    };
    let address = step.before.registers.code_pointer;
    let Some(site) = sites.get(&address).copied() else {
        return Err(SourceInputTraceError::UnexpectedGuestInput);
    };
    let profile = current_profile();
    let raw_accumulator = match input {
        TraceInput::Byte(byte) => u32::from(byte),
        TraceInput::EndOfInput => profile.eof_word(),
    };
    let valid_semantics = match site.semantics {
        GuestCodeInputSemantics::ByteU8 => true,
        GuestCodeInputSemantics::SignedC23 {
            raw_eof_word,
            c23_eof_cells,
        } => {
            raw_eof_word == profile.eof_word()
                && c23_eof_cells == encode_i32_cells(u32::MAX)
        },
    };
    if !valid_semantics
        || step.decoded != Some(profile.input_instruction())
        || step.after.registers.accumulator != raw_accumulator
        || step.result.is_err()
    {
        return Err(SourceInputTraceError::InvalidInputTransition);
    }
    observations.push(SourceInputSiteObservation {
        block: site.block,
        code_address: address,
        destination: site.destination,
        function: site.function,
        input,
        ordinal: site.ordinal,
        raw_accumulator,
        semantics: site.semantics,
        trace_index,
    });
    Ok(())
}

// Input order, including revisits to the same source block, is checked by
// the authenticated source-CFG walk below. A block-local ordinal check cannot
// distinguish a legal loop backedge from an impossible in-block reorder.
// Actual reads are still associated with their unique physical code anchors.

// Exact source scalar facts constrain only feasible input paths, never guest
// arithmetic or emitted bytes. Unknown operations do not select a branch.
// Preserve exact signed source representations. Narrow signed values are
// stored as their original bit patterns; widening sign-extends *that* width.
// The 32-bit result is a source fact, not a guest computation.
const fn source_sign_extend(bits: u32, width: u32) -> u32 {
    let shift = 32u32.saturating_sub(width);
    bits.wrapping_shl(shift)
        .cast_signed()
        .wrapping_shr(shift)
        .cast_unsigned()
}

fn known_source_materialize(
    operation: &TernaryOperation,
) -> Option<KnownSourceScalar> {
    if let TernaryOperation::MaterializeI32 { result, scalar, .. }
    | TernaryOperation::MaterializeU32 { result, scalar, .. } = *operation
    {
        Some((result, Some(scalar.bits())))
    } else if let TernaryOperation::MaterializeI16 { result, scalar, .. }
    | TernaryOperation::MaterializeU16 { result, scalar, .. } =
        *operation
    {
        Some((result, Some(u32::from(scalar.bits()))))
    } else if let TernaryOperation::MaterializeI8 { result, scalar, .. }
    | TernaryOperation::MaterializeU8 { result, scalar, .. } =
        *operation
    {
        Some((result, Some(u32::from(scalar.bits()))))
    } else if let TernaryOperation::MaterializeBool { result, value, .. } =
        *operation
    {
        Some((result, Some(u32::from(value))))
    } else {
        None
    }
}

fn known_source_same_bits(
    operation: &TernaryOperation,
    known: &BTreeMap<u32, u32>,
) -> Option<KnownSourceScalar> {
    if let TernaryOperation::BitcastI8ToI8 { result, value, .. }
    | TernaryOperation::BitcastI8ToU8 { result, value, .. }
    | TernaryOperation::BitcastU8ToI8 { result, value, .. }
    | TernaryOperation::BitcastU8ToU8 { result, value, .. }
    | TernaryOperation::BitcastI16ToI16 { result, value, .. }
    | TernaryOperation::BitcastI16ToU16 { result, value, .. }
    | TernaryOperation::BitcastU16ToI16 { result, value, .. }
    | TernaryOperation::BitcastU16ToU16 { result, value, .. }
    | TernaryOperation::BitcastI32ToI32 { result, value, .. }
    | TernaryOperation::BitcastI32ToU32 { result, value, .. }
    | TernaryOperation::BitcastU32ToI32 { result, value, .. }
    | TernaryOperation::BitcastU32ToU32 { result, value, .. }
    | TernaryOperation::BoolToI8 { result, value, .. }
    | TernaryOperation::BoolToI16 { result, value, .. }
    | TernaryOperation::BoolToI32 { result, value, .. }
    | TernaryOperation::ZeroExtendU8ToU16 { result, value, .. }
    | TernaryOperation::ZeroExtendU8ToU32 { result, value, .. }
    | TernaryOperation::ZeroExtendU16ToU32 { result, value, .. } = *operation
    {
        Some((result, known.get(&value).copied()))
    } else {
        None
    }
}

fn known_source_truncate(
    operation: &TernaryOperation,
    known: &BTreeMap<u32, u32>,
) -> Option<KnownSourceScalar> {
    if let TernaryOperation::TruncateI16ToI8 { result, value, .. }
    | TernaryOperation::TruncateI16ToU8 { result, value, .. }
    | TernaryOperation::TruncateI32ToI8 { result, value, .. }
    | TernaryOperation::TruncateI32ToU8 { result, value, .. }
    | TernaryOperation::TruncateU16ToI8 { result, value, .. }
    | TernaryOperation::TruncateU16ToU8 { result, value, .. }
    | TernaryOperation::TruncateU32ToI8 { result, value, .. }
    | TernaryOperation::TruncateU32ToU8 { result, value, .. } = *operation
    {
        Some((result, known.get(&value).map(|bits| bits & 0xff)))
    } else if let TernaryOperation::TruncateI32ToI16 { result, value, .. }
    | TernaryOperation::TruncateI32ToU16 { result, value, .. }
    | TernaryOperation::TruncateU32ToI16 { result, value, .. }
    | TernaryOperation::TruncateU32ToU16 { result, value, .. } =
        *operation
    {
        Some((result, known.get(&value).map(|bits| bits & 0xffff)))
    } else {
        None
    }
}

fn known_source_sign_extend(
    operation: &TernaryOperation,
    known: &BTreeMap<u32, u32>,
) -> Option<KnownSourceScalar> {
    if let TernaryOperation::SignExtendI8ToI16 { result, value, .. } =
        *operation
    {
        Some((
            result,
            known
                .get(&value)
                .map(|bits| source_sign_extend(*bits, 8) & 0xffff),
        ))
    } else if let TernaryOperation::SignExtendI8ToI32 {
        result, value, ..
    } = *operation
    {
        Some((
            result,
            known.get(&value).map(|bits| source_sign_extend(*bits, 8)),
        ))
    } else if let TernaryOperation::SignExtendI16ToI32 {
        result, value, ..
    } = *operation
    {
        Some((
            result,
            known.get(&value).map(|bits| source_sign_extend(*bits, 16)),
        ))
    } else {
        None
    }
}

fn known_source_nonzero(
    operation: &TernaryOperation,
    known: &BTreeMap<u32, u32>,
) -> Option<KnownSourceScalar> {
    if let TernaryOperation::I8ToBool { result, value, .. }
    | TernaryOperation::I16ToBool { result, value, .. }
    | TernaryOperation::I32ToBool { result, value, .. }
    | TernaryOperation::U8ToBool { result, value, .. }
    | TernaryOperation::U16ToBool { result, value, .. }
    | TernaryOperation::U32ToBool { result, value, .. } = *operation
    {
        Some((result, known.get(&value).map(|bits| u32::from(*bits != 0))))
    } else {
        None
    }
}

fn known_source_cast(
    operation: &TernaryOperation,
    known: &BTreeMap<u32, u32>,
) -> Option<KnownSourceScalar> {
    known_source_materialize(operation)
        .or_else(|| known_source_same_bits(operation, known))
        .or_else(|| known_source_truncate(operation, known))
        .or_else(|| known_source_sign_extend(operation, known))
        .or_else(|| known_source_nonzero(operation, known))
}

fn apply_known_binary(
    known: &BTreeMap<u32, u32>,
    left: u32,
    right: u32,
    apply: KnownSourceOperator,
) -> Option<u32> {
    known
        .get(&left)
        .zip(known.get(&right))
        .map(|(lhs, rhs)| apply(*lhs, *rhs))
}

fn apply_known_signed_binary(
    known: &BTreeMap<u32, u32>,
    left: u32,
    right: u32,
    apply: KnownSignedSourceOperator,
) -> Option<u32> {
    known
        .get(&left)
        .zip(known.get(&right))
        .and_then(|(lhs, rhs)| {
            let lhs = i32::from_ne_bytes(lhs.to_ne_bytes());
            let rhs = i32::from_ne_bytes(rhs.to_ne_bytes());
            apply(lhs, rhs).map(|value| u32::from_ne_bytes(value.to_ne_bytes()))
        })
}

fn known_source_binary(
    operation: &TernaryOperation,
    known: &BTreeMap<u32, u32>,
) -> Option<KnownSourceScalar> {
    let (result, derived) =
        if let TernaryOperation::EqualI32 { left, result, right, .. }
        | TernaryOperation::EqualU32 { left, result, right, .. } = *operation
        {
            (
                result,
                apply_known_binary(known, left, right, |lhs, rhs| {
                    u32::from(lhs == rhs)
                }),
            )
        } else if let TernaryOperation::NotEqualI32 {
            left,
            result,
            right,
            ..
        }
        | TernaryOperation::NotEqualU32 {
            left,
            result,
            right,
            ..
        } = *operation
        {
            (
                result,
                apply_known_binary(known, left, right, |lhs, rhs| {
                    u32::from(lhs != rhs)
                }),
            )
        } else if let TernaryOperation::AddI32 { left, result, right, .. } =
            *operation
        {
            (
                result,
                apply_known_signed_binary(known, left, right, i32::checked_add),
            )
        } else if let TernaryOperation::AddU32 { left, result, right, .. } =
            *operation
        {
            (
                result,
                apply_known_binary(known, left, right, u32::wrapping_add),
            )
        } else if let TernaryOperation::SubtractI32 {
            left,
            result,
            right,
            ..
        } = *operation
        {
            (
                result,
                apply_known_signed_binary(known, left, right, i32::checked_sub),
            )
        } else if let TernaryOperation::SubtractU32 {
            left,
            result,
            right,
            ..
        } = *operation
        {
            (
                result,
                apply_known_binary(known, left, right, u32::wrapping_sub),
            )
        } else if let TernaryOperation::MultiplyI32 {
            left,
            result,
            right,
            ..
        } = *operation
        {
            (
                result,
                apply_known_signed_binary(known, left, right, i32::checked_mul),
            )
        } else if let TernaryOperation::MultiplyU32 {
            left,
            result,
            right,
            ..
        } = *operation
        {
            (
                result,
                apply_known_binary(known, left, right, u32::wrapping_mul),
            )
        } else if let TernaryOperation::DivideI32 {
            left, result, right, ..
        } = *operation
        {
            (
                result,
                apply_known_signed_binary(known, left, right, i32::checked_div),
            )
        } else if let TernaryOperation::DivideU32 {
            left, result, right, ..
        } = *operation
        {
            (
                result,
                known
                    .get(&left)
                    .zip(known.get(&right))
                    .and_then(|(lhs, rhs)| lhs.checked_div(*rhs)),
            )
        } else if let TernaryOperation::RemainderI32 {
            left,
            result,
            right,
            ..
        } = *operation
        {
            (
                result,
                apply_known_signed_binary(known, left, right, i32::checked_rem),
            )
        } else if let TernaryOperation::RemainderU32 {
            left,
            result,
            right,
            ..
        } = *operation
        {
            (
                result,
                known
                    .get(&left)
                    .zip(known.get(&right))
                    .and_then(|(lhs, rhs)| lhs.checked_rem(*rhs)),
            )
        } else if let TernaryOperation::AndI32 { left, result, right, .. }
        | TernaryOperation::AndU32 { left, result, right, .. } =
            *operation
        {
            (
                result,
                apply_known_binary(known, left, right, |lhs, rhs| lhs & rhs),
            )
        } else if let TernaryOperation::OrI32 { left, result, right, .. }
        | TernaryOperation::OrU32 { left, result, right, .. } =
            *operation
        {
            (
                result,
                apply_known_binary(known, left, right, |lhs, rhs| lhs | rhs),
            )
        } else if let TernaryOperation::XorI32 { left, result, right, .. }
        | TernaryOperation::XorU32 { left, result, right, .. } =
            *operation
        {
            (
                result,
                apply_known_binary(known, left, right, |lhs, rhs| lhs ^ rhs),
            )
        } else {
            return None;
        };
    Some((result, derived))
}

// A checked binary result of `None` is source-unknown when an operand is
// unknown, but is *undefined* when all required operands are known and the
// checked C23 operation fails. Division by a known zero is undefined even
// if the dividend has not yet become source-known.
fn source_binary_is_undefined(
    operation: &TernaryOperation,
    known: &BTreeMap<u32, u32>,
    derived: Option<u32>,
) -> bool {
    let (left, right, division) = match *operation {
        TernaryOperation::AddI32 { left, right, .. }
        | TernaryOperation::SubtractI32 { left, right, .. }
        | TernaryOperation::MultiplyI32 { left, right, .. } => {
            (left, right, false)
        },
        TernaryOperation::DivideI32 { left, right, .. }
        | TernaryOperation::DivideU32 { left, right, .. }
        | TernaryOperation::RemainderI32 { left, right, .. }
        | TernaryOperation::RemainderU32 { left, right, .. } => {
            (left, right, true)
        },
        _ => return false,
    };
    (division && known.get(&right) == Some(&0))
        || (derived.is_none()
            && known.contains_key(&left)
            && known.contains_key(&right))
}

// Source-only knowledge must never turn C shift UB or a platform-specific
// signed right shift into a made-up guest output or a definite branch arm.
fn known_signed_left_shift(left: i32, count: u32) -> Option<i32> {
    (count < 32u32).then_some(())?;
    (left >= 0i32)
        .then_some(())
        .and_then(|()| i64::from(left).checked_shl(count))
        .and_then(|bits| i32::try_from(bits).ok())
}

fn known_signed_right_shift(left: i32, count: u32) -> Option<i32> {
    (left >= 0i32).then_some(())?;
    left.checked_shr(count)
}

// `None` means that an operation is not a shift. Within a recognized shift,
// `Ok(None)` means insufficient source knowledge (or implementation-defined
// signed-right behavior). `Err(())` means the reached C23 shift is undefined
// and therefore cannot certify *any* complete source return, even if its
// resulting SSA value is never used by a later byte effect.
fn known_source_shift(
    operation: &TernaryOperation,
    known: &BTreeMap<u32, u32>,
) -> Option<(u32, Result<Option<u32>, ()>)> {
    let (left, result, right) = match *operation {
        TernaryOperation::ShiftLeftU32 { left, result, right, .. }
        | TernaryOperation::ShiftRightLogicalU32 {
            left, result, right, ..
        }
        | TernaryOperation::ShiftLeftI32 { left, result, right, .. }
        | TernaryOperation::ShiftRightArithmeticI32 {
            left,
            result,
            right,
            ..
        } => (left, result, right),
        _ => return None,
    };
    let left_bits = known.get(&left).copied();
    let count = known.get(&right).copied();
    // C shifts with negative counts or counts >= the promoted operand width
    // are undefined, independently of whether the left operand is known.
    if count.is_some_and(|value| value >= 32) {
        return Some((result, Err(())));
    }
    let derived = match *operation {
        TernaryOperation::ShiftLeftU32 { .. } => {
            Ok(left_bits.zip(count).map(|(lhs, rhs)| lhs << rhs))
        },
        TernaryOperation::ShiftRightLogicalU32 { .. } => {
            Ok(left_bits.zip(count).map(|(lhs, rhs)| lhs >> rhs))
        },
        TernaryOperation::ShiftLeftI32 { .. } => {
            let signed =
                left_bits.map(|bits| i32::from_ne_bytes(bits.to_ne_bytes()));
            if signed.is_some_and(|value| value < 0) {
                Err(())
            } else if let Some((lhs, rhs)) = signed.zip(count) {
                known_signed_left_shift(lhs, rhs)
                    .map(|value| u32::from_ne_bytes(value.to_ne_bytes()))
                    .map(Some)
                    .ok_or(())
            } else {
                Ok(None)
            }
        },
        TernaryOperation::ShiftRightArithmeticI32 { .. } => {
            let signed =
                left_bits.map(|bits| i32::from_ne_bytes(bits.to_ne_bytes()));
            Ok(signed.zip(count).and_then(|(lhs, rhs)| {
                known_signed_right_shift(lhs, rhs)
                    .map(|value| u32::from_ne_bytes(value.to_ne_bytes()))
            }))
        },
        _ => unreachable!("recognized shift variant"),
    };
    Some((result, derived))
}

fn known_source_threshold(
    operation: &TernaryOperation,
    known: &BTreeMap<u32, u32>,
) -> Option<KnownSourceScalar> {
    let (result, derived) = if let TernaryOperation::LessUnsignedU32 {
        left,
        result,
        right,
        ..
    } = *operation
    {
        (
            result,
            apply_known_binary(known, left, right, |lhs, rhs| {
                u32::from(lhs < rhs)
            }),
        )
    } else if let TernaryOperation::LessUnsignedEqualU32 {
        left,
        result,
        right,
        ..
    } = *operation
    {
        (
            result,
            apply_known_binary(known, left, right, |lhs, rhs| {
                u32::from(lhs <= rhs)
            }),
        )
    } else if let TernaryOperation::LessSignedI32 {
        left, result, right, ..
    } = *operation
    {
        (
            result,
            apply_known_binary(known, left, right, |lhs, rhs| {
                u32::from(
                    i32::from_be_bytes(lhs.to_be_bytes())
                        < i32::from_be_bytes(rhs.to_be_bytes()),
                )
            }),
        )
    } else if let TernaryOperation::LessSignedEqualI32 {
        left,
        result,
        right,
        ..
    } = *operation
    {
        (
            result,
            apply_known_binary(known, left, right, |lhs, rhs| {
                u32::from(
                    i32::from_be_bytes(lhs.to_be_bytes())
                        <= i32::from_be_bytes(rhs.to_be_bytes()),
                )
            }),
        )
    } else {
        return None;
    };
    Some((result, derived))
}

// `false` marks executed undefined C23 arithmetic, not unknown SSA.
// No source return can be certified through such an operation.
fn advance_known_source_scalar(
    operation: &TernaryOperation,
    known: &mut BTreeMap<u32, u32>,
) -> bool {
    let tracked = known_source_cast(operation, known)
        .or_else(|| known_source_binary(operation, known))
        .or_else(|| known_source_threshold(operation, known));
    let (result, derived) = if let Some(scalar) = tracked {
        if source_binary_is_undefined(operation, known, scalar.1) {
            let _old = known.remove(&scalar.0);
            return false;
        }
        scalar
    } else if let Some((result, shifted)) = known_source_shift(operation, known)
    {
        let Ok(derived) = shifted else {
            let _old = known.remove(&result);
            return false;
        };
        (result, derived)
    } else {
        return true;
    };
    if let Some(derived_value) = derived {
        let _old = known.insert(result, derived_value);
    } else {
        let _old = known.remove(&result);
    }
    true
}

fn source_successor_state(
    function: &TernaryCfgFunction,
    current: &SourceInputWalkState,
    target: u32,
) -> Option<SourceInputWalkState> {
    let target_block = usize::try_from(target)
        .ok()
        .and_then(|index| function.blocks.get(index))
        .filter(|block| block.id == target)?;
    let updates = target_block
        .phis
        .iter()
        .map(|phi| {
            let incoming = phi
                .incoming
                .iter()
                .find(|(predecessor, _value)| *predecessor == current.block)?;
            Some((phi.result, current.known.get(&incoming.1).copied()))
        })
        .collect::<Option<Vec<_>>>()?;
    let mut known = current.known.clone();
    for (result, optional_value) in updates {
        if let Some(known_value) = optional_value {
            let _old = known.insert(result, known_value);
        } else {
            let _old = known.remove(&result);
        }
    }
    Some(SourceInputWalkState {
        block: target,
        consumed: current.consumed,
        known,
        io_count: current.io_count,
        operation: 0,
        output_count: current.output_count,
        branch_match: current.branch_match,
    })
}

// Preserve the exact physical output effect's source operation identity.
// Equal bytes from different source operations are not interchangeable.
fn advance_source_output_operation(
    next: &mut SourceInputWalkState,
    current: &SourceInputWalkState,
    value: u32,
    expected: SourceOutputExpectations<'_>,
) -> Option<()> {
    let output = expected.expected_output?;
    // The canonical ByteOutput operand is typed u8. Never infer this byte
    // from an unknown source scalar or from the physical VM accumulator.
    let byte = u8::try_from(*next.known.get(&value)?).ok()?;
    if output.get(next.output_count) != Some(&byte) {
        return None;
    }
    if let Some(events) = expected.expected_io {
        if events.get(next.io_count) != Some(&SourceInputIoEvent::Output(byte))
        {
            return None;
        }
        next.io_count = next.io_count.saturating_add(1);
    }
    if let Some(sites) = expected.expected_sites {
        let site = sites.get(next.output_count)?;
        if (
            site.function,
            site.block,
            usize::try_from(site.ordinal).ok(),
            site.byte,
        ) != (
            expected.function,
            current.block,
            Some(current.operation),
            byte,
        ) {
            return None;
        }
    }
    next.output_count = next.output_count.saturating_add(1);
    Some(())
}

fn advance_source_input_operation(
    current: &SourceInputWalkState,
    operation: &TernaryOperation,
    observations: &[&SourceInputSiteObservation],
    expected: SourceOutputExpectations<'_>,
) -> Option<SourceInputWalkState> {
    let mut next = current.clone();
    next.operation = next.operation.saturating_add(1);
    if let TernaryOperation::GetcharI32 { result, .. }
    | TernaryOperation::ByteInput { result, .. } = *operation
    {
        let observed = observations.get(current.consumed)?;
        if observed.block != current.block
            || usize::try_from(observed.ordinal).ok() != Some(current.operation)
        {
            return None;
        }
        let input_value = match observed.input {
            TraceInput::Byte(byte) => u32::from(byte),
            TraceInput::EndOfInput
                if matches!(operation, TernaryOperation::GetcharI32 { .. }) =>
            {
                u32::MAX
            },
            TraceInput::EndOfInput => return None,
        };
        let _old = next.known.insert(result, input_value);
        if let Some(events) = expected.expected_io {
            if events.get(next.io_count)
                != Some(&SourceInputIoEvent::Input {
                    observation_index: u16::try_from(next.consumed).ok()?,
                })
            {
                return None;
            }
            next.io_count = next.io_count.saturating_add(1);
        }
        next.consumed = next.consumed.saturating_add(1);
    } else if let TernaryOperation::ByteOutput { value, .. } = *operation {
        if expected.expected_output.is_some() {
            advance_source_output_operation(
                &mut next, current, value, expected,
            )?;
        }
    } else if !advance_known_source_scalar(operation, &mut next.known) {
        return None;
    }
    Some(next)
}

// Track one exact source branch occurrence in the same CFG walk that must
// consume the entire physical input trace and reach a source return. A second
// occurrence before a new read is not the nominated single physical transfer.
fn source_terminator_successors(
    function: &TernaryCfgFunction,
    current: &SourceInputWalkState,
    terminator: TernaryCfgTerminator,
    expected_branch: Option<SourceBranchObligation>,
) -> Vec<SourceInputWalkState> {
    let (targets, branch_match) = match terminator {
        TernaryCfgTerminator::Branch {
            condition,
            false_target,
            true_target,
            ..
        } => {
            let truth = current.known.get(&condition).map(|value| *value != 0);
            let targets = match truth {
                Some(false) => vec![false_target],
                Some(true) => vec![true_target],
                None => vec![false_target, true_target],
            };
            let match_result = expected_branch.and_then(|branch| {
                // A source CFG backedge can revisit the same block. Select
                // the exact input occurrence of this physical transfer;
                // neither block identity nor the read count is sufficient.
                let at_source_block = current.block == branch.block;
                let at_input_occurrence =
                    current.consumed == branch.after_inputs;
                (at_source_block && at_input_occurrence).then(|| {
                    current.branch_match.is_none()
                        && truth == Some(branch.expected_true)
                        && branch
                            .io_before_transfer
                            .is_none_or(|count| current.io_count == count)
                })
            });
            (targets, match_result)
        },
        TernaryCfgTerminator::Jump { target, .. } => (vec![target], None),
        TernaryCfgTerminator::Return(_) => (Vec::new(), None),
    };
    targets
        .into_iter()
        .filter_map(|target| {
            let mut next = source_successor_state(function, current, target)?;
            if let Some(matches) = branch_match {
                next.branch_match = Some(matches);
            }
            Some(next)
        })
        .collect()
}

// Source-known conditions constrain only possible input paths. Arithmetic
// not explicitly tracked above is unknown, never evaluated as a host output.
// The walk ends at the final observed read, not at a source-C return. Guest
// jump/branch transitions and all following effects still need verification.
fn source_path_matches_input_prefix(
    function: &TernaryCfgFunction,
    observations: &[&SourceInputSiteObservation],
    max_states: usize,
) -> Result<bool, SourceInputTraceError> {
    source_path_matches_input_trace(function, observations, max_states, false)
}

// Reaching the last physical read proves only a *prefix*. If a candidate
// skips a source input site and then halts, require a source return without
// any additional input operation. Unknown computations can only widen the
// set of possible source paths, never certify guest arithmetic or output.
fn source_path_matches_input_trace(
    function: &TernaryCfgFunction,
    observations: &[&SourceInputSiteObservation],
    max_states: usize,
    require_return: bool,
) -> Result<bool, SourceInputTraceError> {
    source_path_matches_input_walk(
        function,
        observations,
        max_states,
        require_return,
        None,
        None,
        None,
    )
}

// Compare the complete source-input/byte-output effect sequence against one
// caller-supplied finite byte vector. A matching path cannot use unknown
// output scalars; all guest effects still require independent VM evidence.
#[cfg(test)]
fn source_path_matches_input_observables(
    function: &TernaryCfgFunction,
    observations: &[&SourceInputSiteObservation],
    expected_output: &[u8],
    max_states: usize,
) -> Result<bool, SourceInputTraceError> {
    source_path_matches_input_walk(
        function,
        observations,
        max_states,
        true,
        Some(expected_output),
        None,
        None,
    )
}

fn source_path_matches_input_walk(
    function: &TernaryCfgFunction,
    observations: &[&SourceInputSiteObservation],
    max_states: usize,
    require_return: bool,
    expected_output: Option<&[u8]>,
    expected_io: Option<&[SourceInputIoEvent]>,
    expected_sites: Option<&[SourceOutputSiteObservation]>,
) -> Result<bool, SourceInputTraceError> {
    source_path_matches_input_walk_with_branch(
        function,
        observations,
        max_states,
        require_return,
        expected_output,
        expected_io,
        expected_sites,
        None,
    )
}

#[expect(
    clippy::too_many_arguments,
    reason = "finite source path includes separate I/O and branch obligations"
)]
fn source_path_matches_input_walk_with_branch(
    function: &TernaryCfgFunction,
    observations: &[&SourceInputSiteObservation],
    max_states: usize,
    require_return: bool,
    expected_output: Option<&[u8]>,
    expected_io: Option<&[SourceInputIoEvent]>,
    expected_sites: Option<&[SourceOutputSiteObservation]>,
    expected_branch: Option<SourceBranchObligation>,
) -> Result<bool, SourceInputTraceError> {
    let mut pending =
        VecDeque::from([SourceInputWalkState::entry(function.entry)]);
    let mut visited = BTreeSet::new();
    let mut matching_return = false;
    let mut incompatible_return = false;
    while let Some(state) = pending.pop_front() {
        if !require_return && state.consumed == observations.len() {
            return Ok(true);
        }
        if visited.len() >= max_states {
            return Err(SourceInputTraceError::SourceInputSearchLimit);
        }
        if !visited.insert(state.clone()) {
            continue;
        }
        let Some(block) = usize::try_from(state.block)
            .ok()
            .and_then(|index| function.blocks.get(index))
            .filter(|block| block.id == state.block)
        else {
            return Ok(false);
        };
        if let Some(operation) = block.operations.get(state.operation) {
            if let Some(next) = advance_source_input_operation(
                &state,
                operation,
                observations,
                SourceOutputExpectations {
                    expected_output,
                    expected_io,
                    expected_sites,
                    function: function.id,
                },
            ) {
                pending.push_back(next);
            }
        } else {
            let completed_return =
                matches!(block.terminator, TernaryCfgTerminator::Return(_))
                    && state.consumed == observations.len()
                    && expected_output
                        .is_none_or(|bytes| state.output_count == bytes.len())
                    && expected_io
                        .is_none_or(|events| state.io_count == events.len());
            if completed_return && expected_branch.is_none() {
                return Ok(true);
            }
            if completed_return {
                matching_return |= state.branch_match == Some(true);
                incompatible_return |= state.branch_match != Some(true);
            }
            pending.extend(source_terminator_successors(
                function,
                &state,
                block.terminator,
                expected_branch,
            ));
        }
    }
    Ok(expected_branch.is_some() && matching_return && !incompatible_return)
}

// Re-derive the exact C conditional from the canonical typed IR. Accept a
// physical landing only when every complete input-compatible source return
// reaches the nominated branch once with a known, agreeing truth value.
// This is source/guest control parity for one finite arm, not guest C storage,
// predicate computation, or an executable source backedge.
pub(super) fn verify_source_branch_landing(
    canonical: &[u8],
    observations: &[SourceInputSiteObservation],
    binding: SourceBranchLanding,
    physical_landing: u32,
) -> Result<(), SourceInputTraceError> {
    verify_source_branch_landing_with_io(
        canonical,
        SourceBranchInputEvidence {
            observations,
            receipt: None,
            io_before_transfer: None,
        },
        binding,
        physical_landing,
    )
}

// A source return that independently proves a branch and an output is not
// enough: the two witnesses must agree on one *same* path, including I/O
// order. Unknown source outputs or paths with conflicting arm choices refuse.
pub(super) fn verify_source_branch_io_landing(
    canonical: &[u8],
    proof: &SourceInputPrefixProof,
    binding: SourceBranchLanding,
    physical_landing: u32,
    io_before_transfer: usize,
) -> Result<(), SourceInputTraceError> {
    verify_source_branch_landing_with_io(
        canonical,
        SourceBranchInputEvidence {
            observations: &proof.observations,
            receipt: Some(proof),
            io_before_transfer: Some(io_before_transfer),
        },
        binding,
        physical_landing,
    )
}

// Keep the complete VM receipt attached to the observations it authenticates;
// source-only branch callers intentionally leave I/O obligations absent.
struct SourceBranchInputEvidence<'source> {
    observations: &'source [SourceInputSiteObservation],
    receipt: Option<&'source SourceInputPrefixProof>,
    io_before_transfer: Option<usize>,
}

fn verify_source_branch_landing_with_io(
    canonical: &[u8],
    evidence: SourceBranchInputEvidence<'_>,
    binding: SourceBranchLanding,
    physical_landing: u32,
) -> Result<(), SourceInputTraceError> {
    let SourceBranchInputEvidence {
        observations,
        receipt,
        io_before_transfer,
    } = evidence;
    use SourceInputTraceError::{
        InvalidBranchBinding, InvalidSourcePlacement, SourceBranchMismatch,
    };
    if binding.after_inputs > observations.len()
        || binding.false_landing == binding.true_landing
    {
        return Err(InvalidBranchBinding);
    }
    let expected_true = if physical_landing == binding.false_landing {
        false
    } else if physical_landing == binding.true_landing {
        true
    } else {
        return Err(SourceBranchMismatch);
    };
    let cfg = lower_canonical_dynamic_cfg(canonical)
        .map_err(|_error| InvalidSourcePlacement)?;
    let function = cfg
        .functions
        .iter()
        .find(|candidate| candidate.id == binding.function)
        .ok_or(InvalidBranchBinding)?;
    if !function.blocks.iter().any(|block| {
        block.id == binding.block
            && matches!(block.terminator, TernaryCfgTerminator::Branch { .. })
    }) || observations
        .iter()
        .any(|observation| observation.function != binding.function)
    {
        return Err(InvalidBranchBinding);
    }
    let observed = observations.iter().collect::<Vec<_>>();
    if source_path_matches_input_walk_with_branch(
        function,
        &observed,
        MAX_SOURCE_INPUT_CFG_SEARCH_STATES,
        true,
        receipt.map(|receipt| receipt.guest_output.as_slice()),
        receipt.map(|receipt| receipt.io_events.as_slice()),
        receipt.and_then(|receipt| {
            (!receipt.output_sites.is_empty())
                .then_some(receipt.output_sites.as_slice())
        }),
        Some(SourceBranchObligation {
            after_inputs: binding.after_inputs,
            io_before_transfer,
            block: binding.block,
            expected_true,
        }),
    )? {
        Ok(())
    } else if receipt.is_some() {
        Err(SourceInputTraceError::SourceOutputNotProven)
    } else {
        Err(SourceBranchMismatch)
    }
}

fn verify_source_cfg_input_order(
    canonical: &[u8],
    observations: &[SourceInputSiteObservation],
) -> Result<(), SourceInputTraceError> {
    let cfg = lower_canonical_dynamic_cfg(canonical)
        .map_err(|_error| SourceInputTraceError::InvalidSourcePlacement)?;
    let mut found_functions = BTreeSet::new();
    for function in &cfg.functions {
        let observed = observations
            .iter()
            .filter(|observation| observation.function == function.id)
            .collect::<Vec<_>>();
        if !observed.is_empty() {
            let _new = found_functions.insert(function.id);
            if !source_path_matches_input_prefix(
                function,
                &observed,
                MAX_SOURCE_INPUT_CFG_SEARCH_STATES,
            )? {
                return Err(SourceInputTraceError::SourceInputUnreachable);
            }
        }
    }
    if observations
        .iter()
        .any(|observation| !found_functions.contains(&observation.function))
    {
        return Err(SourceInputTraceError::SourceInputUnreachable);
    }
    Ok(())
}

// A conditional source input may be legitimately absent on an early-EOF
// return path, even though every source input operation must be *anchored*.
// Do not relax missing-site refusals for functions without one complete
// source return path matching the entire physical input trace.
fn verify_source_return_input_path(
    canonical: &[u8],
    sites: &SourceInputSites,
    observations: &[SourceInputSiteObservation],
) -> Result<(), SourceInputTraceError> {
    let functions = sites
        .values()
        .map(|site| site.function)
        .collect::<BTreeSet<_>>();
    let function_ids = functions.iter().copied().collect::<Vec<_>>();
    let [function_id] = function_ids.as_slice() else {
        // Interprocedural source execution is not modeled by this checker.
        return Err(SourceInputTraceError::UnreachedSourceInput);
    };
    let cfg = lower_canonical_dynamic_cfg(canonical)
        .map_err(|_error| SourceInputTraceError::InvalidSourcePlacement)?;
    let function = cfg
        .functions
        .iter()
        .find(|function| function.id == *function_id)
        .ok_or(SourceInputTraceError::InvalidSourcePlacement)?;
    let observed = observations.iter().collect::<Vec<_>>();
    if source_path_matches_input_trace(
        function,
        &observed,
        MAX_SOURCE_INPUT_CFG_SEARCH_STATES,
        true,
    )? {
        Ok(())
    } else {
        Err(SourceInputTraceError::UnreachedSourceInput)
    }
}

/// Execute a physical program and prove its source-typed input steps.
///
/// Every source input effect must have an exact physical code anchor, but a
/// source-CFG-valid early return may skip anchored input sites. The same code
/// site may occur repeatedly if its physical instruction really
/// decodes as input again and the authenticated source-CFG walk permits the
/// entire observed sequence. Source-known guards constrain path feasibility.
/// Guest branch targets and source arithmetic remain unverified: even when a
/// loop input prefix matches, its guest control and mutable state do not.
/// This result proves no C23 stores, normalization, branch or arithmetic and
/// does not discharge any source-C output or artifact-publication obligation.
///
/// # Errors
///
/// Refuses malformed source, invalid anchors, missing/extra or source-invalid
/// input, incorrect raw input state, VM failures and non-halt termination.
pub fn verify_source_input_site_prefix(
    probe: SourceInputProbe<'_>,
) -> Result<SourceInputPrefixProof, SourceInputTraceError> {
    verify_source_input_site_trace(probe, false, None, false)
}

impl SourceInputProbe<'_> {
    /// Verify real VM input steps at explicitly positioned source operations.
    ///
    /// Every input anchor must match the first effect of an authenticated
    /// source operation. Checked in-block gaps may contain unverified
    /// pointer/setup instructions; neither those instructions, C23 signed
    /// conversion, later stores nor source CFG branching become proven.
    ///
    /// # Errors
    ///
    /// Refuses contradictory code reservations, missing operation anchors,
    /// and every physical input/source-order violation.
    pub fn verify_with_operation_anchors(
        self,
        proposals: GuestCodeProposals<'_>,
        anchors: &[GuestCodeOperationAnchor],
    ) -> Result<SourceInputPrefixProof, SourceInputTraceError> {
        verify_source_input_site_trace(
            self,
            false,
            Some((proposals, anchors, &[])),
            false,
        )
    }

    /// Require a source CFG return after the explicitly positioned input
    /// effects, without inventing further unread byte/EOF operations.
    ///
    /// # Errors
    ///
    /// Refuses physical input, source placement or return-path mismatches.
    pub fn verify_return_with_operation_anchors(
        self,
        proposals: GuestCodeProposals<'_>,
        anchors: &[GuestCodeOperationAnchor],
    ) -> Result<SourceInputPrefixProof, SourceInputTraceError> {
        verify_source_input_site_trace(
            self,
            true,
            Some((proposals, anchors, &[])),
            false,
        )
    }

    /// Require a source-compatible return after individually anchored
    /// effects. Subsequent guest stores remain unverified by this method.
    ///
    /// # Errors
    ///
    /// Refuses unsupported or reordered effect positions, physical input
    /// mismatches, and source CFG paths without a matching return.
    pub fn verify_return_with_effect_anchors(
        self,
        proposals: GuestCodeProposals<'_>,
        operation_anchors: &[GuestCodeOperationAnchor],
        effect_anchors: &[GuestCodeEffectAnchor],
    ) -> Result<SourceInputPrefixProof, SourceInputTraceError> {
        verify_source_input_site_trace(
            self,
            true,
            Some((proposals, operation_anchors, effect_anchors)),
            false,
        )
    }

    /// Require a complete source return and matching source-known output
    /// after the physically reached, explicitly placed guest input sites.
    /// The reached physical output address must be a source-placed output
    /// effect. This does not prove operand storage or physical control flow.
    /// No unproved source computation or control transition is accepted.
    ///
    /// # Errors
    ///
    /// Refuses physical input, source return or output-order disagreements.
    pub fn verify_output_with_operation_anchors(
        self,
        proposals: GuestCodeProposals<'_>,
        anchors: &[GuestCodeOperationAnchor],
    ) -> Result<SourceInputPrefixProof, SourceInputTraceError> {
        let proof = verify_source_input_site_trace(
            self,
            true,
            Some((proposals, anchors, &[])),
            true,
        )?;
        verify_source_output_path(self, proof)
    }
}

// Preserve both source output/value and exact guest output-site checks
// when the physical state verifier subsequently replays the same program.
// This is still a necessary-condition gate, not full source dataflow.
pub(super) fn verify_source_input_site_output_with_effect_anchors(
    probe: SourceInputProbe<'_>,
    proposals: GuestCodeProposals<'_>,
    operation_anchors: &[GuestCodeOperationAnchor],
    effect_anchors: &[GuestCodeEffectAnchor],
) -> Result<SourceInputPrefixProof, SourceInputTraceError> {
    let proof = verify_source_input_site_trace(
        probe,
        true,
        Some((proposals, operation_anchors, effect_anchors)),
        true,
    )?;
    verify_source_output_path(probe, proof)
}

/// Verify a physically halted guest input trace can reach a return in the
/// authenticated source CFG without any additional source input operation.
///
/// Unlike the input-only prefix verifier, this rejects a halted guest that
/// physically visited every anchored read once but stopped before the source
/// would require a further visit to the same input site on a loop backedge.
/// This is a *necessary* source-path check, not evidence for physical branch
/// targets, guest arithmetic, C32 local writes, output or translated C code.
/// Unknown source calculations remain nondeterministic within the bounded
/// source search; they do not become invented guest predicates.
///
/// # Errors
///
/// Refuses every prefix-verifier error, plus source paths that cannot return
/// after exactly the observed input events. Search exhaustion is distinct
/// from a proven impossible return path.
pub fn verify_source_input_site_return_compatible(
    probe: SourceInputProbe<'_>,
) -> Result<SourceInputPrefixProof, SourceInputTraceError> {
    verify_source_input_site_trace(probe, true, None, false)
}

/// Require the physical guest's complete I/O effect order and output bytes
/// to agree with one source-known CFG path after the observed input reads.
///
/// The input/return checker runs first against the actual normative VM. Only
/// exact source-known constants, casts, unsigned wrapping arithmetic,
/// defined signed arithmetic, checked signed/unsigned division and
/// remainder, defined unsigned shifts, conservatively defined signed shifts,
/// comparisons, bitwise operations and parallel phi assignments can justify
/// output here. Unknown byte scalars fail closed; no host-produced checksum
/// is substituted for a guest output,
/// and output-before-read is not accepted as output-after-read. This is a
/// necessary finite I/O check, *not* target arithmetic, state writes, jump or
/// full C translation proof.
///
/// # Errors
///
/// Refuses a physical/input/return mismatch, interprocedural source calls,
/// an unknown source output value or differing guest output bytes.
pub fn verify_source_input_site_output_compatible(
    probe: SourceInputProbe<'_>,
) -> Result<SourceInputPrefixProof, SourceInputTraceError> {
    let proof = verify_source_input_site_return_compatible(probe)?;
    verify_source_output_path(probe, proof)
}

fn verify_source_output_path(
    probe: SourceInputProbe<'_>,
    proof: SourceInputPrefixProof,
) -> Result<SourceInputPrefixProof, SourceInputTraceError> {
    let function_ids = probe
        .anchors
        .iter()
        .map(|anchor| anchor.function)
        .collect::<BTreeSet<_>>();
    let mut ids = function_ids.iter();
    let Some(function_id) = ids.next().copied() else {
        return Err(SourceInputTraceError::InvalidSourcePlacement);
    };
    if ids.next().is_some() {
        return Err(SourceInputTraceError::SourceOutputNotProven);
    }
    let cfg = lower_canonical_dynamic_cfg(probe.canonical)
        .map_err(|_error| SourceInputTraceError::InvalidSourcePlacement)?;
    let function = cfg
        .functions
        .iter()
        .find(|function| function.id == function_id)
        .ok_or(SourceInputTraceError::InvalidSourcePlacement)?;
    let observed = proof.observations.iter().collect::<Vec<_>>();
    if !source_path_matches_input_walk(
        function,
        &observed,
        MAX_SOURCE_INPUT_CFG_SEARCH_STATES,
        true,
        Some(&proof.guest_output),
        Some(&proof.io_events),
        (!proof.output_sites.is_empty())
            .then_some(proof.output_sites.as_slice()),
    )? {
        return Err(SourceInputTraceError::SourceOutputNotProven);
    }
    Ok(proof)
}

/// Project one reached physical I/O instruction into source-placed events.
/// Raw I/O is observable even when the corresponding SSA result stores are
/// still unproved. The stronger output path can require an addressed source
/// effect instead of relying on matching output bytes alone.
#[expect(
    clippy::too_many_arguments,
    reason = "physical step, source sites and two I/O journals"
)]
fn append_reached_source_io(
    step: &ProfileStepTrace,
    trace_index: usize,
    sites: &SourceIoSites,
    observations: &mut Vec<SourceInputSiteObservation>,
    io_events: &mut Vec<SourceInputIoEvent>,
    output_sites: &mut Vec<SourceOutputSiteObservation>,
    require_output_anchors: bool,
) -> Result<(), SourceInputTraceError> {
    if step.input.is_some() && step.output.is_some() {
        return Err(SourceInputTraceError::InvalidGuestExecution);
    }
    observe_input_step(step, trace_index, &sites.inputs, observations)?;
    if step.input.is_some() {
        let observation_index = observations
            .len()
            .checked_sub(1)
            .and_then(|index| u16::try_from(index).ok())
            .ok_or(SourceInputTraceError::InvalidProbeBound)?;
        io_events.push(SourceInputIoEvent::Input { observation_index });
    } else if let Some(byte) = step.output {
        if require_output_anchors {
            let code_address = step.before.registers.code_pointer;
            let site = sites
                .outputs
                .get(&code_address)
                .ok_or(SourceInputTraceError::UnexpectedGuestOutput)?;
            output_sites.push(SourceOutputSiteObservation {
                block: site.block,
                byte,
                code_address,
                function: site.function,
                ordinal: site.ordinal,
                trace_index,
            });
        }
        io_events.push(SourceInputIoEvent::Output(byte));
    }
    Ok(())
}

fn verify_source_input_site_trace(
    probe: SourceInputProbe<'_>,
    require_source_return: bool,
    explicit: Option<ExplicitOperationPlacement<'_>>,
    require_output_anchors: bool,
) -> Result<SourceInputPrefixProof, SourceInputTraceError> {
    let sites = authenticate_io_sites(probe, explicit)?;
    let mut machine = ProfileMachine::from_source(
        current_profile(),
        probe.physical_source,
        probe.input.to_vec(),
    )
    .map_err(|_error| SourceInputTraceError::InvalidGuestExecution)?;
    let mut observations = Vec::new();
    let mut io_events = Vec::new();
    let mut output_sites = Vec::new();
    let mut failed = None;
    let mut trace_index = 0usize;
    let outcome = machine
        .run_traced(probe.step_budget, &mut |step| {
            let current = trace_index;
            trace_index = trace_index.saturating_add(1);
            if failed.is_none() {
                failed = append_reached_source_io(
                    step,
                    current,
                    &sites,
                    &mut observations,
                    &mut io_events,
                    &mut output_sites,
                    require_output_anchors,
                )
                .err();
            }
        })
        .map_err(|_error| SourceInputTraceError::InvalidGuestExecution)?;
    if let Some(error) = failed {
        return Err(error);
    }
    match outcome {
        RunOutcome::BudgetExhausted { .. } => {
            return Err(SourceInputTraceError::StepBudgetExhausted);
        },
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            ..
        } => {},
        RunOutcome::Terminated { .. } => {
            return Err(SourceInputTraceError::UnexpectedGuestTermination);
        },
    }
    verify_source_cfg_input_order(probe.canonical, &observations)?;
    if require_source_return
        || sites.inputs.keys().any(|address| {
            !observations
                .iter()
                .any(|entry| entry.code_address == *address)
        })
    {
        verify_source_return_input_path(
            probe.canonical,
            &sites.inputs,
            &observations,
        )?;
    }
    Ok(SourceInputPrefixProof {
        bytes_consumed: machine.input_consumed(),
        guest_output: machine.output().to_vec(),
        io_events,
        output_sites,
        observations,
        outcome,
    })
}

#[cfg(test)]
#[path = "../../../../tests/compiler/source_input_cfg_order.rs"]
mod source_input_cfg_order_tests;
