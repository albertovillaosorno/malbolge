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
//   - A real all-byte executable arm reached through signed EOF control.
// - Must-Not:
//   - Claim that the EOF arm, runtime C loop, or checksum is implemented.
// - Allows:
//   - Inputs: one graphical N15 program and bounded binary/EOF streams.
//   - Outputs: independently checked arithmetic and normative guest traces.
//   - Side effects: isolated, bounded in-memory VM runs only.
// - Split-When:
//   - EOF also reaches a placed executable arm.
// - Merge-When:
//   - The C compiler lowers verified dynamic source branches to these arms.
// - Summary:
//   - Four real crazy writes bring successful bytes back into source code.

//! One real branch arm is executable after four data-dependent guest writes.
//! EOF still fails before the destination can execute.

use malbolge::{
    ProfileMachine, RunOutcome, Termination, current_profile,
    decode_profile_instruction,
};

const LENGTH: usize = 132;
const FIRST_OPERAND: u32 = 7_174_341;
const ROTATED_OPERAND: u32 = 3_618;
const THIRD_OPERAND: u32 = 7_174_350;
const FOURTH_OPERAND: u32 = 134;
const SUCCESS_CONTROL: u32 = 125;
const EOF_CONTROL: u32 = 368;

fn encode(opcode: u8, position: usize) -> u8 {
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(
                u32::from(*byte),
                u32::try_from(position).expect("bounded position"),
            ) == Some(opcode)
        })
        .expect("opcode has graphical encoding at the requested position")
}

fn guest_source() -> Vec<u8> {
    let mut source = (0..LENGTH)
        .map(|position| encode(b'o', position))
        .collect::<Vec<_>>();
    source[8] = encode(b'j', 8);
    for round in 0..12 {
        let position = 17 + round * 3;
        source[position] = encode(b'*', position);
        source[position + 1] = encode(b'j', position + 1);
        source[position + 2] = encode(b'j', position + 2);
    }
    source[53] = encode(current_profile().input_instruction(), 53);
    // D=135 after the input; one no-op reaches M[137]=125. A genuine j
    // then rewinds D to 126, and eight no-ops reach virgin loader M[134].
    source[55] = encode(b'j', 55);
    for position in 64..=66 {
        source[position] = encode(b'p', position);
    }
    // Skip virgin M[137] and M[138] to use M[139]=134 as fourth operand.
    source[69] = encode(b'p', 69);
    // M[142] -> 7,174,350; M[7,174,351] -> 134. Rewind and then
    // advance D to the written fourth result at M[139].
    source[72] = encode(b'j', 72);
    source[73] = encode(b'j', 73);
    source[78] = encode(b'i', 78);
    // The success control 125 first encrypts this still-graphical cell.
    // Execution then enters the previously skipped success arm at C=126.
    source[126] = encode(current_profile().output_instruction(), 126);
    source[127] = encode(b'v', 127);
    source[130] = b'-';
    source[131] = b'}';
    source
}

// Independent literal trit table, not the normative runtime implementation.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent exact 15-trit arithmetic oracle"
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

fn control(input: u32) -> u32 {
    let rotated = (0..12).fold(134, |word, _| scalar_rotate(word));
    assert_eq!(rotated, ROTATED_OPERAND);
    let first = scalar_crazy(FIRST_OPERAND, input);
    let second = scalar_crazy(rotated, first);
    let third = scalar_crazy(THIRD_OPERAND, second);
    scalar_crazy(FOURTH_OPERAND, third)
}

#[test]
fn independent_c23_byte_and_eof_control_words() {
    let profile = current_profile();
    assert_eq!(profile.word_trits(), 15);
    for byte in u8::MIN..=u8::MAX {
        assert_eq!(
            control(u32::from(byte)),
            SUCCESS_CONTROL,
            "successful input byte {byte}"
        );
    }
    assert_eq!(control(profile.eof_word()), EOF_CONTROL);
    assert_ne!(SUCCESS_CONTROL, EOF_CONTROL);
}

#[test]
fn all_successful_bytes_reach_graphical_output_arm_but_eof_does_not()
-> Result<(), String> {
    let profile = current_profile();
    let source = guest_source();
    assert_eq!(source.len(), LENGTH);
    assert_eq!(&source[130..], b"-}");
    for (position, &byte) in source.iter().enumerate() {
        let opcode = decode_profile_instruction(
            u32::from(byte),
            u32::try_from(position).expect("bounded position"),
        );
        if !matches!(
            opcode,
            Some(b'j' | b'i' | b'*' | b'p' | b'o' | b'<' | b'/' | b'v')
        ) {
            return Err(format!("invalid graphical instruction at {position}"));
        }
    }
    for input in [vec![0], vec![1], vec![0x80], vec![0xff], vec![]] {
        let eof = input.is_empty();
        let word = input
            .first()
            .map_or(profile.eof_word(), |byte| u32::from(*byte));
        let mut vm =
            ProfileMachine::from_source(profile, &source, input.clone())
                .map_err(|error| error.to_string())?;
        let mut trace = vec![];
        let outcome = vm.run_traced(82, &mut |step| trace.push(*step));
        for (position, address, operand) in [
            (64u32, 134u32, FIRST_OPERAND),
            (65, 135, ROTATED_OPERAND),
            (66, 136, THIRD_OPERAND),
            (69, 139, FOURTH_OPERAND),
            (72, 142, THIRD_OPERAND),
            (73, 7_174_351, 134),
        ] {
            let step = trace
                .iter()
                .find(|step| step.before.registers.code_pointer == position)
                .ok_or_else(|| format!("unreached C={position}"))?;
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, operand)),
                "C={position}"
            );
        }
        let branch = trace
            .iter()
            .find(|step| step.before.registers.code_pointer == 78)
            .ok_or("missing conditional i")?;
        assert_eq!(branch.decoded, Some(b'i'));
        assert_eq!(branch.before.registers.data_pointer, 139);
        assert_eq!(branch.before.registers.accumulator, control(word));
        assert_eq!(
            branch
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((139, control(word)))
        );
        if eof {
            // The VM rejects the unplaced EOF encryption target before
            // committing i. This is an explicit unsupported guest path.
            let error = outcome.expect_err("unplaced EOF arm must refuse");
            assert!(
                error.to_string().contains("self-encryption target 368"),
                "{error}"
            );
            assert_eq!(trace.len(), 79);
            assert_eq!(vm.memory_word(139), Ok(EOF_CONTROL));
            assert_eq!(vm.memory_word(368), Ok(7_174_341));
            assert!(vm.output().is_empty());
            assert_eq!(vm.input_consumed(), 0);
            continue;
        }
        assert_eq!(
            outcome.map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 81,
            },
            "input {input:?}"
        );
        assert_eq!(vm.memory_word(139), Ok(control(word)));
        assert_eq!(vm.input_consumed(), usize::from(!input.is_empty()));
        assert_eq!(branch.after.registers.code_pointer, 126);
        assert_eq!(trace.last().map(|step| step.decoded), Some(Some(b'v')));
        assert_eq!(vm.output(), b"}");
    }
    Ok(())
}
