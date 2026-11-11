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
//   - A source-independent thirty-four-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim thirty-four-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: thirty-four exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest thirty-four-byte compiler owns this physical proof.
// - Summary:
//   - Thirty-four relocated guest arithmetic instructions emit distinct binary bytes.
// - Description:
//   - Each byte is computed by the real VM, not host output substitution.
// - Usage:
//   - cargo test --locked --test guest_thirty_four_distinct_literal_witness
// - Defaults:
//   - Does not admit any thirty-four-byte source C program to the compiler.

//! Thirty-four disjoint guest arithmetic writes and distinct bytes in the real VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 34] = [
    63, 17, 44, 20, 57, 4, 168, 80, 54, 61, 66, 68, 47, 11, 214, 156, 227,
    160, 210, 173, 147, 224, 159, 228, 170, 213, 174, 9, 212, 172, 225,
    158, 226, 171,
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
fn thirty_four_distinct_binary_bytes_are_computed_by_guest_arithmetic() -> Result<(), String> {
    // Twenty-six no-ops place the relocating j at source position 26.
    // One internal no-op before byte eight shifts later data addresses;
    // rotations at bytes 7, 14, 21, and 28 keep all outputs distinct.
    let mut operations = vec![LinearOpcode::NoOperation; 26];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..34usize {
        if index == 7 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if index == 6 || index == 13 || index == 20 || index == 27 {
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
    let expected_writes: Vec<u32> = (109..=121).step_by(2)
        .chain((124..=176).step_by(2))
        .collect();
    assert_eq!(writes, expected_writes);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 34);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address).is_ok_and(|position| position >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 34);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(current_profile(), layout.source(), input)
            .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(97).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps, .. } if steps == 97));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
