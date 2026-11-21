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
// - Owns: exact changed-memory and I/O journals between physical reentries.
// - Must-Not: infer an arbitrary-input loop from a finite return trajectory.
// - Allows: canonical source, bounded normative steps and repeated code sites.
// - Summary: exposes complete-state restoration instead of phase coincidence.

//! A bounded physical reentry contract from the normative Malbolge VM.
//!
//! Every changed memory word is journaled from its first before-value to its
//! last after-value, including self-encryption and data/code aliasing. This
//! avoids cloning the entire N15 memory at every reentry. Equality of the
//! complete nonterminated VM state is sufficient for a deterministic closed
//! cycle under the *same fixed input*, but merely revisiting a code pointer
//! or restoring C/D/A never establishes a general byte-stream loop.

use std::collections::BTreeMap;
use std::mem::take;

use malbolge::{
    MemoryLiveIn, ProfileDescriptor, ProfileMachine, ProfileMemoryRead,
    ProfileMemoryWrite, ProfileRegisterSet, ProfileRegisters, ProfileStepTrace,
    RegisterMaskedRegionEffectProgram, RunOutcome, StepOutcome, TraceInput,
};

/// Maximum source cells admitted by this bounded physical-state experiment.
pub const MAX_PHYSICAL_REENTRY_SOURCE: usize = 4096;
/// Maximum real guest instructions examined in one source execution.
pub const MAX_PHYSICAL_REENTRY_STEPS: usize = 2048;
/// Maximum observed visits to the selected physical code site.
pub const MAX_PHYSICAL_REENTRY_VISITS: usize = 4;

/// An exact physical guest boundary, before the entry code cell is fetched.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PhysicalEntryState {
    /// Number of successful stdin bytes consumed before this boundary.
    pub input_consumed: usize,
    /// Number of stdout bytes committed before this boundary.
    pub output_len: usize,
    /// The actual accumulator, code pointer and data pointer.
    pub registers: ProfileRegisters,
    /// Zero-based count of previously committed VM instructions.
    pub step: usize,
}

/// One net changed word between two observed entries to the same code site.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PhysicalWordChange {
    /// Actual profile memory address.
    pub address: u32,
    /// Value at the following entry, after all intervening writes.
    pub after: u32,
    /// Value at the first entry, before any intervening instruction.
    pub before: u32,
}

/// One actual data-operand instruction inside a physical return interval.
///
/// The written word records the *instruction* result for `p` or `*`, even
/// when the write is idempotent or its address aliases the encryption target.
/// This is not necessarily the final word at that address after XLAT2.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PhysicalDataOperation {
    /// Physical code site that executed the decoded instruction.
    pub code_pointer: u32,
    /// The actual decoded data-using opcode (`i`, `j`, `p` or `*`).
    pub opcode: u8,
    /// Exact semantic data-pointer read, including its observed value.
    pub read: ProfileMemoryRead,
    /// Global zero-based step index before the operation committed.
    pub step: usize,
    /// `p`/`*` result, including an idempotent write; `None` for `i`/`j`.
    pub written_value: Option<u32>,
}

/// One changed post-instruction XLAT2 word, with source and target sites.
///
/// For a reached `i` the encrypted cell is the *jump target*, rather than
/// the fetched instruction. Aliases to a data write retain the final effect.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PhysicalCodeMutation {
    /// Code pointer fetched at the start of the committed instruction.
    pub execution_site: u32,
    /// Exact changed cell, original value and final encrypted value.
    pub write: ProfileMemoryWrite,
    /// Global zero-based guest instruction index.
    pub step: usize,
}

/// One actual guest I/O effect, retaining its exact source-code site.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PhysicalIoEffect {
    /// A reached input read, including exhausted-input attempts.
    Input(TraceInput),
    /// One committed guest output byte.
    Output(u8),
}

/// A chronological I/O event within a source-loaded physical interval.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PhysicalIoOperation {
    /// Physical code pointer that executed the input or output instruction.
    pub code_pointer: u32,
    /// The committed semantic I/O effect.
    pub effect: PhysicalIoEffect,
    /// Global zero-based guest instruction index.
    pub step: usize,
}

