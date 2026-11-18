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
//   - A placed EOF operand and a separate bounded dynamic guest branch.
// - Must-Not:
//   - Claim a complete EOF branch, arbitrary byte control, or C lowering.
// - Allows:
//   - Inputs: graphical N15 guests and explicitly bounded binary inputs.
//   - Outputs: actual guest memory reads, writes, and VM outcome.
//   - Side effects: bounded independent normative VM execution.
// - Split-When:
//   - A linked two-operand guest EOF branch replaces this placement witness.
// - Merge-When:
//   - The compiler constructs both data operands and branches on EOF.
// - Summary:
//   - Traces real operand writes and selected input-dependent i jumps.

//! Physical operands and a limited input-dependent branch in the N15 VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use layout::{
    LinearOpcode, admit_c23_eof_control_word_plan, encode_linear_layout,
};
use malbolge::{
    ProfileMachine, RunOutcome, Termination, current_profile, profile_crazy,
};

const FIRST_DATA_WORD: u32 = 7_174_332;
const LOADER_SEED: [u8; 2] = [81, 125];
const LENGTH: usize = 38;

fn source() -> Result<Vec<u8>, String> {
    let mut code = vec![LinearOpcode::NoOperation; LENGTH];
    code[0] = LinearOpcode::InputWord;
    code[3] = LinearOpcode::RelocateDataPointer;
    code[4] = LinearOpcode::CrazyData;
    code[5] = LinearOpcode::OutputByte;
    code[35] = LinearOpcode::Halt;
    code[36] = LinearOpcode::SkippedDataByte {
        byte: u32::from(LOADER_SEED[0]),
    };
    code[37] = LinearOpcode::SkippedDataByte {
        byte: u32::from(LOADER_SEED[1]),
    };
    let plan = encode_linear_layout(current_profile(), &code)
        .map_err(|error| format!("first operand placement: {error:?}"))?;
    assert_eq!(plan.source().len(), LENGTH);
    assert_eq!(&plan.source()[36..], &LOADER_SEED);
    assert_eq!(plan.data_write_positions()[4], Some(38));
    Ok(plan.source().to_vec())
}

#[test]
fn one_eof_discriminator_operand_is_real_guest_loader_data()
-> Result<(), String> {
    let profile = current_profile();
    let reduced =
        admit_c23_eof_control_word_plan(profile, [FIRST_DATA_WORD, 728], [
            728, 485,
        ])
        .expect("257-case one-write EOF discriminator");
    assert_eq!(reduced.mandatory_runtime_operand_writes(), [false, true]);
    assert_eq!(reduced.next_code_addresses(), [729, 486]);
    let source = source()?;
    assert_eq!(
        profile_crazy(81, 125, profile.word_trits()),
        FIRST_DATA_WORD
    );
    for input in [vec![], vec![0], vec![0x80], vec![0xff]] {
        let input_word = input
            .first()
            .map_or(profile.eof_word(), |byte| u32::from(*byte));
        let expected =
            profile_crazy(FIRST_DATA_WORD, input_word, profile.word_trits());
        let mut machine =
            ProfileMachine::from_source(profile, &source, input.clone())
                .map_err(|error| error.to_string())?;
        assert_eq!(machine.memory_word(38), Ok(FIRST_DATA_WORD));
        let mut trace = vec![];
        let outcome = machine
            .run_traced(36, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 36,
        });
        assert_eq!(trace[0].decoded, Some(profile.input_instruction()));
        assert_eq!(trace[4].decoded, Some(b'p'));
        let read = trace[4].memory_reads.data.ok_or("missing p data read")?;
        assert_eq!((read.address, read.value), (38, FIRST_DATA_WORD));
        assert_eq!(machine.memory_word(38), Ok(expected));
        assert_eq!(machine.input_consumed(), usize::from(!input.is_empty()));
    }
    Ok(())
}

