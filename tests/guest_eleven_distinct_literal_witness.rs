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
//   - A source-independent eleven-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim eleven-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: eleven exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest eleven-byte compiler owns this physical proof.
// - Summary:
//   - Eleven relocated guest arithmetic instructions emit distinct binary bytes.
// - Description:
//   - Each byte is computed by the real VM, not host output substitution.
// - Usage:
//   - cargo test --locked --test guest_eleven_distinct_literal_witness
// - Defaults:
//   - Does not admit any eleven-byte source C program to the compiler.

//! Eleven disjoint guest arithmetic writes and distinct bytes in the real VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 11] = [
    0x50, 0x1d, 0x1a, 0x36, 0x05, 0xb4, 0xba, 0xb3, 0x84, 0xcf, 0x9e,
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
fn eleven_distinct_binary_bytes_are_computed_by_guest_arithmetic() -> Result<(), String> {
    // The relocation reads the first code word, then eleven distinct data
    // addresses receive guest writes; rotate at the fifth arithmetic step.
    let mut operations = vec![LinearOpcode::RelocateDataPointer];
    for index in 0..11usize {
        operations.extend([
            if index == 4 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 24);

    let layout = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("encode: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    assert_eq!(writes, [41, 43, 45, 47, 49, 51, 53, 55, 57, 59, 61]);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 11);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address).is_ok_and(|position| position >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 11);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(current_profile(), layout.source(), input)
            .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(24).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps, .. } if steps == 24));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
