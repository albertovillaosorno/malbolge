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
//   - A source-independent twenty-three-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim twenty-three-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: twenty-three exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest twenty-three-byte compiler owns this physical proof.
// - Summary:
//   - Twenty-three relocated guest arithmetic instructions emit distinct binary bytes.
// - Description:
//   - Each byte is computed by the real VM, not host output substitution.
// - Usage:
//   - cargo test --locked --test guest_twenty_three_distinct_literal_witness
// - Defaults:
//   - Does not admit any twenty-three-byte source C program to the compiler.

//! Twenty-three disjoint guest arithmetic writes and distinct bytes in the real VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 23] = [
    66, 14, 47, 23, 57, 4, 142, 36, 159, 27, 160, 35, 151, 21, 40, 39, 41, 20, 50, 30, 139, 38, 146,
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
fn twenty_three_distinct_binary_bytes_are_computed_by_guest_arithmetic() -> Result<(), String> {
    // Eight reached no-ops shift the relocating j to source position 8.
    // Rotate at byte positions 6, 13 and 20; the final no-op changes the
    // source recurrence seed while keeping all writes outside source.
    let mut operations = vec![LinearOpcode::NoOperation; 8];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..23usize {
        operations.extend([
            if index == 6 || index == 13 || index == 20 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::NoOperation);
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 57);
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
            127, 129, 131, 133, 135, 137, 139, 141, 143, 145, 147, 149, 151, 153, 155, 157, 159,
            161, 163, 165, 167, 169, 171
        ]
    );
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 23);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address).is_ok_and(|position| position >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 23);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(current_profile(), layout.source(), input)
            .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(57).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps, .. } if steps == 57));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