// A distinct, strictly bounded instruction-level bridge: input-dependent
// control flow is real, but only the selected successful bytes are safe.
// It is not the all-257-input C23 EOF discriminator above.
fn binary_branch_source() -> Result<Vec<u8>, String> {
    use malbolge::decode_profile_instruction;

    const LENGTH: usize = 136;
    let encode = |instruction: u8, position: usize| -> Result<u8, String> {
        (33..=126u8)
            .find(|value| {
                decode_profile_instruction(
                    u32::from(*value),
                    u32::try_from(position).expect("bounded source position"),
                ) == Some(instruction)
            })
            .ok_or_else(|| format!("no encoding at {position}"))
    };
    let mut source = (0..LENGTH)
        .map(|position| encode(b'o', position))
        .collect::<Result<Vec<_>, _>>()?;
    // The first i jumps from C=0 to C=99, encrypting cell 98 on the way.
    source[0] = encode(b'i', 0)?;
    assert_eq!(source[0], 98);
    // Branches jump back into the original skipped region. For NUL, C=7
    // outputs A=6 then halts at 8; for byte 1, C=8 halts immediately.
    source[7] = encode(b'<', 7)?;
    source[8] = encode(b'v', 8)?;
    // A deliberate second j at C=116 reads source[18]=50 (skipped) and
    // arranges D=65 at C=131. The source[65]=97 word then places D=98.
    source[18] = 50;
    source[65] = 97;
    // Actual operands are in *past* graphical source cells, not the
    // untouched expanded loader. i at C=0 first encrypts 64 to 81;
    // execution at C=99 encrypts 63 to 43. Output at C=100 encrypts 93
    // to 98, later becoming the j operand that revisits mutated cell 99.
    source[98] = 64;
    source[99] = encode(b'o', 99)?;
    source[100] = encode(b'<', 100)?;
    source[101] = encode(current_profile().input_instruction(), 101)?;
    source[116] = encode(b'j', 116)?;
    source[131] = encode(b'j', 131)?;
    source[132] = encode(b'p', 132)?;
    source[133] = encode(b'p', 133)?;
    source[134] = encode(b'j', 134)?;
    source[135] = encode(b'i', 135)?;
    for (position, byte) in source.iter().enumerate() {
        let decoded = decode_profile_instruction(
            u32::from(*byte),
            u32::try_from(position).expect("bounded source position"),
        );
        if !matches!(
            decoded,
            Some(b'j' | b'i' | b'*' | b'p' | b'o' | b'<' | b'/' | b'v')
        ) {
            return Err(format!("source invalid at {position}: {decoded:?}"));
        }
    }
    Ok(source)
}

#[test]
fn binary_input_takes_two_real_crazy_and_distinct_guest_jump_paths()
-> Result<(), String> {
    use malbolge::encrypt_profile_cell;

    let profile = current_profile();
    let source = binary_branch_source()?;
    assert_eq!(encrypt_profile_cell(u32::from(source[98])), Some(81));
    assert_eq!(encrypt_profile_cell(u32::from(source[99])), Some(43));
    assert_eq!(encrypt_profile_cell(u32::from(source[100])), Some(98));
    for (input, final_word, expected_output, final_path, expected_steps) in [
        (0u8, 6u32, vec![0, 6], vec![7, 8], 40usize),
        (1u8, 7u32, vec![0], vec![8], 39usize),
    ] {
        let mut vm = ProfileMachine::from_source(profile, &source, vec![input])
            .map_err(|error| error.to_string())?;
        let mut trace = vec![];
        let outcome = vm
            .run_traced(128, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: expected_steps,
        });
        assert_eq!(trace.len(), expected_steps);
        let path = trace
            .iter()
            .map(|step| step.before.registers.code_pointer)
            .collect::<Vec<_>>();
        assert_eq!(path.first(), Some(&0));
        assert_eq!(path.get(1), Some(&99));
        assert!(path.ends_with(&final_path));
        for (position, opcode, d, word) in [
            (116u32, b'j', 18u32, 50u32),
            (131, b'j', 65, 97),
            (132, b'p', 98, 81),
            (133, b'p', 99, 43),
            (134, b'j', 100, 98),
            (135, b'i', 99, final_word),
        ] {
            let step = trace
                .iter()
                .find(|step| step.before.registers.code_pointer == position)
                .ok_or_else(|| {
                    format!("missing instruction at C={position}")
                })?;
            assert_eq!(step.decoded, Some(opcode));
            let read = step.memory_reads.data.ok_or("missing data read")?;
            assert_eq!((read.address, read.value), (d, word), "C={position}");
        }
        assert_eq!(
            trace
                .iter()
                .filter(|step| step.decoded == Some(b'p'))
                .count(),
            2
        );
        assert_eq!(vm.memory_word(99), Ok(final_word));
        assert_eq!(vm.input_consumed(), 1);
        assert_eq!(vm.output(), expected_output);
    }
    Ok(())
}

