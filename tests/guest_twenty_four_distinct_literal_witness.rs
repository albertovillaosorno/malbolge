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
//   - A source-independent twenty-four-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim twenty-four-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: twenty-four exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest twenty-four-byte compiler owns this physical proof.
// - Summary:
//   - Twenty-four relocated guest arithmetic instructions emit distinct binary bytes.
// - Description:
//   - Each byte is computed by the real VM, not host output substitution.
// - Usage:
//   - cargo test --locked --test guest_twenty_four_distinct_literal_witness
// - Defaults:
//   - Does not admit any twenty-four-byte source C program to the compiler.

//! Twenty-four disjoint guest arithmetic writes and distinct bytes in the real VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 24] = [
    62, 11, 44, 18, 54, 1, 61, 149, 15, 157, 23, 139, 33, 147, 146, 32, 148, 14, 155, 24, 138, 28,
    47, 35,
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
fn twenty_four_distinct_binary_bytes_are_computed_by_guest_arithmetic() -> Result<(), String> {
    // Twenty-one reached no-ops shift the relocating j to source position 21.
    // Rotate at byte positions 7, 14 and 21; the final no-op changes the
    // source recurrence seed while keeping all writes outside source.
    let mut operations = vec![LinearOpcode::NoOperation; 21];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..24usize {
        operations.extend([
            if index == 7 || index == 14 || index == 21 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::NoOperation);
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 72);
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
            114, 116, 118, 120, 122, 124, 126, 128, 130, 132, 134, 136, 138, 140, 142, 144, 146,
            148, 150, 152, 154, 156, 158, 160
        ]
    );
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 24);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address).is_ok_and(|position| position >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 24);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(current_profile(), layout.source(), input)
            .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(72).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps, .. } if steps == 72));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
