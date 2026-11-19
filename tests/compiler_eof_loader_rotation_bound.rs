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
//   - Finite lower bound for passive adjacent loader-derived EOF operands.
// - Must-Not:
//   - Treat arithmetic rotations as guest writes or publish C artifacts.
// - Allows:
//   - Inputs: all 94-by-94 graphical source tails and 12 loader phases.
//   - Outputs: independently checked 257-case conversion candidates.
//   - Side effects: one isolated in-memory VM loader witness.
// - Split-When:
//   - Executable guest code performs the actual repeated rotations and p/p.
// - Merge-When:
//   - Complete compiler data-placement search subsumes this finite family.
// - Summary:
//   - Exactly one rotation split works in the finite loader operand family.

//! Exact finite obstacle to cheap C23 signed EOF conversion operands.
//!
//! The candidate family comprises two adjacent loader-expanded data cells:
//! both may independently undergo 0..=14 rotations before their p reads.
//! This is NOT a lower bound for arbitrary Malbolge programs. In particular,
//! a guest can synthesize additional data words through p and other writes.

use malbolge::{ProfileMachine, current_profile, decode_profile_instruction};

const TRITS: usize = 15;
const WORD_MODULUS: u32 = 14_348_907;
const SOURCE_GRAPHICAL_START: u32 = 33;
const SOURCE_GRAPHICAL_END: u32 = 126;

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent fixed-width base-three scalar oracle"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0u32;
    let mut place = 1u32;
    for _ in 0..TRITS {
        let row = usize::try_from(data % 3).unwrap_or_default();
        let column = usize::try_from(accumulator % 3).unwrap_or_default();
        let digit = TABLE
            .get(row)
            .and_then(|digits| digits.get(column))
            .copied()
            .unwrap_or_default();
        result += digit * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::integer_division,
    reason = "single 15-trit cyclic right rotation"
)]
const fn scalar_rotate(word: u32) -> u32 {
    word / 3 + (word % 3) * (WORD_MODULUS / 3)
}

#[expect(
    clippy::integer_division_remainder_used,
    reason = "exact unsigned-char conversion at the C23 byte boundary"
)]
fn converted_output(first: u32, second: u32, input: u32) -> u32 {
    scalar_crazy(second, scalar_crazy(first, input)) % 256
}

fn admits_all_signed_c23_inputs(first: u32, second: u32, eof: u32) -> bool {
    for byte in 0..=255u32 {
        if converted_output(first, second, byte) != byte {
            return false;
        }
    }
    converted_output(first, second, eof) == 255
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    reason = "finite loader proof with test assertions"
)]
fn every_adjacent_graphical_loader_pair_needs_nine_first_rotations()
-> Result<(), String> {
    let profile = current_profile();
    assert_eq!(
        profile.word_trits(),
        u8::try_from(TRITS).map_err(|error| error.to_string())?
    );
    assert_eq!(profile.word_modulus(), WORD_MODULUS);
    let eof = profile.eof_word();
    // Screen byte 0, byte 1, high byte and true target EOF before the
    // 257-case independent proof. A sample match is never acceptance.
    let samples = [(0, 0), (1, 1), (255, 255), (eof, 255)];
    let mut candidates = Vec::new();
    for first_tail in SOURCE_GRAPHICAL_START..=SOURCE_GRAPHICAL_END {
        for second_tail in SOURCE_GRAPHICAL_START..=SOURCE_GRAPHICAL_END {
            let mut expanded = [0u32; 16];
            expanded[0] = first_tail;
            expanded[1] = second_tail;
            for position in 2..expanded.len() {
                expanded[position] = scalar_crazy(
                    expanded[position - 2],
                    expanded[position - 1],
                );
            }
            // The loader recurrence has a 12-word phase cycle for these
            // graphical seeds. Examine all phases, never a selected one.
            assert_eq!(&expanded[1..4], &expanded[13..16]);
            for phase in 0..12usize {
                let mut first_operand = expanded[phase + 2];
                for first_rotations in 0..TRITS {
                    let intermediate = samples
                        .map(|(input, _)| scalar_crazy(first_operand, input));
                    let mut second_operand = expanded[phase + 3];
                    for second_rotations in 0..TRITS {
                        if samples.iter().zip(intermediate).all(
                            |((_, expected), first_pass)| {
                                scalar_crazy(second_operand, first_pass) % 256
                                    == *expected
                            },
                        ) && admits_all_signed_c23_inputs(
                            first_operand,
                            second_operand,
                            eof,
                        ) {
                            candidates.push((
                                first_rotations,
                                second_rotations,
                                first_tail,
                                second_tail,
                                phase,
                                first_operand,
                                second_operand,
                            ));
                        }
                        second_operand = scalar_rotate(second_operand);
                    }
                    first_operand = scalar_rotate(first_operand);
                }
            }
        }
    }
    let expected = [72, 73, 75, 76]
        .into_iter()
        .flat_map(|first| {
            [4, 10].map(move |phase| (9, 0, first, 121, phase, 7_138_732, 121))
        })
        .collect::<Vec<_>>();
    assert_eq!(candidates, expected);

    // The known source at C89,C90 is a legitimate graphical tail for
    // phase four at M95,M96, not a license to claim nine actual writes.
    assert_eq!(decode_profile_instruction(73, 89), Some(b'o'));
    assert_eq!(decode_profile_instruction(121, 90), Some(b'/'));
    let mut source = (0..89u32)
        .map(|position| {
            (33..=126u8)
                .find(|byte| {
                    decode_profile_instruction(u32::from(*byte), position)
                        == Some(b'o')
                })
                .ok_or_else(|| format!("no graphical nop at C={position}"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    source.extend_from_slice(b"Iy");
    let vm = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| format!("graphical loader rejected: {error}"))?;
    let mut first = vm.memory_word(95).map_err(|error| error.to_string())?;
    let second = vm.memory_word(96).map_err(|error| error.to_string())?;
    for _ in 0usize..9 {
        first = scalar_rotate(first);
    }
    assert_eq!([first, second], [7_138_732, 121]);
    Ok(())
}