// A standalone real guest classifier, not yet linked to the C frontend or
// control-flow lowering. It leaves the successful-byte and EOF outcomes in
// distinct accumulator words and emits their low bytes. Both outcomes have
// been checked for *every* C23 getchar value by an independent trit oracle.
fn executable_eof_classifier_source() -> Result<Vec<u8>, String> {
    use malbolge::decode_profile_instruction;

    const LENGTH: usize = 132;
    let encode = |opcode: u8, position: usize| -> Result<u8, String> {
        (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(
                    u32::from(*byte),
                    u32::try_from(position).expect("bounded code position"),
                ) == Some(opcode)
            })
            .ok_or_else(|| format!("no {opcode} encoding at {position}"))
    };
    let mut source = (0..LENGTH)
        .map(|position| encode(b'o', position))
        .collect::<Result<Vec<_>, _>>()?;
    // The first j moves D=8 to D=127. Eight no-ops advance it to 135.
    source[8] = encode(b'j', 8)?;
    assert_eq!(source[8], 126);
    // The loader seed '-}' gives M[135]=134, M[136]=7,174,350 and
    // M[7,174,351]=134. The two j instructions per rotation therefore
    // return D to 135 without changing the rotated operand or its neighbor.
    for round in 0..12 {
        source[17 + round * 3] = encode(b'*', 17 + round * 3)?;
        source[18 + round * 3] = encode(b'j', 18 + round * 3)?;
        source[19 + round * 3] = encode(b'j', 19 + round * 3)?;
    }
    source[53] = encode(current_profile().input_instruction(), 53)?;
    source[54] = encode(b'j', 54)?;
    source[55] = encode(b'j', 55)?;
    source[56] = encode(b'p', 56)?;
    source[57] = encode(b'p', 57)?;
    source[58] = encode(b'p', 58)?;
    source[59] = encode(b'<', 59)?;
    source[60] = encode(b'v', 60)?;
    source[130] = 45;
    source[131] = 125;
    for (position, byte) in source.iter().enumerate() {
        let decoded = decode_profile_instruction(
            u32::from(*byte),
            u32::try_from(position).expect("bounded source position"),
        );
        if !matches!(
            decoded,
            Some(b'j' | b'i' | b'*' | b'p' | b'o' | b'<' | b'/' | b'v')
        ) {
            return Err(format!(
                "invalid physical source at {position}: {decoded:?}"
            ));
        }
    }
    Ok(source)
}

// Separate digitwise table, not an invocation of the normative VM primitive.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "fixed-width 15-trit independent arithmetic proof"
)]
fn independent_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0;
    let mut power = 1;
    for _ in 0..15 {
        result +=
            TABLE[(data % 3) as usize][(accumulator % 3) as usize] * power;
        data /= 3;
        accumulator /= 3;
        power *= 3;
    }
    result
}

