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
//   - Bounded proof of a physical N15 first-input storage-linker obstacle.
// - Must-Not:
//   - Claim lossless guest storage or completed C32 checksum state.
// - Allows:
//   - Inputs: original 132-cell branch and finite graphical tail patches.
//   - Outputs: independent trit search and real guest counterexample.
//   - Side effects: isolated in-memory VM runs only.
// - Split-When:
//   - General guest data/code placement supersedes the fixed 132-cell bound.
// - Merge-When:
//   - The stateful guest linker can place byte-injective local storage.
// - Summary:
//   - Rejects an apparent injective fold that breaks the actual EOF path.

//! Exhaust a small, source-preserving pre-input storage construction.
//! A perfect byte encoding is not usable if it breaks the physical EOF arm.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, TraceInput, current_profile,
    decode_profile_instruction,
};

const WORD_MODULUS: u32 = 14_348_907;
const ORIGINAL_DATA_TAIL: u32 = 7_174_350;
const INJECTIVE_SEED: u32 = 7_174_453;

// Independent 15-trit truth table, not the VM's implementation.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "bounded independent integer truth table for verification"
)]
fn ternary_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut result = 0;
    let mut place = 1;
    for _ in 0..15 {
        let digit = match (data % 3, accumulator % 3) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        result += digit * place;
        place *= 3;
        data /= 3;
        accumulator /= 3;
    }
    result
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "15-trit right rotation, independently expanded"
)]
fn rotate(value: u32) -> u32 {
    value / 3 + (value % 3) * (WORD_MODULUS / 3)
}

fn graphical_tail(address: u32) -> Vec<u8> {
    (33u8..=126)
        .filter(|source| {
            decode_profile_instruction(u32::from(*source), address)
                .is_some_and(|opcode| b"oijp*/<v".contains(&opcode))
        })
        .collect()
}

fn step(op: u8, data: u32, accumulator: u32) -> (u32, u32) {
    match op {
        b'o' => (data, accumulator),
        b'p' => {
            let folded = ternary_crazy(data, accumulator);
            (folded, folded)
        },
        b'*' => {
            let rotated = rotate(data);
            (rotated, rotated)
        },
        _ => unreachable!("pinned finite operation grammar"),
    }
}

#[test]
fn source_tail_preserving_the_pointer_chain_cannot_seed_an_entire_byte() {
    // C127 `*`, C128 `<`, C129 `v` are reached on the real EOF arm.
    // Keep C9..C11 inert so they do not overwrite those code words.
    // C12 and C13 may be inert, crazy or rotate on M130 and M131.
    // C14 still writes M132, C53 reads, and C61 folds the first input.
    // Changing the 132-cell loader tail must preserve the initial M132,
    // or the existing C17..C52 pointer-chain proof is inapplicable.
    let tails = graphical_tail(130)
        .into_iter()
        .flat_map(|low| {
            graphical_tail(131)
                .into_iter()
                .filter(move |high| {
                    ternary_crazy(u32::from(low), u32::from(*high))
                        == ORIGINAL_DATA_TAIL
                })
                .map(move |high| (low, high))
        })
        .collect::<Vec<_>>();
    assert_eq!(tails, [(45, 125), (126, 125)]);

    let mut maximum_classes = 0;
    let mut admitted_seeds = BTreeSet::new();
    let mut enumerated = 0;
    for (low, high) in tails {
        for first in b"op*" {
            for second in b"op*" {
                // C12 starts with A=0. C13 sees exactly the result of
                // C12 and then C53 later replaces A with actual input.
                let (_, accumulator) = step(*first, u32::from(low), 0);
                let (saved_seed, _) =
                    step(*second, u32::from(high), accumulator);
                let classes = (u8::MIN..=u8::MAX)
                    .map(|byte| ternary_crazy(saved_seed, u32::from(byte)))
                    .collect::<BTreeSet<_>>()
                    .len();
                maximum_classes = maximum_classes.max(classes);
                let _ = admitted_seeds.insert(saved_seed);
                enumerated += 1;
                assert!(classes < 256, "unexpected byte-injective seed");
            }
        }
    }
    assert_eq!(enumerated, 18);
    assert_eq!(admitted_seeds.len(), 6);
    assert!(maximum_classes < 256);
}

#[test]
#[expect(
    clippy::expect_used,
    reason = "fixed real-guest counterexample"
)]
fn byte_injective_tail_change_breaks_the_existing_second_eof_path() {
    let profile = current_profile();
    // C10/C12 produce A=8, and C13 then creates an all-one seed in M131.
    // The 256 byte classes and signed EOF are pairwise distinguishable.
    assert_eq!(ternary_crazy(65, 0), 7_174_481);
    assert_eq!(ternary_crazy(97, 7_174_481), 8);
    assert_eq!(ternary_crazy(125, 8), INJECTIVE_SEED);
    let classes = (u8::MIN..=u8::MAX)
        .map(|byte| ternary_crazy(INJECTIVE_SEED, u32::from(byte)))
        .collect::<BTreeSet<_>>();
    assert_eq!(classes.len(), 256);
    assert!(
        !classes.contains(&ternary_crazy(INJECTIVE_SEED, profile.eof_word(),))
    );

    let mut source =
        layout::build_second_input_branch_with_dual_first_fold_source(profile)
            .expect("original bounded physical EOF branch");
    // Unlike the actual original `-}` loader tail, `a}` changes M132.
    // The three data writes are real instructions, not host-computed data.
    source[130] = b'a';
    for address in [10usize, 12, 13] {
        source[address] = (33u8..=126)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), address as u32)
                    == Some(b'p')
            })
            .expect("loader-valid graphical pre-input p");
    }
    assert_eq!(source.get(130..), Some(b"a}".as_slice()));
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .expect("graphical source is loadable, not yet admitted as control");
    assert_eq!(loaded.memory()[131], 125);
    assert_eq!(loaded.memory()[132], 7_174_337);
    let mut vm = ProfileMachine::from_state(
        profile,
        loaded.memory().to_vec(),
        Vec::new(),
        ProfileRegisters::default(),
    )
    .expect("isolated empty-stream guest");
    let mut operations = Vec::new();
    let mut reads = Vec::new();
    let result = vm.run_traced(119, &mut |transition| {
        let code = transition.before.registers.code_pointer;
        if [10, 12, 13].contains(&code) {
            operations.push((
                code,
                transition.decoded,
                transition.after.registers.accumulator,
            ));
        }
        if let Some(read) = transition.input {
            reads.push((code, read));
        }
    });
    assert_eq!(operations, [
        (10, Some(b'p'), 7_174_481),
        (12, Some(b'p'), 8),
        (13, Some(b'p'), INJECTIVE_SEED),
    ]);
    assert!(reads.contains(&(53, TraceInput::EndOfInput)));
    // The original correct EOF arm must halt at step 119 and emit 0x1e.
    // This mathematically perfect seed instead corrupts its loader chain.
    assert_eq!(result, Ok(RunOutcome::BudgetExhausted { steps: 119 }));
    assert_eq!(vm.registers().code_pointer, 69);
    assert_ne!(vm.output(), [106, 30]);
}
