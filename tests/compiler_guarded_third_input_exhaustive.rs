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
//   - Exhaustive second-input byte-class admission for a guarded third read.
// - Must-Not:
//   - Confuse successful bytes 31 and 255 with the signed EOF sentinel.
// - Allows:
//   - Inputs: all 256 second bytes, three third-byte classes, EOF controls.
//   - Outputs: exact normative VM input sites, stdout and bounded halts.
//   - Side effects: bounded, isolated in-memory VM processes only.
// - Split-When:
//   - Dynamic C23 CFG backend subsumes conditional-read validation.
// - Merge-When:
//   - General signed-input admission covers all 256 byte classes.
// - Summary:
//   - Reject false EOF-class aliases for every successful second input.

//! Exhaustive real-guest branch coverage for a conditional third signed read.
//! This proves real input effects, not arithmetic on or output of the third
//! word; the original mutable C23 checksum remains physically unlinked.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use malbolge::{
    ProfileDescriptor, ProfileMachine, ProfileRegisters, RunOutcome,
    Termination, TraceInput, current_profile,
};

/// Check one complete normative VM path against exact physical read sites.
#[expect(
    clippy::too_many_arguments,
    reason = "distinct independent input, I/O and halt oracles"
)]
fn verify_path(
    profile: &'static ProfileDescriptor,
    initial_memory: &[u32],
    input: Vec<u8>,
    expected_reads: &[(u32, TraceInput)],
    expected_output: &[u8],
    consumed: usize,
    steps: usize,
    context: &str,
) -> Result<(), String> {
    let mut vm = ProfileMachine::from_state(
        profile,
        initial_memory.to_vec(),
        input,
        ProfileRegisters::default(),
    )
    .map_err(|error| format!("{context}: {error}"))?;
    let mut reads = Vec::new();
    let outcome = vm
        .run_traced(steps, &mut |step| {
            if let Some(value) = step.input {
                reads.push((step.before.registers.code_pointer, value));
            }
        })
        .map_err(|error| format!("{context}: {error}"))?;
    assert_eq!(
        outcome,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps,
        },
        "{context}: incomplete or wrong-branch VM halt",
    );
    assert_eq!(
        vm.output(),
        expected_output,
        "{context}: wrong guest stdout"
    );
    assert_eq!(
        vm.input_consumed(),
        consumed,
        "{context}: consumed too many or too few input bytes",
    );
    assert_eq!(
        reads, expected_reads,
        "{context}: missing or unguarded physical input event",
    );
    Ok(())
}

#[expect(
    clippy::too_many_lines,
    reason = "each byte class checks three real third reads and true EOF"
)]
fn verify_second_input_range(low: u8, high: u8) -> Result<(), String> {
    let profile = current_profile();
    let source = layout::build_second_input_guarded_third_read_source(profile)
        .map_err(|error| format!("guarded third input builder: {error:?}"))?;
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| format!("VM refused graphical source: {error}"))?;
    let memory = loaded.memory();
    // The second read is genuinely successful for every binary value,
    // including 0x1f and 0xff; its true EOF branch must never be selected.
    for second in low..=high {
        for third in [0u8, 31, 255] {
            verify_path(
                profile,
                memory,
                vec![165, second, third, 77],
                &[
                    (53, TraceInput::Byte(165)),
                    (63, TraceInput::Byte(second)),
                    (101, TraceInput::Byte(third)),
                ],
                &[165, 154],
                3,
                175,
                &format!("second={second}, third={third}"),
            )?;
        }
        // The same physical success arm also attempts the third input
        // when it is genuinely missing; EOF must be reported at C101.
        verify_path(
            profile,
            memory,
            vec![165, second],
            &[
                (53, TraceInput::Byte(165)),
                (63, TraceInput::Byte(second)),
                (101, TraceInput::EndOfInput),
            ],
            &[165, 154],
            2,
            175,
            &format!("second={second}, true third EOF"),
        )?;
    }
    Ok(())
}

#[test]
fn second_input_bytes_00_through_3f() -> Result<(), String> {
    verify_second_input_range(0x00, 0x3f)
}

#[test]
fn second_input_bytes_40_through_7f() -> Result<(), String> {
    verify_second_input_range(0x40, 0x7f)
}

#[test]
fn second_input_bytes_80_through_bf() -> Result<(), String> {
    verify_second_input_range(0x80, 0xbf)
}

#[test]
fn second_input_bytes_c0_through_ff() -> Result<(), String> {
    verify_second_input_range(0xc0, 0xff)
}

#[test]
fn true_second_eof_never_reaches_conditional_third_read() -> Result<(), String>
{
    let profile = current_profile();
    let source = layout::build_second_input_guarded_third_read_source(profile)
        .map_err(|error| format!("guarded third input builder: {error:?}"))?;
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| format!("VM refused graphical source: {error}"))?;
    let memory = loaded.memory();
    // The actual *second* EOF must stop before the guarded third input,
    // independently of the first input word's boundary class.
    for first in [None, Some(0), Some(31), Some(255)] {
        let expected_first =
            first.map_or(TraceInput::EndOfInput, TraceInput::Byte);
        verify_path(
            profile,
            memory,
            first.into_iter().collect(),
            &[(53, expected_first), (63, TraceInput::EndOfInput)],
            &[first.unwrap_or(106), 30],
            usize::from(first.is_some()),
            119,
            &format!("true second EOF after {first:?}"),
        )?;
    }
    Ok(())
}
