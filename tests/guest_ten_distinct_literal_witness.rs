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
//   - A source-independent ten-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim ten-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: ten exact VM bytes and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest ten-byte compiler owns this physical proof.
// - Summary:
//   - Ten relocated guest arithmetic instructions emit distinct binary bytes.
// - Description:
//   - Each byte is computed by the real VM, not host output substitution.
// - Usage:
//   - cargo test --locked --test guest_ten_distinct_literal_witness
// - Defaults:
//   - Does not admit any ten-byte source C program to the compiler.

//! Ten independent data writes and distinct output bytes in the real VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{encode_linear_layout, LinearOpcode};
use malbolge::{current_profile, ProfileMachine, RunOutcome};

const EXPECTED: [u8; 10] = [0x51, 0x22, 0xfd, 0xce, 0xa5, 0x98, 0xba, 0xb6, 0x87, 0xcb];

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions independently bind arithmetic to the real VM"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "one physical witness checks writes, exact steps and binary output"
)]
fn ten_distinct_binary_bytes_are_computed_by_guest_arithmetic() -> Result<(), String> {
    // A single reached no-op and relocation precede ten fresh data writes.
    // Rotate at the third arithmetic step avoids later crazy-word repetitions.
    let mut operations = vec![LinearOpcode::NoOperation, LinearOpcode::RelocateDataPointer];
    for index in 0..10usize {
        operations.extend([
            if index == 2 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 23);

    let layout = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("encode: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    assert_eq!(writes, [40, 42, 44, 46, 48, 50, 52, 54, 56, 58]);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 10);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address).is_ok_and(|position| position >= layout.source().len())
    }));
    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 10);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(current_profile(), layout.source(), input)
            .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(23).map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps, .. } if steps == 23));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}
