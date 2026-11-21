// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier: Apache-2.0
//
// Boundary-Contract:
// - Owns: real guarded-third-read code-transfer and source-tail constraints.
// - Must-Not: treat a data-pointer reset as a C23 checksum or guest loop.
// - Allows: exact N15 traces, all source-valid two-cell loader tails.
// - Summary: a reached j changes the third-read state, but i still fails.

//! Attempt a genuine post-third-input control transfer in the signed EOF guest.
//! Physical read sites, self-encryption, and the source-tail loader period are
//! checked independently; this is a bounded failed linker experiment.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction,
};

fn graphical(position: u32, opcode: u8) -> Result<u8, String> {
    (33u8..=126)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), position)
                == Some(opcode)
        })
        .ok_or_else(|| format!("missing {opcode} at {position}"))
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent exact 15-trit loader recurrence"
)]
fn independent_crazy(mut left: u32, mut right: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0u32;
    let mut factor = 1u32;
    for _ in 0..15 {
        let row = usize::try_from(left % 3).unwrap_or_default();
        let column = usize::try_from(right % 3).unwrap_or_default();
        result += TABLE
            .get(row)
            .and_then(|values| values.get(column))
            .copied()
            .unwrap_or_default()
            * factor;
        factor *= 3;
        left /= 3;
        right /= 3;
    }
    result
}

#[test]
fn source_valid_tail_pairs_never_load_a_graphical_third_return_word()
-> Result<(), String> {
    let profile = current_profile();
    let eligible = |position: u32| {
        (33u8..=126)
            .filter(|byte| {
                decode_profile_instruction(u32::from(*byte), position)
                    .is_some_and(|op| b"oijp*/<v".contains(&op))
            })
            .collect::<Vec<_>>()
    };
    let mut examined = 0usize;
    for first in eligible(130) {
        for second in eligible(131) {
            let mut previous = u32::from(first);
            let mut last = u32::from(second);
            let mut generated = [0u32; 6];
            for word in &mut generated {
                *word = independent_crazy(previous, last);
                previous = last;
                last = *word;
            }
            // M7,174,402 lies four positions after the start of the
            // six-period source-loader recurrence at M132. Even permitting
            // all 64 valid tail pairs, that code-transfer word is never
            // graphical before a reached data instruction changes it.
            assert!(generated[4] > 126, "tail={first},{second}");
            examined += 1;
        }
    }
    assert_eq!(examined, 64);
    for (tail, expected) in [([45u8, 125], 7_174_350), ([97, 125], 7_174_339)] {
        let mut source =
            layout::build_two_input_class_state_with_guarded_third_read_source(
                profile,
            )
            .map_err(|error| format!("{error:?}"))?;
        source[130..].copy_from_slice(&tail);
        let machine = ProfileMachine::from_source(profile, &source, Vec::new())
            .map_err(|error| error.to_string())?;
        assert_eq!(machine.memory_word(7_174_402), Ok(expected));
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "explicit finite VM error and signed EOF negative oracle"
)]
fn graphical_second_pass_j_preserves_reads_but_fails_third_return()
-> Result<(), String> {
    let profile = current_profile();
    let mut source =
        layout::build_two_input_class_state_with_guarded_third_read_source(
            profile,
        )
        .map_err(|error| format!("{error:?}"))?;
    // C71 first pass emits the classifier accumulator and, after XLAT2,
    // its second visit executes j. C104 o avoids the ordinary second-pass
    // v halt; C112 p avoids its second-pass i, revealing C114's return.
    for (position, first) in [(71u32, b'<'), (104, b'o'), (112, b'p')] {
        source
            [usize::try_from(position).map_err(|error| error.to_string())?] =
            graphical(position, first)?;
    }
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    for (input, expected_reads, expected_output) in [
        (
            vec![3, 4, 5],
            vec![
                (53, TraceInput::Byte(3)),
                (63, TraceInput::Byte(4)),
                (101, TraceInput::Byte(5)),
            ],
            vec![3, 134, 154],
        ),
        (
            vec![3],
            vec![(53, TraceInput::Byte(3)), (63, TraceInput::EndOfInput)],
            vec![3, 121, 134],
        ),
    ] {
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut reads = Vec::new();
        let mut second_j = Vec::new();
        let mut returns = Vec::new();
        let outcome = vm.run_traced(190, &mut |step| {
            if let Some(value) = step.input {
                reads.push((step.before.registers.code_pointer, value));
            }
            if step.before.registers.code_pointer == 71
                && step.decoded == Some(b'j')
            {
                second_j.push((
                    step.before.registers.data_pointer,
                    step.after.registers.data_pointer,
                ));
            }
            if step.before.registers.code_pointer == 114 {
                returns.push((step.decoded, step.before.registers.accumulator));
            }
        });
        assert_eq!(reads, expected_reads);
        assert_eq!(vm.output(), expected_output);
        if input.len() == 3 {
            assert_eq!(second_j, [(7_174_359, 135)]);
            assert_eq!(returns.len(), 2);
            assert_eq!(returns[1], (Some(b'i'), 5));
            assert!(matches!(
                outcome,
                Err(malbolge::ProfileMachineError::InvalidEncryptionTarget {
                    pointer: 134,
                    value: 7_174_449,
                })
            ));
        } else {
            assert!(second_j.is_empty());
            assert_eq!(returns, [(Some(b'i'), 7_174_345)]);
            assert_eq!(
                outcome,
                Ok(RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 119,
                })
            );
        }
    }
    Ok(())
}
