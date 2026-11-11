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
//   - A source-independent twenty-five-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim twenty-five-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: twenty-five exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest twenty-five-byte compiler owns this physical proof.
// - Summary:
//   - Twenty-five relocated guest arithmetic instructions emit distinct binary bytes.
// - Description:
//   - Each byte is computed by the real VM, not host output substitution.
// - Usage:
//   - cargo test --locked --test guest_twenty_five_distinct_literal_witness
// - Defaults:
//   - Does not admit any twenty-five-byte source C program to the compiler.

//! Twenty-five disjoint guest arithmetic writes and distinct bytes in the real VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 25] = [
    81, 62, 53, 56, 84, 31, 78, 51, 61, 57, 5, 83, 35, 27, 181, 44, 203, 18, 198, 46, 175, 180,
    248, 202, 14,
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
fn twenty_five_distinct_binary_bytes_are_computed_by_guest_arithmetic() -> Result<(), String> {
    // Twenty-six reached no-ops shift the relocating j to source position 26.
    // Rotate at byte positions 7, 14 and 21; twenty-seven trailing no-ops
    // preserve the source recurrence seed of the proven 28-byte layout.
    let mut operations = vec![LinearOpcode::NoOperation; 26];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..25usize {
        operations.extend([
            if index == 7 || index == 14 || index == 21 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.extend(std::iter::repeat_n(LinearOpcode::NoOperation, 27));
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
            109, 111, 113, 115, 117, 119, 121, 123, 125, 127, 129, 131, 133, 135, 137, 139, 141,
            143, 145, 147, 149, 151, 153, 155, 157
        ]
    );
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 25);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address).is_ok_and(|position| position >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 25);
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
