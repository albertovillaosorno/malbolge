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

impl PhysicalReentryWindow {
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
