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
//   - Actual N15 guest placement of one proposed EOF discriminator operand.
// - Must-Not:
//   - Claim a second operand, executable EOF branch, or stateful C lowering.
// - Allows:
//   - Inputs: one static loader seed and selected binary/EOF input streams.
//   - Outputs: actual guest memory reads, writes, and VM outcome.
//   - Side effects: bounded independent normative VM execution.
// - Split-When:
//   - A linked two-operand guest EOF branch replaces this placement witness.
// - Merge-When:
//   - The compiler constructs both data operands and branches on EOF.
// - Summary:
//   - Shows the first operand can be read by a real input-dependent guest p.

//! A placed first crazy operand on a real N15 input-driven guest.

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
