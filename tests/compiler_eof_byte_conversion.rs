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
// Each ordered pair of trits enters a 3- or 4-cycle after at most one
// transition; their least common period is 12. Exhaust every graphical
// seed pair and every phase, not merely the first few expanded cells.
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
