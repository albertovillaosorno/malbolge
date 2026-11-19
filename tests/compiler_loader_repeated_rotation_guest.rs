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
//   - Real repeated same-cell guest rotations with source-bound pointer reset.
// - Must-Not:
//   - Claim rotated 44/72 operands implement signed C23 conversion.
// - Allows:
//   - Inputs: exact N15 target and one through fifteen preparation rounds.
//   - Outputs: real rotate and jump traces, final byte from the actual VM.
//   - Side effects: bounded isolated normative VM execution.
// - Split-When:
//   - General repeated-data-operand synthesis subsumes the fixed reset chain.
// - Merge-When:
//   - P2 compiler can physically prepare C23 operands and link control.
// - Summary:
//   - Sixteen rounds collide with a fixed source pointer cell.

//! Real same-cell guest rotation with a source-validated three-jump reset.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, current_profile,
    historical_profile,
};

const WORD_MODULUS: u32 = 14_348_907;
const SEED_WORD: u32 = 7_174_457;

// Independent scalar rotation rather than calling the production helper.
#[expect(
    clippy::integer_division_remainder_used,
    reason = "independent 15-trit position-cycle oracle"
)]
const fn scalar_rotate(word: u32) -> u32 {
    word / 3 + (word % 3) * (WORD_MODULUS / 3)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "normative full trace is independently checked at each round"
)]
fn physical_reset_chain_rotates_one_loader_cell_repeatedly()
-> Result<(), String> {
    let profile = current_profile();
    for rotations in 1u8..=15 {
        let source =
            layout::build_repeated_loader_rotation_source(profile, rotations)
                .map_err(|error| format!("{error:?}"))?;
        assert_eq!(source.len(), 91);
        assert_eq!(source.get(89..), Some(b",H".as_slice()));
        let mut machine = ProfileMachine::from_source(profile, &source, vec![])
            .map_err(|error| error.to_string())?;
        assert_eq!(machine.memory_word(95), Ok(SEED_WORD));
        assert_eq!(machine.memory_word(96), Ok(72));
        let output_position = if rotations == 10 {
            41usize
        } else {
            usize::from(rotations) * 4
        };
        let mut trace = vec![];
        let result = machine
            .run_traced(64, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(result, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: output_position + 2,
        });
        assert_eq!(trace.len(), output_position + 2);
        let mut value = SEED_WORD;
        for round in 0..usize::from(rotations) {
            let position = 3 + round * 4;
            let rotation =
                trace.get(position).ok_or("missing guest rotation")?;
            assert_eq!(rotation.decoded, Some(b'*'));
            assert_eq!(rotation.before.registers.code_pointer, position as u32);
            assert_eq!(rotation.before.registers.data_pointer, 95);
            assert_eq!(
                rotation
                    .memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((95, value)),
            );
            value = scalar_rotate(value);
            assert_eq!(rotation.after.registers.accumulator, value);
            assert_eq!(
                rotation.memory_delta.data.map(|delta| delta.after),
                Some(value)
            );
            if round + 1 != usize::from(rotations) {
                for (offset, address, initial) in
                    [(1usize, 96u32, 72u32), (2, 73, 61), (3, 62, 94)]
                {
                    let reset = &trace[position + offset];
                    assert_eq!(reset.decoded, Some(b'j'));
                    assert_eq!(reset.before.registers.data_pointer, address);
                    assert_eq!(
                        reset.memory_reads.data.map(|read| read.value),
                        Some(initial),
                    );
                }
            }
        }
        assert_eq!(machine.memory_word(95), Ok(value));
        assert_eq!(machine.memory_word(97), Ok(7_174_493));
        assert_eq!(trace[output_position].decoded, Some(b'<'));
        assert_eq!(trace[output_position].output, Some((value % 256) as u8));
        assert_eq!(machine.output(), &[(value % 256) as u8]);
        assert_eq!(machine.input_consumed(), 0);
    }
    Ok(())
}

