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
//   - Outputs: one M95 fold and optional real guest prefix-stream bytes.
//   - Side effects: isolated normative N15 VM traces under 67 steps.
// - Split-When:
//   - The general code/data linker can realize arbitrary fold iterations.
// - Merge-When:
//   - Real C state uses verified physical read/modify/write instructions.
// - Summary:
//   - A parametric physical stream accumulator, not another output fixture.

//! Real guest input folds, stored state and prefix-stream output.

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
    for _ in 0usize..15 {
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

#[expect(
    clippy::excessive_nesting,
    reason = "fixed three-position by eighteen-byte test input generation"
)]
fn cases(events: u8) -> Vec<Vec<u8>> {
    let mut streams =
        vec![vec![], vec![0x42], vec![0, 255], vec![0, 255, 128], vec![
            0, 255, 128, 17,
        ]];
    if events == 3 {
        for position in 0..3 {
            for byte in BOUNDARIES {
                let mut input = vec![0x42, 0x81, 0xc3];
                if let Some(slot) = input.get_mut(position) {
                    *slot = byte;
                }
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
    assert_eq!(
        layout::build_seeded_two_input_prefix_fold_source(
            historical_profile(),
            *b",H",
        ),
        Err(layout::RepeatedLoaderRotationError::UnsupportedProfile),
    );
    assert_eq!(
        layout::build_seeded_two_input_prefix_fold_source(profile, *b"Iy"),
        Err(layout::RepeatedLoaderRotationError::InvalidResetSeed {
            tail: *b"Iy",
        }),
    );
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
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
                    let step =
                        trace.get(position).ok_or("missing guest rotation")?;
                    assert_eq!(step.decoded, Some(b'*'));
                    assert_eq!(step.before.registers.data_pointer, TARGET);
                    assert_eq!(
                        step.memory_reads.data.map(|cell| cell.value),
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
                    let read =
                        trace.get(input_at).ok_or("missing guest input")?;
                    assert_eq!(read.decoded, Some(profile.input_instruction()));
                    assert_eq!(read.before.registers.data_pointer, TARGET);
                    assert_eq!(read.input, Some(expected_input));
                    let reset_at = input_at + 1;
                    for (offset, address, word) in
                        [(0usize, 96u32, 72u32), (1, 73, 61), (2, 62, 94)]
                    {
                        let reset = trace
                            .get(reset_at + offset)
                            .ok_or("missing reset")?;
                        assert_eq!(reset.decoded, Some(b'j'));
                        assert_eq!(
                            reset.before.registers.data_pointer,
                            address
                        );
                        assert_eq!(
                            reset.memory_reads.data.map(|cell| cell.value),
                            Some(word)
                        );
                    }
                    let update =
                        trace.get(input_at + 4).ok_or("missing guest write")?;
                    let next = crazy(state, input_word);
                    assert_eq!(update.decoded, Some(b'p'));
                    assert_eq!(update.before.registers.data_pointer, TARGET);
                    assert_eq!(
                        update.memory_reads.data.map(|cell| cell.value),
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
                            let reset = trace
                                .get(input_at + 5 + offset)
                                .ok_or("missing next reset")?;
                            assert_eq!(reset.decoded, Some(b'j'));
                            assert_eq!(
                                reset.before.registers.data_pointer,
                                address
                            );
                            assert_eq!(
                                reset.memory_reads.data.map(|cell| cell.value),
                                Some(word)
                            );
                        }
                    }
                }
                let output_at = 44 + (usize::from(events) - 1) * 8;
                let byte = u8::try_from(state % 256)
                    .map_err(|error| error.to_string())?;
                assert_eq!(
                    trace.get(output_at).and_then(|step| step.output),
                    Some(byte)
                );
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
#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded full VM parity assertions return a diagnostic on mismatch"
)]
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
            vm.run(62).map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 62
            }
        );
        _ = outputs.insert(vm.output().to_vec());
        _ = data_words
            .insert(vm.memory_word(TARGET).map_err(|error| error.to_string())?);
    }
    assert!(outputs.len() > 1);
    assert!(data_words.len() > 1);
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "independent oracle checks both reached guest output events"
)]
fn two_guest_inputs_emit_mutable_state_prefixes() -> Result<(), String> {
    let profile = current_profile();
    let mut paths = 0usize;
    for (tail, initial) in [(*b",H", 7_174_457u32), (*b"CH", 7_174_480)] {
        let source =
            layout::build_seeded_two_input_prefix_fold_source(profile, tail)
                .map_err(|error| format!("{error:?}"))?;
        assert_eq!(source.len(), 91);
        assert_eq!(source.get(89..), Some(tail.as_slice()));
        let loaded = ProfileMachine::from_source(profile, &source, vec![])
            .map_err(|error| error.to_string())?;
        let prepared = (0..9usize).fold(initial, |state, _| rotated(state));
        let streams = [vec![], vec![0x81], vec![0x81, 0xc3, 0x17]]
            .into_iter()
            .chain(BOUNDARIES.map(|first| vec![first, 0x81]))
            .chain(BOUNDARIES.map(|second| vec![0x42, second]));
        for input in streams {
            let first = crazy(
                prepared,
                input.first().map_or_else(
                    || profile.eof_word(),
                    |byte| u32::from(*byte),
                ),
            );
            let second = crazy(
                first,
                input.get(1).map_or_else(
                    || profile.eof_word(),
                    |byte| u32::from(*byte),
                ),
            );
            let expected = [
                u8::try_from(first % 256).map_err(|error| error.to_string())?,
                u8::try_from(second % 256)
                    .map_err(|error| error.to_string())?,
            ];
            let mut vm = ProfileMachine::from_state(
                profile,
                loaded.memory().to_vec(),
                input.clone(),
                ProfileRegisters::default(),
            )
            .map_err(|error| error.to_string())?;
            let mut trace = Vec::new();
            assert_eq!(
                vm.run_traced(58, &mut |step| trace.push(*step))
                    .map_err(|error| error.to_string())?,
                RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 58,
                }
            );
            for (at, expected_input) in
                [(39usize, input.first()), (51, input.get(1))]
            {
                let event = trace.get(at).ok_or("missing read")?;
                assert_eq!(event.decoded, Some(profile.input_instruction()));
                assert_eq!(event.before.registers.data_pointer, TARGET);
                assert_eq!(
                    event.input,
                    Some(
                        expected_input
                            .copied()
                            .map_or(TraceInput::EndOfInput, TraceInput::Byte,)
                    )
                );
            }
            for (at, old, new) in
                [(43usize, prepared, first), (55, first, second)]
            {
                let event = trace.get(at).ok_or("missing state update")?;
                assert_eq!(event.decoded, Some(b'p'));
                assert_eq!(event.before.registers.data_pointer, TARGET);
                assert_eq!(
                    event.memory_reads.data.map(|cell| cell.value),
                    Some(old)
                );
                assert_eq!(event.after.registers.accumulator, new);
                assert_eq!(
                    event.memory_delta.data.map(|delta| {
                        (delta.address, delta.before, delta.after)
                    }),
                    (old != new).then_some((TARGET, old, new)),
                );
            }
            for (at, address, word) in [
                (40usize, 96u32, 72u32),
                (41, 73, 61),
                (42, 62, 94),
                (44, 96, 72),
                (45, 73, 61),
                (46, 62, 94),
                (48, 96, 72),
                (49, 73, 61),
                (50, 62, 94),
                (52, 96, 72),
                (53, 73, 61),
                (54, 62, 94),
            ] {
                let reset = trace.get(at).ok_or("missing reset")?;
                assert_eq!(reset.decoded, Some(b'j'));
                assert_eq!(reset.before.registers.data_pointer, address);
                assert_eq!(
                    reset.memory_reads.data.map(|cell| cell.value),
                    Some(word)
                );
            }
            for (at, byte) in [(47usize, expected[0]), (56, expected[1])] {
                let output = trace.get(at).ok_or("missing prefix output")?;
                assert_eq!(output.decoded, Some(profile.output_instruction()));
                assert_eq!(output.output, Some(byte));
            }
            assert_eq!(vm.output(), &expected);
            assert_eq!(vm.memory_word(TARGET), Ok(second));
            assert_eq!(vm.input_consumed(), input.len().min(2));
            paths += 1;
        }
    }
    assert_eq!(paths, 78);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "cross-seed guest trace parity with the independent trit oracle"
)]
fn all_loader_compatible_prefix_fold_seeds_reach_both_outputs()
-> Result<(), String> {
    let profile = current_profile();
    // Each graphical tail yields M96=72. The first two are fully traced by
    // the 78-path test; these six independently probe the remaining seeds.
    let seeds = [
        (*b"-H", 7_174_462u32),
        (*b"IH", 7_174_489),
        (*b"VH", 7_174_418),
        (*b"gH", 7_174_435),
        (*b"hH", 7_174_436),
        (*b"zH", 7_174_454),
    ];
    let mut paths = 0usize;
    for (tail, starting_word) in seeds {
        let source =
            layout::build_seeded_two_input_prefix_fold_source(profile, tail)
                .map_err(|error| format!("{error:?}"))?;
        let loaded = ProfileMachine::from_source(profile, &source, vec![])
            .map_err(|error| error.to_string())?;
        assert_eq!(loaded.memory_word(TARGET), Ok(starting_word));
        let prepared =
            (0..9usize).fold(starting_word, |state, _| rotated(state));
        for input in [vec![], vec![0], vec![0xff, 1], vec![0x81], vec![
            0x42, 0x80, 0x17,
        ]] {
            let first_input = input
                .first()
                .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
            let second_input = input
                .get(1)
                .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
            let first_state = crazy(prepared, first_input);
            let last_state = crazy(first_state, second_input);
            let expected = [
                u8::try_from(first_state % 256)
                    .map_err(|error| error.to_string())?,
                u8::try_from(last_state % 256)
                    .map_err(|error| error.to_string())?,
            ];
            let mut vm = ProfileMachine::from_state(
                profile,
                loaded.memory().to_vec(),
                input.clone(),
                ProfileRegisters::default(),
            )
            .map_err(|error| error.to_string())?;
            assert_eq!(
                vm.run(58).map_err(|error| error.to_string())?,
                RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 58,
                }
            );
            assert_eq!(vm.output(), &expected);
            assert_eq!(vm.memory_word(TARGET), Ok(last_state));
            assert_eq!(vm.input_consumed(), input.len().min(2));
            paths += 1;
        }
    }
    assert_eq!(paths, 30);
    Ok(())
}

