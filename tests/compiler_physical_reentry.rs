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
// - Owns: complete N15 memory-state comparison at physical reentry.
// - Must-Not: equate two visits or finite EOF streams with an infinite loop.
// - Allows: canonical 132-cell source, three signed reads and VM-only traces.
// - Summary: a reentered code site must restore actual state, not its phase.

//! Physical reentry is not a reusable guest loop without a state contract.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use layout::{
    PhysicalCodeMutation, PhysicalDataOperation, PhysicalEntryState,
    PhysicalIoEffect, PhysicalReentryChainError, PhysicalReentryError,
    PhysicalReentryWindow, PhysicalReplayBlocker, PhysicalWordChange,
    build_two_input_class_state_with_guarded_third_read_source,
    observe_physical_reentries, verify_physical_reentry_chain,
};
use malbolge::{
    MemoryLiveIn, ProfileMachine, ProfileMemoryRead, ProfileRegisterSet,
    ProfileRegisters, ProfileStepTrace, RegisterMaskedRegionEffectProgram,
    RunOutcome, StepOutcome, current_profile, decode_profile_instruction,
    profile_crazy, profile_rotate,
};

const ENTRY: u32 = 71;
const STEPS: usize = 190;

/// The same three explicit physical edits as the source-locked third-read
/// witness; no host-supplied VM memory or post-load modifications.
fn source() -> Result<Vec<u8>, String> {
    let mut source =
        build_two_input_class_state_with_guarded_third_read_source(
            current_profile(),
        )
        .map_err(|error| format!("{error:?}"))?;
    for (position, opcode) in [(71usize, b'<'), (104, b'o'), (112, b'p')] {
        let encoded = (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(
                    u32::from(*byte),
                    u32::try_from(position).unwrap_or(u32::MAX),
                ) == Some(opcode)
            })
            .ok_or_else(|| format!("unencodable {opcode} at {position}"))?;
        *source
            .get_mut(position)
            .ok_or_else(|| format!("missing site {position}"))? = encoded;
    }
    Ok(source)
}

#[test]
fn exact_cycle_predicate_requires_no_io_progress_even_if_core_matches() {
    // A logical boundary predicate test, not a source-loaded cycle witness.
    let from = PhysicalEntryState {
        input_consumed: 0,
        output_len: 0,
        registers: ProfileRegisters::default(),
        step: 0,
    };
    let mut window = PhysicalReentryWindow {
        code_encryption_changes: 0,
        code_mutations: Vec::new(),
        data_instruction_writes: 0,
        data_operations: Vec::new(),
        data_read_addresses: Vec::new(),
        data_write_addresses: Vec::new(),
        from,
        io_operations: Vec::new(),
        input_events: Vec::new(),
        memory_live_ins: Vec::new(),
        register_live_ins: ProfileRegisterSet {
            accumulator: true,
            code_pointer: true,
            data_pointer: true,
        },
        net_changed_words: Vec::new(),
        output_bytes: Vec::new(),
        to: PhysicalEntryState { step: 5, ..from },
    };
    assert!(window.core_state_restored());
    assert!(window.exact_closed_cycle());
    window.to.input_consumed = 1;
    assert!(window.core_state_restored());
    assert!(!window.exact_closed_cycle());
    window.to.input_consumed = 0;
    window.to.output_len = 1;
    assert!(window.core_state_restored());
    assert!(!window.exact_closed_cycle());
    window.to.output_len = 0;
    window.to.registers.data_pointer = 3;
    assert!(!window.core_state_restored());
    assert!(!window.exact_closed_cycle());
}