/// One real interval between two entries to an identical code address.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PhysicalReentryWindow {
    /// Count of real changed-value post-instruction XLAT2 writes.
    pub code_encryption_changes: usize,
    /// Chronological changed XLAT2 effects, including actual jump targets.
    pub code_mutations: Vec<PhysicalCodeMutation>,
    /// Count of reached p/* instruction writes, including idempotent writes.
    pub data_instruction_writes: usize,
    /// Exact chronological data-operand operations and their values.
    pub data_operations: Vec<PhysicalDataOperation>,
    /// Every real guest data read address, in chronological order.
    pub data_read_addresses: Vec<u32>,
    /// Every p/* instruction's data target, including idempotent writes.
    pub data_write_addresses: Vec<u32>,
    /// First reached entry state.
    pub from: PhysicalEntryState,
    /// Entry words read before any reached write, including code fetch,
    /// instruction data and XLAT2 operand reads.
    pub memory_live_ins: Vec<MemoryLiveIn>,
    /// Register values actually read before their first committed overwrite.
    pub register_live_ins: ProfileRegisterSet,
    /// Actual source-site and step chronology of every reached I/O effect.
    pub io_operations: Vec<PhysicalIoOperation>,
    /// All real input attempts, including EOF without consumption.
    pub input_events: Vec<TraceInput>,
    /// Final-minus-initial changes in the *whole* profile memory image.
    pub net_changed_words: Vec<PhysicalWordChange>,
    /// Exact newly committed output bytes in the interval.
    pub output_bytes: Vec<u8>,
    /// Second reached entry state.
    pub to: PhysicalEntryState,
}

/// One exact obstruction to replaying an observed region on its fixed input.
///
/// These are *necessary entry-state repairs*, not executable instructions or
/// sufficient obligations for a parametric C source-loop translation. A live
/// memory word is relevant even when its change was post-step encryption.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PhysicalReplayBlocker {
    /// The observed live accumulator is not restored for the next traversal.
    Accumulator {
        /// Accumulator at the first entry.
        required: u32,
        /// Accumulator at the following entry.
        actual: u32,
    },
    /// The observed live code pointer is not restored for the next traversal.
    CodePointer {
        /// Code pointer at the first entry.
        required: u32,
        /// Code pointer at the following entry.
        actual: u32,
    },
    /// The observed live data pointer is not restored for the next traversal.
    DataPointer {
        /// Data pointer at the first entry.
        required: u32,
        /// Data pointer at the following entry.
        actual: u32,
    },
    /// A word read before any write has a different next-entry version.
    Memory {
        /// Physical address of the live-in memory word.
        address: u32,
        /// Memory word required at the original entry.
        required: u32,
        /// Observed memory word at the following entry.
        actual: u32,
    },
    /// The same input bytes would be read from a different cursor position.
    InputCursor {
        /// Bytes consumed at the original entry.
        required: usize,
        /// Bytes consumed at the following entry.
        actual: usize,
    },
}

impl PhysicalReentryWindow {
    /// Exact live-in values blocking replay of this observed fixed-input path.
    ///
    /// Order is A, C, D, sorted memory addresses, then the stdin cursor.
    /// Dead-register and dead-memory differences are deliberately excluded.
    /// Only actual source-backed VM traces justify using these as a proposed
    /// repair set; a parametric or source-C loop needs separate verification.
    #[must_use]
    pub fn fixed_input_replay_blockers(&self) -> Vec<PhysicalReplayBlocker> {
        let mut blockers = Vec::new();
        let required = self.register_live_ins;
        let from = self.from.registers;
        let to = self.to.registers;
        if required.accumulator && from.accumulator != to.accumulator {
            blockers.push(PhysicalReplayBlocker::Accumulator {
                required: from.accumulator,
                actual: to.accumulator,
            });
        }
        if required.code_pointer && from.code_pointer != to.code_pointer {
            blockers.push(PhysicalReplayBlocker::CodePointer {
                required: from.code_pointer,
                actual: to.code_pointer,
            });
        }
        if required.data_pointer && from.data_pointer != to.data_pointer {
            blockers.push(PhysicalReplayBlocker::DataPointer {
                required: from.data_pointer,
                actual: to.data_pointer,
            });
        }
        for live_in in &self.memory_live_ins {
            if let Some(change) = self
                .net_changed_words
                .iter()
                .find(|change| change.address == live_in.address)
                && change.after != live_in.value
            {
                blockers.push(PhysicalReplayBlocker::Memory {
                    address: live_in.address,
                    required: live_in.value,
                    actual: change.after,
                });
            }
        }
        if self.from.input_consumed != self.to.input_consumed {
            blockers.push(PhysicalReplayBlocker::InputCursor {
                required: self.from.input_consumed,
                actual: self.to.input_consumed,
            });
        }
        blockers
    }

