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
//   - A source-independent forty-three-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim forty-three-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: forty-three exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest forty-three-byte compiler owns this physical proof.
// - Summary:
//   - Forty-three relocated guest arithmetic instructions emit distinct bytes.
// - Description:
//   - Each byte is computed by the real VM, not host output substitution.
// - Usage:
//   - cargo test --locked --test guest_forty_three_distinct_literal_witness
// - Defaults:
//   - Does not admit any forty-three-byte C program to the compiler.

//! Forty-three disjoint guest arithmetic writes and distinct real VM bytes.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 43] = [
    81, 46, 79, 29, 26, 47, 27, 28, 36, 38, 17, 167, 5, 184, 252, 182, 64, 45,
    73, 52, 56, 62, 146, 228, 164, 226, 174, 218, 172, 8, 213, 171, 221, 162,
    222, 170, 11, 217, 156, 227, 163, 210, 173,
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
fn forty_three_distinct_binary_bytes_are_computed_by_guest_arithmetic()
-> Result<(), String> {
    // Ten reached no-ops relocate data beyond the source. No-ops
    // preceding outputs 4 and 16 shift later data positions. Rotations
    // at 11, 22, 29 and 36 avoid repeating earlier bytes.
    let mut operations = vec![LinearOpcode::NoOperation; 10];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..43usize {
        if index == 4 || index == 16 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if [11, 22, 29, 36].contains(&index) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 100);
    let layout = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("encode: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    let expected_writes: Vec<u32> = (0..43)
        .map(|i| 125 + 2 * i + u32::from(i >= 4) + u32::from(i >= 16))
        .collect();
    assert_eq!(writes, expected_writes);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 43);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address)
            .is_ok_and(|position| position >= layout.source().len())
    }));

    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 43);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            input,
        )
        .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(100).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps: 100, .. }));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