#[test]
#[expect(
    clippy::integer_division_remainder_used,
    reason = "independent rotation oracle over exactly fifteen trits"
)]
fn physical_guest_distinguishes_every_c23_byte_from_signed_eof()
-> Result<(), String> {
    let profile = current_profile();
    let source = executable_eof_classifier_source()?;
    let mut rotated = 134;
    let mut rotation_states = vec![rotated];
    for _ in 0..12 {
        rotated = rotated / 3 + (rotated % 3) * (profile.word_modulus() / 3);
        rotation_states.push(rotated);
    }
    assert_eq!(rotated, 3_618);
    let classify = |word| {
        independent_crazy(
            125,
            independent_crazy(7_174_350, independent_crazy(rotated, word)),
        )
    };
    // Full 257-case proof; five of these cases also execute the real guest.
    for byte in u8::MIN..=u8::MAX {
        assert_eq!(classify(u32::from(byte)), 7_174_223, "byte {byte}");
    }
    assert_eq!(classify(profile.eof_word()), 377);
    assert_eq!((7_174_223_u32 % 256, 377_u32 % 256), (79, 121));

    for input in [vec![], vec![0], vec![1], vec![0x80], vec![0xff]] {
        let input_word = input
            .first()
            .map_or(profile.eof_word(), |byte| u32::from(*byte));
        let first = independent_crazy(rotated, input_word);
        let second = independent_crazy(7_174_350, first);
        let final_word = independent_crazy(125, second);
        let mut vm =
            ProfileMachine::from_source(profile, &source, input.clone())
                .map_err(|error| error.to_string())?;
        assert_eq!(vm.memory_word(135), Ok(134));
        assert_eq!(vm.memory_word(136), Ok(7_174_350));
        assert_eq!(vm.memory_word(137), Ok(125));
        assert_eq!(vm.memory_word(7_174_351), Ok(134));
        let mut trace = vec![];
        let result = vm
            .run_traced(96, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(result, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 61,
        });
        assert_eq!(trace[8].decoded, Some(b'j'));
        assert_eq!(
            trace[8].memory_reads.data.map(|r| (r.address, r.value)),
            Some((8, 126))
        );
        for round in 0..12 {
            let rotation = &trace[17 + round * 3];
            assert_eq!(rotation.decoded, Some(b'*'));
            assert_eq!(
                rotation.memory_reads.data.map(|r| (r.address, r.value)),
                Some((135, rotation_states[round]))
            );
            let forward = &trace[18 + round * 3];
            assert_eq!(forward.decoded, Some(b'j'));
            assert_eq!(
                forward.memory_reads.data.map(|r| (r.address, r.value)),
                Some((136, 7_174_350))
            );
            let back = &trace[19 + round * 3];
            assert_eq!(back.decoded, Some(b'j'));
            assert_eq!(
                back.memory_reads.data.map(|r| (r.address, r.value)),
                Some((7_174_351, 134))
            );
        }
        assert_eq!(trace[53].decoded, Some(profile.input_instruction()));
        for (position, address, operand) in
            [(56, 135, rotated), (57, 136, 7_174_350), (58, 137, 125)]
        {
            assert_eq!(trace[position].decoded, Some(b'p'));
            assert_eq!(
                trace[position]
                    .memory_reads
                    .data
                    .map(|r| (r.address, r.value)),
                Some((address, operand))
            );
        }
        assert_eq!(vm.memory_word(135), Ok(first));
        assert_eq!(vm.memory_word(136), Ok(second));
        assert_eq!(vm.memory_word(137), Ok(final_word));
        assert_eq!(vm.output(), &[
            u8::try_from(final_word % 256).expect("normalized output byte")
        ]);
        assert_eq!(vm.input_consumed(), usize::from(!input.is_empty()));
    }
    Ok(())
}

// The 728 operand of the reduced EOF pair cannot be obtained from a virgin
// loader cell by rotation alone. This source actually performs the missing
// nonlinear write after eleven rotations; the separately required first
// operand and input-dependent branch are not integrated here.
fn synthesized_second_eof_operand_source() -> Result<Vec<u8>, String> {
    use malbolge::decode_profile_instruction;

    const LENGTH: usize = 91;
    let encode = |opcode: u8, position: usize| -> Result<u8, String> {
        (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(
                    u32::from(*byte),
                    u32::try_from(position).expect("bounded position"),
                ) == Some(opcode)
            })
            .ok_or_else(|| format!("no {opcode} encoding at {position}"))
    };
    let mut source = (0..LENGTH)
        .map(|position| encode(b'o', position))
        .collect::<Result<Vec<_>, _>>()?;
    // j at C=1 sees M[1]=39 and sets D=40. The next j sees the
    // still-unexecuted M[40]=94 and sets D=95.
    source[1] = 39;
    source[2] = encode(b'j', 2)?;
    // M[95]=7,174,457, M[96]=72, M[97]=7,174,493 from the
    // graphical 44/72 tail. Between rotations, three j instructions
    // follow 96 -> 73 -> 62 -> 95 using fixed source words.
    for round in 0..10 {
        let start = 3 + round * 4;
        source[start] = encode(b'*', start)?;
        for position in start + 1..=start + 3 {
            source[position] = encode(b'j', position)?;
        }
    }
    source[43] = encode(b'*', 43)?;
    source[44] = encode(b'o', 44)?;
    source[45] = encode(b'p', 45)?;
    source[46] = encode(b'<', 46)?;
    source[47] = encode(b'v', 47)?;
    // All three reset cells must be physically loader-valid; source[40]
    // is also *executed* as the j of the tenth rotation.
    source[40] = 94;
    source[62] = 94;
    source[73] = 61;
    source[89] = 44;
    source[90] = 72;
    for (position, byte) in source.iter().enumerate() {
        let decoded = decode_profile_instruction(
            u32::from(*byte),
            u32::try_from(position).expect("bounded position"),
        );
        if !matches!(
            decoded,
            Some(b'j' | b'i' | b'*' | b'p' | b'o' | b'<' | b'/' | b'v')
        ) {
            return Err(format!("invalid source at {position}: {decoded:?}"));
        }
    }
    Ok(source)
}

