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
//   - Exhaustive first-octet evidence for physical second-EOF guest control.
// - Must-Not:
//   - Claim arbitrary C23 source, mutable checksum or generalized looping.
// - Allows:
//   - Inputs: one frozen N15 guest source and 256 real first-byte streams.
//   - Outputs: normative VM traces, exact output and halt provenance.
//   - Side effects: isolated in-memory interpreter allocations only.
// - Split-When:
//   - General source-verified C23 conditional guest replaces this template.
// - Merge-When:
//   - Complete C23 checksum guest parity subsumes this first-byte result.
// - Summary:
//   - Every first byte reaches a second EOF and keeps its exact first output.
//

//! Independent full-octet first-read verification of a real EOF-branch guest.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
};

#[test]
#[expect(
    clippy::expect_used,
    reason = "frozen physical guest and exhaustive VM outcomes must be valid"
)]
fn every_first_byte_survives_true_second_eof_branch() {
    let profile = current_profile();
    let source =
        layout::build_second_input_eof_classified_first_echo_source(profile)
            .expect("frozen physical EOF branch source");
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .expect("valid source-loaded profile machine");
    assert_eq!(source.len(), 132);
    assert_eq!(source.get(130..), Some(b"-}".as_slice()));

    for first in u8::MIN..=u8::MAX {
        let mut machine = loaded
            .fork_with_input(vec![first])
            .expect("fresh checkpoint permits any first byte");
        let mut inputs = Vec::new();
        let mut outputs = Vec::new();
        let outcome = machine.run_traced(119, &mut |step| {
            if let Some(input) = step.input {
                inputs.push((step.before.registers.code_pointer, input));
            }
            if let Some(output) = step.output {
                outputs.push((step.before.registers.code_pointer, output));
            }
        });
        assert_eq!(
            outcome,
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 119,
            }),
            "first byte {first}",
        );
        assert_eq!(
            inputs,
            [(53, TraceInput::Byte(first)), (63, TraceInput::EndOfInput),],
            "first byte {first}",
        );
        assert_eq!(outputs, [(54, first), (128, 30)], "first byte {first}",);
        assert_eq!(machine.output(), [first, 30], "first byte {first}");
        assert_eq!(machine.input_consumed(), 1, "first byte {first}");
    }
    assert_eq!(loaded.input_consumed(), 0);
    assert!(loaded.output().is_empty());
}
