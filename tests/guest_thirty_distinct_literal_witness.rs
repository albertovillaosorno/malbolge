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
//   - A source-independent thirty-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim thirty-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: thirty exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - Source-to-guest thirty-byte compilation owns this physical proof.
// - Summary:
//   - Thirty distinct binary bytes are calculated by the real VM.
// - Description:
//   - A reached no-op selects a separate data-memory recurrence phase.
// - Usage:
//   - cargo test --locked --test guest_thirty_distinct_literal_witness
// - Defaults:
//   - Does not admit a thirty-byte C source to the compiler.

//! Thirty source-independent guest arithmetic bytes in the normative VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 30] = [
    0x39, 0xa8, 0x07, 0xda, 0x99, 0xdd, 0xa3, 0xcf, 0xa7, 0xd9, 0x09, 0xd4,
    0xac, 0xe1, 0x9e, 0xe2, 0xab, 0x0b, 0xd6, 0x9c, 0xe3, 0xa0, 0xd2, 0xad,
    0x93, 0xe0, 0x9f, 0xe4, 0xaa, 0xd5,
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
fn thirty_guest_arithmetic_bytes_are_distinct() -> Result<(), String> {
    // The j at position 34 redirects D beyond the 97 graphical source cells.
    // One no-op before the fourth arithmetic pair selects the loader seed
    // phase.
    let mut operations = vec![LinearOpcode::NoOperation; 34];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..30 {
        if index == 3 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if index == 1 || index == 10 || index == 17 || index == 24 {
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
    let expected_writes: Vec<_> = [101u32, 103, 105]
        .into_iter()
        .chain((108u32..=160).step_by(2))
        .collect();
    assert_eq!(writes, expected_writes);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 30);
    assert!(writes.iter().all(|&address| {
        usize::try_from(address)
            .is_ok_and(|value| value >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 30);

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