#[test]
fn checkpoint_reset_refuses_unproved_source_seed_and_profile() {
    let profile = current_profile();
    assert_eq!(
        layout::build_seeded_three_input_checkpoint_fold_source(
            historical_profile(),
            *b",B",
        ),
        Err(layout::RepeatedLoaderRotationError::UnsupportedProfile),
    );
    for tail in [*b",H", *b"Iy", [0u8, b'B']] {
        assert_eq!(
            layout::build_seeded_three_input_checkpoint_fold_source(
                profile, tail,
            ),
            Err(layout::RepeatedLoaderRotationError::InvalidResetSeed { tail }),
        );
    }
    // Existing eight-tail reset admission remains exactly unchanged.
    assert_eq!(
        layout::build_seeded_guest_input_state_fold_source(profile, *b",B", 3,),
        Err(layout::RepeatedLoaderRotationError::InvalidResetSeed {
            tail: *b",B",
        }),
    );
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "independent traced inputs, writes, resets, and outputs"
)]
fn relocated_reset_preserves_guest_checkpoint_across_two_later_updates()
-> Result<(), String> {
    let profile = current_profile();
    let mut checked = 0usize;
    for (tail, initial) in [(*b",B", 7_174_448u32), (*b"CB", 7_174_468)] {
        let source = layout::build_seeded_three_input_checkpoint_fold_source(
            profile, tail,
        )
        .map_err(|error| format!("{error:?}"))?;
        assert_eq!(source.len(), 91);
        assert_eq!(source.get(89..), Some(tail.as_slice()));
        assert_eq!((source[67], source[68]), (67, 94));
        assert_ne!(source[62], 94);
        let loaded = ProfileMachine::from_source(profile, &source, vec![])
            .map_err(|error| error.to_string())?;
        assert_eq!(loaded.memory_word(TARGET), Ok(initial));
        assert_eq!(loaded.memory_word(96), Ok(66));
        let prepared = (0..9usize).fold(initial, |word, _| rotated(word));
        let mut streams =
            vec![vec![], vec![0x81], vec![0, 255], vec![0, 255, 128], vec![
                0, 255, 128, 17,
            ]];
        for position in 0..3 {
            for byte in [0u8, 1, 127, 128, 254, 255] {
                let mut input = vec![0x42, 0x81, 0xc3];
                let slot =
                    input.get_mut(position).ok_or("missing input slot")?;
                *slot = byte;
                streams.push(input);
            }
        }
        for input in streams {
            let mut states = [0u32; 3];
            let mut state = prepared;
            for (position, value) in states.iter_mut().enumerate() {
                let byte = input.get(position).map_or_else(
                    || profile.eof_word(),
                    |byte| u32::from(*byte),
                );
                state = crazy(state, byte);
                *value = state;
            }
            let expected = [
                u8::try_from(states[0] % 256).map_err(|e| e.to_string())?,
                u8::try_from(states[2] % 256).map_err(|e| e.to_string())?,
            ];
            let mut vm = ProfileMachine::from_state(
                profile,
                loaded.memory().to_vec(),
                input.clone(),
                ProfileRegisters::default(),
            )
            .map_err(|error| error.to_string())?;
            let mut trace = Vec::new();
            assert_eq!(
                vm.run_traced(66, &mut |step| trace.push(*step))
                    .map_err(|error| error.to_string())?,
                RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 66,
                }
            );
            for (at, position) in [(39usize, 0usize), (51, 1), (59, 2)] {
                let step = trace.get(at).ok_or("missing input trace")?;
                assert_eq!(step.decoded, Some(profile.input_instruction()));
                assert_eq!(step.before.registers.data_pointer, TARGET);
                assert_eq!(
                    step.input,
                    Some(
                        input
                            .get(position)
                            .copied()
                            .map_or(TraceInput::EndOfInput, TraceInput::Byte,)
                    ),
                );
            }
            for (at, before, after) in [
                (43usize, prepared, states[0]),
                (55, states[0], states[1]),
                (63, states[1], states[2]),
            ] {
                let step = trace.get(at).ok_or("missing write trace")?;
                assert_eq!(step.decoded, Some(b'p'));
                assert_eq!(step.before.registers.data_pointer, TARGET);
                assert_eq!(
                    step.memory_reads.data.map(|read| read.value),
                    Some(before)
                );
                assert_eq!(step.after.registers.accumulator, after);
                assert_eq!(
                    step.memory_delta.data.map(|delta| {
                        (delta.address, delta.before, delta.after)
                    }),
                    (before != after).then_some((TARGET, before, after)),
                );
            }
            for start in [36usize, 40, 44, 48, 52, 56, 60] {
                for (offset, pointer, word) in
                    [(0usize, 96u32, 66u32), (1, 67, 67), (2, 68, 94)]
                {
                    let step = trace
                        .get(start + offset)
                        .ok_or("missing reset trace")?;
                    assert_eq!(step.decoded, Some(b'j'));
                    assert_eq!(step.before.registers.data_pointer, pointer);
                    assert_eq!(
                        step.memory_reads.data.map(|read| read.value),
                        Some(word),
                    );
                }
            }
            for (at, byte) in [(47usize, expected[0]), (64, expected[1])] {
                let step = trace.get(at).ok_or("missing output trace")?;
                assert_eq!(step.decoded, Some(profile.output_instruction()));
                assert_eq!(step.output, Some(byte));
            }
            assert_eq!(vm.output(), &expected);
            assert_eq!(vm.memory_word(TARGET), Ok(states[2]));
            assert_eq!(vm.memory_word(67), Ok(67));
            assert_eq!(vm.memory_word(68), Ok(94));
            assert_eq!(vm.input_consumed(), input.len().min(3));
            checked += 1;
        }
    }
    assert_eq!(checked, 46);
    Ok(())
}
