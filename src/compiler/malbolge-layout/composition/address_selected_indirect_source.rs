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
//   - Finite paired guest evidence of input-selected pointer addresses.
// - Must-Not:
//   - Certify source-C truth, arbitrary control flow or pointer-value taint.
// - Allows:
//   - Inputs: one graphical source, two input streams and exact branch sites.
//   - Outputs: independently replayed selection, route and transfer receipts.
//   - Side effects: isolated normative VM replays.
// - Split-When:
//   - More than one selector or input per branch is required.
// - Merge-When:
//   - A source-bound conditional verifier subsumes paired route evidence.
// - Summary:
//   - Distinguishes selection of a pointer address from writing its value.

//! Exact finite counterfactual evidence for address-selected indirect jumps.
//!
//! Two executions of the same program differ in exactly one reached input
//! before the same transfer. They follow the same code prefix, write distinct
//! selector values at the same store, and traverse read-only data routes to
//! distinct pointer cells and landings. This is not the pointer-value writer
//! proof and cannot certify untested inputs or source-C control semantics.

use malbolge::{
    ProfileDescriptor, RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction,
};

use super::{
    MAX_INDIRECT_SUFFIX_PROOF_INPUT, SourcePhysicalDataRead,
    SourcePhysicalDataWrite, SourcePhysicalImageTrace,
    SourcePhysicalImageTraceError, SourcePhysicalIoEvent,
    SourcePhysicalTraceBudget, SourcePhysicalWordEffect,
    admit_c23_probe_graphical_source,
    verify_source_physical_image_trace_with_budget,
};

/// One proposed physical result of a finite input stream.
#[derive(Clone, Copy, Debug)]
pub struct AddressSelectedIndirectCase<'source> {
    /// Full input, with genuine EOF represented by exhaustion.
    pub input: &'source [u8],
    /// Exact code address expected after the indirect transfer.
    pub landing_address: u32,
    /// Exact address expected in D immediately before the transfer.
    pub pointer_cell: u32,
}

/// One pair of independently replayed input-selected address routes.
#[derive(Clone, Copy, Debug)]
pub struct AddressSelectedIndirectProbe<'source> {
    /// Two distinct proposed physical branch outcomes.
    pub cases: [AddressSelectedIndirectCase<'source>; 2],
    /// The shared indirect instruction, reached exactly once in each case.
    pub indirect_code_cell: u32,
    /// Exactly one reached input before both transfers at this code site.
    pub input_code_cell: u32,
    /// The shared data cell containing the input-dependent selector value.
    pub selector_cell: u32,
    /// The reached `j` which begins the read-only pointer address route.
    pub selector_code_cell: u32,
    /// The shared reached `p` or `*` that last wrote the selector.
    pub selector_store_code_cell: u32,
    /// Complete unchanged source used for both normative replays.
    pub source: &'source [u8],
    /// Positive per-case budget, including the real halting instruction.
    pub step_budget: usize,
}

/// Why a finite paired address-selection claim was refused.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AddressSelectedIndirectError {
    /// A route operand was modified differently before its relevant read.
    ChangedRouteOperand,
    /// The replays do not share the same exact fetched code prefix.
    DifferentCodePrefix,
    /// Profile, source, claimed sites or budgets are not admitted.
    InvalidBound,
    /// Missing, repeated, misplaced or otherwise unsuitable input.
    InvalidInput,
    /// A route instruction is not a read-only jump or explicit no-op.
    InvalidRoute,
    /// The selector is missing its live, reached post-input physical store.
    InvalidSelector,
    /// A real halt was not reached within the supplied budget.
    InvalidTermination,
    /// The proposed indirect operand or actual successor is not reached.
    InvalidTransfer,
    /// Input, selector, pointer and landing must distinguish the two cases.
    NonDistinctCases,
    /// One independent physical image replay failed.
    PhysicalImage(SourcePhysicalImageTraceError),
}

/// One independently replayed branch case; construction is verifier-only.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AddressSelectedIndirectCaseProof {
    input: Vec<u8>,
    input_read: TraceInput,
    input_step: usize,
    journal: SourcePhysicalImageTrace,
    landing_address: u32,
    route: Vec<SourcePhysicalDataRead>,
    selector_write: SourcePhysicalDataWrite,
    transfer: SourcePhysicalDataRead,
}

