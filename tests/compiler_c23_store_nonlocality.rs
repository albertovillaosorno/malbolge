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
//   - Proof that the real Iy C23 converter needs nonlocal EOF state routing.
// - Must-Not:
//   - Claim rotation or runtime branch linkage, or source-C compilation.
// - Allows:
//   - Inputs: exact Iy guest and 257 converted input classes.
//   - Outputs: real N15 traces and finite ternary locality bounds.
//   - Side effects: two isolated normative VM executions only.
// - Split-When:
//   - The complete C32 store linker subsumes this necessary condition.
// - Merge-When:
//   - A proven dynamic C32 store implementation replaces the obstruction.
// - Summary:
//   - More constant-operand crazy writes cannot create signed C32 EOF cells.

//! Exact obstacle to a C23 signed C32 store from the real Iy converter.
//!
//! The second physical input is converted by two reached guest p instructions
//! and left in M96: every successful byte becomes its exact unsigned word,
//! whereas true EOF becomes the distinct word `62_207` (not signed C -1).
//! Another chain of p operations, each with a constant data operand, cannot
//! map this result directly to both canonical C32 SSA cells. At the units
//! trit, successful byte 2 and converted EOF are indistinguishable, but the
//! C32 low and high EOF targets both require different units trits.
//!
//! This is a restricted physical obstruction, not a general impossibility:
//! branch-dependent control, runtime operands, rotation or a different source
//! may move the EOF flag between trit positions before storing C32 values.
//! A stronger finite census also rejects every one-rotation, fixed-crazy
//! chain by showing that even arbitrary unary maps on the fifteen rotated
//! trits cannot reproduce either full C32 cell across all 257 inputs.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::iter::once;

use layout::typed_cfg_adapter::state_storage::encode_i32_cells;
use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
};

const CONVERTED_EOF: u32 = 62_207;
const BYTE_TWO: u32 = 2;
const SECOND_READ_ADDRESS: u32 = 66;
const SECOND_CONVERT_ADDRESS: u32 = 78;
const SECOND_CONVERT_DESTINATION: u32 = 96;

// This record is an exact summary of C78's normative trace, rather than
// a fabricated guest C state or a replacement for the real VM.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct SecondInputWitness {
    observed_input: TraceInput,
    operand_address: u32,
    stored_word: u32,
    written_at: u32,
}

#[expect(
    clippy::integer_division_remainder_used,
    reason = "exact three-valued independent trit-locality proof"
)]
const fn units_trit(word: u32) -> u32 {
    word % 3
}

// Independent one-trit crazy table, transcribed from the normative ternary
// semantics. Never call the VM's production crazy primitive as its own oracle.
const fn independent_crazy_units(
    data_digit: u32,
    input_digit: u32,
) -> Option<u32> {
    match (data_digit, input_digit) {
        (0 | 1, 0) | (2, 2) => Some(1),
        (1, 2) | (2, 0 | 1) => Some(2),
        (0, 1 | 2) | (1, 1) => Some(0),
        _ => None,
    }
}