#[test]
fn dead_memory_changes_do_not_invalidate_observed_replay_preconditions() {
    // A logical window predicate only; the source-backed negative witness
    // below independently checks real VM entries and live memory.
    let from = PhysicalEntryState {
        input_consumed: 2,
        output_len: 1,
        registers: ProfileRegisters::default(),
        step: 10,
    };
    let mut window = PhysicalReentryWindow {
        code_encryption_changes: 1,
        code_mutations: Vec::new(),
        data_instruction_writes: 1,
        data_operations: Vec::new(),
        data_read_addresses: vec![100],
        data_write_addresses: vec![200],
        from,
        io_operations: Vec::new(),
        input_events: Vec::new(),
        memory_live_ins: vec![MemoryLiveIn { address: 100, value: 42 }],
        register_live_ins: ProfileRegisterSet {
            accumulator: false,
            code_pointer: true,
            data_pointer: false,
        },
        net_changed_words: vec![PhysicalWordChange {
            address: 200,
            before: 7,
            after: 8,
        }],
        output_bytes: vec![9],
        to: PhysicalEntryState {
            step: 14,
            output_len: 2,
            ..from
        },
    };
    assert!(!window.core_state_restored());
    assert!(window.live_memory_restored());
    assert!(window.live_registers_restored());
    assert!(window.live_entry_restored());
    assert!(window.fixed_input_replay_preconditions());
    assert!(window.fixed_input_replay_blockers().is_empty());
    window.net_changed_words.push(PhysicalWordChange {
        address: 100,
        before: 42,
        after: 43,
    });
    assert!(!window.live_memory_restored());
    assert!(!window.live_entry_restored());
    assert!(!window.fixed_input_replay_preconditions());
    assert_eq!(window.fixed_input_replay_blockers(), [
        PhysicalReplayBlocker::Memory {
            address: 100,
            required: 42,
            actual: 43,
        },
    ]);
    let _removed = window.net_changed_words.pop();
    window.to.input_consumed = 3;
    assert!(window.live_memory_restored());
    assert!(!window.fixed_input_replay_preconditions());
    assert_eq!(window.fixed_input_replay_blockers(), [
        PhysicalReplayBlocker::InputCursor { required: 2, actual: 3 },
    ]);
    window.to.input_consumed = 2;
    window.to.registers.accumulator = 1;
    // The observed region never reads A before overwriting it.
    assert!(window.live_registers_restored());
    window.register_live_ins.accumulator = true;
    assert!(!window.live_registers_restored());
    assert!(!window.live_entry_restored());
    assert_eq!(window.fixed_input_replay_blockers(), [
        PhysicalReplayBlocker::Accumulator { required: 0, actual: 1 },
    ]);
}

#[test]
fn genuine_third_input_path_reenters_but_does_not_restore_state()
-> Result<(), String> {
    let source = source()?;
    for input in [vec![3, 4, 5], vec![0, 255, 128], vec![255, 0, 1]] {
        let windows = observe_physical_reentries(
            current_profile(),
            &source,
            &input,
            ENTRY,
            2,
            STEPS,
        )
        .map_err(|error| format!("{error:?}"))?;
        let [window] = windows.as_slice() else {
            return Err("expected exactly one physical reentry".into());
        };
        assert_eq!(window.from.registers.code_pointer, ENTRY);
        assert_eq!(window.to.registers.code_pointer, ENTRY);
        assert!(window.to.step > window.from.step);
        assert_ne!(
            window.from.registers.data_pointer,
            window.to.registers.data_pointer,
        );
        assert!(!window.net_changed_words.is_empty());
        assert_eq!(window.from.step, 71);
        assert_eq!(window.to.step, 141);
        assert_eq!(window.net_changed_words.len(), 78);
        assert_eq!(window.data_instruction_writes, 8);
        assert_eq!(window.code_encryption_changes, 70);
        assert_eq!(window.io_operations.len(), 2);
        assert_eq!(window.input_events, []);
        assert_eq!(window.output_bytes, [134, 154]);
        assert!(!window.core_state_restored());
        assert!(!window.live_entry_restored());
        assert!(!window.fixed_input_replay_preconditions());
        let blockers = window.fixed_input_replay_blockers();
        assert!(blockers.contains(&PhysicalReplayBlocker::Accumulator {
            required: 134,
            actual: 4_783_015,
        }));
        assert!(blockers.contains(&PhysicalReplayBlocker::DataPointer {
            required: 141,
            actual: 7_174_359,
        }));
        assert!(blockers.iter().any(|blocker| matches!(
            blocker,
            PhysicalReplayBlocker::Memory { address, .. } if *address == ENTRY
        )));
        assert!(!blockers.iter().any(|blocker| matches!(
            blocker,
            PhysicalReplayBlocker::InputCursor { .. }
        )));
        assert!(!window.memory_live_ins.is_empty());
        assert!(
            window
                .memory_live_ins
                .windows(2)
                .all(|pair| pair[0].address < pair[1].address)
        );
        assert!(!window.exact_closed_cycle());
    }
    Ok(())
}

