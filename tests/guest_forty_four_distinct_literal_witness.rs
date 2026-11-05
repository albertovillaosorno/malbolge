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
//   - A source-independent forty-four-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim forty-four-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: forty-four exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest forty-four-byte compiler owns this physical proof.
// - Summary:
//   - Forty-four relocated guest arithmetic instructions emit distinct bytes.
// - Description:
//   - Each byte is computed by the real VM, not host output substitution.
// - Usage:
//   - cargo test --locked --test guest_forty_four_distinct_literal_witness
// - Defaults:
//   - Does not admit any forty-four-byte C program to the compiler.

//! Forty-four disjoint guest arithmetic writes and distinct real VM bytes.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 44] = [
    90, 38, 71, 11, 62, 9, 45, 19, 52, 165, 6, 175, 243, 168, 47, 17, 65, 15,
    48, 25, 55, 8, 77, 50, 78, 31, 87, 41, 68, 10, 212, 153, 221, 160, 204,
    170, 211, 7, 213, 145, 222, 161, 220, 171,
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
fn forty_four_distinct_binary_bytes_are_computed_by_guest_arithmetic()
-> Result<(), String> {
    // Eleven reached no-ops relocate guest data beyond the source.
    // No-ops before outputs 3 and 22 shift later data words.
    // Rotations at 9, 13, 14, 29, 37 and 39 avoid byte collisions.
    let mut operations = vec![LinearOpcode::NoOperation; 11];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..44usize {
        if index == 3 || index == 22 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if [9, 13, 14, 29, 37, 39].contains(&index) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 103);
    let layout = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("encode: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    let expected_writes: Vec<u32> = (0..44)
        .map(|i| 124 + 2 * i + u32::from(i >= 3) + u32::from(i >= 22))
        .collect();
    assert_eq!(writes, expected_writes);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 44);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address)
            .is_ok_and(|position| position >= layout.source().len())
    }));

    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 44);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            input,
        )
        .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(103).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps: 103, .. }));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
