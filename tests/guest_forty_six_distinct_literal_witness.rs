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
//   - A source-independent forty-six-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim forty-six-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: forty-six exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest forty-six-byte compiler owns this physical proof.
// - Summary:
//   - Forty-six relocated guest arithmetic instructions emit distinct bytes.
// - Description:
//   - Every byte is computed by the real VM, not host output substitution.
// - Usage:
//   - cargo test --locked --test guest_forty_six_distinct_literal_witness
// - Defaults:
//   - Does not admit any forty-six-byte source C program to the compiler.

//! Forty-six disjoint guest arithmetic writes and distinct bytes in the real
//! VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 46] = [
    84, 34, 79, 35, 83, 30, 9, 8, 226, 171, 221, 126, 192, 125, 186, 129, 188,
    123, 42, 16, 48, 14, 47, 17, 45, 163, 255, 167, 0, 162, 1, 166, 252, 207,
    165, 206, 159, 210, 161, 204, 144, 227, 174, 225, 173, 228,
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
fn forty_six_distinct_binary_bytes_are_computed_by_guest_arithmetic()
-> Result<(), String> {
    // Ten reached no-ops place the relocation at source position 10.
    // No-ops before outputs 11 and 33 shift the later guest data words.
    // Six rotations avoid byte collisions with earlier guest outputs.
    let mut operations = vec![LinearOpcode::NoOperation; 10];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..46usize {
        if index == 11 || index == 33 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if [6, 7, 18, 25, 29, 40].contains(&index) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 106);
    let layout = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("encode: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    let expected_writes: Vec<u32> = (0..46)
        .map(|i| 125 + 2 * i + u32::from(i >= 11) + u32::from(i >= 33))
        .collect();
    assert_eq!(writes, expected_writes);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 46);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address)
            .is_ok_and(|position| position >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 46);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            input,
        )
        .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(106).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps: 106, .. }));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
