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

use std::iter::once;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction,
};

const FIRST_DATA_ADDRESS: u32 = 135;
const DISCRIMINATOR_ADDRESS: u32 = 137;
const SUCCESS_NEXT_CODE: u32 = 7_174_224;
const EOF_NEXT_CODE: u32 = 378;

fn graphical(opcode: u8, position: usize) -> Result<u8, String> {
    let address = u32::try_from(position)
        .map_err(|error| format!("invalid address: {error}"))?;
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), address)
                == Some(opcode)
        })
        .ok_or_else(|| format!("no graphical encoding at {position}"))
}

fn set(source: &mut [u8], position: usize, opcode: u8) -> Result<(), String> {
    let cell = source
        .get_mut(position)
        .ok_or_else(|| format!("source position {position} is out of range"))?;
    *cell = graphical(opcode, position)?;
    Ok(())
}

fn classifier_with_real_jump() -> Result<Vec<u8>, String> {
    const LENGTH: usize = 132;
    let mut source = (0..LENGTH)
        .map(|position| graphical(b'o', position))
        .collect::<Result<Vec<_>, _>>()?;
    set(&mut source, 8, b'j')?;
    for round in 0usize..12 {
        let position = 17usize.saturating_add(round.saturating_mul(3));
        set(&mut source, position, b'*')?;
        set(&mut source, position.saturating_add(1), b'j')?;
        set(&mut source, position.saturating_add(2), b'j')?;
    }
    set(&mut source, 53, current_profile().input_instruction())?;
    set(&mut source, 54, b'j')?;
    set(&mut source, 55, b'j')?;
    for position in 56..=58 {
        set(&mut source, position, b'p')?;
    }
    // After the third p, D=138. The untouched loader recurrence provides
    // M[138]=7,174,350 and M[7,174,351]=134; two j steps reach D=135.
    // Two no-ops then bring D back to M[137], written by the last p.
    set(&mut source, 59, b'j')?;
    set(&mut source, 60, b'j')?;
    set(&mut source, 63, b'i')?;
    let tail = source
        .get_mut(130..132)
        .ok_or_else(|| "source tail is out of range".to_owned())?;
    tail.copy_from_slice(b"-}");
    Ok(source)
}

// Separate literal trit table instead of calling the normative VM helper.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent exact 15-trit arithmetic oracle"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TRITS: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut output = 0;
    let mut place = 1;
    for _ in 0usize..15 {
        let row = usize::try_from(data % 3).unwrap_or_default();
        let column = usize::try_from(accumulator % 3).unwrap_or_default();
        let digit = TRITS.get(row).and_then(|values| values.get(column));
        output += digit.copied().unwrap_or_default() * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    output
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::integer_division,
    reason = "independent exact 15-trit rotation"
)]
const fn scalar_rotate(word: u32) -> u32 {
    word / 3 + (word % 3) * 4_782_969
}

fn expected_jump_operand(input: u32) -> u32 {
    let rotated = (0usize..12).fold(134, |word, _| scalar_rotate(word));
    assert_eq!(rotated, 3_618, "twelve rotations must reach the seed");
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
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "bounded normative guest trace and independent scalar assertions"
)]
fn physical_i_reads_the_written_result_but_cannot_run_its_destinations()
-> Result<(), String> {
    let profile = current_profile();
    let source = classifier_with_real_jump()?;
    assert_eq!(source.len(), 132);
    assert_eq!(source.get(130..), Some(b"-}".as_slice()));
    for (position, byte) in source.iter().enumerate() {
        let decoded = decode_profile_instruction(
            u32::from(*byte),
            u32::try_from(position).map_err(|error| error.to_string())?,
        );
        if !matches!(
            decoded,
            Some(b'j' | b'i' | b'*' | b'p' | b'o' | b'<' | b'/' | b'v')
        ) {
            return Err(format!("invalid source opcode at C={position}"));
        }
    }

    // Construct the canonical 15-trit loader image once. Replaying 257
    // inputs through fresh validated states avoids needlessly rebuilding
    // fourteen million recurrence words per case.
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    for input in
        once(Vec::new()).chain((u8::MIN..=u8::MAX).map(|byte| vec![byte]))
    {
        let word = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let control_word = expected_jump_operand(word);
        let next_code = control_word + 1;
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
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
        let input_step = trace.get(53).ok_or("missing signed input step")?;
        assert_eq!(input_step.decoded, Some(profile.input_instruction()));
        assert_eq!(
            input_step.input,
            Some(input.first().map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            }))
        );
        for (step, address, operand) in [
            (56, FIRST_DATA_ADDRESS, 3_618),
            (57, 136, 7_174_350),
            (58, DISCRIMINATOR_ADDRESS, 125),
            (59, 138, 7_174_350),
            (60, 7_174_351, 134),
        ] {
            let guest = trace.get(step).ok_or("missing operand step")?;
            assert_eq!(
                guest
                    .memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, operand)),
                "step {step}"
            );
        }
        let branch = trace.get(63).ok_or("missing conditional i step")?;
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
        let destination = trace.get(64).ok_or("missing target fetch")?;
        assert_eq!(destination.before.registers.code_pointer, next_code);
        assert_eq!(destination.decoded, None);
        assert_eq!(vm.memory_word(next_code), Ok(7_174_350));
        assert_eq!(vm.input_consumed(), usize::from(!input.is_empty()));
        assert!(vm.output().is_empty());
    }
    Ok(())
}