    /// Registers and all profile memory are exactly restored at this entry.
    ///
    /// Input/output effects may still have advanced, so this is a necessary
    /// *core* condition only, not an arbitrary-stream cycle certificate.
    #[must_use]
    pub fn core_state_restored(&self) -> bool {
        self.from.registers == self.to.registers
            && self.net_changed_words.is_empty()
    }

    /// All memory words needed before the first reached write are restored.
    ///
    /// Dead-memory changes are permitted; a future candidate must still
    /// independently replay the same bounded path on the normative VM.
    #[must_use]
    pub fn live_memory_restored(&self) -> bool {
        self.memory_live_ins.iter().all(|read| {
            self.net_changed_words
                .iter()
                .all(|change| change.address != read.address)
        })
    }

    /// All actually required entry registers are restored.
    ///
    /// Dead registers may differ if the verified region effect projection
    /// proves they are overwritten before any semantic use.
    #[must_use]
    pub fn live_registers_restored(&self) -> bool {
        let required = self.register_live_ins;
        let from = self.from.registers;
        let to = self.to.registers;
        (!required.accumulator || from.accumulator == to.accumulator)
            && (!required.code_pointer || from.code_pointer == to.code_pointer)
            && (!required.data_pointer || from.data_pointer == to.data_pointer)
    }

    /// The fixed-input window's observed live entry dependencies are restored.
    #[must_use]
    pub fn live_entry_restored(&self) -> bool {
        self.live_memory_restored() && self.live_registers_restored()
    }

    /// State preconditions to replay this observed interval on fixed input.
    ///
    /// The input cursor must not advance. Output and dead-memory writes may
    /// advance without changing the following interval's read dependencies.
    /// Independently replay any candidate before accepting it for linking.
    #[must_use]
    pub fn fixed_input_replay_preconditions(&self) -> bool {
        self.live_entry_restored()
            && self.from.input_consumed == self.to.input_consumed
    }

    /// The complete deterministic VM state is restored for this fixed stdin.
    ///
    /// The source, target profile and immutable input stay fixed across
    /// execution. No transition terminates inside an admitted interval.
    /// Identical registers, memory, input cursor and output state therefore
    /// imply deterministic repetition, not progress on arbitrary live input.
    #[must_use]
    pub fn exact_closed_cycle(&self) -> bool {
        self.core_state_restored()
            && self.from.input_consumed == self.to.input_consumed
            && self.from.output_len == self.to.output_len
    }
}

/// Why a proposed sequence of observed physical windows is inconsistent.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PhysicalReentryChainError {
    /// No physical interval was supplied.
    Empty,
    /// A window has invalid bounds, accounting or sorted journals.
    InvalidWindow {
        /// Zero-based window index.
        window_index: usize,
    },
    /// A prior exit is not exactly the next window's entry.
    Disconnected {
        /// Zero-based index of the window after the broken boundary.
        window_index: usize,
    },
    /// A known physical memory version does not match the later evidence.
    MemoryVersion {
        /// Zero-based index of the inconsistent window.
        window_index: usize,
        /// Physical memory address carrying the conflicting versions.
        address: u32,
        /// Value propagated from earlier live reads or actual writes.
        expected: u32,
        /// Value asserted by the later live read or write-before journal.
        observed: u32,
    },
}

