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
//   - Real one-read physical storage surviving nine C23 operand rotations.
// - Must-Not:
//   - Call a lossy saved word a source-C int or a complete C23 conversion.
// - Allows:
//   - Inputs: five signed N15 byte/EOF classes and a no-store control.
//   - Outputs: exact C38 guest write and C67 pointer provenance.
//   - Side effects: isolated, bounded normative N15 guest VM execution.
// - Split-When:
//   - A general source-C input conversion linker subsumes the fixed route.
// - Merge-When:
//   - The physical linker implements lossless one-read C23 value recovery.
// - Summary:
//   - A genuine single signed input controls a later pointer after rotations.

//! One-read saved-input late-pointer witness, not executable source-C lowering.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, RunOutcome, TraceInput, current_profile,
    decode_profile_instruction,
};

const FIRST_READ: usize = 37;
const INPUT_WRITE: usize = 38;
const LATE_READ: usize = 66;
const LATE_POINTER: usize = 67;
const SOURCE_DATA_WORD: u32 = 97;
const INITIAL_SOURCE_DATA: u32 = 7_174_404;
const INPUT_CLASSES: &[InputCase] = &[
    (None, &[]),
    (Some(0), &[0]),
    (Some(1), &[1, 222]),
    (Some(128), &[128]),
    (Some(255), &[255]),
];

type InputCase = (Option<u8>, &'static [u8]);

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::indexing_slicing,
    clippy::as_conversions,
    reason = "independent fixed 15-trit ternary digit oracle"
)]
fn scalar_crazy(mut left: u32, mut right: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0;
    let mut place = 1;
    for _ in 0u8..15 {
        result += TABLE[(left % 3) as usize][(right % 3) as usize] * place;
        left /= 3;
        right /= 3;
        place *= 3;
    }
    result
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::integer_division,
    reason = "independent fifteen-trit cyclic rotation oracle"
)]
const fn scalar_rotate(word: u32) -> u32 {
    word / 3 + word % 3 * 4_782_969
}

fn encoded(position: usize, opcode: u8) -> Result<u8, String> {
    let address = u32::try_from(position).map_err(|error| error.to_string())?;
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), address)
                == Some(opcode)
        })
        .ok_or_else(|| format!("no graphical opcode {opcode} at C{position}"))
}

#[expect(
    clippy::indexing_slicing,
    reason = "fixed 91-byte source with frozen in-range instruction sites"
)]
fn one_read_source(save_input: bool) -> Result<Vec<u8>, String> {
    let profile = current_profile();
    let mut source =
        layout::build_c23_nine_rotated_signed_output_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    source[INPUT_WRITE] = encoded(
        INPUT_WRITE,
        if save_input {
            b'p'
        } else {
            b'o'
        },
    )?;
    source[LATE_READ] = encoded(LATE_READ, b'o')?;
    layout::admit_c23_probe_graphical_source(&source)
        .map_err(|error| format!("{error:?}"))?;
    Ok(source)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::indexing_slicing,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "five finite normative guest traces and exact step assertions"
)]
fn one_signed_input_reaches_late_indirect_pointer_after_nine_rotations()
-> Result<(), String> {
    let profile = current_profile();
    let source = one_read_source(true)?;
    let no_save = one_read_source(false)?;
    assert_eq!(source.len(), 91);
    assert_eq!(source[INPUT_WRITE], encoded(INPUT_WRITE, b'p')?);
    assert_eq!(no_save[INPUT_WRITE], encoded(INPUT_WRITE, b'o')?);
    assert!(source.iter().enumerate().all(|(index, &byte)| {
        index == INPUT_WRITE || no_save[index] == byte
    }));
    let mut pointers = BTreeSet::new();
    for (first_byte, input) in INPUT_CLASSES {
        let mut vm =
            ProfileMachine::from_source(profile, &source, input.to_vec())
                .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let result = vm
            .run_traced(LATE_POINTER + 1, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(result, RunOutcome::BudgetExhausted {
            steps: LATE_POINTER + 1,
        });
        let first = &trace[FIRST_READ];
        assert_eq!(first.decoded, Some(b'/'));
        assert_eq!(
            first.input,
            Some(first_byte.map_or(TraceInput::EndOfInput, TraceInput::Byte,))
        );
        let store = &trace[INPUT_WRITE];
        assert_eq!(store.decoded, Some(b'p'));
        assert_eq!(
            store.memory_reads.data.map(|read| read.address),
            Some(SOURCE_DATA_WORD)
        );
        let input_word = first_byte.map_or(profile.eof_word(), u32::from);
        let stored = scalar_crazy(INITIAL_SOURCE_DATA, input_word);
        assert_eq!(
            store
                .memory_delta
                .data
                .map(|write| (write.address, write.after)),
            Some((SOURCE_DATA_WORD, stored))
        );
        assert_eq!(vm.memory_word(SOURCE_DATA_WORD), Ok(stored));
        let rotates = trace
            .iter()
            .filter(|step| {
                step.decoded == Some(b'*')
                    && step
                        .memory_reads
                        .data
                        .is_some_and(|read| read.address == 95)
            })
            .count();
        assert_eq!(rotates, 9);
        let operand =
            (0u8..9).fold(INITIAL_SOURCE_DATA, |word, _| scalar_rotate(word));
        assert_eq!(operand, 7_138_732);
        assert_eq!(vm.memory_word(95), Ok(operand));
        assert_eq!(vm.memory_word(96), Ok(121));
        let skipped = &trace[LATE_READ];
        assert_eq!(skipped.decoded, Some(b'o'));
        assert_eq!(skipped.input, None);
        let pointer = &trace[LATE_POINTER];
        assert_eq!(pointer.decoded, Some(b'j'));
        assert_eq!(
            pointer
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((SOURCE_DATA_WORD, stored))
        );
        assert_eq!(pointer.after.registers.data_pointer, stored + 1);
        assert!(pointers.insert(stored));
        assert_eq!(vm.output(), &[]);
        assert_eq!(vm.input_consumed(), usize::from(first_byte.is_some()));
    }
    // A real no-store mutation keeps the input and rotations but removes
    // the input-to-late-pointer dependency: C67 reads the virgin M97 seed.
    let mut control = ProfileMachine::from_source(profile, &no_save, vec![1])
        .map_err(|error| error.to_string())?;
    let mut control_trace = Vec::new();
    let control_result = control
        .run_traced(LATE_POINTER + 1, &mut |step| control_trace.push(*step))
        .map_err(|error| error.to_string())?;
    assert_eq!(control_result, RunOutcome::BudgetExhausted {
        steps: LATE_POINTER + 1,
    });
    assert_eq!(control_trace[INPUT_WRITE].decoded, Some(b'o'));
    assert_eq!(
        control_trace[LATE_POINTER]
            .memory_reads
            .data
            .map(|read| (read.address, read.value)),
        Some((SOURCE_DATA_WORD, INITIAL_SOURCE_DATA))
    );
    assert_eq!(pointers.len(), INPUT_CLASSES.len());
    Ok(())
}

#[test]
fn saved_input_is_lossy_but_distinguishes_genuine_eof() {
    let profile = current_profile();
    let bytes = (0u32..=255)
        .map(|input| scalar_crazy(INITIAL_SOURCE_DATA, input))
        .collect::<BTreeSet<_>>();
    assert_eq!(bytes.len(), 36);
    let eof = scalar_crazy(INITIAL_SOURCE_DATA, profile.eof_word());
    assert_eq!(eof, 14_348_700);
    assert!(!bytes.contains(&eof));
}
