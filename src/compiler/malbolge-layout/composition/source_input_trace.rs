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
    GuestCodeInputAnchor, GuestCodeInputSemantics, GuestCodeOperationAnchor,
    GuestCodeOperationEffect, GuestCodeProposals, GuestPlacedOperand,
    bind_source_locked_cfg_code_targets_with_operation_anchors,
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
    /// Physical execution terminated without the source-required halt.
    UnexpectedGuestTermination,
    /// A skipped source input site is mandatory on every possible return path.
    UnreachedSourceInput,
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

/// An input-only physical-prefix witness, never complete C translation proof.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceInputPrefixProof {
    /// Number of actual bytes consumed; EOF reads do not advance this.
    pub bytes_consumed: usize,
    /// Physical VM output, which need not match the source-C program.
    pub guest_output: Vec<u8>,
    /// Real VM input/output effects in their actual execution order.
    pub io_events: Vec<SourceInputIoEvent>,
    /// Input effects in guest execution order, not host CFG path selection.
    pub observations: Vec<SourceInputSiteObservation>,
    /// Actual bounded physical VM termination.
    pub outcome: RunOutcome,
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
    consumed: usize,
    known: BTreeMap<u32, u32>,
    io_count: usize,
    operation: usize,
    output_count: usize,
}

type KnownSourceOperator = fn(u32, u32) -> u32;
type KnownSourceScalar = (u32, Option<u32>);
type SourceInputSites = BTreeMap<u32, SourceInputSite>;
type ExplicitOperationPlacement<'source> = (
    GuestCodeProposals<'source>,
    &'source [GuestCodeOperationAnchor],
);

fn authenticate_input_sites(
    probe: SourceInputProbe<'_>,
    explicit: Option<ExplicitOperationPlacement<'_>>,
) -> Result<SourceInputSites, SourceInputTraceError> {
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
    let plan = if let Some((proposals, anchors)) = explicit {
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
        bind_source_locked_cfg_code_targets_with_operation_anchors(
            probe.canonical,
            source_cells,
            probe.frame_base,
            proposals,
            anchors,
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
    for effect_site in plan.operation_effect_sites {
        if let GuestCodeOperationEffect::Input { destination, semantics } =
            effect_site.effect
            && sites
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
    Ok(sites)
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
fn known_source_cast(
    operation: &TernaryOperation,
    known: &BTreeMap<u32, u32>,
) -> Option<KnownSourceScalar> {
    if let TernaryOperation::MaterializeI32 { result, scalar, .. }
    | TernaryOperation::MaterializeU32 { result, scalar, .. } = *operation
    {
        Some((result, Some(scalar.bits())))
    } else if let TernaryOperation::MaterializeBool { result, value, .. } =
        *operation
    {
        Some((result, Some(u32::from(value))))
    } else if let TernaryOperation::BitcastI32ToI32 { result, value, .. }
    | TernaryOperation::BitcastI32ToU32 { result, value, .. }
    | TernaryOperation::BitcastU32ToI32 { result, value, .. }
    | TernaryOperation::BitcastU32ToU32 { result, value, .. }
    | TernaryOperation::BoolToI32 { result, value, .. }
    | TernaryOperation::ZeroExtendU8ToU32 {
        result, value, ..
    } = *operation
    {
        Some((result, known.get(&value).copied()))
    } else if let TernaryOperation::TruncateI32ToU8 { result, value, .. }
    | TernaryOperation::TruncateU32ToU8 { result, value, .. } =
        *operation
    {
        Some((result, known.get(&value).map(|bits| bits & 0xff)))
    } else if let TernaryOperation::U8ToBool { result, value, .. }
    | TernaryOperation::I32ToBool { result, value, .. }
    | TernaryOperation::U32ToBool { result, value, .. } = *operation
    {
        Some((result, known.get(&value).map(|bits| u32::from(*bits != 0))))
    } else {
        None
    }
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
        } else if let TernaryOperation::AddU32 { left, result, right, .. } =
            *operation
        {
            (
                result,
                apply_known_binary(known, left, right, u32::wrapping_add),
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

fn advance_known_source_scalar(
    operation: &TernaryOperation,
    known: &mut BTreeMap<u32, u32>,
) {
    // Only total, exact C operations can make a guard source-known.
    // Unmodeled arithmetic retains unknown values, not host-computed output.
    let Some((result, derived)) = known_source_cast(operation, known)
        .or_else(|| known_source_binary(operation, known))
        .or_else(|| known_source_threshold(operation, known))
    else {
        return;
    };
    if let Some(derived_value) = derived {
        let _old = known.insert(result, derived_value);
    } else {
        let _old = known.remove(&result);
    }
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
    })
}

fn advance_source_input_operation(
    current: &SourceInputWalkState,
    operation: &TernaryOperation,
    observations: &[&SourceInputSiteObservation],
    expected_output: Option<&[u8]>,
    expected_io: Option<&[SourceInputIoEvent]>,
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
        if let Some(events) = expected_io {
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
        if let Some(expected) = expected_output {
            // The canonical ByteOutput operand is typed u8. Refuse
            // unknown/mismatched source values; never infer guest output
            // from an unmodeled operation or from the physical VM's A.
            let byte = u8::try_from(*next.known.get(&value)?).ok()?;
            if expected.get(next.output_count) != Some(&byte) {
                return None;
            }
            if let Some(events) = expected_io {
                if events.get(next.io_count)
                    != Some(&SourceInputIoEvent::Output(byte))
                {
                    return None;
                }
                next.io_count = next.io_count.saturating_add(1);
            }
            next.output_count = next.output_count.saturating_add(1);
        }
    } else {
        advance_known_source_scalar(operation, &mut next.known);
    }
    Some(next)
}

fn source_terminator_successors(
    function: &TernaryCfgFunction,
    current: &SourceInputWalkState,
    terminator: TernaryCfgTerminator,
) -> Vec<SourceInputWalkState> {
    let targets = match terminator {
        TernaryCfgTerminator::Branch {
            condition,
            false_target,
            true_target,
            ..
        } => match current.known.get(&condition) {
            Some(0) => vec![false_target],
            Some(_) => vec![true_target],
            None => vec![false_target, true_target],
        },
        TernaryCfgTerminator::Jump { target, .. } => vec![target],
        TernaryCfgTerminator::Return(_) => Vec::new(),
    };
    targets
        .into_iter()
        .filter_map(|target| source_successor_state(function, current, target))
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
    )
}

fn source_path_matches_input_walk(
    function: &TernaryCfgFunction,
    observations: &[&SourceInputSiteObservation],
    max_states: usize,
    require_return: bool,
    expected_output: Option<&[u8]>,
    expected_io: Option<&[SourceInputIoEvent]>,
) -> Result<bool, SourceInputTraceError> {
    let mut pending = VecDeque::from([SourceInputWalkState {
        block: function.entry,
        consumed: 0,
        known: BTreeMap::new(),
        io_count: 0,
        operation: 0,
        output_count: 0,
    }]);
    let mut visited = BTreeSet::new();
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
                expected_output,
                expected_io,
            ) {
                pending.push_back(next);
            }
        } else {
            if matches!(block.terminator, TernaryCfgTerminator::Return(_))
                && state.consumed == observations.len()
                && expected_output
                    .is_none_or(|bytes| state.output_count == bytes.len())
                && expected_io
                    .is_none_or(|events| state.io_count == events.len())
            {
                return Ok(true);
            }
            pending.extend(source_terminator_successors(
                function,
                &state,
                block.terminator,
            ));
        }
    }
    Ok(false)
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
    verify_source_input_site_trace(probe, false, None)
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
        verify_source_input_site_trace(self, false, Some((proposals, anchors)))
    }

    /// Require a complete source return and matching source-known output
    /// after the physically reached, explicitly placed guest input sites.
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
            Some((proposals, anchors)),
        )?;
        verify_source_output_path(self, proof)
    }
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
    verify_source_input_site_trace(probe, true, None)
}

