// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Boundary-Contract:
// - Owns:
//   - Source-return I/O and control reservation binding to a paired route.
// - Must-Not:
//   - Authorize source operand stores, arithmetic, phi copies or publication.
// - Allows:
//   - Inputs: opaque paired physical proof and source-locked placement.
//   - Outputs: independently reconciled finite source-return I/O evidence.
//   - Side effects: isolated normative VM replay.
// - Split-When:
//   - Source branch-prefix and complete-return evidence require different APIs.
// - Merge-When:
//   - The whole guest linker can independently reconcile every source effect.
// - Summary:
//   - Authenticates a reached arm without mistaking placement for execution.

//! Necessary source-return evidence for one previously proven physical arm.

use std::slice::Iter;

use super::source_input_trace::{
    verify_source_branch_io_landing,
    verify_source_input_site_output_with_effect_anchors_and_budget,
};
use super::typed_cfg_adapter::state_relocation::{
    GuestCodeEdgeKind, GuestCodeEffectAnchor, GuestCodeOperationAnchor,
    GuestCodeProposals,
    bind_source_locked_cfg_code_targets_with_effect_anchors,
};
use super::{
    AddressSelectedIndirectCaseProof, AddressSelectedIndirectProof,
    SourceBranchLanding, SourceInputIoEvent, SourceInputPrefixProof,
    SourceInputProbe, SourceInputTraceError, SourceOutputSiteObservation,
    SourcePhysicalIoEvent,
};

/// Exact source proposals and one input already covered by a physical pair.
#[derive(Clone, Copy, Debug)]
pub struct AddressSelectedSourceReturnProbe<'source> {
    /// Source conditional and both proposed physical successor entries.
    pub branch: SourceBranchLanding,
    /// Exact source-typed physical effect reservations.
    pub effect_anchors: &'source [GuestCodeEffectAnchor],
    /// Exact source-typed operation reservations.
    pub operation_anchors: &'source [GuestCodeOperationAnchor],
    /// All disjoint source block and phi-pad code proposals.
    pub proposals: GuestCodeProposals<'source>,
    /// Canonical source and the exact graphical source/input for this case.
    pub source_input: SourceInputProbe<'source>,
}

/// Why the necessary source-return join cannot be authenticated.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AddressSelectedSourceReturnError {
    /// The exact source or input was not authenticated by the physical pair.
    CaseNotProven,
    /// Both independent replays did not agree on the reached effects.
    InconsistentReplay,
    /// Source reservations do not bind both physical branch entries.
    InvalidBinding,
    /// Source-locked input/output/branch checking refused.
    SourceInput(SourceInputTraceError),
}

/// Join one verified physical case to its exact source branch and return I/O.
///
/// Independently rederive both source control reservations and every
/// reached input/output effect. Both proposed successors and the shared
/// control instruction must agree with the actual paired physical transfer
/// after the single authenticated input.
/// The source function must have exactly one reserved return, and the
/// selected case must actually halt at its code address.
/// The source-known branch, input count, output values and I/O chronology
/// must occur on one complete compatible source return path. This does not
/// prove the source condition's storage, arithmetic, phi copies, or other
/// source CFG transitions; the other arm need not implement a source return.
///
/// # Errors
/// Refuses an unproven source/input, forged control and effect reservations,
/// inconsistent replay, or unmatched source branch/return/output path.
pub fn verify_address_selected_source_return(
    physical: &AddressSelectedIndirectProof,
    probe: &AddressSelectedSourceReturnProbe<'_>,
) -> Result<SourceInputPrefixProof, AddressSelectedSourceReturnError> {
    use AddressSelectedSourceReturnError as Error;
    if physical.source() != probe.source_input.physical_source {
        return Err(Error::CaseNotProven);
    }
    let case = physical
        .cases()
        .iter()
        .find(|case| case.input() == probe.source_input.input)
        .ok_or(Error::CaseNotProven)?;
    let return_address = verify_branch_reservations(physical, probe)?;
    let receipt =
        verify_source_input_site_output_with_effect_anchors_and_budget(
            probe.source_input,
            probe.proposals,
            probe.operation_anchors,
            probe.effect_anchors,
            physical.budget(),
        )
        .map_err(Error::SourceInput)?;
    if case
        .journal()
        .code_fetches
        .last()
        .map(|fetch| fetch.code_address)
        != Some(return_address)
    {
        return Err(Error::InvalidBinding);
    }
    let io_before_transfer = verify_replayed_io(case, &receipt)?;
    verify_source_branch_io_landing(
        probe.source_input.canonical,
        &receipt,
        probe.branch,
        case.landing_address(),
        io_before_transfer,
    )
    .map_err(Error::SourceInput)?;
    Ok(receipt)
}

