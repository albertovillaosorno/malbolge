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
//   - A reached, all-byte/EOF-dependent i after real guest classification.
// - Must-Not:
//   - Claim a runnable branch destination or mutable-C checksum lowering.
// - Allows:
//   - Inputs: graphical N15 source and bounded stdin representatives.
//   - Outputs: independently proved operands and normative VM traces.
//   - Side effects: isolated bounded in-memory VM execution only.
// - Split-When:
//   - Both dynamic branch destinations have valid executable guest code.
// - Merge-When:
//   - The compiler emits independently verified source-C dynamic control.
// - Summary:
//   - Reaches real signed-EOF-dependent i with both destinations unplaced.

//! Data-dependent guest control follows three real crazy writes, with no
//! compiler-generated C loop or executable branch destination implied.

use malbolge::{
    ProfileMachine, RunOutcome, Termination, current_profile,
    decode_profile_instruction,
};

const FIRST_DATA_ADDRESS: u32 = 135;
const DISCRIMINATOR_ADDRESS: u32 = 137;
const SUCCESS_NEXT_CODE: u32 = 7_174_224;
const EOF_NEXT_CODE: u32 = 378;

fn graphical(opcode: u8, position: usize) -> u8 {
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(
                u32::from(*byte),
                u32::try_from(position).expect("bounded source position"),
            ) == Some(opcode)
        })
        .expect("all admitted positions have a graphical encoding")
}

fn classifier_with_real_jump() -> Vec<u8> {
    const LENGTH: usize = 132;
    let mut source = (0..LENGTH)
        .map(|position| graphical(b'o', position))
        .collect::<Vec<_>>();
    source[8] = graphical(b'j', 8);
    for round in 0..12 {
        let position = 17 + round * 3;
        source[position] = graphical(b'*', position);
        source[position + 1] = graphical(b'j', position + 1);
        source[position + 2] = graphical(b'j', position + 2);
    }
    source[53] = graphical(current_profile().input_instruction(), 53);
    source[54] = graphical(b'j', 54);
    source[55] = graphical(b'j', 55);
    for position in 56..=58 {
        source[position] = graphical(b'p', position);
    }
    // After the third p, D=138. The untouched loader recurrence provides
    // M[138]=7,174,350 and M[7,174,351]=134; two j steps reach D=135.
    // Two no-ops then bring D back to M[137], written by the last p.
    source[59] = graphical(b'j', 59);
    source[60] = graphical(b'j', 60);
    source[63] = graphical(b'i', 63);
    source[130] = b'-';
    source[131] = b'}';
    source
}

// Separate literal trit table instead of calling the normative VM helper.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent exact 15-trit arithmetic proof"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TRITS: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut output = 0;
    let mut place = 1;
    for _ in 0..15 {
        output +=
            TRITS[(data % 3) as usize][(accumulator % 3) as usize] * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    output
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent constant-width 15-trit rotation"
)]
fn scalar_rotate(word: u32) -> u32 {
    word / 3 + (word % 3) * 4_782_969
}

fn expected_jump_operand(input: u32) -> u32 {
    let rotated = (0..12).fold(134, |word, _| scalar_rotate(word));
    assert_eq!(rotated, 3_618);
    let first = scalar_crazy(rotated, input);
    let second = scalar_crazy(7_174_350, first);
    scalar_crazy(125, second)
}

#[test]
fn independent_257_case_scalar_oracle_proves_both_control_words() {
    let profile = current_profile();
    assert_eq!(profile.word_trits(), 15);
    for byte in u8::MIN..=u8::MAX {
        assert_eq!(
            expected_jump_operand(u32::from(byte)),
            SUCCESS_NEXT_CODE - 1,
            "successful input {byte}"
        );
    }
    assert_eq!(expected_jump_operand(profile.eof_word()), EOF_NEXT_CODE - 1);
    assert_ne!(SUCCESS_NEXT_CODE, EOF_NEXT_CODE);
}

#[test]
fn physical_i_reads_the_written_result_but_cannot_run_its_destinations()
-> Result<(), String> {
    let profile = current_profile();
    let source = classifier_with_real_jump();
    assert_eq!(source.len(), 132);
    assert_eq!(&source[130..], b"-}");
    for (position, byte) in source.iter().enumerate() {
        let decoded = decode_profile_instruction(
            u32::from(*byte),
            u32::try_from(position).expect("bounded source position"),
        );
        if !matches!(
            decoded,
            Some(b'j' | b'i' | b'*' | b'p' | b'o' | b'<' | b'/' | b'v')
        ) {
            return Err(format!("invalid source opcode at C={position}"));
        }
    }

    for input in [vec![], vec![0], vec![1], vec![128], vec![255]] {
        let word = input
            .first()
            .map_or(profile.eof_word(), |byte| u32::from(*byte));
        let control_word = expected_jump_operand(word);
        let next_code = control_word + 1;
        let mut vm =
            ProfileMachine::from_source(profile, &source, input.clone())
                .map_err(|error| error.to_string())?;
        let mut trace = vec![];
        let result = vm
            .run_traced(65, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(result, RunOutcome::Terminated {
            reason: Termination::NonGraphicalCell,
            steps: 65,
        });
        assert_eq!(trace.len(), 65);
        assert_eq!(trace[53].decoded, Some(profile.input_instruction()));
        for (step, address, operand) in [
            (56, FIRST_DATA_ADDRESS, 3_618),
            (57, 136, 7_174_350),
            (58, DISCRIMINATOR_ADDRESS, 125),
            (59, 138, 7_174_350),
            (60, 7_174_351, 134),
        ] {
            let guest = &trace[step];
            assert_eq!(
                guest
                    .memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, operand)),
                "step {step}"
            );
        }
        let branch = &trace[63];
        assert_eq!(branch.decoded, Some(b'i'));
        assert_eq!(branch.before.registers.code_pointer, 63);
        assert_eq!(branch.before.registers.data_pointer, DISCRIMINATOR_ADDRESS);
        assert_eq!(branch.before.registers.accumulator, control_word);
        assert_eq!(
            branch
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((DISCRIMINATOR_ADDRESS, control_word))
        );
        assert_eq!(branch.after.registers.code_pointer, next_code);
        assert_eq!(vm.memory_word(DISCRIMINATOR_ADDRESS), Ok(control_word));
        assert_eq!(trace[64].before.registers.code_pointer, next_code);
        assert_eq!(trace[64].decoded, None);
        assert_eq!(vm.memory_word(next_code), Ok(7_174_350));
        assert_eq!(vm.memory_word(next_code), Ok(7_174_350));
        assert_eq!(vm.input_consumed(), usize::from(!input.is_empty()));
        assert!(vm.output().is_empty());
    }
    Ok(())
}
