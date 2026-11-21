// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier: Apache-2.0
//
// Boundary-Contract:
// - Owns: bounded immediate third-input state/return constraints on N15.
// - Must-Not: infer general loop impossibility from one encrypted code window.
// - Allows: exact graphical opcode census and normative VM mutation replay.
// - Summary: local post-read stores need a distinct control/code layout.

//! Third-input data cannot be stored by a direct source-loaded `p` in the
//! C102..C112 return window of the existing guarded guest program.
//! This is a bounded no-external-code-write result, not general impossibility.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileRegisters, RunOutcome,
    Termination, current_profile, decode_profile_instruction,
    encrypt_profile_cell,
};

#[test]
fn encrypted_return_window_lacks_a_direct_crazy_store_for_third_input() {
    let mut second_outputs = Vec::new();
    let mut second_stores = Vec::new();
    for code_pointer in 102u32..=112 {
        for byte in 33u8..=126 {
            let first =
                decode_profile_instruction(u32::from(byte), code_pointer);
            let Some(initial) =
                first.filter(|decoded| b"oijp*/<v".contains(decoded))
            else {
                continue;
            };
            let second =
                encrypt_profile_cell(u32::from(byte)).and_then(|word| {
                    decode_profile_instruction(word, code_pointer)
                });
            if second == Some(b'p') {
                second_stores.push((code_pointer, byte, initial));
            }
            if second == Some(b'<') {
                second_outputs.push((code_pointer, byte, initial));
            }
        }
    }
    assert!(second_stores.is_empty());
    // C108 could output the third accumulator only if its *first* pass
    // halted at `v`, making it incompatible with the existing classifier.
    assert_eq!(second_outputs, [(108, 67, b'v')]);
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "isolated source-loaded counterexample with exact VM errors"
)]
fn c102_return_cannot_reenter_after_third_read() -> Result<(), String> {
    let profile = current_profile();
    let mut source =
        layout::build_two_input_class_state_with_guarded_third_read_source(
            profile,
        )
        .map_err(|error| format!("{error:?}"))?;
    let original = source[102];
    assert_eq!(
        decode_profile_instruction(u32::from(original), 102),
        Some(b'o')
    );
    // A first-pass `p` encrypts into an actual second-pass `i` at C102.
    // That second pass follows the genuine third input at C101; it is
    // tempting as a guest loop return, but its target is not graphical.
    source[102] = 54;
    assert_eq!(decode_profile_instruction(54, 102), Some(b'p'));
    assert_eq!(
        encrypt_profile_cell(54)
            .and_then(|word| decode_profile_instruction(word, 102)),
        Some(b'i')
    );
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    for input in [Vec::new(), vec![7], vec![7, 8], vec![7, 8, 0], vec![
        7, 8, 255,
    ]] {
        let second_eof = input.len() < 2;
        let mut machine = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let result = machine.run_traced(176, &mut |step| trace.push(*step));
        let read_sites = trace
            .iter()
            .filter(|step| step.decoded == Some(b'/'))
            .map(|step| step.before.registers.code_pointer)
            .collect::<Vec<_>>();
        assert_eq!(
            read_sites,
            if second_eof {
                vec![53, 63]
            } else {
                vec![53, 63, 101]
            },
        );
        assert_eq!(
            machine.input_consumed(),
            input.len().min(if second_eof {
                2
            } else {
                3
            })
        );
        if second_eof {
            assert_eq!(
                result,
                Ok(RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 119,
                })
            );
        } else {
            assert_eq!(
                result,
                Err(ProfileMachineError::InvalidEncryptionTarget {
                    pointer: 7_174_350,
                    value: 7_174_350,
                })
            );
            let attempted = trace.iter().find(|step| {
                step.before.registers.code_pointer == 102
                    && step.decoded == Some(b'i')
            });
            assert!(attempted.is_some());
        }
    }
    Ok(())
}
