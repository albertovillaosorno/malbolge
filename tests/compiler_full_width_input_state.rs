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
//   - Finite lossless-input-state screening against a real N15 guest path.
// - Must-Not:
//   - Mistake an injective crazy mapping for executable C32 storage.
// - Allows:
//   - Inputs: current 132-cell EOF source and bounded loader/early-code edits.
//   - Outputs: 257-input trit proof and guest path/pointer counterexamples.
//   - Side effects: isolated normative VM runs only.
// - Split-When:
//   - A general physical guest storage linker replaces the bounded layout.
// - Merge-When:
//   - Source-C checksum compilation consumes an executable lossless local.
// - Summary:
//   - Rules out two tempting first-input seed repairs in the frozen skeleton.

//! Bounded negative storage experiment, not a general compiler impossibility.
//!
//! The complete mutable-C EOF checksum still needs C32 state across reads.
//! In the current 132-cell guest, C53 reads the signed first input, C62 can
//! write M132 before C63 reads again, and C14 can preseed M132. Test two
//! finite proposed repairs rather than asserting that a lossy fold suffices.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::array;
use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, current_profile,
};

const TRITS: usize = 15;
const WORD_MODULUS: u32 = 14_348_907;
const ORIGINAL_LOADER_WORD: u32 = 7_174_350;
const GRAPHICAL_FIRST: u32 = 33;
const GRAPHICAL_LAST: u32 = 126;

// Independently transcribed trit table, not the compiler/VM implementation.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "fixed 15-trit scalar truth table for the bounded search"
)]
fn oracle_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut word = 0;
    let mut place = 1;
    for _ in 0..TRITS {
        let row = usize::try_from(data % 3).unwrap_or_default();
        let column = usize::try_from(accumulator % 3).unwrap_or_default();
        let digit = TABLE
            .get(row)
            .and_then(|digits| digits.get(column))
            .copied()
            .unwrap_or_default();
        word += digit * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    word
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::integer_division,
    reason = "one exact 15-trit right rotation"
)]
const fn oracle_rotate(word: u32) -> u32 {
    word / 3 + (word % 3) * (WORD_MODULUS / 3)
}

fn distinct_byte_classes(seed: u32) -> (usize, bool) {
    let words = (u8::MIN..=u8::MAX)
        .map(|byte| oracle_crazy(seed, u32::from(byte)))
        .collect::<BTreeSet<_>>();
    let eof_is_separate =
        !words.contains(&oracle_crazy(seed, WORD_MODULUS - 1));
    (words.len(), eof_is_separate)
}

fn loader_tail(first: u32, second: u32) -> [u32; 28] {
    let mut previous = first;
    let mut current = second;
    array::from_fn(|index| match index {
        0 => first,
        1 => second,
        _ => {
            let next = oracle_crazy(previous, current);
            previous = current;
            current = next;
            next
        },
    })
}

#[expect(
    clippy::integer_division_remainder_used,
    reason = "exact twelve-phase finite loader recurrence"
)]
fn after_original_two_jumps(loader: &[u32; 28]) -> Option<u32> {
    let pointer = loader.get(6)?.checked_add(1)?;
    let phase = usize::try_from(pointer.checked_sub(131)? % 12).ok()?;
    loader.get(phase.checked_add(1)?)?.checked_add(1)
}