impl AddressSelectedIndirectCaseProof {
    /// Original finite input for this replay.
    #[must_use]
    pub fn input(&self) -> &[u8] {
        &self.input
    }

    /// Actual single pre-transfer byte or EOF and its trace index.
    #[must_use]
    pub const fn input_origin(&self) -> (TraceInput, usize) {
        (self.input_read, self.input_step)
    }

    /// Complete independently reconciled physical effects and I/O.
    #[must_use]
    pub const fn journal(&self) -> &SourcePhysicalImageTrace {
        &self.journal
    }

    /// Actual branch successor code cell.
    #[must_use]
    pub const fn landing_address(&self) -> u32 {
        self.landing_address
    }

    /// Reached selector jump and subsequent data-jump operands.
    #[must_use]
    pub fn route(&self) -> &[SourcePhysicalDataRead] {
        &self.route
    }

    /// Reached selector write, including idempotent physical stores.
    #[must_use]
    pub const fn selector_write(&self) -> SourcePhysicalDataWrite {
        self.selector_write
    }

    /// Actual final indirect operand (address, value, phase and trace index).
    #[must_use]
    pub const fn transfer(&self) -> SourcePhysicalDataRead {
        self.transfer
    }
}

/// Opaque two-case proof tied to a single graphical N15 source.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AddressSelectedIndirectProof {
    budget: SourcePhysicalTraceBudget,
    cases: [AddressSelectedIndirectCaseProof; 2],
    source: Vec<u8>,
}

impl AddressSelectedIndirectProof {
    /// Resource class used for both complete physical replays.
    #[must_use]
    pub const fn budget(&self) -> SourcePhysicalTraceBudget {
        self.budget
    }

    /// The two exact replay receipts in the supplied order.
    #[must_use]
    pub const fn cases(&self) -> &[AddressSelectedIndirectCaseProof; 2] {
        &self.cases
    }

    /// The single source authenticated by both independent loader runs.
    #[must_use]
    pub fn source(&self) -> &[u8] {
        &self.source
    }
}

/// Reconcile two complete runs and prove their input-selected address routes.
///
/// Each case must execute one input before the transfer, a common physical
/// selector write after that input, and a common `j` selecting the route.
/// The entire fetched code prefix must match. After the selector, only
/// explicit no-ops and data jumps may advance D to the actual `i` operand.
/// The two runs must disagree in input, selector word, pointer address and
/// landing. Every downstream route operand must have the same pre-read
/// effect history in both runs, even when only one run reads that address.
/// Hence the changing address, not a differently written lookup word,
/// explains the distinct transfer. This certifies exactly the supplied pair.
///
/// # Errors
/// Refuses malformed probes, failed physical replays, non-halting runs,
/// unmatched sites, ambiguous input origins or differently written routes.
pub fn verify_address_selected_indirect_guest(
    profile: &'static ProfileDescriptor,
    probe: AddressSelectedIndirectProbe<'_>,
) -> Result<AddressSelectedIndirectProof, AddressSelectedIndirectError> {
    verify_address_selected_indirect_guest_with_budget(
        profile,
        probe,
        SourcePhysicalTraceBudget::Short,
    )
}