#[test]
fn incorrect_rotation_geometry_refuses_before_guest_publication() {
    assert_eq!(
        layout::build_repeated_loader_rotation_source(current_profile(), 0),
        Err(layout::RepeatedLoaderRotationError::InvalidRotationCount {
            rotations: 0
        }),
    );
    assert_eq!(
        layout::build_repeated_loader_rotation_source(current_profile(), 16),
        Err(layout::RepeatedLoaderRotationError::InvalidRotationCount {
            rotations: 16
        }),
    );
    assert_eq!(
        layout::build_repeated_loader_rotation_source(historical_profile(), 9),
        Err(layout::RepeatedLoaderRotationError::UnsupportedProfile),
    );
}

// Changing the loader tail is not an admissible way to reuse this reset
// chain for the separately proved C23 pair. The VM exposes the real defect.
#[test]
fn c23_seed_does_not_inherit_repeated_rotation_reset() -> Result<(), String> {
    let mut source =
        layout::build_repeated_loader_rotation_source(current_profile(), 2)
            .map_err(|error| format!("{error:?}"))?;
    source[89..91].copy_from_slice(b"Iy");
    let mut machine =
        ProfileMachine::from_source(current_profile(), &source, vec![])
            .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    let _ = machine
        .run_traced(9, &mut |step| trace.push(*step))
        .map_err(|error| error.to_string())?;
    assert_eq!(trace[3].before.registers.data_pointer, 95);
    assert_eq!(trace[3].decoded, Some(b'*'));
    assert_eq!(trace[4].before.registers.data_pointer, 96);
    assert_eq!(trace[5].before.registers.data_pointer, 122);
    assert_eq!(trace[6].before.registers.data_pointer, 158);
    assert_eq!(trace[7].before.registers.data_pointer, 158);
    assert_ne!(trace[7].before.registers.data_pointer, 95);
    Ok(())
}

// Exhaust the finite source-tail family rather than assuming that the one
// convenient `,H` tail is the only repeatable operand seed. The eight
// admitted tails yield distinct pre-rotation words but the same real M[96]
// pointer reset; this does not make them signed-C23 conversion operands.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independently checked finite seed class and physical VM traces"
)]
fn seeded_rotation_admits_exact_loader_tail_family() -> Result<(), String> {
    let expected = [
        ([44, 72], 7_174_457),
        ([45, 72], 7_174_462),
        ([67, 72], 7_174_480),
        ([73, 72], 7_174_489),
        ([86, 72], 7_174_418),
        ([103, 72], 7_174_435),
        ([104, 72], 7_174_436),
        ([122, 72], 7_174_454),
    ];
    let mut admitted = vec![];
    for first in 33u8..=126 {
        for second in 33u8..=126 {
            let tail = [first, second];
            match layout::build_seeded_repeated_loader_rotation_source(
                current_profile(),
                9,
                tail,
            ) {
                Ok(source) => {
                    assert_eq!(&source[89..91], &tail);
                    admitted.push(tail);
                },
                Err(
                    layout::RepeatedLoaderRotationError::InvalidResetSeed {
                        tail: rejected,
                    },
                ) => assert_eq!(rejected, tail),
                Err(error) => {
                    return Err(format!("unexpected seed error: {error:?}"));
                },
            }
        }
    }
    assert_eq!(
        admitted,
        expected.map(|(tail, _)| tail).to_vec(),
        "only source-valid tails with M[96]=72 may reset D to M[95]",
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "eight physical nine-rotation guest traces with scalar oracle"
)]
fn seeded_rotation_synthesizes_distinct_loader_words() -> Result<(), String> {
    let expected = [
        ([44, 72], 7_174_457),
        ([45, 72], 7_174_462),
        ([67, 72], 7_174_480),
        ([73, 72], 7_174_489),
        ([86, 72], 7_174_418),
        ([103, 72], 7_174_435),
        ([104, 72], 7_174_436),
        ([122, 72], 7_174_454),
    ];
    for (tail, first_word) in expected {
        let rounds = 9u8;
        let source = layout::build_seeded_repeated_loader_rotation_source(
            current_profile(),
            rounds,
            tail,
        )
        .map_err(|error| format!("{error:?}"))?;
        let mut vm =
            ProfileMachine::from_source(current_profile(), &source, vec![])
                .map_err(|error| error.to_string())?;
        assert_eq!(vm.memory_word(95), Ok(first_word));
        assert_eq!(vm.memory_word(96), Ok(72));
        let mut steps = vec![];
        let outcome = vm
            .run_traced(64, &mut |step| steps.push(*step))
            .map_err(|error| error.to_string())?;
        let output_at = usize::from(rounds) * 4;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: output_at + 2,
        });
        let mut word = first_word;
        for round in 0..usize::from(rounds) {
            let trace = &steps[3 + round * 4];
            assert_eq!(trace.decoded, Some(b'*'));
            assert_eq!(trace.before.registers.data_pointer, 95);
            assert_eq!(
                trace.memory_reads.data.map(|read| read.value),
                Some(word),
            );
            word = scalar_rotate(word);
            assert_eq!(trace.after.registers.accumulator, word);
        }
        assert_eq!(vm.memory_word(95), Ok(word));
        assert_eq!(vm.memory_word(96), Ok(72));
        assert_eq!(vm.output(), &[(word % 256) as u8]);
        assert_eq!(vm.input_consumed(), 0);
    }
    Ok(())
}