#[test]
fn real_guest_data_footprints_match_an_independent_traced_replay()
-> Result<(), String> {
    let source = source()?;
    let input = [3, 4, 5];
    let windows = observe_physical_reentries(
        current_profile(),
        &source,
        &input,
        ENTRY,
        2,
        STEPS,
    )
    .map_err(|error| format!("{error:?}"))?;
    let window = windows
        .first()
        .ok_or_else(|| "no physical reentry".to_owned())?;
    let mut vm =
        ProfileMachine::from_source(current_profile(), &source, input.to_vec())
            .map_err(|error| error.to_string())?;
    let mut visiting = false;
    let mut actual_reads = Vec::new();
    let mut actual_writes = Vec::new();
    let mut actual_operations = Vec::new();
    let mut actual_code_mutations = Vec::new();
    for step in 0..STEPS {
        if vm.registers().code_pointer == ENTRY {
            if visiting {
                break;
            }
            visiting = true;
        }
        let mut trace = None;
        let outcome = vm
            .step_traced(&mut |observed| trace = Some(*observed))
            .map_err(|error| error.to_string())?;
        if visiting {
            let observed = trace.ok_or("missing trace event")?;
            if let Some(write) = observed.memory_delta.encryption {
                actual_code_mutations.push(PhysicalCodeMutation {
                    execution_site: observed.before.registers.code_pointer,
                    write,
                    step,
                });
            }
            if let Some(read) = observed.memory_reads.data {
                let opcode = observed.decoded.ok_or("read without opcode")?;
                actual_reads.push(read.address);
                let written_value = match opcode {
                    b'p' => Some(profile_crazy(
                        read.value,
                        observed.before.registers.accumulator,
                        current_profile().word_trits(),
                    )),
                    b'*' => Some(profile_rotate(
                        read.value,
                        current_profile().word_modulus(),
                    )),
                    b'i' | b'j' => None,
                    _ => return Err("unexpected data opcode".into()),
                };
                if let Some(value) = written_value {
                    actual_writes.push(read.address);
                    assert_eq!(observed.after.registers.accumulator, value);
                }
                actual_operations.push(PhysicalDataOperation {
                    code_pointer: observed.before.registers.code_pointer,
                    opcode,
                    read: ProfileMemoryRead {
                        address: observed.before.registers.data_pointer,
                        value: read.value,
                    },
                    step,
                    written_value,
                });
            }
        }
        assert_eq!(outcome, StepOutcome::Continued);
    }
    assert_eq!(window.data_read_addresses, actual_reads);
    assert_eq!(window.data_write_addresses, actual_writes);
    assert_eq!(window.data_operations, actual_operations);
    assert_eq!(window.code_mutations, actual_code_mutations);
    assert_eq!(window.code_mutations.len(), window.code_encryption_changes);
    assert_eq!(window.code_mutations.len(), 70);
    assert!(
        window
            .code_mutations
            .iter()
            .any(|write| { write.execution_site != write.write.address })
    );
    assert!(window.data_operations.iter().any(|op| op.opcode == b'j'));
    assert!(window.data_operations.iter().any(|op| op.opcode == b'i'));
    assert!(window.data_operations.iter().any(|op| op.opcode == b'p'));
    assert!(window.data_operations.iter().any(|op| op.opcode == b'*'));
    assert_eq!(
        window.data_instruction_writes,
        window.data_write_addresses.len()
    );
    assert!(!window.data_read_addresses.is_empty());
    assert_eq!(window.data_write_addresses.len(), 8);
    Ok(())
}

