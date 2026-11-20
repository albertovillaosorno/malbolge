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
//   - Real guest preseed and live signed first-word fold across second EOF.
// - Must-Not:
//   - Claim lossless C32 storage or executable checksum CFG lowering.
// - Allows:
//   - Inputs: one frozen N15 source and bounded binary/EOF input streams.
//   - Outputs: independent trit oracles, guest state writes and IO traces.
//   - Side effects: isolated, bounded in-memory guest execution only.
// - Split-When:
//   - General full-width scalar guest storage supersedes the folded witness.
// - Merge-When:
//   - Signed EOF guest linker consumes the physical saved-word primitive.
// - Summary:
//   - A real pre-input write increases distinct first-word folded classes.

//! Physically preseed a saved input discriminator before live guest input.
//! The fold remains lossy; the original mutable checksum is still unlinked.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, historical_profile,
};

const ORIGINAL_SEED: u32 = 7_174_350;
const MAX_STEPS: usize = 175;

// A separate 15-trit truth table; not the VM or builder crazy function.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent bounded integer trit truth table"
)]
fn independent_crazy(mut data: u32, mut accumulator: u32) -> u32 {
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

#[test]
fn preseed_expands_but_does_not_complete_first_word_classes() {
    let profile = current_profile();
    let seed = independent_crazy(ORIGINAL_SEED, 0);
    assert_eq!(seed, 7_174_462);
    let classes = |word| {
        (u8::MIN..=u8::MAX)
            .map(|byte| independent_crazy(word, u32::from(byte)))
            .collect::<BTreeSet<_>>()
    };
    let original = classes(ORIGINAL_SEED);
    let preseeded = classes(seed);
    assert_eq!(original.len(), 36);
    assert_eq!(preseeded.len(), 171);
    assert_ne!(original, preseeded);
    let eof = independent_crazy(seed, profile.eof_word());
    assert_eq!(eof, 14_348_897);
    assert!(!preseeded.contains(&eof));
    assert!(preseeded.len() < 256, "not a lossless C byte local");
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::too_many_lines,
    reason = "frozen physical source and complete real-VM trace obligations"
)]
fn real_guest_preseed_and_input_fold_survive_both_eof_arms() {
    let profile = current_profile();
    let source =
        layout::build_second_input_branch_with_preseeded_first_fold_source(
            profile,
        )
        .expect("physical N15 preseed source");
    let old =
        layout::build_second_input_branch_with_first_eof_fold_source(profile)
            .expect("original physical fold source");
    assert_eq!(source.len(), 132);
    assert_eq!(source.get(130..), Some(b"-}".as_slice()));
    assert_eq!(source.get(14), Some(&48));
    assert_eq!(
        source
            .iter()
            .zip(&old)
            .enumerate()
            .filter(|(_, (left, right))| left != right)
            .map(|(position, _)| position)
            .collect::<Vec<_>>(),
        [14],
    );
    assert_eq!(
        layout::build_second_input_branch_with_preseeded_first_fold_source(
            historical_profile()
        ),
        Err(layout::SignedEofBranchSourceError::UnsupportedProfile),
    );
    let initial = ProfileMachine::from_source(profile, &source, Vec::new())
        .expect("loader must accept preseed source");
    assert_eq!(initial.memory().get(132), Some(&ORIGINAL_SEED));
    let seeded = independent_crazy(ORIGINAL_SEED, 0);
    // EOF, binary bytes, both second-EOF/byte branches, and unread suffix.
    let vectors: &[&[u8]] = &[
        &[],
        &[0],
        &[3],
        &[255],
        &[0, 0],
        &[3, 4, 5],
        &[3, 31, 255],
        &[3, 255, 31],
        &[255, 0, 128],
        &[255, 255, 31, 17],
    ];
    for &input in vectors {
        let first = input
            .first()
            .copied()
            .map_or_else(|| profile.eof_word(), u32::from);
        let folded = independent_crazy(seeded, first);
        let eof_second = input.len() < 2;
        let steps = if eof_second {
            119
        } else {
            MAX_STEPS
        };
        let output = [
            input.first().copied().unwrap_or(106),
            if eof_second {
                30
            } else {
                154
            },
        ];
        let mut vm = ProfileMachine::from_state(
            profile,
            initial.memory().to_vec(),
            input.to_vec(),
            ProfileRegisters::default(),
        )
        .expect("isolated guest state");
        let mut writes = Vec::new();
        let mut reads = Vec::new();
        let mut outputs = Vec::new();
        let mut visits_at_62 = 0;
        let mut first_fold_accumulator = None;
        let outcome = vm.run_traced(steps, &mut |step| {
            if let Some(write) = step.memory_delta.data
                && write.address == 132
            {
                writes.push((
                    step.before.registers.code_pointer,
                    write.before,
                    write.after,
                ));
            }
            if let Some(value) = step.input {
                reads.push((step.before.registers.code_pointer, value));
            }
            if let Some(value) = step.output {
                outputs.push((step.before.registers.code_pointer, value));
            }
            if step.before.registers.code_pointer == 14 {
                assert_eq!(step.decoded, Some(b'p'));
                assert_eq!(step.before.registers.accumulator, 0);
                assert_eq!(step.before.registers.data_pointer, 132);
            }
            if step.before.registers.code_pointer == 62 {
                assert_eq!(
                    step.decoded,
                    Some(if visits_at_62 == 0 {
                        b'p'
                    } else {
                        b't'
                    })
                );
                if visits_at_62 > 0 {
                    assert!(step.memory_delta.data.is_none());
                } else {
                    assert_eq!(step.before.registers.data_pointer, 132);
                    assert_eq!(step.before.registers.accumulator, first);
                    first_fold_accumulator =
                        Some(step.after.registers.accumulator);
                }
                visits_at_62 += 1;
            }
        });
        assert_eq!(
            outcome,
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps,
            }),
            "input={input:?}",
        );
        assert_eq!(vm.output(), output, "input={input:?}");
        assert_eq!(vm.input_consumed(), input.len().min(2));
        assert_eq!(vm.memory().get(132), Some(&folded));
        let mut expected_writes = vec![(14, ORIGINAL_SEED, seeded)];
        // The VM correctly omits a memory delta when p writes the exact
        // same word (notably first byte NUL). Reaching the opcode is still
        // checked independently of observable cell change.
        if seeded != folded {
            expected_writes.push((62, seeded, folded));
        }
        assert_eq!(writes, expected_writes);
        assert_eq!(first_fold_accumulator, Some(folded));
        assert_eq!(
            visits_at_62,
            if eof_second {
                1
            } else {
                2
            }
        );
        assert_eq!(reads, [
            (
                53,
                input
                    .first()
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            ),
            (
                63,
                input
                    .get(1)
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            ),
        ]);
        assert_eq!(outputs, [
            (54, output[0]),
            (
                if eof_second {
                    128
                } else {
                    57
                },
                output[1]
            )
        ]);
    }
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::too_many_lines,
    reason = "independent two-cell VM state and bounded control witnesses"
)]
fn consecutive_physical_first_word_stores_keep_eof_control() {
    let profile = current_profile();
    let source =
        layout::build_second_input_branch_with_dual_first_fold_source(profile)
            .expect("two-cell guest fold source");
    let preseed =
        layout::build_second_input_branch_with_preseeded_first_fold_source(
            profile,
        )
        .expect("one-cell preseed source");
    assert_eq!(source.len(), 132);
    assert_eq!(source.get(61), Some(&95));
    assert_eq!(source.get(130..), Some(b"-}".as_slice()));
    assert_eq!(
        source
            .iter()
            .zip(&preseed)
            .enumerate()
            .filter(|(_, (a, b))| a != b)
            .map(|(position, _)| position)
            .collect::<Vec<_>>(),
        [61],
    );
    assert_eq!(
        layout::build_second_input_branch_with_dual_first_fold_source(
            historical_profile()
        ),
        Err(layout::SignedEofBranchSourceError::UnsupportedProfile),
    );
    // The second cell depends on the already-folded first; it does not
    // magically restore distinctions the first 15-trit crazy lost.
    let first_classes = (u8::MIN..=u8::MAX)
        .map(|byte| independent_crazy(125, u32::from(byte)))
        .collect::<BTreeSet<_>>();
    assert!(first_classes.len() < 256);
    let input_zero = independent_crazy(125, 0);
    assert_eq!(input_zero, independent_crazy(125, 1));
    let initial = ProfileMachine::from_source(profile, &source, Vec::new())
        .expect("loader admits both guest-state cells");
    assert_eq!(initial.memory()[131], 125);
    assert_eq!(initial.memory()[132], ORIGINAL_SEED);
    let seeded = independent_crazy(ORIGINAL_SEED, 0);
    for input in [
        &[][..],
        &[0][..],
        &[1, 4][..],
        &[2, 255, 99][..],
        &[31, 31, 8][..],
        &[255, 0, 7][..],
    ] {
        let first = input
            .first()
            .copied()
            .map_or_else(|| profile.eof_word(), u32::from);
        let first_fold = independent_crazy(125, first);
        let second_fold = independent_crazy(seeded, first_fold);
        let eof_second = input.len() < 2;
        let steps = if eof_second {
            119
        } else {
            MAX_STEPS
        };
        let output = [
            input.first().copied().unwrap_or(106),
            if eof_second {
                30
            } else {
                154
            },
        ];
        let mut vm = ProfileMachine::from_state(
            profile,
            initial.memory().to_vec(),
            input.to_vec(),
            ProfileRegisters::default(),
        )
        .expect("isolated state");
        let mut reads = Vec::new();
        let mut outputs = Vec::new();
        let mut state_ops = Vec::new();
        let result = vm.run_traced(steps, &mut |step| {
            if let Some(value) = step.input {
                reads.push((step.before.registers.code_pointer, value));
            }
            if let Some(value) = step.output {
                outputs.push((step.before.registers.code_pointer, value));
            }
            if [14, 61, 62].contains(&step.before.registers.code_pointer) {
                state_ops.push((
                    step.before.registers.code_pointer,
                    step.decoded,
                    step.before.registers.data_pointer,
                    step.after.registers.accumulator,
                ));
            }
        });
        assert_eq!(
            result,
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps,
            }),
            "input={input:?}",
        );
        assert_eq!(vm.output(), output);
        assert_eq!(vm.input_consumed(), input.len().min(2));
        assert_eq!([vm.memory()[131], vm.memory()[132]], [
            first_fold,
            second_fold
        ]);
        assert_eq!(reads, [
            (
                53,
                input
                    .first()
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            ),
            (
                63,
                input
                    .get(1)
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            ),
        ]);
        assert_eq!(outputs, [
            (54, output[0]),
            (
                if eof_second {
                    128
                } else {
                    57
                },
                output[1]
            )
        ]);
        let expected_first_ops = [
            (14, Some(b'p'), 132, seeded),
            (61, Some(b'p'), 131, first_fold),
            (62, Some(b'p'), 132, second_fold),
        ];
        assert_eq!(state_ops.get(..3), Some(expected_first_ops.as_slice()));
        if eof_second {
            assert_eq!(state_ops.len(), 3);
        } else {
            // Both writes are encrypted to inert opcodes on the byte arm.
            assert_eq!(state_ops.len(), 5);
            assert_eq!(state_ops[3].0, 61);
            assert_eq!(state_ops[3].1, Some(b'A'));
            assert_eq!(state_ops[4].0, 62);
            assert_eq!(state_ops[4].1, Some(b't'));
        }
    }
}