// Track the first observed physical version and the latest replayed version.
// An unknown word becomes known at its first read or write-before witness.
fn check_read(
    versions: &mut BTreeMap<u32, (u32, u32)>,
    address: u32,
    value: u32,
) -> bool {
    let version = versions.entry(address).or_insert((value, value));
    version.1 == value
}

fn check_write(
    versions: &mut BTreeMap<u32, (u32, u32)>,
    write: ProfileMemoryWrite,
) -> bool {
    let version = versions
        .entry(write.address)
        .or_insert((write.before, write.before));
    if version.1 != write.before {
        return false;
    }
    version.1 = write.after;
    true
}

fn valid_effect_step(
    previous: &mut Option<usize>,
    step: usize,
    window: &PhysicalReentryWindow,
) -> bool {
    if step < window.from.step
        || step >= window.to.step
        || previous.is_some_and(|last| step <= last)
    {
        return false;
    }
    *previous = Some(step);
    true
}

/// Reject invented instruction effects even when only one interval is known.
///
/// This is a journal-consistency check, not a reimplementation of guest
/// arithmetic or proof that supplied effects originated in a real VM run.
/// Source-loaded normative replay is still required for authenticity.
fn physical_window_effects_consistent(window: &PhysicalReentryWindow) -> bool {
    if window.data_instruction_writes
        != window
            .data_operations
            .iter()
            .filter(|op| op.written_value.is_some())
            .count()
        || window.code_encryption_changes != window.code_mutations.len()
        || !window
            .data_read_addresses
            .iter()
            .copied()
            .eq(window.data_operations.iter().map(|op| op.read.address))
        || !window.data_write_addresses.iter().copied().eq(window
            .data_operations
            .iter()
            .filter(|op| op.written_value.is_some())
            .map(|op| op.read.address))
    {
        return false;
    }

    let mut previous = None;
    for operation in &window.data_operations {
        if !valid_effect_step(&mut previous, operation.step, window)
            || !matches!(operation.opcode, b'i' | b'j' | b'p' | b'*')
            || operation.written_value.is_some()
                != matches!(operation.opcode, b'p' | b'*')
        {
            return false;
        }
    }
    previous = None;
    for mutation in &window.code_mutations {
        if !valid_effect_step(&mut previous, mutation.step, window)
            || mutation.write.before == mutation.write.after
            || window
                .data_operations
                .binary_search_by_key(&mutation.step, |op| op.step)
                .is_ok_and(|index| {
                    window.data_operations[index].code_pointer
                        != mutation.execution_site
                })
        {
            return false;
        }
    }
    previous = None;
    let mut inputs = window.input_events.iter();
    let mut outputs = window.output_bytes.iter();
    for operation in &window.io_operations {
        if !valid_effect_step(&mut previous, operation.step, window)
            || window
                .code_mutations
                .binary_search_by_key(&operation.step, |op| op.step)
                .is_ok_and(|index| {
                    window.code_mutations[index].execution_site
                        != operation.code_pointer
                })
        {
            return false;
        }
        let matches_event = match &operation.effect {
            PhysicalIoEffect::Input(event) => inputs.next() == Some(event),
            PhysicalIoEffect::Output(byte) => outputs.next() == Some(byte),
        };
        if !matches_event {
            return false;
        }
    }
    if inputs.next().is_some() || outputs.next().is_some() {
        return false;
    }

    let mut versions: BTreeMap<u32, (u32, u32)> = window
        .memory_live_ins
        .iter()
        .map(|read| (read.address, (read.value, read.value)))
        .collect();
    let mut data = window.data_operations.iter().peekable();
    let mut code = window.code_mutations.iter().peekable();
    while data.peek().is_some() || code.peek().is_some() {
        let take_data = match (data.peek(), code.peek()) {
            (Some(operation), Some(mutation)) => {
                operation.step <= mutation.step
            },
            (Some(_), None) => true,
            _ => false,
        };
        if take_data {
            let Some(operation) = data.next() else {
                return false;
            };
            if !check_read(
                &mut versions,
                operation.read.address,
                operation.read.value,
            ) {
                return false;
            }
            if let Some(value) = operation.written_value
                && !check_write(&mut versions, ProfileMemoryWrite {
                    address: operation.read.address,
                    before: operation.read.value,
                    after: value,
                })
            {
                return false;
            }
        } else {
            let Some(mutation) = code.next() else {
                return false;
            };
            if !check_write(&mut versions, mutation.write) {
                return false;
            }
        }
    }
    let derived_changes: Vec<_> = versions
        .into_iter()
        .filter_map(|(address, (before, after))| {
            (before != after).then_some(PhysicalWordChange {
                address,
                after,
                before,
            })
        })
        .collect();
    derived_changes == window.net_changed_words
}