#[test]
fn physical_live_ins_agree_with_separate_verified_region_projection()
-> Result<(), String> {
    let source = source()?;
    for input in [vec![3, 4, 5], vec![0, 255, 128]] {
        let windows = observe_physical_reentries(
            current_profile(),
            &source,
            &input,
            ENTRY,
            2,
            STEPS,
        )
        .map_err(|error| format!("{error:?}"))?;
        let window = windows.first().ok_or("no physical reentry")?;
        let mut vm =
            ProfileMachine::from_source(current_profile(), &source, input)
                .map_err(|error| error.to_string())?;
        let mut started = false;
        let mut traces: Vec<ProfileStepTrace> = Vec::new();
        for _ in 0..STEPS {
            if started && vm.registers().code_pointer == ENTRY {
                break;
            }
            started |= vm.registers().code_pointer == ENTRY;
            let mut trace = None;
            let result = vm
                .step_traced(&mut |event| trace = Some(*event))
                .map_err(|error| error.to_string())?;
            assert_eq!(result, StepOutcome::Continued);
            if started {
                traces.push(trace.ok_or("missing traced instruction")?);
            }
        }
        assert_eq!(traces.len(), window.to.step - window.from.step);
        let projection =
            RegisterMaskedRegionEffectProgram::from_profile_region_traces(
                current_profile(),
                &traces,
                traces.len(),
                RunOutcome::BudgetExhausted { steps: traces.len() },
            )
            .map_err(|error| format!("{error:?}"))?;
        assert_eq!(
            window.memory_live_ins, projection.program.memory_live_ins,
            "physical collector and portable region proof disagree",
        );
        assert_eq!(window.register_live_ins, projection.register_live_ins);
        assert!(
            !projection.program.memory_live_ins.is_empty(),
            "no code memory dependencies in a real guest loop is impossible",
        );
    }
    Ok(())
}

#[test]
fn chronological_memory_journal_agrees_with_full_vm_memory_images()
-> Result<(), String> {
    let source = source()?;
    let input = [3, 4, 5];
    let windows = observe_physical_reentries(
        current_profile(),
        &source,
        &input,
        ENTRY,
        2,
        STEPS,
    )
    .map_err(|error| format!("{error:?}"))?;
    let window = windows
        .first()
        .ok_or_else(|| "missing exact physical window".to_owned())?;
    let mut vm =
        ProfileMachine::from_source(current_profile(), &source, input.to_vec())
            .map_err(|error| error.to_string())?;
    let mut first_memory = None;
    let mut second_memory = None;
    let mut boundaries = Vec::new();
    for step in 0..STEPS {
        if vm.registers().code_pointer == ENTRY {
            boundaries.push((
                step,
                vm.registers(),
                vm.input_consumed(),
                vm.output().len(),
            ));
            if first_memory.is_none() {
                first_memory = Some(vm.memory().to_vec());
            } else {
                second_memory = Some(vm.memory().to_vec());
                break;
            }
        }
        assert_eq!(
            vm.step().map_err(|error| error.to_string())?,
            StepOutcome::Continued,
        );
    }
    let first = first_memory.ok_or_else(|| "no first entry".to_owned())?;
    let second = second_memory.ok_or_else(|| "no second entry".to_owned())?;
    let full_diff: Vec<_> = first
        .iter()
        .zip(&second)
        .enumerate()
        .filter_map(|(address, (before, after))| {
            (before != after).then_some((
                u32::try_from(address).unwrap_or(u32::MAX),
                *before,
                *after,
            ))
        })
        .collect();
    let journal_diff: Vec<_> = window
        .net_changed_words
        .iter()
        .map(|change| (change.address, change.before, change.after))
        .collect();
    assert_eq!(journal_diff, full_diff);
    for dependency in &window.memory_live_ins {
        assert_eq!(
            first
                .get(usize::try_from(dependency.address).unwrap_or(usize::MAX)),
            Some(&dependency.value),
            "live-in value differs from the complete first-entry image",
        );
    }
    assert_eq!(boundaries.len(), 2);
    assert_eq!(window.from.step, boundaries[0].0);
    assert_eq!(window.to.step, boundaries[1].0);
    assert_eq!(window.from.registers, boundaries[0].1);
    assert_eq!(window.to.registers, boundaries[1].1);
    assert_eq!(window.from.input_consumed, boundaries[0].2);
    assert_eq!(window.to.input_consumed, boundaries[1].2);
    assert_eq!(window.from.output_len, boundaries[0].3);
    assert_eq!(window.to.output_len, boundaries[1].3);
    Ok(())
}

