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
//   - Actual one-read N15 lossless storage after five C23 operand rotations.
// - Must-Not:
//   - Claim remaining four rotations, source-C output or EOF loop execution.
// - Allows:
//   - Inputs: five real byte/EOF classes and all 257 scalar input words.
//   - Outputs: exact C43/M126 write, termination, and no-store counterexample.
//   - Side effects: isolated and bounded normative N15 guest VM execution.
// - Split-When:
//   - General source-C one-read conversion subsumes this physical probe.
// - Merge-When:
//   - A physical C23 runtime consumes the exact input-state cell.
// - Summary:
//   - Preserves first read injectively without overwriting converter operands.

//! A real source-loaded first-input store, not an executable C23 checksum.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;
use std::iter::once;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction,
};

const INPUT_CLASSES: &[Option<u8>] =
    &[None, Some(0), Some(1), Some(128), Some(255)];
const EXACT_DATA_ADDRESS: u32 = 126;
const EXACT_DATA_SEED: u32 = 121;

// Independent ternary table, not the production VM's crazy helper.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::unwrap_used,
    clippy::indexing_slicing,
    reason = "independent 15-trit table indices are always in 0..3"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut word = 0u32;
    let mut place = 1u32;
    for _ in 0..15u8 {
        let row = usize::try_from(data % 3).unwrap();
        let column = usize::try_from(accumulator % 3).unwrap();
        word += TABLE[row][column] * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    word
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::indexing_slicing,
    reason = "bounded N15 step-indexed source oracle"
)]
fn first_signed_read_is_saved_losslessly_after_five_real_rotations()
-> Result<(), String> {
    let profile = current_profile();
    let source = layout::build_c23_first_input_lossless_store_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..91), Some(b"Iy".as_slice()));
    assert_eq!(
        decode_profile_instruction(u32::from(source[67]), 67),
        Some(b'i')
    );
    assert_eq!(
        decode_profile_instruction(u32::from(source[43]), 43),
        Some(b'p')
    );
    assert_eq!(
        decode_profile_instruction(u32::from(source[44]), 44),
        Some(b'v')
    );
    let all_classes = (0u32..=255).chain(once(profile.eof_word()));
    assert_eq!(
        all_classes
            .map(|raw| scalar_crazy(EXACT_DATA_SEED, raw))
            .collect::<BTreeSet<_>>()
            .len(),
        257,
        "loader-backed M126 p must preserve every signed input class",
    );
    for first in INPUT_CLASSES {
        let stdin = first.map_or_else(Vec::new, |byte| vec![byte]);
        let mut vm = ProfileMachine::from_source(profile, &source, stdin)
            .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(45, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 45,
        });
        assert_eq!(trace.len(), 45);
        assert_eq!(trace[37].decoded, Some(b'/'));
        assert_eq!(
            trace[37].input,
            Some(first.map_or(TraceInput::EndOfInput, TraceInput::Byte)),
        );
        let expected = scalar_crazy(
            EXACT_DATA_SEED,
            first.map_or(profile.eof_word(), u32::from),
        );
        assert_eq!(trace[42].decoded, Some(b'j'));
        assert_eq!(
            trace[42]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((67, 125)),
        );
        assert_eq!(trace[43].decoded, Some(b'p'));
        assert_eq!(
            trace[43].memory_delta.data.map(|write| (
                write.address,
                write.before,
                write.after
            )),
            Some((EXACT_DATA_ADDRESS, EXACT_DATA_SEED, expected)),
        );
        assert_eq!(vm.memory_word(EXACT_DATA_ADDRESS), Ok(expected));
        assert_eq!(vm.memory_word(95), Ok(4_281_052));
        assert_eq!(vm.memory_word(96), Ok(121));
        assert_eq!(vm.input_consumed(), usize::from(first.is_some()));
        assert_eq!(vm.output(), []);
        assert_eq!(trace[44].decoded, Some(b'v'));
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::indexing_slicing,
    reason = "bounded no-store physical mutation and step-indexed VM assertions"
)]
fn absence_of_first_input_store_retains_loader_word() -> Result<(), String> {
    let profile = current_profile();
    let mut source =
        layout::build_c23_first_input_lossless_store_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    source[43] = (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), 43) == Some(b'o')
        })
        .ok_or("C43 must have a graphical no-op")?;
    let mut vm = ProfileMachine::from_source(profile, &source, vec![0xff])
        .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    assert_eq!(
        vm.run_traced(45, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 45,
        },
    );
    assert_eq!(trace[43].decoded, Some(b'o'));
    assert_eq!(trace[43].memory_delta.data, None);
    assert_eq!(vm.memory_word(EXACT_DATA_ADDRESS), Ok(EXACT_DATA_SEED));
    assert_ne!(scalar_crazy(EXACT_DATA_SEED, 255), EXACT_DATA_SEED,);
    Ok(())
}