/// Require the physical guest's complete I/O effect order and output bytes
/// to agree with one source-known CFG path after the observed input reads.
///
/// The input/return checker runs first against the actual normative VM. Only
/// exact source-known constants, casts, unsigned wrapping addition/subtraction,
/// comparisons, bitwise operations and parallel phi assignments can justify
/// output here. Unknown byte scalars fail closed; no host-produced checksum
/// is substituted for a guest output, and output-before-read is not accepted
/// as output-after-read. This is a necessary finite I/O check,
/// *not* target arithmetic, state writes, jump or full C translation proof.
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
    )? {
        return Err(SourceInputTraceError::SourceOutputNotProven);
    }
    Ok(proof)
}

fn verify_source_input_site_trace(
    probe: SourceInputProbe<'_>,
    require_source_return: bool,
    explicit: Option<ExplicitOperationPlacement<'_>>,
) -> Result<SourceInputPrefixProof, SourceInputTraceError> {
    let sites = authenticate_input_sites(probe, explicit)?;
    let mut machine = ProfileMachine::from_source(
        current_profile(),
        probe.physical_source,
        probe.input.to_vec(),
    )
    .map_err(|_error| SourceInputTraceError::InvalidGuestExecution)?;
    let mut observations = Vec::new();
    let mut io_events = Vec::new();
    let mut failed = None;
    let mut trace_index = 0usize;
    let outcome = machine
        .run_traced(probe.step_budget, &mut |step| {
            let current = trace_index;
            trace_index = trace_index.saturating_add(1);
            if failed.is_none() {
                if step.input.is_some() && step.output.is_some() {
                    failed = Some(SourceInputTraceError::InvalidGuestExecution);
                } else if let Err(error) =
                    observe_input_step(step, current, &sites, &mut observations)
                {
                    failed = Some(error);
                } else if step.input.is_some() {
                    if let Ok(observation_index) =
                        u16::try_from(observations.len().saturating_sub(1))
                    {
                        io_events.push(SourceInputIoEvent::Input {
                            observation_index,
                        });
                    } else {
                        failed = Some(SourceInputTraceError::InvalidProbeBound);
                    }
                } else if let Some(byte) = step.output {
                    io_events.push(SourceInputIoEvent::Output(byte));
                }
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
        || sites.keys().any(|address| {
            !observations
                .iter()
                .any(|entry| entry.code_address == *address)
        })
    {
        verify_source_return_input_path(
            probe.canonical,
            &sites,
            &observations,
        )?;
    }
    Ok(SourceInputPrefixProof {
        bytes_consumed: machine.input_consumed(),
        guest_output: machine.output().to_vec(),
        io_events,
        observations,
        outcome,
    })
}

#[cfg(test)]
#[path = "../../../../tests/compiler/source_input_cfg_order.rs"]
mod source_input_cfg_order_tests;
