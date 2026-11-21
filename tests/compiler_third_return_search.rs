// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier: Apache-2.0
//
// Boundary-Contract:
// - Owns: source-valid tail and local-code continuation constraints on N15.
// - Must-Not: infer no general guest loop or claim a source-C compilation.
// - Allows: exactly 64 loader tails, 168 local edits and real VM checks.
// - Summary: bounded physical failures after the genuine third signed read.

//! Two bounded continuation searches on a source-loaded N15 EOF branch.
//!
//! These are necessary linker counterexamples, not exhaustive code synthesis.
//! No host stdout is a substitute for the actual VM or C23 execution.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileRegisters, RunOutcome,
    Termination, current_profile, decode_profile_instruction,
};

const BUDGET: usize = 240;
const CODE_EDITS: [(usize, u8); 3] = [(71, b'<'), (104, b'o'), (112, b'p')];

#[expect(
    clippy::expect_used,
    clippy::shadow_reuse,
    reason = "bounded N15 source encoding within fixed phase decoder"
)]
fn graphical(position: usize, opcode: u8) -> u8 {
    let position = u32::try_from(position).unwrap_or(u32::MAX);
    (33..=126)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), position)
                == Some(opcode)
        })
        .expect("requested opcode has a graphical encoding")
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::as_conversions,
    clippy::default_numeric_fallback,
    clippy::indexing_slicing,
    reason = "15-trit source-loader oracle with proven trit indexes"
)]
fn independent_crazy(mut left: u32, mut right: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let (mut result, mut factor) = (0, 1);
    for _ in 0..15 {
        result += TABLE[(left % 3) as usize][(right % 3) as usize] * factor;
        factor *= 3;
        left /= 3;
        right /= 3;
    }
    result
}

#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "verified 132-cell source and fixed in-range edits"
)]
fn source_with_return_edits() -> Vec<u8> {
    let mut source =
        layout::build_two_input_class_state_with_guarded_third_read_source(
            current_profile(),
        )
        .expect("canonical N15 guarded branch");
    for (position, opcode) in CODE_EDITS {
        source[position] = graphical(position, opcode);
    }
    source
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    clippy::indexing_slicing,
    reason = "finite 64-source recurrence and guest proof with bounded offsets"
)]
fn source_tail_variants_do_not_repair_the_third_read_return()
-> Result<(), String> {
    let profile = current_profile();
    let source = source_with_return_edits();
    let initial = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    let valid = |position| {
        (33u8..=126)
            .filter(|byte| {
                decode_profile_instruction(u32::from(*byte), position)
                    .is_some_and(|opcode| b"oijp*/<v".contains(&opcode))
            })
            .collect::<Vec<_>>()
    };
    let mut reached_third = Vec::new();
    let mut examined = 0usize;
    // The 15-trit recurrence repeats its first six words for every
    // graphical tail in this frozen grammar. Rebuild the memory exactly,
    // avoiding 64 full-capacity VM loader expansions for the search.
    for first in valid(130) {
        for second in valid(131) {
            let mut memory = initial.memory().to_vec();
            memory[130] = u32::from(first);
            memory[131] = u32::from(second);
            let (mut previous, mut last) =
                (u32::from(first), u32::from(second));
            let mut phase = [0u32; 6];
            for value in &mut phase {
                *value = independent_crazy(previous, last);
                previous = last;
                last = *value;
            }
            for cells in memory[132..].chunks_mut(6) {
                cells.copy_from_slice(&phase[..cells.len()]);
            }
            // Independently reload all three surviving three-read tails.
            // This checks the synthetic repetition against the *actual*
            // strict N15 graphical loader before guest-run conclusions.
            if second == 125 && [45, 63, 126].contains(&first) {
                let mut candidate_source = source.clone();
                candidate_source[130] = first;
                candidate_source[131] = second;
                let loaded = ProfileMachine::from_source(
                    profile,
                    &candidate_source,
                    Vec::new(),
                )
                .map_err(|error| error.to_string())?;
                assert_eq!(memory, loaded.memory());
            }
            let mut vm = ProfileMachine::from_state(
                profile,
                memory,
                vec![3, 4, 5],
                ProfileRegisters::default(),
            )
            .map_err(|error| error.to_string())?;
            let mut reads = Vec::new();
            let outcome = vm.run_traced(BUDGET, &mut |step| {
                if step.input.is_some() {
                    reads.push(step.before.registers.code_pointer);
                }
            });
            if reads == [53, 63, 101] {
                assert!(
                    matches!(
                        outcome,
                        Err(
                            ProfileMachineError::InvalidEncryptionTarget { .. }
                        )
                    ),
                    "third-read tail {first},{second}: {outcome:?}"
                );
                reached_third.push((first, second, vm.output().to_vec()));
            }
            examined += 1;
        }
    }
    assert_eq!(examined, 64);
    assert_eq!(reached_third, [
        (45, 125, vec![3, 134, 154]),
        (63, 125, vec![3, 71, 166]),
        (126, 125, vec![3, 134, 154]),
    ]);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    clippy::excessive_nesting,
    clippy::indexing_slicing,
    reason = "finite 168-source guest census with in-range code edits"
)]
fn one_cell_edits_cannot_restore_a_correct_third_read_continuation()
-> Result<(), String> {
    let profile = current_profile();
    let source = source_with_return_edits();
    let initial = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    let mut tried = 0usize;
    let mut three_reads = 0usize;
    let mut non_error_paths = Vec::new();
    for position in (65..=75).chain(102..=114) {
        for &opcode in b"oijp*/<v" {
            let encoded = graphical(position, opcode);
            if initial.memory()[position] == u32::from(encoded) {
                continue;
            }
            let mut memory = initial.memory().to_vec();
            memory[position] = u32::from(encoded);
            let mut vm = ProfileMachine::from_state(
                profile,
                memory,
                vec![3, 4, 5],
                ProfileRegisters::default(),
            )
            .map_err(|error| error.to_string())?;
            let mut reads = Vec::new();
            let outcome = vm.run_traced(BUDGET, &mut |step| {
                if step.input.is_some() {
                    reads.push(step.before.registers.code_pointer);
                }
            });
            if reads == [53, 63, 101] {
                three_reads += 1;
                if !matches!(
                    outcome,
                    Err(ProfileMachineError::InvalidEncryptionTarget { .. })
                ) {
                    non_error_paths.push((
                        position,
                        opcode,
                        outcome,
                        vm.output().to_vec(),
                    ));
                }
            }
            tried += 1;
        }
    }
    assert_eq!(tried, 168);
    assert_eq!(three_reads, 54);
    assert_eq!(non_error_paths, [
        (
            70,
            b'j',
            Ok(RunOutcome::Terminated {
                reason: Termination::NonGraphicalCell,
                steps: 147,
            }),
            vec![3, 134]
        ),
        (
            104,
            b'*',
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 175,
            }),
            vec![3, 134, 154]
        ),
    ]);
    // Neither outcome is a third-byte echo, let alone a repeatable
    // source-C EOF loop or a complete guest checksum.
    Ok(())
}
