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
//   - Exact XLAT2 input-code recurrence constraints for a C23 EOF loop.
// - Must-Not:
//   - Claim a repeated-input guest loop or C source lowering from opcode
//     phases.
// - Allows:
//   - Inputs: 94 decoder phases, graphical code bytes and finite binary input.
//   - Outputs: exhaustive first/second/third input decode and a real N15 read.
//   - Side effects: isolated finite normative VM execution only.
// - Split-When:
//   - An actual source-linked repeating-input machine proves the full cycle.
// - Merge-When:
//   - The complete guest-loop linker proves every reached code mutation.
// - Summary:
//   - Rules out a naive one-encryption physical getchar-site revisit.

//! Phase-exhaustive no-external-write opcode constraint for repeating C reads.
//! A repeatable EOF loop needs a real `/` at the same source input site.
//! The next revisit after one XLAT2 encryption is never `/`, irrespective of
//! N15 pointer phase. This does NOT forbid intervening code revisits,
//! purposeful data writes or distinct input-site copies.

use malbolge::{
    ProfileMachine, ProfileStepTrace, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, encrypt_profile_cell,
    historical_profile,
};

const DECODE_PHASES: u32 = 94;
const INPUT_ADDRESS: u32 = 47;
const SOURCE_LENGTH: usize = 49;

fn input_source_cell(phase: u32) -> Result<u8, String> {
    let mut encoded = (33u8..=126).filter(|byte| {
        decode_profile_instruction(u32::from(*byte), phase) == Some(b'/')
    });
    let selected = encoded
        .next()
        .ok_or_else(|| format!("no input encoding at phase {phase}"))?;
    if encoded.next().is_some() {
        return Err(format!("input encoding not unique at phase {phase}"));
    }
    Ok(selected)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "exhaustive decoder and encryption proof assertions"
)]
fn direct_reexecution_of_an_encrypted_input_cell_never_reads_again()
-> Result<(), String> {
    let mut third_read_phases = Vec::new();
    for phase in 0..DECODE_PHASES {
        let original = input_source_cell(phase)?;
        let encrypted = encrypt_profile_cell(u32::from(original))
            .ok_or_else(|| format!("missing XLAT2 at phase {phase}"))?;
        assert_ne!(
            decode_profile_instruction(encrypted, phase),
            Some(b'/'),
            "the first encrypted revisit must not read at phase {phase}",
        );
        let encrypted_twice = encrypt_profile_cell(encrypted)
            .ok_or_else(|| format!("missing second XLAT2 at phase {phase}"))?;
        if decode_profile_instruction(encrypted_twice, phase) == Some(b'/') {
            third_read_phases.push(phase);
            assert!(
                !matches!(
                    decode_profile_instruction(encrypted, phase),
                    Some(b'i' | b'j' | b'p' | b'*' | b'<' | b'v')
                ),
                "intermediate phase {phase} must be a VM no-op",
            );
        }
    }
    // Two exact 94-position phases permit / -> inert -> / across three
    // visits. These are decoder prerequisites, not physical guest loops.
    assert_eq!(third_read_phases, [43, 47]);
    assert_eq!(input_source_cell(43)?, 74);
    assert_eq!(input_source_cell(47)?, 70);
    Ok(())
}

fn single_input_guest_source() -> Result<Vec<u8>, String> {
    let mut source = (0..SOURCE_LENGTH)
        .map(|position| {
            let phase =
                u32::try_from(position).map_err(|error| error.to_string())?;
            let decoded = match position {
                47 => b'/',
                48 => b'v',
                _ => b'o',
            };
            (33u8..=126)
                .find(|byte| {
                    decode_profile_instruction(u32::from(*byte), phase)
                        == Some(decoded)
                })
                .ok_or_else(|| format!("unencodable opcode at C{position}"))
        })
        .collect::<Result<Vec<_>, _>>()?;
    // The exact source nibble used by the third-visit opportunity is a real
    // graphical, loadable input instruction, not an invented memory word.
    let read = source
        .get_mut(47)
        .ok_or_else(|| "missing C47 input site".to_owned())?;
    *read = input_source_cell(INPUT_ADDRESS)?;
    Ok(source)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    reason = "three physical streams on two profile VMs need full trace checks"
)]
fn phase_47_executes_one_real_guest_input_and_self_encrypts()
-> Result<(), String> {
    let source = single_input_guest_source()?;
    let encoded = u32::from(input_source_cell(INPUT_ADDRESS)?);
    let encrypted = encrypt_profile_cell(encoded)
        .ok_or_else(|| "missing input code encryption".to_owned())?;
    let third_visit_byte = encrypt_profile_cell(encrypted)
        .ok_or_else(|| "missing second encryption".to_owned())?;
    assert_eq!(
        decode_profile_instruction(encoded, INPUT_ADDRESS),
        Some(b'/')
    );
    assert_eq!(
        decode_profile_instruction(encrypted, INPUT_ADDRESS),
        Some(b'P')
    );
    assert_eq!(
        decode_profile_instruction(third_visit_byte, INPUT_ADDRESS),
        Some(b'/')
    );
    for profile in [current_profile(), historical_profile()] {
        for input in [Vec::new(), vec![0], vec![0xff]] {
            let expected_read = input
                .first()
                .copied()
                .map_or(TraceInput::EndOfInput, TraceInput::Byte);
            let mut machine =
                ProfileMachine::from_source(profile, &source, input.clone())
                    .map_err(|error| error.to_string())?;
            let mut trace = Vec::<ProfileStepTrace>::new();
            let outcome = machine
                .run_traced(SOURCE_LENGTH, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?;
            assert_eq!(outcome, RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: SOURCE_LENGTH,
            });
            let read =
                trace.get(47).ok_or_else(|| "unreached C47".to_owned())?;
            assert_eq!(read.before.registers.code_pointer, INPUT_ADDRESS);
            assert_eq!(read.decoded, Some(b'/'));
            assert_eq!(read.input, Some(expected_read));
            assert_eq!(read.fetched_cell, Some(encoded));
            assert_eq!(machine.memory_word(INPUT_ADDRESS), Ok(encrypted));
            assert_eq!(machine.input_consumed(), input.len().min(1));
        }
    }
    Ok(())
}
