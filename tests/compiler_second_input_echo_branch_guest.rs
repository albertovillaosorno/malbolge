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
//   - Real first-input-dependent guest memory before second signed EOF branch.
// - Must-Not:
//   - Claim C32 lossless locals, source-C checksum or executable CFG lowering.
// - Allows:
//   - Inputs: one frozen N15 guest source and finite signed input streams.
//   - Outputs: independent trit-fold oracle and normative VM state/I/O paths.
//   - Side effects: bounded, isolated in-memory guest execution only.
// - Split-When:
//   - A general input-state linker implements full-width C guest state.
// - Merge-When:
//   - Physical signed EOF branch tests subsume the saved-input effect.
// - Summary:
//   - Save a lossy first-word EOF discriminator before overwriting A at C63.

//! Physically verify saved first-word state across a second EOF-dependent read.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, historical_profile,
};

const LOADER_OPERAND_AT_132: u32 = 7_174_350;
const TEST_MAX_STEPS: usize = 175;

// This oracle is an independently transcribed fifteen-trit truth table,
// rather than the VM's crazy primitive or the layout builder's code.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent small exact-finite trit arithmetic oracle"
)]
fn independent_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut word = 0;
    let mut place = 1;
    for _ in 0usize..15 {
        let trit = match (data % 3, accumulator % 3) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        word += trit * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    word
}

#[test]
fn first_eof_fold_is_provably_distinct_but_not_a_c32_local() {
    let profile = current_profile();
    let sentinel = independent_crazy(LOADER_OPERAND_AT_132, profile.eof_word());
    assert_eq!(sentinel, 14_348_673);
    let byte_words = (u8::MIN..=u8::MAX)
        .map(|byte| independent_crazy(LOADER_OPERAND_AT_132, u32::from(byte)))
        .collect::<BTreeSet<_>>();
    assert_eq!(byte_words.len(), 36);
    assert!(!byte_words.contains(&sentinel));
    assert_eq!(
        independent_crazy(LOADER_OPERAND_AT_132, 1),
        independent_crazy(LOADER_OPERAND_AT_132, 2),
        "the fold is not an injective 8-bit or C32 storage encoding",
    );
}

#[test]
#[expect(
    clippy::expect_used,
    reason = "negative physical source control must be loadable"
)]
fn stdout_parity_does_not_prove_a_saved_first_word() {
    let profile = current_profile();
    let real =
        layout::build_second_input_branch_with_first_eof_fold_source(profile)
            .expect("physical stateful candidate");
    let no_store =
        layout::build_second_input_eof_classified_first_echo_source(profile)
            .expect("physical output-only control");
    assert_ne!(real, no_store);
    let saved_init = ProfileMachine::from_source(profile, &real, Vec::new())
        .expect("candidate load");
    let unsaved_init =
        ProfileMachine::from_source(profile, &no_store, Vec::new())
            .expect("negative control load");
    for input in [&b""[..], &b"\x03"[..], &b"\x03\x04"[..]] {
        let mut saved = ProfileMachine::from_state(
            profile,
            saved_init.memory().to_vec(),
            input.to_vec(),
            ProfileRegisters::default(),
        )
        .expect("candidate state");
        let mut unsaved = ProfileMachine::from_state(
            profile,
            unsaved_init.memory().to_vec(),
            input.to_vec(),
            ProfileRegisters::default(),
        )
        .expect("negative control state");
        let steps = if input.len() < 2 {
            119
        } else {
            TEST_MAX_STEPS
        };
        assert_eq!(saved.run(steps), unsaved.run(steps));
        assert_eq!(saved.output(), unsaved.output());
        assert_ne!(saved.memory().get(132), unsaved.memory().get(132));
    }
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::expect_used,
    clippy::excessive_nesting,
    clippy::too_many_lines,
    reason = "one bounded whole-path VM witness with explicit assertion points"
)]
fn exact_guest_first_fold_survives_second_read_on_both_arms() {
    let profile = current_profile();
    let source =
        layout::build_second_input_branch_with_first_eof_fold_source(profile)
            .expect("current-profile source must encode");
    assert_eq!(source.len(), 132);
    assert_eq!(source.get(130..), Some(b"-}".as_slice()));
    assert_eq!(
        layout::build_second_input_branch_with_first_eof_fold_source(
            historical_profile()
        ),
        Err(layout::SignedEofBranchSourceError::UnsupportedProfile),
    );
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .expect("valid graphical N15 source");
    assert_eq!(loaded.memory().get(132), Some(&LOADER_OPERAND_AT_132));

    // The first word varies independently of the second, including same
    // first with opposite EOF outcomes and an intentionally unread suffix.
    let vectors: &[&[u8]] = &[
        &[],
        &[0],
        &[3],
        &[255],
        &[0, 0],
        &[3, 4],
        &[3, 255, 119],
        &[255, 0, 128],
    ];
    for &input in vectors {
        let eof_second = input.len() < 2;
        let first = input
            .first()
            .copied()
            .map_or_else(|| profile.eof_word(), u32::from);
        let fold = independent_crazy(LOADER_OPERAND_AT_132, first);
        let expected_steps = if eof_second {
            119
        } else {
            TEST_MAX_STEPS
        };
        let output = [
            input.first().copied().unwrap_or(106),
            if eof_second {
                30
            } else {
                154
            },
        ];
        let mut machine = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input.to_vec(),
            ProfileRegisters::default(),
        )
        .expect("independent source state");
        let mut writes_at_132 = Vec::new();
        let mut visits_at_62 = 0usize;
        let mut reads = Vec::new();
        let mut outputs = Vec::new();
        let outcome = machine.run_traced(expected_steps, &mut |step| {
            if let Some(write) = step.memory_delta.data
                && write.address == 132
            {
                writes_at_132.push((
                    step.before.registers.code_pointer,
                    write.before,
                    write.after,
                ));
            }
            if let Some(input_word) = step.input {
                reads.push((step.before.registers.code_pointer, input_word));
            }
            if let Some(output_byte) = step.output {
                outputs.push((step.before.registers.code_pointer, output_byte));
            }
            if step.before.registers.code_pointer == 62 {
                let opcode = if visits_at_62 == 0 {
                    b'p'
                } else {
                    b't'
                };
                assert_eq!(step.decoded, Some(opcode));
                if visits_at_62 != 0 {
                    assert_eq!(step.memory_delta.data, None);
                }
                visits_at_62 += 1;
            }
        });
        assert_eq!(
            outcome,
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: expected_steps,
            }),
            "stdin={input:?}",
        );
        assert_eq!(
            visits_at_62,
            if eof_second {
                1
            } else {
                2
            }
        );
        assert_eq!(machine.output(), output, "stdin={input:?}");
        assert_eq!(machine.input_consumed(), input.len().min(2));
        assert_eq!(machine.memory().get(132), Some(&fold), "stdin={input:?}");
        assert_eq!(
            writes_at_132,
            [(62, LOADER_OPERAND_AT_132, fold)],
            "the first input must be saved exactly once",
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
        ],);
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
        ],);
    }
}