#[test]
fn invalid_seed_refuses_even_when_rotation_count_is_valid() {
    assert_eq!(
        layout::build_seeded_repeated_loader_rotation_source(
            current_profile(),
            9,
            *b"Iy",
        ),
        Err(layout::RepeatedLoaderRotationError::InvalidResetSeed {
            tail: *b"Iy",
        }),
    );
    assert_eq!(
        layout::build_seeded_repeated_loader_rotation_source(
            current_profile(),
            9,
            [0, 72],
        ),
        Err(layout::RepeatedLoaderRotationError::InvalidResetSeed {
            tail: [0, 72],
        }),
    );
}

// Physical composition proof: nine real rotations, one signed input, and
// two consecutive input-dependent p writes. These are deliberately the
// wrong operands for the C23 byte conversion used by the mutable checksum.
#[expect(
    clippy::integer_division_remainder_used,
    clippy::arithmetic_side_effects,
    reason = "independent 15-trit crazy table for normative VM comparison"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut result = 0u32;
    let mut place = 1u32;
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

#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    reason = "guest path and effects independently checked"
)]
fn prove_seeded_nine_rotations(
    tail: [u8; 2],
    seed: u32,
    inputs: impl Iterator<Item = Vec<u8>>,
) -> Result<(), String> {
    use malbolge::{ProfileRegisters, TraceInput};

    let profile = current_profile();
    let source = layout::build_seeded_rotated_input_crazy_source(profile, tail)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..), Some(tail.as_slice()));
    let loader = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(loader.memory_word(95), Ok(seed));
    assert_eq!(loader.memory_word(96), Ok(72));
    let rotated = (0..9).fold(seed, |word, _| scalar_rotate(word));
    for input in inputs {
        let first_byte = input.first().copied();
        let guest_word = first_byte.map_or(profile.eof_word(), u32::from);
        let first_crazy = scalar_crazy(rotated, guest_word);
        let second_crazy = scalar_crazy(72, first_crazy);
        let output = u8::try_from(second_crazy % 256)
            .map_err(|error| error.to_string())?;
        if first_byte.is_none() {
            assert_ne!(output, 0xff, "reset seeds do not convert C23 EOF");
        }
        let mut vm = ProfileMachine::from_state(
            profile,
            loader.memory().to_vec(),
            input,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut steps = vec![];
        let outcome = vm
            .run_traced(47, &mut |step| steps.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 47,
        });
        for round in 0..9 {
            let write = &steps[3 + round * 4];
            assert_eq!(write.decoded, Some(b'*'));
            assert_eq!(write.before.registers.data_pointer, 95);
            let expected = (0..round).fold(seed, |word, _| scalar_rotate(word));
            assert_eq!(
                write.memory_reads.data.map(|read| read.value),
                Some(expected)
            );
            assert_eq!(
                write.after.registers.accumulator,
                scalar_rotate(expected)
            );
        }
        for (position, data_pointer) in
            [(36, 96), (37, 73), (38, 62), (40, 96), (41, 73), (42, 62)]
        {
            assert_eq!(steps[position].decoded, Some(b'j'));
            assert_eq!(
                steps[position].before.registers.data_pointer,
                data_pointer
            );
        }
        assert_eq!(steps[39].decoded, Some(profile.input_instruction()));
        assert_eq!(steps[39].before.registers.data_pointer, 95);
        assert_eq!(
            steps[39].input,
            Some(first_byte.map_or(TraceInput::EndOfInput, TraceInput::Byte))
        );
        for (position, address, before, after) in
            [(43, 95, rotated, first_crazy), (44, 96, 72, second_crazy)]
        {
            let write = &steps[position];
            assert_eq!(write.decoded, Some(b'p'));
            assert_eq!(write.before.registers.data_pointer, address);
            assert_eq!(
                write.memory_reads.data.map(|read| read.value),
                Some(before)
            );
            assert_eq!(write.after.registers.accumulator, after);
            assert_eq!(vm.memory_word(address), Ok(after));
        }
        assert_eq!(steps[45].decoded, Some(profile.output_instruction()));
        assert_eq!(steps[45].output, Some(output));
        assert_eq!(steps[46].decoded, Some(b'v'));
        assert_eq!(vm.output(), &[output]);
        assert_eq!(vm.input_consumed(), usize::from(first_byte.is_some()));
    }
    Ok(())
}