#[test]
fn forged_physical_effect_journals_fail_without_a_second_window()
-> Result<(), String> {
    let windows = observe_physical_reentries(
        current_profile(),
        &source()?,
        &[3, 4, 5],
        ENTRY,
        2,
        STEPS,
    )
    .map_err(|error| format!("{error:?}"))?;
    assert_eq!(windows.len(), 1);
    assert_eq!(verify_physical_reentry_chain(&windows), Ok(()));
    let invalid =
        Err(PhysicalReentryChainError::InvalidWindow { window_index: 0 });

    // Boundary-only checking misses invented p/* results, even when no
    // following window exists to expose the false intermediate version.
    let mut false_data = windows.clone();
    let data = false_data[0]
        .data_operations
        .iter_mut()
        .find(|operation| operation.written_value.is_some())
        .ok_or("missing real guest data write")?;
    data.written_value = data.written_value.map(|value| value ^ 1);
    assert_eq!(verify_physical_reentry_chain(&false_data), invalid);

    let mut false_code = windows.clone();
    let code = false_code[0]
        .code_mutations
        .first_mut()
        .ok_or("missing real guest encryption")?;
    code.write.after ^= 1;
    assert_eq!(verify_physical_reentry_chain(&false_code), invalid);

    let mut false_read = windows.clone();
    let read = false_read[0]
        .data_operations
        .iter_mut()
        .find(|operation| operation.written_value.is_some())
        .ok_or("missing real guest operand")?;
    read.read.value ^= 1;
    assert_eq!(verify_physical_reentry_chain(&false_read), invalid);

    let mut phantom_net = windows.clone();
    let unused = current_profile().memory_words() - 1;
    assert!(
        phantom_net[0]
            .net_changed_words
            .iter()
            .all(|w| w.address != unused)
    );
    phantom_net[0].net_changed_words.push(PhysicalWordChange {
        address: unused,
        before: 134,
        after: 135,
    });
    assert_eq!(verify_physical_reentry_chain(&phantom_net), invalid);

    let mut false_output = windows.clone();
    false_output[0].io_operations[0].effect = PhysicalIoEffect::Output(0);
    assert_eq!(verify_physical_reentry_chain(&false_output), invalid);
    Ok(())
}

#[test]
fn eof_only_path_does_not_fabricate_a_second_entry() -> Result<(), String> {
    let source = source()?;
    for input in [vec![], vec![3]] {
        assert_eq!(
            observe_physical_reentries(
                current_profile(),
                &source,
                &input,
                ENTRY,
                2,
                STEPS,
            ),
            Err(PhysicalReentryError::MissingReentry),
        );
    }
    Ok(())
}

#[test]
fn rejected_steps_and_finite_bounds_fail_closed() -> Result<(), String> {
    let source = source()?;
    let profile = current_profile();
    let invalid = [
        (0, 2, STEPS),
        (ENTRY, 1, STEPS),
        (ENTRY, 5, STEPS),
        (ENTRY, 2, 0),
        (ENTRY, 2, 2049),
        (profile.memory_words(), 2, STEPS),
    ];
    for (entry, visits, steps) in invalid {
        assert_eq!(
            observe_physical_reentries(
                profile,
                &source,
                &[3, 4, 5],
                entry,
                visits,
                steps,
            ),
            if entry == 0 {
                // C0 is valid, but this path fails before the full budget.
                Err(PhysicalReentryError::GuestStep)
            } else {
                Err(PhysicalReentryError::InvalidRequest)
            },
        );
    }
    assert_eq!(
        observe_physical_reentries(profile, &[], &[], ENTRY, 2, STEPS),
        Err(PhysicalReentryError::InvalidRequest),
    );
    assert_eq!(
        observe_physical_reentries(
            profile,
            &source,
            &vec![0; 2049],
            ENTRY,
            2,
            STEPS,
        ),
        Err(PhysicalReentryError::InvalidRequest),
    );
    assert_eq!(
        observe_physical_reentries(
            profile,
            &vec![b'o'; 4097],
            &[],
            ENTRY,
            2,
            STEPS,
        ),
        Err(PhysicalReentryError::InvalidRequest),
    );
    assert_eq!(
        observe_physical_reentries(profile, &[0, 0], &[], ENTRY, 2, STEPS),
        Err(PhysicalReentryError::GuestLoad),
    );
    assert_eq!(
        observe_physical_reentries(
            profile,
            &source,
            &[3, 4, 5],
            ENTRY,
            3,
            STEPS,
        ),
        Err(PhysicalReentryError::GuestStep),
    );
    Ok(())
}
