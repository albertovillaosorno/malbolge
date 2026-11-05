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
//   - A source-independent thirty-nine-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim thirty-nine-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: thirty-nine exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest thirty-nine-byte compiler owns this physical proof.
// - Summary:
//   - Thirty-nine relocated guest arithmetic instructions emit distinct binary
//     bytes.
// - Description:
//   - Each byte is computed by the real VM, not host output substitution.
// - Usage:
//   - cargo test --locked --test guest_thirty_nine_distinct_literal_witness
// - Defaults:
//   - Does not admit any thirty-nine-byte source C program to the compiler.

//! Thirty-nine disjoint guest arithmetic writes and distinct bytes in the real
//! VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 39] = [
    92, 50, 38, 168, 7, 187, 2, 182, 12, 177, 48, 13, 60, 17, 44, 20, 57, 166,
    70, 66, 68, 47, 80, 54, 9, 212, 172, 225, 158, 226, 171, 11, 214, 156, 227,
    160, 210, 173, 147,
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
fn thirty_nine_distinct_binary_bytes_are_computed_by_guest_arithmetic()
-> Result<(), String> {
    // Fifteen no-ops place the relocating j at source position 15.
    // Two internal no-ops before byte indices 2 and 18 shift data addresses;
    // rotations at 3, 10, 17, 24, 31 and 38 ensure distinct output.
    let mut operations = vec![LinearOpcode::NoOperation; 15];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..39usize {
        if index == 2 || index == 18 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if index == 3
                || index == 10
                || index == 17
                || index == 24
                || index == 31
                || index == 38
            {
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
    let expected_writes: Vec<u32> = (120..=122)
        .step_by(2)
        .chain((125..=155).step_by(2))
        .chain((158..=198).step_by(2))
        .collect();
    assert_eq!(writes, expected_writes);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 39);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address)
            .is_ok_and(|position| position >= layout.source().len())
    }));

    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 39);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            input,
        )
        .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(97).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps: 97, .. }));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
