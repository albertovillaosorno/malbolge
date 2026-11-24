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

// Independent scalar check: eight rotations are ordinary 15-trit right
// rotations, not host-precomputed guest memory states.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "independent 15-trit cyclic word rotation"
)]
fn scalar_rotate(word: u32) -> u32 {
    word / 3 + word % 3 * 4_782_969
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::indexing_slicing,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "source-locked 66-step normative guest trace for five inputs"
)]
fn first_signed_input_survives_eighth_rotation_without_second_read()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_c23_first_input_saved_eight_rotations_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..91), Some(b"Iy".as_slice()));
    let initial = 7_174_404u32;
    let expected_eighth = (0u8..8).fold(initial, |word, _| scalar_rotate(word));
    assert_eq!(expected_eighth, 7_067_290);
    for first in INPUT_CLASSES {
        let stdin = first.map_or_else(Vec::new, |byte| vec![byte]);
        let mut vm = ProfileMachine::from_source(profile, &source, stdin)
            .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(66, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 66,
        });
        assert_eq!(trace.len(), 66);
        assert_eq!(trace[37].decoded, Some(b'/'));
        assert_eq!(
            trace[37].input,
            Some(first.map_or(TraceInput::EndOfInput, TraceInput::Byte))
        );
        let expected_store = scalar_crazy(
            EXACT_DATA_SEED,
            first.map_or(profile.eof_word(), u32::from),
        );
        assert_eq!(
            trace[43]
                .memory_delta
                .data
                .map(|write| (write.address, write.after)),
            Some((EXACT_DATA_ADDRESS, expected_store)),
        );
        assert_eq!(trace[44].decoded, Some(b'p'));
        assert_eq!(
            trace[44]
                .memory_delta
                .data
                .map(|write| (write.address, write.before)),
            Some((127, 7_174_404)),
        );
        for (round, position) in [50usize, 57, 64].iter().enumerate() {
            let previous =
                (0..(round + 5)).fold(initial, |word, _| scalar_rotate(word));
            let next = scalar_rotate(previous);
            assert_eq!(trace[*position].decoded, Some(b'*'));
            assert_eq!(
                trace[*position].memory_delta.data.map(|write| (
                    write.address,
                    write.before,
                    write.after
                )),
                Some((95, previous, next)),
            );
        }
        for reset in [49usize, 56, 63] {
            assert_eq!(
                trace[reset]
                    .memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((68, 94)),
            );
        }
        assert_eq!(trace[65].decoded, Some(b'v'));
        assert_eq!(vm.memory_word(95), Ok(expected_eighth));
        assert_eq!(vm.memory_word(96), Ok(121));
        assert_eq!(vm.memory_word(EXACT_DATA_ADDRESS), Ok(expected_store));
        assert_eq!(vm.input_consumed(), usize::from(first.is_some()));
        assert_eq!(vm.output(), []);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::indexing_slicing,
    reason = "bounded real no-store mutation following eight rotations"
)]
fn eighth_rotation_requires_the_original_input_write() -> Result<(), String> {
    let profile = current_profile();
    let mut source =
        layout::build_c23_first_input_saved_eight_rotations_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    source[43] = (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), 43) == Some(b'o')
        })
        .ok_or("no graphical no-op at C43")?;
    let mut vm = ProfileMachine::from_source(profile, &source, vec![255])
        .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    assert_eq!(
        vm.run_traced(66, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 66,
        },
    );
    assert_eq!(trace[43].decoded, Some(b'o'));
    assert_eq!(trace[43].memory_delta.data, None);
    assert_eq!(vm.memory_word(95), Ok(7_067_290));
    assert_eq!(vm.memory_word(96), Ok(121));
    assert_eq!(vm.memory_word(EXACT_DATA_ADDRESS), Ok(EXACT_DATA_SEED));
    assert_ne!(scalar_crazy(EXACT_DATA_SEED, 255), EXACT_DATA_SEED);
    assert_eq!(vm.output(), []);
    Ok(())
}

// Necessary, local source-code constraint, not a proof that other linker
// layouts cannot route around C67. A C48 physical write sees the C44 p result
// in A, so both candidate M67 effects use the exact source-locked operand.
#[test]
fn single_c48_mutation_cannot_restore_a_valid_ninth_rotation_code_site() {
    let profile = current_profile();
    let classes = (0u32..=255).chain(once(profile.eof_word()));
    let mutated = classes
        .map(|raw| {
            let saved = scalar_crazy(EXACT_DATA_SEED, raw);
            let second = scalar_crazy(7_174_404, saved);
            let changed_c67 = scalar_crazy(125, second);
            decode_profile_instruction(changed_c67, 67)
        })
        .collect::<Vec<_>>();
    assert_eq!(mutated.len(), 257);
    assert_eq!(
        mutated.iter().filter(|opcode| opcode.is_none()).count(),
        256
    );
    assert_eq!(
        mutated
            .iter()
            .filter(|opcode| **opcode == Some(b'p'))
            .count(),
        1
    );
    // One C48 rotation overwrites the fixed pointer source as well, but its
    // new C67 code word does not decode to any valid guest instruction.
    assert_eq!(scalar_rotate(125), 9_565_979);
    assert_eq!(decode_profile_instruction(scalar_rotate(125), 67), None);
}