#[test]
#[expect(
    clippy::integer_division_remainder_used,
    reason = "independent fifteen-trit rotation witness"
)]
fn physical_guest_synthesizes_728_with_rotations_and_crazy()
-> Result<(), String> {
    let profile = current_profile();
    let source = synthesized_second_eof_operand_source()?;
    let mut rotated = 7_174_457;
    let mut states = vec![rotated];
    for _ in 0..11 {
        rotated = rotated / 3 + (rotated % 3) * (profile.word_modulus() / 3);
        states.push(rotated);
    }
    assert_eq!(rotated, 7_174_777);
    assert_eq!(independent_crazy(7_174_493, rotated), 728);
    for input in [vec![], vec![0], vec![0xff]] {
        let mut vm = ProfileMachine::from_source(profile, &source, input)
            .map_err(|error| error.to_string())?;
        assert_eq!(vm.memory_word(95), Ok(7_174_457));
        assert_eq!(vm.memory_word(96), Ok(72));
        assert_eq!(vm.memory_word(97), Ok(7_174_493));
        let mut trace = vec![];
        let outcome = vm
            .run_traced(64, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 48,
        });
        for (position, address, value) in [(1, 1, 39), (2, 40, 94)] {
            let step = &trace[position];
            assert_eq!(step.decoded, Some(b'j'));
            assert_eq!(
                step.memory_reads.data.map(|r| (r.address, r.value)),
                Some((address, value)),
            );
        }
        for round in 0..11 {
            let start = 3 + round * 4;
            let rotation = &trace[start];
            assert_eq!(rotation.decoded, Some(b'*'));
            assert_eq!(
                rotation.memory_reads.data.map(|r| (r.address, r.value)),
                Some((95, states[round])),
            );
        }
        for round in 0..10 {
            let start = 3 + round * 4;
            for (offset, address, value) in
                [(1, 96, 72), (2, 73, 61), (3, 62, 94)]
            {
                let reset = &trace[start + offset];
                assert_eq!(reset.decoded, Some(b'j'));
                assert_eq!(
                    reset.memory_reads.data.map(|r| (r.address, r.value)),
                    Some((address, value)),
                );
            }
        }
        let write = &trace[45];
        assert_eq!(write.decoded, Some(b'p'));
        assert_eq!(
            write.memory_reads.data.map(|r| (r.address, r.value)),
            Some((97, 7_174_493)),
        );
        assert_eq!(vm.memory_word(95), Ok(rotated));
        assert_eq!(vm.memory_word(97), Ok(728));
        assert_eq!(vm.output(), &[216]);
        assert_eq!(vm.input_consumed(), 0);
    }
    Ok(())
}

