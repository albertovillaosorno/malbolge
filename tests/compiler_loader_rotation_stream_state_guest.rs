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
//   - Normative guest proof of a bounded, repeatable input-driven state fold.
// - Must-Not:
//   - Claim C23 EOF normalization, C integer arithmetic or a dynamic C loop.
// - Allows:
//   - Inputs: 1..3 signed read events and exact graphical loader seeds.
//   - Outputs: traced writes to one M95 cell and independent trit oracles.
//   - Side effects: isolated normative N15 VM traces under 62 steps.
// - Split-When:
//   - The general code/data linker can realize arbitrary fold iterations.
// - Merge-When:
//   - Real C state uses verified physical read/modify/write instructions.
// - Summary:
//   - A parametric physical stream accumulator, not another output fixture.

//! Sequential input events really update and reread one guest data cell.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, historical_profile,
};

const TARGET: u32 = 95;
const BOUNDARIES: [u8; 18] = [
    0, 1, 2, 3, 7, 15, 31, 63, 64, 65, 95, 127, 128, 129, 191, 223, 254, 255,
];

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "independent fixed-width fifteen-trit rotation formula"
)]
const fn rotated(word: u32) -> u32 {
    word / 3 + word % 3 * 4_782_969
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent positional truth table for fifteen-trit crazy"
)]
fn crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut result = 0;
    let mut place = 1;
    for _ in 0..15 {
        let trit = match (data % 3, accumulator % 3) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        result += trit * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

fn cases(events: u8) -> Vec<Vec<u8>> {
    let mut streams =
        vec![vec![], vec![0x42], vec![0, 255], vec![0, 255, 128], vec![
            0, 255, 128, 17,
        ]];
    if events == 3 {
        for position in 0..3 {
            for byte in BOUNDARIES {
                let mut input = vec![0x42, 0x81, 0xc3];
                input[position] = byte;
                streams.push(input);
            }
        }
    }
    streams
}

#[test]
fn bounded_guest_fold_refuses_unproved_count_profile_and_seed() {
    let profile = current_profile();
    for inputs in [0u8, 4, 7, 255] {
        assert_eq!(
            layout::build_seeded_guest_input_state_fold_source(
                profile, *b",H", inputs,
            ),
            Err(layout::RepeatedLoaderRotationError::InvalidInputCount {
                inputs,
            }),
        );
    }
    assert_eq!(
        layout::build_seeded_guest_input_state_fold_source(
            historical_profile(),
            *b",H",
            3,
        ),
        Err(layout::RepeatedLoaderRotationError::UnsupportedProfile),
    );
    assert_eq!(
        layout::build_seeded_guest_input_state_fold_source(profile, *b"Iy", 3,),
        Err(layout::RepeatedLoaderRotationError::InvalidResetSeed {
            tail: *b"Iy",
        }),
    );
    assert_eq!(
        layout::build_seeded_guest_input_state_fold_source(profile, *b",H", 2,),
        layout::build_seeded_two_input_state_update_source(profile, *b",H"),
    );
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "each physical read and state write has an independent oracle"
)]
fn real_guest_folds_one_to_three_separate_inputs_into_one_memory_word()
-> Result<(), String> {
    let profile = current_profile();
    let mut checked = 0usize;
    for (tail, starting_word) in [(*b",H", 7_174_457u32), (*b"CH", 7_174_480)] {
        for events in 1u8..=3 {
            let source = layout::build_seeded_guest_input_state_fold_source(
                profile, tail, events,
            )
            .map_err(|error| format!("{error:?}"))?;
            assert_eq!(source.len(), 91);
            assert_eq!(source.get(89..), Some(tail.as_slice()));
            let loaded = ProfileMachine::from_source(profile, &source, vec![])
                .map_err(|error| error.to_string())?;
            assert_eq!(loaded.memory_word(TARGET), Ok(starting_word));
            for input in cases(events) {
                let mut vm = ProfileMachine::from_state(
                    profile,
                    loaded.memory().to_vec(),
                    input.clone(),
                    ProfileRegisters::default(),
                )
                .map_err(|error| error.to_string())?;
                let mut trace = Vec::new();
                let steps = 46 + (usize::from(events) - 1) * 8;
                let outcome = vm
                    .run_traced(steps, &mut |step| trace.push(*step))
                    .map_err(|error| error.to_string())?;
                assert_eq!(outcome, RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps,
                });
                assert_eq!(trace.len(), steps);
                let mut state = starting_word;
                for position in [3usize, 7, 11, 15, 19, 23, 27, 31, 35] {
                    let step = &trace[position];
                    assert_eq!(step.decoded, Some(b'*'));
                    assert_eq!(step.before.registers.data_pointer, TARGET);
                    assert_eq!(
                        step.memory_reads.data.map(|r| r.value),
                        Some(state)
                    );
                    state = rotated(state);
                    assert_eq!(step.after.registers.accumulator, state);
                }
                for event in 0..usize::from(events) {
                    let input_at = 39 + event * 8;
                    let input_word = input
                        .get(event)
                        .copied()
                        .map_or_else(|| profile.eof_word(), u32::from);
                    let expected_input = input
                        .get(event)
                        .copied()
                        .map_or(TraceInput::EndOfInput, TraceInput::Byte);
                    let read = &trace[input_at];
                    assert_eq!(read.decoded, Some(profile.input_instruction()));
                    assert_eq!(read.before.registers.data_pointer, TARGET);
                    assert_eq!(read.input, Some(expected_input));
                    let reset_at = input_at + 1;
                    for (offset, address, word) in
                        [(0usize, 96u32, 72u32), (1, 73, 61), (2, 62, 94)]
                    {
                        let reset = &trace[reset_at + offset];
                        assert_eq!(reset.decoded, Some(b'j'));
                        assert_eq!(
                            reset.before.registers.data_pointer,
                            address
                        );
                        assert_eq!(
                            reset.memory_reads.data.map(|r| r.value),
                            Some(word)
                        );
                    }
                    let update = &trace[input_at + 4];
                    let next = crazy(state, input_word);
                    assert_eq!(update.decoded, Some(b'p'));
                    assert_eq!(update.before.registers.data_pointer, TARGET);
                    assert_eq!(
                        update.memory_reads.data.map(|r| r.value),
                        Some(state)
                    );
                    assert_eq!(update.after.registers.accumulator, next);
                    assert_eq!(
                        update.memory_delta.data.map(|delta| {
                            (delta.address, delta.before, delta.after)
                        }),
                        (state != next).then_some((TARGET, state, next))
                    );
                    state = next;
                    if event + 1 < usize::from(events) {
                        for (offset, address, word) in
                            [(0usize, 96u32, 72u32), (1, 73, 61), (2, 62, 94)]
                        {
                            let reset = &trace[input_at + 5 + offset];
                            assert_eq!(reset.decoded, Some(b'j'));
                            assert_eq!(
                                reset.before.registers.data_pointer,
                                address
                            );
                            assert_eq!(
                                reset.memory_reads.data.map(|r| r.value),
                                Some(word)
                            );
                        }
                    }
                }
                let output_at = 44 + (usize::from(events) - 1) * 8;
                let byte = u8::try_from(state % 256)
                    .map_err(|error| error.to_string())?;
                assert_eq!(trace[output_at].output, Some(byte));
                assert_eq!(vm.output(), &[byte]);
                assert_eq!(vm.memory_word(TARGET), Ok(state));
                assert_eq!(
                    vm.input_consumed(),
                    input.len().min(usize::from(events))
                );
                checked += 1;
            }
        }
    }
    // Two independent loader seeds and all bounded truncation/binary classes.
    assert_eq!(checked, 138);
    Ok(())
}

#[test]
fn third_input_really_affects_guest_state_not_only_the_output_position()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_seeded_guest_input_state_fold_source(profile, *b",H", 3)
            .map_err(|error| format!("{error:?}"))?;
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    let mut outputs = BTreeSet::new();
    let mut data_words = BTreeSet::new();
    for byte in BOUNDARIES {
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            vec![0x42, 0x81, byte],
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        assert_eq!(
            vm.run(62).map_err(|e| e.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 62
            }
        );
        _ = outputs.insert(vm.output().to_vec());
        _ = data_words
            .insert(vm.memory_word(TARGET).map_err(|e| e.to_string())?);
    }
    assert!(outputs.len() > 1);
    assert!(data_words.len() > 1);
    Ok(())
}
