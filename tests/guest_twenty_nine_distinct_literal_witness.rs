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
//   - A source-independent twenty-nine-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim twenty-nine-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: twenty-nine exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - Source-to-guest twenty-nine-byte compilation owns this physical proof.
// - Summary:
//   - Twenty-nine distinct binary bytes are calculated by the real VM.
// - Description:
//   - One interleaved no-op selects an independently checked data seed phase.
// - Usage:
//   - cargo test --locked --test guest_twenty_nine_distinct_literal_witness
// - Defaults:
//   - Does not admit a twenty-nine-byte C source to the compiler.

//! Twenty-nine source-independent guest arithmetic bytes in the normative VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 29] = [
    0x87, 0xb7, 0xbc, 0xb1, 0x8a, 0xce, 0x9f, 0x9c, 0xb5, 0x2c, 0xcb, 0x12, 0xc6, 0x2e,
    0xaf, 0xb4, 0xf8, 0xca, 0x0e, 0x95, 0x2d, 0xab, 0x33, 0x3d, 0x39, 0x05, 0x53, 0x23,
    0x1b,
];

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions bind source-independent guest arithmetic to the normative VM"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "one physical witness checks disjoint writes, exact steps and output"
)]
fn twenty_nine_distinct_bytes_are_computed_by_guest_arithmetic() -> Result<(), String> {
    // The j at position nine moves D beyond the 105 graphical source cells.
    // One no-op before the second pair changes the guest recurrence phase.
    let mut operations = vec![LinearOpcode::NoOperation; 9];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..29 {
        if index == 1 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if index == 0 || index == 8 || index == 15 || index == 22 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.extend(std::iter::repeat_n(LinearOpcode::NoOperation, 35));
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
    let expected_writes: Vec<_> = std::iter::once(126u32)
        .chain((129u32..=183).step_by(2))
        .collect();
    assert_eq!(writes, expected_writes);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 29);
    assert!(writes.iter().all(|&address| {
        usize::try_from(address).is_ok_and(|value| value >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 29);

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
