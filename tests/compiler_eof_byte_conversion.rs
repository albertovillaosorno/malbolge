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
//   - Exhaustive 257-case C23 signed getchar-to-putchar ternary-word proof.
// - Must-Not:
//   - Mistake a scalar conversion plan for executable source-cell placement.
// - Allows:
//   - Inputs: 256 successful byte words and the N15 EOF sentinel.
//   - Outputs: admitted operand plan or precise byte/EOF failure.
//   - Side effects: none; all checks are deterministic pure arithmetic.
// - Split-When:
//   - Layout assigns and replays both real crazy operand data cells.
// - Merge-When:
//   - Guest C stdio realizes and checks signed EOF conversion end to end.
// - Summary:
//   - Separates proof of correct crazy words from real guest implementation.

//! A bounded algebraic prerequisite, not a proof of guest-executable C I/O.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use layout::{
    C23SignedOutputWordPlanError, CURRENT_C23_SIGNED_OUTPUT_WORDS,
    admit_c23_signed_output_word_plan,
};
use malbolge::{current_profile, historical_profile, profile_crazy};

fn scalar_crazy(data: u32, accumulator: u32, trits: u8) -> u32 {
    let mut accumulator_word = accumulator;
    let mut data_word = data;
    let mut place = 1u32;
    let mut output = 0u32;
    for _ in 0..trits {
        let value = match (data_word % 3, accumulator_word % 3) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        output += value * place;
        place *= 3;
        data_word /= 3;
        accumulator_word /= 3;
    }
    output
}

#[test]
fn two_real_crazy_operand_words_cover_every_c23_getchar_outcome() {
    let profile = current_profile();
    let plan = admit_c23_signed_output_word_plan(
        profile,
        CURRENT_C23_SIGNED_OUTPUT_WORDS,
    )
    .expect("the complete C23 signed byte conversion must be verified");
    assert_eq!(plan.operands(), [87_844, 2_551]);
    for input in 0..=256u32 {
        let (machine_input, expected) = if input == 256 {
            (profile.eof_word(), 255u8)
        } else {
            (input, input as u8)
        };
        let [first, second] = plan.operands();
        let intermediate = scalar_crazy(first, machine_input, 15);
        let result = scalar_crazy(second, intermediate, 15);
        assert_eq!(
            profile_crazy(first, machine_input, 15),
            intermediate,
            "intermediate VM primitive disagrees with scalar C23 oracle"
        );
        assert_eq!(
            profile_crazy(second, intermediate, 15),
            result,
            "final VM primitive disagrees with scalar C23 oracle"
        );
        assert_eq!(
            (result % 256) as u8,
            expected,
            "wrong C23 unsigned-char conversion for input {input}"
        );
    }
    assert_ne!(profile.eof_word() % 256, 255);
}

#[test]
fn wrong_or_unplaceable_operands_do_not_acquire_a_conversion_proof() {
    let profile = current_profile();
    assert_eq!(
        admit_c23_signed_output_word_plan(
            historical_profile(),
            CURRENT_C23_SIGNED_OUTPUT_WORDS,
        ),
        Err(C23SignedOutputWordPlanError::UnsupportedProfile),
    );
    assert_eq!(
        admit_c23_signed_output_word_plan(profile, [
            profile.word_modulus(),
            2_551
        ],),
        Err(C23SignedOutputWordPlanError::InvalidOperand),
    );
    for operands in [[87_844, 2_552], [87_845, 2_551], [2_551, 87_844], [0, 0]]
    {
        assert!(
            admit_c23_signed_output_word_plan(profile, operands).is_err(),
            "mutation unexpectedly preserved all C23 outcomes: {operands:?}"
        );
    }
}

// A candidate only converts C23 signed getchar if *every* successful
// byte and EOF has the exact putchar unsigned-char result.
fn converts_c23_getchar_to_putchar(
    operands: &[u32],
    trits: u8,
    eof: u32,
) -> bool {
    (0..=256u32).all(|input| {
        let word = if input == 256 {
            eof
        } else {
            input
        };
        let result = operands.iter().fold(word, |accumulator, &data| {
            scalar_crazy(data, accumulator, trits)
        });
        result % 256
            == if input == 256 {
                255
            } else {
                input
            }
    })
}

// Screen every untouched loader phase and 2..12 adjacent operands. The
// sample counter is only a filter; a four-sample pass is checked against
// all 257 possible C23 getchar outcomes before it counts as a solution.
fn passive_loader_candidate_counts(
    memory: &[u32; 26],
    trits: u8,
    eof: u32,
) -> ([usize; 11], usize) {
    let mut sample_counts = [0usize; 11];
    let mut complete_count = 0usize;
    let samples = [0, 1, 255, eof];
    let expected = [0, 1, 255, 255];
    // Every expanded-word phase repeats every 12 transitions. The first
    // phase begins at address 2, and the 12-word witness stays in bounds.
    for start in 2..14 {
        let mut observed = samples;
        for length in 1..=12usize {
            let operand = memory[start + length - 1];
            for accumulator in &mut observed {
                *accumulator = scalar_crazy(operand, *accumulator, trits);
            }
            if length < 2
                || observed
                    .iter()
                    .zip(expected)
                    .any(|(&value, expected)| value % 256 != expected)
            {
                continue;
            }
            sample_counts[length - 2] += 1;
            if converts_c23_getchar_to_putchar(
                &memory[start..start + length],
                trits,
                eof,
            ) {
                complete_count += 1;
            }
        }
    }
    (sample_counts, complete_count)
}