#[test]
fn seeded_nine_rotation_input_byte_00_3f() -> Result<(), String> {
    // Also exercise true EOF and prove the unread suffix survives the halt.
    let inputs = std::iter::once(Vec::new())
        .chain((0..=63u8).map(|byte| vec![byte]))
        .chain(std::iter::once(vec![127, 128, 255]));
    prove_seeded_nine_rotations(*b",H", 7_174_457, inputs)
}

#[test]
fn seeded_nine_rotation_input_byte_40_7f() -> Result<(), String> {
    prove_seeded_nine_rotations(
        *b",H",
        7_174_457,
        (64..=127u8).map(|byte| vec![byte]),
    )
}

#[test]
fn seeded_nine_rotation_input_byte_80_bf() -> Result<(), String> {
    prove_seeded_nine_rotations(
        *b",H",
        7_174_457,
        (128..=191u8).map(|byte| vec![byte]),
    )
}

#[test]
fn seeded_nine_rotation_input_byte_c0_ff() -> Result<(), String> {
    prove_seeded_nine_rotations(
        *b",H",
        7_174_457,
        (192..=255u8).map(|byte| vec![byte]),
    )
}

#[test]
fn seeded_nine_rotation_other_loader_tails() -> Result<(), String> {
    for (tail, seed) in [
        (*b"-H", 7_174_462),
        (*b"CH", 7_174_480),
        (*b"IH", 7_174_489),
        (*b"VH", 7_174_418),
        (*b"gH", 7_174_435),
        (*b"hH", 7_174_436),
        (*b"zH", 7_174_454),
    ] {
        let inputs = std::iter::once(Vec::new())
            .chain([0u8, 1, 127, 128, 255].map(|byte| vec![byte]))
            .chain(std::iter::once(vec![127, 128, 255]));
        prove_seeded_nine_rotations(tail, seed, inputs)?;
    }
    Ok(())
}

#[test]
fn signed_crazy_probe_refuses_invalid_seed_or_profile() {
    assert_eq!(
        layout::build_seeded_rotated_input_crazy_source(
            current_profile(),
            *b"Iy",
        ),
        Err(layout::RepeatedLoaderRotationError::InvalidResetSeed {
            tail: *b"Iy",
        }),
    );
    assert_eq!(
        layout::build_seeded_rotated_input_crazy_source(
            historical_profile(),
            *b",H",
        ),
        Err(layout::RepeatedLoaderRotationError::UnsupportedProfile),
    );
}