fn execute_second_input(
    source: &[u8],
    input: &[u8],
) -> Result<SecondInputWitness, String> {
    let profile = current_profile();
    let mut vm = ProfileMachine::from_source(profile, source, input.to_vec())
        .map_err(|error| error.to_string())?;
    let mut second_input = None;
    let mut conversion = None;
    let outcome = vm
        .run_traced(82, &mut |step| {
            let address = step.before.registers.code_pointer;
            if address == SECOND_READ_ADDRESS {
                second_input = step.input;
            }
            if address == SECOND_CONVERT_ADDRESS {
                conversion = Some((
                    address,
                    step.decoded,
                    step.before.registers.data_pointer,
                    step.memory_delta.data,
                ));
            }
        })
        .map_err(|error| error.to_string())?;
    if outcome
        != (RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 82,
        })
    {
        return Err(format!("physical converter did not halt: {outcome:?}"));
    }
    let observed_input = second_input.ok_or("missing physical second input")?;
    let (written_at, Some(b'p'), operand_address, Some(delta)) =
        conversion.ok_or("missing physical second conversion")?
    else {
        return Err("second conversion did not write physical data".to_owned());
    };
    if operand_address != SECOND_CONVERT_DESTINATION
        || delta.address != operand_address
    {
        return Err("C78 wrote outside the expected converter cell".to_owned());
    }
    let stored_word = vm
        .memory_word(SECOND_CONVERT_DESTINATION)
        .map_err(|error| error.to_string())?;
    if stored_word != delta.after {
        return Err("conversion did not persist in guest memory".to_owned());
    }
    Ok(SecondInputWitness {
        observed_input,
        operand_address,
        stored_word,
        written_at,
    })
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    reason = "bounded physical VM traces and finite trit locality proof"
)]
fn reached_c23_converter_needs_nonlocal_state_for_signed_eof()
-> Result<(), String> {
    let source =
        layout::build_c23_signed_output_with_post_conversion_fold_source(
            current_profile(),
        )
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..), Some(b"Iy".as_slice()));
    let success = execute_second_input(&source, &[0x5a, 2])?;
    let eof = execute_second_input(&source, &[0x5a])?;
    assert_eq!(success.observed_input, TraceInput::Byte(2));
    assert_eq!(eof.observed_input, TraceInput::EndOfInput);
    assert_eq!(success.stored_word, BYTE_TWO);
    assert_eq!(eof.stored_word, CONVERTED_EOF);
    assert_eq!(success.operand_address, SECOND_CONVERT_DESTINATION);
    assert_eq!(eof.operand_address, SECOND_CONVERT_DESTINATION);
    assert_eq!(success.written_at, SECOND_CONVERT_ADDRESS);
    assert_eq!(eof.written_at, SECOND_CONVERT_ADDRESS);

    let success_c32 = encode_i32_cells(BYTE_TWO);
    let eof_c32 = encode_i32_cells(u32::MAX);
    assert_eq!(eof_c32, [4_644_102, 299]);
    assert_eq!(success_c32, [2, 0]);

    // The two actual input states share the same low trit. But the required
    // C32 low word differs there, and so does the C32 high word.
    assert_eq!(units_trit(success.stored_word), units_trit(eof.stored_word));
    for (success_target, eof_target) in success_c32.into_iter().zip(eof_c32) {
        assert_ne!(units_trit(success_target), units_trit(eof_target));
    }

    // The normative crazy table depends only on its local input/data
    // trits. Exhaust the three unit operand choices for both *different*
    // full converter words. Equal local trits yield equal local results.
    // Inductively, every finite chain of constant-operand p remains
    // indistinguishable at this trit; neither exact C32 cell can result.
    for operand_units in 0u32..=2 {
        assert_eq!(
            independent_crazy_units(
                operand_units,
                units_trit(success.stored_word),
            ),
            independent_crazy_units(operand_units, units_trit(eof.stored_word),)
        );
    }
    Ok(())
}

// Each fixed-operand crazy composition acts separately on each ternary
// coordinate. Exactly one whole-word rotation only permutes those inputs;
// at each destination trit the result must be a unary function of the one
// source trit placed there. This oracle allows *every* unary function, even
// ones unavailable to Malbolge crazy, making any contradiction stronger.
#[expect(
    clippy::integer_division_remainder_used,
    reason = "independent canonical base-three coordinate oracle"
)]
fn ternary_digit(mut word: u32, index: usize) -> u32 {
    for _ in 0..index {
        word /= 3;
    }
    word % 3
}

#[test]
#[expect(
    clippy::excessive_nesting,
    clippy::integer_division_remainder_used,
    clippy::indexing_slicing,
    reason = "finite 15-rotation by 257-input mathematical locality census"
)]
fn one_rotation_and_constant_crazy_cannot_store_signed_c32() {
    const TRITS: usize = 15;
    const EOF_CELLS: [u32; 2] = [4_644_102, 299];
    let canonical_eof = encode_i32_cells(u32::MAX);
    assert_eq!(canonical_eof, EOF_CELLS);
    let mut minimum_conflicts = [TRITS; 2];
    for rotation_count in 0..TRITS {
        for word in 0..2usize {
            let mut conflicting_trits = 0usize;
            for destination_trit in 0..TRITS {
                let source_trit = (destination_trit + rotation_count) % TRITS;
                let mut mapped: [Option<u32>; 3] = [None; 3];
                let cases = (u8::MIN..=u8::MAX)
                    .map(|byte| (u32::from(byte), [u32::from(byte), 0]))
                    .chain(once((CONVERTED_EOF, EOF_CELLS)));
                let mut conflict = false;
                for (converted, targets) in cases {
                    let argument = ternary_digit(converted, source_trit);
                    let result = ternary_digit(targets[word], destination_trit);
                    let index = usize::try_from(argument).unwrap_or(usize::MAX);
                    let previous = &mut mapped[index];
                    if previous.is_some_and(|prior| prior != result) {
                        conflict = true;
                        break;
                    }
                    *previous = Some(result);
                }
                conflicting_trits += usize::from(conflict);
            }
            minimum_conflicts[word] =
                minimum_conflicts[word].min(conflicting_trits);
            assert!(
                conflicting_trits > 0,
                "word {word} could arise from one rotate {rotation_count} \
                 and a trit-local source mapping",
            );
        }
    }
    // Even an arbitrary per-trit unary map cannot repair every position.
    // The high word gets closest at 7 rotations, but one trit still fails.
    assert_eq!(minimum_conflicts, [10, 1]);
}
