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
    GuestCodeInputAnchor, GuestCodeInputSemantics, GuestCodeOperationEffect,
    GuestPlacedOperand, plan_source_locked_cfg_with_input_anchors,
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
    /// The same source input site executed more than once in this prefix.
    RepeatedSourceInput,
    /// Physical input order contradicts source order within one basic block.
    SourceInputOutOfOrder,
    /// Source-input path search exhausted its finite state budget.
    SourceInputSearchLimit,
    /// No source CFG walk can produce the observed input-site prefix.
    SourceInputUnreachable,
    /// Physical execution did not terminate within the declared ceiling.
    StepBudgetExhausted,
    /// An executed input instruction had no authenticated source input site.
    UnexpectedGuestInput,
    /// Physical execution terminated without the source-required halt.
    UnexpectedGuestTermination,
    /// Some source-locked input site was not executed in the guest prefix.
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

/// An input-only physical-prefix witness, never complete C translation proof.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceInputPrefixProof {
    /// Number of actual bytes consumed; EOF reads do not advance this.
    pub bytes_consumed: usize,
    /// Physical VM output, which need not match the source-C program.
    pub guest_output: Vec<u8>,
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
    operation: usize,
}

type KnownSourceOperator = fn(u32, u32) -> u32;
type KnownSourceScalar = (u32, Option<u32>);
type SourceInputSites = BTreeMap<u32, SourceInputSite>;

fn authenticate_input_sites(
    probe: SourceInputProbe<'_>,
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
    let plan = plan_source_locked_cfg_with_input_anchors(
        probe.canonical,
        source_cells,
        probe.frame_base,
        probe.anchors,
    )
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
    if observations
        .iter()
        .any(|entry| entry.code_address == address)
    {
        return Err(SourceInputTraceError::RepeatedSourceInput);
    }
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

// The input-only witness may span several source blocks, whose control flow
// has not yet been linked. Within *one* basic block, however, source input
// effects have an unambiguous instruction order: a guest prefix that reads a
// later source ordinal before an earlier one cannot implement that block.
// Function identity is required because block IDs are function-local.
fn verify_same_block_input_order(
    observations: &[SourceInputSiteObservation],
) -> Result<(), SourceInputTraceError> {
    let mut last_by_block = BTreeMap::new();
    for observation in observations {
        let key = (observation.function, observation.block);
        if last_by_block
            .get(&key)
            .is_some_and(|&previous| previous >= observation.ordinal)
        {
            return Err(SourceInputTraceError::SourceInputOutOfOrder);
        }
        let _previous = last_by_block.insert(key, observation.ordinal);
    }
    Ok(())
}

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
        operation: 0,
    })
}

fn advance_source_input_operation(
    current: &SourceInputWalkState,
    operation: &TernaryOperation,
    observations: &[&SourceInputSiteObservation],
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
        next.consumed = next.consumed.saturating_add(1);
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
    let mut pending = VecDeque::from([SourceInputWalkState {
        block: function.entry,
        consumed: 0,
        known: BTreeMap::new(),
        operation: 0,
    }]);
    let mut visited = BTreeSet::new();
    while let Some(state) = pending.pop_front() {
        if state.consumed == observations.len() {
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
            if let Some(next) =
                advance_source_input_operation(&state, operation, observations)
            {
                pending.push_back(next);
            }
        } else {
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

/// Execute a physical program and prove its source-typed input steps.
///
/// Each source input site must be observed exactly once with no extra reads.
/// Input order must follow a source-CFG path; branches are constrained only
/// where source constants and observed input make their conditions known.
/// Guest branch targets and source arithmetic remain unverified.
/// Loops and repeated input require a later full control-flow verifier.
/// This result proves no C23 stores, normalization, branch or arithmetic and
/// does not discharge any source-C output or artifact-publication obligation.
///
/// # Errors
///
/// Refuses malformed source, invalid anchors, missing/repeated/extra input,
/// incorrect raw input state, VM failures and non-halt termination.
pub fn verify_source_input_site_prefix(
    probe: SourceInputProbe<'_>,
) -> Result<SourceInputPrefixProof, SourceInputTraceError> {
    let sites = authenticate_input_sites(probe)?;
    let mut machine = ProfileMachine::from_source(
        current_profile(),
        probe.physical_source,
        probe.input.to_vec(),
    )
    .map_err(|_error| SourceInputTraceError::InvalidGuestExecution)?;
    let mut observations = Vec::new();
    let mut failed = None;
    let mut trace_index = 0usize;
    let outcome = machine
        .run_traced(probe.step_budget, &mut |step| {
            let current = trace_index;
            trace_index = trace_index.saturating_add(1);
            if failed.is_none()
                && let Err(error) =
                    observe_input_step(step, current, &sites, &mut observations)
            {
                failed = Some(error);
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
    if observations.len() != sites.len() {
        return Err(SourceInputTraceError::UnreachedSourceInput);
    }
    verify_same_block_input_order(&observations)?;
    verify_source_cfg_input_order(probe.canonical, &observations)?;
    Ok(SourceInputPrefixProof {
        bytes_consumed: machine.input_consumed(),
        guest_output: machine.output().to_vec(),
        observations,
        outcome,
    })
}

#[cfg(test)]
mod tests {
    use malbolge::TraceInput;

    use super::super::typed_cfg_adapter::ternary::TernaryCfgScalarKind;
    use super::{
        GuestCodeInputSemantics, GuestPlacedOperand,
        SourceInputSiteObservation, SourceInputTraceError,
        verify_same_block_input_order,
    };

    // These are source-linked observation records, not a surrogate guest
    // execution. Independent VM tests cover actual physical input effects.
    fn observed(
        function: u32,
        block: u32,
        ordinal: u32,
    ) -> SourceInputSiteObservation {
        SourceInputSiteObservation {
            block,
            code_address: ordinal.saturating_add(37),
            destination: GuestPlacedOperand {
                address: ordinal.saturating_add(128),
                type_kind: TernaryCfgScalarKind::U8,
                value: ordinal,
                words: 1,
            },
            function,
            input: TraceInput::Byte(3),
            ordinal,
            raw_accumulator: 3,
            semantics: GuestCodeInputSemantics::ByteU8,
            trace_index: usize::try_from(ordinal).unwrap_or_default(),
        }
    }

    #[test]
    fn input_order_requires_source_order_within_each_function_block() {
        let first = observed(0, 0, 0);
        let second = observed(0, 0, 1);
        assert_eq!(verify_same_block_input_order(&[first, second]), Ok(()));
        assert_eq!(
            verify_same_block_input_order(&[second, first]),
            Err(SourceInputTraceError::SourceInputOutOfOrder),
        );
        assert_eq!(
            verify_same_block_input_order(&[first, first]),
            Err(SourceInputTraceError::SourceInputOutOfOrder),
        );
        // Different control blocks and distinct functions have independent
        // source-local ordinals. Their order needs a full CFG verifier.
        assert_eq!(
            verify_same_block_input_order(&[
                second,
                observed(0, 1, 0),
                observed(1, 0, 0),
            ]),
            Ok(()),
        );
    }
}

#[cfg(test)]
#[path = "../../../../tests/compiler/source_input_cfg_order.rs"]
mod source_input_cfg_order_tests;