fn verify_branch_reservations(
    physical: &AddressSelectedIndirectProof,
    probe: &AddressSelectedSourceReturnProbe<'_>,
) -> Result<u32, AddressSelectedSourceReturnError> {
    use AddressSelectedSourceReturnError as Error;
    let source = probe.source_input;
    let source_cells = u32::try_from(source.physical_source.len())
        .map_err(|_error| Error::InvalidBinding)?;
    let plan = bind_source_locked_cfg_code_targets_with_effect_anchors(
        source.canonical,
        source_cells,
        source.frame_base,
        probe.proposals,
        probe.operation_anchors,
        probe.effect_anchors,
    )
    .map_err(|_error| Error::InvalidBinding)?;
    let [first, second] = physical.cases();
    let branch = probe.branch;
    let actual = [first.landing_address(), second.landing_address()];
    if branch.after_inputs != 1
        || !actual.contains(&branch.false_landing)
        || !actual.contains(&branch.true_landing)
        || branch.false_landing == branch.true_landing
    {
        return Err(Error::InvalidBinding);
    }
    let control = first.transfer().code_address;
    let predecessor = branch.block;
    for (kind, landing) in [
        (GuestCodeEdgeKind::WhenFalse, branch.false_landing),
        (GuestCodeEdgeKind::WhenTrue, branch.true_landing),
    ] {
        if !plan.control_edges.iter().any(|edge| {
            edge.function == branch.function
                && edge.predecessor == predecessor
                && edge.kind == kind
                && edge.control_address == control
                && edge.entry_address == landing
        }) {
            return Err(Error::InvalidBinding);
        }
    }
    let mut returns = plan
        .return_sites
        .iter()
        .filter(|site| site.function == branch.function);
    let site = returns.next().ok_or(Error::InvalidBinding)?;
    if returns.next().is_some() {
        return Err(Error::InvalidBinding);
    }
    Ok(site.address)
}

fn verify_replayed_io(
    case: &AddressSelectedIndirectCaseProof,
    receipt: &SourceInputPrefixProof,
) -> Result<usize, AddressSelectedSourceReturnError> {
    use AddressSelectedSourceReturnError as Error;
    let journal = case.journal();
    if journal.source.outcome != receipt.outcome
        || journal.io_events.len() != receipt.io_events.len()
    {
        return Err(Error::InconsistentReplay);
    }
    let mut outputs = receipt.output_sites.iter();
    let mut before = 0usize;
    for (physical, source) in journal.io_events.iter().zip(&receipt.io_events) {
        let step = verify_io_event(physical, *source, receipt, &mut outputs)?;
        if step < case.transfer().trace_index {
            before = before.saturating_add(1);
        }
    }
    if outputs.next().is_some() {
        return Err(Error::InconsistentReplay);
    }
    Ok(before)
}

fn verify_io_event<'receipt>(
    physical: &SourcePhysicalIoEvent,
    source: SourceInputIoEvent,
    receipt: &'receipt SourceInputPrefixProof,
    outputs: &mut Iter<'receipt, SourceOutputSiteObservation>,
) -> Result<usize, AddressSelectedSourceReturnError> {
    use AddressSelectedSourceReturnError as Error;
    let step = match (physical, source) {
        (
            SourcePhysicalIoEvent::Input {
                code_address,
                raw_word,
                read,
                trace_index,
            },
            SourceInputIoEvent::Input { observation_index },
        ) => {
            let observed = receipt
                .observations
                .get(usize::from(observation_index))
                .ok_or(Error::InconsistentReplay)?;
            if (
                observed.code_address,
                observed.raw_accumulator,
                observed.input,
                observed.trace_index,
            ) != (*code_address, *raw_word, *read, *trace_index)
            {
                return Err(Error::InconsistentReplay);
            }
            *trace_index
        },
        (
            SourcePhysicalIoEvent::Output {
                code_address,
                byte,
                trace_index,
                ..
            },
            SourceInputIoEvent::Output(source_byte),
        ) => {
            let observed = outputs.next().ok_or(Error::InconsistentReplay)?;
            if (observed.code_address, observed.byte, observed.trace_index)
                != (*code_address, *byte, *trace_index)
                || *byte != source_byte
            {
                return Err(Error::InconsistentReplay);
            }
            *trace_index
        },
        (
            SourcePhysicalIoEvent::Input { .. },
            SourceInputIoEvent::Output(_),
        )
        | (
            SourcePhysicalIoEvent::Output { .. },
            SourceInputIoEvent::Input { .. },
        ) => {
            return Err(Error::InconsistentReplay);
        },
    };
    Ok(step)
}