// Real source-locked pointer-repair attempt on the correct C23 loader seed.
// At C37 the required pointer byte decodes as `/`, ending preparation after
// five rotations rather than silently substituting host-side nine rotations.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "physical seed rotations and input have independent full traces"
)]
fn c23_seed_loader_pointer_repair_rotates_and_reads_signed_input()
-> Result<(), String> {
    use malbolge::{ProfileRegisters, TraceInput};

    let profile = current_profile();
    let source = layout::build_c23_seed_rotated_input_echo_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(&source[89..91], b"Iy");
    let loader = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(loader.memory_word(94), Ok(157));
    assert_eq!(loader.memory_word(95), Ok(7_174_404));
    assert_eq!(loader.memory_word(96), Ok(121));
    assert_eq!(loader.memory_word(158), Ok(157));
    for input in [
        vec![],
        vec![0],
        vec![1],
        vec![127],
        vec![128],
        vec![255],
        vec![1, 0, 128, 254],
        vec![5, 0, 129],
    ] {
        let first = input.first().copied();
        let word = first.map_or(profile.eof_word(), u32::from);
        let mut vm = ProfileMachine::from_state(
            profile,
            loader.memory().to_vec(),
            input,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = vec![];
        let outcome = vm
            .run_traced(40, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 40,
        });
        assert_eq!(trace[2].decoded, Some(b'p'));
        assert_eq!(trace[2].before.registers.data_pointer, 94);
        assert_eq!(
            trace[2].memory_delta.data.map(|delta| delta.after),
            Some(7_174_489)
        );
        assert_eq!(trace[6].decoded, Some(b'p'));
        assert_eq!(trace[6].before.registers.data_pointer, 158);
        assert_eq!(
            trace[6].memory_delta.data.map(|delta| delta.after),
            Some(36)
        );
        for (index, address) in [
            (0usize, 0u32),
            (1, 41),
            (4, 96),
            (5, 122),
            (8, 160),
            (9, 158),
            (10, 37),
            (11, 81),
        ] {
            assert_eq!(trace[index].decoded, Some(b'j'));
            assert_eq!(trace[index].before.registers.data_pointer, address);
        }
        let mut operand = 7_174_404;
        for round in 0..5usize {
            let position = 12 + round * 6;
            let rotation = &trace[position];
            assert_eq!(rotation.decoded, Some(b'*'));
            assert_eq!(rotation.before.registers.data_pointer, 95);
            assert_eq!(
                rotation.memory_reads.data.map(|read| read.value),
                Some(operand)
            );
            operand = scalar_rotate(operand);
            assert_eq!(rotation.after.registers.accumulator, operand);
            if round != 4 {
                for (offset, pointer) in
                    [(1usize, 96u32), (2, 122), (3, 158), (4, 37), (5, 81)]
                {
                    let reset = &trace[position + offset];
                    assert_eq!(reset.decoded, Some(b'j'));
                    assert_eq!(reset.before.registers.data_pointer, pointer);
                }
            }
        }
        assert_eq!(operand, 4_281_052);
        assert_ne!(operand, 7_138_732, "nine rotations are still missing");
        assert_eq!(vm.memory_word(95), Ok(operand));
        assert_eq!(vm.memory_word(96), Ok(121));
        assert_eq!(vm.memory_word(158), Ok(36));
        assert_eq!(trace[37].decoded, Some(profile.input_instruction()));
        assert_eq!(trace[37].before.registers.data_pointer, 96);
        assert_eq!(
            trace[37].input,
            Some(first.map_or(TraceInput::EndOfInput, TraceInput::Byte)),
        );
        assert_eq!(trace[38].decoded, Some(profile.output_instruction()));
        assert_eq!(trace[38].output, Some((word % 256) as u8));
        assert_eq!(trace[39].decoded, Some(b'v'));
        assert_eq!(vm.output(), &[(word % 256) as u8]);
        assert_eq!(vm.input_consumed(), usize::from(first.is_some()));
    }
    Ok(())
}

#[test]
fn c23_seed_pointer_repair_refuses_historical_profile() {
    assert_eq!(
        layout::build_c23_seed_rotated_input_echo_source(historical_profile()),
        Err(layout::RepeatedLoaderRotationError::UnsupportedProfile),
    );
}