// A single physical N15 guest prepares both operands of the independently
// admitted reduced EOF discriminator. The two writes occur before any input;
// this is not yet a 257-input classifier or a reached conditional jump.
fn joined_eof_operand_source() -> Result<Vec<u8>, String> {
    use malbolge::decode_profile_instruction;

    const LENGTH: usize = 91;
    let encode = |opcode: u8, position: usize| -> Result<u8, String> {
        (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(
                    u32::from(*byte),
                    u32::try_from(position).expect("bounded code position"),
                ) == Some(opcode)
            })
            .ok_or_else(|| format!("no encoding for {opcode} at {position}"))
    };
    let mut code = (0..LENGTH)
        .map(|position| encode(b'o', position))
        .collect::<Result<Vec<_>, _>>()?;
    code[1] = 39; // D=1 -> D=40.
    code[2] = encode(b'j', 2)?; // M[40]=94 -> D=95.
    for round in 0..10 {
        let start = 3 + round * 4;
        code[start] = encode(b'*', start)?;
        for position in start + 1..=start + 3 {
            code[position] = encode(b'j', position)?;
        }
    }
    code[43] = encode(b'*', 43)?;
    code[45] = encode(b'p', 45)?; // M[97] becomes 728.
    for position in [48, 49, 50, 52, 53, 54, 64, 68, 69, 70, 71, 72, 73] {
        code[position] = encode(b'j', position)?;
    }
    code[51] = encode(b'*', 51)?; // M[95] rotated once more.
    code[55] = encode(b'p', 55)?; // M[95]: 7,174,561 -> 108.
    code[62] = encode(b'p', 62)?; // M[102]=72 -> 7,174,408.
    code[63] = encode(b'p', 63)?; // M[103]=7,174,493 -> 125.
    code[79] = encode(b'p', 79)?; // M[95]=108 -> 7,174,332.
    code[80] = encode(b'<', 80)?;
    code[81] = encode(b'v', 81)?;
    // Reset chain: untouched M[73]=61 -> M[62]=94 -> D=95;
    // after C62 encrypts M[62]=57, M[58]'s prior encryption to 89
    // gives the alternate D=90 -> D=95 continuation at C68..C78.
    code[40] = 94;
    code[62] = 94;
    code[73] = 61;
    code[89] = 44;
    code[90] = 72;
    for (position, byte) in code.iter().enumerate() {
        let decoded = decode_profile_instruction(
            u32::from(*byte),
            u32::try_from(position).expect("bounded position"),
        );
        if !matches!(
            decoded,
            Some(b'j' | b'i' | b'*' | b'p' | b'o' | b'<' | b'/' | b'v')
        ) {
            return Err(format!("invalid source at {position}: {decoded:?}"));
        }
    }
    Ok(code)
}

#[test]
fn physical_guest_prepares_both_eof_operands_in_one_run() -> Result<(), String>
{
    let profile = current_profile();
    let source = joined_eof_operand_source()?;
    let proved =
        admit_c23_eof_control_word_plan(profile, [7_174_332, 728], [728, 485]);
    assert!(proved.is_ok(), "257-case scalar plan: {proved:?}");
    for input in [vec![], vec![0], vec![0x80], vec![0xff]] {
        let mut vm = ProfileMachine::from_source(profile, &source, input)
            .map_err(|error| error.to_string())?;
        for (address, expected) in [
            (95, 7_174_457),
            (96, 72),
            (97, 7_174_493),
            (98, 36),
            (99, 7_174_493),
            (100, 72),
            (102, 72),
            (103, 7_174_493),
            (104, 36),
        ] {
            assert_eq!(vm.memory_word(address), Ok(expected), "M[{address}]");
        }
        let mut trace = vec![];
        let outcome = vm
            .run_traced(100, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 82,
        });
        for (position, opcode, address, operand) in [
            (45, b'p', 97, 7_174_493),
            (51, b'*', 95, 7_174_777),
            (55, b'p', 95, 7_174_561),
            (62, b'p', 102, 72),
            (63, b'p', 103, 7_174_493),
            (79, b'p', 95, 108),
        ] {
            let step = &trace[position];
            assert_eq!(step.decoded, Some(opcode), "C={position}");
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, operand)),
                "C={position}",
            );
        }
        for (position, address, operand) in [
            (48, 100, 72),
            (49, 73, 61),
            (50, 62, 94),
            (64, 104, 36),
            (68, 40, 57),
            (69, 58, 89),
            (70, 90, 72),
            (71, 73, 61),
            (72, 62, 57),
            (73, 58, 89),
        ] {
            let step = &trace[position];
            assert_eq!(step.decoded, Some(b'j'), "C={position}");
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, operand)),
                "C={position}",
            );
        }
        assert_eq!(vm.memory_word(95), Ok(7_174_332));
        assert_eq!(vm.memory_word(97), Ok(728));
        assert_eq!(vm.memory_word(96), Ok(72));
        assert_eq!(
            vm.output(),
            &[u8::try_from(7_174_332 % 256).expect("byte")]
        );
        assert_eq!(vm.input_consumed(), 0);
    }
    Ok(())
}