/// Reconcile the same paired address-selection proof under a finite class.
///
/// This opt-in affects only the full-image replay resource ceilings. The
/// selector, common prefix, operand history and real halt checks are the
/// same as for the original short proof.
///
/// # Errors
///
/// Refuses malformed probes, exhausted bounds and any invalid paired route.
pub fn verify_address_selected_indirect_guest_with_budget(
    profile: &'static ProfileDescriptor,
    probe: AddressSelectedIndirectProbe<'_>,
    budget: SourcePhysicalTraceBudget,
) -> Result<AddressSelectedIndirectProof, AddressSelectedIndirectError> {
    use AddressSelectedIndirectError as Error;
    let [first_case, second_case] = probe.cases;
    if profile != current_profile()
        || probe.source.len() > budget.max_source_cells()
        || admit_c23_probe_graphical_source(probe.source).is_err()
        || !(1..=budget.max_steps()).contains(&probe.step_budget)
        || [first_case, second_case].iter().any(|case| {
            case.input.len() > MAX_INDIRECT_SUFFIX_PROOF_INPUT
                || case.pointer_cell >= profile.memory_words()
                || case.landing_address >= profile.memory_words()
        })
        || probe.selector_cell >= profile.memory_words()
    {
        return Err(Error::InvalidBound);
    }
    let first = replay_case(profile, probe, first_case, budget)?;
    let second = replay_case(profile, probe, second_case, budget)?;
    verify_pair(&first, &second)?;
    Ok(AddressSelectedIndirectProof {
        budget,
        cases: [first, second],
        source: probe.source.to_vec(),
    })
}

fn unique_read(
    journal: &SourcePhysicalImageTrace,
    code_address: u32,
    opcode: u8,
) -> Option<SourcePhysicalDataRead> {
    let mut matches = journal.data_reads.iter().filter(|read| {
        read.code_address == code_address && read.opcode == opcode
    });
    let first = matches.next()?;
    matches.next().is_none().then_some(*first)
}

fn pretransfer_input(
    journal: &SourcePhysicalImageTrace,
    code_cell: u32,
    transfer_step: usize,
) -> Option<(TraceInput, usize)> {
    let mut inputs = journal.io_events.iter().filter_map(|event| match event {
        SourcePhysicalIoEvent::Input {
            code_address,
            read,
            trace_index,
            ..
        } if *trace_index < transfer_step => {
            Some((*code_address, *read, *trace_index))
        },
        SourcePhysicalIoEvent::Input { .. }
        | SourcePhysicalIoEvent::Output { .. } => None,
    });
    let (address, read, index) = inputs.next()?;
    (address == code_cell && inputs.next().is_none()).then_some((read, index))
}

const fn next_word(value: u32, memory_words: u32) -> Option<u32> {
    if value >= memory_words {
        None
    } else if value == memory_words.saturating_sub(1) {
        Some(0)
    } else {
        value.checked_add(1)
    }
}

fn live_selector_write(
    journal: &SourcePhysicalImageTrace,
    probe: AddressSelectedIndirectProbe<'_>,
    selector: SourcePhysicalDataRead,
    input_step: usize,
) -> Option<SourcePhysicalDataWrite> {
    let Some(SourcePhysicalWordEffect::DataWrite { trace_index }) =
        selector.last_word_effect
    else {
        return None;
    };
    if trace_index <= input_step
        || trace_index >= selector.trace_index
        || selector.data_address != probe.selector_cell
    {
        return None;
    }
    journal.data_writes.iter().copied().find(|write| {
        write.trace_index == trace_index
            && write.code_address == probe.selector_store_code_cell
            && write.data_address == selector.data_address
            && write.after == selector.value
    })
}

fn read_only_route(
    journal: &SourcePhysicalImageTrace,
    selector: SourcePhysicalDataRead,
    transfer: SourcePhysicalDataRead,
    memory_words: u32,
) -> Result<Vec<SourcePhysicalDataRead>, AddressSelectedIndirectError> {
    use AddressSelectedIndirectError as Error;
    let start = selector.trace_index.saturating_add(1);
    let mut address =
        next_word(selector.value, memory_words).ok_or(Error::InvalidRoute)?;
    let mut route = vec![selector];
    let fetches = journal
        .code_fetches
        .get(start..transfer.trace_index)
        .ok_or(Error::InvalidRoute)?;
    for fetch in fetches {
        match decode_profile_instruction(fetch.value, fetch.code_address) {
            Some(b'o') => (),
            Some(b'j') => {
                let read = journal
                    .data_reads
                    .iter()
                    .find(|read| read.trace_index == fetch.trace_index)
                    .ok_or(Error::InvalidRoute)?;
                if read.opcode != b'j' || read.data_address != address {
                    return Err(Error::InvalidRoute);
                }
                address = read.value;
                route.push(*read);
            },
            _ => return Err(Error::InvalidRoute),
        }
        address =
            next_word(address, memory_words).ok_or(Error::InvalidRoute)?;
    }
    if address != transfer.data_address {
        return Err(Error::InvalidRoute);
    }
    Ok(route)
}

