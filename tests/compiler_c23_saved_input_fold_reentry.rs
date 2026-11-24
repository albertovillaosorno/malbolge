// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier: Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Source-valid N15 guest fold of live second input with saved first state.
// - Must-Not:
//   - Claim source-C signed EOF conversion, mutable checksum or CFG linkage.
// - Allows:
//   - Inputs: finite real guest bytes/EOF and source-loaded code cells.
//   - Outputs: exact VM state, physical crazy result, output and valid halt.
//   - Side effects: isolated normative VM execution only.
// - Split-When:
//   - The general C23 guest arithmetic/control linker subsumes this primitive.
// - Merge-When:
//   - A source-locked reusable guest two-input primitive exists.
// - Summary:
//   - Data-dependent guest computation followed by encrypted-code reentry.

//! Two genuine inputs, a saved state-dependent crazy operation and a real halt.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::iter::once;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction,
};

fn graphical(position: u32, opcode: u8) -> Option<u8> {
    (33..=126u8).find(|byte| {
        decode_profile_instruction(u32::from(*byte), position) == Some(opcode)
    })
}

#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "a frozen source-defined 135-cell physical experiment"
)]
fn saved_input_fold_source() -> Vec<u8> {
    let mut source = (0..135u32)
        .map(|at| graphical(at, b'o').expect("valid source no-op"))
        .collect::<Vec<_>>();
    for (position, opcode) in [
        (10u32, b'/'),
        (11, b'<'),
        (29, b'j'),
        (30, b'p'),
        (58, b'j'),
        (59, b'j'),
        (82, b'/'),
        (83, b'j'),
        (84, b'j'),
        (85, b'j'),
        (86, b'j'),
        (87, b'p'),
        (88, b'<'),
        (89, b'j'),
        (90, b'j'),
        (91, b'j'),
        (92, b'j'),
        (93, b'j'),
        (94, b'i'),
    ] {
        source[usize::try_from(position).expect("bounded code position")] =
            graphical(position, opcode).expect("source-valid code opcode");
    }
    for (position, value) in [
        (95usize, 97u8),
        (98, 36),
        (99, 94),
        (100, 93),
        (101, 110),
        (104, 123),
        (106, 121),
        (108, 103),
        (111, 81),
        (124, 126),
        (127, 100),
        (134, 58),
    ] {
        source[position] = value;
    }
    layout::admit_c23_probe_graphical_source(&source)
        .expect("entire positional source is admissible");
    source
}

// Independent finite ternary arithmetic; never use the production VM crazy
// primitive to predict the candidate output.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "fifteen fixed ternary places form the independent scalar oracle"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut result = 0u32;
    let mut place = 1u32;
    for _ in 0..15u8 {
        let digit = match (data % 3, accumulator % 3) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        result += digit * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "small finite original physical guest stage-and-halt trace"
)]
fn source_loaded_second_input_folds_saved_first_word_before_valid_halt() {
    let source = saved_input_fold_source();
    assert_eq!(source.len(), 135);
    let profile = current_profile();
    let pristine = ProfileMachine::from_source(profile, &source, vec![])
        .expect("source-loaded normative N15 machine");
    for input in [
        vec![],
        vec![0],
        vec![255],
        vec![0, 0],
        vec![3, 4],
        vec![255, 0],
        vec![0, 255],
        vec![0x80, 0x7f],
        vec![0x7f, 0x80, 1],
    ] {
        let first = input
            .first()
            .map_or_else(|| profile.eof_word(), |value| u32::from(*value));
        let second = input
            .get(1)
            .map_or_else(|| profile.eof_word(), |value| u32::from(*value));
        let saved = scalar_crazy(121, first);
        let folded = scalar_crazy(saved, second);
        let mut machine = pristine
            .fork_with_input(input.clone())
            .expect("fresh guest input");
        let mut trace = Vec::new();
        assert_eq!(
            machine.run_traced(100, &mut |step| trace.push(*step)),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 96,
            }),
            "stdin={input:?}; steps={:?}",
            trace
                .iter()
                .enumerate()
                .skip(78)
                .map(|(at, step)| (
                    at,
                    step.before.registers.code_pointer,
                    step.before.registers.data_pointer,
                    step.decoded,
                    step.memory_reads.data,
                ))
                .collect::<Vec<_>>()
        );
        assert_eq!(machine.input_consumed(), input.len().min(2));
        assert_eq!(machine.output(), [
            u8::try_from(first % 256).expect("first low byte"),
            u8::try_from(folded % 256).expect("fold low byte"),
        ]);
        assert_eq!(
            trace[10].input,
            Some(input.first().map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            },))
        );
        assert_eq!(
            trace[82].input,
            Some(input.get(1).map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            },))
        );
        assert_eq!(
            trace[30].memory_delta.data.map(|delta| (
                delta.address,
                delta.before,
                delta.after
            )),
            Some((106, 121, saved))
        );
        assert_eq!(
            trace[87]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((106, saved))
        );
        // C37 executed as a source no-op on the first pass, encrypting
        // its own code word into a real pointer literal. C86 reads that
        // encrypted cell, not a host-selected pointer for the second p.
        assert_eq!(trace[37].decoded, Some(b'o'));
        assert_eq!(machine.memory_word(37), Ok(105));
        for (index, address, value) in [
            (83, 99, 94),
            (84, 95, 97),
            (85, 98, 36),
            (86, 37, 105),
            (89, 108, 103),
            (90, 104, 123),
            (91, 124, 126),
            (92, 127, 100),
            (93, 101, 110),
            (94, 111, 81),
        ] {
            assert_eq!(
                trace[index]
                    .memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, value)),
                "stdin={input:?} step={index}"
            );
        }
        assert_eq!(trace[87].decoded, Some(b'p'));
        assert_eq!(trace[87].after.registers.accumulator, folded);
        // A same-value physical p has no memory delta, but still reads the
        // live saved source word and puts the folded word in A.
        assert_eq!(
            trace[87].memory_delta.data.map(|delta| (
                delta.address,
                delta.before,
                delta.after
            )),
            (saved != folded).then_some((106, saved, folded))
        );
        assert_eq!(
            trace[88].output,
            Some(u8::try_from(folded % 256).expect("fold"))
        );
        assert_eq!(machine.memory_word(106), Ok(folded));
        assert_eq!(trace[95].before.registers.code_pointer, 82);
        assert_eq!(trace[95].decoded, Some(b'v'));
    }
}

