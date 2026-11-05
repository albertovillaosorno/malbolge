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
//   - A source-independent forty-seven-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim forty-seven-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: forty-seven exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest forty-seven-byte compiler owns this physical proof.
// - Summary:
//   - Forty-seven relocated guest arithmetic instructions emit distinct bytes.
// - Description:
//   - Every byte is computed by the real VM, not host output substitution.
// - Usage:
//   - cargo test --locked --test guest_forty_seven_distinct_literal_witness
// - Defaults:
//   - Does not admit any forty-seven-byte source C program to the compiler.

//! Forty-seven disjoint guest arithmetic writes and distinct bytes in the real
//! VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 47] = [
    5, 252, 205, 167, 216, 194, 187, 195, 215, 64, 65, 89, 36, 90, 28, 27, 46,
    79, 47, 26, 72, 185, 253, 211, 23, 157, 51, 183, 176, 59, 175, 55, 81, 29,
    80, 56, 54, 74, 53, 20, 44, 63, 45, 10, 70, 38, 17,
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
fn forty_seven_distinct_binary_bytes_are_computed_by_guest_arithmetic()
-> Result<(), String> {
    // Sixteen reached no-ops reach a safe relocation at source position 16.
    // Six interleaved no-ops shift the disjoint guest arithmetic data words.
    // Five rotations break repeated low-byte values in the crazy trace.
    let mut operations = vec![LinearOpcode::NoOperation; 16];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..47usize {
        if [3, 14, 16, 31, 37, 40].contains(&index) {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if [0, 1, 9, 21, 28].contains(&index) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 118);
    let layout = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("encode: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    let expected_writes: Vec<u32> = (0..47)
        .map(|i| {
            119 + 2 * i
                + [3, 14, 16, 31, 37, 40]
                    .iter()
                    .filter(|&&pad_at| i >= pad_at)
                    .count() as u32
        })
        .collect();
    assert_eq!(writes, expected_writes);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 47);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address)
            .is_ok_and(|position| position >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 47);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            input,
        )
        .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(118).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps: 118, .. }));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    // One additional source cell consumes the relocation's strict data/code
    // gap; the independently admitted backend must refuse the overlap.
    operations.insert(operations.len() - 1, LinearOpcode::NoOperation);
    assert!(matches!(
        encode_linear_layout(current_profile(), &operations),
        Err(layout::LinearLayoutError::UnsafeDataPlacement)
    ));
    Ok(())
}
