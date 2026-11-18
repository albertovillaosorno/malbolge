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
//   - Exhaustive signed-EOF versus successful-input control-word proof.
// - Must-Not:
//   - Claim placed `p` operands, executable jumps or a guest C checksum.
// - Allows:
//   - Inputs: 256 byte words, real N15 EOF, two proposed crazy operands.
//   - Outputs: exact proposed branch words or precise scalar refusal.
//   - Side effects: none; independent 15-trit arithmetic only.
// - Split-When:
//   - A guest linker realizes and verifies actual input-dependent jumps.
// - Merge-When:
//   - The compiler emits source-proven C23 EOF conditionals in the guest.
// - Summary:
//   - Checks target-word discrimination without fabricating guest control.

//! A source-independent arithmetic prerequisite for dynamic EOF branching.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use layout::{
    C23EofControlWordError, CURRENT_C23_EOF_CONTROL_WORDS,
    CURRENT_C23_EOF_TARGET_WORDS, admit_c23_eof_control_word_plan,
};
use malbolge::{current_profile, historical_profile, profile_crazy};

// Independent mathematical truth table, without invoking the VM helper.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "fixed-width independent 15-trit mathematical oracle"
)]
fn independent_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut result = 0u32;
    let mut place = 1u32;
    for _ in 0u8..15 {
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

// Prove an independently calculated result matches both the expected branch
// word and the normative profile arithmetic primitive for this one input.
fn check_input_control(
    profile: &malbolge::ProfileDescriptor,
    operands: [u32; 2],
    word: u32,
    expected: u32,
) {
    let first = independent_crazy(operands[0], word);
    let actual = independent_crazy(operands[1], first);
    assert_eq!(actual, expected, "input word {word}");
    assert_eq!(
        actual,
        profile_crazy(
            operands[1],
            profile_crazy(operands[0], word, profile.word_trits()),
            profile.word_trits(),
        ),
        "trit oracle disagrees with profile for input {word}",
    );
}

#[test]
fn two_crazy_control_words_distinguish_every_c23_getchar_result() {
    let profile = current_profile();
    let checked = admit_c23_eof_control_word_plan(
        profile,
        CURRENT_C23_EOF_CONTROL_WORDS,
        CURRENT_C23_EOF_TARGET_WORDS,
    );
    assert!(checked.is_ok(), "all 257 C23 outcomes: {checked:?}");
    let Ok(plan) = checked else {
        return;
    };
    assert_eq!(plan.operands(), [14_348_906, 486]);
    assert_eq!(plan.targets(), [243, 486]);
    assert_eq!(plan.next_code_addresses(), [244, 487]);
    assert_eq!(plan.mandatory_runtime_operand_writes(), [true, true]);
    // In particular, input 0xff is NOT C's signed EOF sentinel.
    for byte in u8::MIN..=u8::MAX {
        check_input_control(
            profile,
            plan.operands(),
            u32::from(byte),
            plan.targets()[0],
        );
    }
    check_input_control(
        profile,
        plan.operands(),
        profile.eof_word(),
        plan.targets()[1],
    );
}

#[test]
fn changed_words_or_targets_are_rejected_before_layout() {
    let profile = current_profile();
    assert_eq!(
        admit_c23_eof_control_word_plan(
            historical_profile(),
            CURRENT_C23_EOF_CONTROL_WORDS,
            CURRENT_C23_EOF_TARGET_WORDS,
        ),
        Err(C23EofControlWordError::UnsupportedProfile)
    );
    assert_eq!(
        admit_c23_eof_control_word_plan(
            profile,
            [profile.word_modulus(), 486],
            CURRENT_C23_EOF_TARGET_WORDS,
        ),
        Err(C23EofControlWordError::InvalidOperand)
    );
    assert_eq!(
        admit_c23_eof_control_word_plan(
            profile,
            CURRENT_C23_EOF_CONTROL_WORDS,
            [243, 243],
        ),
        Err(C23EofControlWordError::IndistinguishableTargets)
    );
    assert_eq!(
        admit_c23_eof_control_word_plan(
            profile,
            CURRENT_C23_EOF_CONTROL_WORDS,
            [profile.word_modulus(), 486],
        ),
        Err(C23EofControlWordError::InvalidTarget)
    );
    assert_eq!(
        admit_c23_eof_control_word_plan(
            profile,
            CURRENT_C23_EOF_CONTROL_WORDS,
            [242, 486],
        ),
        Err(C23EofControlWordError::ByteMismatch { byte: 0, actual: 243 })
    );
    assert_eq!(
        admit_c23_eof_control_word_plan(
            profile,
            CURRENT_C23_EOF_CONTROL_WORDS,
            [243, 485],
        ),
        Err(C23EofControlWordError::EofMismatch { actual: 486 })
    );
    for words in [[14_348_905, 486], [14_348_906, 487], [486, 14_348_906]] {
        assert!(
            admit_c23_eof_control_word_plan(
                profile,
                words,
                CURRENT_C23_EOF_TARGET_WORDS,
            )
            .is_err(),
            "mutated operand pair unexpectedly proved an EOF branch: {words:?}"
        );
    }
}

// Independent digitwise recurrence for the 3^5 plane of graphical source
// loader seeds. This is not a substituted VM trace or a guest layout.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "small exhaustive arithmetic proof of the graphical seed plane"
)]
#[test]
fn a_complete_eof_discriminator_requires_guest_operand_synthesis() {
    let trit = |data: u32, accumulator: u32| -> u32 {
        match (data, accumulator) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        }
    };
    // Both 0 and 243 are successful C23 getchar bytes. At exactly trit 5
    // they are 0 and 1; at every other trit they are identical. A two-p
    // cascade without operand trit 2 in this plane cannot collapse them.
    for first in 0..=1 {
        for second in 0..=1 {
            assert_ne!(
                trit(second, trit(first, 0)),
                trit(second, trit(first, 1)),
                "unmodified loader digits cannot collapse bytes 0 and 243"
            );
        }
    }
    // Source cells are graphical ASCII. All 94^2 initial seed pairs have
    // fifth trit zero; the independent recurrence keeps that trit 0 or 1.
    // This checked finite prefix illustrates the inductive closure
    // (0,0)->(0,1)->(1,0)->(0,1)... for arbitrarily long expansion.
    for left in 33u32..=126 {
        for right in 33u32..=126 {
            assert_eq!((left / 243) % 3, 0);
            assert_eq!((right / 243) % 3, 0);
            let (mut a, mut b) = ((left / 243) % 3, (right / 243) % 3);
            for _ in 0..32 {
                let next = trit(a, b);
                assert_ne!(next, 2, "loader cannot create trit 2 from 0/1");
                (a, b) = (b, next);
            }
        }
    }
    let profile = current_profile();
    let plan = admit_c23_eof_control_word_plan(
        profile,
        CURRENT_C23_EOF_CONTROL_WORDS,
        CURRENT_C23_EOF_TARGET_WORDS,
    )
    .expect("existing exhaustive EOF discriminator");
    assert!(plan.mandatory_runtime_operand_writes().iter().any(|v| *v));
    assert_eq!(plan.mandatory_runtime_operand_writes(), [true, true]);
    // An independently chosen lower-magnitude first operand also proves
    // the same 257-case targets, but cannot bypass operand synthesis.
    let alternative = admit_c23_eof_control_word_plan(
        profile,
        [7_174_817, 486],
        CURRENT_C23_EOF_TARGET_WORDS,
    )
    .expect("alternative two-p discriminator");
    assert_eq!(alternative.mandatory_runtime_operand_writes(), [true, true]);
}

