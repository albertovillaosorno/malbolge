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