// The loader's ternary recurrence operates independently on each trit.
// Each ordered pair of trits enters a 2- or 3-cycle after at most one
// transition; the least common period is 6. Exhaust two full periods
// for every graphical seed pair, not just the first expanded cells.
// No guest C output is published by this negative feasibility study.
#[test]
fn passive_loader_words_cannot_convert_signed_eof_in_twelve_crazy_steps() {
    let profile = current_profile();
    let eof = profile.eof_word();
    let mut four_sample_matches = [0usize; 11];
    let mut complete_matches = 0usize;

    for first in 33..=126u32 {
        for second in 33..=126u32 {
            // Positions zero and one are the two graphical source-tail
            // words; all later cells follow the real loader recurrence.
            let mut memory = [0u32; 26];
            memory[0] = first;
            memory[1] = second;
            for index in 2..memory.len() {
                memory[index] = scalar_crazy(
                    memory[index - 2],
                    memory[index - 1],
                    profile.word_trits(),
                );
            }
            assert_eq!(
                &memory[1..14],
                &memory[13..26],
                "graphical tail ({first},{second}) violated the 12-cycle"
            );
            let (sample_counts, complete_count) =
                passive_loader_candidate_counts(
                    &memory,
                    profile.word_trits(),
                    eof,
                );
            for (count, subtotal) in
                four_sample_matches.iter_mut().zip(sample_counts)
            {
                *count += subtotal;
            }
            complete_matches += complete_count;
        }
    }
    assert_eq!(
        four_sample_matches,
        [0, 0, 16, 0, 16, 0, 0, 0, 16, 0, 16],
        "a different loader candidate population requires renewed review"
    );
    assert_eq!(
        complete_matches, 0,
        "an actual passive-loader conversion would need guest layout proof"
    );
}

// A graphical source tail can supply a signed EOF conversion after nine
// exact rotations of one loader-expanded operand. The linker has not
// generated those nine writes or restored D for a subsequent p/p/output.
// This is a constructive pre-layout witness, not a compiled C guest.
#[test]
fn source_loaded_rotated_operands_admit_signed_eof_conversion() {
    let profile = current_profile();
    // Position-dependent XLAT1 admits the tail "Iy" at C=89 and 90.
    // Prepend 89 independently encoded no-ops rather than claiming the
    // graphical loader can start with the invalid source bytes at C=0.
    let mut source = Vec::with_capacity(91);
    for position in 0..89u32 {
        source.push(
            (33..=126u8)
                .find(|cell| {
                    malbolge::decode_profile_instruction(
                        u32::from(*cell),
                        position,
                    ) == Some(b'o')
                })
                .expect("every decode phase has one graphical nop"),
        );
    }
    source.extend_from_slice(b"Iy");
    assert_eq!(malbolge::decode_profile_instruction(73, 89), Some(b'o'),);
    assert_eq!(
        malbolge::decode_profile_instruction(121, 90),
        Some(profile.input_instruction()),
    );
    let machine =
        malbolge::ProfileMachine::from_source(profile, &source, Vec::new())
            .expect("all 91 source cells must load into N15 memory");
    let mut words = [0u32; 8];
    words[0] = 73;
    words[1] = 121;
    for index in 2..words.len() {
        words[index] = scalar_crazy(
            words[index - 2],
            words[index - 1],
            profile.word_trits(),
        );
    }
    for (address, word) in words.iter().copied().enumerate() {
        assert_eq!(
            machine.memory_word(
                u32::try_from(source.len() - 2 + address).unwrap()
            ),
            Ok(word),
            "the normative loader disagrees at address {address}"
        );
    }
    // The same loader word recurs at phase four, immediately before
    // phase five. Thus addresses 95 and 96, unlike 91 and 96, can be
    // consumed by consecutive p steps once the nine writes are realized.
    assert_eq!(words[6], words[2]);
    assert_eq!(words[7], 121);
    assert_eq!(machine.memory_word(95), Ok(words[6]));
    assert_eq!(machine.memory_word(96), Ok(words[7]));
    let mut first = words[6];
    for _ in 0..9 {
        let independently_rotated = first.div_euclid(3)
            + first.rem_euclid(3) * profile.word_modulus().div_euclid(3);
        assert_eq!(
            malbolge::profile_rotate(first, profile.word_modulus()),
            independently_rotated,
        );
        first = independently_rotated;
    }
    let second = words[7];
    assert_eq!([first, second], [7_138_732, 121]);
    let plan = admit_c23_signed_output_word_plan(profile, [first, second])
        .expect("source-derived operands must pass all 257 C23 outcomes");
    assert_eq!(plan.operands(), [first, second]);
    for input in 0..=256u32 {
        let word = if input == 256 {
            profile.eof_word()
        } else {
            input
        };
        let result = scalar_crazy(second, scalar_crazy(first, word, 15), 15);
        let expected = if input == 256 {
            255
        } else {
            u8::try_from(input).expect("input is a successful byte")
        };
        assert_eq!(
            u8::try_from(result.rem_euclid(256)).expect("result is one byte"),
            expected,
        );
    }
    let extra_rotation = first.div_euclid(3)
        + first.rem_euclid(3) * profile.word_modulus().div_euclid(3);
    assert_ne!(extra_rotation, first);
    assert!(
        admit_c23_signed_output_word_plan(profile, [extra_rotation, second])
            .is_err(),
        "an extra rotation must invalidate the exact C23 conversion"
    );
}