// Strengthens the one-write candidate's lower bound: the required 728
// contains six 2-trits. Every graphical source word has at most four, and
// the loader cannot create another in any place >= 3^4. Rotation permutes
// trits without changing that population, even after repeated rotations.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent fixed-width base-three digit and recurrence oracle"
)]
#[test]
fn rotations_of_virgin_loader_words_cannot_supply_728() {
    const SECOND_OPERAND: u32 = 728;
    const MODULUS: u32 = 14_348_907;
    let two_count = |mut word: u32| {
        let mut count = 0;
        for _ in 0..15 {
            count += u32::from(word % 3 == 2);
            word /= 3;
        }
        count
    };
    let rotate = |word: u32| word / 3 + (word % 3) * (MODULUS / 3);
    assert_eq!(two_count(SECOND_OPERAND), 6);
    for left in 33..=126u32 {
        for right in 33..=126u32 {
            let (mut older, mut newer) = (left, right);
            // All loader addresses begin with these two graphical source
            // cells. For each trit >= 4, their 0/1-only state is inductive:
            // independent_crazy(0/1, 0/1) is again 0/1.
            for _ in 0..8 {
                assert!(two_count(older) <= 4);
                let mut rotated = older;
                for _ in 0..15 {
                    assert_eq!(two_count(rotated), two_count(older));
                    assert_ne!(rotated, SECOND_OPERAND);
                    rotated = rotate(rotated);
                }
                assert_eq!(rotated, older);
                let next = independent_crazy(older, newer);
                // In addition to the finite phases, this is a complete
                // recurrence invariant: no 2 trit at positions 4..14.
                let mut high = next / 81;
                for _ in 4..15 {
                    assert_ne!(high % 3, 2);
                    high /= 3;
                }
                (older, newer) = (newer, next);
            }
        }
    }
}
