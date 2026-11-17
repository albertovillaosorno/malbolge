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
    let mut a = accumulator;
    let mut d = data;
    let mut place = 1u32;
    let mut output = 0u32;
    for _ in 0..trits {
        let value = match (d % 3, a % 3) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        output += value * place;
        place *= 3;
        d /= 3;
        a /= 3;
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
