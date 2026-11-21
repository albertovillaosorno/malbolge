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

// This is a necessary, branch-insensitive source control-flow check. Unlike
// source-order sorting, it refuses a physical input site reached before a
// mandatory source read or after an impossible predecessor transition. It
// neither proves which branch condition held nor that guest jumps match CFG.
// A walk stops immediately after the last observed read, so this remains a
// prefix check: following source effects and repeated loop reads are outside
// the present physical verifier's claims.
fn source_path_matches_input_prefix(
    function: &TernaryCfgFunction,
    observations: &[&SourceInputSiteObservation],
) -> bool {
    let mut pending = VecDeque::from([(function.entry, 0usize, 0usize)]);
    let mut visited = BTreeSet::new();
    while let Some((block_id, operation, consumed)) = pending.pop_front() {
        if consumed == observations.len() {
            return true;
        }
        if !visited.insert((block_id, operation, consumed)) {
            continue;
        }
        let Some(block) = usize::try_from(block_id)
            .ok()
            .and_then(|index| function.blocks.get(index))
            .filter(|block| block.id == block_id)
        else {
            return false;
        };
        if let Some(source_operation) = block.operations.get(operation) {
            let is_input = matches!(
                source_operation,
                TernaryOperation::ByteInput { .. }
                    | TernaryOperation::GetcharI32 { .. }
            );
            if !is_input
                || observations.get(consumed).is_some_and(|observed| {
                    observed.block == block_id
                        && usize::try_from(observed.ordinal).ok()
                            == Some(operation)
                })
            {
                pending.push_back((
                    block_id,
                    operation.saturating_add(1),
                    consumed.saturating_add(usize::from(is_input)),
                ));
            }
            continue;
        }
        match block.terminator {
            TernaryCfgTerminator::Branch {
                false_target,
                true_target,
                ..
            } => {
                pending.push_back((false_target, 0, consumed));
                pending.push_back((true_target, 0, consumed));
            },
            TernaryCfgTerminator::Jump { target, .. } => {
                pending.push_back((target, 0, consumed));
            },
            TernaryCfgTerminator::Return(_) => {},
        }
    }
    false
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
            if !source_path_matches_input_prefix(function, &observed) {
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
/// Inputs belonging to the same source function/block must occur in original
/// operation order. Cross-block CFG edges remain unverified by this prefix.
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