/// Verify exact continuity of bounded physical windows without cloning N15.
///
/// The verifier propagates only known memory versions: words read at an
/// interval entry and words changed in its net journal. It cannot infer an
/// unknown initial cell's value. A source-loaded VM trace authenticates the
/// journals separately; consistent windows do not certify a loop or input
/// parametricity. A changed live code cell is checked like any data word.
///
/// # Errors
///
/// Refuses empty, disconnected, internally inconsistent or contradictory
/// journals. All input and output counts must agree with recorded effects.
pub fn verify_physical_reentry_chain(
    windows: &[PhysicalReentryWindow],
) -> Result<(), PhysicalReentryChainError> {
    if windows.is_empty() {
        return Err(PhysicalReentryChainError::Empty);
    }
    let mut known = BTreeMap::<u32, u32>::new();
    let mut previous_exit = None;
    for (window_index, window) in windows.iter().enumerate() {
        let input_bytes = window
            .input_events
            .iter()
            .filter(|event| matches!(event, TraceInput::Byte(_)))
            .count();
        if window.from.step >= window.to.step
            || window.from.registers.code_pointer
                != window.to.registers.code_pointer
            || window
                .to
                .input_consumed
                .checked_sub(window.from.input_consumed)
                != Some(input_bytes)
            || window.to.output_len.checked_sub(window.from.output_len)
                != Some(window.output_bytes.len())
            || !window
                .memory_live_ins
                .windows(2)
                .all(|pair| pair[0].address < pair[1].address)
            || !window
                .net_changed_words
                .windows(2)
                .all(|pair| pair[0].address < pair[1].address)
        {
            return Err(PhysicalReentryChainError::InvalidWindow {
                window_index,
            });
        }
        if previous_exit.is_some_and(|exit| exit != window.from) {
            return Err(PhysicalReentryChainError::Disconnected {
                window_index,
            });
        }
        for live_in in &window.memory_live_ins {
            if let Some(expected) = known.insert(live_in.address, live_in.value)
                && expected != live_in.value
            {
                return Err(PhysicalReentryChainError::MemoryVersion {
                    window_index,
                    address: live_in.address,
                    expected,
                    observed: live_in.value,
                });
            }
        }
        for change in &window.net_changed_words {
            if let Some(expected) = known.insert(change.address, change.after)
                && expected != change.before
            {
                return Err(PhysicalReentryChainError::MemoryVersion {
                    window_index,
                    address: change.address,
                    expected,
                    observed: change.before,
                });
            }
        }
        if !physical_window_effects_consistent(window) {
            return Err(PhysicalReentryChainError::InvalidWindow {
                window_index,
            });
        }
        previous_exit = Some(window.to);
    }
    Ok(())
}

/// Why an exact bounded state comparison could not be completed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PhysicalReentryError {
    /// The canonical graphical source cannot be loaded by the profile VM.
    GuestLoad,
    /// A real guest transition could not commit or the trace is inconsistent.
    GuestStep,
    /// Source size, entry address or finite search limits are invalid.
    InvalidRequest,
    /// Guest halted or the fixed budget ended before enough reentries.
    MissingReentry,
}

