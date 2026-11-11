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
//   - One source-independent thirty-one-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Substitute host-computed output or claim thirty-one-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: thirty-one exact VM bytes with disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - Source-to-guest thirty-one-byte compilation owns this physical proof.
// - Summary:
//   - Thirty-one distinct binary bytes are calculated by the real VM.
// - Description:
//   - One reached no-op selects a disjoint loader-data recurrence phase.
// - Usage:
//   - cargo test --locked --test guest_thirty_one_distinct_literal_witness
// - Defaults:
//   - Does not admit a thirty-one-byte C source to the compiler.

//! Thirty-one source-independent guest arithmetic bytes in the normative VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 31] = [
    0x3f, 0x0b, 0x92, 0x21, 0x94, 0x0e, 0x9d, 0x1c, 0x34, 0x27, 0x2b, 0x25,
    0x35, 0x1d, 0x33, 0x11, 0xa8, 0xa2, 0x95, 0xab, 0x9f, 0x98, 0x14, 0xac,
    0xae, 0xa4, 0x9b, 0xa5, 0xad, 0xa3, 0x9c,
];

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions bind guest arithmetic to the normative VM"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "physical witness checks disjoint writes, steps and output"
)]
fn thirty_one_guest_arithmetic_bytes_are_distinct() -> Result<(), String> {
    // The j at position eight redirects D beyond all 73 source cells.
    // One reached no-op before pair nine shifts the loader recurrence phase.
    let mut operations = vec![LinearOpcode::NoOperation; 8];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..31 {
        if index == 8 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if matches!(index, 2 | 7 | 15 | 22 | 26) {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 73);

    let layout = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("encode: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    let expected_writes: Vec<_> = (127u32..=141)
        .step_by(2)
        .chain((144u32..=188).step_by(2))
        .collect();
    assert_eq!(writes, expected_writes);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 31);
    assert!(writes.iter().all(|&address| {
        usize::try_from(address)
            .is_ok_and(|value| value >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 31);

    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            input,
        )
        .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(73).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps: 73, .. }));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
