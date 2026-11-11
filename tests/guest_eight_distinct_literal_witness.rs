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
//   - A source-independent eight-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim eight-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: eight exact VM bytes, 21 steps and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest eight-byte compiler owns this physical proof.
// - Summary:
//   - Eight relocated guest arithmetic instructions emit distinct binary bytes.
// - Description:
//   - Seven CrazyData writes and one RotateData write compute eight bytes.
// - Usage:
//   - cargo test --locked --test guest_eight_distinct_literal_witness
// - Defaults:
//   - Does not admit any eight-byte source C program to the compiler.

//! Eight independent data writes and eight distinct output bytes in the real VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 8] = [0x53, 0x20, 0x17, 0x3c, 0x36, 0x01, 0x52, 0x06];

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions independently bind guest arithmetic to the actual VM"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "one physical witness checks writes, exact steps and binary VM output"
)]
fn eight_distinct_binary_bytes_are_computed_by_guest_arithmetic() -> Result<(), String> {
    // The exact source length and relocation phase determine expanded data.
    let mut operations = vec![LinearOpcode::NoOperation; 3];
    operations.push(LinearOpcode::RelocateDataPointer);
    for _ in 0usize..7 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.extend([LinearOpcode::RotateData, LinearOpcode::OutputByte]);
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 21);

    let layout = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("encode: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    assert_eq!(writes, [38, 40, 42, 44, 46, 48, 50, 52]);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 8);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address).is_ok_and(|position| position >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 8);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(current_profile(), layout.source(), input)
            .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(21).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps, .. } if steps == 21));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