fn append_write(
    journal: &mut BTreeMap<u32, PhysicalWordChange>,
    write: ProfileMemoryWrite,
) -> Result<(), PhysicalReentryError> {
    use std::collections::btree_map::Entry;
    match journal.entry(write.address) {
        Entry::Vacant(entry) => {
            let _entry = entry.insert(PhysicalWordChange {
                address: write.address,
                before: write.before,
                after: write.after,
            });
        },
        Entry::Occupied(mut entry) => {
            if entry.get().after != write.before {
                return Err(PhysicalReentryError::GuestStep);
            }
            entry.get_mut().after = write.after;
        },
    }
    Ok(())
}

/// Observe exact machine-state restoration across repeated physical entries.
///
/// This is a *trace analyzer*, not a code synthesizer. It never creates
/// candidate guest output or overwrites registers/memory to force a return.
/// The first entry may occur after a prefix. An incomplete or invalid path
/// is always an error instead of a fabricated reentry.
///
/// # Errors
///
/// Rejects invalid finite bounds, source loading, failed guest transitions
/// and fewer than the requested number of genuine visits.
pub fn observe_physical_reentries(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    input: &[u8],
    entry_code_pointer: u32,
    required_visits: usize,
    step_budget: usize,
) -> Result<Vec<PhysicalReentryWindow>, PhysicalReentryError> {
    if !(2..=MAX_PHYSICAL_REENTRY_SOURCE).contains(&source.len())
        || !(2..=MAX_PHYSICAL_REENTRY_VISITS).contains(&required_visits)
        || !(1..=MAX_PHYSICAL_REENTRY_STEPS).contains(&step_budget)
        || entry_code_pointer >= profile.memory_words()
        || input.len() > MAX_PHYSICAL_REENTRY_STEPS
    {
        return Err(PhysicalReentryError::InvalidRequest);
    }
    let mut vm = ProfileMachine::from_source(profile, source, input.to_vec())
        .map_err(|_error| PhysicalReentryError::GuestLoad)?;
    let mut previous: Option<PhysicalEntryState> = None;
    let mut journal: BTreeMap<u32, PhysicalWordChange> = BTreeMap::new();
    // Reuse the independently checked portable v6 dependency projection,
    // rather than maintaining another interpreter for read/write dominance.
    let mut region_traces: Vec<ProfileStepTrace> = Vec::new();
    let mut windows = Vec::with_capacity(required_visits.saturating_sub(1));
    let mut io_operations = Vec::new();
    let mut input_events = Vec::new();
    let mut output_bytes = Vec::new();
    let mut data_instruction_writes = 0usize;
    let mut data_operations = Vec::new();
    let mut data_read_addresses = Vec::new();
    let mut data_write_addresses = Vec::new();
    let mut code_encryption_changes = 0usize;
    let mut code_mutations = Vec::new();

    for step in 0..step_budget {
        if vm.registers().code_pointer == entry_code_pointer {
            let boundary = PhysicalEntryState {
                step,
                registers: vm.registers(),
                input_consumed: vm.input_consumed(),
                output_len: vm.output().len(),
            };
            if let Some(from) = previous {
                let region = RegisterMaskedRegionEffectProgram::
                    from_profile_region_traces(
                        profile,
                        &region_traces,
                        region_traces.len(),
                        RunOutcome::BudgetExhausted {
                            steps: region_traces.len(),
                        },
                    )
                    .map_err(|_error| PhysicalReentryError::GuestStep)?;
                windows.push(PhysicalReentryWindow {
                    from,
                    to: boundary,
                    memory_live_ins: region.program.memory_live_ins,
                    register_live_ins: region.register_live_ins,
                    net_changed_words: journal
                        .values()
                        .copied()
                        .filter(|word| word.before != word.after)
                        .collect(),
                    data_instruction_writes,
                    data_operations: take(&mut data_operations),
                    data_read_addresses: take(&mut data_read_addresses),
                    data_write_addresses: take(&mut data_write_addresses),
                    code_encryption_changes,
                    code_mutations: take(&mut code_mutations),
                    io_operations: take(&mut io_operations),
                    input_events: take(&mut input_events),
                    output_bytes: take(&mut output_bytes),
                });
            }
            previous = Some(boundary);
            journal.clear();
            region_traces.clear();
            data_instruction_writes = 0;
            code_encryption_changes = 0;
        }
        if windows.len().saturating_add(1) == required_visits {
            verify_physical_reentry_chain(&windows)
                .map_err(|_error| PhysicalReentryError::GuestStep)?;
            return Ok(windows);
        }

        let mut observed = None;
        let outcome = vm
            .step_traced(&mut |trace| observed = Some(*trace))
            .map_err(|_error| PhysicalReentryError::GuestStep)?;
        let trace = observed.ok_or(PhysicalReentryError::GuestStep)?;
        if previous.is_some() {
            region_traces.push(trace);
            if let Some(read) = trace.memory_reads.data {
                let opcode =
                    trace.decoded.ok_or(PhysicalReentryError::GuestStep)?;
                if !matches!(opcode, b'i' | b'j' | b'p' | b'*')
                    || read.address != trace.before.registers.data_pointer
                {
                    return Err(PhysicalReentryError::GuestStep);
                }
                let written_value = matches!(opcode, b'p' | b'*')
                    .then_some(trace.after.registers.accumulator);
                if let Some(value) = written_value {
                    data_write_addresses.push(read.address);
                    data_instruction_writes =
                        data_instruction_writes.saturating_add(1);
                    if let Some(write) = trace.memory_delta.data
                        && (write.address != read.address
                            || write.before != read.value
                            || write.after != value)
                    {
                        return Err(PhysicalReentryError::GuestStep);
                    }
                }
                data_read_addresses.push(read.address);
                data_operations.push(PhysicalDataOperation {
                    code_pointer: trace.before.registers.code_pointer,
                    opcode,
                    read,
                    step,
                    written_value,
                });
            } else if matches!(trace.decoded, Some(b'i' | b'j' | b'p' | b'*')) {
                return Err(PhysicalReentryError::GuestStep);
            }
            if let Some(write) = trace.memory_delta.data {
                append_write(&mut journal, write)?;
            }
            if let Some(write) = trace.memory_delta.encryption {
                code_encryption_changes =
                    code_encryption_changes.saturating_add(1);
                code_mutations.push(PhysicalCodeMutation {
                    execution_site: trace.before.registers.code_pointer,
                    write,
                    step,
                });
                append_write(&mut journal, write)?;
            }
            if let Some(event) = trace.input {
                if trace.decoded != Some(b'/') {
                    return Err(PhysicalReentryError::GuestStep);
                }
                input_events.push(event);
                io_operations.push(PhysicalIoOperation {
                    code_pointer: trace.before.registers.code_pointer,
                    effect: PhysicalIoEffect::Input(event),
                    step,
                });
            }
            if let Some(byte) = trace.output {
                if trace.decoded != Some(b'<') {
                    return Err(PhysicalReentryError::GuestStep);
                }
                output_bytes.push(byte);
                io_operations.push(PhysicalIoOperation {
                    code_pointer: trace.before.registers.code_pointer,
                    effect: PhysicalIoEffect::Output(byte),
                    step,
                });
            }
        }
        if outcome != StepOutcome::Continued {
            return Err(PhysicalReentryError::MissingReentry);
        }
    }
    Err(PhysicalReentryError::MissingReentry)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn journal_cancels_a_real_net_rewrite_but_checks_write_order() {
        let mut journal = BTreeMap::new();
        let first = ProfileMemoryWrite {
            address: 140,
            before: 33,
            after: 54,
        };
        assert_eq!(append_write(&mut journal, first), Ok(()));
        assert_eq!(
            append_write(&mut journal, ProfileMemoryWrite {
                address: 140,
                before: 54,
                after: 33,
            }),
            Ok(())
        );
        let net: Vec<_> = journal
            .values()
            .filter(|change| change.before != change.after)
            .collect();
        assert!(net.is_empty());
        assert_eq!(
            append_write(&mut journal, ProfileMemoryWrite {
                address: 140,
                before: 33 + 1,
                after: 51,
            }),
            Err(PhysicalReentryError::GuestStep)
        );
    }
}