fn replay_case(
    profile: &'static ProfileDescriptor,
    probe: AddressSelectedIndirectProbe<'_>,
    case: AddressSelectedIndirectCase<'_>,
    budget: SourcePhysicalTraceBudget,
) -> Result<AddressSelectedIndirectCaseProof, AddressSelectedIndirectError> {
    use AddressSelectedIndirectError as Error;
    let journal = verify_source_physical_image_trace_with_budget(
        profile,
        probe.source,
        case.input,
        probe.step_budget,
        budget,
    )
    .map_err(Error::PhysicalImage)?;
    if !matches!(journal.source.outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        ..
    }) {
        return Err(Error::InvalidTermination);
    }
    let transfer = unique_read(&journal, probe.indirect_code_cell, b'i')
        .ok_or(Error::InvalidTransfer)?;
    let landing = journal
        .code_fetches
        .get(transfer.trace_index.saturating_add(1))
        .ok_or(Error::InvalidTransfer)?
        .code_address;
    if transfer.data_address != case.pointer_cell
        || next_word(transfer.value, profile.memory_words()) != Some(landing)
        || landing != case.landing_address
    {
        return Err(Error::InvalidTransfer);
    }
    let (input_read, input_step) = pretransfer_input(
        &journal,
        probe.input_code_cell,
        transfer.trace_index,
    )
    .ok_or(Error::InvalidInput)?;
    let selector = unique_read(&journal, probe.selector_code_cell, b'j')
        .ok_or(Error::InvalidSelector)?;
    let selector_write =
        live_selector_write(&journal, probe, selector, input_step)
            .ok_or(Error::InvalidSelector)?;
    let route =
        read_only_route(&journal, selector, transfer, profile.memory_words())?;
    Ok(AddressSelectedIndirectCaseProof {
        input: case.input.to_vec(),
        input_read,
        input_step,
        journal,
        landing_address: landing,
        route,
        selector_write,
        transfer,
    })
}

fn same_operand_history(
    first: &SourcePhysicalImageTrace,
    second: &SourcePhysicalImageTrace,
    read: &SourcePhysicalDataRead,
) -> bool {
    let address = read.data_address;
    let data = |write: &&SourcePhysicalDataWrite| {
        write.data_address == address && write.trace_index < read.trace_index
    };
    let encryption = |write: &&super::SourcePhysicalEncryptionWrite| {
        write.target_address == address && write.trace_index < read.trace_index
    };
    first
        .data_writes
        .iter()
        .filter(data)
        .eq(second.data_writes.iter().filter(data))
        && first
            .encryptions
            .iter()
            .filter(encryption)
            .eq(second.encryptions.iter().filter(encryption))
}

fn verify_pair(
    first: &AddressSelectedIndirectCaseProof,
    second: &AddressSelectedIndirectCaseProof,
) -> Result<(), AddressSelectedIndirectError> {
    use AddressSelectedIndirectError as Error;
    let transfer_step = first.transfer.trace_index;
    if first.input_step != second.input_step
        || transfer_step != second.transfer.trace_index
        || first.journal.code_fetches.get(..=transfer_step)
            != second.journal.code_fetches.get(..=transfer_step)
    {
        return Err(Error::DifferentCodePrefix);
    }
    if first.input_read == second.input_read
        || first.selector_write.trace_index != second.selector_write.trace_index
        || first.selector_write.opcode != second.selector_write.opcode
        || first.selector_write.after == second.selector_write.after
        || first.transfer.data_address == second.transfer.data_address
        || first.landing_address == second.landing_address
    {
        return Err(Error::NonDistinctCases);
    }
    if first
        .route
        .iter()
        .skip(1)
        .chain(second.route.iter().skip(1))
        .chain([&first.transfer, &second.transfer])
        .any(|read| {
            !same_operand_history(&first.journal, &second.journal, read)
        })
    {
        return Err(Error::ChangedRouteOperand);
    }
    Ok(())
}
