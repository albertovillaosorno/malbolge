// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - A source-independent thirty-two-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim thirty-two-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: thirty-two exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest thirty-two-byte compiler owns this physical proof.
// - Summary:
//   - Thirty-two relocated guest arithmetic instructions emit distinct binary bytes.
// - Description:
//   - Each byte is computed by the real VM, not host output substitution.
// - Usage:
//   - cargo test --locked --test guest_thirty_two_distinct_literal_witness
// - Defaults:
//   - Does not admit any thirty-two-byte source C program to the compiler.

//! Thirty-two disjoint guest arithmetic writes and distinct bytes in the real VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 32] = [
    65, 23, 50, 24, 80, 35, 92, 39, 75, 52, 79, 9, 212, 172, 225, 158, 226, 171, 11, 214, 156, 227,
    160, 210, 173, 147, 224, 159, 228, 170, 213, 174,
];

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions bind guest arithmetic to the normative real VM"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "one physical witness checks writes, exact steps and binary output"
)]
fn thirty_two_distinct_binary_bytes_are_computed_by_guest_arithmetic() -> Result<(), String> {
    // Thirty reached no-ops shift the relocating j to source position 30.
    // One internal no-op after four bytes shifts later data addresses;
    // rotations at byte positions 11, 18, and 25 keep all outputs distinct.
    let mut operations = vec![LinearOpcode::NoOperation; 30];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..32usize {
        if index == 4 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if index == 11 || index == 18 || index == 25 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 97);
    let layout = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("encode: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    assert_eq!(
        writes,
        [
            105, 107, 109, 111, 114, 116, 118, 120, 122, 124, 126, 128, 130, 132, 134, 136, 138,
            140, 142, 144, 146, 148, 150, 152, 154, 156, 158, 160, 162, 164, 166, 168
        ]
    );
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 32);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address).is_ok_and(|position| position >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 32);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(current_profile(), layout.source(), input)
            .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(97).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps, .. } if steps == 97));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
