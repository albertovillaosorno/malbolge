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
//   - Real-VM rejection witness for a deceptively halted third-byte echo.
// - Must-Not:
//   - Treat a few successful bytes as proof of a general C23 EOF branch.
// - Allows:
//   - Inputs: unchanged source-valid 132-cell N15 physical branch and patches.
//   - Outputs: exact independent EOF/byte IO, code positions and halts.
//   - Side effects: isolated bounded in-memory VM runs only.
// - Split-When:
//   - A genuine general EOF-controlled third-byte output is linked.
// - Merge-When:
//   - The dynamic C23 source checksum reaches the normative guest VM.
// - Summary:
//   - An apparently repaired EOF arm aliases successful byte classes.

//! Reject a tempting false-positive repair of the physical third-byte echo.
//! Two encrypted input/output revisits and a compensating first-pass jump
//! make both observed arms halt, but non-EOF bytes still select the EOF arm.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, encrypt_profile_cell,
};

fn graphical_revisit(address: usize, first: u8, second: u8) -> Option<u8> {
    (33..=126).find(|candidate| {
        let code_pointer = u32::try_from(address).ok();
        code_pointer.is_some_and(|pointer| {
            decode_profile_instruction(u32::from(*candidate), pointer)
                == Some(first)
                && encrypt_profile_cell(u32::from(*candidate))
                    .and_then(|cell| decode_profile_instruction(cell, pointer))
                    == Some(second)
        })
    })
}

fn graphical_opcode(address: usize, opcode: u8) -> Option<u8> {
    let pointer = u32::try_from(address).ok()?;
    (33..=126).find(|candidate| {
        decode_profile_instruction(u32::from(*candidate), pointer)
            == Some(opcode)
    })
}

// This is the source-level intent the proposed physical linker would have
// claimed: EOF on the second read skips a third read; every successful
// second byte, regardless of its numeric class, performs it.
fn expected_c23_control(input: &[u8]) -> Vec<u8> {
    let first = input.first().copied().unwrap_or(106);
    if input.get(1).is_none() {
        vec![first, 30]
    } else {
        vec![first, 4, input.get(2).copied().unwrap_or(106)]
    }
}

#[test]
fn third_echo_with_extra_jump_still_misclassifies_non_eof_bytes()
-> Result<(), String> {
    let profile = current_profile();
    let original =
        layout::build_second_input_eof_classified_first_echo_source(profile)
            .map_err(|error| format!("physical branch: {error:?}"))?;
    let mut source = original.clone();
    source[62] = graphical_revisit(62, b'j', b'/')
        .ok_or("missing C62 j-then-input encoding")?;
    source[66] = graphical_revisit(66, b'j', b'<')
        .ok_or("missing C66 j-then-output encoding")?;
    source[93] =
        graphical_opcode(93, b'j').ok_or("missing C93 first-pass jump")?;
    assert_eq!(source[62], b'H');
    assert_eq!(source[66], b'D');
    assert_eq!(source.get(130..), original.get(130..));
    assert_eq!(
        source
            .iter()
            .zip(&original)
            .enumerate()
            .filter(|(_, (actual, before))| actual != before)
            .map(|(position, _)| position)
            .collect::<Vec<_>>(),
        [62, 66, 93],
    );

    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    // All paths are genuine VM executions. The first two EOF cases and the
    // small-byte case appear to establish a conditional third read; the
    // non-EOF 31/255 counterexamples disprove that tempting inference.
    let cases: &[(&[u8], &[u8], usize, usize, usize)] = &[
        (b"", &[106, 30], 119, 0, 2),
        (b"\x03", &[3, 30], 119, 1, 2),
        (b"\x03\x00\x80", &[3, 4, 128], 172, 3, 3),
        (b"\x03\x04\x05\x99", &[3, 4, 5], 172, 3, 3),
        (b"\x03\xc0\xff", &[3, 4, 255], 172, 3, 3),
        (b"\x03\x07", &[3, 4, 106], 172, 2, 3),
        (b"\x03\x1f\x80", &[3, 30], 119, 2, 2),
        (b"\x03\xff\x80", &[3, 30], 119, 2, 2),
    ];
    for (input, output, steps, consumed, reads) in cases {
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input.to_vec(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(200, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: *steps,
            },
            "input={input:?}",
        );
        assert_eq!(vm.output(), *output, "input={input:?}");
        let oracle = expected_c23_control(input);
        if input
            .get(1)
            .is_some_and(|second| [31, 255].contains(second))
        {
            assert_ne!(vm.output(), oracle, "false EOF on {input:?}");
        } else {
            assert_eq!(vm.output(), oracle, "actual matching arm on {input:?}");
        }
        assert_eq!(vm.input_consumed(), *consumed, "input={input:?}");
        let input_steps = trace
            .iter()
            .filter(|step| step.input.is_some())
            .collect::<Vec<_>>();
        assert_eq!(input_steps.len(), *reads, "input={input:?}");
        assert_eq!(
            input_steps
                .iter()
                .map(|step| step.before.registers.code_pointer)
                .collect::<Vec<_>>(),
            if *reads == 2 {
                vec![53, 63]
            } else {
                vec![53, 63, 62]
            },
        );
        if *reads == 3 {
            let third = input
                .get(2)
                .copied()
                .map_or(TraceInput::EndOfInput, TraceInput::Byte);
            assert_eq!(input_steps[2].input, Some(third));
            assert!(trace.iter().any(|step| {
                step.before.registers.code_pointer == 66
                    && step.output == Some(output[2])
            }));
        }
    }

    // The actual N15 third-read candidate selects the short arm for two
    // *successful* second bytes; it must never be published as C23 EOF.
    Ok(())
}
