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