/// A different source-loaded, single-read route bypasses the lossy M127
/// scratch and applies two identical M71/M72=121 crazy operands. The guest
/// output is exact for finite bytes, while real EOF remains non-C23.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::indexing_slicing,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "six independent normative N15 paths and source/word chronology"
)]
fn first_input_double_crazy_echoes_all_bytes_but_not_c23_eof()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_c23_first_input_two_crazy_byte_echo_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..91), Some(b"Iy".as_slice()));
    layout::admit_c23_probe_graphical_source(&source)
        .map_err(|error| format!("{error:?}"))?;
    for (position, value) in [
        (64usize, 70u8),
        (65, 69),
        (66, 68),
        (67, 67),
        (68, 65),
        (69, 64),
        (70, 63),
        (71, 121),
        (72, 121),
    ] {
        assert_eq!(source[position], value);
        assert!(
            decode_profile_instruction(u32::from(value), position as u32)
                .is_some_and(|opcode| b"oijp*/<v".contains(&opcode)),
            "source must remain loader-valid at position {position}",
        );
    }
    let all_inputs = (0u32..=255).chain(once(profile.eof_word()));
    let results = all_inputs
        .map(|raw| {
            scalar_crazy(EXACT_DATA_SEED, scalar_crazy(EXACT_DATA_SEED, raw))
        })
        .collect::<Vec<_>>();
    assert_eq!(results.len(), 257);
    assert_eq!(results.iter().copied().collect::<BTreeSet<_>>().len(), 257);
    for value in 0u32..=255 {
        assert_eq!(
            results[usize::try_from(value).map_err(|e| e.to_string())?],
            value
        );
    }
    assert_eq!(results[256], 7_174_574);
    assert_eq!(
        results[256] % 256,
        174,
        "true EOF must not masquerade as C23 0xff"
    );

    for first in [None, Some(0), Some(1), Some(128), Some(174), Some(255)] {
        let stdin = first.map_or_else(Vec::new, |byte| vec![byte]);
        let mut vm = ProfileMachine::from_source(profile, &source, stdin)
            .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(53, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 53,
            },
        );
        assert_eq!(trace.len(), 53);
        assert_eq!(trace[37].decoded, Some(b'/'));
        assert_eq!(
            trace[37].input,
            Some(first.map_or(TraceInput::EndOfInput, TraceInput::Byte)),
        );
        assert_eq!(trace[42].decoded, Some(b'j'));
        assert_eq!(
            trace[42]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((67, 67)),
        );
        for (index, (address, value)) in [
            (68u32, 65u32),
            (66, 68),
            (69, 64),
            (65, 69),
            (70, 63),
            (64, 70),
        ]
        .iter()
        .enumerate()
        {
            let step = &trace[43 + index];
            assert_eq!(step.decoded, Some(b'j'));
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((*address, *value)),
            );
        }
        let raw = first.map_or(profile.eof_word(), u32::from);
        let middle = scalar_crazy(EXACT_DATA_SEED, raw);
        let restored = scalar_crazy(EXACT_DATA_SEED, middle);
        assert_eq!(trace[49].decoded, Some(b'p'));
        assert_eq!(
            trace[49].memory_delta.data.map(|write| (
                write.address,
                write.before,
                write.after
            )),
            Some((71, EXACT_DATA_SEED, middle)),
        );
        assert_eq!(trace[50].decoded, Some(b'p'));
        assert_eq!(
            trace[50].memory_delta.data.map(|write| (
                write.address,
                write.before,
                write.after
            )),
            Some((72, EXACT_DATA_SEED, restored)),
        );
        assert_eq!(trace[51].decoded, Some(b'<'));
        assert_eq!(trace[51].output, Some((restored % 256) as u8));
        assert_eq!(trace[52].decoded, Some(b'v'));
        assert_eq!(vm.output(), [first.unwrap_or(174)]);
        assert_eq!(vm.memory_word(71), Ok(middle));
        assert_eq!(vm.memory_word(72), Ok(restored));
        assert_eq!(vm.memory_word(95), Ok(4_281_052));
        assert_eq!(vm.memory_word(96), Ok(121));
        assert_eq!(vm.input_consumed(), usize::from(first.is_some()));
    }
    Ok(())
}
