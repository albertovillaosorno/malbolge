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
//   - A source-independent forty-five-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim forty-five-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: forty-five exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest forty-five-byte compiler owns this physical proof.
// - Summary:
//   - Forty-five relocated guest arithmetic instructions emit distinct binary bytes.
// - Description:
//   - Each byte is computed by the real VM, not host output substitution.
// - Usage:
//   - cargo test --locked --test guest_forty_five_distinct_literal_witness
// - Defaults:
//   - Does not admit any forty-five-byte source C program to the compiler.

//! Forty-five disjoint guest arithmetic writes and distinct bytes in the real VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 45] = [
    81, 62, 53, 56, 84, 31, 78, 135, 209, 165, 153, 9, 8, 199, 198, 194, 145, 225, 167, 172, 152,
    219, 155, 160, 183, 191, 124, 181, 44, 203, 18, 180, 248, 202, 14, 149, 45, 171, 51, 61, 57, 5,
    83, 35, 27,
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
fn forty_five_distinct_binary_bytes_are_computed_by_guest_arithmetic() -> Result<(), String> {
    // Eleven reached no-ops place the relocation at source position 11.
    // An internal no-op after twenty bytes and a trailing no-op adjust
    // data addresses and source recurrence without any host-side output.
    let mut operations = vec![LinearOpcode::NoOperation; 11];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..45usize {
        if index == 20 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if [7, 11, 12, 27, 31, 38].contains(&index) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::NoOperation);
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 105);
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
            124, 126, 128, 130, 132, 134, 136, 138, 140, 142, 144, 146, 148, 150, 152, 154, 156,
            158, 160, 162, 165, 167, 169, 171, 173, 175, 177, 179, 181, 183, 185, 187, 189, 191,
            193, 195, 197, 199, 201, 203, 205, 207, 209, 211, 213
        ]
    );
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 45);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address).is_ok_and(|position| position >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 45);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(current_profile(), layout.source(), input)
            .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(105).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps, .. } if steps == 105));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
