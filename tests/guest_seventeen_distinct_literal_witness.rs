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
//   - A source-independent seventeen-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim seventeen-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: seventeen exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest seventeen-byte compiler owns this physical proof.
// - Summary:
//   - Seventeen relocated guest arithmetic instructions emit distinct binary bytes.
// - Description:
//   - Each byte is computed by the real VM, not host output substitution.
// - Usage:
//   - cargo test --locked --test guest_seventeen_distinct_literal_witness
// - Defaults:
//   - Does not admit any seventeen-byte source C program to the compiler.

//! Seventeen disjoint guest arithmetic writes and distinct bytes in the real VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 17] = [
    89, 63, 44, 72, 80, 27, 24, 50, 21, 77, 75, 59, 66, 15, 68, 48, 23,
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
fn seventeen_distinct_binary_bytes_are_computed_by_guest_arithmetic() -> Result<(), String> {
    // A single no-op followed by j relocates D beyond the source. Rotate
    // at positions 6, 8, and 13 to avoid repeated output bytes.
    let mut operations = vec![LinearOpcode::NoOperation, LinearOpcode::RelocateDataPointer];
    for index in 0..17usize {
        operations.extend([
            if index == 6 || index == 8 || index == 13 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 37);
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
            40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 62, 64, 66, 68, 70, 72
        ]
    );
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 17);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address).is_ok_and(|position| position >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 17);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(current_profile(), layout.source(), input)
            .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(37).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps, .. } if steps == 37));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