// An algebraically proven pair of p operands is not itself a code image.
// Execute representative single-read N15 /,p,p,<,v traces with those cells.
// The preceding scalar test already exhausts all 257 algebraic outcomes.
// *explicitly seeded* beyond the graphical source. This isolates the exact
// missing physical constant-placement and data-pointer setup obligations:
// it does not claim that the C frontend can emit those operands or the loop.
#[test]
fn seeded_one_read_c23_output_executes_real_crazy_writes_for_byte_and_eof()
-> Result<(), String> {
    use malbolge::{
        ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
        decode_profile_instruction,
    };

    let profile = current_profile();
    let [first, second] = admit_c23_signed_output_word_plan(
        profile,
        CURRENT_C23_SIGNED_OUTPUT_WORDS,
    )
    .map_err(|error| format!("unproved C23 operands: {error:?}"))?
    .operands();
    let operations = [b'/', b'p', b'p', b'<', b'v'];
    let source = operations
        .iter()
        .enumerate()
        .map(|(at, &opcode)| {
            (33..=126u8)
                .find(|byte| {
                    decode_profile_instruction(
                        u32::from(*byte),
                        u32::try_from(at).unwrap_or(u32::MAX),
                    ) == Some(opcode)
                })
                .ok_or_else(|| format!("missing graphical opcode at {at}"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| format!("graphical source: {error:?}"))?;
    // No data operand is a graphical byte or derived from the actual loader.
    // A future source-linked emitter must build and place BOTH of these words.
    assert!(first > 126 && second > 126);
    let mut seeded = loaded.memory().to_vec();
    *seeded.get_mut(100).ok_or("missing first target word")? = first;
    *seeded.get_mut(101).ok_or("missing second target word")? = second;
    let registers = ProfileRegisters {
        accumulator: profile.eof_word(),
        code_pointer: 0,
        data_pointer: 99,
    };
    for value in [0, 1, 0x7b, 0x80, 0xff, 256u32] {
        let (input, expected, observed_input) = if value == 256 {
            (Vec::new(), 255u8, TraceInput::EndOfInput)
        } else {
            let byte = u8::try_from(value).map_err(|e| e.to_string())?;
            (vec![byte], byte, TraceInput::Byte(byte))
        };
        let mut machine = ProfileMachine::from_state(
            profile,
            seeded.clone(),
            input.clone(),
            registers,
        )
        .map_err(|error| format!("seeded VM: {error:?}"))?;
        let mut trace = Vec::new();
        let outcome = machine
            .run_traced(5, &mut |step| trace.push(*step))
            .map_err(|error| format!("VM transition: {error:?}"))?;
        assert_eq!(
            outcome,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 5,
            },
            "input class {value}"
        );
        assert_eq!(trace.len(), 5);
        assert_eq!(trace[0].input, Some(observed_input));
        assert_eq!(trace[0].before.registers.data_pointer, 99);
        assert_eq!(
            trace[0].after.registers.accumulator,
            if value == 256 {
                profile.eof_word()
            } else {
                value
            }
        );
        assert_eq!(trace[1].decoded, Some(b'p'));
        assert_eq!(trace[1].before.registers.data_pointer, 100);
        assert_eq!(
            trace[1].memory_reads.data.map(|read| read.value),
            Some(first)
        );
        let intermediate = scalar_crazy(
            first,
            if value == 256 {
                profile.eof_word()
            } else {
                value
            },
            profile.word_trits(),
        );
        assert_eq!(trace[1].after.registers.accumulator, intermediate);
        assert_eq!(machine.memory_word(100), Ok(intermediate));
        assert_eq!(trace[2].decoded, Some(b'p'));
        assert_eq!(trace[2].before.registers.data_pointer, 101);
        assert_eq!(
            trace[2].memory_reads.data.map(|read| read.value),
            Some(second)
        );
        let converted =
            scalar_crazy(second, intermediate, profile.word_trits());
        assert_eq!(trace[2].after.registers.accumulator, converted);
        assert_eq!(machine.memory_word(101), Ok(converted));
        assert_eq!(trace[3].decoded, Some(b'<'));
        assert_eq!(trace[3].output, Some(expected));
        assert_eq!(trace[4].decoded, Some(b'v'));
        assert_eq!(machine.output(), &[expected], "input class {value}");
        assert_eq!(machine.input_consumed(), input.len(), "one real read");
    }
    Ok(())
}
