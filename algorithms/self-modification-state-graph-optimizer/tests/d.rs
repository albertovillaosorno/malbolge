// File:
//   - d.rs
// Path:
//   - algorithms/self-modification-state-graph-optimizer/tests/d.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Complete-memory evidence for the per-step mutation-count bound.
// - Must-Not:
//   - Infer writes from private transition plans or trace implementation
//   - detail.
// - Allows:
//   - Inputs: public classic/profile state constructors and one-step execution.
//   - Outputs: exact before/after changed-cell counts for every instruction
//   - family.
//   - Side effects: test-process allocation of complete current memory
//   - snapshots.
// - Split-When:
//   - Split when a persistent/delta representation gains independent evidence.
// - Merge-When:
//   - Merge when runtime traces expose a stable semantic memory-delta contract.
// - Summary:
//   - Proves every instruction family changes at most two memory cells per
//   - step.
// - Description:
//   - Includes real two-cell crazy/rotate and zero-cell rejection/halt
//   - witnesses.
// - Usage:
//   - Composed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Compares complete before/after memory images, not planned write metadata.
//
// Related documents:
// - math/algorithms/self-modification-state-graph-optimizer.tex
//
// Large file:
//   - false
//

//! Complete-memory witnesses for the normative per-step mutation-count bound.

use malbolge::{
    MEMORY_WORDS, Machine, MachineError, Memory, MemoryDelta, ProfileMachine,
    ProfileMachineError, ProfileMachineIoState, ProfileMachineState,
    ProfileMemoryDelta, ProfileRegisters, ProfileStepTrace, Registers,
    StepTrace, Word, current_profile,
};

const ACCUMULATOR: u8 = 7;
const CURRENT_BASE_SOURCE: &[u8] = b"QP";
const DATA_ADDRESS: u8 = 1;
const DATA_VALUE: u8 = 2;
const ENCRYPTION_TARGET: u8 = 2;
const GRAPHICAL_TARGET: u8 = b'D';
const INPUT: u8 = 0x41;
const MAX_MEMORY_DELTA: usize = 2;

const CASES: &[InstructionCase] = &[
    InstructionCase {
        cell: b'>',
        expected_changes: 2,
        rejection: false,
    },
    InstructionCase {
        cell: b'Q',
        expected_changes: 0,
        rejection: false,
    },
    InstructionCase {
        cell: b'c',
        expected_changes: 1,
        rejection: false,
    },
    InstructionCase {
        cell: b'b',
        expected_changes: 1,
        rejection: false,
    },
    InstructionCase {
        cell: b'(',
        expected_changes: 1,
        rejection: false,
    },
    InstructionCase {
        cell: b'D',
        expected_changes: 1,
        rejection: false,
    },
    InstructionCase {
        cell: b'u',
        expected_changes: 1,
        rejection: false,
    },
    InstructionCase {
        cell: b'\'',
        expected_changes: 2,
        rejection: false,
    },
    InstructionCase {
        cell: b'b',
        expected_changes: 0,
        rejection: true,
    },
];

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
struct Change {
    address: u32,
    after: u32,
    before: u32,
}

type ClassicCaseResult = Result<(Vec<Change>, MemoryDelta), String>;
type ProfileCaseResult = Result<(Vec<Change>, ProfileMemoryDelta), String>;

#[derive(Clone, Copy, Debug)]
struct InstructionCase {
    cell: u8,
    expected_changes: usize,
    rejection: bool,
}

fn changed_classic_cells(
    before: &Memory,
    after: &Machine,
) -> Result<Vec<Change>, String> {
    let mut changed = Vec::new();
    for raw in 0..MEMORY_WORDS {
        let value = u16::try_from(raw).map_err(|error| {
            format!("classic address conversion failed: {error}")
        })?;
        let address = Word::new(value)
            .map_err(|error| format!("classic address invalid: {error}"))?;
        let before_word = before
            .read(address)
            .map_err(|error| format!("classic before read failed: {error}"))?;
        let after_word = after
            .memory_word(address)
            .map_err(|error| format!("classic after read failed: {error}"))?;
        if before_word != after_word {
            changed.push(Change {
                address: u32::from(value),
                after: u32::from(after_word.value()),
                before: u32::from(before_word.value()),
            });
        }
    }
    Ok(changed)
}

fn changed_profile_cells(
    before: &[u32],
    after: &[u32],
) -> Result<Vec<Change>, String> {
    if before.len() != after.len() {
        return Err(String::from(
            "profile memory length changed after one step",
        ));
    }
    let mut changed = Vec::new();
    for (raw_address, (before_word, after_word)) in
        before.iter().zip(after).enumerate()
    {
        if before_word != after_word {
            let address = u32::try_from(raw_address).map_err(|error| {
                format!("profile address conversion: {error}")
            })?;
            changed.push(Change {
                address,
                after: *after_word,
                before: *before_word,
            });
        }
    }
    Ok(changed)
}

fn classic_trace_changes(delta: MemoryDelta) -> Vec<Change> {
    let mut changed = [delta.data, delta.encryption]
        .into_iter()
        .flatten()
        .map(|write| Change {
            address: u32::from(write.address.value()),
            after: u32::from(write.after.value()),
            before: u32::from(write.before.value()),
        })
        .collect::<Vec<_>>();
    changed.sort_unstable();
    changed
}

fn profile_trace_changes(delta: ProfileMemoryDelta) -> Vec<Change> {
    let mut changed = [delta.data, delta.encryption]
        .into_iter()
        .flatten()
        .map(|write| Change {
            address: write.address,
            after: write.after,
            before: write.before,
        })
        .collect::<Vec<_>>();
    changed.sort_unstable();
    changed
}