// The exact source-loaded machine is replayed against both full byte
// marginals plus the distinct raw N15 EOF sentinel. These are runtime
// inputs; neither the source nor the saved state is specialized per byte.
#[test]
#[expect(
    clippy::expect_used,
    clippy::integer_division_remainder_used,
    clippy::cognitive_complexity,
    reason = "exhaustive finite 257+257 class guest-input counterexamples"
)]
fn two_real_input_marginals_preserve_the_saved_state_fold() {
    let profile = current_profile();
    let source = saved_input_fold_source();
    let pristine = ProfileMachine::from_source(profile, &source, vec![])
        .expect("source-loaded normative machine");
    for first_fixed in [true, false] {
        for raw in (0..=255u32).chain(once(profile.eof_word())) {
            let first = if first_fixed {
                5
            } else {
                raw
            };
            let second = if first_fixed {
                raw
            } else {
                profile.eof_word()
            };
            let input = if first_fixed {
                if raw == profile.eof_word() {
                    vec![5]
                } else {
                    vec![5, u8::try_from(raw).expect("raw byte")]
                }
            } else if raw == profile.eof_word() {
                vec![]
            } else {
                vec![u8::try_from(raw).expect("raw byte")]
            };
            let saved = scalar_crazy(121, first);
            let folded = scalar_crazy(saved, second);
            let mut machine = pristine
                .fork_with_input(input.clone())
                .expect("fresh N15 input");
            assert_eq!(
                machine.run(100),
                Ok(RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 96,
                }),
                "first_fixed={first_fixed} raw={raw}"
            );
            assert_eq!(machine.input_consumed(), input.len().min(2));
            assert_eq!(machine.output(), [
                u8::try_from(first % 256).expect("first byte"),
                u8::try_from(folded % 256).expect("folded byte"),
            ]);
            assert_eq!(machine.memory_word(106), Ok(folded));
        }
    }
}

// Each source-valid mutation removes an essential physical participant;
// matching output, real 2-stage state fold and valid terminal together
// must never be inferred after the guest computation or control is missing.
#[test]
#[expect(
    clippy::expect_used,
    clippy::integer_division_remainder_used,
    clippy::indexing_slicing,
    reason = "five bounded source-valid negative controls"
)]
fn forged_primitive_cannot_preserve_all_output_state_and_halt_obligations() {
    let profile = current_profile();
    let source = saved_input_fold_source();
    let input = vec![2, 4];
    let folded = scalar_crazy(scalar_crazy(121, 2), 4);
    for (position, opcode) in [
        (30usize, b'o'),
        (86, b'o'),
        (87, b'o'),
        (94, b'o'),
        (111, b'o'),
    ] {
        let mut altered = source.clone();
        altered[position] =
            graphical(u32::try_from(position).expect("bounded"), opcode)
                .expect("valid graphical mutation");
        layout::admit_c23_probe_graphical_source(&altered)
            .expect("source-valid adversarial mutation");
        let mut machine =
            ProfileMachine::from_source(profile, &altered, input.clone())
                .expect("normative altered source");
        let reached = machine.run(100);
        let complete = reached
            == Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 96,
            })
            && machine.input_consumed() == 2
            && machine.output()
                == [2, u8::try_from(folded % 256).expect("fold byte")]
            && machine.memory_word(106) == Ok(folded);
        assert!(!complete, "mutation at position {position} succeeded");
    }
}

// The fold is not merely another echo: changing either runtime input alone
// can alter the second guest output without changing its source bytes.
#[test]
#[expect(
    clippy::expect_used,
    reason = "three finite source-identical guest executions"
)]
fn guest_fold_second_output_depends_on_both_physical_inputs() {
    let profile = current_profile();
    let source = saved_input_fold_source();
    let pristine = ProfileMachine::from_source(profile, &source, vec![])
        .expect("canonical source-loaded VM");
    let outcomes = [[2u8, 0u8], [13, 0], [2, 2]].map(|input| {
        let mut machine = pristine
            .fork_with_input(input.to_vec())
            .expect("fresh two-byte input");
        assert_eq!(
            machine.run(100),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 96,
            })
        );
        (
            machine.output().get(1).copied().expect("computed byte"),
            machine.memory_word(106).expect("saved fold"),
        )
    });
    assert_ne!(outcomes.first(), outcomes.get(1));
    assert_ne!(outcomes.first(), outcomes.get(2));
}