#[test]
#[expect(
    clippy::integer_division_remainder_used,
    clippy::panic_in_result_fn,
    reason = "bounded base-three test with assertions and fallible VM setup"
)]
fn no_five_early_inert_p_rotate_choices_preserve_a_lossless_first_word()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_second_input_branch_with_first_eof_fold_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(
        source.get(127..132),
        Some([100, 65, 46, 45, 125].as_slice())
    );
    let memory = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    assert_eq!(memory.memory().get(132), Some(&ORIGINAL_LOADER_WORD));
    let mut max_byte_classes = 0;
    // In the frozen reached prefix, C9..C13 address M127..M131 once,
    // with A initially zero. All 3^5 arrangements of inert `o`, `p`,
    // and `*` preserve linear C progression to a C14 `p` on M132.
    // Allowing alterations even to reached EOF-arm cells C127..C129
    // makes this a *superset* of physically safe candidates.
    for mut choice in 0..243usize {
        let mut accumulator = 0;
        for &operand in memory
            .memory()
            .get(127..132)
            .ok_or_else(|| String::from("frozen five-cell preseed"))?
        {
            let instruction = choice % 3;
            choice /= 3;
            accumulator = match instruction {
                0 => accumulator,
                1 => oracle_crazy(operand, accumulator),
                _ => oracle_rotate(operand),
            };
        }
        let seed = oracle_crazy(ORIGINAL_LOADER_WORD, accumulator);
        let (classes, eof_separate) = distinct_byte_classes(seed);
        assert!(classes < 256 || !eof_separate);
        max_byte_classes = max_byte_classes.max(classes);
    }
    assert_eq!(max_byte_classes, 175);
    Ok(())
}

#[test]
fn injective_graphical_tail_cannot_keep_the_original_two_jump_chain() {
    // For this exact source skeleton, C18 and C19 are the two guest `j`
    // instructions returning D to M135 for the next rotation at C20.
    // The C14 preseed alters only M132, so the original loader-derived
    // M136 and the distant cell reached by C18 remain unchanged.
    let mut checked: usize = 0;
    let mut injective: usize = 0;
    let mut preserved: usize = 0;
    let mut best_classes = 0;
    for first in GRAPHICAL_FIRST..=GRAPHICAL_LAST {
        for second in GRAPHICAL_FIRST..=GRAPHICAL_LAST {
            let loader = loader_tail(first, second);
            assert_eq!(&loader[1..16], &loader[13..28]);
            // C14 `p` with A=0 is the only proposed pre-input seed.
            let seed = oracle_crazy(loader[2], 0);
            let (classes, eof_separate) = distinct_byte_classes(seed);
            checked += 1;
            best_classes = best_classes.max(classes);
            if classes != 256 || !eof_separate {
                continue;
            }
            injective += 1;
            // `j` reads M[D], then increments D. The loader recurrence
            // has twelve-word phase starting at M131. This is
            // M[M136+1]+1, not a hypothetical jump to M136.
            if after_original_two_jumps(&loader) == Some(135) {
                preserved += 1;
            }
        }
    }
    assert_eq!(checked, 94 * 94);
    assert_eq!(best_classes, 256);
    assert_eq!(injective, 1763);
    assert_eq!(preserved, 0);
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions diagnose VM counterexample after fallible setup"
)]
fn actual_injective_tail_breaks_the_unchanged_guest_eof_control()
-> Result<(), String> {
    let profile = current_profile();
    let mut altered =
        layout::build_second_input_branch_with_preseeded_first_fold_source(
            profile,
        )
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(altered.get(130..), Some(b"-}".as_slice()));
    assert_eq!(altered.get(14), Some(&48));
    *altered
        .get_mut(130)
        .ok_or_else(|| String::from("C130 source byte exists"))? = b'b';
    let new_seed = oracle_crazy(loader_tail(98, 125)[2], 0);
    assert_eq!(distinct_byte_classes(new_seed), (256, true));

    let loaded = ProfileMachine::from_source(profile, &altered, Vec::new())
        .map_err(|error| error.to_string())?;
    let mut vm = ProfileMachine::from_state(
        profile,
        loaded.memory().to_vec(),
        Vec::new(),
        ProfileRegisters::default(),
    )
    .map_err(|error| error.to_string())?;
    let mut c20_data_pointer = None;
    let actual = vm.run_traced(119, &mut |step| {
        if step.before.registers.code_pointer == 20 {
            c20_data_pointer = Some(step.before.registers.data_pointer);
        }
    });
    assert_eq!(c20_data_pointer, Some(122));
    assert_ne!(
        actual,
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 119,
        }),
        "injective mathematical seed must not masquerade as a valid branch",
    );
    assert_eq!(vm.output(), []);
    Ok(())
}