fn classic_case(case: InstructionCase) -> ClassicCaseResult {
    let mut memory = Memory::filled(Word::ZERO);
    memory
        .replace(Word::ZERO, Word::from_byte(case.cell))
        .map_err(|error| {
            format!("classic instruction setup failed: {error}")
        })?;
    memory
        .replace(Word::from_byte(DATA_ADDRESS), Word::from_byte(DATA_VALUE))
        .map_err(|error| format!("classic data setup failed: {error}"))?;
    let target = if case.rejection {
        Word::ZERO
    } else {
        Word::from_byte(GRAPHICAL_TARGET)
    };
    memory
        .replace(Word::from_byte(ENCRYPTION_TARGET), target)
        .map_err(|error| format!("classic target setup failed: {error}"))?;
    let before = memory.clone();
    let registers = Registers {
        accumulator: Word::from_byte(ACCUMULATOR),
        code_pointer: Word::ZERO,
        data_pointer: Word::from_byte(DATA_ADDRESS),
    };
    let mut machine = Machine::with_registers(memory, vec![INPUT], registers);
    let mut traced_delta = None;
    let result = machine.step_traced(&mut |trace: &StepTrace| {
        traced_delta = Some(trace.memory_delta);
    });
    if case.rejection {
        let expected = Err(MachineError::InvalidEncryptionTarget {
            pointer: Word::from_byte(ENCRYPTION_TARGET),
            value: Word::ZERO,
        });
        if result != expected {
            return Err(format!("classic rejection mismatch: {result:?}"));
        }
    } else if result.is_err() {
        return Err(format!(
            "classic instruction unexpectedly failed: {result:?}"
        ));
    }
    let changed = changed_classic_cells(&before, &machine)?;
    let delta = traced_delta.ok_or_else(|| {
        String::from("classic trace did not emit memory delta")
    })?;
    Ok((changed, delta))
}

fn current_base_memory() -> Result<Vec<u32>, String> {
    let machine = ProfileMachine::from_source(
        current_profile(),
        CURRENT_BASE_SOURCE,
        Vec::new(),
    )
    .map_err(|error| format!("current base load failed: {error}"))?;
    Ok(machine.snapshot_state().memory().to_vec())
}

fn profile_case(base: &[u32], case: InstructionCase) -> ProfileCaseResult {
    let mut memory = base.to_vec();
    let instruction = memory
        .get_mut(0)
        .ok_or_else(|| String::from("missing current instruction cell"))?;
    *instruction = u32::from(case.cell);
    let data = memory
        .get_mut(usize::from(DATA_ADDRESS))
        .ok_or_else(|| String::from("missing current data cell"))?;
    *data = u32::from(DATA_VALUE);
    let target = memory
        .get_mut(usize::from(ENCRYPTION_TARGET))
        .ok_or_else(|| String::from("missing current encryption target"))?;
    *target = if case.rejection {
        0
    } else {
        u32::from(GRAPHICAL_TARGET)
    };
    let before = memory.clone();
    let io = ProfileMachineIoState::new(vec![INPUT], 0, Vec::new(), None)
        .map_err(|error| format!("current IO state failed: {error}"))?;
    let state = ProfileMachineState::new(
        current_profile(),
        memory,
        ProfileRegisters {
            accumulator: u32::from(ACCUMULATOR),
            code_pointer: 0,
            data_pointer: u32::from(DATA_ADDRESS),
        },
        io,
    )
    .map_err(|error| format!("current state failed: {error}"))?;
    let mut machine = ProfileMachine::from_snapshot(state);
    let mut traced_delta = None;
    let result = machine.step_traced(&mut |trace: &ProfileStepTrace| {
        traced_delta = Some(trace.memory_delta);
    });
    if case.rejection {
        let expected = Err(ProfileMachineError::InvalidEncryptionTarget {
            pointer: u32::from(ENCRYPTION_TARGET),
            value: 0,
        });
        if result != expected {
            return Err(format!("current rejection mismatch: {result:?}"));
        }
    } else if result.is_err() {
        return Err(format!(
            "current instruction unexpectedly failed: {result:?}"
        ));
    }
    let after = machine.snapshot_state();
    let changed = changed_profile_cells(&before, after.memory())?;
    let delta = traced_delta.ok_or_else(|| {
        String::from("profile trace did not emit memory delta")
    })?;
    Ok((changed, delta))
}

fn validate_case(
    case: InstructionCase,
    mut observed: Vec<Change>,
    mut traced: Vec<Change>,
    profile: &str,
) -> Result<(), String> {
    observed.sort_unstable();
    traced.sort_unstable();
    if observed.len() > MAX_MEMORY_DELTA {
        return Err(format!(
            "{profile} step changed {} memory cells",
            observed.len()
        ));
    }
    if observed.len() != case.expected_changes {
        return Err(format!(
            "{profile} cell={} expected {} changes, observed {}",
            case.cell,
            case.expected_changes,
            observed.len()
        ));
    }
    if observed != traced {
        return Err(format!(
            "{profile} delta cell={}: actual={observed:?} trace={traced:?}",
            case.cell
        ));
    }
    Ok(())
}

#[test]
fn classic_instruction_families_obey_two_cell_memory_delta()
-> Result<(), String> {
    for case in CASES {
        let (observed, delta) = classic_case(*case)?;
        validate_case(
            *case,
            observed,
            classic_trace_changes(delta),
            "classic",
        )?;
    }
    Ok(())
}

#[test]
fn current_instruction_families_obey_two_cell_memory_delta()
-> Result<(), String> {
    let base = current_base_memory()?;
    for case in CASES {
        let (observed, delta) = profile_case(&base, *case)?;
        validate_case(
            *case,
            observed,
            profile_trace_changes(delta),
            "current",
        )?;
    }
    Ok(())
}
